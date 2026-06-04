# -*- coding: utf-8 -*-
"""tests/test_cache_helper.py — PT-1 Anthropic prompt cache helper 회귀 테스트.

owner G2 D1 ACCEPT (2026-05-10) 적용 검증:
    - 5 Tier S 페르소나만 cache_control 활성
    - 그 외 페르소나 / Tier A/B/C / 미존재 페르소나 모두 None
    - frontmatter caching_path != "sora_engine" 일 때 None
    - graceful fallback (yaml 실패 / 파일 미존재 / 비정상 입력)
"""

from __future__ import annotations

import sys
import unittest
from pathlib import Path
from unittest import mock

REPO_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(REPO_ROOT))

from src.core.llm.cache_helper import (  # noqa: E402
    ALLOWED_CACHED_PERSONAS,
    build_system_with_cache,
    clear_cache,
    get_cache_config,
)


class TestAllowedPersonas(unittest.TestCase):
    """5 Tier S 페르소나만 허용 — D1 ACCEPT 박제."""

    def setUp(self) -> None:
        clear_cache()  # 매 테스트마다 frontmatter cache 무효화

    def test_allowlist_exact_5_personas(self) -> None:
        """ALLOWED_CACHED_PERSONAS 는 정확히 5개 (D1 결정 박제)."""
        self.assertEqual(len(ALLOWED_CACHED_PERSONAS), 5)

    def test_allowlist_contains_required_5(self) -> None:
        """필수 5 페르소나가 모두 allowlist 에 있는지."""
        required = {
            "senior-backend-eng-korean",
            "senior-da-pm-korean",
            "quant-strategy-lead",
            "prompt-injection-auditor",
            "multi-agent-orchestrator",
        }
        self.assertEqual(ALLOWED_CACHED_PERSONAS, frozenset(required))

    def test_tier_s_korean_copywriter_excluded(self) -> None:
        """Tier S 8개 중 cache_strategy 가 sora_engine 미명시 페르소나는 None."""
        # korean-copywriter-tone 은 caching_path 명시 안 함 → None
        result = get_cache_config("korean-copywriter-tone")
        self.assertIsNone(result)

    def test_tier_s_korean_seo_excluded(self) -> None:
        """korean-seo-geo-strategist 는 caching_path 미명시 → None."""
        result = get_cache_config("korean-seo-geo-strategist")
        self.assertIsNone(result)

    def test_tier_s_sora_sre_ops_excluded(self) -> None:
        """sora-sre-ops 는 P0 이지만 caching_path 미명시 → None (D1 명시 5개만)."""
        result = get_cache_config("sora-sre-ops")
        self.assertIsNone(result)


class TestActivatedPersonas(unittest.TestCase):
    """5 Tier S 페르소나가 실제로 ephemeral cache 반환하는지."""

    def setUp(self) -> None:
        clear_cache()

    def test_senior_backend_eng_korean(self) -> None:
        """senior-backend-eng-korean → ephemeral cache (5m)."""
        result = get_cache_config("senior-backend-eng-korean")
        self.assertEqual(result, {"type": "ephemeral", "ttl": "5m"})

    def test_senior_da_pm_korean(self) -> None:
        """senior-da-pm-korean → ephemeral cache (5m)."""
        result = get_cache_config("senior-da-pm-korean")
        self.assertEqual(result, {"type": "ephemeral", "ttl": "5m"})

    def test_quant_strategy_lead(self) -> None:
        """quant-strategy-lead → ephemeral cache (1h, cron routine 적합)."""
        result = get_cache_config("quant-strategy-lead")
        self.assertEqual(result, {"type": "ephemeral", "ttl": "1h"})

    def test_prompt_injection_auditor(self) -> None:
        """prompt-injection-auditor → ephemeral cache (1h, G2 burst 대응)."""
        result = get_cache_config("prompt-injection-auditor")
        self.assertEqual(result, {"type": "ephemeral", "ttl": "1h"})

    def test_multi_agent_orchestrator(self) -> None:
        """multi-agent-orchestrator → ephemeral cache (5m)."""
        result = get_cache_config("multi-agent-orchestrator")
        self.assertEqual(result, {"type": "ephemeral", "ttl": "5m"})


class TestNonAllowedTiers(unittest.TestCase):
    """Tier A/B/C 페르소나는 D1 결정 명시: 모두 None."""

    def setUp(self) -> None:
        clear_cache()

    def test_tier_a_database_architect(self) -> None:
        """database-architect-postgres (Tier A) → None."""
        result = get_cache_config("database-architect-postgres")
        self.assertIsNone(result)

    def test_tier_a_api_design(self) -> None:
        """api-design-restful (Tier A) → None."""
        result = get_cache_config("api-design-restful")
        self.assertIsNone(result)

    def test_tier_b_devops(self) -> None:
        """devops-cicd-engineer (Tier B) → None."""
        result = get_cache_config("devops-cicd-engineer")
        self.assertIsNone(result)


