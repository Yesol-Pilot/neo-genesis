# -*- coding: utf-8 -*-
"""
MANUAL 라이브 스모크 (CI 아님) — orchestrator → worker_dispatch → 실제 CLI → 증거게이트 전 경로.

⚠️ 실제 `claude -p` (또는 codex/ollama) 호출 = 구독 quota 소모. 검증용 1회.
실행: python tests/core/smoke_live_dispatch.py
"""
from __future__ import annotations

import os
import sys
import tempfile
from pathlib import Path

_JARVIS = Path(__file__).resolve().parents[2] / "src" / "core" / "jarvis"
_QUEUE = Path(__file__).resolve().parents[2] / "src" / "core" / "queue"
sys.path.insert(0, str(_QUEUE))
sys.path.insert(0, str(_JARVIS))
import sqlite_ledger as ledger  # noqa: E402
import orchestrator as O  # noqa: E402

try:  # Windows cp949 콘솔에서 이모지 출력 크래시 방지
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

OWNER = "1566967334"


def main():
    db = os.path.join(tempfile.mkdtemp(), "smoke.db")
    conn = ledger.connect(db)
    ledger.init_schema(conn)

    # 기본 = DESIGN lane(claude). argv[1] 주면 그 메시지로 (예: CHAT lane → 로컬 ollama)
    text = sys.argv[1] if len(sys.argv) > 1 else \
        "이 한 줄 함수의 시간복잡도를 한 문장으로 평가해: def f(n): return sum(range(n))"
    print(f"[입력] {text}")
    print("[실행] orchestrator.handle_message (real runner = 실제 claude -p)...")
    r = O.handle_message(conn, source="cli", update_id="1", chat_id=OWNER, user_id=OWNER,
                         text=text, owner_chat_id=OWNER)

    print("\n=== 결과 ===")
    print("action:", r.get("action"))
    print("engine:", r.get("engine"))
    disp = r.get("dispatch", {})
    print("tool:", disp.get("tool"), "| exit:", disp.get("exit_code"),
          "| status:", disp.get("status"), "| can_report_success:", disp.get("can_report_success"))
    print("reason:", disp.get("reason"))
    print("stdout[:200]:", (disp.get("stdout") or "")[:200])
    print("report:", (r.get("report") or "").encode("ascii", "replace").decode())

    # ledger 에 실제 tool_run 증거가 기록됐는지 직접 확인 (증거게이트 검증)
    rows = conn.execute("SELECT tool_name, status, exit_code, output_hash FROM tool_runs").fetchall()
    print("\n=== tool_runs 증거 (DB) ===")
    for row in rows:
        print(dict(row))
    jobs = conn.execute("SELECT status FROM jobs").fetchall()
    print("job status:", [j["status"] for j in jobs])

    # 판정
    ok = (disp.get("tool") == "claude" and disp.get("exit_code") == 0
          and disp.get("can_report_success") is True and "실행 완료" in (r.get("report") or ""))
    print("\n[VERDICT]", "PASS — 실 claude 워커 + 증거게이트 end-to-end OK" if ok else "CHECK — 위 출력 확인 필요")
    conn.close()


if __name__ == "__main__":
    main()
