# -*- coding: utf-8 -*-
"""
LLM Client — 멀티 모델 라우팅 엔진

Gemini 3종(2.5-Flash / 2.5-Pro / 3.1-Pro) 지원.
Vertex AI 경유 호출 지원 (USE_VERTEX_AI=true 환경변수로 전환).
확장 가능한 프로바이더 추상화로 향후 Claude/GPT/Ollama 추가 가능.
"""
import os
import json
import time
import base64
import logging
import mimetypes
import urllib.request
import urllib.error
from abc import ABC, abstractmethod

logger = logging.getLogger("neo.llm")

# ── 환경 변수 ──────────────────────────────
GEMINI_API_KEY = os.environ.get("SORA_GEMINI_API_KEY") or os.environ.get("GEMINI_API_KEY", "")
USE_VERTEX_AI = os.environ.get("USE_VERTEX_AI", "").lower() in ("true", "1", "yes")
GCP_PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "neo-genesis-ee9d5")
GCP_REGION = os.environ.get("GCP_REGION", "us-central1")


# ══════════════════════════════════════════
# 프로바이더 추상화 (확장 포인트)
# ══════════════════════════════════════════
class LLMProvider(ABC):
    """LLM 프로바이더 인터페이스. 향후 Claude/GPT/Ollama 추가 시 이 클래스 상속."""

    @abstractmethod
    def generate(
        self,
        user_prompt: str,
        system_prompt: str = "",
        image_paths: list[str] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        ...


# ══════════════════════════════════════════
# Gemini 프로바이더
# ══════════════════════════════════════════
class GeminiProvider(LLMProvider):
    """Google Gemini API 프로바이더 (google.genai SDK)."""

    def __init__(self, model: str, api_key: str = "", use_vertex: bool | None = None):
        self.model = model
        self.api_key = api_key or GEMINI_API_KEY
        self.use_vertex = use_vertex if use_vertex is not None else USE_VERTEX_AI
        self._client = None

    def _get_client(self):
        if self._client is None:
            try:
                from google import genai
                if self.use_vertex:
                    self._client = genai.Client(
                        vertexai=True,
                        project=GCP_PROJECT_ID,
                        location=GCP_REGION,
                    )
                    logger.info(
                        f"Vertex AI 클라이언트 초기화: project={GCP_PROJECT_ID}, location={GCP_REGION}"
                    )
                else:
                    self._client = genai.Client(api_key=self.api_key)
            except Exception as e:
                logger.error(f"google.genai Client 초기화 실패: {e}")
        return self._client

    def generate(
        self,
        user_prompt: str,
        system_prompt: str = "",
        image_paths: list[str] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        if not self.use_vertex and not self.api_key:
            return "[API Error] No API Key provided."

        client = self._get_client()
        if not client:
            return "[API Error] SDK Client 초기화 실패."

        # 콘텐츠 구성
        contents = []
        if image_paths:
            for path in image_paths:
                try:
                    mime_type, _ = mimetypes.guess_type(path)
                    if not mime_type:
                        mime_type = "image/png"
                    with open(path, "rb") as f:
                        img_data = f.read()
                    from google.genai import types
                    contents.append(types.Part.from_bytes(data=img_data, mime_type=mime_type))
                except Exception as e:
                    logger.error(f"Image load failed: {path} - {e}")

        contents.append(user_prompt)

        # 생성 설정
        config_kwargs = {
            "max_output_tokens": max_tokens,
            "temperature": temperature,
        }
        if system_prompt:
            config_kwargs["system_instruction"] = system_prompt

        max_retries = 5
        for attempt in range(max_retries):
            try:
                response = client.models.generate_content(
                    model=self.model,
                    contents=contents,
                    config=config_kwargs,
                )
                return response.text.strip()
            except Exception as e:
                err_str = str(e).lower()
                if any(k in err_str for k in ("429", "500", "502", "503", "quota", "resource")) and attempt < max_retries - 1:
                    wait = 10 * (2 ** attempt)
                    logger.warning(
                        f"Gemini {self.model} error. Retry in {wait}s ({attempt+1}/{max_retries}): {str(e)[:100]}"
                    )
                    time.sleep(wait)
                    continue
                logger.error(f"Gemini request failed: {e}")
                return f"[Gemini Error] {str(e)[:100]}"

        return "[Gemini Error] Max retries exceeded."


# ══════════════════════════════════════════
# Claude 프로바이더 (Anthropic API)
# ══════════════════════════════════════════
ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")


class ClaudeProvider(LLMProvider):
    """Anthropic Claude API 프로바이더."""

    def __init__(self, model: str = "claude-sonnet-4-20250514", api_key: str = ""):
        self.model = model
        self.api_key = api_key or ANTHROPIC_API_KEY
        self._client = None

    def _get_client(self):
        if self._client is None:
            if not self.api_key:
                logger.warning("[Claude] ANTHROPIC_API_KEY 미설정")
                return None
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
                logger.info(f"[Claude] 클라이언트 초기화: {self.model}")
            except ImportError:
                logger.error("[Claude] anthropic 패키지 미설치: pip install anthropic")
                return None
            except Exception as e:
                logger.error(f"[Claude] 클라이언트 초기화 실패: {e}")
                return None
        return self._client

    def generate(
        self,
        user_prompt: str,
        system_prompt: str = "",
        image_paths: list[str] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        client = self._get_client()
        if not client:
            return "[Claude Error] API 키 미설정 또는 SDK 미설치"

        # 메시지 구성
        messages = []

        # 이미지 포함 시 멀티모달
        if image_paths:
            content = []
            for path in image_paths:
                try:
                    mime_type, _ = mimetypes.guess_type(path)
                    if not mime_type:
                        mime_type = "image/png"
                    with open(path, "rb") as f:
                        img_data = base64.b64encode(f.read()).decode()
                    content.append({
                        "type": "image",
                        "source": {"type": "base64", "media_type": mime_type, "data": img_data},
                    })
                except Exception as e:
                    logger.error(f"[Claude] Image load failed: {path} - {e}")
            content.append({"type": "text", "text": user_prompt})
            messages.append({"role": "user", "content": content})
        else:
            messages.append({"role": "user", "content": user_prompt})

        max_retries = 3
        for attempt in range(max_retries):
            try:
                response = client.messages.create(
                    model=self.model,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    system=system_prompt if system_prompt else "You are Sora, a helpful AI assistant. Respond in Korean.",
                    messages=messages,
                )
                # 텍스트 추출
                text_parts = [block.text for block in response.content if hasattr(block, "text")]
                return "\n".join(text_parts).strip()

            except Exception as e:
                err_str = str(e).lower()
                if any(k in err_str for k in ("429", "overloaded", "rate")) and attempt < max_retries - 1:
                    wait = 5 * (2 ** attempt)
                    logger.warning(f"[Claude] Rate limit, retry in {wait}s: {str(e)[:100]}")
                    time.sleep(wait)
                    continue
                logger.error(f"[Claude] Request failed: {e}")
                return f"[Claude Error] {str(e)[:200]}"

        return "[Claude Error] Max retries exceeded."


# ══════════════════════════════════════════
# Ollama 프로바이더 (로컬 폴백)
# ══════════════════════════════════════════
class OllamaProvider(LLMProvider):
    """로컬 Ollama 서버 프로바이더 (무료, 오프라인)."""

    def __init__(self, model: str = "qwen2.5:14b", base_url: str = "http://localhost:11434"):
        self.model = model
        self.base_url = base_url

    def generate(
        self,
        user_prompt: str,
        system_prompt: str = "",
        image_paths: list[str] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> str:
        try:
            payload = json.dumps({
                "model": self.model,
                "prompt": user_prompt,
                "system": system_prompt or "You are a helpful assistant. Respond in Korean.",
                "stream": False,
                "options": {"temperature": temperature, "num_predict": max_tokens},
            }).encode()

            req = urllib.request.Request(
                f"{self.base_url}/api/generate",
                data=payload,
                headers={"Content-Type": "application/json"},
            )
            resp = urllib.request.urlopen(req, timeout=60)
            data = json.loads(resp.read())
            return data.get("response", "").strip()
        except Exception as e:
            return f"[Ollama Error] {str(e)[:200]}"


# ══════════════════════════════════════════
# 모델 라우터
# ══════════════════════════════════════════
class ModelRouter:
    """태스크 특성에 따라 최적 Gemini 모델을 자동 선택.

    확장: PROVIDERS dict에 새 프로바이더 등록 시 Claude/GPT/Ollama 추가 가능.
    """

    # tier → (provider_type, model_name, description)
    MODELS = {
        "flash":   ("gemini",    "gemini-2.5-flash",            "빠르고 저렴 — 상태 점검, 단순 실행"),
        "think":   ("gemini",    "gemini-2.5-pro",              "코드 생성, 분석, 디버깅"),
        "god":     ("gemini",    "gemini-2.5-pro",              "최상급 Gemini 추론"),
        "claude":  ("anthropic", "claude-sonnet-4-20250514",    "Claude 정밀 추론, 코드 리뷰"),
        "opus":    ("anthropic", "claude-opus-4-20250514",      "Claude 최상급 (복잡한 아키텍처)"),
        "local":   ("ollama",    "qwen2.5:14b",                "로컬 오프라인 (무료)"),
    }

    # 폴백 체인: claude → think → flash, opus → claude → think
    FALLBACK_CHAIN = {
        "opus":   "claude",
        "claude": "think",
        "god":    "think",
        "think":  "flash",
    }

    def __init__(self):
        self._providers: dict[str, LLMProvider] = {}

    def _get_provider(self, tier: str) -> LLMProvider:
        """프로바이더 인스턴스를 캐싱하여 반환."""
        if tier not in self._providers:
            if tier not in self.MODELS:
                tier = "flash"
            provider_type, model_name, _ = self.MODELS[tier]
            if provider_type == "gemini":
                self._providers[tier] = GeminiProvider(model=model_name)
            elif provider_type == "anthropic":
                self._providers[tier] = ClaudeProvider(model=model_name)
            elif provider_type == "ollama":
                self._providers[tier] = OllamaProvider(model=model_name)
            else:
                logger.warning(f"Unknown provider: {provider_type}, fallback to Gemini Flash")
                self._providers[tier] = GeminiProvider(model="gemini-2.5-flash")
        return self._providers[tier]

    def _generate_with_fallback(
        self,
        tier: str,
        user_prompt: str,
        system_prompt: str = "",
        image_paths: list[str] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
    ) -> tuple[str, str]:
        """모델 호출 실패 시 폴백 체인을 따라 하위 티어로 자동 전환."""
        current_tier = tier
        tried = []
        while current_tier:
            tried.append(current_tier)
            provider = self._get_provider(current_tier)
            result = provider.generate(
                user_prompt=user_prompt,
                system_prompt=system_prompt,
                image_paths=image_paths,
                max_tokens=max_tokens,
                temperature=temperature,
            )
            # 에러 응답이 아니면 성공
            if not any(result.startswith(p) for p in ("[Gemini Error]", "[Claude Error]", "[Ollama Error]", "[API Error]", "[LLM Error]")):
                if current_tier != tier:
                    logger.warning(f"LLM 폴백: {tier} → {current_tier} (tried: {tried})")
                return result, current_tier
            # 폴백 시도
            fallback = self.FALLBACK_CHAIN.get(current_tier)
            if fallback:
                logger.warning(f"LLM {current_tier} 실패, {fallback}으로 폴백")
                current_tier = fallback
            else:
                return result, current_tier  # 더 이상 폴백 없음
        return "[LLM Error] All tiers exhausted.", tier

    def select_tier(self, context: dict | None = None) -> str:
        """컨텍스트 기반 최적 모델 티어 선택."""
        if not context:
            return "flash"

        task_type = context.get("task_type", "")
        step = context.get("step", 0)
        override = context.get("model_override")

        # 사용자 수동 오버라이드
        if override and override in self.MODELS:
            return override

        # Claude: 복잡한 추론, 아키텍처, 코드 리뷰, 전략
        if task_type in ("architecture", "code_review", "strategy", "evolutionary"):
            return "claude" if ANTHROPIC_API_KEY else "think"

        # Gemini Think: 코드 생성, 분석, 디버깅
        if task_type in ("code_gen", "debug", "analysis", "planning", "refactor"):
            return "think"

        # Gemini Flash: 단순 작업
        if task_type in ("status_check", "file_read", "simple", "monitoring", "tool_call"):
            return "flash"

        # 단계별 에스컬레이션
        if step < 5:
            return "flash"
        elif step < 10:
            return "think"
        return "claude" if ANTHROPIC_API_KEY else "god"

    def generate(
        self,
        user_prompt: str,
        system_prompt: str = "",
        image_paths: list[str] | None = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        context: dict | None = None,
        tier: str | None = None,
    ) -> tuple[str, str]:
        """최적 모델로 텍스트 생성 (폴백 체인 포함).

        Returns:
            (response_text, used_tier)
        """
        used_tier = tier or self.select_tier(context)
        logger.info(f"LLM [{used_tier}:{self.MODELS[used_tier][1]}] prompt={len(user_prompt)} chars")
        return self._generate_with_fallback(
            tier=used_tier,
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            image_paths=image_paths,
            max_tokens=max_tokens,
            temperature=temperature,
        )


# ══════════════════════════════════════════
# 하위 호환 — 기존 코드 깨지지 않도록
# ══════════════════════════════════════════
class GeminiClient:
    """기존 코드 호환 래퍼. 내부적으로 ModelRouter를 사용."""

    def __init__(self, api_key: str = None, model: str = None):
        self.api_key = api_key or GEMINI_API_KEY
        # 하위 호환: 기존 코드가 GeminiClient(model_name)으로 호출 시
        # model_name이 api_key 자리에 들어올 수 있음 → 감지 후 보정
        if self.api_key and ("gemini" in self.api_key or "models/" in self.api_key):
            model = self.api_key
            self.api_key = GEMINI_API_KEY
        self._router = ModelRouter()
        self._default_model = model  # 특정 모델 고정 요청 시 사용

    def generate(
        self,
        user_prompt: str,
        system_prompt: str = "",
        image_paths: list[str] = None,
        max_tokens: int = 4096,
        tier: str = "flash",
        context: dict = None,
    ) -> str:
        """기존 인터페이스와 호환 + 모델 선택 추가."""
        response, _ = self._router.generate(
            user_prompt=user_prompt,
            system_prompt=system_prompt,
            image_paths=image_paths,
            max_tokens=max_tokens,
            context=context,
            tier=tier,
        )
        return response
