from __future__ import annotations

import argparse
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

PACKAGE_DIR = Path(__file__).resolve().parent
CONFIG_PATH = PACKAGE_DIR / "config" / "receipt_room_strategy.json"


@dataclass(frozen=True)
class Claim:
    text: str
    evidence_level: str = "fan_speculation"
    sensitivity: str = "none"
    source_ids: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class IssueCandidate:
    title: str
    summary: str
    entities: list[str] = field(default_factory=list)
    source_ids: list[str] = field(default_factory=list)
    evidence_items: list[dict[str, Any]] = field(default_factory=list)
    claims: list[Claim] = field(default_factory=list)
    trend_signals: dict[str, Any] = field(default_factory=dict)
    keywords: list[str] = field(default_factory=list)
    published_at: str | None = None


@dataclass(frozen=True)
class RiskAssessment:
    hard_blockers: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    labels: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class Scorecard:
    total: int
    dimensions: dict[str, int]
    weighted_total_before_risk: int
    risk_penalty: int
    decision_floor: int


def load_strategy(path: Path = CONFIG_PATH) -> dict[str, Any]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing Receipt Room strategy config: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid Receipt Room strategy config: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise RuntimeError(f"Receipt Room strategy config must be a JSON object: {path}")
    return raw


def candidate_from_dict(raw: dict[str, Any]) -> IssueCandidate:
    claims = []
    for row in raw.get("claims", []):
        if isinstance(row, dict):
            claims.append(
                Claim(
                    text=str(row.get("text", "")),
                    evidence_level=str(row.get("evidence_level", "fan_speculation")),
                    sensitivity=str(row.get("sensitivity", "none")),
                    source_ids=[str(item) for item in row.get("source_ids", []) if item],
                )
            )
    return IssueCandidate(
        title=str(raw.get("title", "")),
        summary=str(raw.get("summary", "")),
        entities=[str(item) for item in raw.get("entities", []) if item],
        source_ids=[str(item) for item in raw.get("source_ids", []) if item],
        evidence_items=[item for item in raw.get("evidence_items", []) if isinstance(item, dict)],
        claims=claims,
        trend_signals={str(k): v for k, v in raw.get("trend_signals", {}).items()},
        keywords=[str(item) for item in raw.get("keywords", []) if item],
        published_at=str(raw["published_at"]) if raw.get("published_at") else None,
    )


def _text_blob(candidate: IssueCandidate) -> str:
    parts = [
        candidate.title,
        candidate.summary,
        " ".join(candidate.entities),
        " ".join(candidate.keywords),
        " ".join(claim.text for claim in candidate.claims),
    ]
    return " ".join(parts).lower()


def _contains_any(text: str, terms: list[str]) -> bool:
    lowered = text.lower()
    return any(term.lower() in lowered for term in terms)


def _count_keyword_hits(text: str, terms: list[str]) -> int:
    lowered = text.lower()
    return sum(1 for term in terms if term.lower() in lowered)


def _clamp_score(value: float | int) -> int:
    return max(0, min(100, int(round(float(value)))))


def _source_rows(strategy: dict[str, Any], source_ids: list[str]) -> list[dict[str, Any]]:
    registry = strategy.get("source_registry", {})
    rows = []
    if isinstance(registry, dict):
        for source_id in source_ids:
            row = registry.get(source_id)
            if isinstance(row, dict):
                rows.append(row)
    return rows


def _score_sources(candidate: IssueCandidate, strategy: dict[str, Any]) -> int:
    source_ids = list(dict.fromkeys([*candidate.source_ids, *(sid for claim in candidate.claims for sid in claim.source_ids)]))
    rows = _source_rows(strategy, source_ids)
    if not rows:
        return 0
    reliability_values = [int(row.get("reliability", 0)) for row in rows]
    best = max(reliability_values)
    verified_sources = sum(1 for row in rows if row.get("counts_as_verified"))
    social_only = all(str(row.get("category", "")).endswith("signal") or row.get("category") == "rumor_signal" for row in rows)
    multi_source_bonus = min(12, max(0, len(rows) - 1) * 4)
    verified_bonus = min(14, verified_sources * 7)
    score = best + multi_source_bonus + verified_bonus
    if social_only:
        score = min(score, 42)
    return _clamp_score(score)


