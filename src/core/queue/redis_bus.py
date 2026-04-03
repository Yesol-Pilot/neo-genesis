# -*- coding: utf-8 -*-
"""
Sora v2.0 — Redis Message Bus

Gateway ↔ Brain Worker 간 비동기 메시지 전달.
Gateway는 LLM을 직접 호출하지 않고, Redis 큐에 요청을 넣고 결과를 기다림.
Brain Worker가 큐에서 요청을 꺼내 LLM 호출 후 결과를 publish.

Architecture:
    [Gateway] --enqueue--> [Redis Queue] --dequeue--> [Brain Worker]
    [Brain Worker] --publish--> [Redis PubSub] --subscribe--> [Gateway]
"""
import asyncio
import json
import logging
import os
import time
import uuid
from typing import Any, Callable, Optional

import redis.asyncio as aioredis

logger = logging.getLogger("neo.queue.redis")

# ── 설정 ──
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379/0")
REQUEST_QUEUE = "sora:requests"          # Brain Worker가 소비하는 큐
RESULT_CHANNEL = "sora:results"          # 결과 pubsub 채널
DEVICE_CHANNEL = "sora:devices"          # 디바이스 이벤트 채널
DEFAULT_TIMEOUT = 120                     # 응답 대기 최대 시간 (초)


