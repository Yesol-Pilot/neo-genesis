# -*- coding: utf-8 -*-
"""
Sora v2.0 — Chat REST API

sora-app, 대시보드, CLI에서 소라와 대화하기 위한 엔드포인트.
메시지를 Redis 큐에 넣고, Brain Worker 응답을 기다려 반환.
Gateway 이벤트 루프를 블로킹하지 않음.
"""
import logging
from fastapi import APIRouter, Request
from pydantic import BaseModel

logger = logging.getLogger("neo.gateway.chat")

router = APIRouter()


class ChatRequest(BaseModel):
    message: str
    channel: str = "dashboard"
    device_id: str = "web"
    session_id: str = "default"


class ChatResponse(BaseModel):
    reply: str
    error: str | None = None
    request_id: str = ""
    latency_ms: float = 0


@router.post("/api/chat", response_model=ChatResponse)
async def chat(body: ChatRequest):
    """소라에게 메시지 전송 → Brain Worker 처리 → 응답 반환.

    흐름: Gateway → Redis Queue → Brain Worker → Redis PubSub → Gateway → 응답
    """
    try:
        from src.core.queue.redis_bus import get_redis_bus
        bus = get_redis_bus()
        await bus.connect()

        # Redis 큐에 적재
        request_id = await bus.enqueue_request(
            text=body.message,
            channel=body.channel,
            device_id=body.device_id,
        )

        # Brain Worker 응답 대기 (최대 90초)
        result = await bus.wait_for_result(request_id, timeout=90)

        return ChatResponse(
            reply=result.get("reply", "응답 없음"),
            error=result.get("error"),
            request_id=request_id,
            latency_ms=result.get("metadata", {}).get("latency_ms", 0),
        )

    except Exception as e:
        logger.error(f"[Chat] 에러: {e}")
        return ChatResponse(
            reply=f"⚠️ 처리 중 오류: {str(e)[:200]}",
            error=str(e)[:200],
        )


@router.get("/api/chat/health")
async def chat_health():
    """채팅 시스템 헬스체크 (Redis + Brain Worker 상태)."""
    try:
        from src.core.queue.redis_bus import get_redis_bus
        bus = get_redis_bus()
        redis_ok = await bus.health_check()
        queue_len = await bus.get_queue_length() if redis_ok else -1
        return {
            "redis": "ok" if redis_ok else "down",
            "queue_length": queue_len,
            "status": "healthy" if redis_ok else "degraded",
        }
    except Exception as e:
        return {"redis": "error", "status": "unhealthy", "error": str(e)[:200]}