def _score_keyword_dimension(candidate: IssueCandidate, strategy: dict[str, Any], name: str, signal_name: str) -> int:
    explicit = candidate.trend_signals.get(signal_name)
    if isinstance(explicit, (int, float)):
        return _clamp_score(explicit)
    terms = strategy["issue_scoring"]["keyword_bonuses"].get(name, [])
    hits = _count_keyword_hits(_text_blob(candidate), [str(term) for term in terms])
    return _clamp_score(25 + hits * 14)


def _score_freshness(candidate: IssueCandidate) -> int:
    signal = candidate.trend_signals.get("freshness")
    if isinstance(signal, (int, float)):
        return _clamp_score(signal)
    if candidate.published_at:
        return 72
    return 45


def assess_risk(candidate: IssueCandidate, strategy: dict[str, Any] | None = None) -> RiskAssessment:
    strategy = strategy or load_strategy()
    policy = strategy["risk_policy"]
    text = _text_blob(candidate)
    blockers: list[str] = []
    warnings: list[str] = []
    labels = [str(policy["default_disclosure"])]

    if _contains_any(text, [str(term) for term in policy["hard_block_terms"]]):
        blockers.append("hard_blocked_ai_likeness_or_harmful_context")

    source_score = _score_sources(candidate, strategy)
    reliable_source_present = source_score >= int(strategy["issue_scoring"]["minimum_source_reliability"])
    allowed_sensitive_levels = {str(item) for item in policy["allowed_sensitive_evidence_levels"]}
    sensitive_terms = [str(term) for term in policy["sensitive_claim_terms"]]
    for claim in candidate.claims:
        claim_text = claim.text.lower()
        sensitivity = claim.sensitivity.lower()
        is_sensitive = sensitivity not in {"", "none", "ordinary"} or _contains_any(claim_text, sensitive_terms)
        if is_sensitive and (claim.evidence_level not in allowed_sensitive_levels or not reliable_source_present):
            blockers.append("unsupported_sensitive_claim")

    if candidate.entities:
        warnings.append("real_public_figures_must_be_symbolized")
    if any(claim.evidence_level in {"fan_speculation", "rumor"} for claim in candidate.claims):
        labels.append("fan speculation is visually separated from verified reporting")
        warnings.append("fan_speculation_boundary_required")
    if source_score < int(strategy["issue_scoring"]["minimum_source_reliability"]):
        warnings.append("weak_source_base")

    return RiskAssessment(
        hard_blockers=list(dict.fromkeys(blockers)),
        warnings=list(dict.fromkeys(warnings)),
        labels=list(dict.fromkeys(labels)),
    )


def score_issue(candidate: IssueCandidate, strategy: dict[str, Any] | None = None) -> Scorecard:
    strategy = strategy or load_strategy()
    scoring = strategy["issue_scoring"]
    dimensions = {
        "source_reliability": _score_sources(candidate, strategy),
        "trend_velocity": _clamp_score(candidate.trend_signals.get("trend_velocity", 0)),
        "fandom_conflict": _score_keyword_dimension(candidate, strategy, "fandom_conflict", "fandom_conflict"),
        "visual_drama": _score_keyword_dimension(candidate, strategy, "visual_drama", "visual_drama"),
        "microdrama_fit": _score_keyword_dimension(candidate, strategy, "microdrama_fit", "microdrama_fit"),
        "search_intent": _score_keyword_dimension(candidate, strategy, "search_intent", "search_intent"),
        "freshness": _score_freshness(candidate),
        "originality": _clamp_score(candidate.trend_signals.get("originality", 55)),
    }
    weights = {str(key): int(value) for key, value in scoring["weights"].items()}
    weight_total = sum(weights.values()) or 1
    weighted = sum(dimensions[name] * weights.get(name, 0) for name in dimensions) / weight_total

    risk = assess_risk(candidate, strategy)
    risk_penalty = 0
    if risk.hard_blockers:
        risk_penalty += 100
    if "weak_source_base" in risk.warnings:
        risk_penalty += 18
    if "fan_speculation_boundary_required" in risk.warnings:
        risk_penalty += 4

    total = _clamp_score(weighted - risk_penalty)
    return Scorecard(
        total=total,
        dimensions=dimensions,
        weighted_total_before_risk=_clamp_score(weighted),
        risk_penalty=risk_penalty,
        decision_floor=int(scoring["minimum_to_plan"]),
    )


