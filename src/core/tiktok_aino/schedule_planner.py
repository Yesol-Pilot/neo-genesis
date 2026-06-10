"""Build a rolling AiNo TikTok publishing plan.

This module plans local generation and TikTok Studio scheduling targets only.
It does not upload, schedule, or publish anything on TikTok.
"""

from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import re
import sys
from dataclasses import asdict
from pathlib import Path
from zoneinfo import ZoneInfo

from src.core.tiktok_aino import pipeline


DEFAULT_FORMAT_SEQUENCE = ["growth_short", "reward_deep", "debate_followup"]
DEFAULT_TIMEZONE = "Asia/Seoul"
DEFAULT_PERFORMANCE_REPORT_DIR = pipeline.DEFAULT_PERFORMANCE_REPORT_DIR
UNSUITABLE_TOPIC_TERMS = ("살해", "피살", "범행", "성폭력", "강간", "자살", "아동학대")
DIRECT_ELECTION_ACTION_TERMS = (
    "투표하자",
    "투표하세요",
    "투표합시다",
    "투표해야",
    "표로심판",
    "표로응징",
    "찍자",
    "뽑자",
    "지지하자",
    "심판하자",
)
PUBLIC_ACCOUNTABILITY_TERMS = (
    "특검",
    "수사",
    "검찰",
    "법원",
    "판결",
    "증언",
    "국회",
    "기록",
    "의혹",
    "책임",
    "조사",
    "공직선거법",
    "근거",
    "규명",
    "허점",
    "공세",
    "음모론",
    "프레임",
    "관리",
    "공식",
)
GENERIC_DUPLICATE_TERMS = {
    "이슈",
    "지금",
    "기록",
    "다시",
    "보기",
    "정치",
    "쟁점",
    "논란",
    "사안",
    "핵심",
    "전말",
    "근거",
    "책임",
    "기준",
    "무엇",
    "왜",
    "선고",
    "구형",
}
SUPPORT_GENERIC_TERMS = {
    *GENERIC_DUPLICATE_TERMS,
    "대통령",
    "전대통령",
    "전 대통령",
    "정부",
    "여당",
    "야당",
    "정당",
    "민주당",
    "더불어민주당",
    "국민의힘",
    "이재명",
    "국회",
    "정치공세",
    "공방",
    "공세",
    "의혹",
    "선거",
}
WEAK_SHARED_SUPPORT_TERMS = {
    "특검",
    "책임",
    "논란",
    "공방",
    "공세",
    "의혹",
    "정부",
    "국회",
    "검찰",
}


def _slot_datetime(day: dt.date, upload_slot: str, timezone: ZoneInfo) -> dt.datetime:
    hour_text, minute_text = upload_slot.split(":", 1)
    return dt.datetime(
        day.year,
        day.month,
        day.day,
        int(hour_text),
        int(minute_text),
        tzinfo=timezone,
    )


def _candidate_items(discovery: dict[str, object]) -> list[dict[str, object]]:
    rows = discovery.get("candidates", [])
    return [row for row in rows if isinstance(row, dict)]


def _latest_performance_report() -> Path | None:
    return pipeline._latest_performance_feedback_source()


def _load_performance_feedback(report_path: Path | None) -> dict[str, object]:
    return pipeline.load_performance_feedback(report_path or _latest_performance_report())


