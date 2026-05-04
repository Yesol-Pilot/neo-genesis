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
from pathlib import Path
import subprocess
import sys
import time
import uuid
from typing import Any, Callable, Optional
from urllib.parse import SplitResult, urlsplit, urlunsplit

import redis.asyncio as aioredis
from redis.exceptions import ConnectionError as RedisConnectionError, TimeoutError as RedisTimeoutError

logger = logging.getLogger("neo.queue.redis")

# ── 설정 ──
PROJECT_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_REDIS_URL = "redis://localhost:6379/0"


def _load_local_redis_password() -> Optional[str]:
    password_file = PROJECT_ROOT / "data" / "automation" / "redis_password.txt"
    try:
        password = password_file.read_text(encoding="ascii").strip()
    except OSError:
        return None
    return password or None


def _default_redis_url() -> str:
    password = os.getenv("SORA_REDIS_PASSWORD") or _load_local_redis_password()
    if password:
        return f"redis://:{password}@localhost:6379/0"
    return DEFAULT_REDIS_URL


def _redact_redis_url(redis_url: str) -> str:
    parsed = urlsplit(redis_url)
    if "@" not in parsed.netloc:
        return redis_url
    host_part = parsed.netloc.rsplit("@", 1)[1]
    return urlunsplit(
        SplitResult(
            scheme=parsed.scheme,
            netloc=f"***@{host_part}",
            path=parsed.path,
            query=parsed.query,
            fragment=parsed.fragment,
        )
    )


REDIS_URL = os.getenv("REDIS_URL", _default_redis_url())
REDIS_WSL_DISTRO = os.getenv("SORA_WSL_DISTRO", "Ubuntu-24.04")
REQUEST_QUEUE = "sora:requests"          # Brain Worker가 소비하는 큐
RESULT_CHANNEL = "sora:results"          # 결과 pubsub 채널
DEVICE_CHANNEL = "sora:devices"          # 디바이스 이벤트 채널
PROGRESS_PREFIX = "sora:progress:"       # 진행 이벤트 채널 prefix (+ request_id)
CONFIRM_PREFIX = "sora:confirm:"         # 확인 응답 키 prefix (+ request_id)
DEFAULT_TIMEOUT = 120                     # 응답 대기 최대 시간 (초)


def _is_windows_localhost_url(redis_url: str) -> bool:
    parsed = urlsplit(redis_url)
    return sys.platform.startswith("win") and (parsed.hostname or "").lower() in {"localhost", "127.0.0.1"}


def _resolve_wsl_primary_ip(distro: str) -> Optional[str]:
    try:
        completed = subprocess.run(
            ["wsl.exe", "-d", distro, "--", "bash", "-lc", "hostname -I 2>/dev/null"],
            capture_output=True,
            text=False,
            timeout=5,
            check=False,
        )
    except Exception:
        return None

    if completed.returncode != 0:
        return None

    try:
        stdout = completed.stdout.decode("utf-8", errors="ignore")
    except Exception:
        stdout = ""

    for token in stdout.strip().split():
        if token.count(".") == 3:
            return token
    return None


def _replace_redis_host(redis_url: str, host: str) -> str:
    parsed = urlsplit(redis_url)
    auth = ""
    if parsed.username:
        auth = parsed.username
        if parsed.password:
            auth += f":{parsed.password}"
        auth += "@"

    port = parsed.port or 6379
    replaced = SplitResult(
        scheme=parsed.scheme or "redis",
        netloc=f"{auth}{host}:{port}",
        path=parsed.path or "/0",
        query=parsed.query,
        fragment=parsed.fragment,
    )
    return urlunsplit(replaced)


def _build_redis_url_candidates(redis_url: str) -> list[str]:
    candidates = [redis_url]
    if _is_windows_localhost_url(redis_url):
        wsl_ip = _resolve_wsl_primary_ip(REDIS_WSL_DISTRO)
        if wsl_ip:
            candidates.append(_replace_redis_host(redis_url, wsl_ip))
    return list(dict.fromkeys(candidates))