def _select_episode_format(candidate: IssueCandidate, strategy: dict[str, Any]) -> tuple[str, dict[str, Any]]:
    text = _text_blob(candidate)
    best_key = "evidence_board"
    best_hits = -1
    for key, row in strategy["episode_formats"].items():
        terms = [str(term) for term in row.get("best_for", [])]
        hits = _count_keyword_hits(text, terms)
        if hits > best_hits:
            best_key = key
            best_hits = hits
    return best_key, strategy["episode_formats"][best_key]


def _reference_style_for_presentation(strategy: dict[str, Any], presentation: str) -> str:
    policy = strategy.get("character_archetypes", {}).get("reference_style_policy", {})
    if not isinstance(policy, dict):
        return ""
    global_rules = policy.get("global_rules") if isinstance(policy.get("global_rules"), list) else []
    style = str(policy.get(presentation) or policy.get("neutral_drama") or "")
    parts = [
        style,
        "Creative direction: " + "; ".join(str(item) for item in global_rules),
    ]
    return " ".join(part for part in parts if part.strip())


def _character_for_entity(entity: str, strategy: dict[str, Any]) -> dict[str, str]:
    lower = entity.lower()
    for row in strategy["character_archetypes"].get("by_keyword", []):
        if _contains_any(lower, [str(term) for term in row.get("terms", [])]):
            presentation = str(row.get("presentation", "neutral_drama"))
            return {
                "real_world_reference": entity,
                "screen_character": str(row["screen_character"]),
                "visual_rules": str(row["visual_rules"]),
                "presentation": presentation,
                "reference_style_rules": _reference_style_for_presentation(strategy, presentation),
            }
    default = strategy["character_archetypes"]["default"]
    presentation = str(default.get("presentation", "neutral_drama"))
    return {
        "real_world_reference": entity,
        "screen_character": str(default["screen_character"]),
        "visual_rules": str(default["visual_rules"]),
        "presentation": presentation,
        "reference_style_rules": _reference_style_for_presentation(strategy, presentation),
    }


def _characters(candidate: IssueCandidate, strategy: dict[str, Any]) -> list[dict[str, str]]:
    entities = candidate.entities[:4] or ["public figure"]
    deduped: list[dict[str, str]] = []
    seen: set[str] = set()
    for entity in entities:
        row = _character_for_entity(entity, strategy)
        key = row["screen_character"]
        if key not in seen:
            seen.add(key)
            deduped.append(row)
    return deduped


def _verified_fact(candidate: IssueCandidate) -> str:
    for claim in candidate.claims:
        if claim.evidence_level in {"confirmed", "official", "court_record", "reported", "observed"}:
            return claim.text
    if candidate.evidence_items:
        first = candidate.evidence_items[0]
        return str(first.get("text") or first.get("summary") or candidate.summary)
    return candidate.summary


def _fan_theory(candidate: IssueCandidate) -> str:
    for claim in candidate.claims:
        if claim.evidence_level in {"fan_speculation", "rumor"}:
            return claim.text
    return "the internet is building a theory from the public moment"


