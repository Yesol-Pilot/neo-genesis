#!/usr/bin/env python3
"""
Persona Dispatcher v1.2
Layer 1 (slash) + Layer 2 (keyword regex) + Layer 3 (embedding stub) + Layer 4 (bandit stub)

작성: 2026-05-08, Strategy Lead Claude Opus 4.7 자율 진행
SSOT:
  - .agent/personas/_schema/persona_schema_v1.2.yaml
  - .agent/personas/_schema/framework_mapping_v1.2.md
  - .agent/personas/dispatcher/keyword_rules.yaml

사용:
  python scripts/persona/dispatcher.py --query "이번 주 ToolPick 방문자 분석해줘"
  python scripts/persona/dispatcher.py --slash "/persona quant-strategy-lead"
  python scripts/persona/dispatcher.py --list

출력 (JSON):
  {
    "persona_id": "senior-da-pm-korean",
    "matched_layer": "L2_keyword",
    "matched_pattern": "(?i)(GA4|PostHog|...)",
    "confidence": 0.85,
    "secondary_personas": [],
    "ensemble_pattern": "single",
    "g2_detected": false,
    "framework": "JTBD + AARRR + Pre-mortem"
  }
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Any, Optional

try:
    import yaml
except ImportError:
    yaml = None  # graceful fallback (라이트 모드)

# ============================================================
# Configuration
# ============================================================
REPO_ROOT = Path(__file__).resolve().parents[2]
PERSONAS_DIR = REPO_ROOT / ".agent" / "personas"
KEYWORD_RULES_PATH = PERSONAS_DIR / "dispatcher" / "keyword_rules.yaml"
SCHEMA_V1_2 = PERSONAS_DIR / "_schema" / "persona_schema_v1.2.yaml"

DEFAULT_FALLBACK_PERSONA = "senior-backend-eng-korean"


# ============================================================
# Layer 1: Slash command
# ============================================================
def parse_slash_command(query: str) -> Optional[dict[str, Any]]:
    """
    /persona <name>            → 직접 호출
    /personas list             → 32 카탈로그
    /personas tier=S           → tier 필터링
    /ensemble p1 p2 [p3]       → 강제 ensemble
    /critic p1                 → 강제 critic via neo-reviewer
    /devils-advocate p1        → 강제 반대 입장 invoke
    """
    query = query.strip()
    if not query.startswith("/"):
        return None

    parts = query.split(maxsplit=2)
    cmd = parts[0].lower()

    if cmd == "/persona" and len(parts) >= 2:
        return {
            "matched_layer": "L1_slash",
            "persona_id": parts[1],
            "confidence": 1.0,
            "ensemble_pattern": "single",
        }

    if cmd == "/personas":
        sub = parts[1] if len(parts) >= 2 else "list"
        return {
            "matched_layer": "L1_slash_meta",
            "persona_id": None,
            "meta_action": sub,
        }

    if cmd == "/ensemble" and len(parts) >= 2:
        rest = parts[1] + (" " + parts[2] if len(parts) > 2 else "")
        personas = rest.split()
        return {
            "matched_layer": "L1_slash",
            "persona_id": personas[0],
            "secondary_personas": personas[1:] if len(personas) > 1 else [],
            "ensemble_pattern": "ensemble_forced",
            "confidence": 1.0,
        }

    if cmd == "/critic" and len(parts) >= 2:
        return {
            "matched_layer": "L1_slash",
            "persona_id": parts[1],
            "secondary_personas": ["neo-reviewer"],
            "ensemble_pattern": "critic",
            "confidence": 1.0,
        }

    if cmd == "/devils-advocate" and len(parts) >= 2:
        return {
            "matched_layer": "L1_slash",
            "persona_id": parts[1],
            "ensemble_pattern": "devils_advocate",
            "confidence": 1.0,
        }

    return None


# ============================================================
# Layer 2: Keyword Regex
# ============================================================
def load_keyword_rules() -> list[dict[str, Any]]:
    """Load .agent/personas/dispatcher/keyword_rules.yaml"""
    if not yaml or not KEYWORD_RULES_PATH.exists():
        return []
    try:
        data = yaml.safe_load(KEYWORD_RULES_PATH.read_text(encoding="utf-8"))
        return data.get("rules", []) if data else []
    except Exception:
        return []


def match_keyword(query: str) -> Optional[dict[str, Any]]:
    """
    Layer 2: keyword regex 매칭 (priority desc 정렬).
    First match wins. Multi-domain detection (3+ matches) → multi-agent-orchestrator.
    """
    rules = load_keyword_rules()
    if not rules:
        return None

    rules_sorted = sorted(rules, key=lambda r: r.get("priority", 0), reverse=True)

    matches: list[dict[str, Any]] = []
    for rule in rules_sorted:
        pattern = rule.get("pattern", "")
        if not pattern:
            continue
        try:
            if re.search(pattern, query):
                matches.append({
                    "persona_id": rule["primary"],
                    "secondary_personas": rule.get("secondary", []),
                    "matched_pattern": pattern,
                    "priority": rule.get("priority", 0),
                    "confidence": min(0.85, rule.get("priority", 0) / 100.0),
                })
        except re.error:
            continue

    if not matches:
        return None

    # Multi-domain detection: 3+ distinct personas → multi-agent-orchestrator
    distinct_personas = {m["persona_id"] for m in matches}
    if len(distinct_personas) >= 3:
        return {
            "matched_layer": "L2_keyword_multidomain",
            "persona_id": "multi-agent-orchestrator",
            "secondary_personas": list(distinct_personas)[:5],
            "matched_pattern": "multi_domain_3plus",
            "confidence": 0.9,
            "ensemble_pattern": "multi_agent_required",
        }

    # Single best match
    best = matches[0]
    return {
        "matched_layer": "L2_keyword",
        "persona_id": best["persona_id"],
        "secondary_personas": best["secondary_personas"],
        "matched_pattern": best["matched_pattern"],
        "confidence": best["confidence"],
        "ensemble_pattern": "single" if not best["secondary_personas"] else "cascade",
    }


# ============================================================
# Layer 3: Embedding Cosine (stub, Phase B 본격 구현)
# ============================================================
def match_embedding(query: str) -> Optional[dict[str, Any]]:
    """KURE-v1 cosine similarity vs 32 페르소나 (Phase B)"""
    # TODO Phase B: KURE-v1 embedding via embedding_service:7702
    return None


# ============================================================
# Layer 4: Bandit Thompson Sampling (Phase D)
# ============================================================
# TODO Phase D D11: bandit arms (persona × model × cache_strategy)


# ============================================================
# G2 Keyword Detection (CONSTITUTION Article 0)
# ============================================================
G2_PATTERNS = [
    r"(?i)(1000만원|입금|송금|capital transfer|withdraw)",
    r"(?i)Tier 1.*(영문 매체|PR)|보도자료",
    r"(?i)production deploy|force push|git push --force",
    r"(?i)credential 회전|토큰 회전|secret rotation",
    r"(?i)DROP TABLE|TRUNCATE|rm -rf",
    r"(?i)LIVE 모드|LIVE mode 전환|paper.*live",
    r"(?i)merge.*main|머지.*main",
]


def detect_g2(query: str) -> bool:
    """G2 액션 키워드 감지 (owner 직접 승인 필요)"""
    return any(re.search(p, query) for p in G2_PATTERNS)


# ============================================================
# Framework lookup (v1.2)
# ============================================================
def lookup_framework(persona_id: str) -> Optional[str]:
    """v1.2 schema 의 framework_mapping 에서 primary_framework 조회"""
    if not yaml or not SCHEMA_V1_2.exists():
        return None
    try:
        data = yaml.safe_load(SCHEMA_V1_2.read_text(encoding="utf-8"))
        if not data:
            return None
        mapping = data.get("framework_mapping", {})
        for tier_name, tier_personas in mapping.items():
            if isinstance(tier_personas, dict) and persona_id in tier_personas:
                return tier_personas[persona_id].get("primary_framework")
    except Exception:
        return None
    return None


# ============================================================
# Main Dispatcher
# ============================================================
def dispatch(query: str) -> dict[str, Any]:
    """4-tier hybrid dispatcher with v1.2 framework attribution"""
    # Layer 1: Slash
    result = parse_slash_command(query)
    if result:
        result["g2_detected"] = detect_g2(query)
        if result.get("persona_id"):
            result["framework"] = lookup_framework(result["persona_id"])
        return result

    # Layer 2: Keyword
    result = match_keyword(query)
    if result:
        result["g2_detected"] = detect_g2(query)
        result["framework"] = lookup_framework(result["persona_id"])
        return result

    # Layer 3: Embedding (stub)
    result = match_embedding(query)
    if result:
        result["g2_detected"] = detect_g2(query)
        return result

    # Fallback
    return {
        "matched_layer": "fallback",
        "persona_id": DEFAULT_FALLBACK_PERSONA,
        "confidence": 0.0,
        "ensemble_pattern": "single",
        "reason": "no keyword match, embedding stub returned None",
        "g2_detected": detect_g2(query),
        "framework": lookup_framework(DEFAULT_FALLBACK_PERSONA),
    }


# ============================================================
# Persona List (CLI helper)
# ============================================================
def list_personas() -> list[str]:
    """32 페르소나 카탈로그 list (filename 기반)"""
    personas: list[str] = []
    for tier in ["tier-s", "tier-a", "tier-b", "tier-c"]:
        tier_dir = PERSONAS_DIR / tier
        if tier_dir.exists():
            for p in sorted(tier_dir.glob("*.md")):
                personas.append(f"{tier}/{p.stem}")
    return personas


# ============================================================
# CLI
# ============================================================
def main() -> int:
    parser = argparse.ArgumentParser(description="Persona Dispatcher v1.2")
    parser.add_argument("--query", help="User query for dispatch")
    parser.add_argument("--slash", help="Slash command (e.g., '/persona quant-strategy-lead')")
    parser.add_argument("--list", action="store_true", help="List all personas")
    args = parser.parse_args()

    if args.list:
        for p in list_personas():
            print(p)
        return 0

    query = args.query or args.slash
    if not query:
        parser.print_help()
        return 1

    result = dispatch(query)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
