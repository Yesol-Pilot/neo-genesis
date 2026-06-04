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
    "투표",
    "사전투표",
    "본투표",
    "표로",
    "찍자",
    "뽑자",
    "지지하자",
    "심판하자",
    "투표서",
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


def _normalized_topic_text(text: str) -> str:
    return re.sub(r"[^0-9A-Za-z가-힣]", "", text).casefold()


def _stable_hash(text: str, length: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:length]


def _duplicate_anchor_terms() -> list[str]:
    terms = pipeline.HOT_TOPIC_STRATEGY.get("duplicate_anchor_terms", [])
    if not isinstance(terms, list):
        return []
    return [str(term) for term in terms if str(term).strip()]


def _topic_terms(text: str) -> set[str]:
    normalized = re.sub(r"5\s*[·\.\-]\s*18", "518", text)
    terms: set[str] = set()
    for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", normalized):
        cleaned = token.strip().casefold()
        if not cleaned or cleaned in pipeline.SEARCH_STOPWORDS or cleaned in GENERIC_DUPLICATE_TERMS:
            continue
        terms.add(cleaned)
    for anchor in _duplicate_anchor_terms():
        if anchor and anchor in text:
            terms.add(_normalized_topic_text(anchor))
    return terms


def _shares_duplicate_anchor(title: str, existing: str) -> bool:
    for anchor in _duplicate_anchor_terms():
        if anchor and anchor in title and anchor in existing:
            return True
    return False


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
        if pipeline._has_specific_topic_overlap(title, existing) and pipeline._topic_overlap_score(title, existing) >= 6:
            return True
        existing_terms = _topic_terms(existing)
        shared = title_terms & existing_terms
        if len(shared) >= 3:
            smaller = max(1, min(len(title_terms), len(existing_terms)))
            if len(shared) / smaller >= 0.5:
                return True
    return False


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
    deep_score: int,
    progressive_reaction_score: int,
    trusted_source_present: bool,
) -> list[str]:
    blockers: list[str] = []
    if source_count < 2:
        blockers.append(f"source_count_below_2:{source_count}")
    if not trusted_source_present and source_count < 3:
        blockers.append("trusted_source_or_three_sources_required")
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
    title = str(row.get("title", ""))
    query = str(row.get("query", ""))
    title_terms = _topic_terms(title)
    candidates: list[dict[str, object]] = []
    for candidate in rows:
        candidate_title = str(candidate.get("title", ""))
        if candidate_title == title:
            continue
        candidate_query = str(candidate.get("query", ""))
        candidate_terms = _topic_terms(candidate_title)
        shared_terms = title_terms & candidate_terms
        same_cluster = pipeline._has_specific_topic_overlap(title, candidate_title)
        overlap_score = pipeline._topic_overlap_score(title, candidate_title)
        same_query_support = bool(query and candidate_query and query == candidate_query and len(shared_terms) >= 2)
        accountability_support = bool(
            len(shared_terms) >= 2
            and any(term in f"{title} {candidate_title}" for term in PUBLIC_ACCOUNTABILITY_TERMS)
        )
        if (same_cluster and overlap_score >= 5) or same_query_support or accountability_support:
            candidates.append(candidate)
    return sorted(candidates, key=lambda item: int(item.get("adjusted_score", item.get("score", 0)) or 0), reverse=True)[:max_count]


def _topic_from_candidate(
    row: dict[str, object],
    index: int,
    supporting_rows: list[dict[str, object]] | None = None,
) -> tuple[pipeline.TopicCandidate, dict[str, pipeline.Source]]:
    source_id = f"hot_news_plan_{index:02d}"
    title = str(row.get("title", "")).strip()
    publisher = str(row.get("publisher", "")).strip()
    query = str(row.get("query", "")).strip()
    source = pipeline.Source(
        source_id=source_id,
        title=f"{publisher}: {title}".strip(": "),
        url=str(row.get("url", "")),
        note=f"rolling_schedule_candidate query={query}; published={row.get('published_at', '')}; heat_score={row.get('score', '')}",
    )
    claim_template = str(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY.get("claim_text_template", ""))
    sources = {source_id: source}
    claims = [
        pipeline.Claim(
            text=pipeline._format_prompt_template(
                claim_template,
                {"publisher": publisher, "title": title, "query": query},
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
        angle=str(pipeline.HOT_TOPIC_CANDIDATE_STRATEGY.get("angle", "")),
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
    candidate_pool_limit = max(slot_count * 10, 30)
    adjusted_candidates = _apply_feedback_to_candidates(_candidate_items(discovery), feedback, discovery)
    exclusion_titles = [*_recent_generated_titles(), *_performance_report_exclusions(performance_report)]
    candidates = _diverse_candidates(adjusted_candidates, candidate_pool_limit, exclusions=exclusion_titles)
    now = dt.datetime.now(timezone)
    start_day = (now + dt.timedelta(days=start_offset_days)).date()

    slots: list[dict[str, object]] = []
    available_candidates = list(candidates)
    candidate_index = 0
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
                slot_topic_discovery = _slot_topic_discovery(row, discovery)

                script = pipeline.apply_content_format(
                    pipeline.generate_script(topic, style, topic_discovery=slot_topic_discovery or {"mode": "rolling_schedule_plan"}),
                    plan,
                    topic=topic,
                    sources=sources,
                )
                script, gate, readability, quality = pipeline.select_publish_script([script], topic, sources, plan)
                blockers = quality.blockers + gate.errors + readability.issues
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
                if not trusted_source_present and len(sources) < 2:
                    blockers.append("trusted_source_or_multi_source_required")
                blockers.extend(
                    _strict_topic_blockers(
                        title=topic.title,
                        content_format=content_format,
                        source_count=len(sources),
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
                    "ready_for_generation": ready_for_generation,
                    "skipped_candidates": skipped,
                }
                if ready_for_generation:
                    slot = candidate_slot
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