def _safe_visual_text(text: str, candidate: IssueCandidate) -> str:
    safe = str(text)
    for entity in candidate.entities:
        if entity:
            safe = re.sub(re.escape(entity), "the symbolic character", safe, flags=re.IGNORECASE)
    return safe


def _render_template(template: str, values: dict[str, str]) -> str:
    rendered = str(template)
    for key, value in values.items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def _shot_list(candidate: IssueCandidate, strategy: dict[str, Any], episode_format: dict[str, Any], characters: list[dict[str, str]]) -> list[dict[str, Any]]:
    main_character = characters[0]["screen_character"] if characters else "The Spotlight Figure"
    second_character = characters[1]["screen_character"] if len(characters) > 1 else "The Internet Jury"
    hook = str(episode_format["hook_template"])
    values = {
        "hook": hook,
        "main_character": main_character,
        "second_character": second_character,
        "verified_fact": _verified_fact(candidate),
        "fan_theory": _fan_theory(candidate),
        "drama_question": "what happened in public and what the internet invented around it",
        "comment_prompt": str(episode_format["comment_prompt"]),
    }
    shots = []
    for index, row in enumerate(strategy["shot_templates"], start=1):
        visual = _render_template(str(row["visual_template"]), values)
        caption = _render_template(str(row["caption_template"]), values)
        shots.append(
            {
                "shot_id": index,
                "beat": str(row["beat"]),
                "duration_sec": int(row["duration_sec"]),
                "caption": caption,
                "visual_prompt": _safe_visual_text(
                    f"{visual} Stylized luxury tabloid animation with fictionalized faces, symbolic branding, and paparazzi-drama staging.",
                    candidate,
                ),
                "motion": str(row["motion"]),
                "evidence_boundary": "verified" if row["beat"] == "verified_fact" else ("fan_speculation" if row["beat"] == "fan_theory" else "commentary"),
            }
        )
    return shots


def roast_gate(plan: dict[str, Any], strategy: dict[str, Any] | None = None) -> dict[str, Any]:
    strategy = strategy or load_strategy()
    gate = strategy["roast_gate"]
    blockers: list[str] = []
    notes: list[str] = []
    shots = plan.get("shot_list", [])
    total_duration = sum(int(shot.get("duration_sec", 0)) for shot in shots if isinstance(shot, dict))

    if len(shots) < int(gate["minimum_shots"]):
        blockers.append("shot_count_below_minimum")
    if total_duration < int(gate["minimum_total_duration_sec"]):
        blockers.append("duration_below_microdrama_floor")
    if gate.get("require_verified_fact") and not any(shot.get("evidence_boundary") == "verified" for shot in shots):
        blockers.append("verified_fact_missing")
    if gate.get("require_fan_speculation_boundary") and not any(
        shot.get("evidence_boundary") == "fan_speculation" for shot in shots
    ):
        blockers.append("fan_speculation_boundary_missing")
    if gate.get("require_motion_per_shot") and any(not str(shot.get("motion", "")).strip() for shot in shots):
        blockers.append("static_shot_found")
    if gate.get("reject_if_no_comment_conflict") and not plan.get("publish_package", {}).get("comment_prompt"):
        blockers.append("comment_conflict_missing")

    if gate.get("reject_if_prompt_contains_real_names"):
        entity_names = [str(entity).lower() for entity in plan.get("source_entities", []) if entity]
        prompts = " ".join(str(shot.get("visual_prompt", "")) for shot in shots).lower()
        leaked = [entity for entity in entity_names if entity and entity in prompts]
        if leaked:
            blockers.append("real_name_leaked_to_visual_prompt")
            notes.append("leaked_entities=" + ",".join(leaked))

    return {
        "passed": not blockers,
        "blockers": list(dict.fromkeys(blockers)),
        "notes": notes,
        "total_duration_sec": total_duration,
    }


