# -*- coding: utf-8 -*-
"""
Sora — ProgressReporter

Brain Worker에서 실행 단계별 진행 상태를 Redis pubsub으로 발행.
neo_assistant_bot.py의 구독 루프가 수신하여 텔레그램 메시지를 편집.

흐름:
    [BrainWorker] → ProgressReporter.update() → Redis pubsub
    [neo_assistant_bot] ← subscribe_progress() ← Redis pubsub
    [neo_assistant_bot] → edit_message_text(progress_msg)
"""
import asyncio
import logging
import time
from typing import Optional

logger = logging.getLogger("neo.progress")

# 텔레그램 edit_message_text 최소 간격 (초) — Rate Limit 대응
_MIN_INTERVAL = 2.0


class ProgressReporter:
    """단일 요청의 진행 상태를 Redis pubsub으로 발행."""

    def __init__(self, bus, request_id: str, chat_id: str):
        """
        Args:
            bus: RedisBus 인스턴스
            request_id: 요청 고유 ID (sora:progress:{request_id} 채널에 발행)
            chat_id: 텔레그램 chat_id (구독자가 어느 채팅에 편집할지 식별)
        """
        self.bus = bus
        self.request_id = request_id
        self.chat_id = chat_id
        self._step = 0
        self._last_publish: float = 0.0

    async def update(
        self,
        message: str,
        tool_name: Optional[str] = None,
        status: str = "running",
        force: bool = False,
    ) -> None:
        """진행 이벤트 발행.

        Args:
            message: 표시할 진행 메시지 (예: "🔧 웹 검색 중...")
            tool_name: 현재 실행 중인 도구 이름 (선택)
            status: running | step_done | error | confirm_required
            force: Rate Limit throttle 무시 여부 (확인 요청 등 즉시 전달 필요 시)
        """
        now = time.time()
        # Rate Limit throttle (force=True이면 무시)
        if not force and (now - self._last_publish) < _MIN_INTERVAL:
            return
        self._last_publish = now
        self._step += 1

        try:
            await self.bus.publish_progress(self.request_id, {
                "chat_id": self.chat_id,
                "request_id": self.request_id,
                "step": self._step,
                "message": message,
                "tool_name": tool_name,
                "status": status,
                "ts": now,
            })
        except Exception as e:
            logger.debug(f"[Progress] 발행 실패 (무시): {e}")

    async def confirm_required(self, action_description: str) -> None:
        """위험 작업 확인 요청 이벤트 발행 (즉시 전달)."""
        await self.update(
            message=action_description,
            status="confirm_required",
            force=True,
        )

    async def error(self, message: str) -> None:
        """에러 이벤트 발행 (즉시 전달)."""
        await self.update(message=message, status="error", force=True)
