# -*- coding: utf-8 -*-
"""
Jarvis Gateway Guard — owner allowlist + 멱등 dedup + token bucket (owner 문제 2.1)

설계: 20260524_JARVIS_ARCHITECTURE_v2.md §5.1 / §0.7
LLM 호출 前 게이트 (비용 방화벽). sqlite_ledger 의 dedup/token_bucket 사용.

흐름 (LLM/큐 진입 이전):
1) owner allowlist  — owner chat_id 외 hard-reject (개인 자비스)
2) dedup            — update_id + content_hash (재전송/재시작/409 복원 흡수). 중복이면 처리 0.
3) token bucket     — per-chat (+ 선택 cost-route). 초과 시 rate_limited (LLM 호출 안 함).
→ 통과 시에만 ACCEPT (request_id 반환).
"""
from __future__ import annotations

import sys
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Optional

# ── ledger import (경로 robust, standalone 테스트 가능) ──
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "queue"))
import sqlite_ledger as ledger  # type: ignore  # noqa: E402


class Action(str, Enum):
    ACCEPT = "accept"
    DUPLICATE = "duplicate"
    RATE_LIMITED = "rate_limited"
    UNAUTHORIZED = "unauthorized"


@dataclass
class GatewayDecision:
    action: Action
    request_id: Optional[str] = None
    reason: str = ""
    retry_after_sec: float = 0.0


# per-chat 토큰버킷 기본값 (owner 개인 채팅 = 넉넉, 비-owner = 즉시 거부됨)
OWNER_BUCKET = {"capacity": 5.0, "refill_per_sec": 2.0}
# cost-route 버킷 (검증 보고서 #5 권고: 비용 클래스 분리)
COST_ROUTE_BUCKETS = {
    "cloud_coder": {"capacity": 5.0, "refill_per_sec": 0.05},   # Codex/Claude CLI 등 고비용
    "image": {"capacity": 4.0, "refill_per_sec": 0.05},
    "video": {"capacity": 2.0, "refill_per_sec": 0.02},
    "research": {"capacity": 8.0, "refill_per_sec": 0.1},
    "local": {"capacity": 60.0, "refill_per_sec": 5.0},          # 로컬 L1 = 사실상 자유
}


def check_inbound(conn, *, source: str, update_id: str, chat_id: str, user_id: str,
                  text: str, owner_chat_id: str,
                  owner_bucket: dict = OWNER_BUCKET) -> GatewayDecision:
    """인입 메시지 게이트. ACCEPT 시에만 하류(LLM/큐) 진입 허용."""
    # 1) owner allowlist (개인 자비스 — owner 외 차단)
    if str(chat_id) != str(owner_chat_id):
        ledger.audit(conn, actor=str(user_id), event_type="gateway_unauthorized",
                     detail={"chat_id": str(chat_id), "source": source})
        return GatewayDecision(Action.UNAUTHORIZED, reason="owner allowlist 외 chat_id")

    # 2) dedup (update_id + content_hash)
    chash = ledger.content_hash(source, chat_id, user_id, text)
    is_dup, request_id = ledger.seen_or_mark(conn, source=source, update_id=str(update_id), chash=chash)
    if is_dup:
        return GatewayDecision(Action.DUPLICATE, request_id=request_id, reason="중복 update")

    # 3) per-chat token bucket (LLM 호출 前)
    key = f"chat:{chat_id}"
    allowed = ledger.token_bucket_consume(
        conn, key=key, capacity=owner_bucket["capacity"], refill_per_sec=owner_bucket["refill_per_sec"])
    if not allowed:
        ledger.audit(conn, actor=str(user_id), event_type="gateway_rate_limited",
                     detail={"chat_id": str(chat_id)})
        return GatewayDecision(Action.RATE_LIMITED, request_id=request_id,
                               reason="per-chat rate limit", retry_after_sec=1.0)

    return GatewayDecision(Action.ACCEPT, request_id=request_id)


def check_cost_route(conn, *, route: str) -> bool:
    """고비용 lane(cloud_coder/image/video 등) 실행 직전 cost-route 버킷 소비. True=허용."""
    cfg = COST_ROUTE_BUCKETS.get(route, COST_ROUTE_BUCKETS["local"])
    return ledger.token_bucket_consume(conn, key=f"route:{route}", capacity=cfg["capacity"],
                                       refill_per_sec=cfg["refill_per_sec"])


if __name__ == "__main__":
    import tempfile, os
    db = os.path.join(tempfile.mkdtemp(), "gw.db")
    c = ledger.connect(db)
    ledger.init_schema(c)
    OWNER = "1566967334"
    print("first:", check_inbound(c, source="telegram", update_id="1", chat_id=OWNER, user_id=OWNER, text="hi", owner_chat_id=OWNER).action.value)
    print("dup:  ", check_inbound(c, source="telegram", update_id="1", chat_id=OWNER, user_id=OWNER, text="hi", owner_chat_id=OWNER).action.value)
    print("other:", check_inbound(c, source="telegram", update_id="2", chat_id="999", user_id="999", text="hi", owner_chat_id=OWNER).action.value)
