# -*- coding: utf-8 -*-
"""
LocalLLMAdapter — OpenAI-compatible local LLM bridge for Sora.

역할:
    - LiteLLM Proxy (또는 llama-server / TabbyAPI) 를 OpenAI 호환 API 로 감싸
      SoraEngine 이 Gemini 대신 사용할 수 있는 통일 인터페이스를 제공한다.
    - Shadow 모드 → Fallback 승격 → Default 전환의 3단 스위치를
      LOCAL_FIRST_ENABLED 환경변수로 제어한다.
    - Gemini AutomaticFunctionCalling 과 OpenAI tools[] 사이의 포맷 차이를
      양방향 정규화한다.

설계 제약:
    - stateful chat session 이 아닌 stateless messages[] 기반
      (LiteLLM/llama-server 가 OpenAI 호환이므로)
    - SoraEngine 의 기존 `.text` 접근을 유지하기 위해 응답 래퍼를 제공
    - 실패는 조용히 None/False 를 반환하여 상위 폴백 경로를 깨뜨리지 않는다.

Feature flag:
    LOCAL_FIRST_ENABLED=true  → SoraEngine 이 로컬을 1차 시도
    LOCAL_FIRST_ENABLED=false → Gemini 유지, 이 어댑터는 shadow 로만 사용
"""
from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from dataclasses import dataclass, field
from typing import Any, AsyncIterator, Callable, Optional

# Qwen3 hybrid-thinking 블록 정규식. 비활성화하려면 STRIP_THINKING=false
_THINK_BLOCK_RE = re.compile(r"^\s*<think>[\s\S]*?</think>\s*", re.IGNORECASE)


def strip_thinking(text: str) -> str:
    """Qwen3 reasoning models wrap pre-answer reasoning in <think>...</think>.
    Sora UX 에서는 일반적으로 최종 답변만 원하므로 앞단 블록만 제거한다."""
    if not text:
        return text
    return _THINK_BLOCK_RE.sub("", text, count=1).lstrip()

try:
    from openai import AsyncOpenAI
    from openai.types.chat import ChatCompletion, ChatCompletionChunk
    _OPENAI_AVAILABLE = True
except ImportError:
    _OPENAI_AVAILABLE = False

logger = logging.getLogger("neo.sora.local_llm")


# ══════════════════════════════════════════════════
# 응답 래퍼 — Gemini response 인터페이스와 호환 유지
# ══════════════════════════════════════════════════

@dataclass
class LocalLLMResponse:
    """SoraEngine 이 `.text` / `.function_calls` 로 접근할 수 있는 통일 응답."""
    text: str = ""
    function_calls: list[dict] = field(default_factory=list)
    usage: dict = field(default_factory=dict)
    model: str = ""
    latency_ms: float = 0.0
    raw: Any = None

    def __bool__(self) -> bool:
        return bool(self.text) or bool(self.function_calls)


# ══════════════════════════════════════════════════
# 포맷 정규화 — Gemini ↔ OpenAI
# ══════════════════════════════════════════════════

def gemini_tools_to_openai(gemini_tools: Any) -> list[dict]:
    """
    Gemini `types.Tool` / `FunctionDeclaration` 리스트를
    OpenAI `tools=[{type:function, function:{name, description, parameters}}]` 로 변환.

    Gemini SDK의 Tool 객체는 `.function_declarations` 필드에 FunctionDeclaration 리스트를 갖는다.
    """
    if not gemini_tools:
        return []

    out: list[dict] = []
    for tool in gemini_tools:
        # Gemini Tool 객체
        fds = getattr(tool, "function_declarations", None)
        if fds is None and isinstance(tool, dict):
            fds = tool.get("function_declarations") or tool.get("functionDeclarations")
        if not fds:
            continue
        for fd in fds:
            name = getattr(fd, "name", None) or (fd.get("name") if isinstance(fd, dict) else None)
            desc = getattr(fd, "description", None) or (fd.get("description") if isinstance(fd, dict) else "")
            params = getattr(fd, "parameters", None) or (fd.get("parameters") if isinstance(fd, dict) else {})
            if hasattr(params, "to_dict"):
                try:
                    params = params.to_dict()
                except Exception:
                    params = {}
            if not name:
                continue
            out.append({
                "type": "function",
                "function": {
                    "name": name,
                    "description": desc or "",
                    "parameters": params or {"type": "object", "properties": {}},
                },
            })
    return out


