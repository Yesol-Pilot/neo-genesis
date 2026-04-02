# -*- coding: utf-8 -*-
"""
Sora v2.0 — Telegram Webhook Router

polling 모드 대신 webhook으로 텔레그램 메시지를 수신.
메시지를 Redis 큐에 넣고, Brain Worker가 처리 후 직접 응답 전송.
Gateway(FastAPI)의 이벤트 루프를 절대 블로킹하지 않음.
"""
import json
import logging
import os

from fastapi import APIRouter, Request, Response

logger = logging.getLogger("neo.gateway.telegram")

BOT_TOKEN = os.getenv("NEO_ALERT_BOT_TOKEN", "")
ALLOWED_CHAT_ID = os.getenv("NEO_ALERT_CHAT_ID", "")

router = APIRouter()


@router.post("/api/telegram/webhook")
async def telegram_webhook(request: Request):
    """텔레그램 webhook 수신 → Redis 큐 적재."""
    try:
        from src.core.queue.redis_bus import get_redis_bus

        body = await request.json()
        message = body.get("message", {})

        if not message:
            return Response(status_code=200)

        chat_id = str(message.get("chat", {}).get("id", ""))
        text = message.get("text", "")
        photo = message.get("photo")
        document = message.get("document")

        # 권한 확인
        if ALLOWED_CHAT_ID and chat_id != ALLOWED_CHAT_ID:
            logger.warning(f"[TG] 미인가 chat_id: {chat_id}")
            return Response(status_code=200)

        if not text and not photo and not document:
            return Response(status_code=200)

        # 사진/문서 처리 (캡션 추출)
        if photo:
            text = message.get("caption", "이 이미지를 분석해주세요.")
        elif document:
            doc_name = document.get("file_name", "document")
            text = message.get("caption", f"이 파일({doc_name})을 분석해주세요.")

        logger.info(f"[TG] 수신: {chat_id} → {text[:50]}")

        # Redis 큐에 적재 (Brain Worker가 처리)
        bus = get_redis_bus()
        request_id = await bus.enqueue_request(
            text=text,
            channel="telegram",
            device_id="phone",
            chat_id=chat_id,
            metadata={"from": message.get("from", {})},
        )

        logger.info(f"[TG] 큐 적재 완료: {request_id}")
        return Response(status_code=200)

    except Exception as e:
        logger.error(f"[TG] webhook 에러: {e}", exc_info=True)
        return Response(status_code=200)  # 텔레그램에 항상 200 반환


@router.post("/api/telegram/set-webhook")
async def set_telegram_webhook(request: Request):
    """텔레그램 webhook URL 등록."""
    try:
        import httpx
        body = await request.json()
        webhook_url = body.get("url", "")

        if not webhook_url:
            return {"error": "url 필수"}

        async with httpx.AsyncClient() as client:
            r = await client.post(
                f"https://api.telegram.org/bot{BOT_TOKEN}/setWebhook",
                json={"url": webhook_url, "drop_pending_updates": True},
            )
            return r.json()

    except Exception as e:
        return {"error": str(e)}


@router.get("/api/telegram/webhook-info")
async def get_webhook_info():
    """현재 webhook 상태 확인."""
    try:
        import httpx
        async with httpx.AsyncClient() as client:
            r = await client.get(
                f"https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo",
            )
            return r.json()
    except Exception as e:
        return {"error": str(e)}