def plan_episode(candidate: IssueCandidate, strategy: dict[str, Any] | None = None) -> dict[str, Any]:
    strategy = strategy or load_strategy()
    risk = assess_risk(candidate, strategy)
    scorecard = score_issue(candidate, strategy)
    format_key, episode_format = _select_episode_format(candidate, strategy)
    characters = _characters(candidate, strategy)
    shots = _shot_list(candidate, strategy, episode_format, characters)
    decision = "greenlight" if scorecard.total >= scorecard.decision_floor and not risk.hard_blockers else "revise"
    if risk.hard_blockers:
        decision = "blocked"

    plan: dict[str, Any] = {
        "brand": strategy["brand"]["name"],
        "episode_format": format_key,
        "episode_title": candidate.title,
        "hook": episode_format["hook_template"],
        "decision": decision,
        "source_entities": candidate.entities,
        "characters": characters,
        "verified_facts": [
            claim.text
            for claim in candidate.claims
            if claim.evidence_level in {"confirmed", "official", "court_record", "reported", "observed"}
        ],
        "speculation_boundaries": [
            claim.text for claim in candidate.claims if claim.evidence_level in {"fan_speculation", "rumor"}
        ],
        "scorecard": asdict(scorecard),
        "risk": asdict(risk),
        "story_beats": [
            "public moment",
            "confirmed receipt",
            "fan theory",
            "contradicting clue",
            "symbolic microdrama scene",
            "verdict meter",
            "comment jury"
        ],
        "shot_list": shots,
        "risk_labels": risk.labels,
        "publish_package": {
            "caption": f"{episode_format['hook_template']} Verified receipts first, fan theories second.",
            "hashtags": ["#ReceiptRoom1159", "#PopCulture", "#CelebrityTok", "#GossipExplained", "#AIGenerated"],
            "comment_prompt": episode_format["comment_prompt"],
        },
    }
    gate = roast_gate(plan, strategy)
    plan["roast_gate"] = gate
    if decision == "greenlight" and not gate["passed"]:
        plan["decision"] = "revise"
    return plan


def _demo_candidate() -> IssueCandidate:
    return candidate_from_dict(
        {
            "title": "The red carpet run-in that split the internet",
            "summary": "A public celebrity run-in became a fan debate because the body language looked awkward on a short clip.",
            "entities": ["Bad Bunny", "Kris Jenner"],
            "source_ids": ["just_jared", "vogue_trend_tracker", "tiktok_creative_center"],
            "keywords": ["red carpet", "met gala", "awkward", "ex", "fan theory", "receipt"],
            "trend_signals": {
                "trend_velocity": 86,
                "fandom_conflict": 88,
                "visual_drama": 92,
                "microdrama_fit": 85,
                "search_intent": 76,
                "freshness": 80,
                "originality": 70
            },
            "claims": [
                {
                    "text": "A public red carpet greeting was reported and circulated as a short clip.",
                    "evidence_level": "reported",
                    "sensitivity": "ordinary",
                    "source_ids": ["just_jared"]
                },
                {
                    "text": "Fans debated whether the greeting looked awkward because of past relationship context.",
                    "evidence_level": "fan_speculation",
                    "sensitivity": "ordinary",
                    "source_ids": ["tiktok_creative_center"]
                }
            ]
        }
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Plan a Receipt Room 11:59 symbolic gossip microdrama episode.")
    parser.add_argument("--candidate-json", type=Path, help="Path to a structured issue candidate JSON file.")
    parser.add_argument("--output", type=Path, help="Optional output path for the episode plan JSON.")
    parser.add_argument("--demo", action="store_true", help="Use a built-in demonstration candidate.")
    args = parser.parse_args(argv)

    if args.demo:
        candidate = _demo_candidate()
    elif args.candidate_json:
        candidate = candidate_from_dict(json.loads(args.candidate_json.read_text(encoding="utf-8")))
    else:
        parser.error("Use --demo or --candidate-json.")

    plan = plan_episode(candidate)
    payload = json.dumps(plan, ensure_ascii=False, indent=2)
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(payload + "\n", encoding="utf-8")
    else:
        print(payload)
    return 0 if plan["decision"] in {"greenlight", "revise"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
