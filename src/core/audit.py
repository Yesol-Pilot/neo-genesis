# -*- coding: utf-8 -*-
"""
Sora — AuditLogger

모든 도구 실행 이벤트를 JSONL 파일에 기록.
대시보드의 /api/v2/audit 엔드포인트를 통해 조회 가능.

로그 위치: data/logs/sora_audit.jsonl
항목 보존: 최근 30일 (자동 순환 없음 — 로그 분석용)
"""
import asyncio
import json
import logging
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

logger = logging.getLogger("neo.audit")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
AUDIT_LOG_PATH = PROJECT_ROOT / "data" / "logs" / "sora_audit.jsonl"
AUDIT_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)

# 파일 쓰기 잠금 (동시 쓰기 방지)
_write_lock = asyncio.Lock()


class AuditLogger:
    """도구 실행 감사 로그 — JSONL 파일 기록."""

    async def log(
        self,
        request_id: str,
        user_message: str,
        tools_executed: list[str],
        duration_ms: float,
        strategy: str = "unknown",
        confirm_required: bool = False,
        confirm_response: Optional[str] = None,
        error: Optional[str] = None,
        tokens_in: int = 0,
        tokens_out: int = 0,
    ) -> None:
        """감사 로그 항목 기록.

        Args:
            request_id: 요청 고유 ID
            user_message: 사용자 원본 메시지 (200자 제한)
            tools_executed: 실행된 도구 이름 목록
            duration_ms: 처리 소요 시간 (밀리초)
            strategy: 처리 경로 (task_planner / agent_router / direct)
            confirm_required: 위험 작업 확인 요청 여부
            confirm_response: 확인 응답 (approved / rejected / timeout)
            error: 에러 메시지 (있을 경우)
            tokens_in: 입력 토큰 수 (추정)
            tokens_out: 출력 토큰 수 (추정)
        """
        entry = {
            "ts": datetime.now().isoformat(),
            "request_id": request_id,
            "user_message": user_message[:200],
            "strategy": strategy,
            "tools_executed": tools_executed,
            "tools_count": len(tools_executed),
            "confirm_required": confirm_required,
            "confirm_response": confirm_response,
            "duration_ms": round(duration_ms, 1),
            "tokens_in": tokens_in,
            "tokens_out": tokens_out,
            "error": error[:200] if error else None,
        }
        try:
            async with _write_lock:
                with open(AUDIT_LOG_PATH, "a", encoding="utf-8") as f:
                    f.write(json.dumps(entry, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"[Audit] 로그 기록 실패: {e}")

    def read_recent(self, limit: int = 50) -> list[dict]:
        """최근 N개 감사 로그 반환 (최신순).

        Args:
            limit: 반환할 최대 항목 수
        """
        if not AUDIT_LOG_PATH.exists():
            return []
        try:
            lines = AUDIT_LOG_PATH.read_text(encoding="utf-8").strip().splitlines()
            entries = []
            for line in reversed(lines[-limit * 2:]):
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    continue
                if len(entries) >= limit:
                    break
            return entries
        except Exception as e:
            logger.warning(f"[Audit] 로그 읽기 실패: {e}")
            return []

    def get_stats(self, hours: int = 24) -> dict:
        """최근 N시간 통계 반환."""
        cutoff = time.time() - hours * 3600
        entries = self.read_recent(limit=10000)
        recent = [
            e for e in entries
            if e.get("ts", "") >= datetime.fromtimestamp(cutoff).isoformat()
        ]
        if not recent:
            return {"period_hours": hours, "total": 0}

        tool_counts: dict[str, int] = {}
        for entry in recent:
            for tool in entry.get("tools_executed", []):
                tool_counts[tool] = tool_counts.get(tool, 0) + 1

        return {
            "period_hours": hours,
            "total": len(recent),
            "errors": sum(1 for e in recent if e.get("error")),
            "avg_duration_ms": round(
                sum(e.get("duration_ms", 0) for e in recent) / len(recent), 1
            ),
            "confirm_required": sum(1 for e in recent if e.get("confirm_required")),
            "top_tools": sorted(tool_counts.items(), key=lambda x: -x[1])[:5],
        }


# 싱글턴
_audit_logger: Optional[AuditLogger] = None


def get_audit_logger() -> AuditLogger:
    global _audit_logger
    if _audit_logger is None:
        _audit_logger = AuditLogger()
    return _audit_logger
