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
# Layer 3: Embedding Cosine (KURE-v1)
# ============================================================
PERSONA_EMBEDDINGS_CACHE = PERSONAS_DIR / "dispatcher" / "persona_embeddings.json"
EMBEDDING_SERVICE_URLS = [
    "http://localhost:7702",
    "http://desktop-sol01:7702",
    "http://172.17.0.1:7702",
]
EMBEDDING_TIMEOUT_S = 2.0
COSINE_PRIMARY_CUTOFF = 0.5
COSINE_SECONDARY_CUTOFF = 0.6
EMBEDDING_CONFIDENCE_CAP = 0.92

# In-process cache (loaded once per process)
_embedding_cache: Optional[dict[str, Any]] = None


def _load_embedding_cache() -> Optional[dict[str, Any]]:
    """persona_embeddings.json 1회 로드 (in-process cache)."""
    global _embedding_cache
    if _embedding_cache is not None:
        return _embedding_cache
    if not PERSONA_EMBEDDINGS_CACHE.exists():
        return None
    try:
        _embedding_cache = json.loads(PERSONA_EMBEDDINGS_CACHE.read_text(encoding="utf-8"))
        return _embedding_cache
    except Exception:
        return None


def _embed_query(query: str) -> Optional[list[float]]:
    """KURE-v1 service 호출. graceful fail (None on error)."""
    try:
        import httpx  # type: ignore
    except ImportError:
        return None

    for url in EMBEDDING_SERVICE_URLS:
        try:
            r = httpx.post(
                f"{url.rstrip('/')}/embed",
                json={"texts": [query], "model": "kure-v1"},
                timeout=EMBEDDING_TIMEOUT_S,
            )
            if r.status_code != 200:
                continue
            embs = r.json().get("embeddings")
            if embs and len(embs) == 1 and isinstance(embs[0], list):
                return embs[0]
        except Exception:
            continue
    return None


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    """Normalized vectors → dot product = cosine. graceful for length mismatch."""
    if not a or not b or len(a) != len(b):
        return 0.0
    return sum(x * y for x, y in zip(a, b))


def match_embedding(query: str) -> Optional[dict[str, Any]]:
    """KURE-v1 cosine similarity vs 32 페르소나.

    Workflow:
      1. persona_embeddings.json 로드 (없으면 None → fallback)
      2. KURE-v1 service 호출 (미가용 → None → fallback)
      3. 32 페르소나 cosine similarity (normalized vectors)
      4. top-1 cosine >= 0.5 → primary, secondaries cosine >= 0.6 (top 3)
    """
    cache = _load_embedding_cache()
    if not cache:
        return None
    personas = cache.get("personas") or {}
    if not personas:
        return None

    query_emb = _embed_query(query)
    if not query_emb:
        return None

    similarities: list[tuple[str, float]] = []
    for persona_id, data in personas.items():
        emb = data.get("embedding")
        if not isinstance(emb, list):
            continue
        sim = _cosine_similarity(query_emb, emb)
        similarities.append((persona_id, sim))

    if not similarities:
        return None

    similarities.sort(key=lambda x: x[1], reverse=True)
    top_id, top_sim = similarities[0]

    if top_sim < COSINE_PRIMARY_CUTOFF:
        return None  # confidence too low → fallback layer

    secondaries = [
        pid for pid, sim in similarities[1:4] if sim >= COSINE_SECONDARY_CUTOFF
    ]

    framework = personas.get(top_id, {}).get("framework")

    return {
        "matched_layer": "L3_embedding",
        "persona_id": top_id,
        "secondary_personas": secondaries,
        "matched_pattern": f"cosine_similarity={top_sim:.4f}",
        "confidence": min(EMBEDDING_CONFIDENCE_CAP, top_sim),
        "ensemble_pattern": "single" if not secondaries else "cascade",
        "framework": framework,
    }


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

    # Layer 3: Embedding (KURE-v1 cosine)
    result = match_embedding(query)
    if result:
        result["g2_detected"] = detect_g2(query)
        if not result.get("framework"):
            result["framework"] = lookup_framework(result["persona_id"])
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

    # 2026-05-14: ontology v0.3 자동 ActionRun 박제 (fast-path, write_queue 우회)
    # 실패는 dispatcher 결과에 영향 없음 (best-effort)
    try:
        import sys as _sys
        from pathlib import Path as _Path
        _ar_path = _Path(__file__).resolve().parents[1] / "ontology"
        if _ar_path.exists():
            _sys.path.insert(0, str(_ar_path))
        from auto_record import record_action  # type: ignore
        primary = result.get("persona_id")
        secondary = result.get("secondary_personas") or []
        affected = []
        if primary:
            affected.append(f"neo://agent/{primary}")
        affected.extend([f"neo://agent/{s}" for s in secondary])
        record_action(
            kind="dispatcher_route",
            agent_id="neo://agent/claude-opus-4-7",
            affected=affected,
            meta={
                "matched_layer": result.get("matched_layer"),
                "matched_pattern": result.get("matched_pattern"),
                "ensemble_pattern": result.get("ensemble_pattern"),
                "g2_detected": result.get("g2_detected"),
                "query_hash": __import__("hashlib").sha256(query.encode("utf-8")).hexdigest()[:12],
            },
            confidence=float(result.get("confidence") or 0.0) if result.get("confidence") is not None else None,
            label=f"dispatch {result.get('matched_layer','?')} -> {primary}",
        )
    except Exception:
        pass  # auto-record failure is non-fatal
    return 0


if __name__ == "__main__":
    sys.exit(main())
