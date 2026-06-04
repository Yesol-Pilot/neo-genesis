# -*- coding: utf-8 -*-
"""Persona-aware Anthropic prompt cache helper (PT-1, D1 ACCEPT 2026-05-10).

owner G2 결정 (Strategy Lead 자율 ACCEPT, 2026-05-10):
    - Sora engine path 한정 cache_control 적용
    - 5 Tier S 페르소나만 활성 (caching_path: "sora_engine")
    - 추정 절감 $32/월 (Realistic, persona_caching_cost_analysis_v1.md 근거)

대상 페르소나 5건:
    1. senior-da-pm-korean (5m TTL)
    2. multi-agent-orchestrator (5m TTL, opus)
    3. quant-strategy-lead (1h TTL, opus, daily cron 정합)
    4. prompt-injection-auditor (1h TTL, opus, G2 burst 정합)
    5. senior-backend-eng-korean (5m TTL)

설계 원칙:
    - Allowlist 기반 — 알려진 5 페르소나만 cache 활성, 그 외 None
    - frontmatter `cache_strategy.caching_path == "sora_engine"` 이중 검증
    - 페르소나 미발견 / yaml 실패 시 graceful None (기존 string system 유지)
    - Anthropic ephemeral cache (5m default) 사용, 1h cache 는 beta header 필요해 본 helper 미적용
    - 모든 외부 의존성은 lazy import (pyyaml 미설치 환경 안전)
"""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Union

logger = logging.getLogger("neo.llm.cache_helper")

# ── 경로 설정 ─────────────────────────────────────────
# src/core/llm/cache_helper.py → repo root = parents[3]
_THIS_FILE = Path(__file__).resolve()
PERSONAS_DIR = _THIS_FILE.parents[3] / ".agent" / "personas"

# ── Allowlist (D1 ACCEPT, owner G2) ──────────────────
# 본 5건만 cache_control 적용. 다른 페르소나가 frontmatter 에 caching_path 를
# 추가해도 명시적 ALLOWLIST 추가 없이는 활성화 안 됨 (안전 가드).
ALLOWED_CACHED_PERSONAS = frozenset({
    "senior-backend-eng-korean",
    "senior-da-pm-korean",
    "quant-strategy-lead",
    "prompt-injection-auditor",
    "multi-agent-orchestrator",
})


def _find_persona_path(persona_id: str) -> Optional[Path]:
    """4 tier 디렉토리를 순회해 persona 파일 경로를 찾는다."""
    if not persona_id or not persona_id.replace("-", "").replace("_", "").isalnum():
        return None  # 안전: 비정상 id 차단
    for tier in ("tier-s", "tier-a", "tier-b", "tier-c"):
        candidate = PERSONAS_DIR / tier / f"{persona_id}.md"
        if candidate.exists():
            return candidate
    return None


def _parse_frontmatter(persona_path: Path) -> Optional[dict[str, Any]]:
    """페르소나 .md 파일에서 YAML frontmatter 만 추출."""
    try:
        import yaml  # lazy import — yaml 미설치 환경에서도 import 시점 충돌 X
    except ImportError:  # pragma: no cover
        logger.debug("[cache_helper] PyYAML 미설치 → cache disabled")
        return None

    try:
        text = persona_path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError) as exc:
        logger.debug("[cache_helper] persona read failed (%s): %s", persona_path, exc)
        return None

    if not text.startswith("---\n") and not text.startswith("---\r\n"):
        return None
    # 두 번째 `\n---\n` 위치 검색
    end = text.find("\n---\n", 4)
    if end < 0:
        end = text.find("\n---\r\n", 4)
    if end < 0:
        return None

    fm_text = text[4:end]
    try:
        loaded = yaml.safe_load(fm_text)
    except yaml.YAMLError as exc:
        logger.debug("[cache_helper] yaml parse failed (%s): %s", persona_path, exc)
        return None

    if not isinstance(loaded, dict):
        return None
    return loaded