class RedisBus:
    """Redis 기반 메시지 버스 — Gateway와 Brain Worker 간 통신."""

    def __init__(self, redis_url: Optional[str] = None):
        self._redis_url = redis_url or os.getenv("REDIS_URL", _default_redis_url())
        self._redis: Optional[aioredis.Redis] = None
        self._pubsub: Optional[aioredis.client.PubSub] = None
        self._pending: dict[str, asyncio.Future] = {}  # request_id → Future
        self._handlers: dict[str, Callable] = {}       # channel → handler
        self._listener_task: Optional[asyncio.Task] = None

    async def connect(self):
        """Redis 연결."""
        if self._redis is not None:
            try:
                await self._redis.ping()
                return self._redis
            except Exception as exc:
                logger.warning(f"[RedisBus] stale connection detected, reconnecting: {exc}")
                try:
                    await self._redis.aclose()
                except Exception:
                    pass
                self._redis = None

        last_error = None
        for candidate in _build_redis_url_candidates(self._redis_url):
            redis_client = aioredis.from_url(
                candidate,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5,
                socket_keepalive=True,
                health_check_interval=30,
                retry_on_timeout=True,
            )
            try:
                await redis_client.ping()
                self._redis = redis_client
                self._redis_url = candidate
                logger.info(f"[RedisBus] connected: {_redact_redis_url(candidate)}")
                return self._redis
            except Exception as exc:
                last_error = exc
                logger.warning(f"[RedisBus] connect failed: {_redact_redis_url(candidate)} ({exc})")
                try:
                    await redis_client.aclose()
                except Exception:
                    pass

        raise last_error or RuntimeError("Redis connection failed")

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
        session_id: str = "",
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
            "session_id": session_id or channel,
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

        Returns:
            dict: 큐 메시지 (실 요청 도착 시)
            None: 큐 비어있음 (timeout 만료, idle 상태 — 정상)
        """
        reconnect_delay = 1.0
        while True:
            redis = await self.connect()
            try:
                result = await redis.brpop(REQUEST_QUEUE, timeout=timeout)
                if result:
                    _, message = result
                    return json.loads(message)
                return None
            except RedisTimeoutError:
                # BRPOP socket-level read timeout = idle 상태 (큐 비어있음).
                # brain.worker._run_worker_loop 가 다음 cycle 에서 재호출하므로 None 반환이 정상.
                # traceback 로깅을 brain_err.log 에 남기지 않음 (2026-04-29 noise 정리).
                return None
            except RedisConnectionError as exc:
                logger.info(f"[RedisBus] dequeue reconnecting: {exc}")
                self._redis = None
                await asyncio.sleep(reconnect_delay)
                reconnect_delay = min(reconnect_delay * 2, 5.0)

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

        try:
            await redis.publish(RESULT_CHANNEL, message)
        except RedisConnectionError as exc:
            logger.warning(f"[RedisBus] publish reconnecting: {exc}")
            self._redis = None
            redis = await self.connect()
            await redis.publish(RESULT_CHANNEL, message)

        # 결과를 짧은 TTL로 저장 (late subscriber가 폴링으로 확인 가능)
        try:
            await redis.set(f"sora:result:{request_id}", message, ex=300)
        except RedisConnectionError as exc:
            logger.warning(f"[RedisBus] result cache reconnecting: {exc}")
            self._redis = None
            redis = await self.connect()
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
            try:
                cached = await redis.get(f"sora:result:{request_id}")
                if cached:
                    return json.loads(cached)
            except RedisConnectionError as exc:
                logger.warning(f"[RedisBus] result poll reconnecting: {exc}")
                self._redis = None
                redis = await self.connect()
                continue
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
        try:
            return await redis.llen(REQUEST_QUEUE)
        except RedisConnectionError as exc:
            logger.warning(f"[RedisBus] queue length reconnecting: {exc}")
            self._redis = None
            redis = await self.connect()
            return await redis.llen(REQUEST_QUEUE)

    async def publish_event(self, channel: str, data: dict):
        """임의 채널에 이벤트 발행."""
        redis = await self.connect()
        payload = json.dumps(data, ensure_ascii=False)
        try:
            await redis.publish(channel, payload)
        except RedisConnectionError as exc:
            logger.warning(f"[RedisBus] event publish reconnecting: {exc}")
            self._redis = None
            redis = await self.connect()
            await redis.publish(channel, payload)

    # ── 진행 이벤트 (Brain Worker → Gateway) ──

    async def publish_progress(self, request_id: str, data: dict) -> None:
        """실행 진행 상태를 request_id별 채널로 발행.

        Args:
            request_id: 요청 ID (sora:progress:{request_id} 채널에 발행)
            data: {"chat_id", "step", "message", "tool_name", "status", "ts"}
        """
        redis = await self.connect()
        channel = f"{PROGRESS_PREFIX}{request_id}"
        payload = json.dumps(data, ensure_ascii=False)
        try:
            await redis.publish(channel, payload)
        except RedisConnectionError as exc:
            logger.warning(f"[RedisBus] progress reconnecting: {exc}")
            self._redis = None
            redis = await self.connect()
            await redis.publish(channel, payload)
        logger.debug(f"[RedisBus] progress 발행: {request_id} — {data.get('message', '')[:40]}")

    async def subscribe_progress(self, request_id: str):
        """request_id의 진행 이벤트를 구독하는 async generator.

        사용 예:
            async for event in bus.subscribe_progress(request_id):
                print(event["message"])

        Note: asyncio.Task로 실행하고 취소 시 CancelledError가 전파됨.
        """
        redis = await self.connect()
        pubsub = redis.pubsub()
        channel = f"{PROGRESS_PREFIX}{request_id}"
        await pubsub.subscribe(channel)
        logger.debug(f"[RedisBus] progress 구독: {channel}")
        try:
            async for raw in pubsub.listen():
                if raw["type"] == "message":
                    yield json.loads(raw["data"])
        except asyncio.CancelledError:
            pass
        finally:
            try:
                await pubsub.unsubscribe(channel)
                await pubsub.aclose()
            except Exception:
                pass

    # ── 확인 응답 (neo_assistant_bot → Brain Worker) ──

    async def set_confirm_decision(self, request_id: str, decision: str, ttl: int = 60) -> None:
        """사용자 확인 응답 상태를 Redis에 저장."""
        normalized = decision.strip().lower()
        if normalized not in {"approved", "rejected"}:
            raise ValueError(f"Unsupported confirm decision: {decision}")

        redis = await self.connect()
        key = f"{CONFIRM_PREFIX}{request_id}"
        try:
            await redis.set(key, normalized, ex=ttl)
        except RedisConnectionError as exc:
            logger.warning(f"[RedisBus] confirm decision reconnecting: {exc}")
            self._redis = None
            redis = await self.connect()
            await redis.set(key, normalized, ex=ttl)

    async def set_confirm(self, request_id: str, approved: bool, ttl: int = 60) -> None:
        """사용자 확인 응답을 Redis에 저장."""
        await self.set_confirm_decision(
            request_id,
            "approved" if approved else "rejected",
            ttl=ttl,
        )

    async def wait_for_confirm_decision(self, request_id: str, timeout: float = 30.0) -> str:
        """사용자 확인 응답 상태를 대기.

        Returns:
            approved | rejected | timeout
        """
        redis = await self.connect()
        key = f"{CONFIRM_PREFIX}{request_id}"
        deadline = time.time() + timeout
        while time.time() < deadline:
            try:
                value = await redis.get(key)
                if value in {"approved", "rejected"}:
                    await redis.delete(key)
                    return value
            except RedisConnectionError as exc:
                logger.warning(f"[RedisBus] confirm poll reconnecting: {exc}")
                self._redis = None
                redis = await self.connect()
                continue
            await asyncio.sleep(0.5)
        logger.info(f"[RedisBus] 확인 타임아웃: {request_id}")
        return "timeout"

    async def wait_for_confirm(self, request_id: str, timeout: float = 30.0) -> bool:
        """사용자 확인 응답을 대기."""
        decision = await self.wait_for_confirm_decision(request_id, timeout=timeout)
        return decision == "approved"

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