def openai_response_to_local(resp: "ChatCompletion", *, latency_ms: float = 0.0) -> LocalLLMResponse:
    """OpenAI ChatCompletion → LocalLLMResponse.
    기본적으로 Qwen3 thinking 블록을 제거한다 (STRIP_THINKING=false 로 비활성 가능)."""
    try:
        choice = resp.choices[0] if resp.choices else None
        msg = choice.message if choice else None
        text = (msg.content or "") if msg else ""
        if os.getenv("STRIP_THINKING", "true").strip().lower() not in ("0", "false", "no", "off"):
            text = strip_thinking(text)

        fcalls: list[dict] = []
        tool_calls = getattr(msg, "tool_calls", None) if msg else None
        if tool_calls:
            for tc in tool_calls:
                fn = getattr(tc, "function", None)
                if not fn:
                    continue
                try:
                    args = json.loads(fn.arguments) if isinstance(fn.arguments, str) else fn.arguments
                except Exception:
                    args = {"_raw": fn.arguments}
                fcalls.append({
                    "id": getattr(tc, "id", ""),
                    "name": fn.name,
                    "args": args or {},
                })

        usage = {}
        if resp.usage:
            usage = {
                "prompt_tokens": resp.usage.prompt_tokens,
                "completion_tokens": resp.usage.completion_tokens,
                "total_tokens": resp.usage.total_tokens,
            }

        return LocalLLMResponse(
            text=text,
            function_calls=fcalls,
            usage=usage,
            model=resp.model or "",
            latency_ms=latency_ms,
            raw=resp,
        )
    except Exception as exc:
        logger.warning("openai_response_to_local: normalization failed: %s", exc)
        return LocalLLMResponse(text="", raw=resp, latency_ms=latency_ms)


# ══════════════════════════════════════════════════
# 어댑터 본체
# ══════════════════════════════════════════════════