def _performance_report_exclusions(report_path: Path | None) -> list[str]:
    if not report_path or not report_path.exists():
        return []
    try:
        payload = json.loads(report_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    exclusions: list[str] = []
    for key in ("scheduled_rows", "top_rows"):
        rows = payload.get(key, [])
        if not isinstance(rows, list):
            continue
        for row in rows:
            if not isinstance(row, dict):
                continue
            title = str(row.get("title", "")).strip()
            if not title:
                continue
            try:
                views = float(row.get("views", 0) or 0)
                likes = float(row.get("likes", 0) or 0)
                comments = float(row.get("comments", 0) or 0)
            except (TypeError, ValueError):
                views, likes, comments = 0.0, 0.0, 0.0
            if key == "scheduled_rows" or (0 < views < 500 and likes + comments <= 5):
                exclusions.append(title)
    return exclusions


def _resolve_repo_path(value: str | Path) -> Path:
    path = Path(value)
    return path if path.is_absolute() else pipeline.REPO_DIR / path


def _load_ha_strategy() -> dict[str, object]:
    payload = pipeline._load_json(pipeline.CONFIG_DIR / "ha_strategy.json")
    return payload if isinstance(payload, dict) else {}


def _recent_queue_titles() -> list[str]:
    strategy = _load_ha_strategy()
    control_tower = strategy.get("control_tower", {})
    state_dir_raw = strategy.get("local_state_dir") or (
        control_tower.get("state_dir") if isinstance(control_tower, dict) else None
    )
    if not state_dir_raw:
        return []
    jobs_path = _resolve_repo_path(str(state_dir_raw)) / "jobs.json"
    try:
        jobs_doc = json.loads(jobs_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []
    duplicate_guard = strategy.get("duplicate_guard", {})
    active_statuses = duplicate_guard.get("active_statuses", []) if isinstance(duplicate_guard, dict) else []
    statuses = {str(status) for status in active_statuses if str(status).strip()}
    if not statuses:
        statuses = {"planned", "generated", "upload_prepared", "scheduled", "published", "monitoring"}
    titles: list[str] = []
    jobs = jobs_doc.get("jobs", {})
    if not isinstance(jobs, dict):
        return titles
    for job in jobs.values():
        if not isinstance(job, dict) or str(job.get("status", "")) not in statuses:
            continue
        for key in ("topic", "post_title"):
            value = str(job.get(key, "")).strip()
            if value:
                titles.append(value)
        payload = job.get("payload", {})
        if isinstance(payload, dict):
            for key in ("topic", "post_title", "title"):
                value = str(payload.get(key, "")).strip()
                if value:
                    titles.append(value)
    return list(dict.fromkeys(titles))


def _normalized_topic_text(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text).casefold()


def _stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _duplicate_anchor_terms() -> list[str]:
    terms = pipeline.HOT_TOPIC_STRATEGY.get("duplicate_anchor_terms", [])
    if not isinstance(terms, list):
        return []
    return [str(term) for term in terms if str(term).strip()]


def _effective_duplicate_anchor_terms() -> list[str]:
    anchors: list[str] = []
    for anchor in _duplicate_anchor_terms():
        normalized = _normalized_topic_text(anchor)
        if not normalized or normalized in GENERIC_DUPLICATE_TERMS or len(normalized) < 2:
            continue
        anchors.append(anchor)
    return list(dict.fromkeys(anchors))


def _topic_terms(text: str) -> set[str]:
    normalized = re.sub(r"5\s*[·\.\-]\s*18", "518", text)
    terms: set[str] = set()
    for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", normalized):
        cleaned = token.strip().casefold()
        if not cleaned or cleaned in pipeline.SEARCH_STOPWORDS or cleaned in GENERIC_DUPLICATE_TERMS:
            continue
        terms.add(cleaned)
    for anchor in _effective_duplicate_anchor_terms():
        if anchor and anchor in text:
            terms.add(_normalized_topic_text(anchor))
    return terms


def _support_anchor_terms() -> list[str]:
    anchors: list[str] = []
    for rule in _schedule_framing_rules():
        for key in ("match_any", "match_all"):
            anchors.extend(_framing_terms(rule.get(key)))
        variants = rule.get("title_variants", [])
        if not isinstance(variants, list):
            continue
        for variant in variants:
            if not isinstance(variant, dict):
                continue
            for key in ("match_any", "match_all"):
                anchors.extend(_framing_terms(variant.get(key)))
    return list(dict.fromkeys(anchor for anchor in anchors if len(anchor.strip()) >= 2))


def _support_terms(text: str) -> set[str]:
    normalized = re.sub(r"5\s*[·\.\-]\s*18", "518", text)
    terms: set[str] = set()
    for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", normalized):
        cleaned = token.strip().casefold()
        if not cleaned or cleaned in pipeline.SEARCH_STOPWORDS or cleaned in SUPPORT_GENERIC_TERMS:
            continue
        terms.add(cleaned)
    for anchor in _support_anchor_terms():
        if anchor and anchor in text:
            normalized_anchor = _normalized_topic_text(anchor)
            if normalized_anchor and normalized_anchor not in SUPPORT_GENERIC_TERMS:
                terms.add(normalized_anchor)
    return terms


def _shares_duplicate_anchor(title: str, existing: str) -> bool:
    for anchor in _effective_duplicate_anchor_terms():
        if anchor and anchor in title and anchor in existing:
            return True
    return False


def _row_publisher_is_trusted(row: dict[str, object]) -> bool:
    return pipeline._publisher_is_trusted(str(row.get("publisher", "")).strip())


def _feedback_adjustment(text: str, feedback: dict[str, object], content_format: str | None = None) -> int:
    return pipeline._performance_feedback_adjustment(text, feedback, content_format=content_format)


def _format_sequence_from_feedback(feedback: dict[str, object]) -> list[str]:
    sequence = list(DEFAULT_FORMAT_SEQUENCE)
    if not feedback.get("enabled"):
        return sequence
    format_scores = feedback.get("format_scores", {})
    if not isinstance(format_scores, dict):
        return sequence
    def score(format_id: str) -> tuple[int, int]:
        try:
            value = int(format_scores.get(format_id, 0))
        except (TypeError, ValueError):
            value = 0
        return value, -sequence.index(format_id)

    return sorted(sequence, key=score, reverse=True)


def _deep_research_candidates_by_title(discovery: dict[str, object]) -> dict[str, dict[str, object]]:
    report = discovery.get("deep_research_report", {})
    candidates = report.get("topic_candidates", []) if isinstance(report, dict) else []
    result: dict[str, dict[str, object]] = {}
    if not isinstance(candidates, list):
        return result
    for candidate in candidates:
        if not isinstance(candidate, dict):
            continue
        title = str(candidate.get("title", "")).strip()
        if title:
            result[_normalized_topic_text(title)] = candidate
    return result


def _deep_research_score_adjustment(candidate: dict[str, object] | None) -> int:
    if not candidate:
        return -40
    try:
        total_score = int(candidate.get("total_score", 0) or 0)
    except (TypeError, ValueError):
        total_score = 0
    if total_score >= 90:
        adjustment = 24
    elif total_score >= 78:
        adjustment = 14
    elif total_score >= 65:
        adjustment = 4
    elif total_score:
        adjustment = -18
    else:
        adjustment = -10
    risks = candidate.get("production_risks", [])
    if isinstance(risks, list):
        adjustment -= min(18, len(risks) * 6)
    components = candidate.get("score_components", {})
    if isinstance(components, dict):
        try:
            progressive_reaction = int(components.get("progressive_reaction", 0) or 0)
        except (TypeError, ValueError):
            progressive_reaction = 0
        try:
            today_relevance = int(components.get("today_relevance", 0) or 0)
        except (TypeError, ValueError):
            today_relevance = 0
        if progressive_reaction >= 80:
            adjustment += 12
        elif progressive_reaction >= 65:
            adjustment += 6
        elif progressive_reaction < 50:
            adjustment -= 12
        if today_relevance >= 88:
            adjustment += 10
        elif today_relevance >= 75:
            adjustment += 4
    return adjustment


def _deep_research_for_row(row: dict[str, object], discovery: dict[str, object]) -> dict[str, object] | None:
    return _deep_research_candidates_by_title(discovery).get(_normalized_topic_text(str(row.get("title", ""))))


def _published_recency_hours(row: dict[str, object]) -> float | None:
    value = str(row.get("published_at", "")).strip()
    if not value:
        return None
    try:
        published = dt.datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if published.tzinfo is None:
        published = published.replace(tzinfo=dt.timezone.utc)
    age = dt.datetime.now(dt.timezone.utc) - published.astimezone(dt.timezone.utc)
    return max(0.0, age.total_seconds() / 3600)


def _lightweight_research_for_row(row: dict[str, object]) -> dict[str, object]:
    title = str(row.get("title", "")).strip()
    publisher = str(row.get("publisher", "")).strip()
    query = str(row.get("query", "")).strip()
    try:
        heat_score = int(row.get("adjusted_score", row.get("score", 0)) or 0)
    except (TypeError, ValueError):
        heat_score = 0
    recency_hours = _published_recency_hours(row)
    today_relevance = 55
    if recency_hours is not None:
        if recency_hours <= 18:
            today_relevance = 92
        elif recency_hours <= 36:
            today_relevance = 82
        elif recency_hours <= 48:
            today_relevance = 72
    text = f"{title} {query}"
    reaction_config = pipeline.DEEP_RESEARCH_PROGRESSIVE_REACTION

    def term_hits(terms: list[str] | object) -> list[str]:
        if not isinstance(terms, list):
            return []
        return [str(term) for term in terms if str(term).strip() and str(term) in text]

    left_hits = term_hits(pipeline.HOT_TOPIC_LEFT_AUDIENCE_TERMS)
    reference_hits = term_hits(pipeline.HOT_TOPIC_ACCOUNT_REFERENCE_TERMS)
    hard_hits = term_hits(pipeline.HOT_TOPIC_HARD_NEWS_TERMS)
    anger_hits = term_hits(reaction_config.get("anger_terms", []))
    accountability_hits = term_hits(reaction_config.get("accountability_terms", []))
    identity_hits = term_hits(reaction_config.get("identity_terms", []))
    provocation_hits = term_hits(pipeline.PROVOCATION_TERMS)
    progressive_reaction = 36
    progressive_reaction += min(28, len(left_hits) * 7)
    progressive_reaction += min(18, len(reference_hits) * 4)
    progressive_reaction += min(18, len(accountability_hits) * 5)
    progressive_reaction += min(14, len(identity_hits) * 5)
    progressive_reaction += min(14, len(anger_hits) * 6)
    progressive_reaction += min(10, len(provocation_hits) * 3)
    progressive_reaction = max(0, min(100, progressive_reaction))
    narrative_clarity = 42
    narrative_clarity += min(26, len(hard_hits) * 6)
    narrative_clarity += min(18, len(term_hits(pipeline.HOT_TOPIC_CONCRETE_STAKES_TERMS)) * 5)
    narrative_clarity += 10 if re.search(r"\d{1,2}일|내달|다음 달|선고|구형|징역|폐쇄|징벌|비하|조롱|혐오", text) else 0
    narrative_clarity = max(0, min(100, narrative_clarity))
    source_reliability = 76 if pipeline._publisher_is_trusted(publisher) else 58
    source_heat = max(45, min(100, heat_score // 2 if heat_score > 100 else heat_score))
    total_score = round(
        progressive_reaction * 0.36
        + today_relevance * 0.22
        + narrative_clarity * 0.17
        + source_reliability * 0.13
        + source_heat * 0.12
    )
    risks = []
    if not pipeline._publisher_is_trusted(publisher):
        risks.append("trusted_source_verification_needed")
    if progressive_reaction < 55:
        risks.append("progressive_reaction_weak")
    if narrative_clarity < 55:
        risks.append("narrative_clarity_weak")
    return {
        "topic_id": f"schedule_preflight_{_stable_hash(title or query or publisher)}",
        "title": title,
        "matched_archetype_id": "schedule_lightweight_research",
        "matched_archetype_label": "실시간 이슈 프리플라이트",
        "research_question": f"{title}에서 무엇이 확인됐고 어떤 책임 기준이 남았나?",
        "total_score": int(total_score),
        "score_components": {
            "progressive_reaction": int(progressive_reaction),
            "today_relevance": int(today_relevance),
            "narrative_clarity": int(narrative_clarity),
            "source_reliability": int(source_reliability),
            "source_heat": int(source_heat),
        },
        "production_risks": risks,
        "comment_trigger": "1 전말, 2 근거, 3 책임 중 무엇부터 봐야 하나요?",
        "follower_promise": "후속 보도에서 바뀌는 책임선과 빈칸을 계속 추적합니다.",
    }


def _slot_topic_discovery(row: dict[str, object], discovery: dict[str, object]) -> dict[str, object]:
    candidate = _deep_research_for_row(row, discovery)
    research_mode = "deep_research_report"
    using_lightweight = False
    if not candidate:
        candidate = _lightweight_research_for_row(row)
        research_mode = "schedule_lightweight_research"
        using_lightweight = True
    report = discovery.get("deep_research_report", {})
    if not isinstance(report, dict):
        report = {}
    return {
        "mode": "rolling_schedule_plan",
        "deep_research_report": {
            "version": report.get("version", "deep_research_v1"),
            "research_mode": research_mode if using_lightweight else report.get("research_mode", research_mode),
            "selected_topic_id": candidate.get("topic_id"),
            "selected_title": candidate.get("title"),
            "selected_archetype_id": candidate.get("matched_archetype_id"),
            "selected_archetype_label": candidate.get("matched_archetype_label"),
            "selected_research_question": candidate.get("research_question"),
            "topic_candidates": [candidate],
            "script_mandates": report.get("script_mandates", []),
            "visual_mandates": report.get("visual_mandates", []),
            "monetization_hypothesis": report.get("monetization_hypothesis", ""),
            "policy_positioning": report.get("policy_positioning", ""),
        },
        "deep_research_score": candidate.get("total_score", 0),
        "progressive_reaction_score": (
            candidate.get("score_components", {}).get("progressive_reaction", 0)
            if isinstance(candidate.get("score_components", {}), dict)
            else 0
        ),
        "today_relevance_score": (
            candidate.get("score_components", {}).get("today_relevance", 0)
            if isinstance(candidate.get("score_components", {}), dict)
            else 0
        ),
        "selected_archetype_label": candidate.get("matched_archetype_label", ""),
        "research_question": candidate.get("research_question", ""),
        "comment_trigger": candidate.get("comment_trigger", ""),
        "follower_promise": candidate.get("follower_promise", ""),
    }


def _apply_feedback_to_candidates(
    rows: list[dict[str, object]],
    feedback: dict[str, object],
    discovery: dict[str, object] | None = None,
) -> list[dict[str, object]]:
    discovery = discovery or {}
    adjusted: list[dict[str, object]] = []
    for row in rows:
        text = f"{row.get('title', '')} {row.get('query', '')} {row.get('publisher', '')}"
        adjustment = _feedback_adjustment(text, feedback)
        reported_deep_candidate = _deep_research_for_row(row, discovery)
        deep_candidate = reported_deep_candidate or _lightweight_research_for_row(row)
        deep_adjustment = _deep_research_score_adjustment(deep_candidate)
        copied = dict(row)
        copied["feedback_adjustment"] = adjustment
        copied["deep_research_adjustment"] = deep_adjustment
        copied["deep_research_score"] = int(deep_candidate.get("total_score", 0) or 0) if deep_candidate else 0
        score_components = deep_candidate.get("score_components", {}) if deep_candidate else {}
        if isinstance(score_components, dict):
            copied["progressive_reaction_score"] = int(score_components.get("progressive_reaction", 0) or 0)
            copied["today_relevance_score"] = int(score_components.get("today_relevance", 0) or 0)
        else:
            copied["progressive_reaction_score"] = 0
            copied["today_relevance_score"] = 0
        copied["selected_archetype_label"] = (
            str(deep_candidate.get("matched_archetype_label", "")) if deep_candidate else ""
        )
        copied["adjusted_score"] = int(copied.get("score", 0) or 0) + adjustment + deep_adjustment
        adjusted.append(copied)
    return sorted(adjusted, key=lambda item: int(item.get("adjusted_score", item.get("score", 0)) or 0), reverse=True)


def _is_duplicate_topic(title: str, existing_titles: list[str]) -> bool:
    normalized = _normalized_topic_text(title)
    title_terms = _topic_terms(title)
    for existing in existing_titles:
        existing_normalized = _normalized_topic_text(existing)
        if normalized and normalized == existing_normalized:
            return True
        if _shares_duplicate_anchor(title, existing):
            return True
        shared_specific = (_support_terms(title) & _support_terms(existing)) - WEAK_SHARED_SUPPORT_TERMS
        if (
            len(shared_specific) >= 2
            and pipeline._has_specific_topic_overlap(title, existing)
            and pipeline._topic_overlap_score(title, existing) >= 6
        ):
            return True
        existing_terms = _topic_terms(existing)
        shared = title_terms & existing_terms
        if len(shared) >= 3:
            smaller = max(1, min(len(title_terms), len(existing_terms)))
            if len(shared) / smaller >= 0.5:
                return True
    return False


def _is_duplicate_planned_title(title: str, existing_titles: list[str]) -> bool:
    normalized = _normalized_topic_text(title)
    title_terms = _topic_terms(title)
    for existing in existing_titles:
        existing_normalized = _normalized_topic_text(existing)
        if normalized and normalized == existing_normalized:
            return True
        existing_terms = _topic_terms(existing)
        shared = title_terms & existing_terms
        if len(shared) >= 3:
            smaller = max(1, min(len(title_terms), len(existing_terms)))
            if len(shared) / smaller >= 0.65:
                return True
    return False


def _is_excluded_after_framing(title: str, exclusion_titles: list[str]) -> bool:
    return _is_duplicate_topic(title, exclusion_titles) or _is_duplicate_planned_title(title, exclusion_titles)


def _has_unsuitable_topic_terms(title: str) -> bool:
    return any(term in title for term in UNSUITABLE_TOPIC_TERMS) or pipeline.is_low_growth_topic(title)


def _is_suppressed_by_feedback(title: str, feedback: dict[str, object]) -> bool:
    if not feedback.get("enabled"):
        return False
    positive_terms = feedback.get("positive_terms", [])
    if isinstance(positive_terms, list) and any(str(term).strip() and str(term) in title for term in positive_terms):
        return False
    negative_terms = feedback.get("negative_terms", [])
    if not isinstance(negative_terms, list):
        return False
    matched = [str(term) for term in negative_terms if str(term).strip() and str(term) in title]
    if len(matched) >= 2:
        return True
    term_scores = feedback.get("term_scores", {})
    if isinstance(term_scores, dict):
        for term, score in term_scores.items():
            if not str(term).strip() or str(term) not in title:
                continue
            try:
                if int(score) <= -14:
                    return True
            except (TypeError, ValueError):
                continue
    return _feedback_adjustment(title, feedback) <= -24


def _contains_direct_election_action(title: str) -> bool:
    compact = re.sub(r"\s+", "", title)
    return any(term in compact for term in DIRECT_ELECTION_ACTION_TERMS)


def _has_public_accountability_frame(title: str) -> bool:
    return any(term in title for term in PUBLIC_ACCOUNTABILITY_TERMS)


def _strict_topic_blockers(
    *,
    title: str,
    content_format: str,
    source_count: int,
    trusted_source_count: int,
    primary_source_trusted: bool,
    deep_score: int,
    progressive_reaction_score: int,
    trusted_source_present: bool,
) -> list[str]:
    blockers: list[str] = []
    if source_count < 2:
        blockers.append(f"source_count_below_2:{source_count}")
    if not trusted_source_present and source_count < 3:
        blockers.append("trusted_source_or_three_sources_required")
    if not primary_source_trusted and trusted_source_count < 2:
        blockers.append("primary_source_untrusted_without_two_trusted_support")
    if deep_score < 60:
        blockers.append(f"deep_research_score_below_60:{deep_score}")
    if progressive_reaction_score < 55:
        blockers.append(f"progressive_reaction_below_55:{progressive_reaction_score}")
    if _contains_direct_election_action(title):
        blockers.append("direct_election_action_topic")
    if "선거" in title and not _has_public_accountability_frame(title):
        blockers.append("election_topic_without_accountability_frame")
    if content_format == "reward_deep" and source_count < 2:
        blockers.append(f"reward_deep_source_count_below_2:{source_count}")
    return blockers


def _recent_generated_titles(limit: int = 120) -> list[str]:
    output_root = pipeline.REPO_DIR / "output"
    if not output_root.exists():
        return []
    manifests = {
        path
        for path in output_root.glob("tiktok_aino*/**/manifest.json")
        if path.parent.name.startswith("leftaino_")
    }
    manifests = sorted(manifests, key=lambda path: path.stat().st_mtime, reverse=True)
    titles: list[str] = []
    for manifest_path in manifests[:limit]:
        try:
            manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        topic = manifest.get("topic", {})
        script = manifest.get("script", {})
        if isinstance(topic, dict):
            title = str(topic.get("title", "")).strip()
            if title:
                titles.append(title)
        if isinstance(script, dict):
            post_title = str(script.get("post_title", "")).strip()
            if post_title:
                titles.append(post_title)
    return titles


def _diverse_candidates(
    rows: list[dict[str, object]],
    limit: int,
    *,
    exclusions: list[str] | None = None,
) -> list[dict[str, object]]:
    selected: list[dict[str, object]] = []
    deferred: list[dict[str, object]] = []
    excluded_titles = exclusions or []
    for row in rows:
        title = str(row.get("title", ""))
        if _is_duplicate_topic(title, excluded_titles):
            continue
        duplicate = _is_duplicate_topic(title, [str(existing.get("title", "")) for existing in selected])
        if duplicate:
            deferred.append(row)
            continue
        selected.append(row)
        if len(selected) >= limit:
            return selected
    for row in deferred:
        if len(selected) >= limit:
            break
        if _is_duplicate_topic(str(row.get("title", "")), excluded_titles):
            continue
        if _is_duplicate_topic(str(row.get("title", "")), [str(existing.get("title", "")) for existing in selected]):
            continue
        selected.append(row)
    return selected


def _supporting_rows(row: dict[str, object], rows: list[dict[str, object]], max_count: int = 2) -> list[dict[str, object]]:
    support_config = pipeline._config_dict(pipeline.PLANNING_STRATEGY, "rolling_schedule")
    minimum_score = pipeline._strategy_int(support_config, "support_match_min_score", 8)
    candidates: list[tuple[int, int, dict[str, object]]] = []
    for candidate in rows:
        candidate_title = str(candidate.get("title", ""))
        if candidate_title == str(row.get("title", "")):
            continue
        support_score = _same_issue_support_score(row, candidate)
        if support_score < minimum_score:
            continue
        try:
            adjusted_score = int(candidate.get("adjusted_score", candidate.get("score", 0)) or 0)
        except (TypeError, ValueError):
            adjusted_score = 0
        candidates.append((support_score, adjusted_score, candidate))
    candidates.sort(key=lambda item: (item[0], item[1]), reverse=True)
    return [candidate for _, _, candidate in candidates[:max_count]]


def _schedule_framing_rules() -> list[dict[str, object]]:
    rules = pipeline.HOT_TOPIC_STRATEGY.get("schedule_framing_rules", [])
    return [rule for rule in rules if isinstance(rule, dict)] if isinstance(rules, list) else []


def _schedule_framing_text(row: dict[str, object], supporting_rows: list[dict[str, object]] | None) -> str:
    support_titles = " ".join(str(item.get("title", "")) for item in supporting_rows or [])
    return " ".join(
        [
            str(row.get("title", "")),
            str(row.get("query", "")),
            str(row.get("publisher", "")),
            support_titles,
        ]
    )


def _schedule_primary_framing_text(row: dict[str, object]) -> str:
    return " ".join(
        [
            str(row.get("title", "")),
            str(row.get("query", "")),
            str(row.get("publisher", "")),
        ]
    )


def _framing_terms(value: object) -> list[str]:
    if not isinstance(value, list):
        return []
    return [str(term).strip() for term in value if str(term).strip()]


def _framing_rule_score(rule: dict[str, object], text: str, order: int) -> tuple[int, int] | None:
    any_terms = _framing_terms(rule.get("match_any"))
    all_terms = _framing_terms(rule.get("match_all"))
    if all_terms and not all(term in text for term in all_terms):
        return None
    if any_terms and not any(term in text for term in any_terms):
        return None
    if not any_terms and not all_terms:
        return None
    try:
        priority = int(rule.get("priority", 0) or 0)
    except (TypeError, ValueError):
        priority = 0
    matched = sum(1 for term in [*any_terms, *all_terms] if term in text)
    return priority + matched, -order


def _best_framing_rule(text: str) -> dict[str, object] | None:
    best: tuple[int, int, dict[str, object]] | None = None
    for order, rule in enumerate(_schedule_framing_rules()):
        score = _framing_rule_score(rule, text, order)
        if score is None:
            continue
        candidate = (score[0], score[1], rule)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return best[2] if best else None


def _framing_variant_score(variant: dict[str, object], text: str, order: int) -> tuple[int, int] | None:
    any_terms = _framing_terms(variant.get("match_any"))
    all_terms = _framing_terms(variant.get("match_all"))
    if all_terms and not all(term in text for term in all_terms):
        return None
    if any_terms and not any(term in text for term in any_terms):
        return None
    if not any_terms and not all_terms:
        return None
    try:
        priority = int(variant.get("priority", 0) or 0)
    except (TypeError, ValueError):
        priority = 0
    matched = sum(1 for term in [*any_terms, *all_terms] if term in text)
    return priority + matched, -order


def _best_framing_variant(rule: dict[str, object], text: str) -> dict[str, object] | None:
    variants = rule.get("title_variants", [])
    if not isinstance(variants, list):
        return None
    best: tuple[int, int, dict[str, object]] | None = None
    for order, variant in enumerate(variants):
        if not isinstance(variant, dict):
            continue
        score = _framing_variant_score(variant, text, order)
        if score is None:
            continue
        candidate = (score[0], score[1], variant)
        if best is None or candidate[:2] > best[:2]:
            best = candidate
    return best[2] if best else None


def _framing_rule_id_for_row(row: dict[str, object]) -> str:
    _, _, rule_id = _framed_topic_fields(row, [])
    return rule_id


def _framing_rule_base(rule_id: str) -> str:
    return rule_id.split(":", 1)[0] if rule_id else ""


def _framing_rule_variant(rule_id: str) -> str:
    return rule_id.split(":", 1)[1] if ":" in rule_id else ""


def _same_issue_support_score(row: dict[str, object], candidate: dict[str, object]) -> int:
    title = str(row.get("title", ""))
    candidate_title = str(candidate.get("title", ""))
    shared = _support_terms(title) & _support_terms(candidate_title)
    shared_strong = {term for term in shared if term not in WEAK_SHARED_SUPPORT_TERMS}
    row_rule = _framing_rule_id_for_row(row)
    candidate_rule = _framing_rule_id_for_row(candidate)
    row_base = _framing_rule_base(row_rule)
    candidate_base = _framing_rule_base(candidate_rule)
    same_base = bool(row_base and row_base == candidate_base)
    same_variant = bool(row_rule and row_rule == candidate_rule)
    same_query = bool(
        str(row.get("query", "")).strip()
        and str(row.get("query", "")).strip() == str(candidate.get("query", "")).strip()
        and shared_strong
    )
    if not shared_strong and not same_variant:
        return 0
    if row_base != candidate_base and not (same_query and len(shared_strong) >= 2):
        return 0
    if (
        not _row_publisher_is_trusted(row)
        and _framing_rule_variant(row_rule)
        and _framing_rule_variant(candidate_rule)
        and _framing_rule_variant(row_rule) != _framing_rule_variant(candidate_rule)
    ):
        return 0
    score = len(shared_strong) * 5 + (len(shared) - len(shared_strong)) * 2
    if same_base:
        score += 4
    if same_variant:
        score += 6
    if same_query:
        score += 2
    if _row_publisher_is_trusted(candidate):
        score += 2
    return score


def _framed_topic_fields(
    row: dict[str, object],
    supporting_rows: list[dict[str, object]] | None,
) -> tuple[str, str, str]:
    original_title = str(row.get("title", "")).strip()
    default_angle = str(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY.get("angle", "")).strip()
    primary_text = _schedule_primary_framing_text(row)
    rule = _best_framing_rule(primary_text)
    if not rule:
        support_text = _schedule_framing_text(row, supporting_rows)
        rule = _best_framing_rule(support_text)
    if rule:
        variant = _best_framing_variant(rule, primary_text)
        selected = variant or rule
        framed_title = str(selected.get("framed_title") or selected.get("title") or "").strip()
        angle = str(selected.get("angle") or rule.get("angle") or default_angle).strip()
        rule_id = str(rule.get("rule_id") or "schedule_framing_rule").strip()
        variant_id = str(selected.get("variant_id") or "").strip() if variant else ""
        if framed_title:
            return framed_title, angle, f"{rule_id}:{variant_id}" if variant_id else rule_id
    return original_title, default_angle, ""


def _topic_from_candidate(
    row: dict[str, object],
    index: int,
    supporting_rows: list[dict[str, object]] | None = None,
) -> tuple[pipeline.TopicCandidate, dict[str, pipeline.Source]]:
    source_id = f"hot_news_plan_{index:02d}"
    original_title = str(row.get("title", "")).strip()
    title, angle, framing_rule_id = _framed_topic_fields(row, supporting_rows)
    publisher = str(row.get("publisher", "")).strip()
    query = str(row.get("query", "")).strip()
    source = pipeline.Source(
        source_id=source_id,
        title=f"{publisher}: {original_title}".strip(": "),
        url=str(row.get("url", "")),
        note=(
            f"rolling_schedule_candidate query={query}; published={row.get('published_at', '')}; "
            f"heat_score={row.get('score', '')}; original_title={original_title}; framing_rule={framing_rule_id}"
        ),
    )
    claim_template = str(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY.get("claim_text_template", ""))
    sources = {source_id: source}
    claims = [
        pipeline.Claim(
            text=pipeline._format_prompt_template(
                claim_template,
                {"publisher": publisher, "title": original_title, "query": query},
            ),
            source_ids=[source_id],
            risk="medium",
        )
    ]
    for support_index, support in enumerate(supporting_rows or [], start=1):
        support_source_id = f"{source_id}_support_{support_index:02d}"
        support_title = str(support.get("title", "")).strip()
        support_publisher = str(support.get("publisher", "")).strip()
        sources[support_source_id] = pipeline.Source(
            source_id=support_source_id,
            title=f"{support_publisher}: {support_title}".strip(": "),
            url=str(support.get("url", "")),
            note=(
                f"rolling_schedule_support query={support.get('query', '')}; "
                f"published={support.get('published_at', '')}; heat_score={support.get('score', '')}"
            ),
        )
        claims.append(
            pipeline.Claim(
                text=pipeline._format_prompt_template(
                    claim_template,
                    {"publisher": support_publisher, "title": support_title, "query": str(support.get("query", ""))},
                ),
                source_ids=[support_source_id],
                risk="medium",
            )
        )
    topic = pipeline.TopicCandidate(
        title=title,
        angle=angle,
        slot=str(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY.get("slot", "")),
        target_duration_sec=pipeline._strategy_int(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY, "target_duration_sec", 75),
        claims=claims,
        source_ids=list(sources),
    )
    return topic, sources


def _fallback_topic(index: int) -> tuple[pipeline.TopicCandidate, dict[str, pipeline.Source]]:
    del index
    topic = pipeline.collect_topic({})
    return topic, pipeline.load_sources()


def build_rolling_plan(
    *,
    days: int = 3,
    output_dir: Path = pipeline.DEFAULT_OUTPUT_DIR / "schedule_plans",
    timezone_name: str = DEFAULT_TIMEZONE,
    start_offset_days: int = 1,
    performance_report: Path | None = None,
) -> dict[str, object]:
    timezone = ZoneInfo(timezone_name)
    style = pipeline._load_json(pipeline.PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    _, _, discovery = pipeline.discover_hot_topic(style)
    feedback = _load_performance_feedback(performance_report)
    format_sequence = _format_sequence_from_feedback(feedback)
    slot_count = days * len(format_sequence)
    schedule_config = pipeline._config_dict(pipeline.PLANNING_STRATEGY, "rolling_schedule")
    candidate_pool_multiplier = pipeline._strategy_int(schedule_config, "candidate_pool_multiplier", 10)
    candidate_pool_min = pipeline._strategy_int(schedule_config, "candidate_pool_min", 30)
    candidate_pool_limit = max(slot_count * candidate_pool_multiplier, candidate_pool_min)
    adjusted_candidates = _apply_feedback_to_candidates(_candidate_items(discovery), feedback, discovery)
    exclusion_titles = [
        *_recent_queue_titles(),
        *_recent_generated_titles(),
        *_performance_report_exclusions(performance_report),
    ]
    candidates = _diverse_candidates(adjusted_candidates, candidate_pool_limit, exclusions=exclusion_titles)
    now = dt.datetime.now(timezone)
    start_day = (now + dt.timedelta(days=start_offset_days)).date()

    slots: list[dict[str, object]] = []
    available_candidates = list(candidates)
    candidate_index = 0
    planned_topic_titles: list[str] = []
    planned_post_titles: list[str] = []
    for day_offset in range(days):
        day = start_day + dt.timedelta(days=day_offset)
        for content_format in format_sequence:
            plan = pipeline.FORMAT_SPECS[content_format]
            publish_at = _slot_datetime(day, plan.upload_slot, timezone)
            skipped: list[dict[str, object]] = []
            slot: dict[str, object] | None = None
            while available_candidates:
                pick_index = 0
                if content_format == "reward_deep":
                    for scan_index, candidate in enumerate(available_candidates):
                        if _supporting_rows(candidate, adjusted_candidates):
                            pick_index = scan_index
                            break
                row = available_candidates.pop(pick_index)
                row_title = str(row.get("title", ""))
                if _has_unsuitable_topic_terms(row_title):
                    skipped.append({"topic": row.get("title", ""), "reason": "unsuitable_topic_terms"})
                    continue
                if _is_suppressed_by_feedback(row_title, feedback):
                    skipped.append({"topic": row.get("title", ""), "reason": "negative_performance_feedback"})
                    continue
                try:
                    row_feedback_adjustment = int(row.get("feedback_adjustment", 0) or 0)
                except (TypeError, ValueError):
                    row_feedback_adjustment = 0
                if row_feedback_adjustment <= -24:
                    skipped.append({"topic": row.get("title", ""), "reason": "negative_performance_feedback"})
                    continue
                support = _supporting_rows(row, adjusted_candidates)
                topic, sources = _topic_from_candidate(row, candidate_index + 1, support)
                candidate_index += 1
                if _is_excluded_after_framing(topic.title, exclusion_titles):
                    skipped.append({"topic": topic.title, "reason": "recent_or_queued_duplicate_topic"})
                    continue
                if _is_duplicate_planned_title(topic.title, planned_topic_titles):
                    skipped.append({"topic": topic.title, "reason": "duplicate_framed_topic"})
                    continue
                slot_topic_discovery = _slot_topic_discovery(row, discovery)

                script = pipeline.apply_content_format(
                    pipeline.generate_script(topic, style, topic_discovery=slot_topic_discovery or {"mode": "rolling_schedule_plan"}),
                    plan,
                    topic=topic,
                    sources=sources,
                )
                script, gate, readability, quality = pipeline.select_publish_script([script], topic, sources, plan)
                blockers = quality.blockers + gate.errors + readability.issues
                if _is_excluded_after_framing(script.post_title, exclusion_titles):
                    blockers.append("recent_or_queued_duplicate_post_title")
                if _is_duplicate_planned_title(script.post_title, planned_post_titles):
                    blockers.append("duplicate_post_title_in_plan")
                reward_source_min = pipeline._strategy_int(pipeline.REWARD_DEEP_STRATEGY, "source_count_min", 2)
                if content_format == "reward_deep" and len(sources) < reward_source_min:
                    blockers.append("reward_deep_source_count_lt_2")
                deep_score = int(slot_topic_discovery.get("deep_research_score", 0) or 0)
                planner_warnings: list[str] = []
                if not slot_topic_discovery:
                    planner_warnings.append("deep_research_missing")
                elif deep_score < 60:
                    blockers.append(f"deep_research_score_below_60:{deep_score}")
                progressive_reaction_score = int(slot_topic_discovery.get("progressive_reaction_score", 0) or 0)
                if slot_topic_discovery and progressive_reaction_score < 50:
                    blockers.append(f"progressive_reaction_below_50:{progressive_reaction_score}")
                trusted_source_present = any(
                    pipeline._publisher_is_trusted(str(source.title).split(":", 1)[0])
                    for source in sources.values()
                )
                trusted_source_count = sum(
                    1
                    for source in sources.values()
                    if pipeline._publisher_is_trusted(str(source.title).split(":", 1)[0])
                )
                primary_source_trusted = _row_publisher_is_trusted(row)
                if not trusted_source_present and len(sources) < 2:
                    blockers.append("trusted_source_or_multi_source_required")
                blockers.extend(
                    _strict_topic_blockers(
                        title=topic.title,
                        content_format=content_format,
                        source_count=len(sources),
                        trusted_source_count=trusted_source_count,
                        primary_source_trusted=primary_source_trusted,
                        deep_score=deep_score,
                        progressive_reaction_score=progressive_reaction_score,
                        trusted_source_present=trusted_source_present,
                    )
                )
                blockers = list(dict.fromkeys(blockers))
                ready_for_generation = quality.passed and gate.passed and readability.passed and not blockers
                candidate_slot = {
                    "publish_at_local": publish_at.isoformat(),
                    "format": plan.format_id,
                    "objective": plan.objective,
                    "topic": topic.title,
                    "post_title": script.post_title,
                    "caption": script.caption,
                    "hashtags": script.hashtags,
                    "topic_candidate": asdict(topic),
                    "topic_discovery": slot_topic_discovery,
                    "quality_score": quality.publish_ready_score,
                    "quality_passed": quality.passed,
                    "gate_passed": gate.passed,
                    "readability_passed": readability.passed,
                    "blockers": blockers,
                    "warnings": planner_warnings,
                    "sources": [asdict(source) for source in sources.values()],
                    "feedback_adjustment": _feedback_adjustment(
                        f"{topic.title} {topic.angle} {topic.slot}",
                        feedback,
                        plan.format_id,
                    ),
                    "source_count": len(sources),
                    "trusted_source_count": trusted_source_count,
                    "primary_source_trusted": primary_source_trusted,
                    "ready_for_generation": ready_for_generation,
                    "skipped_candidates": skipped,
                }
                if ready_for_generation:
                    slot = candidate_slot
                    planned_topic_titles.append(topic.title)
                    planned_post_titles.append(script.post_title)
                    break
                skipped.append({"topic": topic.title, "reason": "quality_blockers", "blockers": blockers})

            if slot is None:
                slot = {
                    "publish_at_local": publish_at.isoformat(),
                    "format": plan.format_id,
                    "objective": plan.objective,
                    "topic": "",
                    "post_title": "",
                    "caption": "",
                    "hashtags": [],
                    "topic_candidate": None,
                    "quality_score": 0,
                    "quality_passed": False,
                    "gate_passed": False,
                    "readability_passed": False,
                    "blockers": ["candidate_pool_exhausted"],
                    "warnings": [],
                    "sources": [],
                    "feedback_adjustment": 0,
                    "source_count": 0,
                    "trusted_source_count": 0,
                    "primary_source_trusted": False,
                    "ready_for_generation": False,
                    "skipped_candidates": skipped,
                }
            slots.append(slot)

    result = {
        "created_at": now.isoformat(),
        "timezone": timezone_name,
        "days": days,
        "start_day": start_day.isoformat(),
        "mode": "rolling_three_day_plan",
        "format_sequence": format_sequence,
        "discovery": discovery,
        "performance_feedback": feedback,
        "slots": slots,
        "ready_count": sum(1 for slot in slots if slot["ready_for_generation"]),
    }
    output_dir.mkdir(parents=True, exist_ok=True)
    path = output_dir / f"rolling_plan_{now:%Y%m%d_%H%M%S}.json"
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    result["path"] = str(path)
    return result


def _print_json(data: object) -> None:
    text = json.dumps(data, ensure_ascii=False, indent=2)
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")


def main() -> int:
    parser = argparse.ArgumentParser(description="Build an AiNo TikTok rolling schedule plan.")
    parser.add_argument("--days", type=int, default=3)
    parser.add_argument("--output-dir", type=Path, default=pipeline.DEFAULT_OUTPUT_DIR / "schedule_plans")
    parser.add_argument("--timezone", default=DEFAULT_TIMEZONE)
    parser.add_argument("--start-offset-days", type=int, default=1)
    parser.add_argument("--performance-report", type=Path)
    args = parser.parse_args()

    result = build_rolling_plan(
        days=max(1, args.days),
        output_dir=args.output_dir,
        timezone_name=args.timezone,
        start_offset_days=max(0, args.start_offset_days),
        performance_report=args.performance_report,
    )
    _print_json(result)
    return 0 if result["ready_count"] == len(result["slots"]) else 2


if __name__ == "__main__":
    raise SystemExit(main())