class RedisBus:
    """Redis 기반 메시지 버스 — Gateway와 Brain Worker 간 통신."""

    def __init__(self, redis_url: str = REDIS_URL):
        self._redis_url = redis_url
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._pending: dict[str, asyncio.Future] = {}  # request_id → Future
        self._handlers: dict[str, Callable] = {}       # channel → handler
        self._listener_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Redis 연결."""
        if self._redis is None:
            self._redis = aioredis.from_url(
                self._redis_url,
                decode_responses=True,
                socket_connect_timeout=5,
            )
            await self._redis.ping()
            logger.info(f"[RedisBus] 연결 완료: {self._redis_url}")
        return self._redis

    async def close(self):
        """연결 종료."""
        if self._listener_task:
            self._listener_task.cancel()
        if self._pubsub:
            await self._pubsub.unsubscribe()
            await self._pubsub.close()
        if self._redis:
            await self._redis.close()
        logger.info("[RedisBus] 연결 종료")

    # ── 요청 큐 (Gateway → Brain) ──

    async def enqueue_request(
        self,
        text: str,
        channel: str = "telegram",
        device_id: str = "cloud",
        chat_id: str = "",
        file_path: str = "",
        metadata: dict = None,
    ) -> str:
        """LLM 요청을 큐에 넣고 request_id 반환.

        Args:
            text: 사용자 메시지
            channel: 요청 채널 (telegram, dashboard, cli)
            device_id: 요청 디바이스
            chat_id: 텔레그램 chat_id 등 (응답 라우팅용)
            file_path: 첨부 파일 경로
            metadata: 추가 메타데이터
        """
        redis = await self.connect()
        request_id = f"req-{uuid.uuid4().hex[:12]}"

        message = json.dumps({
            "request_id": request_id,
            "text": text,
            "channel": channel,
            "device_id": device_id,
            "chat_id": chat_id,
            "file_path": file_path,
            "metadata": metadata or {},
            "timestamp": time.time(),
        }, ensure_ascii=False)

        await redis.lpush(REQUEST_QUEUE, message)
        logger.info(f"[RedisBus] 요청 큐 적재: {request_id} ({channel}) {text[:50]}")
        return request_id

    async def dequeue_request(self, timeout: int = 0) -> Optional[dict]:
        """큐에서 요청을 꺼냄 (Brain Worker용). BRPOP으로 블로킹 대기.

        Args:
            timeout: 대기 시간 (초, 0=무한)
        """
        redis = await self.connect()
        result = await redis.brpop(REQUEST_QUEUE, timeout=timeout)
        if result:
            _, message = result
            return json.loads(message)
        return None

    # ── 결과 발행 (Brain → Gateway) ──

    async def publish_result(self, request_id: str, result: dict):
        """처리 결과를 pubsub으로 발행.

        Args:
            request_id: 원래 요청 ID
            result: {"reply": "...", "error": None, "metadata": {...}}
        """
        redis = await self.connect()
        message = json.dumps({
            "request_id": request_id,
            **result,
            "completed_at": time.time(),
        }, ensure_ascii=False)

        await redis.publish(RESULT_CHANNEL, message)

        # 결과를 짧은 TTL로 저장 (late subscriber가 폴링으로 확인 가능)
        await redis.set(f"sora:result:{request_id}", message, ex=300)
        logger.debug(f"[RedisBus] 결과 발행: {request_id}")

    # ── 결과 대기 (Gateway용) ──

    async def wait_for_result(self, request_id: str, timeout: float = DEFAULT_TIMEOUT) -> dict:
        """특정 request_id의 결과를 대기.

        pubsub 리스너가 돌고 있으면 Future로 즉시 받고,
        아니면 폴링으로 확인.
        """
        # 1. Future 기반 (pubsub 리스너 활성 시)
        if self._listener_task and not self._listener_task.done():
            loop = asyncio.get_running_loop()
            future = loop.create_future()
            self._pending[request_id] = future
            try:
                result = await asyncio.wait_for(future, timeout=timeout)
                return result
            except asyncio.TimeoutError:
                return {"reply": "⏰ 응답 시간이 초과되었습니다.", "error": "timeout"}
            finally:
                self._pending.pop(request_id, None)

        # 2. 폴링 기반 (폴백)
        redis = await self.connect()
        deadline = time.time() + timeout
        while time.time() < deadline:
            cached = await redis.get(f"sora:result:{request_id}")
            if cached:
                return json.loads(cached)
            await asyncio.sleep(0.5)

        return {"reply": "⏰ 응답 시간이 초과되었습니다.", "error": "timeout"}

    # ── PubSub 리스너 ──

    async def start_listener(self):
        """결과 채널 구독 시작 (Gateway 프로세스에서 호출)."""
        redis = await self.connect()
        self._pubsub = redis.pubsub()
        await self._pubsub.subscribe(RESULT_CHANNEL, DEVICE_CHANNEL)

        async def _listen():
            try:
                async for message in self._pubsub.listen():
                    if message["type"] != "message":
                        continue
                    channel = message["channel"]
                    data = json.loads(message["data"])

                    if channel == RESULT_CHANNEL:
                        req_id = data.get("request_id")
                        if req_id and req_id in self._pending:
                            future = self._pending.pop(req_id)
                            if not future.done():
                                future.set_result(data)

                    # 커스텀 핸들러
                    handler = self._handlers.get(channel)
                    if handler:
                        try:
                            await handler(data) if asyncio.iscoroutinefunction(handler) else handler(data)
                        except Exception as e:
                            logger.error(f"[RedisBus] 핸들러 에러 ({channel}): {e}")

            except asyncio.CancelledError:
                pass
            except Exception as e:
                logger.error(f"[RedisBus] 리스너 에러: {e}")

        self._listener_task = asyncio.create_task(_listen())
        logger.info("[RedisBus] PubSub 리스너 시작")

    def on(self, channel: str, handler: Callable):
        """특정 채널에 핸들러 등록."""
        self._handlers[channel] = handler

    # ── 유틸리티 ──

    async def get_queue_length(self) -> int:
        """대기 중인 요청 수."""
        redis = await self.connect()
        return await redis.llen(REQUEST_QUEUE)

    async def publish_event(self, channel: str, data: dict):
        """임의 채널에 이벤트 발행."""
        redis = await self.connect()
        await redis.publish(channel, json.dumps(data, ensure_ascii=False))

    async def health_check(self) -> bool:
        """Redis 연결 상태 확인."""
        try:
            redis = await self.connect()
            return await redis.ping()
        except Exception:
            return False


# ── 싱글턴 ──
_bus: Optional[RedisBus] = None


def get_redis_bus() -> RedisBus:
    """RedisBus 싱글턴."""
    global _bus
    if _bus is None:
        _bus = RedisBus()
    return _bus