class LocalLLMAdapter:
    """
    OpenAI 호환 로컬 LLM 어댑터.

    사용 예:
        adapter = LocalLLMAdapter()
        if await adapter.health_check():
            resp = await adapter.chat(
                messages=[{"role": "user", "content": "안녕"}],
                tools=[...],  # OpenAI format
            )
            print(resp.text)
    """

    def __init__(
        self,
        base_url: Optional[str] = None,
        api_key: Optional[str] = None,
        model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: int = 1,
    ):
        if not _OPENAI_AVAILABLE:
            raise RuntimeError(
                "openai SDK is not installed. `pip install openai>=2.0`"
            )

        self.base_url = (base_url or os.getenv("OPENAI_API_BASE")
                         or "http://127.0.0.1:4000/v1").rstrip("/")
        self.api_key = (api_key or os.getenv("OPENAI_API_KEY")
                        or os.getenv("LITELLM_MASTER_KEY")
                        or "sk-local-litellm-master")
        self.model = (model or os.getenv("LLM_PRIMARY_MODEL")
                      or "local-main")
        try:
            self.timeout = float(timeout if timeout is not None
                                 else os.getenv("LOCAL_LLM_TIMEOUT_SEC", "90"))
        except Exception:
            self.timeout = 90.0
        self.max_retries = max(0, int(max_retries))

        self._client = AsyncOpenAI(
            base_url=self.base_url,
            api_key=self.api_key,
            timeout=self.timeout,
            max_retries=self.max_retries,
        )
        logger.info(
            "[LocalLLMAdapter] init — base=%s model=%s timeout=%.0fs",
            self.base_url, self.model, self.timeout,
        )

    # ── 기능 플래그 ─────────────────────────────────
    @staticmethod
    def is_local_first_enabled() -> bool:
        v = os.getenv("LOCAL_FIRST_ENABLED", "false").strip().lower()
        return v in ("1", "true", "yes", "on")

    # ── 건강 체크 ─────────────────────────────────
    async def health_check(self) -> bool:
        """endpoint가 OpenAI-compat /v1/models 또는 /v1/chat 응답을 주는지 확인."""
        try:
            # LiteLLM / llama-server 공통: /v1/models
            models = await self._client.models.list()
            if models and getattr(models, "data", None) is not None:
                return True
        except Exception as exc:
            logger.debug("[LocalLLMAdapter] models.list failed: %s", exc)

        # fallback: 최소 1회 chat ping
        try:
            resp = await asyncio.wait_for(
                self._client.chat.completions.create(
                    model=self.model,
                    messages=[{"role": "user", "content": "ping"}],
                    max_tokens=1,
                ),
                timeout=min(10.0, self.timeout),
            )
            return bool(resp.choices)
        except Exception as exc:
            logger.warning("[LocalLLMAdapter] health_check failed: %s", exc)
            return False

    # ── 비 스트리밍 ─────────────────────────────────
    async def chat(
        self,
        messages: list[dict],
        *,
        tools: Optional[list[dict]] = None,
        tool_choice: Any = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        extra: Optional[dict] = None,
    ) -> LocalLLMResponse:
        """단일 턴 생성 — OpenAI 표준 ChatCompletion."""
        t0 = time.perf_counter()
        kwargs: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if tools:
            kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice
        if extra:
            kwargs.update(extra)

        try:
            resp: ChatCompletion = await self._client.chat.completions.create(**kwargs)
            dt = (time.perf_counter() - t0) * 1000.0
            out = openai_response_to_local(resp, latency_ms=dt)
            logger.info(
                "[LocalLLMAdapter] chat ok — model=%s tokens_in=%s tokens_out=%s latency=%.0fms tools=%d",
                out.model or kwargs["model"],
                out.usage.get("prompt_tokens"),
                out.usage.get("completion_tokens"),
                dt,
                len(out.function_calls),
            )
            return out
        except Exception as exc:
            dt = (time.perf_counter() - t0) * 1000.0
            err_str = str(exc).lower()
            # 2026-05-14 P0: SSH reverse tunnel reconnect 후 stale connection pool fix.
            # tunnel down → reconnect 시 기존 keep-alive socket dead → ConnectError 재발.
            # client 재생성 + 1회 retry 로 owner 가 14s Gemini fallback 안 겪게.
            if ("connection" in err_str or "econnreset" in err_str
                or "broken pipe" in err_str or "timed out" in err_str):
                logger.warning(
                    "[LocalLLMAdapter] connection-level err — recreating client + retry: %s",
                    str(exc)[:120],
                )
                try:
                    # 새 AsyncOpenAI client 로 stale pool 폐기
                    self._client = AsyncOpenAI(
                        base_url=self.base_url,
                        api_key=self.api_key,
                        timeout=self.timeout,
                        max_retries=self.max_retries,
                    )
                    t1 = time.perf_counter()
                    resp = await self._client.chat.completions.create(**kwargs)
                    dt2 = (time.perf_counter() - t1) * 1000.0
                    out = openai_response_to_local(resp, latency_ms=dt2)
                    logger.info(
                        "[LocalLLMAdapter] chat ok (retry after pool recreate) — model=%s latency=%.0fms",
                        out.model or kwargs["model"], dt2,
                    )
                    return out
                except Exception as exc2:
                    logger.warning(
                        "[LocalLLMAdapter] retry after pool recreate FAILED: %s", exc2,
                    )
                    raise
            logger.warning(
                "[LocalLLMAdapter] chat FAILED — model=%s latency=%.0fms err=%s",
                kwargs["model"], dt, exc,
            )
            raise

    # ── 스트리밍 ────────────────────────────────────
    async def chat_stream(
        self,
        messages: list[dict],
        *,
        tools: Optional[list[dict]] = None,
        model: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        on_chunk: Optional[Callable[[str], None]] = None,
    ) -> AsyncIterator[dict]:
        """
        SSE 스트림 생성 — 대시보드 v4 Phase 1 용.
        yield 포맷: {"type": "text"|"tool_call"|"done", "data": ...}
        """
        kwargs: dict[str, Any] = {
            "model": model or self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": True,
        }
        if max_tokens is not None:
            kwargs["max_tokens"] = max_tokens
        if tools:
            kwargs["tools"] = tools

        stream = await self._client.chat.completions.create(**kwargs)
        try:
            async for chunk in stream:  # ChatCompletionChunk
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta is None:
                    continue
                # 텍스트 조각
                if getattr(delta, "content", None):
                    piece = delta.content
                    if on_chunk:
                        try:
                            on_chunk(piece)
                        except Exception:
                            pass
                    yield {"type": "text", "data": piece}
                # 툴콜 조각 (OpenAI 는 tool_calls 를 점진 전송함)
                tcs = getattr(delta, "tool_calls", None)
                if tcs:
                    yield {"type": "tool_call_delta", "data": [tc.model_dump() for tc in tcs]}
            yield {"type": "done", "data": None}
        finally:
            try:
                await stream.close()
            except Exception:
                pass


# ══════════════════════════════════════════════════
# 싱글턴 접근자
# ══════════════════════════════════════════════════

_singleton: Optional[LocalLLMAdapter] = None


def get_local_llm_adapter() -> Optional[LocalLLMAdapter]:
    """
    전역 싱글턴 반환. OPENAI SDK 미설치 또는 초기화 실패시 None.
    SoraEngine 은 None 을 받으면 기존 Gemini 경로로 빠진다.
    """
    global _singleton
    if _singleton is not None:
        return _singleton
    if not _OPENAI_AVAILABLE:
        logger.warning("[LocalLLMAdapter] openai SDK not available — disabled")
        return None
    try:
        _singleton = LocalLLMAdapter()
        return _singleton
    except Exception as exc:
        logger.warning("[LocalLLMAdapter] init failed: %s", exc)
        return None


__all__ = [
    "LocalLLMAdapter",
    "LocalLLMResponse",
    "get_local_llm_adapter",
    "gemini_tools_to_openai",
    "openai_response_to_local",
]