@lru_cache(maxsize=64)
def get_cache_config(persona_id: str) -> Optional[dict[str, str]]:
    """페르소나 frontmatter 의 cache_strategy 를 검사하고 cache_control dict 반환.

    Returns:
        {"type": "ephemeral"} — 5min cache 활성 시 (Anthropic 표준)
        None — 다음 중 하나라도 해당 시:
            - persona_id 가 ALLOWED_CACHED_PERSONAS 에 없음 (D1 결정 한정)
            - 페르소나 파일 미발견
            - frontmatter 파싱 실패
            - cache_strategy.caching_path != "sora_engine"
            - PyYAML 미설치
    """
    if not persona_id:
        return None

    # 1. Allowlist 게이트 — D1 결정 박제
    if persona_id not in ALLOWED_CACHED_PERSONAS:
        return None

    # 2. 파일 존재 확인
    persona_path = _find_persona_path(persona_id)
    if persona_path is None:
        logger.debug("[cache_helper] persona file not found: %s", persona_id)
        return None

    # 3. frontmatter 파싱
    frontmatter = _parse_frontmatter(persona_path)
    if frontmatter is None:
        return None

    # 4. cache_strategy.caching_path 검증
    cache_strategy = frontmatter.get("cache_strategy") or {}
    if not isinstance(cache_strategy, dict):
        return None
    if cache_strategy.get("caching_path") != "sora_engine":
        logger.debug(
            "[cache_helper] persona %s 의 caching_path 가 sora_engine 아님 → cache disabled",
            persona_id,
        )
        return None

    # 5. TTL 결정 (2026-05-12 P0-3: explicit TTL — Anthropic default 5m silent change 대응)
    # 페르소나 frontmatter cache_strategy.ttl 우선, 없으면 5m default
    # 1h cache 는 client 측에서 `anthropic-beta: extended-cache-ttl-2025-04-11` header 필요
    ttl_value = cache_strategy.get("ttl", "5m")
    if ttl_value == "1h":
        # 1h ephemeral cache (beta 헤더 필요, client 책임)
        return {"type": "ephemeral", "ttl": "1h"}
    # 5m default (Anthropic 표준, beta 헤더 불필요)
    return {"type": "ephemeral", "ttl": "5m"}


def build_system_with_cache(
    persona_id: Optional[str],
    persona_body: str,
) -> Union[str, list[dict[str, Any]]]:
    """cache_control 적용 가능 시 Anthropic structured system, 아니면 string 그대로.

    Args:
        persona_id: 페르소나 식별자 (None / 빈 문자열 시 cache 안 함)
        persona_body: system prompt 본문 텍스트

    Returns:
        - cache_control 적용: [{"type": "text", "text": ..., "cache_control": {...}}]
        - 그 외: persona_body 원본 string (기존 호출 호환)

    예외:
        본 함수는 예외를 던지지 않음 — 모든 실패는 graceful fallback 으로
        원본 string 반환 (기존 sora_engine 호출 break 방지).
    """
    if not persona_id or not isinstance(persona_body, str):
        return persona_body if isinstance(persona_body, str) else ""

    try:
        cache_cfg = get_cache_config(persona_id)
    except Exception as exc:  # pragma: no cover — 방어적 fallback
        logger.warning("[cache_helper] get_cache_config 실패: %s", exc)
        return persona_body

    if cache_cfg:
        return [
            {
                "type": "text",
                "text": persona_body,
                "cache_control": cache_cfg,
            }
        ]
    return persona_body


def clear_cache() -> None:
    """페르소나 frontmatter 캐시를 강제 무효화 (테스트 / 페르소나 hot-reload 용)."""
    get_cache_config.cache_clear()


__all__ = [
    "ALLOWED_CACHED_PERSONAS",
    "build_system_with_cache",
    "clear_cache",
    "get_cache_config",
]