class TestGracefulFallback(unittest.TestCase):
    """비정상 입력 → graceful None / 원본 string 반환."""

    def setUp(self) -> None:
        clear_cache()

    def test_unknown_persona(self) -> None:
        """존재하지 않는 페르소나 ID → None."""
        result = get_cache_config("nonexistent-persona-xyz")
        self.assertIsNone(result)

    def test_empty_persona_id(self) -> None:
        """빈 문자열 → None."""
        result = get_cache_config("")
        self.assertIsNone(result)

    def test_none_persona_id_via_build(self) -> None:
        """None persona_id → 원본 body 반환 (string)."""
        body = "You are a helpful assistant."
        result = build_system_with_cache(None, body)
        self.assertEqual(result, body)
        self.assertIsInstance(result, str)

    def test_invalid_persona_id_with_special_chars(self) -> None:
        """비정상 id (path traversal 시도) → None (안전 차단)."""
        result = get_cache_config("../../etc/passwd")
        self.assertIsNone(result)

    def test_non_string_body(self) -> None:
        """body 가 string 이 아닌 경우 → 빈 string fallback."""
        result = build_system_with_cache("senior-backend-eng-korean", 12345)  # type: ignore[arg-type]
        self.assertEqual(result, "")


class TestBuildSystemWithCache(unittest.TestCase):
    """build_system_with_cache 의 반환 형식 검증."""

    def setUp(self) -> None:
        clear_cache()

    def test_allowed_persona_returns_structured(self) -> None:
        """allowed persona → list[{type, text, cache_control}]."""
        body = "You are a senior Korean DA + PM."
        result = build_system_with_cache("senior-da-pm-korean", body)
        self.assertIsInstance(result, list)
        assert isinstance(result, list)  # type narrow
        self.assertEqual(len(result), 1)
        block = result[0]
        self.assertEqual(block["type"], "text")
        self.assertEqual(block["text"], body)
        # 2026-05-12: TTL 명시 (5m default for senior-backend-eng-korean)
        self.assertEqual(block["cache_control"], {"type": "ephemeral", "ttl": "5m"})

    def test_disallowed_persona_returns_string(self) -> None:
        """disallowed persona → 원본 string."""
        body = "You are a generic assistant."
        result = build_system_with_cache("korean-copywriter-tone", body)
        self.assertEqual(result, body)
        self.assertIsInstance(result, str)

    def test_unknown_persona_returns_string(self) -> None:
        """미존재 persona → 원본 string."""
        body = "Generic instruction."
        result = build_system_with_cache("totally-unknown", body)
        self.assertEqual(result, body)


class TestCacheBehavior(unittest.TestCase):
    """lru_cache 동작 확인 — frontmatter 가 한 번만 파싱되는지."""

    def setUp(self) -> None:
        clear_cache()

    def test_lru_cache_hits(self) -> None:
        """동일 persona 반복 호출 시 cache 적중 (frontmatter 1회 파싱)."""
        get_cache_config("senior-da-pm-korean")
        info_before = get_cache_config.cache_info()
        get_cache_config("senior-da-pm-korean")  # cache hit
        info_after = get_cache_config.cache_info()
        self.assertEqual(info_after.hits, info_before.hits + 1)

    def test_clear_cache_resets(self) -> None:
        """clear_cache() 호출 후 cache 비워졌는지."""
        get_cache_config("senior-da-pm-korean")
        clear_cache()
        info = get_cache_config.cache_info()
        self.assertEqual(info.currsize, 0)


class TestYamlFailureGuard(unittest.TestCase):
    """PyYAML 미설치 / yaml parse 실패 시 graceful None."""

    def setUp(self) -> None:
        clear_cache()

    def test_yaml_import_failure(self) -> None:
        """yaml import 실패 시 None (테스트 환경에서는 yaml 있으므로 mock)."""
        # 본 테스트는 _parse_frontmatter 가 ImportError 를 잡는지 검증
        from src.core.llm import cache_helper
        # 가짜 ImportError 강제: _parse_frontmatter 가 yaml import 시점 ImportError 잡음
        with mock.patch.dict("sys.modules", {"yaml": None}):
            clear_cache()  # 캐시 무효화 후 import 재시도되도록
            # 실제 yaml import 가 None 으로 강제되면 ImportError 발생
            # 단, sys.modules[yaml]=None 패턴이 PyYAML 의 import 동작에 따라 다를 수 있어
            # 직접 _parse_frontmatter 호출로 검증
            from src.core.llm.cache_helper import _parse_frontmatter, _find_persona_path
            persona_path = _find_persona_path("senior-da-pm-korean")
            self.assertIsNotNone(persona_path)
            # ImportError 발생 시 None 반환 확인
            result = _parse_frontmatter(persona_path)
            # yaml 가 None 으로 mock 됐을 때 ImportError → None
            self.assertIsNone(result)


if __name__ == "__main__":
    unittest.main(verbosity=2)
