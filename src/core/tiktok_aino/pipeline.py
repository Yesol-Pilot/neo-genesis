"""Deterministic MVP pipeline for the leftaino TikTok account.

This module intentionally avoids external posting. It creates one
policy-checked content package, provider-traced media assets, and local review
artifacts before any Chrome Extension upload automation is wired in.
"""

from __future__ import annotations

import argparse
import contextlib
import datetime as dt
import email.utils
import hashlib
import html
import json
import math
import os
import re
import shutil
import subprocess
import sys
import time
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field, replace
from functools import lru_cache
from io import BytesIO
from pathlib import Path
from typing import Any
from urllib.parse import urlencode

import imageio.v2 as imageio
import numpy as np
from PIL import Image, ImageColor, ImageDraw, ImageEnhance, ImageFilter, ImageFont

from src.core.tiktok_aino import privacy as privacy_policy


PACKAGE_DIR = Path(__file__).resolve().parent
REPO_DIR = PACKAGE_DIR.parents[2]
DEFAULT_OUTPUT_DIR = REPO_DIR / "output" / "tiktok_aino"
DEFAULT_PERFORMANCE_REPORT_DIR = REPO_DIR / "output" / "tiktok_aino_performance_reports"
DEFAULT_PERFORMANCE_FEEDBACK_PATH = DEFAULT_PERFORMANCE_REPORT_DIR / "performance_feedback.json"
CONFIG_DIR = PACKAGE_DIR / "config"
SEOUL_TZ = dt.timezone(dt.timedelta(hours=9))


def _load_runtime_env_files() -> None:
    if os.environ.get("AINO_SKIP_ENV_FILE_LOAD", "").lower() in {"1", "true", "yes", "on"}:
        return
    for path in (REPO_DIR / ".env.local", REPO_DIR / ".env"):
        if not path.exists() or not path.is_file():
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except OSError:
            continue
        for raw in lines:
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            if line.startswith("export "):
                line = line[len("export ") :].strip()
            name, value = line.split("=", 1)
            name = name.strip()
            value = value.strip()
            if not name or name in os.environ:
                continue
            if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
                value = value[1:-1]
            os.environ[name] = value


_load_runtime_env_files()


def default_real_image_limit_from_env() -> int | None:
    value = os.environ.get("AINO_REAL_IMAGE_LIMIT")
    if value is None or not value.strip():
        return None
    return max(0, int(value))


@lru_cache(maxsize=16)
def _load_strategy_config(filename: str) -> dict[str, Any]:
    path = CONFIG_DIR / filename
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError as exc:
        raise RuntimeError(f"Missing TikTok AiNo strategy config: {path}") from exc
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Invalid TikTok AiNo strategy config: {path}: {exc}") from exc
    if not isinstance(raw, dict):
        raise RuntimeError(f"TikTok AiNo strategy config must be a JSON object: {path}")
    return raw


def _config_list(config: dict[str, Any], key: str) -> list[str]:
    value = config.get(key)
    if not isinstance(value, list):
        raise RuntimeError(f"Strategy config key must be a list: {key}")
    return [str(item) for item in value if str(item).strip()]


def _config_dict(config: dict[str, Any], key: str) -> dict[str, Any]:
    value = config.get(key)
    if not isinstance(value, dict):
        raise RuntimeError(f"Strategy config key must be an object: {key}")
    return value


def _config_int_map(config: dict[str, Any], key: str) -> dict[str, int]:
    value = _config_dict(config, key)
    result: dict[str, int] = {}
    for item_key, item_value in value.items():
        try:
            result[str(item_key)] = int(item_value)
        except (TypeError, ValueError) as exc:
            raise RuntimeError(f"Strategy config value must be an integer: {key}.{item_key}") from exc
    return result


def _strategy_int(section: dict[str, Any], key: str, fallback: int) -> int:
    try:
        return int(section.get(key, fallback))
    except (TypeError, ValueError) as exc:
        raise RuntimeError(f"Strategy config value must be an integer: {key}") from exc


def _strategy_terms(section: dict[str, Any], key: str) -> list[str]:
    value = section.get(key, [])
    if not isinstance(value, list):
        raise RuntimeError(f"Strategy config key must be a list: {key}")
    return [str(term) for term in value if str(term).strip()]


class _MissingPromptValue(dict):
    def __missing__(self, key: str) -> str:
        return ""


def _format_prompt_template(template: str, values: dict[str, Any]) -> str:
    return template.format_map(_MissingPromptValue({key: str(value) for key, value in values.items()}))


def _config_nested_list(config: dict[str, Any], section_key: str, item_key: str) -> list[str]:
    section = _config_dict(config, section_key)
    value = section.get(item_key, [])
    if not isinstance(value, list):
        raise RuntimeError(f"Strategy config key must be a list: {section_key}.{item_key}")
    return [str(item) for item in value if str(item).strip()]


def _contains_any_marker(text: str, markers: list[str]) -> bool:
    normalized = text.casefold()
    return any(marker.casefold() in normalized for marker in markers)


def _contains_all_markers(text: str, markers: list[str]) -> bool:
    normalized = text.casefold()
    return all(marker.casefold() in normalized for marker in markers)

CANVAS_WIDTH = 1080
CANVAS_HEIGHT = 1920
VIDEO_FPS = 30
VIDEO_CODEC = "libx264"
VIDEO_BITRATE = "10M"
MOBILE_PREVIEW_WIDTH = 390
TEXT_SAFE_LEFT = 104
TEXT_SAFE_RIGHT = 936
TEXT_SAFE_WIDTH = TEXT_SAFE_RIGHT - TEXT_SAFE_LEFT
BODY_TEXT_LEFT = 144
BODY_TEXT_WIDTH = TEXT_SAFE_RIGHT - BODY_TEXT_LEFT - 40
CRITICAL_TEXT_BOTTOM = 1558
TIKTOK_RIGHT_RAIL_LEFT = 936
TIKTOK_BOTTOM_UI_TOP = 1660
MOBILE_PREVIEW_HEIGHT = round(CANVAS_HEIGHT * MOBILE_PREVIEW_WIDTH / CANVAS_WIDTH)
HEADLINE_FONT_INITIAL = 78
HEADLINE_FONT_MIN = 54
BODY_FONT_INITIAL = 46
BODY_FONT_MIN = 40
HEADLINE_MIN_CHARS = 8
HEADLINE_TARGET_MAX_CHARS = 24
BODY_TEXT_MIN_CHARS_MOBILE = 32
BODY_TEXT_MAX_CHARS_MOBILE = 84
FORMAT_BODY_TEXT_MAX_CHARS = {
    "growth_short": 52,
    "ranking_battle_65": 72,
    "narrative_confession": 72,
    "reward_deep": 84,
    "reformed_briefing": 84,
    "debate_followup": 72,
}
MIN_HEADLINE_PREVIEW_PX = 19
MIN_BODY_PREVIEW_PX = 14
MAX_TEXT_PANEL_COVERAGE_PCT = 18.0
HOT_TOPIC_STRATEGY = _load_strategy_config("hot_topic_strategy.json")
HOT_TOPIC_QUERIES = _config_list(HOT_TOPIC_STRATEGY, "queries")
HOT_TOPIC_PRIORITY_QUERIES = _config_list(HOT_TOPIC_STRATEGY, "priority_queries")
HOT_TOPIC_TARGET_TERMS = _config_list(HOT_TOPIC_STRATEGY, "target_terms")
HOT_TOPIC_RISK_TERMS = _config_list(HOT_TOPIC_STRATEGY, "risk_terms")
HOT_TOPIC_TRUSTED_SOURCES = _config_list(HOT_TOPIC_STRATEGY, "trusted_sources")
HOT_TOPIC_OPINION_TERMS = _config_list(HOT_TOPIC_STRATEGY, "opinion_terms")
HOT_TOPIC_LOW_NEWS_TERMS = _config_list(HOT_TOPIC_STRATEGY, "low_news_terms")
HOT_TOPIC_HARD_NEWS_TERMS = _config_list(HOT_TOPIC_STRATEGY, "hard_news_terms")
HOT_TOPIC_LEFT_AUDIENCE_TERMS = _config_list(HOT_TOPIC_STRATEGY, "left_audience_terms")
HOT_TOPIC_ACCOUNT_REFERENCE_TERMS = _config_list(HOT_TOPIC_STRATEGY, "account_reference_terms")
HOT_TOPIC_CONCRETE_STAKES_TERMS = _config_list(HOT_TOPIC_STRATEGY, "concrete_stakes_terms")
HOT_TOPIC_WEAK_ADMIN_TERMS = _config_list(HOT_TOPIC_STRATEGY, "weak_admin_terms")
HOT_TOPIC_BROAD_CLUSTER_TOKENS = set(_config_list(HOT_TOPIC_STRATEGY, "broad_cluster_tokens"))
HOT_TOPIC_SCORES = _config_int_map(HOT_TOPIC_STRATEGY, "scores")
HOT_TOPIC_CANDIDATE_STRATEGY = _config_dict(HOT_TOPIC_STRATEGY, "topic_candidate")
HOT_TOPIC_TREND_CLUSTERS = [row for row in HOT_TOPIC_STRATEGY.get("trend_clusters", []) if isinstance(row, dict)]
SEARCH_VALUE_PRIORITY_TERMS = _config_list(HOT_TOPIC_STRATEGY, "search_value_priority_terms")
PROVOCATION_TERMS = _config_list(HOT_TOPIC_STRATEGY, "provocation_terms")
PROVOCATION_CONTRAST_TERMS = _config_list(HOT_TOPIC_STRATEGY, "provocation_contrast_terms")
UNSAFE_PROVOCATION_TERMS = _config_list(HOT_TOPIC_STRATEGY, "unsafe_provocation_terms")
SEARCH_STOPWORDS = set(_config_list(HOT_TOPIC_STRATEGY, "search_stopwords"))
HOT_HOOK_HEADLINE_RULES = list(HOT_TOPIC_STRATEGY.get("hook_headline_rules", []))
HOT_HOOK_FALLBACK_HEADLINE = str(HOT_TOPIC_STRATEGY.get("fallback_hook_headline", "이 이슈, 왜 지금?"))
HOT_CUSTOM_ISSUE_KIND_RULES = [row for row in HOT_TOPIC_STRATEGY.get("custom_issue_kind_rules", []) if isinstance(row, dict)]
REFERENCE_STORY_RULE_SCORING = _config_int_map(HOT_TOPIC_STRATEGY, "reference_storyboard_rule_scoring")
DEEP_RESEARCH_STRATEGY = _load_strategy_config("deep_research_strategy.json")
DEEP_RESEARCH_VERSION = str(DEEP_RESEARCH_STRATEGY.get("version", "deep_research_v1"))
DEEP_RESEARCH_MODE = str(DEEP_RESEARCH_STRATEGY.get("research_mode", "official_policy_plus_live_news"))
DEEP_RESEARCH_PLATFORM_CONSTRAINTS = [
    row for row in DEEP_RESEARCH_STRATEGY.get("official_platform_constraints", []) if isinstance(row, dict)
]
DEEP_RESEARCH_ARCHETYPES = [
    row for row in DEEP_RESEARCH_STRATEGY.get("reference_archetypes", []) if isinstance(row, dict)
]
DEEP_RESEARCH_DEFAULT_VALUES = _config_dict(DEEP_RESEARCH_STRATEGY, "default_values")
DEEP_RESEARCH_SCORING = _config_int_map(DEEP_RESEARCH_STRATEGY, "scoring")
DEEP_RESEARCH_DIMENSION_WEIGHTS = _config_int_map(DEEP_RESEARCH_STRATEGY, "dimension_weights")
DEEP_RESEARCH_MINIMUMS = _config_int_map(DEEP_RESEARCH_STRATEGY, "minimums")
DEEP_RESEARCH_PROGRESSIVE_REACTION = _config_dict(DEEP_RESEARCH_STRATEGY, "progressive_reaction")
DEEP_RESEARCH_TENSION_TERMS = _config_list(DEEP_RESEARCH_STRATEGY, "tension_terms")
DEEP_RESEARCH_EVIDENCE_TERMS = _config_list(DEEP_RESEARCH_STRATEGY, "evidence_terms")
DEEP_RESEARCH_CINEMATIC_TERMS = _config_list(DEEP_RESEARCH_STRATEGY, "cinematic_terms")
DEEP_RESEARCH_COMMENT_TERMS = _config_list(DEEP_RESEARCH_STRATEGY, "comment_terms")
DEEP_RESEARCH_SCRIPT_MANDATES = _config_list(DEEP_RESEARCH_STRATEGY, "script_mandates")
DEEP_RESEARCH_VISUAL_MANDATES = _config_list(DEEP_RESEARCH_STRATEGY, "visual_mandates")
PLANNING_STRATEGY = _load_strategy_config("planning_strategy.json")
PLANNING_ROLE_QUESTIONS = _config_dict(PLANNING_STRATEGY, "role_questions")
PLANNING_ROLE_EVIDENCE_NEEDS = _config_dict(PLANNING_STRATEGY, "role_evidence_needs")
PLANNING_NARRATIVE_ARCS = _config_dict(PLANNING_STRATEGY, "narrative_arc_by_format")
FACT_PACK_STRATEGY = _config_dict(PLANNING_STRATEGY, "fact_pack")
RISK_FLAGS_STRATEGY = _config_dict(PLANNING_STRATEGY, "risk_flags")
SOURCE_CARD_STRATEGY = _config_dict(PLANNING_STRATEGY, "source_card")
ANGLE_BRIEF_STRATEGY = _config_dict(PLANNING_STRATEGY, "angle_brief")
STORYBOARD_BRIEF_STRATEGY = _config_dict(PLANNING_STRATEGY, "storyboard_brief")
TTS_PERFORMANCE_STRATEGY = _config_dict(PLANNING_STRATEGY, "tts_performance")
REFERENCE_PATTERNS_CONFIG = _load_strategy_config("reference_patterns.json")
FORMAT_ROUTER_CONFIG = _load_strategy_config("format_router.json")
HOOK_PATTERNS_CONFIG = _load_strategy_config("hook_patterns.json")
SCENE_TYPE_LIBRARY_CONFIG = _load_strategy_config("scene_type_library.json")
CTA_PATTERNS_CONFIG = _load_strategy_config("cta_patterns.json")
KEYWORD_STRATEGY = _load_strategy_config("keyword_strategy.json")
KEYWORD_BASE_QUERIES = _config_list(KEYWORD_STRATEGY, "base_queries")
KEYWORD_SEED_BASKETS = [row for row in KEYWORD_STRATEGY.get("seed_baskets", []) if isinstance(row, dict)]
KEYWORD_QUERY_TEMPLATES = _config_list(KEYWORD_STRATEGY, "query_templates")
KEYWORD_STOPWORDS = set(_config_list(KEYWORD_STRATEGY, "stopwords"))
KEYWORD_BAD_PHRASE_LEADING_TERMS = set(_config_list(KEYWORD_STRATEGY, "bad_phrase_leading_terms"))
KEYWORD_HIGH_INTENT_TERMS = _config_list(KEYWORD_STRATEGY, "high_intent_terms")
KEYWORD_GENERIC_SINGLE_TERMS = set(_config_list(KEYWORD_STRATEGY, "generic_single_terms"))
KEYWORD_SCORING = _config_int_map(KEYWORD_STRATEGY, "scoring")
KEYWORD_LIMITS = _config_int_map(KEYWORD_STRATEGY, "limits")
EDITORIAL_STRATEGY = _load_strategy_config("editorial_strategy.json")
EDITORIAL_ANGLE_RULES = [row for row in EDITORIAL_STRATEGY.get("angle_rules", []) if isinstance(row, dict)]
PUBLISH_QUALITY_STRATEGY = _load_strategy_config("publish_quality_strategy.json")
SEARCH_VALUE_STRATEGY = _config_dict(PUBLISH_QUALITY_STRATEGY, "search_value")
SAFE_PROVOCATION_STRATEGY = _config_dict(PUBLISH_QUALITY_STRATEGY, "safe_provocation")
POLICY_GATE_STRATEGY = _config_dict(PUBLISH_QUALITY_STRATEGY, "policy_gate")
CONTENT_REVIEW_STRATEGY = _config_dict(PUBLISH_QUALITY_STRATEGY, "content_review")
RENDERING_STRATEGY = _config_dict(PUBLISH_QUALITY_STRATEGY, "rendering")
SCRIPT_QUALITY_STRATEGY = _config_dict(PUBLISH_QUALITY_STRATEGY, "script_quality")
IMAGE_BUDGET_STRATEGY = _load_strategy_config("image_budget_strategy.json")
SCRIPT_QUALITY_WEIGHTS = {
    str(key): float(value)
    for key, value in _config_dict(SCRIPT_QUALITY_STRATEGY, "weights").items()
}
SCRIPT_QUALITY_MINIMUMS = _config_int_map(SCRIPT_QUALITY_STRATEGY, "minimums")
HEADLINE_QUOTE_FORMAT_BANNED_TERMS = list(
    dict.fromkeys(
        [
            "보도 제목 기준",
            "뉴스 보도 제목",
            "ë³´ë„ ì œëª© ê¸°ì¤€",
            "ë‰´ìŠ¤ ë³´ë„ ì œëª©",
            *_strategy_terms(SCRIPT_QUALITY_STRATEGY, "headline_quote_banned_terms"),
        ]
    )
)
FATIGUED_QUESTION_TEMPLATE_TERMS = list(
    dict.fromkeys(
        [
            "왜 먹히나",
            "왜 흔들리나",
            "왜 갈리나",
            "뭐가 먹히나",
            "누가 먹히나",
            "왜 안 죽나",
            *_strategy_terms(SCRIPT_QUALITY_STRATEGY, "fatigued_question_template_terms"),
        ]
    )
)
SCRIPT_STRATEGY = _load_strategy_config("script_strategy.json")
COPY_NORMALIZATION_STRATEGY = _config_dict(SCRIPT_STRATEGY, "copy_normalization")
POST_METADATA_STRATEGY = _config_dict(SCRIPT_STRATEGY, "post_metadata")
REWARD_DEEP_STRATEGY = _config_dict(SCRIPT_STRATEGY, "reward_deep_format")
HOT_TOPIC_SCRIPT_STRATEGY = _config_dict(SCRIPT_STRATEGY, "hot_topic_script")
DEFAULT_SCRIPT_STRATEGY = _config_dict(SCRIPT_STRATEGY, "default_script")
SCRIPT_VARIANT_STRATEGY = _config_dict(SCRIPT_STRATEGY, "variants")
DEFAULT_TOPIC_STRATEGY = _config_dict(SCRIPT_STRATEGY, "default_topic")
TTS_STRATEGY = _load_strategy_config("tts_strategy.json")
SINO_DIGITS = _strategy_terms(TTS_STRATEGY, "sino_digits")
NATIVE_ONES = {
    int(key): (str(value[0]), str(value[1]))
    for key, value in _config_dict(TTS_STRATEGY, "native_ones").items()
    if isinstance(value, list) and len(value) >= 2
}
NATIVE_TENS = {int(key): str(value) for key, value in _config_dict(TTS_STRATEGY, "native_tens").items()}
NATIVE_COUNTER_UNITS = set(_strategy_terms(TTS_STRATEGY, "native_counter_units"))
SINO_COUNTER_UNITS = set(_strategy_terms(TTS_STRATEGY, "sino_counter_units"))
TTS_SINO_UNITS = [
    (int(item.get("value", 0)), str(item.get("word", "")))
    for item in TTS_STRATEGY.get("sino_units", [])
    if isinstance(item, dict)
]
TTS_LARGE_UNITS = [
    (int(item.get("value", 0)), str(item.get("word", "")))
    for item in TTS_STRATEGY.get("large_units", [])
    if isinstance(item, dict)
]
TTS_NEGATIVE_PREFIX = str(TTS_STRATEGY.get("negative_prefix", ""))
TTS_NATIVE_TWENTY_ATTRIBUTIVE = str(TTS_STRATEGY.get("native_twenty_attributive", ""))
TTS_URL_REPLACEMENT = str(TTS_STRATEGY.get("url_replacement", ""))
TTS_HASHTAG_PREFIX = str(TTS_STRATEGY.get("hashtag_prefix", ""))
TTS_MENTION_SUFFIX = str(TTS_STRATEGY.get("mention_suffix", ""))
TTS_SYMBOL_REPLACEMENTS = {
    str(key): str(value) for key, value in _config_dict(TTS_STRATEGY, "symbol_replacements").items()
}


@dataclass(frozen=True)
class Source:
    source_id: str
    title: str
    url: str
    note: str


@dataclass(frozen=True)
class Claim:
    text: str
    source_ids: list[str]
    risk: str = "low"


@dataclass(frozen=True)
class TopicCandidate:
    title: str
    angle: str
    slot: str
    target_duration_sec: int
    claims: list[Claim]
    source_ids: list[str]


@dataclass(frozen=True)
class HotTopicItem:
    title: str
    publisher: str
    url: str
    published_at: str
    query: str
    score: int


@dataclass(frozen=True)
class KeywordCandidate:
    keyword: str
    basket_id: str
    intent: str
    score: int
    support_count: int
    matched_seeds: list[str]
    matched_modifiers: list[str]
    matched_high_intent_terms: list[str]
    risk_terms: list[str]
    source_queries: list[str]
    rationale: list[str]


@dataclass(frozen=True)
class KeywordPlan:
    version: str
    base_queries: list[str]
    expanded_queries: list[str]
    selected_keywords: list[KeywordCandidate]
    rejected_keywords: list[KeywordCandidate]
    scoring_notes: list[str]


@dataclass(frozen=True)
class TopicPoolCandidate:
    topic_id: str
    title: str
    query: str
    publisher: str
    url: str
    published_at: str
    keywords: list[str]
    support_count: int
    risk: str
    format_hint: str
    score: int
    score_components: dict[str, int]


@dataclass(frozen=True)
class TopicPool:
    version: str
    candidates: list[TopicPoolCandidate]


@dataclass(frozen=True)
class TopicPlan:
    version: str
    selected_topic_id: str
    selected_title: str
    selection_reason: str
    scores: dict[str, int]
    support_count: int
    keywords: list[str]
    blocked_candidates: list[dict[str, Any]]


@dataclass(frozen=True)
class DeepResearchCandidate:
    topic_id: str
    title: str
    query: str
    publisher: str
    url: str
    matched_archetype_id: str
    matched_archetype_label: str
    matched_terms: list[str]
    research_question: str
    counterpoint_focus: str
    comment_trigger: str
    follower_promise: str
    script_arc: list[str]
    visual_sequence: list[str]
    score_components: dict[str, int]
    total_score: int
    rationale: list[str]
    production_risks: list[str]


@dataclass(frozen=True)
class DeepResearchReport:
    version: str
    generated_at: str
    research_mode: str
    official_platform_constraints: list[dict[str, Any]]
    selected_topic_id: str
    selected_title: str
    selected_archetype_id: str
    selected_archetype_label: str
    selected_research_question: str
    topic_candidates: list[DeepResearchCandidate]
    reference_archetypes: list[dict[str, Any]]
    script_mandates: list[str]
    visual_mandates: list[str]
    monetization_hypothesis: str
    policy_positioning: str
    blocked_or_demoted: list[dict[str, Any]]


@dataclass(frozen=True)
class EditorialPlan:
    version: str
    topic_title: str
    angle_id: str
    angle_label: str
    core_question: str
    viewer_promise: str
    tone: str
    must_include: list[str]
    must_avoid: list[str]
    final_comment_question: str
    source_ids: list[str]


@dataclass(frozen=True)
class FactPackItem:
    fact_id: str
    item_type: str
    text: str
    source_ids: list[str]
    confidence: str
    risk: str
    usage_guidance: str


@dataclass(frozen=True)
class FactPack:
    version: str
    topic_title: str
    generated_at: str
    source_count: int
    trusted_source_count: int
    source_roles: dict[str, str | None]
    confirmed_facts: list[FactPackItem]
    reported_claims: list[FactPackItem]
    counterpoints: list[FactPackItem]
    unanswered_questions: list[FactPackItem]
    risk_phrases_to_avoid: list[str]
    gate_passed: bool
    blockers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RiskFlag:
    level: str
    reason: str
    requires_label: bool | None = None


@dataclass(frozen=True)
class RiskFlags:
    version: str
    topic_title: str
    generated_at: str
    election: RiskFlag
    aigc: RiskFlag
    defamation: RiskFlag
    copyright: RiskFlag
    public_importance: RiskFlag
    political_actor_monetization: RiskFlag
    manual_review_required: bool
    publish_blockers: list[str]
    safe_rewrite_notes: list[str]
    gate_passed: bool
    blockers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SourceCard:
    version: str
    topic_title: str
    source_name: str
    source_type: str
    published_at: str
    claim_boundary: str
    display_text: str
    source_url: str
    source_ids: list[str]
    gate_passed: bool
    blockers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ReferenceFit:
    version: str
    status: str
    topic_title: str
    format_id: str
    source_benchmark: str
    playback_qa: str
    route_when: list[str]
    selected_pattern_ids: list[str]
    selected_hook_ids: list[str]
    selected_scene_type_ids: list[str]
    selected_cta_ids: list[str]
    matched_terms: list[str]
    fit_score: int
    usage_notes: list[str]
    gate_passed: bool
    blockers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class AngleBrief:
    version: str
    topic_title: str
    format_id: str
    viewer_promise: str
    one_sentence_thesis: str
    audience_emotion: str
    share_reason: str
    comment_question: str
    follow_reason: str
    safe_provocation: str
    forbidden_angle: str
    source_fact_ids: list[str]
    gate_passed: bool
    blockers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class StoryboardSceneBrief:
    scene_id: int
    narrative_job: str
    evidence_item_ids: list[str]
    visual_job: str
    tts_job: str
    viewer_question: str
    required_new_information: str
    risk_controls: list[str]
    overlay_lane: str


@dataclass(frozen=True)
class StoryboardBrief:
    version: str
    topic_title: str
    format_id: str
    scene_count: int
    scenes: list[StoryboardSceneBrief]
    gate_passed: bool
    blockers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class SignalSnapshot:
    version: str
    collected_at: str
    sources: list[str]
    base_queries: list[str]
    item_count: int
    raw_items: list[dict[str, Any]]
    detected_terms: dict[str, list[str]]
    risk_terms: list[str]


@dataclass(frozen=True)
class SelectedScriptPlan:
    version: str
    variant_id: str
    selection_reason: str
    title: str
    format_id: str
    target_duration_sec: int
    scene_count: int
    gate_score: int
    readability_passed: bool
    publish_ready_score: int
    quality_scores: dict[str, int]
    blockers: list[str]
    script: dict[str, Any]


@dataclass(frozen=True)
class VisualScenePlan:
    scene_id: int
    prompt_basis: str
    image_need: str
    visual_role: str
    issue_type: str
    location: str
    camera: str
    required_anchors: list[str]
    avoid: list[str]
    diegetic_text: str
    diegetic_text_directive: str
    asset_provider: str | None
    asset_status: str | None
    asset_path: str | None
    prompt_lineage: dict[str, Any]


@dataclass(frozen=True)
class VisualPlan:
    version: str
    topic_title: str
    scene_count: int
    scenes: list[VisualScenePlan]


@dataclass(frozen=True)
class ContentFormatPlan:
    format_id: str
    objective: str
    target_duration_min_sec: int
    target_duration_max_sec: int
    scene_count_min: int
    scene_count_max: int
    min_visual_beats: int
    reward_eligible: bool
    upload_slot: str
    selection_reason: str
    master_image_min: int = 0
    master_image_max: int = 0
    max_seconds_per_master_image: float = 7.0
    visual_beats_per_minute: int = 22


@dataclass(frozen=True)
class VisualCadencePlan:
    version: str
    duration_sec: int
    script_scene_count: int
    master_image_min: int
    master_image_max: int
    target_master_images: int
    min_visual_beats: int
    target_visual_beats: int
    max_seconds_per_master_image: float
    visual_beats_per_minute: int
    rationale: list[str]


FORMAT_SPECS: dict[str, ContentFormatPlan] = {
    "evidence_briefing_75": ContentFormatPlan(
        format_id="evidence_briefing_75",
        objective="evidence_first_monetization_and_trust",
        target_duration_min_sec=60,
        target_duration_max_sec=95,
        scene_count_min=8,
        scene_count_max=12,
        min_visual_beats=24,
        reward_eligible=True,
        upload_slot="11:20",
        selection_reason="default evidence briefing: sourced claims, visible source card, and 60~95s Korean TTS retention target",
        master_image_min=10,
        master_image_max=12,
        max_seconds_per_master_image=7.0,
        visual_beats_per_minute=24,
    ),
    "growth_short": ContentFormatPlan(
        format_id="growth_short",
        objective="follower_acquisition",
        target_duration_min_sec=63,
        target_duration_max_sec=75,
        scene_count_min=9,
        scene_count_max=11,
        min_visual_beats=20,
        reward_eligible=True,
        upload_slot="08:10",
        selection_reason="high-hook one-minute format for discovery and reward eligibility",
        master_image_min=10,
        master_image_max=11,
        max_seconds_per_master_image=7.0,
        visual_beats_per_minute=24,
    ),
    "ranking_battle_65": ContentFormatPlan(
        format_id="ranking_battle_65",
        objective="ranking_reveal_comment_battle",
        target_duration_min_sec=60,
        target_duration_max_sec=78,
        scene_count_min=7,
        scene_count_max=10,
        min_visual_beats=20,
        reward_eligible=True,
        upload_slot="19:30",
        selection_reason="ranking-first format: immediate list reveal, compressed verdicts, and comment-choice finish",
        master_image_min=9,
        master_image_max=10,
        max_seconds_per_master_image=7.0,
        visual_beats_per_minute=24,
    ),
    "reward_deep": ContentFormatPlan(
        format_id="reward_deep",
        objective="creator_rewards_candidate",
        target_duration_min_sec=65,
        target_duration_max_sec=95,
        scene_count_min=9,
        scene_count_max=12,
        min_visual_beats=24,
        reward_eligible=True,
        upload_slot="11:20",
        selection_reason="one-minute-plus sourced explainer for watch-time and RPM signals",
        master_image_min=12,
        master_image_max=12,
        max_seconds_per_master_image=7.0,
        visual_beats_per_minute=26,
    ),
    "debate_followup": ContentFormatPlan(
        format_id="debate_followup",
        objective="comment_reactivation",
        target_duration_min_sec=63,
        target_duration_max_sec=90,
        scene_count_min=9,
        scene_count_max=12,
        min_visual_beats=20,
        reward_eligible=True,
        upload_slot="19:30",
        selection_reason="comment-driven one-minute follow-up format",
        master_image_min=10,
        master_image_max=12,
        max_seconds_per_master_image=7.0,
        visual_beats_per_minute=25,
    ),
    "narrative_confession": ContentFormatPlan(
        format_id="narrative_confession",
        objective="follow_growth_narrative_confession",
        target_duration_min_sec=63,
        target_duration_max_sec=82,
        scene_count_min=9,
        scene_count_max=11,
        min_visual_beats=20,
        reward_eligible=True,
        upload_slot="08:10",
        selection_reason="follow-growth narrative: personal stance shift, issue confession, and next-episode promise",
        master_image_min=10,
        master_image_max=11,
        max_seconds_per_master_image=7.0,
        visual_beats_per_minute=24,
    ),
    "reformed_briefing": ContentFormatPlan(
        format_id="reformed_briefing",
        objective="follow_growth_reformed_briefing",
        target_duration_min_sec=65,
        target_duration_max_sec=92,
        scene_count_min=9,
        scene_count_max=12,
        min_visual_beats=24,
        reward_eligible=True,
        upload_slot="11:20",
        selection_reason="reformed briefing: sourced context, actor/issue keyword, and explicit follow-through promise",
        master_image_min=12,
        master_image_max=12,
        max_seconds_per_master_image=7.0,
        visual_beats_per_minute=26,
    ),
}


def _format_master_image_min(plan: ContentFormatPlan) -> int:
    return max(1, int(plan.master_image_min or plan.scene_count_min))


def _format_master_image_max(plan: ContentFormatPlan) -> int:
    return max(_format_master_image_min(plan), int(plan.master_image_max or plan.scene_count_max))


def plan_visual_cadence(scenes: list["Scene"], format_plan: ContentFormatPlan | None = None) -> VisualCadencePlan:
    plan = format_plan or FORMAT_SPECS["reward_deep"]
    duration_sec = sum(max(0, int(scene.duration_sec)) for scene in scenes)
    scene_count = len(scenes)
    master_min = _format_master_image_min(plan)
    master_max = _format_master_image_max(plan)
    max_seconds_per_image = max(3.0, float(plan.max_seconds_per_master_image or 7.0))
    duration_target = math.ceil(duration_sec / max_seconds_per_image) if duration_sec else master_min
    long_scene_bonus = sum(1 for scene in scenes if scene.duration_sec >= 10)
    scene_floor = min(master_max, max(master_min, scene_count))
    target_master_images = min(master_max, max(master_min, duration_target, scene_floor))
    if long_scene_bonus and target_master_images < master_max:
        target_master_images = min(master_max, target_master_images + min(2, long_scene_bonus))

    beat_density = max(1, int(plan.visual_beats_per_minute or 22))
    duration_beat_target = math.ceil(duration_sec * beat_density / 60) if duration_sec else plan.min_visual_beats
    target_visual_beats = max(plan.min_visual_beats, duration_beat_target, target_master_images * 2)
    rationale = [
        f"duration_sec={duration_sec}",
        f"scene_count={scene_count}",
        f"duration_target_images={duration_target}",
        f"format_master_range={master_min}-{master_max}",
        f"beat_density_per_minute={beat_density}",
    ]
    if long_scene_bonus:
        rationale.append(f"long_scene_bonus={long_scene_bonus}")
    return VisualCadencePlan(
        version="visual_cadence_v1",
        duration_sec=duration_sec,
        script_scene_count=scene_count,
        master_image_min=master_min,
        master_image_max=master_max,
        target_master_images=target_master_images,
        min_visual_beats=plan.min_visual_beats,
        target_visual_beats=target_visual_beats,
        max_seconds_per_master_image=max_seconds_per_image,
        visual_beats_per_minute=beat_density,
        rationale=rationale,
    )


@dataclass(frozen=True)
class Scene:
    scene_id: int
    duration_sec: int
    title: str
    body: str
    visual: str
    on_screen_text: str


@dataclass(frozen=True)
class ScriptPackage:
    title: str
    caption: str
    hashtags: list[str]
    post_title: str
    post_body: str
    pinned_comment: str
    narration: str
    scenes: list[Scene]
    target_duration_sec: int
    sources: list[str]
    disclosure: str
    variant_id: str = "evidence_expose"


@dataclass(frozen=True)
class GateResult:
    passed: bool
    score: int
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    checks: dict[str, bool] = field(default_factory=dict)


@dataclass(frozen=True)
class ContentReview:
    passed: bool
    recommendation: str
    scores: dict[str, int]
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class PublishQualityResult:
    passed: bool
    selected_variant: str
    publish_ready_score: int
    scores: dict[str, int]
    blockers: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    variant_scores: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class ReadabilityResult:
    passed: bool
    checks: dict[str, bool]
    max_on_screen_chars: int
    max_narration_chars: int
    issues: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class VisualBrief:
    scene_id: int
    role: str
    issue_type: str
    visual_intent: str
    concrete_scene: str
    visual_anchor: list[str]
    location: str
    camera: str
    emotion: str
    palette: str
    treatment_id: str
    visual_treatment: str
    action_beat: str
    relevance_terms: list[str]
    diversity_tags: list[str]
    safety_constraints: list[str]
    shot_contract: list[str] = field(default_factory=list)
    forbidden_dominant_elements: list[str] = field(default_factory=list)
    scene_uniqueness_key: str = ""
    diegetic_text: str = ""
    diegetic_text_directive: str = ""
    render_style: str = ""


@dataclass(frozen=True)
class VisualQualityResult:
    passed: bool
    scores: dict[str, int]
    blockers: list[str] = field(default_factory=list)
    scene_scores: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class VisualAsset:
    scene_id: int
    provider: str
    status: str
    path: str | None
    prompt: str
    visual_brief: dict[str, Any] = field(default_factory=dict)
    visual_quality: dict[str, Any] = field(default_factory=dict)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ImageBudgetDecision:
    version: str
    requested_image_mode: str
    effective_image_mode: str
    requested_real_image_limit: int
    effective_real_image_limit: int
    allowed_external_generation: bool
    reasons: list[str]
    daily_real_image_limit: int
    daily_real_images_used: int
    min_publish_ready_score: int
    gate_passed: bool
    readability_passed: bool
    quality_passed: bool
    publish_ready_score: int


@dataclass(frozen=True)
class ContentScenePlan:
    scene_id: int
    script_role: str
    narrative_step: str
    viewer_question: str
    on_screen_text: str
    narration_goal: str
    evidence_need: str
    image_need: str
    visual_role: str
    issue_type: str
    location: str
    camera: str
    required_anchors: list[str]
    avoid: list[str]
    diegetic_text: str
    diegetic_text_directive: str
    source_ids: list[str]


@dataclass(frozen=True)
class ContentPlan:
    version: str
    topic_title: str
    format_id: str
    topic_selection_rationale: str
    editorial_frame: str
    key_question: str
    trend_clusters: list[dict[str, Any]]
    narrative_arc: list[str]
    source_requirements: list[str]
    risk_controls: list[str]
    image_plan: list[ContentScenePlan]


@dataclass(frozen=True)
class VisualBeat:
    scene_id: int
    beat_id: int
    start_sec: float
    duration_sec: float
    zoom_start: float
    zoom_end: float
    pan_x: int
    pan_y: int
    overlay: str


@dataclass(frozen=True)
class MobileVisualCheck:
    scene_id: int
    preview_path: str
    layout_id: str
    passed: bool
    headline_mobile_px: float
    body_mobile_px: float
    headline_line_count: int
    body_line_count: int
    headline_fits_box: bool
    body_fits_box: bool
    text_box_overflow: bool
    text_panel_coverage_pct: float
    text_right_rail_clear: bool
    text_above_bottom_ui: bool
    text_render_passed: bool
    preview_size: str


@dataclass(frozen=True)
class AudioAsset:
    provider: str
    status: str
    path: str
    notes: list[str] = field(default_factory=list)
    tts_text_path: str | None = None
    lint_path: str | None = None
    scene_timings: list[dict[str, Any]] = field(default_factory=list)


@dataclass(frozen=True)
class TTSPreprocessResult:
    text: str
    replacements: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    metrics: dict[str, int | float] = field(default_factory=dict)


@dataclass(frozen=True)
class SceneAudioTiming:
    scene_id: int
    original_duration_sec: int
    audio_duration_sec: float
    card_duration_sec: int
    silence_pad_sec: float
    audio_path: str
    padded_audio_path: str
    tts_text_path: str
    lint_path: str
    provider: str
    status: str
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TTSScenePlan:
    scene_id: int
    source_text: str
    tts_text: str
    tts_text_path: str | None
    lint_path: str | None
    provider: str | None
    status: str | None
    card_duration_sec: int | None
    audio_duration_sec: float | None
    warnings: list[str] = field(default_factory=list)
    replacements: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TTSPerformanceScenePlan:
    scene_id: int
    target_duration_sec: int
    pacing: str
    breath_group: str
    emphasis_terms: list[str]
    pronunciation_alias_terms: list[str]
    pause_after_sec: float
    delivery_note: str


@dataclass(frozen=True)
class TTSPerformancePlan:
    version: str
    voice_direction: str
    model_family: str
    language: str
    scene_plans: list[TTSPerformanceScenePlan]
    gate_passed: bool
    blockers: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class TTSPlan:
    version: str
    provider: str
    actual_provider: str
    status: str
    publish_candidate: bool
    voice: str
    model: str
    language_code: str
    output_format: str
    enable_logging: bool
    voice_settings: dict[str, float | bool]
    scene_texts: list[TTSScenePlan]
    warnings: list[str] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class RenderManifest:
    version: str
    run_id: str
    target_size: str
    fps: int
    codec: str
    video_bitrate: str
    scene_count: int
    duration_sec: int
    static_hold_images: bool
    transition_policy: str
    safe_zones: dict[str, Any]
    visual_motion: dict[str, Any]
    visual_cadence: dict[str, Any]
    artifacts: dict[str, str]
    gates: dict[str, Any]


@dataclass(frozen=True)
class UploadPlan:
    version: str
    run_id: str
    status: str
    required_status: str
    manifest_status: str
    caption: str
    post_title: str
    hashtags: list[str]
    aigc_label_required: bool
    schedule_time_local: str | None
    schedule_reason: str
    mp4_path: str
    blockers: list[str] = field(default_factory=list)
    stop_conditions: list[str] = field(default_factory=list)
    human_confirmation_required: bool = True


@dataclass(frozen=True)
class RenderArtifacts:
    mp4: str
    audio_path: str
    audio_provider: str
    audio_status: str
    storyboard: str
    mobile_preview_storyboard: str
    mobile_visual_checks: str
    asset_manifest: str
    fact_pack: str
    risk_flags: str
    source_card: str
    reference_fit: str
    angle_brief: str
    storyboard_brief: str
    signal_snapshot: str | None
    content_plan: str
    keyword_plan: str | None
    topic_pool: str | None
    topic_plan: str | None
    deep_research_report: str | None
    editorial_plan: str | None
    selected_script: str
    visual_plan: str
    tts_performance_plan: str
    tts_plan: str
    render_manifest: str
    upload_plan: str
    report_html: str
    manifest_json: str
    render_textfit_report: str | None = None


@dataclass(frozen=True)
class PipelineResult:
    run_id: str
    status: str
    topic: TopicCandidate
    format_plan: ContentFormatPlan
    script: ScriptPackage
    gate: GateResult
    readability: ReadabilityResult
    quality: PublishQualityResult
    review: ContentReview
    artifacts: RenderArtifacts


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def _latest_performance_feedback_source() -> Path | None:
    if DEFAULT_PERFORMANCE_FEEDBACK_PATH.exists():
        return DEFAULT_PERFORMANCE_FEEDBACK_PATH
    candidates = [
        *DEFAULT_PERFORMANCE_REPORT_DIR.glob("performance_feedback_*.json"),
        *DEFAULT_PERFORMANCE_REPORT_DIR.glob("performance_report_*.json"),
    ]
    if not candidates:
        return None
    return max(candidates, key=lambda path: path.stat().st_mtime)


def _feedback_body(data: dict[str, Any]) -> dict[str, Any]:
    if data.get("version") == "performance_feedback_v1":
        body = data.get("feedback", {})
        if isinstance(body, dict):
            return body
    body = data.get("feedback", {})
    return body if isinstance(body, dict) else {}


def load_performance_feedback(path: Path | None = None) -> dict[str, Any]:
    source_path = path or _latest_performance_feedback_source()
    if not source_path or not source_path.exists():
        return {"enabled": False, "reason": "no_performance_feedback"}
    try:
        data = json.loads(source_path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {"enabled": False, "reason": "invalid_performance_feedback", "path": str(source_path)}
    if not isinstance(data, dict):
        return {"enabled": False, "reason": "invalid_performance_feedback", "path": str(source_path)}
    body = _feedback_body(data)
    try:
        sample_count = int(data.get("sample_count", body.get("sample_count", 0)) or 0)
    except (TypeError, ValueError):
        sample_count = 0
    return {
        "enabled": sample_count > 0,
        "path": str(source_path),
        "mode": str(data.get("mode", "")),
        "sample_count": sample_count,
        "term_scores": body.get("term_scores", {}) if isinstance(body.get("term_scores", {}), dict) else {},
        "format_scores": body.get("format_scores", {}) if isinstance(body.get("format_scores", {}), dict) else {},
        "visual_scores": body.get("visual_scores", {}) if isinstance(body.get("visual_scores", {}), dict) else {},
        "positive_terms": body.get("positive_terms", []) if isinstance(body.get("positive_terms", []), list) else [],
        "negative_terms": body.get("negative_terms", []) if isinstance(body.get("negative_terms", []), list) else [],
        "notes": body.get("notes", []) if isinstance(body.get("notes", []), list) else [],
    }


def _performance_feedback_adjustment(text: str, feedback: dict[str, Any] | None, *, content_format: str | None = None) -> int:
    if not feedback or not feedback.get("enabled"):
        return 0
    adjustment = 0
    term_scores = feedback.get("term_scores", {})
    if isinstance(term_scores, dict):
        for term, raw_score in term_scores.items():
            if not str(term) or str(term) not in text:
                continue
            try:
                adjustment += int(raw_score)
            except (TypeError, ValueError):
                continue
    format_scores = feedback.get("format_scores", {})
    if content_format and isinstance(format_scores, dict):
        try:
            adjustment += int(format_scores.get(content_format, 0))
        except (TypeError, ValueError):
            pass
    return max(-40, min(40, adjustment))


def _hangul_count(text: str) -> int:
    return sum(1 for char in text if "\uac00" <= char <= "\ud7a3")


def _cjk_count(text: str) -> int:
    return sum(1 for char in text if "\u4e00" <= char <= "\u9fff")


def _text_integrity_issues(label: str, text: Any, *, korean_expected: bool = True) -> list[str]:
    value = str(text or "").strip()
    if not value:
        return [f"{label}:missing"]
    issues: list[str] = []
    if "\ufffd" in value:
        issues.append(f"{label}:replacement_character")
    if korean_expected and _hangul_count(value) < 2:
        issues.append(f"{label}:korean_text_missing")
    if korean_expected and _cjk_count(value) >= 4 and _cjk_count(value) > max(2, _hangul_count(value) // 4):
        issues.append(f"{label}:likely_mojibake_cjk_noise")
    if re.search(r"\?{3,}", value):
        issues.append(f"{label}:question_mark_noise")
    return issues


def _script_text_integrity_issues(script: dict[str, Any], format_plan: dict[str, Any] | None = None) -> list[str]:
    issues: list[str] = []
    for key in ["title", "caption", "post_title", "post_body", "pinned_comment", "narration"]:
        issues.extend(_text_integrity_issues(f"script.{key}", script.get(key)))
    hashtags = script.get("hashtags", [])
    if not isinstance(hashtags, list) or not hashtags:
        issues.append("script.hashtags:missing")
    else:
        joined_hashtags = " ".join(str(item) for item in hashtags)
        issues.extend(_text_integrity_issues("script.hashtags", joined_hashtags))
    scenes = script.get("scenes", [])
    expected_min_scenes = 9
    if isinstance(format_plan, dict):
        try:
            expected_min_scenes = int(format_plan.get("scene_count_min") or expected_min_scenes)
        except (TypeError, ValueError):
            expected_min_scenes = 9
    if not isinstance(scenes, list) or len(scenes) < expected_min_scenes:
        issues.append("script.scenes:too_few")
        return issues
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            issues.append(f"script.scenes[{index}]:invalid")
            continue
        issues.extend(_text_integrity_issues(f"script.scenes[{index}].body", scene.get("body")))
        issues.extend(_text_integrity_issues(f"script.scenes[{index}].on_screen_text", scene.get("on_screen_text")))
    issues.extend(_scene_headline_quality_issues(scenes))
    return issues


def _scene_headline_quality_issues(scenes: list[Any]) -> list[str]:
    issues: list[str] = []
    seen: dict[str, int] = {}
    banned_fragments = ["핵심 체크", "핵심 기준", " 체크", "포인트"]
    for index, scene in enumerate(scenes, start=1):
        if not isinstance(scene, dict):
            continue
        text = _clean_card_text(scene.get("on_screen_text"))
        compact = re.sub(r"\s+", "", text)
        for fragment in banned_fragments:
            if fragment in text:
                issues.append(f"script.scenes[{index}].on_screen_text:generic_headline:{fragment}")
        if compact in seen:
            issues.append(f"script.scenes[{index}].on_screen_text:duplicate_of_scene_{seen[compact]}")
        elif compact:
            seen[compact] = index
    return issues


def _script_headline_quote_format_fields(script: dict[str, Any]) -> list[str]:
    fields: list[str] = []
    for key in ["title", "caption", "post_title", "post_body", "pinned_comment", "narration"]:
        value = str(script.get(key, "") or "")
        if _contains_any(value, HEADLINE_QUOTE_FORMAT_BANNED_TERMS):
            fields.append(f"script.{key}")
    scenes = script.get("scenes", [])
    if isinstance(scenes, list):
        for index, scene in enumerate(scenes, start=1):
            if not isinstance(scene, dict):
                continue
            text = " ".join(str(scene.get(key, "") or "") for key in ["title", "body", "on_screen_text"])
            if _contains_any(text, HEADLINE_QUOTE_FORMAT_BANNED_TERMS):
                fields.append(f"script.scenes[{index}]")
    return fields


def _script_has_headline_quote_format(script: ScriptPackage) -> bool:
    return bool(_script_headline_quote_format_fields(asdict(script)))


def validate_manifest_for_upload(manifest: dict[str, Any]) -> dict[str, Any]:
    """Strict final gate shared by Chrome Extension, CLI upload, and HA workers."""

    technical_blockers: list[str] = []
    quality_blockers: list[str] = []
    gate = manifest.get("gate") if isinstance(manifest.get("gate"), dict) else {}
    readability = manifest.get("readability") if isinstance(manifest.get("readability"), dict) else {}
    review = manifest.get("review") if isinstance(manifest.get("review"), dict) else {}
    quality = manifest.get("quality") if isinstance(manifest.get("quality"), dict) else {}
    audio = manifest.get("audio_asset") if isinstance(manifest.get("audio_asset"), dict) else {}
    script = manifest.get("script") if isinstance(manifest.get("script"), dict) else {}
    artifacts = manifest.get("artifacts") if isinstance(manifest.get("artifacts"), dict) else {}
    fact_pack = manifest.get("fact_pack") if isinstance(manifest.get("fact_pack"), dict) else {}
    risk_flags = manifest.get("risk_flags") if isinstance(manifest.get("risk_flags"), dict) else {}
    source_card = manifest.get("source_card") if isinstance(manifest.get("source_card"), dict) else {}
    reference_fit = manifest.get("reference_fit") if isinstance(manifest.get("reference_fit"), dict) else {}
    angle_brief = manifest.get("angle_brief") if isinstance(manifest.get("angle_brief"), dict) else {}
    storyboard_brief = manifest.get("storyboard_brief") if isinstance(manifest.get("storyboard_brief"), dict) else {}
    tts_performance_plan = (
        manifest.get("tts_performance_plan") if isinstance(manifest.get("tts_performance_plan"), dict) else {}
    )
    tts_plan = manifest.get("tts_plan") if isinstance(manifest.get("tts_plan"), dict) else {}

    if gate.get("passed") is not True:
        technical_blockers.append("policy_gate_not_passed")
    if readability.get("passed") is not True:
        technical_blockers.append("readability_not_passed")
    if review.get("passed") is not True:
        technical_blockers.append("content_review_not_passed")
    if audio.get("provider") != "elevenlabs" or audio.get("status") != "generated":
        technical_blockers.append("elevenlabs_audio_not_generated")
    if not tts_plan:
        technical_blockers.append("tts_plan_missing")
    elif tts_plan.get("enable_logging") is not False:
        technical_blockers.append("elevenlabs_zero_retention_not_confirmed")
    elif not _manifest_confirms_elevenlabs_history_clear(manifest):
        technical_blockers.append("elevenlabs_history_not_verified_clear")
    if manifest.get("synced_duration_matches_format") is not True:
        technical_blockers.append("duration_not_synced_to_format")

    mobile_checks = manifest.get("mobile_visual_checks")
    if manifest.get("mobile_visual_passed") is not True:
        technical_blockers.append("mobile_visual_not_passed")
    if not isinstance(mobile_checks, list) or not mobile_checks:
        technical_blockers.append("mobile_visual_checks_missing")
    else:
        for index, check in enumerate(mobile_checks, start=1):
            if not isinstance(check, dict):
                technical_blockers.append(f"mobile_visual_check_{index}_invalid")
                continue
            if check.get("passed") is not True:
                technical_blockers.append(f"mobile_visual_check_{index}_not_passed")
            if check.get("text_render_passed") is not True:
                technical_blockers.append(f"mobile_visual_check_{index}_text_render_not_passed")
            if "text_panel_coverage_pct" in check:
                try:
                    coverage = float(check.get("text_panel_coverage_pct"))
                except (TypeError, ValueError):
                    coverage = MAX_TEXT_PANEL_COVERAGE_PCT + 1
                if coverage > MAX_TEXT_PANEL_COVERAGE_PCT:
                    technical_blockers.append(f"mobile_visual_check_{index}_text_panel_too_large")

    if not artifacts.get("mp4"):
        technical_blockers.append("mp4_artifact_missing")
    required_artifacts = [
        "fact_pack",
        "risk_flags",
        "source_card",
        "reference_fit",
        "angle_brief",
        "storyboard_brief",
        "tts_performance_plan",
    ]
    for artifact_name in required_artifacts:
        if not artifacts.get(artifact_name):
            technical_blockers.append(f"{artifact_name}_artifact_missing")
    for gate_name, gate_doc in [
        ("fact_pack", fact_pack),
        ("risk_flags", risk_flags),
        ("source_card", source_card),
        ("reference_fit", reference_fit),
        ("angle_brief", angle_brief),
        ("storyboard_brief", storyboard_brief),
        ("tts_performance_plan", tts_performance_plan),
    ]:
        if gate_doc.get("gate_passed") is not True:
            technical_blockers.append(f"{gate_name}_not_passed")
    format_plan = manifest.get("format_plan") if isinstance(manifest.get("format_plan"), dict) else {}
    technical_blockers.extend(_script_text_integrity_issues(script, format_plan))
    headline_quote_fields = _script_headline_quote_format_fields(script)
    if headline_quote_fields:
        technical_blockers.append(f"headline_quote_format_banned:{','.join(headline_quote_fields)}")

    if quality.get("passed") is not True:
        quality_blockers.append("publish_quality_not_passed")

    upload_ready = not technical_blockers
    publish_ready = upload_ready and not quality_blockers
    return {
        "upload_ready": upload_ready,
        "publish_ready": publish_ready,
        "status": "publish_ready" if publish_ready else ("upload_ready" if upload_ready else "needs_revision"),
        "technical_blockers": technical_blockers,
        "quality_blockers": quality_blockers,
        "blockers": [*technical_blockers, *quality_blockers],
    }


def load_sources() -> dict[str, Source]:
    raw = _load_json(PACKAGE_DIR / "policy" / "source_registry.json")
    return {item["source_id"]: Source(**item) for item in raw["sources"]}


def collect_topic(style: dict[str, Any]) -> TopicCandidate:
    """Build one configured fallback topic from local strategy data."""
    raw_claims = DEFAULT_TOPIC_STRATEGY.get("claims", [])
    if not isinstance(raw_claims, list):
        raise RuntimeError("Strategy config key must be a list: default_topic.claims")
    claims = [
        Claim(
            text=str(row.get("text", "")),
            source_ids=[str(source_id) for source_id in row.get("source_ids", [])],
        )
        for row in raw_claims
        if isinstance(row, dict)
    ]
    return TopicCandidate(
        title=str(DEFAULT_TOPIC_STRATEGY.get("title", "")),
        angle=str(DEFAULT_TOPIC_STRATEGY.get("angle", "")),
        slot=str(DEFAULT_TOPIC_STRATEGY.get("slot", "")),
        target_duration_sec=_strategy_int(DEFAULT_TOPIC_STRATEGY, "target_duration_sec", 75),
        claims=claims,
        source_ids=sorted({sid for claim in claims for sid in claim.source_ids}),
    )


def _clean_news_title(raw_title: str) -> tuple[str, str]:
    title = html.unescape(_clean_card_text(raw_title))
    publisher = ""
    if " - " in title:
        title, publisher = title.rsplit(" - ", 1)
    title = re.sub(r"^\[[^\]]+\]\s*", "", title).strip()
    return title, publisher.strip()


def _parse_pub_date(raw: str | None) -> dt.datetime:
    if not raw:
        return dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3)
    try:
        parsed = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError):
        return dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=3)
    if parsed.tzinfo is None:
        parsed = parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _publisher_is_trusted(publisher: str) -> bool:
    return any(source in publisher for source in HOT_TOPIC_TRUSTED_SOURCES)


def _topic_tokens(text: str) -> set[str]:
    tokens = re.findall(r"[\uac00-\ud7a3A-Za-z0-9]{2,}", text.lower())
    return {token for token in tokens if len(token) >= 2}


def _specific_topic_tokens(text: str) -> set[str]:
    return {
        token
        for token in _topic_tokens(text)
        if len(token) >= 3 and token not in HOT_TOPIC_BROAD_CLUSTER_TOKENS
    }


def _has_specific_topic_overlap(left: str, right: str) -> bool:
    left_specific = _specific_topic_tokens(left)
    if not left_specific:
        left_tokens = _topic_tokens(left) - HOT_TOPIC_BROAD_CLUSTER_TOKENS
        right_tokens = _topic_tokens(right) - HOT_TOPIC_BROAD_CLUSTER_TOKENS
        return bool(left_tokens and left_tokens & right_tokens)
    return bool(left_specific & _specific_topic_tokens(right))


def _topic_overlap_score(left: str, right: str) -> int:
    priority_terms = list(dict.fromkeys([
        *SEARCH_VALUE_PRIORITY_TERMS,
        *HOT_TOPIC_LEFT_AUDIENCE_TERMS,
        *HOT_TOPIC_TARGET_TERMS,
    ]))
    score = sum(3 for term in priority_terms if term and term in left and term in right)
    token_overlap = _topic_tokens(left) & _topic_tokens(right)
    score += min(8, len(token_overlap) * 2)
    return score


def _cluster_support_count(item: HotTopicItem, candidates: list[HotTopicItem]) -> int:
    return sum(
        1
        for other in candidates
        if other.title != item.title
        and _has_specific_topic_overlap(item.title, other.title)
        and _topic_overlap_score(item.title, other.title) >= 5
    )


def _select_supporting_hot_topics(
    selected: HotTopicItem,
    ranked: list[HotTopicItem],
    *,
    max_items: int = 4,
) -> list[HotTopicItem]:
    support_rows: list[tuple[int, HotTopicItem]] = []
    for item in ranked:
        if item.title == selected.title:
            continue
        if not _has_specific_topic_overlap(selected.title, item.title):
            continue
        overlap = _topic_overlap_score(selected.title, item.title)
        query_bonus = _topic_score_weight("same_query_support_bonus", 2) if item.query == selected.query else 0
        trust_bonus = _topic_score_weight("trusted_support_bonus", 1) if _publisher_is_trusted(item.publisher) else 0
        support_score = overlap + query_bonus + trust_bonus
        if support_score >= _topic_score_weight("cluster_overlap_minimum", 6) or (
            item.query == selected.query and overlap >= _topic_score_weight("same_query_overlap_minimum", 4)
        ):
            support_rows.append((support_score, item))
    support_rows.sort(key=lambda row: (row[0], row[1].score, row[1].published_at), reverse=True)
    return [item for _, item in support_rows[:max_items]]


def _topic_score_weight(name: str, fallback: int) -> int:
    return HOT_TOPIC_SCORES.get(name, fallback)


def _keyword_score_weight(name: str, fallback: int) -> int:
    return KEYWORD_SCORING.get(name, fallback)


def _keyword_limit(name: str, fallback: int) -> int:
    return KEYWORD_LIMITS.get(name, fallback)


def _keyword_tokens(text: str) -> list[str]:
    tokens = re.findall(r"[0-9A-Za-z가-힣]{2,}", text)
    return [
        token
        for token in tokens
        if token not in KEYWORD_STOPWORDS and token not in HOT_TOPIC_BROAD_CLUSTER_TOKENS
    ]


def _keyword_phrases_from_title(title: str, basket: dict[str, Any]) -> set[str]:
    seeds = [str(term) for term in basket.get("seeds", []) if str(term).strip()]
    modifiers = [str(term) for term in basket.get("modifiers", []) if str(term).strip()]
    tokens = _keyword_tokens(title)
    phrases: set[str] = set()
    for seed in seeds:
        if seed in title:
            phrases.add(seed)
            for modifier in modifiers:
                if modifier in title:
                    phrases.add(f"{seed} {modifier}")
    for modifier in modifiers:
        if modifier in title:
            phrases.add(modifier)
    for left, right in zip(tokens, tokens[1:]):
        if left in KEYWORD_BAD_PHRASE_LEADING_TERMS:
            continue
        phrase = f"{left} {right}"
        if any(seed in phrase for seed in seeds) or any(modifier in phrase for modifier in modifiers):
            phrases.add(phrase)
    return {phrase for phrase in phrases if len(phrase.replace(" ", "")) >= 2}


def _score_keyword_candidate(
    keyword: str,
    basket: dict[str, Any],
    supporting_items: list[HotTopicItem],
    performance_feedback: dict[str, Any] | None = None,
) -> KeywordCandidate:
    seeds = [str(term) for term in basket.get("seeds", []) if str(term).strip()]
    modifiers = [str(term) for term in basket.get("modifiers", []) if str(term).strip()]
    intents = [str(term) for term in basket.get("intents", []) if str(term).strip()]
    matched_seeds = [seed for seed in seeds if seed in keyword]
    matched_modifiers = [modifier for modifier in modifiers if modifier in keyword]
    matched_high_intent = [term for term in KEYWORD_HIGH_INTENT_TERMS if term in keyword]
    risk_terms = [term for term in HOT_TOPIC_RISK_TERMS if term in keyword]
    trusted_support = sum(1 for item in supporting_items if _publisher_is_trusted(item.publisher))
    support_count = len(supporting_items)
    score = _keyword_score_weight("base", 20)
    score += len(matched_seeds) * _keyword_score_weight("seed_match", 14)
    score += len(matched_modifiers) * _keyword_score_weight("modifier_match", 10)
    score += len(matched_high_intent) * _keyword_score_weight("high_intent_match", 12)
    score += support_count * _keyword_score_weight("news_support", 7)
    score += trusted_support * _keyword_score_weight("trusted_source", 4)
    score += _keyword_score_weight("specific_phrase", 8) if " " in keyword else 0
    if risk_terms:
        score += _keyword_score_weight("risk_penalty", -18)
    if not matched_seeds and not matched_modifiers and support_count <= 1:
        score += _keyword_score_weight("generic_penalty", -12)
    generic_single = " " not in keyword and keyword in KEYWORD_GENERIC_SINGLE_TERMS and not matched_seeds
    if generic_single:
        score += _keyword_score_weight("generic_penalty", -12)
        score = min(score, _keyword_score_weight("generic_single_cap", 62))
    rationale = [
        f"support={support_count}",
        f"seeds={','.join(matched_seeds) or 'none'}",
        f"modifiers={','.join(matched_modifiers) or 'none'}",
        f"high_intent={','.join(matched_high_intent) or 'none'}",
    ]
    if risk_terms:
        rationale.append(f"risk={','.join(risk_terms)}")
    if generic_single:
        rationale.append("generic_single=auxiliary_only")
    feedback_delta = _performance_feedback_adjustment(keyword, performance_feedback)
    if feedback_delta:
        score += feedback_delta
        rationale.append(f"performance_feedback={feedback_delta:+d}")
    return KeywordCandidate(
        keyword=keyword,
        basket_id=str(basket.get("basket_id", "")),
        intent=intents[0] if intents else str(basket.get("basket_id", "")),
        score=max(0, score),
        support_count=support_count,
        matched_seeds=matched_seeds,
        matched_modifiers=matched_modifiers,
        matched_high_intent_terms=matched_high_intent,
        risk_terms=risk_terms,
        source_queries=sorted({item.query for item in supporting_items if item.query}),
        rationale=rationale,
    )


def build_keyword_plan(
    seed_items: list[HotTopicItem],
    performance_feedback: dict[str, Any] | None = None,
) -> KeywordPlan:
    limited_items = seed_items[: _keyword_limit("max_seed_items", 36)]
    candidates: dict[tuple[str, str], list[HotTopicItem]] = {}
    for basket in KEYWORD_SEED_BASKETS:
        for seed in [str(term) for term in basket.get("seeds", []) if str(term).strip()]:
            candidates.setdefault((seed, str(basket.get("basket_id", ""))), [])
        for item in limited_items:
            phrases = _keyword_phrases_from_title(item.title, basket)
            for phrase in phrases:
                candidates.setdefault((phrase, str(basket.get("basket_id", ""))), []).append(item)

    scored: list[KeywordCandidate] = []
    basket_by_id = {str(row.get("basket_id", "")): row for row in KEYWORD_SEED_BASKETS}
    for (keyword, basket_id), supporting_items in candidates.items():
        basket = basket_by_id.get(basket_id, {})
        scored.append(_score_keyword_candidate(keyword, basket, supporting_items, performance_feedback))
    scored.sort(key=lambda item: (item.score, item.support_count, len(item.keyword)), reverse=True)

    selected = scored[: _keyword_limit("max_selected_keywords", 8)]
    rejected = scored[
        _keyword_limit("max_selected_keywords", 8) : _keyword_limit("max_selected_keywords", 8)
        + _keyword_limit("max_rejected_keywords", 12)
    ]
    expanded_queries: list[str] = []
    for query in KEYWORD_BASE_QUERIES:
        if query not in expanded_queries:
            expanded_queries.append(query)
    for candidate in selected:
        for template in KEYWORD_QUERY_TEMPLATES:
            query = _format_prompt_template(template, {"keyword": candidate.keyword}).strip()
            if query and query not in expanded_queries:
                expanded_queries.append(query)
            if len(expanded_queries) >= _keyword_limit("max_expanded_queries", 18):
                break
        if len(expanded_queries) >= _keyword_limit("max_expanded_queries", 18):
            break
    if not expanded_queries:
        expanded_queries = HOT_TOPIC_QUERIES[: _keyword_limit("max_expanded_queries", 18)]
    return KeywordPlan(
        version=str(KEYWORD_STRATEGY.get("version", "keyword_research_v1")),
        base_queries=KEYWORD_BASE_QUERIES,
        expanded_queries=expanded_queries,
        selected_keywords=selected,
        rejected_keywords=rejected,
        scoring_notes=[
            "base_queries collect broad recent public signals",
            "seed baskets define attention surfaces and safety boundaries",
            "news titles expand concrete issue keywords before RSS topic scoring",
            (
                f"performance_feedback applied from {performance_feedback.get('path', 'memory')}"
                if performance_feedback and performance_feedback.get("enabled")
                else "performance_feedback inactive"
            ),
        ],
    )


def build_signal_snapshot(seed_items: list[HotTopicItem]) -> SignalSnapshot:
    combined_text = " ".join(item.title for item in seed_items)
    seed_terms = [
        str(term)
        for basket in KEYWORD_SEED_BASKETS
        for term in basket.get("seeds", [])
        if str(term).strip() and str(term) in combined_text
    ]
    modifier_terms = [
        str(term)
        for basket in KEYWORD_SEED_BASKETS
        for term in basket.get("modifiers", [])
        if str(term).strip() and str(term) in combined_text
    ]
    high_intent_terms = [term for term in KEYWORD_HIGH_INTENT_TERMS if term in combined_text]
    risk_terms = [term for term in HOT_TOPIC_RISK_TERMS if term in combined_text]
    raw_items = [
        {
            "title": item.title,
            "publisher": item.publisher,
            "url": item.url,
            "published_at": item.published_at,
            "query": item.query,
            "score": item.score,
            "trusted_source": _publisher_is_trusted(item.publisher),
        }
        for item in seed_items
    ]
    return SignalSnapshot(
        version="signal_collection_v1",
        collected_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        sources=["google_news_rss"],
        base_queries=KEYWORD_BASE_QUERIES,
        item_count=len(seed_items),
        raw_items=raw_items,
        detected_terms={
            "seed_terms": sorted(set(seed_terms)),
            "modifier_terms": sorted(set(modifier_terms)),
            "high_intent_terms": sorted(set(high_intent_terms)),
            "queries": sorted({item.query for item in seed_items if item.query}),
        },
        risk_terms=sorted(set(risk_terms)),
    )


def _keywords_for_topic_title(title: str, keyword_plan: KeywordPlan) -> list[str]:
    matched = [
        candidate.keyword
        for candidate in keyword_plan.selected_keywords
        if candidate.keyword in title
        or (
            _has_specific_topic_overlap(candidate.keyword, title)
            and _topic_overlap_score(candidate.keyword, title) >= 5
        )
    ]
    if matched:
        return matched[:6]
    title_terms = [term for term in SEARCH_VALUE_PRIORITY_TERMS if term and term in title]
    return list(dict.fromkeys(title_terms))[:5]


def _topic_candidate_risk(title: str) -> str:
    if any(term in title for term in HOT_TOPIC_RISK_TERMS):
        return "high"
    if any(term in title for term in ["선거", "대선", "투표", "여론조사", "후보"]):
        return "medium"
    if any(term in title for term in ["의혹", "특검", "수사", "압수수색"]):
        return "medium"
    return "low"


def _topic_format_hint(item: HotTopicItem, support_count: int) -> str:
    if support_count >= 2 and item.score >= 80:
        return "reward_deep"
    if any(term in item.title for term in ["반박", "논란", "공방", "해명"]):
        return "debate_followup"
    return "growth_short"


def build_topic_pool(ranked_items: list[HotTopicItem], keyword_plan: KeywordPlan) -> TopicPool:
    candidates: list[TopicPoolCandidate] = []
    for index, item in enumerate(ranked_items[:12], start=1):
        support_count = _cluster_support_count(item, ranked_items)
        trusted = 1 if _publisher_is_trusted(item.publisher) else 0
        risk = _topic_candidate_risk(item.title)
        recency_score = min(100, max(0, item.score))
        source_score = min(100, 40 + support_count * 12 + trusted * 8)
        search_score = min(100, 45 + len(_keywords_for_topic_title(item.title, keyword_plan)) * 12)
        risk_score = 45 if risk == "high" else (70 if risk == "medium" else 88)
        candidates.append(
            TopicPoolCandidate(
                topic_id=f"topic_{index:03d}",
                title=item.title,
                query=item.query,
                publisher=item.publisher,
                url=item.url,
                published_at=item.published_at,
                keywords=_keywords_for_topic_title(item.title, keyword_plan),
                support_count=support_count,
                risk=risk,
                format_hint=_topic_format_hint(item, support_count),
                score=item.score,
                score_components={
                    "recency_heat": recency_score,
                    "source_support": source_score,
                    "search_value": search_score,
                    "policy_safety": risk_score,
                },
            )
        )
    return TopicPool(version="topic_pool_v1", candidates=candidates)


def build_topic_plan(
    selected: HotTopicItem,
    supporting: list[HotTopicItem],
    topic_pool: TopicPool,
    keyword_plan: KeywordPlan,
) -> TopicPlan:
    selected_candidate = next(
        (candidate for candidate in topic_pool.candidates if candidate.title == selected.title),
        topic_pool.candidates[0] if topic_pool.candidates else None,
    )
    keywords = _keywords_for_topic_title(selected.title, keyword_plan)
    source_support = min(100, 45 + (len(supporting) + 1) * 11)
    search_value = min(100, 50 + len(keywords) * 10)
    policy_safety = 45 if _topic_candidate_risk(selected.title) == "high" else 76
    visual_potential = 88 if any(term in selected.title for term in ["압수수색", "감사원", "국회", "검찰", "관저"]) else 72
    blocked = [
        {
            "topic_id": candidate.topic_id,
            "title": candidate.title,
            "reason": "low_score_or_high_policy_risk",
        }
        for candidate in topic_pool.candidates
        if candidate.title != selected.title and (candidate.score < 45 or candidate.risk == "high")
    ][:6]
    selection_reason = (
        f"selected by heat_score={selected.score}, support_sources={len(supporting) + 1}, "
        f"keywords={', '.join(keywords) or 'none'}"
    )
    return TopicPlan(
        version="topic_plan_v1",
        selected_topic_id=selected_candidate.topic_id if selected_candidate else "topic_000",
        selected_title=selected.title,
        selection_reason=selection_reason,
        scores={
            "recency": min(100, selected.score),
            "source_support": source_support,
            "search_value": search_value,
            "visual_potential": visual_potential,
            "policy_safety": policy_safety,
        },
        support_count=len(supporting) + 1,
        keywords=keywords,
        blocked_candidates=blocked,
    )


def _deep_research_weight(name: str, fallback: int = 0) -> int:
    return DEEP_RESEARCH_SCORING.get(name, fallback)


def _deep_research_text(candidate: TopicPoolCandidate) -> str:
    return " ".join(
        [
            candidate.title,
            candidate.query,
            candidate.publisher,
            " ".join(candidate.keywords),
        ]
    ).casefold()


def _deep_research_terms_in_text(terms: list[str], text: str) -> list[str]:
    return [term for term in terms if term.casefold() in text]


def _deep_research_progressive_terms(key: str) -> list[str]:
    values = DEEP_RESEARCH_PROGRESSIVE_REACTION.get(key, [])
    if not isinstance(values, list):
        return []
    return [str(term) for term in values if str(term).strip()]


def _deep_research_today_relevance_score(today_memory_terms: list[str], heat: int) -> int:
    score = min(72, max(0, heat - 20))
    if today_memory_terms:
        score = max(score, min(100, 48 + len(today_memory_terms) * 14))
    today_key = str(DEEP_RESEARCH_PROGRESSIVE_REACTION.get("civic_memory_month_day", "")).strip()
    if today_key and dt.datetime.now(SEOUL_TZ).strftime("%m-%d") == today_key and today_memory_terms:
        score += _deep_research_weight("civic_memory_day_bonus", 22)
    return min(100, score)


def _deep_research_archetype(candidate: TopicPoolCandidate) -> tuple[dict[str, Any], list[str]]:
    text = _deep_research_text(candidate)
    best: dict[str, Any] | None = None
    best_terms: list[str] = []
    for row in DEEP_RESEARCH_ARCHETYPES:
        terms = [str(term) for term in row.get("match_terms", []) if str(term).strip()]
        matched = _deep_research_terms_in_text(terms, text)
        if len(matched) > len(best_terms):
            best = row
            best_terms = matched
    if best is None:
        fallback_id = str(DEEP_RESEARCH_STRATEGY.get("default_archetype_id", "receipts_then_missing_answer"))
        best = next(
            (row for row in DEEP_RESEARCH_ARCHETYPES if str(row.get("archetype_id", "")) == fallback_id),
            DEEP_RESEARCH_ARCHETYPES[0] if DEEP_RESEARCH_ARCHETYPES else {},
        )
    return best, best_terms


def _deep_research_primary_term(candidate: TopicPoolCandidate) -> str:
    for keyword in candidate.keywords:
        if keyword and (keyword in candidate.title or _has_specific_topic_overlap(keyword, candidate.title)):
            return keyword
    for term in SEARCH_VALUE_PRIORITY_TERMS:
        if term in candidate.title:
            return term
    for basket in ("identity_terms", "accountability_terms", "today_memory_terms"):
        for term in _deep_research_progressive_terms(basket):
            if term in candidate.title:
                return term
    title = _clean_card_text(candidate.title)
    return _compact_card_text(title, 16) if title else candidate.query


def _deep_research_public_archetypes() -> list[dict[str, Any]]:
    public_rows: list[dict[str, Any]] = []
    for row in DEEP_RESEARCH_ARCHETYPES:
        public_rows.append(
            {
                "archetype_id": str(row.get("archetype_id", "")),
                "label": str(row.get("label", "")),
                "match_terms": [str(term) for term in row.get("match_terms", []) if str(term).strip()],
                "hook_formulas": [str(item) for item in row.get("hook_formulas", []) if str(item).strip()],
                "script_arc": [str(item) for item in row.get("script_arc", []) if str(item).strip()],
                "visual_sequence": [str(item) for item in row.get("visual_sequence", []) if str(item).strip()],
            }
        )
    return public_rows


def _deep_research_candidate(
    candidate: TopicPoolCandidate,
    keyword_plan: KeywordPlan,
    performance_feedback: dict[str, Any] | None,
) -> DeepResearchCandidate:
    text = _deep_research_text(candidate)
    progressive_text = " ".join([candidate.title, " ".join(candidate.keywords)]).casefold()
    archetype, matched_archetype_terms = _deep_research_archetype(candidate)
    tension_terms = _deep_research_terms_in_text(DEEP_RESEARCH_TENSION_TERMS, text)
    evidence_terms = _deep_research_terms_in_text(DEEP_RESEARCH_EVIDENCE_TERMS, text)
    cinematic_terms = _deep_research_terms_in_text(DEEP_RESEARCH_CINEMATIC_TERMS, text)
    comment_terms = _deep_research_terms_in_text(DEEP_RESEARCH_COMMENT_TERMS, text)
    identity_terms = _deep_research_terms_in_text(_deep_research_progressive_terms("identity_terms"), progressive_text)
    accountability_terms = _deep_research_terms_in_text(
        _deep_research_progressive_terms("accountability_terms"), progressive_text
    )
    hard_accountability_terms = _deep_research_terms_in_text(
        _deep_research_progressive_terms("hard_accountability_terms"), progressive_text
    )
    friendly_terms = _deep_research_terms_in_text(_deep_research_progressive_terms("friendly_terms"), progressive_text)
    anger_terms = _deep_research_terms_in_text(_deep_research_progressive_terms("anger_terms"), progressive_text)
    counter_frame_terms = _deep_research_terms_in_text(_deep_research_progressive_terms("counter_frame_terms"), progressive_text)
    today_memory_terms = _deep_research_terms_in_text(_deep_research_progressive_terms("today_memory_terms"), progressive_text)
    selected_keyword_terms = [
        keyword.keyword
        for keyword in keyword_plan.selected_keywords
        if keyword.keyword.casefold() in text
    ]
    positive_terms = []
    if performance_feedback and isinstance(performance_feedback.get("positive_terms"), list):
        positive_terms = [
            str(term)
            for term in performance_feedback.get("positive_terms", [])
            if str(term).strip() and str(term).casefold() in text
        ]

    source_density = min(
        100,
        38
        + candidate.support_count * _deep_research_weight("source_density_per_support", 12)
        + (_deep_research_weight("trusted_source_bonus", 8) if _publisher_is_trusted(candidate.publisher) else 0),
    )
    search_value = max(
        int(candidate.score_components.get("search_value", 0)),
        min(100, 42 + len(selected_keyword_terms) * _deep_research_weight("keyword_match_bonus", 8)),
    )
    reference_fit = min(
        100,
        38 + len(matched_archetype_terms) * _deep_research_weight("reference_match_bonus", 12),
    )
    narrative_tension = min(
        100,
        34 + len(tension_terms) * _deep_research_weight("tension_term_bonus", 8) + candidate.support_count * 3,
    )
    evidence_density = min(
        100,
        32
        + len(evidence_terms) * _deep_research_weight("evidence_term_bonus", 8)
        + min(20, candidate.support_count * 5),
    )
    cinematic_sceneability = min(
        100,
        36
        + len(cinematic_terms) * _deep_research_weight("cinematic_term_bonus", 7)
        + min(18, len(archetype.get("visual_sequence", [])) * 2),
    )
    comment_potential = min(
        100,
        36
        + len(comment_terms) * _deep_research_weight("comment_term_bonus", 6)
        + min(18, len(tension_terms) * 3),
    )
    follower_conversion = min(100, 38 + reference_fit // 5 + comment_potential // 5 + search_value // 8)
    monetization_fit = min(
        100,
        46
        + (12 if candidate.format_hint == "reward_deep" else 4)
        + (
            _deep_research_weight("monetization_min_support_bonus", 8)
            if candidate.support_count >= DEEP_RESEARCH_MINIMUMS.get("min_support_for_reward_deep", 2)
            else 0
        )
        + len(positive_terms) * _deep_research_weight("performance_term_bonus", 4),
    )
    policy_safety = {"high": 42, "medium": 74, "low": 92}.get(candidate.risk, 72)
    heat = min(100, max(0, candidate.score))
    progressive_reaction = min(
        100,
        30
        + len(identity_terms) * _deep_research_weight("progressive_identity_bonus", 9)
        + len(accountability_terms) * _deep_research_weight("accountability_term_bonus", 7)
        + len(hard_accountability_terms) * _deep_research_weight("hard_accountability_term_bonus", 8)
        + len(anger_terms) * _deep_research_weight("anger_term_bonus", 7)
        + len(counter_frame_terms) * _deep_research_weight("counter_frame_bonus", 5)
        + min(12, candidate.support_count * 3),
    )
    if friendly_terms and not hard_accountability_terms:
        progressive_reaction = max(
            0,
            progressive_reaction + _deep_research_weight("friendly_only_penalty", -18),
        )
    today_relevance = _deep_research_today_relevance_score(today_memory_terms, heat)

    components = {
        "heat": heat,
        "source_density": source_density,
        "search_value": search_value,
        "reference_fit": reference_fit,
        "progressive_reaction": progressive_reaction,
        "today_relevance": today_relevance,
        "narrative_tension": narrative_tension,
        "evidence_density": evidence_density,
        "cinematic_sceneability": cinematic_sceneability,
        "comment_potential": comment_potential,
        "follower_conversion": follower_conversion,
        "monetization_fit": monetization_fit,
        "policy_safety": policy_safety,
    }
    total_weight = sum(DEEP_RESEARCH_DIMENSION_WEIGHTS.get(key, 0) for key in components) or 1
    weighted_total = round(
        sum(score * DEEP_RESEARCH_DIMENSION_WEIGHTS.get(key, 0) for key, score in components.items())
        / total_weight
    )
    risk_adjustment = 0
    if candidate.risk == "medium":
        risk_adjustment = _deep_research_weight("medium_policy_penalty", -7)
    elif candidate.risk == "high":
        risk_adjustment = _deep_research_weight("high_policy_penalty", -38)
    total_score = max(
        0,
        min(
            100,
            weighted_total
            + risk_adjustment
            + len(positive_terms) * _deep_research_weight("performance_term_bonus", 4),
        ),
    )

    primary_term = _deep_research_primary_term(candidate)
    research_question = _format_prompt_template(
        str(
            archetype.get(
                "research_question_template",
                DEEP_RESEARCH_DEFAULT_VALUES.get("research_question", ""),
            )
        ),
        {"primary_term": primary_term, "selected_title": candidate.title},
    )
    production_risks: list[str] = []
    if reference_fit < DEEP_RESEARCH_MINIMUMS.get("low_reference_fit", 48):
        production_risks.append("low_reference_fit")
    if cinematic_sceneability < DEEP_RESEARCH_MINIMUMS.get("low_sceneability", 50):
        production_risks.append("low_sceneability")
    if candidate.risk == "high" or policy_safety <= DEEP_RESEARCH_MINIMUMS.get("high_policy_safety_floor", 40):
        production_risks.append("policy_risk")
    if candidate.support_count < 2:
        production_risks.append("thin_source_support")
    if progressive_reaction < DEEP_RESEARCH_MINIMUMS.get("low_progressive_reaction", 50):
        production_risks.append("low_progressive_reaction")

    rationale = [
        f"archetype={str(archetype.get('archetype_id', ''))}",
        f"matched_terms={', '.join(matched_archetype_terms[:6]) or 'none'}",
        f"progressive_terms={', '.join([*identity_terms, *accountability_terms, *hard_accountability_terms, *anger_terms][:8]) or 'none'}",
        f"friendly_terms={', '.join(friendly_terms[:5]) or 'none'}",
        f"today_memory_terms={', '.join(today_memory_terms[:5]) or 'none'}",
        f"support_count={candidate.support_count}",
        f"format_hint={candidate.format_hint}",
    ]
    if positive_terms:
        rationale.append(f"performance_positive_terms={', '.join(positive_terms[:5])}")

    return DeepResearchCandidate(
        topic_id=candidate.topic_id,
        title=candidate.title,
        query=candidate.query,
        publisher=candidate.publisher,
        url=candidate.url,
        matched_archetype_id=str(archetype.get("archetype_id", "")),
        matched_archetype_label=str(
            archetype.get("label", DEEP_RESEARCH_DEFAULT_VALUES.get("reference_label", ""))
        ),
        matched_terms=matched_archetype_terms,
        research_question=research_question,
        counterpoint_focus=str(
            archetype.get("counterpoint_focus", DEEP_RESEARCH_DEFAULT_VALUES.get("counterpoint_focus", ""))
        ),
        comment_trigger=str(
            archetype.get("comment_trigger", DEEP_RESEARCH_DEFAULT_VALUES.get("comment_trigger", ""))
        ),
        follower_promise=str(
            archetype.get("follower_promise", DEEP_RESEARCH_DEFAULT_VALUES.get("follower_promise", ""))
        ),
        script_arc=[str(item) for item in archetype.get("script_arc", []) if str(item).strip()],
        visual_sequence=[str(item) for item in archetype.get("visual_sequence", []) if str(item).strip()],
        score_components=components,
        total_score=total_score,
        rationale=rationale,
        production_risks=production_risks,
    )


def _deep_research_rank_score(candidate: DeepResearchCandidate) -> int:
    penalty = 0
    for risk in candidate.production_risks:
        if risk == "low_progressive_reaction":
            penalty += 14
        elif risk == "policy_risk":
            penalty += 20
        elif risk == "thin_source_support":
            penalty += 6
        else:
            penalty += 4
    return max(0, candidate.total_score - penalty)


def build_deep_research_report(
    signal_snapshot: SignalSnapshot,
    keyword_plan: KeywordPlan,
    topic_pool: TopicPool,
    topic_plan: TopicPlan,
    performance_feedback: dict[str, Any] | None = None,
) -> DeepResearchReport:
    del signal_snapshot
    candidates = [
        _deep_research_candidate(candidate, keyword_plan, performance_feedback)
        for candidate in topic_pool.candidates
    ]
    candidates.sort(
        key=lambda row: (
            _deep_research_rank_score(row),
            row.score_components.get("progressive_reaction", 0),
            row.score_components.get("source_density", 0),
        ),
        reverse=True,
    )
    selected = candidates[0] if candidates else DeepResearchCandidate(
        topic_id=topic_plan.selected_topic_id,
        title=topic_plan.selected_title,
        query="",
        publisher="",
        url="",
        matched_archetype_id="",
        matched_archetype_label=str(DEEP_RESEARCH_DEFAULT_VALUES.get("reference_label", "")),
        matched_terms=[],
        research_question=str(DEEP_RESEARCH_DEFAULT_VALUES.get("research_question", "")),
        counterpoint_focus=str(DEEP_RESEARCH_DEFAULT_VALUES.get("counterpoint_focus", "")),
        comment_trigger=str(DEEP_RESEARCH_DEFAULT_VALUES.get("comment_trigger", "")),
        follower_promise=str(DEEP_RESEARCH_DEFAULT_VALUES.get("follower_promise", "")),
        script_arc=[],
        visual_sequence=[],
        score_components={},
        total_score=0,
        rationale=["fallback_empty_topic_pool"],
        production_risks=["empty_topic_pool"],
    )
    blocked_or_demoted = [
        {
            "topic_id": row.topic_id,
            "title": row.title,
            "total_score": row.total_score,
            "reasons": row.production_risks or ["lower_deep_research_score"],
        }
        for row in candidates
        if row.topic_id != selected.topic_id and (row.production_risks or selected.total_score - row.total_score >= 12)
    ][:8]
    hypothesis = _format_prompt_template(
        str(DEEP_RESEARCH_STRATEGY.get("monetization_hypothesis_template", "{selected_title}")),
        {"selected_title": selected.title, "selected_archetype_label": selected.matched_archetype_label},
    )
    return DeepResearchReport(
        version=DEEP_RESEARCH_VERSION,
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        research_mode=DEEP_RESEARCH_MODE,
        official_platform_constraints=[dict(row) for row in DEEP_RESEARCH_PLATFORM_CONSTRAINTS],
        selected_topic_id=selected.topic_id,
        selected_title=selected.title,
        selected_archetype_id=selected.matched_archetype_id,
        selected_archetype_label=selected.matched_archetype_label,
        selected_research_question=selected.research_question,
        topic_candidates=candidates,
        reference_archetypes=_deep_research_public_archetypes(),
        script_mandates=DEEP_RESEARCH_SCRIPT_MANDATES,
        visual_mandates=DEEP_RESEARCH_VISUAL_MANDATES,
        monetization_hypothesis=hypothesis,
        policy_positioning=str(DEEP_RESEARCH_STRATEGY.get("policy_positioning", "")),
        blocked_or_demoted=blocked_or_demoted,
    )


def _select_editorial_rule(topic_title: str) -> dict[str, Any]:
    for rule in EDITORIAL_ANGLE_RULES:
        terms = [str(term) for term in rule.get("terms", []) if str(term).strip()]
        if any(term in topic_title for term in terms):
            return rule
    return EDITORIAL_ANGLE_RULES[0] if EDITORIAL_ANGLE_RULES else {}


def build_editorial_plan(
    topic: TopicCandidate,
    sources: dict[str, Source],
    format_plan: ContentFormatPlan,
    topic_discovery: dict[str, Any] | None,
) -> EditorialPlan:
    rule = _select_editorial_rule(topic.title)
    values = {
        "topic_title": topic.title,
        "format_id": format_plan.format_id,
    }
    must_avoid = [
        str(item) for item in EDITORIAL_STRATEGY.get("global_must_avoid", []) if str(item).strip()
    ]
    must_avoid.extend(str(item) for item in rule.get("extra_must_avoid", []) if str(item).strip())
    topic_plan = (topic_discovery or {}).get("topic_plan")
    if isinstance(topic_plan, dict) and topic_plan.get("keywords"):
        keywords = ", ".join(str(item) for item in topic_plan.get("keywords", [])[:3])
        viewer_promise_fallback = f"{keywords}를 중심으로 전말, 근거, 책임 기준을 분리한다."
    else:
        viewer_promise_fallback = "전말, 근거, 책임 기준을 분리한다."
    return EditorialPlan(
        version=str(EDITORIAL_STRATEGY.get("version", "editorial_plan_v1")),
        topic_title=topic.title,
        angle_id=str(rule.get("angle_id", "timeline_explainer")),
        angle_label=str(rule.get("label", "전말형")),
        core_question=_format_prompt_template(
            str(rule.get("core_question_template", "{topic_title}에서 무엇을 확인해야 하나?")),
            values,
        ),
        viewer_promise=_format_prompt_template(
            str(rule.get("viewer_promise_template", viewer_promise_fallback)),
            values,
        ),
        tone=str(EDITORIAL_STRATEGY.get("default_tone", "")),
        must_include=[str(item) for item in rule.get("must_include", []) if str(item).strip()],
        must_avoid=list(dict.fromkeys(must_avoid)),
        final_comment_question=str(EDITORIAL_STRATEGY.get("default_comment_question", "")),
        source_ids=[source_id for source_id in topic.source_ids if source_id in sources],
    )


def _source_is_trusted(source: Source) -> bool:
    markers = [
        str(item)
        for item in FACT_PACK_STRATEGY.get("trusted_source_markers", [])
        if str(item).strip()
    ]
    text = f"{source.source_id} {source.title} {source.note} {source.url}"
    return bool(markers and any(marker in text for marker in markers)) or _publisher_is_trusted(source.title)


def _source_roles(topic: TopicCandidate, sources: dict[str, Source]) -> dict[str, str | None]:
    valid_ids = [source_id for source_id in topic.source_ids if source_id in sources]
    official = next(
        (
            source_id
            for source_id in valid_ids
            if _source_is_trusted(sources[source_id])
            or any(marker in sources[source_id].url.lower() for marker in ["gov", "assembly", "court", "tiktok.com"])
        ),
        None,
    )
    return {
        "primary_report": valid_ids[0] if valid_ids else None,
        "supporting_report": valid_ids[1] if len(valid_ids) >= 2 else None,
        "official_or_original": official,
        "counterpoint_or_response": valid_ids[-1] if len(valid_ids) >= 2 else None,
    }


def _claim_item_type(claim: Claim, sources: dict[str, Source]) -> str:
    source_rows = [sources[source_id] for source_id in claim.source_ids if source_id in sources]
    text = claim.text
    if claim.risk in {"medium", "high"}:
        return "reported_claim"
    if any(marker in text for marker in ["의혹", "해명", "보도", "주장", "통보", "입건", "수사"]):
        return "reported_claim"
    if len(source_rows) >= 2 or any(_source_is_trusted(source) for source in source_rows):
        return "confirmed_fact"
    return "reported_claim"


def _fact_pack_item(
    *,
    item_id: str,
    item_type: str,
    text: str,
    source_ids: list[str],
    risk: str,
) -> FactPackItem:
    guidance_key = {
        "confirmed_fact": "confirmed_fact_guidance",
        "reported_claim": "reported_claim_guidance",
        "counterpoint": "counterpoint_guidance",
        "unanswered_question": "counterpoint_guidance",
    }.get(item_type, "reported_claim_guidance")
    confidence = "high" if item_type == "confirmed_fact" else ("medium" if source_ids else "low")
    return FactPackItem(
        fact_id=item_id,
        item_type=item_type,
        text=_clean_card_text(text),
        source_ids=source_ids,
        confidence=confidence,
        risk=risk,
        usage_guidance=str(FACT_PACK_STRATEGY.get(guidance_key, "")),
    )


def _deep_research_selected_candidate(topic_discovery: dict[str, Any] | None) -> dict[str, Any]:
    report = (topic_discovery or {}).get("deep_research_report")
    if not isinstance(report, dict):
        return {}
    selected_id = str(report.get("selected_topic_id", ""))
    candidates = report.get("topic_candidates")
    if not isinstance(candidates, list):
        return {}
    for candidate in candidates:
        if isinstance(candidate, dict) and str(candidate.get("topic_id", "")) == selected_id:
            return candidate
    return next((candidate for candidate in candidates if isinstance(candidate, dict)), {})


def build_fact_pack(
    topic: TopicCandidate,
    sources: dict[str, Source],
    format_plan: ContentFormatPlan,
    topic_discovery: dict[str, Any] | None = None,
) -> FactPack:
    confirmed: list[FactPackItem] = []
    reported: list[FactPackItem] = []
    for index, claim in enumerate(topic.claims, start=1):
        item_type = _claim_item_type(claim, sources)
        item = _fact_pack_item(
            item_id=f"{item_type}_{index:02d}",
            item_type=item_type,
            text=claim.text,
            source_ids=[source_id for source_id in claim.source_ids if source_id in sources],
            risk=claim.risk,
        )
        if item_type == "confirmed_fact":
            confirmed.append(item)
        else:
            reported.append(item)

    selected_candidate = _deep_research_selected_candidate(topic_discovery)
    counterpoint_focus = str(
        selected_candidate.get("counterpoint_focus")
        or FACT_PACK_STRATEGY.get("default_counterpoint_focus", "")
    ).strip()
    counterpoints = [
        _fact_pack_item(
            item_id="counterpoint_01",
            item_type="counterpoint",
            text=counterpoint_focus,
            source_ids=[source_id for source_id in topic.source_ids if source_id in sources][:2],
            risk="medium",
        )
    ] if counterpoint_focus else []

    core_question = str(selected_candidate.get("research_question") or f"{topic.title}에서 무엇을 확인해야 하나?")
    unanswered = [
        _fact_pack_item(
            item_id="unanswered_01",
            item_type="unanswered_question",
            text=_format_prompt_template(
                str(FACT_PACK_STRATEGY.get("unanswered_question_template", "{core_question}")),
                {"core_question": core_question, "topic_title": topic.title},
            ),
            source_ids=[],
            risk="medium",
        )
    ]

    source_count = len([source_id for source_id in topic.source_ids if source_id in sources])
    trusted_count = sum(1 for source_id in topic.source_ids if source_id in sources and _source_is_trusted(sources[source_id]))
    min_sources = int(
        FACT_PACK_STRATEGY.get(
            "reward_deep_min_source_count" if format_plan.reward_eligible else "min_source_count",
            2,
        )
    )
    blockers: list[str] = []
    if source_count < min_sources:
        blockers.append(f"source_count_below_{min_sources}:{source_count}")
    if not confirmed and not reported:
        blockers.append("no_claim_items")
    if reported and not counterpoints:
        blockers.append("reported_claims_without_counterpoint")

    return FactPack(
        version=str(FACT_PACK_STRATEGY.get("version", "fact_pack_v1")),
        topic_title=topic.title,
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        source_count=source_count,
        trusted_source_count=trusted_count,
        source_roles=_source_roles(topic, sources),
        confirmed_facts=confirmed,
        reported_claims=reported,
        counterpoints=counterpoints,
        unanswered_questions=unanswered,
        risk_phrases_to_avoid=[
            str(item) for item in FACT_PACK_STRATEGY.get("risk_phrases_to_avoid", []) if str(item).strip()
        ],
        gate_passed=not blockers,
        blockers=blockers,
    )


def _fact_ids_for_angle(fact_pack: FactPack) -> list[str]:
    rows = [*fact_pack.confirmed_facts, *fact_pack.reported_claims, *fact_pack.counterpoints]
    return [row.fact_id for row in rows[:6]]


def _risk_level(level: str, reason: str, requires_label: bool | None = None) -> RiskFlag:
    allowed = {"none", "low", "medium", "high"}
    normalized = level if level in allowed else "medium"
    return RiskFlag(level=normalized, reason=reason, requires_label=requires_label)


def _risk_terms(key: str) -> list[str]:
    return _strategy_terms(RISK_FLAGS_STRATEGY, key)


def _topic_fact_text(topic: TopicCandidate, fact_pack: FactPack) -> str:
    rows = [
        topic.title,
        topic.angle,
        topic.slot,
        *[claim.text for claim in topic.claims],
        *[item.text for item in [*fact_pack.confirmed_facts, *fact_pack.reported_claims, *fact_pack.counterpoints]],
    ]
    return " ".join(str(row) for row in rows if str(row).strip()).lower()


def _manual_review_levels(flags: list[RiskFlag]) -> bool:
    return any(flag.level == "high" for flag in flags)


def build_risk_flags(topic: TopicCandidate, fact_pack: FactPack, format_plan: ContentFormatPlan) -> RiskFlags:
    text = _topic_fact_text(topic, fact_pack)
    blockers: list[str] = []
    rewrite_notes: list[str] = []

    election_level = "medium" if _contains_any_marker(text, _risk_terms("election_terms")) else "none"
    if _contains_any_marker(text, _risk_terms("election_high_risk_terms")):
        election_level = "high"
        blockers.append("election_high_risk")
        rewrite_notes.append("선거 절차, 투표 방법, 결과 단정은 제거하고 공개 근거 범위만 설명한다.")

    aigc_level = "low"
    aigc_reason = "AI 생성 이미지 또는 편집 가능성이 있어 생성 이미지 고지를 유지한다."
    if _contains_any_marker(text, _risk_terms("aigc_high_risk_terms")):
        aigc_level = "high"
        blockers.append("aigc_public_figure_or_deepfake_risk")
        rewrite_notes.append("실존 인물 얼굴·목소리 합성처럼 보이는 장면은 삭제한다.")

    claim_risks = {claim.risk.lower() for claim in topic.claims}
    defamation_level = "medium" if "medium" in claim_risks else "none"
    if "high" in claim_risks or _contains_any_marker(text, _risk_terms("defamation_high_risk_terms")):
        defamation_level = "high"
        blockers.append("defamation_high_risk")
        rewrite_notes.append("범죄 확정 표현을 보도된 주장과 확인된 사실로 분리한다.")

    copyright_level = "low" if fact_pack.source_count else "none"
    if _contains_any_marker(text, _risk_terms("copyright_high_risk_terms")):
        copyright_level = "high"
        blockers.append("copyright_high_risk")
        rewrite_notes.append("원본 클립 재업로드 대신 짧은 인용, 출처 표기, 해설 중심으로 바꾼다.")

    public_level = "high" if _contains_any_marker(text, _risk_terms("public_importance_terms")) else "medium"

    monetization_level = "medium" if _contains_any_marker(text, _risk_terms("political_actor_terms")) else "none"
    if _contains_any_marker(text, _risk_terms("paid_political_terms")):
        monetization_level = "high"
        blockers.append("paid_political_or_campaign_monetization_risk")
        rewrite_notes.append("정당·후보 협업, 후원, 투표 행동 유도 표현을 제거한다.")

    min_sources = int(RISK_FLAGS_STRATEGY.get("min_sources_for_evidence_briefing", 2))
    if format_plan.format_id == "evidence_briefing_75" and fact_pack.source_count < min_sources:
        blockers.append(f"evidence_briefing_source_count_below_{min_sources}:{fact_pack.source_count}")
    if not fact_pack.gate_passed:
        blockers.append("fact_pack_not_passed")

    risk_flags_for_review = [
        _risk_level(election_level, "선거·투표·결과·여론조사 관련 오인 가능성 검사"),
        _risk_level(aigc_level, aigc_reason, requires_label=True),
        _risk_level(defamation_level, "명예훼손 또는 범죄 단정 가능성 검사"),
        _risk_level(copyright_level, "뉴스/영상/문서 재사용과 저작권 리스크 검사"),
        _risk_level(monetization_level, "정치 주체 계정 또는 유료 정치성 콘텐츠 오인 가능성 검사"),
    ]
    public_importance = _risk_level(public_level, "공익성과 제도적 중요성 평가")
    flags = [*risk_flags_for_review[:4], public_importance, risk_flags_for_review[4]]
    manual_review = _manual_review_levels(risk_flags_for_review)
    if manual_review and "manual_review_required" not in blockers:
        blockers.append("manual_review_required")

    return RiskFlags(
        version=str(RISK_FLAGS_STRATEGY.get("version", "risk_flags_v1")),
        topic_title=topic.title,
        generated_at=dt.datetime.now(dt.timezone.utc).isoformat(),
        election=flags[0],
        aigc=flags[1],
        defamation=flags[2],
        copyright=flags[3],
        public_importance=flags[4],
        political_actor_monetization=flags[5],
        manual_review_required=manual_review,
        publish_blockers=blockers,
        safe_rewrite_notes=[note for note in rewrite_notes if note],
        gate_passed=not blockers,
        blockers=blockers,
    )


def _source_type(source: Source) -> str:
    text = f"{source.title} {source.note} {source.url}".lower()
    if any(term in text for term in ["국회", "assembly", "bill"]):
        return "assembly"
    if any(term in text for term in ["법원", "대법원", "헌법재판소", "court"]):
        return "court"
    if any(term in text for term in ["선관위", "정부", "공식", "go.kr", "official"]):
        return "official"
    if any(term in text for term in ["여론조사", "poll", "survey"]):
        return "poll"
    if any(term in text for term in ["tiktok", "youtube", "instagram", "support.google", "newsroom"]):
        return "platform_policy"
    return "news"


def _source_card_item(fact_pack: FactPack) -> FactPackItem | None:
    rows = [*fact_pack.confirmed_facts, *fact_pack.reported_claims]
    return next((row for row in rows if row.source_ids), None)


def build_source_card(topic: TopicCandidate, sources: dict[str, Source], fact_pack: FactPack) -> SourceCard:
    item = _source_card_item(fact_pack)
    blockers: list[str] = []
    if item is None:
        blockers.append("source_card_fact_item_missing")
    source_id = item.source_ids[0] if item and item.source_ids else ""
    source = sources.get(source_id)
    if source is None:
        blockers.append("source_card_source_missing")
        source = Source(source_id or "missing", "출처 확인 필요", "", "missing")
    if not source.url:
        blockers.append("source_card_url_missing")

    boundary = item.item_type if item else "unverified"
    source_name = _compact_card_text(source.title, 36, keep_question=False) if source.title else "출처 확인 필요"
    display_template = str(SOURCE_CARD_STRATEGY.get("display_template", "{source_name} 기준"))
    display_text = _format_prompt_template(
        display_template,
        {
            "source_name": source_name,
            "claim_boundary": boundary,
            "topic_title": topic.title,
        },
    )
    display_text = _compact_card_text(display_text, int(SOURCE_CARD_STRATEGY.get("display_max_chars", 42)))
    return SourceCard(
        version=str(SOURCE_CARD_STRATEGY.get("version", "source_card_v1")),
        topic_title=topic.title,
        source_name=source_name,
        source_type=_source_type(source),
        published_at="확인 필요",
        claim_boundary=boundary,
        display_text=display_text,
        source_url=source.url,
        source_ids=[source_id] if source_id else [],
        gate_passed=not blockers,
        blockers=blockers,
    )


def _reference_config_rows(config: dict[str, Any], key: str) -> list[dict[str, Any]]:
    rows = config.get(key, [])
    if not isinstance(rows, list):
        raise RuntimeError(f"Reference config key must be a list: {key}")
    return [row for row in rows if isinstance(row, dict)]


def _reference_row_ids(rows: list[dict[str, Any]]) -> list[str]:
    return [str(row.get("id")) for row in rows if str(row.get("id", "")).strip()]


def _reference_route_for_format(format_id: str) -> dict[str, Any]:
    routes = _reference_config_rows(FORMAT_ROUTER_CONFIG, "routing_rules")
    exact = next((route for route in routes if route.get("format_id") == format_id), None)
    default = next((route for route in routes if route.get("default") is True), None)
    return exact or default or {}


def _reference_text_for_topic(topic: TopicCandidate, fact_pack: FactPack) -> str:
    parts = [
        topic.title,
        topic.angle,
        topic.slot,
        *[claim.text for claim in topic.claims],
        *[
            item.text
            for item in [
                *fact_pack.confirmed_facts,
                *fact_pack.reported_claims,
                *fact_pack.counterpoints,
                *fact_pack.unanswered_questions,
            ]
        ],
    ]
    return " ".join(str(part) for part in parts if str(part).strip()).casefold()


def _append_unique(items: list[str], value: str) -> None:
    if value and value not in items:
        items.append(value)


def _reference_term_hits(text: str, terms: list[str]) -> list[str]:
    hits: list[str] = []
    for term in terms:
        normalized = str(term).strip()
        if normalized and normalized.casefold() in text:
            _append_unique(hits, normalized)
    return hits


def _select_reference_hooks(text: str, available_hook_ids: list[str]) -> tuple[list[str], list[str]]:
    hooks: list[str] = []
    matched_terms: list[str] = []

    actor_terms = [
        *HOT_TOPIC_ACCOUNT_REFERENCE_TERMS,
        "president",
        "assembly",
        "court",
        "prosecutor",
        "government",
        "party",
        "candidate",
        "election",
        "대통령",
        "국회",
        "법원",
        "검찰",
        "정부",
        "정당",
        "후보",
        "선거",
        "여론조사",
        "교육부",
        "교육",
        "학교",
        "교실",
        "늘봄학교",
    ]
    number_terms = [
        "%",
        "percent",
        "won",
        "billion",
        "million",
        "date",
        "poll",
        "지지율",
        "여론조사",
    ]
    quote_terms = [
        '"',
        "'",
        "quote",
        "said",
        "claim",
        "denial",
        "contradiction",
        "발언",
        "주장",
        "해명",
        "반박",
        "논란",
    ]
    civic_terms = [
        "court",
        "assembly",
        "hearing",
        "document",
        "newsroom",
        "street",
        "법원",
        "국회",
        "청문회",
        "문서",
        "자료",
        "뉴스룸",
        "거리",
        "집회",
        "교육",
        "학교",
        "교실",
    ]

    actor_hits = _reference_term_hits(text, actor_terms)
    if actor_hits and "named_actor_first" in available_hook_ids:
        _append_unique(hooks, "named_actor_first")
        matched_terms.extend(actor_hits[:4])

    number_hits = _reference_term_hits(text, number_terms)
    has_number_signal = bool(number_hits or re.search(r"\d+(?:\.\d+)?\s*(?:%|원|억|조|만|명|건|일|월|년)?", text))
    if has_number_signal and "number_receipt_first" in available_hook_ids:
        _append_unique(hooks, "number_receipt_first")
        matched_terms.extend(number_hits[:4] or ["number"])

    quote_hits = _reference_term_hits(text, quote_terms)
    if quote_hits and "quote_contradiction_first" in available_hook_ids:
        _append_unique(hooks, "quote_contradiction_first")
        matched_terms.extend(quote_hits[:4])

    civic_hits = _reference_term_hits(text, civic_terms)
    if civic_hits and "civic_scene_first" in available_hook_ids:
        _append_unique(hooks, "civic_scene_first")
        matched_terms.extend(civic_hits[:4])

    for hook_id in available_hook_ids:
        if len(hooks) >= 3:
            break
        _append_unique(hooks, hook_id)
    return hooks[:3], list(dict.fromkeys(matched_terms))


def _select_reference_scene_types(pattern_ids: list[str], available_scene_type_ids: list[str]) -> list[str]:
    scene_map = {
        "actor_allegation_caption": ["street_speech_closeup", "civic_location_exterior", "news_graphic_title_card"],
        "debate_or_hearing_quote": ["debate_microphone_closeup", "hearing_room_wide", "document_receipt_desk"],
        "receipt_number_collage": ["document_receipt_desk", "news_graphic_title_card", "civic_location_exterior"],
        "documentary_title_card": ["news_graphic_title_card", "civic_location_exterior", "document_receipt_desk"],
        "subscribe_or_share_overlay": ["news_graphic_title_card", "street_speech_closeup"],
    }
    selected: list[str] = []
    for pattern_id in pattern_ids:
        for scene_type_id in scene_map.get(pattern_id, []):
            if scene_type_id in available_scene_type_ids:
                _append_unique(selected, scene_type_id)
    for scene_type_id in available_scene_type_ids:
        if len(selected) >= 4:
            break
        _append_unique(selected, scene_type_id)
    return selected[:4]


def _select_reference_ctas(format_id: str) -> list[str]:
    selected: list[str] = []
    for row in _reference_config_rows(CTA_PATTERNS_CONFIG, "cta_patterns"):
        use_when = row.get("use_when", [])
        if isinstance(use_when, list) and format_id in [str(item) for item in use_when]:
            _append_unique(selected, str(row.get("id", "")))
    for fallback in ["save_for_receipt", "share_for_context", "next_part_follow"]:
        if len(selected) >= 2:
            break
        _append_unique(selected, fallback)
    return selected[:2]


def build_reference_fit(
    topic: TopicCandidate,
    format_plan: ContentFormatPlan,
    fact_pack: FactPack,
    source_card: SourceCard,
) -> ReferenceFit:
    pattern_rows = _reference_config_rows(REFERENCE_PATTERNS_CONFIG, "patterns")
    hook_rows = _reference_config_rows(HOOK_PATTERNS_CONFIG, "hook_patterns")
    scene_rows = _reference_config_rows(SCENE_TYPE_LIBRARY_CONFIG, "scene_types")
    route = _reference_route_for_format(format_plan.format_id)
    available_pattern_ids = _reference_row_ids(pattern_rows)
    available_hook_ids = _reference_row_ids(hook_rows)
    available_scene_type_ids = _reference_row_ids(scene_rows)

    route_pattern_ids = [
        str(pattern_id)
        for pattern_id in route.get("reference_patterns", [])
        if str(pattern_id) in available_pattern_ids
    ]
    selected_pattern_ids = route_pattern_ids or available_pattern_ids[:2]
    reference_text = _reference_text_for_topic(topic, fact_pack)
    selected_hook_ids, matched_terms = _select_reference_hooks(reference_text, available_hook_ids)
    selected_scene_type_ids = _select_reference_scene_types(selected_pattern_ids, available_scene_type_ids)
    selected_cta_ids = _select_reference_ctas(format_plan.format_id)

    blockers: list[str] = []
    if not selected_pattern_ids:
        blockers.append("reference_patterns_missing")
    if not selected_hook_ids:
        blockers.append("hook_patterns_missing")
    if not selected_scene_type_ids:
        blockers.append("scene_type_guidance_missing")
    if not selected_cta_ids:
        blockers.append("cta_patterns_missing")
    if not fact_pack.gate_passed:
        blockers.append("fact_pack_not_passed")
    if not source_card.gate_passed:
        blockers.append("source_card_not_passed")

    route_when = [str(item) for item in route.get("when", []) if str(item).strip()]
    source_benchmark = str(
        REFERENCE_PATTERNS_CONFIG.get("source_benchmark")
        or FORMAT_ROUTER_CONFIG.get("source_benchmark")
        or ""
    )
    playback_qa = str(
        REFERENCE_PATTERNS_CONFIG.get("playback_qa")
        or FORMAT_ROUTER_CONFIG.get("playback_qa")
        or ""
    )
    usage_notes = list(
        dict.fromkeys(
            [
                str(REFERENCE_PATTERNS_CONFIG.get("config_use_rule", "")).strip(),
                str(HOOK_PATTERNS_CONFIG.get("config_use_rule", "")).strip(),
                str(SCENE_TYPE_LIBRARY_CONFIG.get("layout_variety_rule", "")).strip(),
                "Do not synthesize real politician faces, party logos, fake broadcast UI, or unsourced crime assertions.",
                "Use reference rows as structure and pacing guidance only; each scene still needs topic-specific visual planning.",
            ]
        )
    )
    usage_notes = [note for note in usage_notes if note]

    fit_score = min(
        100,
        25
        + min(20, len(selected_pattern_ids) * 7)
        + min(20, len(selected_hook_ids) * 6)
        + min(15, len(selected_scene_type_ids) * 4)
        + (10 if fact_pack.gate_passed else 0)
        + (10 if source_card.gate_passed else 0)
        + (5 if route else 0),
    )
    return ReferenceFit(
        version=str(REFERENCE_PATTERNS_CONFIG.get("version", "reference_fit_v1")),
        status="wired_candidate_config_active",
        topic_title=topic.title,
        format_id=format_plan.format_id,
        source_benchmark=source_benchmark,
        playback_qa=playback_qa,
        route_when=route_when,
        selected_pattern_ids=selected_pattern_ids,
        selected_hook_ids=selected_hook_ids,
        selected_scene_type_ids=selected_scene_type_ids,
        selected_cta_ids=selected_cta_ids,
        matched_terms=list(dict.fromkeys(matched_terms)),
        fit_score=fit_score,
        usage_notes=usage_notes,
        gate_passed=not blockers,
        blockers=blockers,
    )


def build_angle_brief(
    topic: TopicCandidate,
    fact_pack: FactPack,
    editorial_plan: EditorialPlan,
    format_plan: ContentFormatPlan,
    topic_discovery: dict[str, Any] | None = None,
) -> AngleBrief:
    selected_candidate = _deep_research_selected_candidate(topic_discovery)
    emotion_map = _config_dict(ANGLE_BRIEF_STRATEGY, "audience_emotion_by_angle")
    values = {
        "topic_title": topic.title,
        "core_question": editorial_plan.core_question,
        "viewer_promise": editorial_plan.viewer_promise,
        "format_id": format_plan.format_id,
    }
    comment_question = str(selected_candidate.get("comment_trigger") or editorial_plan.final_comment_question).strip()
    follow_reason = str(
        selected_candidate.get("follower_promise")
        or _format_prompt_template(str(ANGLE_BRIEF_STRATEGY.get("follow_reason_template", "")), values)
    ).strip()
    brief = AngleBrief(
        version=str(ANGLE_BRIEF_STRATEGY.get("version", "angle_brief_v1")),
        topic_title=topic.title,
        format_id=format_plan.format_id,
        viewer_promise=editorial_plan.viewer_promise,
        one_sentence_thesis=_format_prompt_template(str(ANGLE_BRIEF_STRATEGY.get("thesis_template", "")), values),
        audience_emotion=str(emotion_map.get(editorial_plan.angle_id) or emotion_map.get("timeline_explainer") or ""),
        share_reason=_format_prompt_template(str(ANGLE_BRIEF_STRATEGY.get("share_reason_template", "")), values),
        comment_question=comment_question,
        follow_reason=follow_reason,
        safe_provocation=_format_prompt_template(str(ANGLE_BRIEF_STRATEGY.get("safe_provocation_template", "")), values),
        forbidden_angle=_format_prompt_template(str(ANGLE_BRIEF_STRATEGY.get("forbidden_angle_template", "")), values),
        source_fact_ids=_fact_ids_for_angle(fact_pack),
        gate_passed=True,
        blockers=[],
    )
    blockers: list[str] = []
    if not fact_pack.gate_passed:
        blockers.append("fact_pack_not_passed")
    required_fields = [
        "viewer_promise",
        "one_sentence_thesis",
        "audience_emotion",
        "share_reason",
        "comment_question",
        "follow_reason",
        "safe_provocation",
        "forbidden_angle",
    ]
    for field_name in required_fields:
        if not str(getattr(brief, field_name)).strip():
            blockers.append(f"{field_name}_missing")
    if not brief.source_fact_ids:
        blockers.append("source_fact_ids_missing")
    return replace(brief, gate_passed=not blockers, blockers=blockers)


def _planning_fact_id_sequence(fact_pack: FactPack) -> list[str]:
    ids = [row.fact_id for row in [*fact_pack.confirmed_facts, *fact_pack.reported_claims, *fact_pack.counterpoints]]
    return ids or ["unanswered_01"]


def build_storyboard_brief(
    topic: TopicCandidate,
    script: ScriptPackage,
    fact_pack: FactPack,
    angle_brief: AngleBrief,
    format_plan: ContentFormatPlan,
) -> StoryboardBrief:
    visual_briefs = {brief.scene_id: brief for brief in build_visual_briefs(topic, script.scenes)}
    narrative_jobs = _config_dict(STORYBOARD_BRIEF_STRATEGY, "narrative_jobs_by_role")
    tts_jobs = _config_dict(STORYBOARD_BRIEF_STRATEGY, "tts_jobs_by_role")
    overlay_lanes = [
        str(item)
        for item in STORYBOARD_BRIEF_STRATEGY.get("overlay_lanes", ["top", "middle", "bottom"])
        if str(item).strip()
    ] or ["top", "middle", "bottom"]
    fact_ids = _planning_fact_id_sequence(fact_pack)
    scenes: list[StoryboardSceneBrief] = []
    seen_information: set[str] = set()
    for index, scene in enumerate(script.scenes):
        brief = visual_briefs.get(scene.scene_id)
        role = brief.role if brief else "evidence"
        fact_id = fact_ids[min(index, len(fact_ids) - 1)]
        required_info = _compact_card_text(scene.body, 58, keep_question="?" in scene.body)
        seen_information.add(required_info)
        if brief:
            visual_job = " | ".join(
                part
                for part in [
                    brief.visual_intent,
                    f"concrete_scene={brief.concrete_scene}",
                    f"action={brief.action_beat}",
                    f"camera={brief.camera}",
                    f"palette={brief.palette}",
                    f"treatment={brief.treatment_id}",
                ]
                if part
            )
        else:
            visual_job = scene.visual
        scenes.append(
            StoryboardSceneBrief(
                scene_id=scene.scene_id,
                narrative_job=str(narrative_jobs.get(role) or scene.title),
                evidence_item_ids=[fact_id],
                visual_job=visual_job,
                tts_job=str(tts_jobs.get(role) or "자연스럽게 읽는다."),
                viewer_question=_planning_text_value(PLANNING_ROLE_QUESTIONS, role, angle_brief.safe_provocation),
                required_new_information=required_info,
                risk_controls=[
                    *fact_pack.risk_phrases_to_avoid[:4],
                    angle_brief.forbidden_angle,
                ],
                overlay_lane=overlay_lanes[index % len(overlay_lanes)],
            )
        )
    blockers: list[str] = []
    if not angle_brief.gate_passed:
        blockers.append("angle_brief_not_passed")
    if len(scenes) < format_plan.scene_count_min:
        blockers.append(f"scene_count_below_{format_plan.scene_count_min}:{len(scenes)}")
    if len(seen_information) < min(len(scenes), 7):
        blockers.append("scene_new_information_too_repetitive")
    visual_uniques = {scene.visual_job for scene in scenes if scene.visual_job}
    if len(visual_uniques) < min(len(scenes), 7):
        blockers.append("scene_visual_jobs_too_repetitive")
    if any(not row.evidence_item_ids for row in scenes):
        blockers.append("scene_missing_evidence_ids")
    return StoryboardBrief(
        version=str(STORYBOARD_BRIEF_STRATEGY.get("version", "storyboard_brief_v1")),
        topic_title=topic.title,
        format_id=format_plan.format_id,
        scene_count=len(scenes),
        scenes=scenes,
        gate_passed=not blockers,
        blockers=blockers,
    )


def _quality_with_workflow_gates(
    quality: PublishQualityResult,
    fact_pack: FactPack,
    risk_flags: RiskFlags,
    source_card: SourceCard,
    reference_fit: ReferenceFit,
    angle_brief: AngleBrief,
    storyboard_brief: StoryboardBrief,
) -> PublishQualityResult:
    blockers = list(quality.blockers)
    for gate_name, passed, gate_blockers in [
        ("fact_pack", fact_pack.gate_passed, fact_pack.blockers),
        ("risk_flags", risk_flags.gate_passed, risk_flags.blockers),
        ("source_card", source_card.gate_passed, source_card.blockers),
        ("reference_fit", reference_fit.gate_passed, reference_fit.blockers),
        ("angle_brief", angle_brief.gate_passed, angle_brief.blockers),
        ("storyboard_brief", storyboard_brief.gate_passed, storyboard_brief.blockers),
    ]:
        if not passed:
            detail = ",".join(gate_blockers) if gate_blockers else "failed"
            blockers.append(f"{gate_name}_not_passed:{detail}")
    return replace(quality, passed=quality.passed and not blockers, blockers=list(dict.fromkeys(blockers)))


def build_selected_script_plan(
    script: ScriptPackage,
    gate: GateResult,
    readability: ReadabilityResult,
    quality: PublishQualityResult,
    format_plan: ContentFormatPlan,
) -> SelectedScriptPlan:
    blockers = [*gate.errors, *readability.issues, *quality.blockers]
    return SelectedScriptPlan(
        version="selected_script_v1",
        variant_id=script.variant_id,
        selection_reason=(
            f"selected_variant={quality.selected_variant}; "
            f"publish_ready_score={quality.publish_ready_score}; "
            f"format={format_plan.format_id}"
        ),
        title=script.title,
        format_id=format_plan.format_id,
        target_duration_sec=script.target_duration_sec,
        scene_count=len(script.scenes),
        gate_score=gate.score,
        readability_passed=readability.passed,
        publish_ready_score=quality.publish_ready_score,
        quality_scores=quality.scores,
        blockers=blockers,
        script=asdict(script),
    )


def build_visual_plan(content_plan: ContentPlan, visual_assets: list[VisualAsset]) -> VisualPlan:
    asset_by_scene = {asset.scene_id: asset for asset in visual_assets}
    scenes: list[VisualScenePlan] = []
    for scene_plan in content_plan.image_plan:
        asset = asset_by_scene.get(scene_plan.scene_id)
        generated_prompt = asset.prompt if asset else ""
        scenes.append(
            VisualScenePlan(
                scene_id=scene_plan.scene_id,
                prompt_basis="content_plan.image_need",
                image_need=scene_plan.image_need,
                visual_role=scene_plan.visual_role,
                issue_type=scene_plan.issue_type,
                location=scene_plan.location,
                camera=scene_plan.camera,
                required_anchors=scene_plan.required_anchors,
                avoid=scene_plan.avoid,
                diegetic_text=scene_plan.diegetic_text,
                diegetic_text_directive=scene_plan.diegetic_text_directive,
                asset_provider=asset.provider if asset else None,
                asset_status=asset.status if asset else None,
                asset_path=asset.path if asset else None,
                prompt_lineage={
                    "content_image_need": scene_plan.image_need,
                    "generated_prompt": generated_prompt,
                    "visual_brief": asset.visual_brief if asset else {},
                },
            )
        )
    return VisualPlan(
        version="visual_plan_v1",
        topic_title=content_plan.topic_title,
        scene_count=len(scenes),
        scenes=scenes,
    )


def _read_text_if_exists(path_value: Any) -> str:
    if not path_value:
        return ""
    path = Path(str(path_value))
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8").strip()


def _read_json_object_if_exists(path_value: Any) -> dict[str, Any]:
    if not path_value:
        return {}
    path = Path(str(path_value))
    if not path.exists():
        return {}
    try:
        loaded = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return {}
    return loaded if isinstance(loaded, dict) else {}


def _elevenlabs_voice_settings(model_id: str) -> dict[str, float | bool]:
    settings: dict[str, float | bool] = {
        "stability": _env_float_ratio("ELEVENLABS_STABILITY", 0.12),
        "similarity_boost": _env_float_ratio("ELEVENLABS_SIMILARITY_BOOST", 0.18),
        "speed": _env_float("ELEVENLABS_SPEED", 1.09, min_value=0.7, max_value=1.2),
    }
    if _model_supports_style_settings(model_id):
        settings["style"] = _env_float_ratio("ELEVENLABS_STYLE", 0.07)
        settings["use_speaker_boost"] = _env_bool("ELEVENLABS_USE_SPEAKER_BOOST", True)
    return settings


def _elevenlabs_enable_logging() -> bool:
    return _env_bool("ELEVENLABS_ENABLE_LOGGING", False)


def _elevenlabs_tts_disabled() -> bool:
    return _env_bool("AINO_DISABLE_ELEVENLABS_TTS", False)


def _elevenlabs_history_scrub_enabled() -> bool:
    return _env_bool("ELEVENLABS_HISTORY_SCRUB_AFTER_TTS", True)


def _elevenlabs_zero_retention_requested() -> bool:
    return not _elevenlabs_enable_logging()


def _elevenlabs_history_note(audit: dict[str, Any], *, final: bool = False) -> str:
    if not audit.get("enabled"):
        return "elevenlabs_history_audit_disabled"
    if audit.get("error"):
        return f"elevenlabs_history_audit_failed={audit.get('error')}"
    deleted = int(audit.get("deleted") or 0)
    remaining = int(audit.get("remaining_first_page") or 0)
    prefix = "elevenlabs_history_final" if final else "elevenlabs_history_intermediate"
    return f"{prefix}_deleted={deleted};{prefix}_remaining_first_page={remaining}"


def _elevenlabs_scrub_history(api_key: str) -> dict[str, Any]:
    if not _elevenlabs_history_scrub_enabled():
        return {"enabled": False, "deleted": 0, "remaining_first_page": None}
    try:
        import requests
    except Exception as exc:  # pragma: no cover - requests is available in normal runtime
        return {"enabled": True, "deleted": 0, "remaining_first_page": None, "error": str(exc)}

    headers = {"xi-api-key": api_key}
    deleted = 0
    try:
        response = requests.get("https://api.elevenlabs.io/v1/history?page_size=100", headers=headers, timeout=30)
        if response.status_code >= 400:
            return {
                "enabled": True,
                "deleted": deleted,
                "remaining_first_page": None,
                "error": f"history_get_http_{response.status_code}",
            }
        data = response.json() if hasattr(response, "json") else json.loads(response.text or "{}")
        history = data.get("history") if isinstance(data, dict) else []
        for item in history or []:
            history_item_id = str(item.get("history_item_id") or "").strip() if isinstance(item, dict) else ""
            if not history_item_id:
                continue
            delete_response = requests.delete(
                f"https://api.elevenlabs.io/v1/history/{history_item_id}",
                headers=headers,
                timeout=30,
            )
            if 200 <= delete_response.status_code < 300:
                deleted += 1
        check_response = requests.get("https://api.elevenlabs.io/v1/history?page_size=1", headers=headers, timeout=30)
        if check_response.status_code >= 400:
            return {
                "enabled": True,
                "deleted": deleted,
                "remaining_first_page": None,
                "error": f"history_check_http_{check_response.status_code}",
            }
        check_data = check_response.json() if hasattr(check_response, "json") else json.loads(check_response.text or "{}")
        remaining_history = check_data.get("history") if isinstance(check_data, dict) else []
        return {"enabled": True, "deleted": deleted, "remaining_first_page": len(remaining_history or [])}
    except Exception as exc:
        return {"enabled": True, "deleted": deleted, "remaining_first_page": None, "error": str(exc)}


def _elevenlabs_scrub_history_until_clear(api_key: str) -> dict[str, Any]:
    if not _elevenlabs_history_scrub_enabled():
        return {"enabled": False, "deleted": 0, "remaining_first_page": None}
    try:
        attempts = max(1, min(10, int(os.environ.get("ELEVENLABS_HISTORY_SCRUB_ATTEMPTS", "6"))))
    except ValueError:
        attempts = 6
    try:
        wait_sec = max(0.0, min(10.0, float(os.environ.get("ELEVENLABS_HISTORY_SCRUB_WAIT_SEC", "2"))))
    except ValueError:
        wait_sec = 2.0

    total_deleted = 0
    last_audit: dict[str, Any] = {"enabled": True, "deleted": 0, "remaining_first_page": None}
    clear_streak = 0
    for attempt in range(attempts):
        audit = _elevenlabs_scrub_history(api_key)
        total_deleted += int(audit.get("deleted") or 0)
        last_audit = {**audit, "deleted": total_deleted, "attempts": attempt + 1}
        if audit.get("remaining_first_page") == 0 and not audit.get("error"):
            clear_streak += 1
            if clear_streak >= 2:
                return last_audit
        else:
            clear_streak = 0
        if attempt < attempts - 1 and wait_sec:
            time.sleep(wait_sec)
    return last_audit


def _note_confirms_elevenlabs_history_clear(note: str) -> bool:
    return "elevenlabs_history_final_remaining_first_page=0" in str(note)


def _audio_asset_confirms_elevenlabs_history_clear(audio_asset: AudioAsset) -> bool:
    notes = [*audio_asset.notes]
    for timing in audio_asset.scene_timings:
        if isinstance(timing, dict):
            notes.extend(str(note) for note in timing.get("notes", []) if str(note).strip())
    return any(_note_confirms_elevenlabs_history_clear(note) for note in notes)


def _manifest_confirms_elevenlabs_history_clear(manifest: dict[str, Any]) -> bool:
    notes: list[str] = []
    audio = manifest.get("audio_asset") if isinstance(manifest.get("audio_asset"), dict) else {}
    tts_plan = manifest.get("tts_plan") if isinstance(manifest.get("tts_plan"), dict) else {}
    notes.extend(str(note) for note in audio.get("notes", []) if str(note).strip())
    notes.extend(str(note) for note in tts_plan.get("notes", []) if str(note).strip())
    for timing in audio.get("scene_timings", []) if isinstance(audio.get("scene_timings"), list) else []:
        if isinstance(timing, dict):
            notes.extend(str(note) for note in timing.get("notes", []) if str(note).strip())
    return any(_note_confirms_elevenlabs_history_clear(note) for note in notes)


def _tts_pronunciation_alias_terms(text: str) -> list[str]:
    path = PACKAGE_DIR / "account" / "ko_tts_pronunciation.json"
    if not path.exists():
        return []
    try:
        aliases = _config_dict(_load_json(path), "aliases")
    except Exception:
        return []
    return [term for term in aliases if term and term in text][:8]


def build_tts_performance_plan(script: ScriptPackage, angle_brief: AngleBrief) -> TTSPerformancePlan:
    emphasis_terms = [
        str(item)
        for item in TTS_PERFORMANCE_STRATEGY.get("emphasis_terms", [])
        if str(item).strip()
    ]
    scene_plans: list[TTSPerformanceScenePlan] = []
    for scene in script.scenes:
        text = f"{scene.on_screen_text} {scene.body}"
        matched_emphasis = [term for term in emphasis_terms if term in text][:4]
        scene_plans.append(
            TTSPerformanceScenePlan(
                scene_id=scene.scene_id,
                target_duration_sec=scene.duration_sec,
                pacing=str(TTS_PERFORMANCE_STRATEGY.get("default_pacing", "")),
                breath_group="1-2호흡" if len(scene.body) <= BODY_TEXT_MAX_CHARS_MOBILE else "2호흡 이상",
                emphasis_terms=matched_emphasis,
                pronunciation_alias_terms=_tts_pronunciation_alias_terms(text),
                pause_after_sec=float(TTS_PERFORMANCE_STRATEGY.get("pause_after_sec", 0.25)),
                delivery_note=angle_brief.audience_emotion or str(TTS_PERFORMANCE_STRATEGY.get("voice_direction", "")),
            )
        )
    blockers: list[str] = []
    if not angle_brief.gate_passed:
        blockers.append("angle_brief_not_passed")
    if not scene_plans:
        blockers.append("tts_scene_plans_missing")
    if any(plan.target_duration_sec < 5 for plan in scene_plans):
        blockers.append("tts_scene_duration_too_short")
    return TTSPerformancePlan(
        version=str(TTS_PERFORMANCE_STRATEGY.get("version", "tts_performance_plan_v1")),
        voice_direction=str(TTS_PERFORMANCE_STRATEGY.get("voice_direction", "")),
        model_family=str(TTS_PERFORMANCE_STRATEGY.get("model_family", "eleven_multilingual_v2")),
        language=str(TTS_PERFORMANCE_STRATEGY.get("language", "ko")),
        scene_plans=scene_plans,
        gate_passed=not blockers,
        blockers=blockers,
    )


def build_tts_plan(script: ScriptPackage, audio_asset: AudioAsset) -> TTSPlan:
    model_id = _env_value("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2"
    enable_logging = _elevenlabs_enable_logging()
    history_clear = _audio_asset_confirms_elevenlabs_history_clear(audio_asset)
    publish_candidate = (
        audio_asset.provider == "elevenlabs"
        and audio_asset.status == "generated"
        and not enable_logging
        and history_clear
    )
    timing_by_scene = {
        int(row.get("scene_id")): row
        for row in audio_asset.scene_timings
        if isinstance(row, dict) and row.get("scene_id") is not None
    }
    combined_lint = _read_json_object_if_exists(audio_asset.lint_path)
    scene_texts: list[TTSScenePlan] = []
    warnings: list[str] = [str(item) for item in combined_lint.get("warnings", []) if str(item).strip()]
    notes: list[str] = [str(item) for item in audio_asset.notes if str(item).strip()]
    for scene in script.scenes:
        timing = timing_by_scene.get(scene.scene_id, {})
        lint = _read_json_object_if_exists(timing.get("lint_path"))
        tts_text = _read_text_if_exists(timing.get("tts_text_path")) or _preprocess_korean_tts(scene.body).text
        scene_warnings = [str(item) for item in lint.get("warnings", []) if str(item).strip()]
        scene_replacements = [str(item) for item in lint.get("replacements", []) if str(item).strip()]
        timing_notes = [str(item) for item in timing.get("notes", []) if str(item).strip()]
        notes.extend(timing_notes)
        warnings.extend(f"scene_{scene.scene_id:02d}:{warning}" for warning in scene_warnings)
        scene_texts.append(
            TTSScenePlan(
                scene_id=scene.scene_id,
                source_text=scene.body,
                tts_text=tts_text,
                tts_text_path=str(timing.get("tts_text_path")) if timing.get("tts_text_path") else None,
                lint_path=str(timing.get("lint_path")) if timing.get("lint_path") else None,
                provider=str(timing.get("provider")) if timing.get("provider") else None,
                status=str(timing.get("status")) if timing.get("status") else None,
                card_duration_sec=int(timing["card_duration_sec"]) if timing.get("card_duration_sec") is not None else None,
                audio_duration_sec=float(timing["audio_duration_sec"]) if timing.get("audio_duration_sec") is not None else None,
                warnings=scene_warnings,
                replacements=scene_replacements,
            )
        )
    return TTSPlan(
        version="tts_plan_v1",
        provider="elevenlabs",
        actual_provider=audio_asset.provider,
        status=audio_asset.status,
        publish_candidate=publish_candidate,
        voice=_env_value("ELEVENLABS_VOICE_NAME") or "Anna Kim",
        model=model_id,
        language_code=_env_value("ELEVENLABS_LANGUAGE_CODE") or "ko",
        output_format=_env_value("ELEVENLABS_OUTPUT_FORMAT") or "mp3_44100_128",
        enable_logging=enable_logging,
        voice_settings=_elevenlabs_voice_settings(model_id),
        scene_texts=scene_texts,
        warnings=list(dict.fromkeys(warnings)),
        notes=list(dict.fromkeys(notes)),
    )


def build_render_manifest(
    *,
    run_id: str,
    render_scenes: list[Scene],
    visual_beats: list[VisualBeat],
    mp4_path: Path,
    video_only_path: Path,
    storyboard_path: Path,
    mobile_storyboard_path: Path,
    mobile_checks_path: Path,
    frames_dir: Path,
    render_textfit_report_path: Path | None = None,
    gate: GateResult,
    readability: ReadabilityResult,
    review: ContentReview,
    quality: PublishQualityResult,
    audio_asset: AudioAsset,
    visual_quality: VisualQualityResult,
    synced_duration_matches_format: bool,
    mobile_visual_passed: bool,
    layout_quality: dict[str, Any] | None = None,
    visual_cadence: VisualCadencePlan | None = None,
) -> RenderManifest:
    duration_sec = sum(scene.duration_sec for scene in render_scenes)
    motion = _visual_motion_summary(visual_beats)
    layout_quality = layout_quality or {"passed": True}
    cadence = visual_cadence or plan_visual_cadence(render_scenes)
    artifacts = {
        "mp4": str(mp4_path),
        "video_only_mp4": str(video_only_path),
        "storyboard": str(storyboard_path),
        "mobile_preview_storyboard": str(mobile_storyboard_path),
        "mobile_visual_checks": str(mobile_checks_path),
        "frames_dir": str(frames_dir),
        "audio_path": audio_asset.path,
    }
    if render_textfit_report_path is not None:
        artifacts["render_textfit_report"] = str(render_textfit_report_path)
    return RenderManifest(
        version="render_manifest_v1",
        run_id=run_id,
        target_size=f"{CANVAS_WIDTH}x{CANVAS_HEIGHT}",
        fps=VIDEO_FPS,
        codec=VIDEO_CODEC,
        video_bitrate=VIDEO_BITRATE,
        scene_count=len(render_scenes),
        duration_sec=duration_sec,
        static_hold_images=bool(motion["all_static_hold"]),
        transition_policy="scene_boundary_only",
        safe_zones={
            "right_rail_left_px": TIKTOK_RIGHT_RAIL_LEFT,
            "bottom_ui_top_px": TIKTOK_BOTTOM_UI_TOP,
            "text_safe_left_px": TEXT_SAFE_LEFT,
            "text_safe_right_px": TEXT_SAFE_RIGHT,
            "critical_text_bottom_px": CRITICAL_TEXT_BOTTOM,
        },
        visual_motion=motion,
        visual_cadence=asdict(cadence),
        artifacts=artifacts,
        gates={
            "policy": gate.passed,
            "readability": readability.passed,
            "content_review": review.passed,
            "publish_quality": quality.passed,
            "visual_quality": visual_quality.passed,
            "audio_publish_candidate": (
                audio_asset.provider == "elevenlabs"
                and audio_asset.status == "generated"
                and _elevenlabs_zero_retention_requested()
            ),
            "mobile_visual": mobile_visual_passed,
            "layout_variety": bool(layout_quality.get("passed")),
            "duration": synced_duration_matches_format,
        },
    )


def build_upload_plan(
    *,
    run_id: str,
    script: ScriptPackage,
    format_plan: ContentFormatPlan,
    validation: dict[str, Any],
    mp4_path: Path,
    planned_publish_at_local: str | None = None,
) -> UploadPlan:
    publish_ready = validation.get("publish_ready") is True
    blockers = [str(item) for item in validation.get("blockers", []) if str(item).strip()]
    return UploadPlan(
        version="upload_plan_v1",
        run_id=run_id,
        status="planned" if publish_ready else "blocked",
        required_status="publish_ready",
        manifest_status=str(validation.get("status", "needs_revision")),
        caption=script.caption,
        post_title=script.post_title,
        hashtags=script.hashtags,
        aigc_label_required=True,
        schedule_time_local=planned_publish_at_local,
        schedule_reason=(
            f"planned slot from schedule: {planned_publish_at_local}"
            if planned_publish_at_local
            else f"format default slot {format_plan.upload_slot}; not assigned to calendar yet"
        ),
        mp4_path=str(mp4_path),
        blockers=blockers,
        stop_conditions=[
            "login_required",
            "captcha_or_security_prompt",
            "account_restriction",
            "manifest_not_publish_ready",
        ],
        human_confirmation_required=True,
    )


def _matched_trend_clusters(text: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    for cluster in HOT_TOPIC_TREND_CLUSTERS:
        terms = [str(term) for term in cluster.get("terms", []) if str(term).strip()]
        matched_terms = [term for term in terms if term in text]
        if not matched_terms:
            continue
        try:
            score_bonus = int(cluster.get("score_bonus", 0))
        except (TypeError, ValueError):
            score_bonus = 0
        matches.append(
            {
                "cluster_id": str(cluster.get("cluster_id", "")),
                "label": str(cluster.get("label", "")),
                "matched_terms": matched_terms,
                "score_bonus": score_bonus,
                "editorial_frame": str(cluster.get("editorial_frame", "")),
                "risk_controls": [
                    str(item) for item in cluster.get("risk_controls", []) if str(item).strip()
                ],
            }
        )
    return matches


def is_low_growth_topic(title: str) -> bool:
    has_weak_admin_shape = any(term in title for term in HOT_TOPIC_WEAK_ADMIN_TERMS)
    has_concrete_stakes = any(term in title for term in [*HOT_TOPIC_CONCRETE_STAKES_TERMS, *HOT_TOPIC_HARD_NEWS_TERMS])
    has_account_reference = any(term in title for term in HOT_TOPIC_ACCOUNT_REFERENCE_TERMS)
    return has_weak_admin_shape and not (has_concrete_stakes or has_account_reference)


def _score_hot_topic(title: str, publisher: str, published_at: dt.datetime) -> int:
    now = dt.datetime.now(dt.timezone.utc)
    age_hours = max(0.0, (now - published_at).total_seconds() / 3600)
    score = max(0, _topic_score_weight("recency_base", 36) - int(age_hours))
    score += sum(_topic_score_weight("target_term", 10) for term in HOT_TOPIC_TARGET_TERMS if term in title)
    score += (
        _topic_score_weight("trusted_source_bonus", 16)
        if _publisher_is_trusted(publisher)
        else _topic_score_weight("untrusted_source_penalty", -18)
    )
    score += sum(_topic_score_weight("hard_news_term", 8) for term in HOT_TOPIC_HARD_NEWS_TERMS if term in title)
    score += sum(
        _topic_score_weight("left_audience_term", 8) for term in HOT_TOPIC_LEFT_AUDIENCE_TERMS if term in title
    )
    score += sum(
        _topic_score_weight("account_reference_term", 12)
        for term in HOT_TOPIC_ACCOUNT_REFERENCE_TERMS
        if term in title
    )
    score += sum(
        _topic_score_weight("concrete_stakes_term", 9)
        for term in HOT_TOPIC_CONCRETE_STAKES_TERMS
        if term in title
    )
    for cluster in _matched_trend_clusters(title):
        matched_count = len(cluster.get("matched_terms", []))
        score += min(
            int(cluster.get("score_bonus", 0)),
            matched_count * _topic_score_weight("trend_cluster_term_bonus", 7),
        )
    score += sum(_topic_score_weight("weak_admin_penalty", -52) for term in HOT_TOPIC_WEAK_ADMIN_TERMS if term in title)
    if not any(term in title for term in HOT_TOPIC_ACCOUNT_REFERENCE_TERMS):
        score += _topic_score_weight("no_account_reference_penalty", -16)
    if is_low_growth_topic(title):
        score += _topic_score_weight("low_growth_topic_penalty", -60)
    score += sum(_topic_score_weight("risk_term_penalty", -8) for term in HOT_TOPIC_RISK_TERMS if term in title)
    if any(marker in title for marker in HOT_TOPIC_OPINION_TERMS):
        score += _topic_score_weight("opinion_penalty", -18)
    if any(marker in title for marker in HOT_TOPIC_LOW_NEWS_TERMS):
        score += _topic_score_weight("low_news_penalty", -24)
    return max(0, score)


def _fetch_google_news_items(query: str, *, limit: int | None = None) -> list[HotTopicItem]:
    rss_config = _config_dict(HOT_TOPIC_STRATEGY, "rss")
    lookback_days = max(1, min(7, _strategy_int(rss_config, "lookback_days", 2)))
    per_query_limit = max(1, min(50, int(limit or _strategy_int(rss_config, "per_query_limit", 12))))
    rss_url = "https://news.google.com/rss/search?" + urlencode(
        {
            "q": f"{query} when:{lookback_days}d",
            "hl": "ko",
            "gl": "KR",
            "ceid": "KR:ko",
        }
    )
    try:
        with urllib.request.urlopen(rss_url, timeout=20) as response:
            raw_xml = response.read()
    except Exception:
        return []

    try:
        root = ET.fromstring(raw_xml)
    except ET.ParseError:
        return []

    items: list[HotTopicItem] = []
    for item in root.findall("./channel/item")[:per_query_limit]:
        title, publisher = _clean_news_title(item.findtext("title") or "")
        if len(title) < 12:
            continue
        published = _parse_pub_date(item.findtext("pubDate"))
        items.append(
            HotTopicItem(
                title=title,
                publisher=publisher or "Google News",
                url=item.findtext("link") or "",
                published_at=published.isoformat(),
                query=query,
                score=_score_hot_topic(title, publisher, published),
            )
        )
    return items


def _topic_discovery_fallback(reason: str) -> tuple[TopicCandidate, dict[str, Source], dict[str, Any]]:
    topic = collect_topic({})
    return topic, {}, {"mode": "fallback_static", "reason": reason, "candidates": []}


def discover_hot_topic(
    style: dict[str, Any],
    performance_feedback: dict[str, Any] | None = None,
) -> tuple[TopicCandidate, dict[str, Source], dict[str, Any]]:
    del style
    if performance_feedback is None:
        performance_feedback = load_performance_feedback()
    candidates: list[HotTopicItem] = []
    queried: set[str] = set()
    seed_candidates: list[HotTopicItem] = []
    for query in KEYWORD_BASE_QUERIES:
        queried.add(query)
        seed_candidates.extend(_fetch_google_news_items(query))
    signal_snapshot = build_signal_snapshot(seed_candidates)
    keyword_plan = build_keyword_plan(seed_candidates, performance_feedback=performance_feedback)
    candidates.extend(seed_candidates)
    for query in keyword_plan.expanded_queries:
        if query in queried:
            continue
        queried.add(query)
        candidates.extend(_fetch_google_news_items(query))
    if not candidates:
        for query in HOT_TOPIC_QUERIES:
            if query in queried:
                continue
            candidates.extend(_fetch_google_news_items(query))
    term_frequency = {
        term: sum(1 for item in candidates if term in item.title)
        for term in HOT_TOPIC_TARGET_TERMS
    }
    priority_queries = set(HOT_TOPIC_PRIORITY_QUERIES) | set(keyword_plan.expanded_queries[:8])
    candidates = [
        replace(
            item,
            score=item.score
            + (
                0
                if any(marker in item.title for marker in HOT_TOPIC_OPINION_TERMS)
                else sum(
                    min(
                        _topic_score_weight("frequency_term_cap", 12),
                        term_frequency[term] * _topic_score_weight("frequency_term_multiplier", 3),
                    )
                    for term in HOT_TOPIC_TARGET_TERMS
                    if term in item.title
                )
            )
            + (_topic_score_weight("priority_query_bonus", 6) if item.query in priority_queries else 0),
        )
        for item in candidates
    ]
    if performance_feedback.get("enabled"):
        candidates = [
            replace(
                item,
                score=item.score
                + _performance_feedback_adjustment(
                    f"{item.title} {item.query} {item.publisher}",
                    performance_feedback,
                ),
            )
            for item in candidates
        ]

    deduped: dict[str, HotTopicItem] = {}
    for item in candidates:
        key = re.sub(r"[^0-9A-Za-z가-힣]", "", item.title)[:42]
        if not key:
            continue
        current = deduped.get(key)
        if current is None or item.score > current.score:
            deduped[key] = item

    ranked_all = sorted(deduped.values(), key=lambda item: (item.score, item.published_at), reverse=True)
    if not ranked_all:
        return _topic_discovery_fallback("news_rss_empty")

    ranked = [
        item
        for item in ranked_all
        if _publisher_is_trusted(item.publisher) or _cluster_support_count(item, ranked_all) >= 2
    ] or ranked_all
    selected = ranked[0]
    supporting = _select_supporting_hot_topics(selected, ranked_all)
    topic_pool = build_topic_pool(ranked_all, keyword_plan)
    topic_plan = build_topic_plan(selected, supporting, topic_pool, keyword_plan)
    deep_research_report = build_deep_research_report(
        signal_snapshot,
        keyword_plan,
        topic_pool,
        topic_plan,
        performance_feedback=performance_feedback,
    )
    selected_by_deep_research = False
    if deep_research_report.selected_topic_id != topic_plan.selected_topic_id:
        deep_candidate = next(
            (
                candidate
                for candidate in topic_pool.candidates
                if candidate.topic_id == deep_research_report.selected_topic_id
            ),
            None,
        )
        deep_item = next(
            (item for item in ranked_all if deep_candidate is not None and item.title == deep_candidate.title),
            None,
        )
        if deep_item is not None:
            selected = deep_item
            supporting = _select_supporting_hot_topics(selected, ranked_all)
            topic_plan = build_topic_plan(selected, supporting, topic_pool, keyword_plan)
            deep_research_report = build_deep_research_report(
                signal_snapshot,
                keyword_plan,
                topic_pool,
                topic_plan,
                performance_feedback=performance_feedback,
            )
            selected_by_deep_research = True
    picked = [selected, *supporting]
    sources: dict[str, Source] = {}
    claims: list[Claim] = []
    claim_template = str(HOT_TOPIC_CANDIDATE_STRATEGY.get("claim_text_template", ""))
    for index, item in enumerate(picked, start=1):
        source_id = f"hot_news_{index:02d}"
        sources[source_id] = Source(
            source_id=source_id,
            title=f"{item.publisher}: {item.title}",
            url=item.url,
            note=f"Google News RSS query={item.query}; published={item.published_at}; heat_score={item.score}",
        )
        claims.append(
            Claim(
                text=_format_prompt_template(
                    claim_template,
                    {"publisher": item.publisher, "title": item.title, "query": item.query},
                ),
                source_ids=[source_id],
                risk="medium" if any(term in item.title for term in HOT_TOPIC_RISK_TERMS) else "low",
            )
        )

    topic = TopicCandidate(
        title=_clean_card_text(selected.title),
        angle="; ".join(
            item
            for item in [
                str(HOT_TOPIC_CANDIDATE_STRATEGY.get("angle", "")),
                deep_research_report.selected_archetype_label,
                deep_research_report.selected_research_question,
            ]
            if item
        ),
        slot=str(HOT_TOPIC_CANDIDATE_STRATEGY.get("slot", "")),
        target_duration_sec=_strategy_int(HOT_TOPIC_CANDIDATE_STRATEGY, "target_duration_sec", 75),
        claims=claims,
        source_ids=[f"hot_news_{index:02d}" for index in range(1, len(picked) + 1)],
    )
    return topic, sources, {
        "mode": "google_news_rss",
        "signal_snapshot": asdict(signal_snapshot),
        "queries": keyword_plan.expanded_queries,
        "keyword_plan": asdict(keyword_plan),
        "deep_research_report": asdict(deep_research_report),
        "performance_feedback": {
            "enabled": bool(performance_feedback.get("enabled")),
            "path": performance_feedback.get("path"),
            "sample_count": performance_feedback.get("sample_count", 0),
            "term_scores": performance_feedback.get("term_scores", {}),
            "format_scores": performance_feedback.get("format_scores", {}),
            "visual_scores": performance_feedback.get("visual_scores", {}),
            "positive_terms": performance_feedback.get("positive_terms", [])[:12],
            "negative_terms": performance_feedback.get("negative_terms", [])[:12],
        },
        "topic_pool": asdict(topic_pool),
        "topic_plan": asdict(topic_plan),
        "selected_by_deep_research": selected_by_deep_research,
        "trend_cluster_scoring": True,
        "selected_trend_clusters": _matched_trend_clusters(selected.title),
        "selected": asdict(selected),
        "supporting_count": len(supporting),
        "supporting": [asdict(item) for item in supporting],
        "candidates": [asdict(item) for item in ranked_all[: max(12, len(HOT_TOPIC_QUERIES) * 6)]],
    }


def _hot_claim_text(topic: TopicCandidate, index: int, fallback: str) -> str:
    if index >= len(topic.claims):
        return fallback
    text = topic.claims[index].text
    text = re.sub(r"^[^:]+:\s*", "", text)
    return _compact_card_text(text, BODY_TEXT_MAX_CHARS_MOBILE)


def _hot_primary_hook_term(title: str) -> str:
    suppressed = {
        str(term)
        for term in HOT_TOPIC_STRATEGY.get("hook_suppressed_terms", [])
        if str(term).strip()
    }
    for token in re.findall(r"[가-힣A-Za-z0-9]{2,}", title):
        cleaned = re.sub(r"(에서|에게|으로|부터|까지|하고|라는|처럼|보다|은|는|이|가|을|를|의|도|만|와|과)$", "", token)
        if not cleaned or cleaned in SEARCH_STOPWORDS or cleaned in suppressed:
            continue
        return cleaned
    return _compact_card_text(title, 12)


def _configured_hot_hook_headline(title: str) -> str:
    values = {
        "primary_term": _hot_primary_hook_term(title),
        "topic_title": title,
    }
    for rule in HOT_HOOK_HEADLINE_RULES:
        if not isinstance(rule, dict):
            continue
        must_include = [str(term) for term in rule.get("must_include", []) if str(term).strip()]
        any_include = [str(term) for term in rule.get("any_include", []) if str(term).strip()]
        if must_include and not all(term in title for term in must_include):
            continue
        if any_include and not any(term in title for term in any_include):
            continue
        headline = str(rule.get("headline", "")).strip()
        if headline:
            return _compact_card_text(_format_prompt_template(headline, values), 26, keep_question="?" in headline)
    return ""


def _hot_hook_headline(title: str) -> str:
    configured = _configured_hot_hook_headline(title)
    if configured:
        return configured
    values = {
        "primary_term": _hot_primary_hook_term(title),
        "topic_title": title,
    }
    return _compact_card_text(
        _format_prompt_template(HOT_HOOK_FALLBACK_HEADLINE, values),
        26,
        keep_question="?" in HOT_HOOK_FALLBACK_HEADLINE,
    )


def _hot_visual_for_text(text: str, role: str, topic_context: str = "") -> str:
    text = _clean_card_text(text)
    combined_text = f"{topic_context} {text}".strip()
    issue_type = _infer_visual_issue_type(combined_text)
    issue_profile = VISUAL_ISSUE_PROFILES.get(issue_type, VISUAL_ISSUE_PROFILES["civic_fact_check"])
    role_profile = VISUAL_ROLE_PROFILES.get(role, VISUAL_ROLE_PROFILES["evidence"])
    issue_anchors = list(issue_profile.get("anchors", []))
    role_anchor_override = VISUAL_ROLE_ISSUE_ANCHOR_OVERRIDES.get(role, [])
    if issue_type != "civic_fact_check":
        anchors = list(dict.fromkeys([*issue_anchors, *role_anchor_override, *role_profile.get("anchors", [])]))[:5]
    else:
        anchors = list(dict.fromkeys([*role_profile.get("anchors", []), *role_anchor_override]))[:5]
    location = _visual_location_for_role_issue(role, issue_type, role_profile, issue_profile)
    camera = str(role_profile.get("camera"))
    palette = str(role_profile.get("palette") or issue_profile.get("palette"))
    reality_beat = VISUAL_ROLE_REALITY_BEATS.get(role, "")
    intensity_beat = VISUAL_ROLE_INTENSITY_BEATS.get(role, "")
    return _format_prompt_template(
        str(VISUAL_HOT_PROMPTING.get("template", "")),
        {
            "base": VISUAL_HOT_PROMPTING.get("base", ""),
            "reality_beat": reality_beat,
            "intensity_beat": intensity_beat,
            "location": location,
            "camera": camera,
            "anchors": ", ".join(anchors),
            "palette": palette,
            "composition": VISUAL_HOT_PROMPTING.get("composition", ""),
            "texture": VISUAL_HOT_PROMPTING.get("texture", ""),
            "people_safety": VISUAL_HOT_PROMPTING.get("people_safety", ""),
            "policy_safety": VISUAL_HOT_PROMPTING.get("policy_safety", ""),
        },
    )


def _deep_research_script_values(topic_discovery: dict[str, Any] | None) -> dict[str, str]:
    defaults = {key: str(value) for key, value in DEEP_RESEARCH_DEFAULT_VALUES.items()}
    report = topic_discovery.get("deep_research_report") if isinstance(topic_discovery, dict) else None
    angle_brief = topic_discovery.get("angle_brief") if isinstance(topic_discovery, dict) else None
    fact_pack = topic_discovery.get("fact_pack") if isinstance(topic_discovery, dict) else None
    if not isinstance(report, dict):
        values = dict(defaults)
        if isinstance(angle_brief, dict):
            values.update(_angle_brief_script_values(angle_brief))
        if isinstance(fact_pack, dict):
            values.update(_fact_pack_script_values(fact_pack))
        return values
    selected_id = str(report.get("selected_topic_id", ""))
    candidates = report.get("topic_candidates")
    selected_candidate = None
    if isinstance(candidates, list):
        selected_candidate = next(
            (candidate for candidate in candidates if isinstance(candidate, dict) and candidate.get("topic_id") == selected_id),
            None,
        )
        if selected_candidate is None:
            selected_candidate = next((candidate for candidate in candidates if isinstance(candidate, dict)), None)
    values = dict(defaults)
    if isinstance(selected_candidate, dict):
        values.update(
            {
                "reference_label": str(selected_candidate.get("matched_archetype_label") or values.get("reference_label", "")),
                "research_question": str(selected_candidate.get("research_question") or values.get("research_question", "")),
                "counterpoint_focus": str(selected_candidate.get("counterpoint_focus") or values.get("counterpoint_focus", "")),
                "comment_trigger": str(selected_candidate.get("comment_trigger") or values.get("comment_trigger", "")),
                "follower_promise": str(selected_candidate.get("follower_promise") or values.get("follower_promise", "")),
                "deep_research_comment_trigger": str(selected_candidate.get("comment_trigger") or ""),
                "deep_research_counterpoint_focus": str(selected_candidate.get("counterpoint_focus") or ""),
            }
        )
    values["selected_archetype_label"] = str(
        report.get("selected_archetype_label") or values.get("reference_label", "")
    )
    values["selected_research_question"] = str(
        report.get("selected_research_question") or values.get("research_question", "")
    )
    values["deep_research_question"] = values["selected_research_question"]
    if isinstance(angle_brief, dict):
        values.update(_angle_brief_script_values(angle_brief))
    if isinstance(fact_pack, dict):
        values.update(_fact_pack_script_values(fact_pack))
    return values


def _angle_brief_script_values(angle_brief: dict[str, Any]) -> dict[str, str]:
    return {
        "viewer_promise": str(angle_brief.get("viewer_promise") or ""),
        "one_sentence_thesis": str(angle_brief.get("one_sentence_thesis") or ""),
        "safe_provocation": str(angle_brief.get("safe_provocation") or ""),
        "comment_trigger": str(angle_brief.get("comment_question") or ""),
        "follower_promise": str(angle_brief.get("follow_reason") or ""),
    }


def _fact_pack_script_values(fact_pack: dict[str, Any]) -> dict[str, str]:
    reported = fact_pack.get("reported_claims")
    confirmed = fact_pack.get("confirmed_facts")
    unanswered = fact_pack.get("unanswered_questions")

    def first_text(rows: Any) -> str:
        if not isinstance(rows, list):
            return ""
        first = next((row for row in rows if isinstance(row, dict) and str(row.get("text", "")).strip()), None)
        return str(first.get("text", "")) if isinstance(first, dict) else ""

    return {
        "first_reported_claim": first_text(reported),
        "first_confirmed_fact": first_text(confirmed),
        "first_unanswered_question": first_text(unanswered),
    }


def _topic_claim_lines(topic: TopicCandidate) -> list[str]:
    lines: list[str] = []
    for claim in topic.claims:
        text = _clean_card_text(claim.text)
        text = re.sub(r"^[^:]{1,32}:\s*", "", text)
        if text:
            lines.append(text)
    return lines


def _topic_issue_basis(topic: TopicCandidate) -> str:
    return _clean_card_text(
        " ".join([topic.title, topic.angle, topic.slot, *_topic_claim_lines(topic)])
    )


def _issue_anchor_terms(text: str, preferred_terms: list[str]) -> list[str]:
    anchors = [term for term in preferred_terms if term and term in text]
    for token in re.findall(r"[가-힣A-Za-z0-9·.]{2,}", text):
        token = token.strip("·.")
        for suffix in (
            "에서",
            "에게",
            "으로",
            "부터",
            "까지",
            "하고",
            "라는",
            "처럼",
            "보다",
            "은",
            "는",
            "이",
            "가",
            "을",
            "를",
            "의",
            "도",
            "만",
            "와",
            "과",
        ):
            if len(token) > len(suffix) + 1 and token.endswith(suffix):
                token = token[: -len(suffix)]
                break
        if not token or token in SEARCH_STOPWORDS or token in HOT_TOPIC_BROAD_CLUSTER_TOKENS:
            continue
        if token not in anchors:
            anchors.append(token)
        if len(anchors) >= 8:
            break
    return anchors


def _date_anchor(text: str) -> str:
    match = re.search(r"(?:내달|다음 달|오는)?\s*\d{1,2}일|20\d{2}[.-]\d{1,2}[.-]\d{1,2}", text)
    return _clean_card_text(match.group(0)) if match else ""


def _issue_brief_script_values(topic: TopicCandidate) -> dict[str, str]:
    text = _topic_issue_basis(topic)
    claim_lines = _topic_claim_lines(topic)
    primary_claim = claim_lines[0] if claim_lines else topic.title
    support_claim = next((line for line in claim_lines[1:] if line != primary_claim), primary_claim)
    date_anchor = _date_anchor(text)
    values = {
        "case_thesis": "핵심은 누가 이겼냐가 아니라, 확인된 보도와 남은 책임선입니다.",
        "what_happened": _compact_card_text(primary_claim, 88),
        "why_now": "오늘 보도에서 같은 쟁점이 반복되며 다시 커졌습니다.",
        "fact_anchor_line": _compact_card_text(support_claim, 88),
        "missing_line": "아직 남은 건 주장과 확인된 사실 사이의 빈칸입니다.",
        "share_line": "이건 반대 의견까지 붙어야 쟁점이 선명해지는 사안입니다.",
        "cta_sentence": "반론까지 보고, 당신은 어느 쪽인지 댓글로 남겨주세요.",
    }

    if "김건희" in text and "특검" in text:
        values.update(
            {
                "reference_label": "김건희 특검과 다음 책임선",
                "case_thesis": "핵심은 의혹 단정이 아니라 특검 수사가 어디까지 이어지는지입니다.",
                "why_now": "윤석열 전 대통령 조사 이후 김건희 관련 수사 방향이 다시 보도되고 있습니다.",
                "fact_anchor_line": "반복되는 축은 특검, 김건희, 윗선, 수사 범위입니다.",
                "missing_line": "아직 남은 건 실제 소환과 확인된 혐의 범위입니다.",
                "research_question": "김건희 특검에서 확인된 보도와 아직 비어 있는 책임선은 무엇인가?",
                "counterpoint_focus": "수사 필요성, 정치공세 반론, 아직 확정되지 않은 사실관계",
                "comment_trigger": "1 소환 시점, 2 윗선 책임, 3 정치공세 반론 중 무엇부터 봐야 하나요?",
                "follower_promise": "특검 흐름과 반론을 확인된 보도 기준으로 계속 추적합니다.",
                "share_line": "특검 과잉인지, 책임 추적인지 댓글이 갈릴 지점입니다.",
                "cta_sentence": "수사 필요성인가 정치공세인가. 당신은 어디에 서나요?",
                "stakes_line": "김건희 특검의 핵심은 분노보다 수사 범위와 책임선입니다.",
                "conflict_line": "한쪽은 성역 없는 수사를 말하고, 다른 쪽은 정치공세라고 반박합니다.",
                "viewer_identity_line": "시민 기준은 이름값보다 확인된 보도와 아직 비어 있는 절차를 나누는 것입니다.",
                "next_watch_line": "다음 포인트는 실제 소환, 압수수색, 혐의 범위가 어디까지 공개되는지입니다.",
            }
        )
    elif "윤석열" in text and "특검" in text and any(term in text for term in ["계엄", "무인기", "종합특검"]):
        values.update(
            {
                "reference_label": "윤석열 특검과 계엄 의혹 책임선",
                "case_thesis": "핵심은 정치적 호불호가 아니라 특검이 확인할 지시와 책임 범위입니다.",
                "why_now": "첫 소환과 관련 재판 일정이 겹치며 책임선 보도가 다시 커지고 있습니다.",
                "fact_anchor_line": "반복되는 축은 윤석열, 종합특검, 계엄, 무인기, 소환조사입니다.",
                "missing_line": "아직 남은 건 지시 여부와 수사로 확인될 문서, 진술, 반론입니다.",
                "research_question": "윤석열 특검에서 확인된 보도와 아직 비어 있는 책임선은 무엇인가?",
                "counterpoint_focus": "특검 주장, 피의자 측 반론, 아직 확정되지 않은 수사 결과",
                "comment_trigger": "1 계엄 의혹, 2 무인기 쟁점, 3 윗선 책임 중 무엇부터 봐야 하나요?",
                "follower_promise": "특검 조사와 재판 일정이 만드는 책임선을 계속 추적합니다.",
                "share_line": "책임 추적인지 정치보복인지 댓글이 갈릴 수밖에 없는 장면입니다.",
                "cta_sentence": "책임 추적인가 정치보복인가. 당신은 어디에 서나요?",
                "stakes_line": "윤석열 특검의 핵심은 감정이 아니라 지시, 문서, 진술이 만나는 책임선입니다.",
                "conflict_line": "한쪽은 계엄 의혹의 윗선을 묻고, 다른 쪽은 정치보복 프레임으로 맞섭니다.",
                "viewer_identity_line": "시민 기준은 분노보다 확인된 절차와 반론을 끝까지 보는 것입니다.",
                "next_watch_line": "다음 포인트는 소환조사 이후 공개되는 진술과 문서입니다.",
            }
        )
    elif any(term in text for term in ["위증", "구형", "징역", "선고", "재판", "법원", "1심", "항소심"]):
        anchors = _issue_anchor_terms(text, ["위증", "구형", "징역", "선고", "1심", "한덕수", "윤석열", "특검"])
        anchor_text = ", ".join(anchors[:4]) if anchors else "위증 혐의와 선고 기준"
        values.update(
            {
                "reference_label": f"{anchor_text}을 잇는 재판 쟁점",
                "case_thesis": "핵심은 유죄 단정이 아니라 위증 혐의, 특검 구형, 1심 선고 기준입니다.",
                "why_now": (
                    f"{date_anchor} 선고를 앞두고 특검 구형과 피고인 측 반론이 다시 보도되고 있습니다."
                    if date_anchor
                    else "선고를 앞두고 특검 구형과 피고인 측 반론이 다시 보도되고 있습니다."
                ),
                "fact_anchor_line": f"보도에서 반복된 단어는 {anchor_text}입니다. 이 단어들이 사건의 순서를 만듭니다.",
                "missing_line": "아직 남은 건 법원이 위증 여부와 계엄 당일 국무회의 경위를 어떻게 볼지입니다.",
                "research_question": "위증 혐의에서 확인된 보도와 아직 법원이 판단할 부분은 무엇인가?",
                "counterpoint_focus": "특검 주장, 피고인 측 반론, 아직 확정되지 않은 법원 판단",
                "comment_trigger": "1 위증 쟁점, 2 국무회의 경위, 3 선고 기준 중 무엇부터 봐야 하나요?",
                "follower_promise": "선고 전후로 바뀌는 책임선과 반론을 계속 추적합니다.",
                "share_line": "특검이 과한 건지, 책임 추적이 당연한 건지 댓글이 갈릴 지점입니다.",
                "cta_sentence": "특검 과잉인가, 책임 추적인가. 당신은 어디에 서나요?",
                "stakes_line": "재판 뉴스의 핵심은 감정이 아니라, 어떤 진술이 법적으로 어떻게 판단되는가입니다.",
                "conflict_line": "특검은 허위 증언을 주장하고, 피고인 측은 허위가 아니라고 다툽니다.",
                "viewer_identity_line": "시민이 볼 기준은 한쪽 응원이 아니라 구형, 반론, 선고의 순서입니다.",
                "next_watch_line": "다음 포인트는 선고문에서 어떤 사실관계가 인정되는지입니다.",
            }
        )
    elif any(term in text for term in ["일베", "혐오", "조롱", "징벌", "폐쇄"]):
        values.update(
            {
                "reference_label": "추도식 조롱 논란과 혐오 조장 책임",
                "case_thesis": "이걸 표현의 자유라고 볼지, 혐오 장사 방치라고 볼지가 핵심입니다.",
                "why_now": "고(故) 노무현 전 대통령 추도식 조롱 논란 뒤, 혐오 조장 사이트 책임론이 커졌습니다.",
                "fact_anchor_line": "보도에서 반복된 축은 조롱 논란, 혐오 조장, 폐쇄 검토, 징벌배상입니다.",
                "missing_line": "우파 반론은 표현의 자유 침해입니다. 반대쪽 질문은 왜 혐오 장사는 보호받느냐입니다.",
                "research_question": "혐오 조장 사이트 책임을 어디까지 제도화할 수 있나?",
                "counterpoint_focus": "표현의 자유 우려와 혐오 조장 방치 책임의 경계",
                "comment_trigger": "1 표현의 자유, 2 혐오 방치, 3 징벌배상. 어디에 서나요?",
                "follower_promise": "국무회의 지시와 후속 입법 논의를 계속 추적합니다.",
                "share_line": "이건 좌우가 같은 댓글창에서 정면으로 부딪힐 수밖에 없는 질문입니다.",
                "cta_sentence": "표현의 자유냐, 혐오 방치냐. 반론까지 보고 어디에 서는지 댓글로 남겨주세요.",
                "stakes_line": "추모의 문제를 넘어, 혐오를 방치하는 플랫폼 책임의 선을 묻는 사안입니다.",
                "conflict_line": "한쪽은 혐오 방치 책임을 말하고, 다른 쪽은 표현의 자유 침해를 우려합니다.",
                "viewer_identity_line": "시민 기준은 조롱을 소비하는 게 아니라 책임과 자유의 경계를 확인하는 것입니다.",
                "next_watch_line": "다음 포인트는 실제 국무회의 지시와 법제화 범위입니다.",
            }
        )
    elif any(term in text for term in ["스타벅스", "탱크데이", "5·18", "5.18"]):
        values.update(
            {
                "reference_label": "5·18 비하 논란과 공적 책임",
                "case_thesis": "핵심은 기업 실수 하나가 아니라 5·18 기억을 대하는 공적 태도입니다.",
                "why_now": "5·18 비하 마케팅 비판에 정치권 반박이 붙으면서 선거 국면 쟁점으로 번졌습니다.",
                "fact_anchor_line": "반복된 축은 5·18 비하 논란, 사과 요구, 공적 권한 개입 우려입니다.",
                "missing_line": "아직 남은 건 사과 이후에도 어떤 책임 기준을 세울지입니다.",
                "research_question": "5·18 기억 훼손 논란에서 공적 비판과 과잉 개입의 선은 어디인가?",
                "counterpoint_focus": "기업 책임, 시민 불매, 공적 권한 개입 우려의 경계",
                "comment_trigger": "1 기업 책임, 2 5·18 기억, 3 공권력 우려 중 무엇부터 봐야 하나요?",
                "follower_promise": "사과 이후 정치권 반응과 책임 기준을 계속 추적합니다.",
                "share_line": "불매가 정당한 시민 비판인지, 과한 압박인지 댓글이 갈릴 지점입니다.",
                "cta_sentence": "불매는 책임 요구인가, 과한 압박인가. 당신은 어디에 서나요?",
                "stakes_line": "민주주의 기억을 대하는 태도는 기업 홍보 문구보다 오래 남습니다.",
                "conflict_line": "비판은 필요하다는 주장과 공적 권한 개입은 조심해야 한다는 반론이 맞섭니다.",
                "viewer_identity_line": "시민 기준은 분노의 크기보다 책임의 선을 명확히 하는 것입니다.",
                "next_watch_line": "다음 포인트는 사과 이후 실제 재발방지 조치입니다.",
            }
        )

    return {key: _compact_card_text(value, 95, keep_question="?" in value) for key, value in values.items()}


def _narrative_profile_for_title(title: str) -> dict[str, str]:
    if any(term in title for term in ["선관위", "투표용지", "부정선거", "재선거", "선거 관리"]):
        return {
            "stakes_line": "선거 관리 논란은 승패보다 절차 신뢰와 책임선의 문제입니다.",
            "conflict_line": "한쪽은 행정 허점을 묻고, 다른 쪽은 음모론 확산을 경계합니다.",
            "viewer_identity_line": "시민 기준은 분노를 키우는 말보다 확인된 허점과 공식 책임을 나누는 것입니다.",
            "next_watch_line": "다음 포인트는 선관위 해명, 국회 조사, 특검 요구가 어디서 갈리는지입니다.",
        }
    if any(term in title for term in ["친일", "반민족", "재산 환수", "부당재산", "현충일", "단죄"]):
        return {
            "stakes_line": "역사 책임 이슈는 과거 이야기가 아니라 지금 권력이 어떤 기준을 세우는가의 문제입니다.",
            "conflict_line": "한쪽은 통합을 말하고, 다른 쪽은 부당하게 남은 이익을 먼저 묻습니다.",
            "viewer_identity_line": "감정적 구호보다 중요한 건 누가 어떤 근거로 환수와 반론을 설명하는지입니다.",
            "next_watch_line": "다음 포인트는 실제 조사 범위와 반발 프레임이 어디서 충돌하는지입니다.",
        }
    if any(term in title for term in ["검찰개혁", "공소취소", "검찰해체", "보완수사권"]):
        return {
            "stakes_line": "검찰개혁 논란의 핵심은 구호가 아니라 권한을 누가 어떻게 통제하느냐입니다.",
            "conflict_line": "개혁의 필요성을 말하는 쪽과 공소취소 프레임을 키우는 쪽의 기준이 충돌합니다.",
            "viewer_identity_line": "시민 기준은 편 가르기보다 권한, 견제, 책임선을 분리해 보는 것입니다.",
            "next_watch_line": "다음 포인트는 보완수사권과 공소취소 논쟁이 실제 법안에서 어떻게 정리되는지입니다.",
        }
    if any(term in title for term in ["국정조사", "진상규명"]):
        return {
            "stakes_line": "국정조사와 특검의 차이는 구호가 아니라 책임을 밝히는 경로의 차이입니다.",
            "conflict_line": "한쪽은 국회 조사를 말하고, 다른 쪽은 특검 없이는 부족하다고 압박합니다.",
            "viewer_identity_line": "시민이 볼 지점은 어느 편이 유리한가보다 어떤 절차가 빈칸을 줄이는가입니다.",
            "next_watch_line": "다음 포인트는 조사 요구가 실제 증거 확보로 이어지는지입니다.",
        }
    if any(term in title for term in ["민주당 책임론", "지지율 60", "정청래 책임론", "선거 책임론", "패배 책임론"]):
        return {
            "stakes_line": "여권 책임론은 자기편을 때리는 뉴스가 아니라 다음 선거를 이길 기준을 묻는 장면입니다.",
            "conflict_line": "한쪽은 시스템 평가를 말하고, 다른 쪽은 책임지는 얼굴이 필요하다고 압박합니다.",
            "viewer_identity_line": "지지층이 볼 지점은 누구를 버리느냐보다 어떤 실패 신호를 고칠 수 있느냐입니다.",
            "next_watch_line": "다음 포인트는 지지율, 후보 전략, 조직 책임이 실제로 어디서 갈리는지입니다.",
        }
    if any(term in title for term in ["순직해병", "임성근", "사단장"]):
        return {
            "stakes_line": "순직해병 특검 논란은 법리 싸움 뒤에 남는 지휘 책임을 묻는 사안입니다.",
            "conflict_line": "위헌 주장은 제도 논쟁을 만들고, 유가족과 시민은 여전히 책임선을 묻습니다.",
            "viewer_identity_line": "시민 기준은 법리 주장과 책임 회피 가능성을 분리해서 보는 것입니다.",
            "next_watch_line": "다음 포인트는 헌법소원과 특검 수사가 서로 어떤 영향을 주는지입니다.",
        }
    if any(term in title for term in ["김건희", "윤석열", "국민의힘", "특검", "공천개입"]):
        return {
            "stakes_line": "끝났다는 말 뒤에 설명 책임이 남는지가 핵심입니다.",
            "conflict_line": "한쪽은 종결을 말하고, 다른 쪽은 왜 여기서 멈추는지 묻습니다.",
            "viewer_identity_line": "분노보다 먼저 봐야 할 건 권한을 가진 쪽의 책임선입니다.",
            "next_watch_line": "다음 보도에서 바뀌는 건 사실관계보다 책임의 방향일 수 있습니다.",
        }
    if any(term in title for term in ["이재명", "민주당", "더불어민주당", "민생", "국정과제"]):
        return {
            "stakes_line": "정쟁 프레임을 걷어내면 남는 건 민생, 권한, 결과의 기준입니다.",
            "conflict_line": "공격 문장만 보면 싸움이고, 기준을 놓고 보면 누가 무엇을 막는지가 보입니다.",
            "viewer_identity_line": "감정적 응원이 아니라 어떤 기준으로 방어할지 정리해야 합니다.",
            "next_watch_line": "후속 편에서는 말보다 결과로 남는 지점을 추적하겠습니다.",
        }
    if any(term in title for term in ["검찰", "경찰", "사법", "판결", "송치", "불송치", "무혐의"]):
        return {
            "stakes_line": "법적 결론처럼 보이는 말과 시민이 물을 수 있는 설명은 다릅니다.",
            "conflict_line": "수사 결과, 해명, 남은 의문을 같은 줄에 놓으면 핵심이 흐려집니다.",
            "viewer_identity_line": "이 사안은 편들기보다 기록을 끝까지 보는 쪽이 유리합니다.",
            "next_watch_line": "다음 신호는 새 주장보다 문서와 책임 라인에서 나옵니다.",
        }
    if any(term in title for term in ["노동", "교육", "학교", "의료", "복지", "물가", "청년"]):
        return {
            "stakes_line": "큰 정치 뉴스는 결국 교실, 일터, 생활비로 내려옵니다.",
            "conflict_line": "정책 발표보다 누가 영향을 받고 누가 설명해야 하는지가 먼저입니다.",
            "viewer_identity_line": "생활에 닿는 기준으로 다시 보면 논쟁의 방향이 달라집니다.",
            "next_watch_line": "다음에는 실제 생활에 닿는 지점을 더 좁혀 보겠습니다.",
        }
    return {
        "stakes_line": "정쟁처럼 보이지만, 남는 건 기준과 책임입니다.",
        "conflict_line": "말의 충돌을 걷어내면 확인된 사실과 비어 있는 설명이 갈라집니다.",
        "viewer_identity_line": "시민 기준으로 보면 무엇을 믿고 무엇을 보류할지 분명해집니다.",
        "next_watch_line": "후속 보도에서 달라지는 지점을 계속 추적하겠습니다.",
    }


def _template_values_for_topic(
    topic: TopicCandidate,
    *,
    title: str,
    hook_headline: str,
    hashtags: list[str],
    topic_discovery: dict[str, Any] | None = None,
) -> dict[str, Any]:
    values = {
        "topic_title": topic.title,
        "title": title,
        "hook_headline": hook_headline,
        "hashtags_text": " ".join(f"#{tag}" for tag in hashtags),
    }
    values.update(_deep_research_script_values(topic_discovery))
    values.update(_narrative_profile_for_title(topic.title))
    values.update(_issue_brief_script_values(topic))
    if (
        str((topic_discovery or {}).get("mode", "")) == "rolling_schedule_plan"
        and not isinstance((topic_discovery or {}).get("deep_research_report"), dict)
    ):
        fallback_values = {
            "reference_label": "권력 책임과 시민 기준을 나누는 뉴스 해설",
            "research_question": "이 사안에서 확인된 사실과 아직 비어 있는 설명은 무엇인가?",
            "counterpoint_focus": "보도된 사실, 주장, 반론 가능성의 경계",
            "comment_trigger": "1 전말, 2 근거, 3 책임 중 무엇부터 봐야 하나요? 댓글로 남겨주세요.",
            "follower_promise": "후속 보도와 책임 답변을 추적할 이유",
        }
        for key, fallback_value in fallback_values.items():
            if not str(values.get(key, "")).strip():
                values[key] = fallback_value
    return values


def _with_deep_research_narration_lineage(script: ScriptPackage, values: dict[str, Any]) -> ScriptPackage:
    required_lines = [
        str(values.get("deep_research_question") or values.get("selected_research_question") or values.get("research_question") or "").strip(),
        str(values.get("deep_research_counterpoint_focus") or values.get("counterpoint_focus") or "").strip(),
        str(values.get("deep_research_comment_trigger") or values.get("comment_trigger") or "").strip(),
    ]
    additions = [line for line in required_lines if line and line not in script.narration]
    if not additions:
        return script
    return replace(script, narration="\n".join([script.narration, *additions]))


def _configured_hot_hashtags(topic: TopicCandidate) -> list[str]:
    tags = [str(tag) for tag in HOT_TOPIC_SCRIPT_STRATEGY.get("base_hashtags", []) if str(tag).strip()]
    for rule in HOT_TOPIC_SCRIPT_STRATEGY.get("conditional_hashtags", []):
        if not isinstance(rule, dict):
            continue
        terms = [str(term) for term in rule.get("if_topic_contains_any", []) if str(term).strip()]
        tag = str(rule.get("tag", "")).strip()
        if not tag or tag in tags or not any(term in topic.title for term in terms):
            continue
        try:
            insert_at = int(rule.get("insert_at", len(tags)))
        except (TypeError, ValueError):
            insert_at = len(tags)
        tags.insert(max(0, min(insert_at, len(tags))), tag)
    limit = _strategy_int(HOT_TOPIC_SCRIPT_STRATEGY, "hashtag_limit", len(tags))
    return tags[:limit]


def _configured_hot_scene(row: dict[str, Any], topic: TopicCandidate, values: dict[str, Any]) -> Scene:
    claim_index = row.get("claim_index")
    if isinstance(claim_index, int):
        claim_text = _hot_claim_text(topic, claim_index, str(row.get("fallback_body", "")))
        claim_template = row.get("claim_body_template")
        body = _format_prompt_template(
            str(claim_template) if claim_template is not None else claim_text,
            {**values, "claim_text": claim_text},
        )
    else:
        body = _format_prompt_template(str(row.get("body_template") or row.get("body") or ""), values)
    visual_source = str(row.get("visual_source", "body"))
    if visual_source == "topic_title":
        visual_text = topic.title
    elif visual_source == "claim" and isinstance(claim_index, int):
        visual_text = _hot_claim_text(topic, claim_index, "")
    else:
        visual_text = body
    on_screen = _format_prompt_template(str(row.get("on_screen_template") or row.get("on_screen_text") or ""), values)
    return Scene(
        int(row.get("scene_id", 0)),
        int(row.get("duration_sec", 8)),
        str(row.get("title", "")),
        body,
        _hot_visual_for_text(
            visual_text,
            str(row.get("visual_role", "evidence")),
            f"{topic.title} {topic.angle}",
        ),
        on_screen,
    )


def _configured_static_scene(row: dict[str, Any]) -> Scene:
    return Scene(
        int(row.get("scene_id", 0)),
        int(row.get("duration_sec", 8)),
        str(row.get("title", "")),
        str(row.get("body", "")),
        str(row.get("visual", "")),
        str(row.get("on_screen_text", "")),
    )



def _generate_hot_topic_script(
    topic: TopicCandidate,
    style: dict[str, Any],
    topic_discovery: dict[str, Any] | None = None,
) -> ScriptPackage:
    title = _compact_card_text(
        topic.title,
        _strategy_int(HOT_TOPIC_SCRIPT_STRATEGY, "title_max_chars", 26),
        keep_question="?" in topic.title,
    )
    hook_headline = _hot_hook_headline(topic.title)
    hashtags = _configured_hot_hashtags(topic)
    values = _template_values_for_topic(
        topic,
        title=title,
        hook_headline=hook_headline,
        hashtags=hashtags,
        topic_discovery=topic_discovery,
    )
    scene_rows = HOT_TOPIC_SCRIPT_STRATEGY.get("scenes", [])
    if not isinstance(scene_rows, list):
        raise RuntimeError("Strategy config key must be a list: hot_topic_script.scenes")
    scenes = [_configured_hot_scene(row, topic, values) for row in scene_rows if isinstance(row, dict)]
    narration = "\n".join(scene.body for scene in scenes)
    caption = _format_prompt_template(str(HOT_TOPIC_SCRIPT_STRATEGY.get("caption_template", "")), values)
    caption_max = _strategy_int(HOT_TOPIC_SCRIPT_STRATEGY, "caption_max_chars", 150)
    script = ScriptPackage(
        title=hook_headline,
        caption=_compact_card_text(caption, caption_max),
        hashtags=hashtags,
        post_title=hook_headline,
        post_body=_format_prompt_template(str(HOT_TOPIC_SCRIPT_STRATEGY.get("post_body_template", "")), values),
        pinned_comment=str(HOT_TOPIC_SCRIPT_STRATEGY.get("pinned_comment", "")),
        narration=narration,
        scenes=scenes,
        target_duration_sec=sum(scene.duration_sec for scene in scenes),
        sources=topic.source_ids,
        disclosure=style["disclosure_policy"],
        variant_id=str(HOT_TOPIC_SCRIPT_STRATEGY.get("variant_id", "hot_issue_check")),
    )
    return _with_deep_research_narration_lineage(script, values)



def _build_default_script(topic: TopicCandidate, style: dict[str, Any]) -> ScriptPackage:
    scene_rows = DEFAULT_SCRIPT_STRATEGY.get("scenes", [])
    if not isinstance(scene_rows, list):
        raise RuntimeError("Strategy config key must be a list: default_script.scenes")
    scenes = [_configured_static_scene(row) for row in scene_rows if isinstance(row, dict)]
    narration = "\n".join(scene.body for scene in scenes)
    hashtags = [str(tag) for tag in DEFAULT_SCRIPT_STRATEGY.get("hashtags", []) if str(tag).strip()]
    return ScriptPackage(
        title=topic.title,
        caption=str(DEFAULT_SCRIPT_STRATEGY.get("caption", "")),
        hashtags=hashtags,
        post_title=str(DEFAULT_SCRIPT_STRATEGY.get("post_title", "")),
        post_body=str(DEFAULT_SCRIPT_STRATEGY.get("post_body", "")),
        pinned_comment=str(DEFAULT_SCRIPT_STRATEGY.get("pinned_comment", "")),
        narration=narration,
        scenes=scenes,
        target_duration_sec=sum(scene.duration_sec for scene in scenes),
        sources=topic.source_ids,
        disclosure=style["disclosure_policy"],
        variant_id=str(DEFAULT_SCRIPT_STRATEGY.get("variant_id", "evidence_expose")),
    )


def _uses_hot_topic_script(topic: TopicCandidate, topic_discovery: dict[str, Any] | None = None) -> bool:
    discovery_mode = str((topic_discovery or {}).get("mode", ""))
    return any(source_id.startswith("hot_news_") for source_id in topic.source_ids) or discovery_mode in {
        "rolling_schedule_plan",
        "curated_three_day_replacement_plan",
    }


def generate_script(
    topic: TopicCandidate,
    style: dict[str, Any],
    topic_discovery: dict[str, Any] | None = None,
) -> ScriptPackage:
    """Generate a configured Korean script without external LLM calls."""
    if _uses_hot_topic_script(topic, topic_discovery):
        return _generate_hot_topic_script(topic, style, topic_discovery=topic_discovery)
    return _build_default_script(topic, style)


def _script_with_scenes(script: ScriptPackage, *, variant_id: str, scenes: list[Scene], **updates: Any) -> ScriptPackage:
    narration = "\n".join(scene.body for scene in scenes)
    return replace(
        script,
        variant_id=variant_id,
        scenes=scenes,
        narration=narration,
        target_duration_sec=sum(scene.duration_sec for scene in scenes),
        **updates,
    )



def _configured_variant(script: ScriptPackage, variant_id: str) -> ScriptPackage:
    config = SCRIPT_VARIANT_STRATEGY.get(variant_id)
    if not isinstance(config, dict):
        raise RuntimeError(f"Missing script variant config: {variant_id}")
    scenes = list(script.scenes)
    scene_updates = config.get("scene_updates", {})
    if not isinstance(scene_updates, dict):
        raise RuntimeError(f"Strategy config key must be an object: variants.{variant_id}.scene_updates")
    for index_text, updates in scene_updates.items():
        if not isinstance(updates, dict):
            continue
        try:
            index = int(index_text)
        except (TypeError, ValueError):
            continue
        if index < 0 or index >= len(scenes):
            continue
        allowed = {key: str(value) for key, value in updates.items() if key in {"title", "body", "visual", "on_screen_text"}}
        scenes[index] = replace(scenes[index], **allowed)
    script_updates_raw = config.get("script_updates", {})
    if not isinstance(script_updates_raw, dict):
        raise RuntimeError(f"Strategy config key must be an object: variants.{variant_id}.script_updates")
    script_updates = {key: str(value) for key, value in script_updates_raw.items()}
    return _script_with_scenes(script, variant_id=variant_id, scenes=scenes, **script_updates)


def _strong_hook_variant(script: ScriptPackage) -> ScriptPackage:
    return _configured_variant(script, "strong_hook")


def _empathy_variant(script: ScriptPackage) -> ScriptPackage:
    return _configured_variant(script, "empathy_parent")


def _fact_pressure_variant(script: ScriptPackage) -> ScriptPackage:
    return _configured_variant(script, "fact_pressure")


def generate_script_variants(
    topic: TopicCandidate,
    style: dict[str, Any],
    topic_discovery: dict[str, Any] | None = None,
) -> list[ScriptPackage]:
    base = generate_script(topic, style, topic_discovery=topic_discovery)
    if _uses_hot_topic_script(topic, topic_discovery):
        return [base]
    return [
        _strong_hook_variant(base),
        _fact_pressure_variant(base),
        _empathy_variant(base),
        base,
    ]


def route_content_format(
    topic: TopicCandidate,
    requested_format: str = "auto",
    performance_feedback: dict[str, Any] | None = None,
) -> ContentFormatPlan:
    if requested_format != "auto":
        if requested_format not in FORMAT_SPECS:
            raise ValueError(f"unknown content format: {requested_format}")
        return FORMAT_SPECS[requested_format]

    text = f"{topic.title} {topic.angle} {topic.slot}".lower()
    has_evidence_briefing_sources = len(topic.claims) >= 2 and len(topic.source_ids) >= 2
    has_followup_signal = any(term in text for term in ["comment", "reply", "followup", "rebuttal", "debate"])
    has_breaking_signal = any(term in text for term in ["breaking", "quick", "속보", "단신"])
    is_ranking_battle = "역대 대통령" in text and "순위" in text
    if is_ranking_battle:
        base = replace(FORMAT_SPECS["ranking_battle_65"], selection_reason="auto: presidential ranking battle format")
    elif has_followup_signal:
        base = replace(FORMAT_SPECS["debate_followup"], selection_reason="auto: comment or rebuttal signal detected")
    elif has_evidence_briefing_sources and not has_breaking_signal:
        base = replace(
            FORMAT_SPECS["evidence_briefing_75"],
            selection_reason="auto: evidence briefing selected from two-or-more sourced claims",
        )
    else:
        base = replace(FORMAT_SPECS["growth_short"], selection_reason="auto: discovery-first short format")

    if not performance_feedback or not performance_feedback.get("enabled"):
        return base
    format_scores = performance_feedback.get("format_scores", {})
    if not isinstance(format_scores, dict):
        return base
    candidates = [
        "evidence_briefing_75",
        "growth_short",
        "ranking_battle_65",
        "narrative_confession",
        "reward_deep",
        "reformed_briefing",
        "debate_followup",
    ]
    if not has_evidence_briefing_sources:
        candidates = [item for item in candidates if item not in {"evidence_briefing_75", "reward_deep"}]
    scored: list[tuple[int, str]] = []
    for format_id in candidates:
        try:
            scored.append((int(format_scores.get(format_id, 0)), format_id))
        except (TypeError, ValueError):
            scored.append((0, format_id))
    scored.sort(reverse=True)
    best_score, best_format = scored[0]
    try:
        base_score = int(format_scores.get(base.format_id, 0))
    except (TypeError, ValueError):
        base_score = 0
    if best_format != base.format_id and best_score >= 4 and best_score - base_score >= 6:
        return replace(
            FORMAT_SPECS[best_format],
            selection_reason=(
                f"auto: performance feedback selected {best_format} "
                f"(delta {best_score - base_score:+d}) over {base.format_id}"
            ),
        )
    if base_score:
        return replace(base, selection_reason=f"{base.selection_reason}; performance_feedback={base_score:+d}")
    return base


def _select_format_scenes(scenes: list[Scene], plan: ContentFormatPlan) -> list[Scene]:
    target_count = min(plan.scene_count_max, len(scenes))
    target_count = max(plan.scene_count_min, target_count)
    if len(scenes) <= target_count:
        selected = scenes
    else:
        selected = [*scenes[: max(1, target_count - 1)], scenes[-1]]

    return [
        replace(scene, scene_id=index + 1)
        for index, scene in enumerate(selected)
    ]


def _cutaway_scene_from_source(source: Scene, inserted_index: int, plan: ContentFormatPlan) -> Scene:
    cutaway_labels = [
        "다른 각도",
        "반론 확인",
        "책임선",
        "근거 재확인",
        "댓글 포인트",
        "빈칸 확인",
    ]
    label = cutaway_labels[inserted_index % len(cutaway_labels)]
    body_suffixes = [
        "다른 장면으로 보면 빈칸과 근거가 더 선명해집니다.",
        "반론 가능성과 확인된 기록을 분리해서 봅니다.",
        "누가 설명해야 하는지 책임선을 다시 좁힙니다.",
        "댓글 전에 확인할 기준을 한 번 더 남깁니다.",
    ]
    headline_seed = source.on_screen_text or source.title or "쟁점 확인"
    body_seed = source.body or headline_seed
    body = _compact_card_text(
        f"{body_seed} {body_suffixes[inserted_index % len(body_suffixes)]}",
        min(_body_text_max_for_plan(plan), 52),
        keep_question="?" in body_seed,
    )
    headline = _compact_card_text(f"{headline_seed} {label}", 34, keep_question="?" in headline_seed)
    visual = (
        f"{source.visual}; adaptive cutaway {inserted_index + 1}: different location depth, "
        "different camera distance, different foreground action, no repeated composition, "
        "keep the same issue context but show a new real-world moment"
    )
    return replace(
        source,
        title=f"{source.title} / {label}".strip(" /"),
        body=body,
        visual=visual,
        on_screen_text=headline,
    )


def _expand_scenes_to_visual_cadence(scenes: list[Scene], plan: ContentFormatPlan) -> list[Scene]:
    if not scenes:
        return scenes
    cadence = plan_visual_cadence(scenes, plan)
    target_count = min(plan.scene_count_max, cadence.target_master_images)
    if len(scenes) >= target_count:
        return [replace(scene, scene_id=index + 1) for index, scene in enumerate(scenes)]

    expanded = list(scenes)
    source_pool = list(scenes[:-1]) or list(scenes)
    extras_needed = target_count - len(expanded)
    extras_by_source: dict[int, list[Scene]] = {index: [] for index in range(len(source_pool))}
    for inserted in range(extras_needed):
        source_index = inserted % len(source_pool)
        extras_by_source[source_index].append(_cutaway_scene_from_source(source_pool[source_index], inserted, plan))

    expanded = []
    if len(scenes) == 1:
        expanded.append(scenes[0])
        expanded.extend(extras_by_source.get(0, []))
        return [replace(scene, scene_id=index + 1) for index, scene in enumerate(expanded)]
    for index, scene in enumerate(scenes[:-1]):
        expanded.append(scene)
        expanded.extend(extras_by_source.get(index, []))
    expanded.append(scenes[-1])
    return [replace(scene, scene_id=index + 1) for index, scene in enumerate(expanded)]


def _reward_deep_values(script: ScriptPackage, topic: TopicCandidate | None, sources: dict[str, Source] | None) -> dict[str, Any]:
    source_count = len(sources or {})
    terms = _metadata_topic_terms(topic, sources) if topic else []
    return {
        "hook_headline": script.post_title or script.title,
        "primary_term": terms[0] if terms else script.title,
        "topic_title": topic.title if topic else script.title,
        "source_count": source_count,
    }


def _apply_reward_deep_format(
    script: ScriptPackage,
    topic: TopicCandidate | None,
    sources: dict[str, Source] | None,
    plan: ContentFormatPlan,
) -> ScriptPackage:
    if plan.format_id not in {"reward_deep", "reformed_briefing"}:
        return script
    values = _reward_deep_values(script, topic, sources)
    updates = _config_dict(REWARD_DEEP_STRATEGY, "scene_updates")
    scenes = list(script.scenes)
    configured_indices: list[int] = []
    for index_text in updates:
        with contextlib.suppress(TypeError, ValueError):
            configured_indices.append(int(index_text))
    configured_last_index = max(configured_indices, default=-1)
    for index_text, scene_updates in updates.items():
        if not isinstance(scene_updates, dict):
            continue
        try:
            index = int(index_text)
        except (TypeError, ValueError):
            continue
        if index == configured_last_index and len(scenes) > configured_last_index + 1:
            index = len(scenes) - 1
        if index < 0 or index >= len(scenes):
            continue
        allowed: dict[str, str] = {}
        for field_name in ["title", "body", "visual", "on_screen_text"]:
            template = scene_updates.get(f"{field_name}_template")
            if template is not None:
                allowed[field_name] = _format_prompt_template(str(template), values)
            elif field_name in scene_updates:
                allowed[field_name] = str(scene_updates[field_name])
        scenes[index] = replace(scenes[index], **allowed)
    post_body = _format_prompt_template(str(REWARD_DEEP_STRATEGY.get("post_body_template", script.post_body)), values)
    pinned_comment = _format_prompt_template(
        str(REWARD_DEEP_STRATEGY.get("pinned_comment_template", script.pinned_comment)),
        values,
    )
    return _script_with_scenes(
        script,
        variant_id=f"{script.variant_id}:reward_optimized",
        scenes=scenes,
        post_body=post_body,
        pinned_comment=pinned_comment,
    )


def _fit_scene_durations(scenes: list[Scene], plan: ContentFormatPlan) -> list[Scene]:
    if not scenes:
        return scenes
    raw_target = sum(scene.duration_sec for scene in scenes)
    target = max(plan.target_duration_min_sec, min(plan.target_duration_max_sec, raw_target))
    if plan.reward_eligible:
        target = max(60, target)
    base = target // len(scenes)
    remainder = target - base * len(scenes)
    fitted: list[Scene] = []
    for index, scene in enumerate(scenes):
        duration = base + (1 if index < remainder else 0)
        fitted.append(replace(scene, duration_sec=max(5, min(12, int(duration)))))
    drift = target - sum(scene.duration_sec for scene in fitted)
    while drift != 0 and fitted:
        if drift > 0:
            index = max(range(len(fitted)), key=lambda i: 12 - fitted[i].duration_sec)
            if fitted[index].duration_sec >= 12:
                break
            fitted[index] = replace(fitted[index], duration_sec=fitted[index].duration_sec + 1)
            drift -= 1
        else:
            index = max(range(len(fitted)), key=lambda i: fitted[i].duration_sec)
            if fitted[index].duration_sec <= 5:
                break
            fitted[index] = replace(fitted[index], duration_sec=fitted[index].duration_sec - 1)
            drift += 1
    return fitted


def _clean_card_text(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?。])\s+", _clean_card_text(text))
    return [part.strip() for part in parts if part.strip()]


def _metadata_int(key: str, fallback: int) -> int:
    return _strategy_int(POST_METADATA_STRATEGY, key, fallback)


def _metadata_terms(section_key: str) -> list[str]:
    return _strategy_terms(POST_METADATA_STRATEGY, section_key)


def _trim_without_overflow_marker(text: str, max_chars: int) -> str:
    text = _clean_card_text(text)
    for marker in _metadata_terms("ellipsis_markers"):
        text = text.replace(marker, " ")
    text = _clean_card_text(text)
    if len(text) <= max_chars:
        return text.strip()

    sentences = _split_sentences(text)
    selected = ""
    for sentence in sentences:
        candidate = sentence if not selected else f"{selected} {sentence}"
        if len(candidate) <= max_chars:
            selected = candidate
            continue
        break
    if selected:
        return selected.strip()

    cut = text[:max_chars].rstrip(" ,.;:")
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0].rstrip(" ,.;:")
    return cut.strip()


def _clean_hashtag(tag: str) -> str:
    tag = tag.strip().lstrip(str(POST_METADATA_STRATEGY.get("hashtag_prefix", "#")))
    return re.sub(r"[^0-9A-Za-z가-힣_]", "", tag)


def _is_internal_metadata_token(token: str) -> bool:
    normalized = token.strip().casefold()
    if not normalized:
        return True
    if normalized.startswith("hot_news"):
        return True
    return normalized in {
        "hot",
        "discovery",
        "hotdiscovery",
        "static",
        "reference",
        "rolling",
        "schedule",
        "plan",
        "test",
    }


def _script_hashtag_text(tags: list[str]) -> str:
    prefix = str(POST_METADATA_STRATEGY.get("hashtag_prefix", "#"))
    return " ".join(f"{prefix}{tag}" for tag in tags if tag)


def _metadata_source_text(topic: TopicCandidate, sources: dict[str, Source] | None) -> str:
    source_titles = []
    if sources:
        source_titles = [sources[source_id].title for source_id in topic.source_ids if source_id in sources]
    return _clean_card_text(
        " ".join(
            [
                topic.title,
                topic.angle,
                topic.slot,
                " ".join(claim.text for claim in topic.claims),
                " ".join(source_titles),
            ]
        )
    )


def _metadata_primary_text(topic: TopicCandidate) -> str:
    return _clean_card_text(" ".join([topic.title, topic.angle]))


def _metadata_topic_terms(topic: TopicCandidate, sources: dict[str, Source] | None) -> list[str]:
    raw = _metadata_primary_text(topic)
    priority = [
        term
        for term in [*SEARCH_VALUE_PRIORITY_TERMS, *_strategy_terms(SCRIPT_QUALITY_STRATEGY, "target_terms")]
        if term and term in raw
    ]
    tokens = [
        token.strip("·")
        for token in re.findall(r"[가-힣A-Za-z0-9·]{2,}", raw)
        if token.strip("·")
        and token.strip("·") not in SEARCH_STOPWORDS
        and not _is_internal_metadata_token(token.strip("·"))
    ]
    return list(dict.fromkeys([*priority, *tokens]))


def _metadata_hashtags(topic: TopicCandidate, sources: dict[str, Source] | None, current_tags: list[str]) -> list[str]:
    raw = _metadata_primary_text(topic)
    grouped = _config_dict(POST_METADATA_STRATEGY, "hashtag_groups")
    candidates: list[str] = []
    for group_key in ["base"]:
        candidates.extend(str(tag) for tag in grouped.get(group_key, []) if str(tag).strip())
    for rule in POST_METADATA_STRATEGY.get("conditional_hashtags", []):
        if not isinstance(rule, dict):
            continue
        terms = [str(term) for term in rule.get("if_topic_contains_any", []) if str(term).strip()]
        if any(term in raw for term in terms):
            candidates.extend(str(tag) for tag in rule.get("tags", []) if str(tag).strip())
    for group_key in ["format", "brand"]:
        candidates.extend(str(tag) for tag in grouped.get(group_key, []) if str(tag).strip())
    candidates.extend(_metadata_topic_terms(topic, sources))
    candidates.extend(str(tag) for tag in grouped.get("audience", []) if str(tag).strip())
    reusable_current_tags = {
        _clean_hashtag(str(tag))
        for group_key in ["base", "format", "audience", "brand"]
        for tag in grouped.get(group_key, [])
        if str(tag).strip()
    }
    for current_tag in current_tags:
        clean_current = _clean_hashtag(str(current_tag))
        if clean_current in reusable_current_tags or clean_current in raw:
            candidates.append(str(current_tag))

    tags: list[str] = []
    max_tags = _metadata_int("hashtags_max", 12)
    for candidate in candidates:
        tag = _clean_hashtag(candidate)
        if not tag or tag in tags or _is_internal_metadata_token(tag):
            continue
        tags.append(tag)
        if len(tags) >= max_tags:
            break
    for brand_tag in grouped.get("brand", []):
        tag = _clean_hashtag(str(brand_tag))
        if not tag or tag in tags:
            continue
        if len(tags) >= max_tags and tags:
            tags[-1] = tag
        else:
            tags.append(tag)
    return tags


def _metadata_title(script: ScriptPackage, topic: TopicCandidate, terms: list[str]) -> str:
    values = {
        "hook_headline": script.post_title or script.title,
        "primary_term": terms[0] if terms else topic.title,
        "topic_title": topic.title,
    }
    min_chars = _metadata_int("title_min_chars", 18)
    max_chars = _metadata_int("title_max_chars", 34)
    hook = _trim_without_overflow_marker(str(values["hook_headline"]), max_chars)
    if hook and 8 <= len(hook) <= max_chars:
        return hook
    templates = _strategy_terms(POST_METADATA_STRATEGY, "title_templates")
    suffixes = _strategy_terms(POST_METADATA_STRATEGY, "title_short_suffixes")
    candidates = [_format_prompt_template(template, values) for template in templates]
    for suffix in suffixes:
        candidates.append(f"{values['hook_headline']} {suffix}")
    for candidate in candidates:
        primary_term = str(values["primary_term"])
        hook_headline = str(values["hook_headline"])
        if primary_term and primary_term in hook_headline and candidate.count(primary_term) > 1:
            continue
        if hook_headline and candidate.count(hook_headline) > 1:
            continue
        title = _trim_without_overflow_marker(candidate, max_chars)
        if min_chars <= len(title) <= max_chars:
            return title
    return _trim_without_overflow_marker(candidates[0] if candidates else script.title, max_chars)


def _metadata_caption_body(values: dict[str, Any]) -> str:
    body = _format_prompt_template(str(POST_METADATA_STRATEGY.get("caption_body_template", "")), values)
    min_chars = _metadata_int("caption_body_min_chars", 120)
    for sentence in _strategy_terms(POST_METADATA_STRATEGY, "caption_expansion_sentences"):
        if len(_clean_card_text(body)) >= min_chars:
            break
        body = f"{body} {sentence}"
    return _trim_without_overflow_marker(body, _metadata_int("caption_body_max_chars", 220))


def _caption_follow_terms() -> list[str]:
    return list(
        dict.fromkeys(
            [
                *_strategy_terms(SCRIPT_QUALITY_STRATEGY, "caption_follow_terms"),
                *_strategy_terms(SCRIPT_QUALITY_STRATEGY, "follow_terms"),
                "팔로우",
                "구독",
            ]
        )
    )


def _series_identity_terms() -> list[str]:
    return list(
        dict.fromkeys(
            [
                *_strategy_terms(SCRIPT_QUALITY_STRATEGY, "series_identity_terms"),
                "다음 편",
                "이어갑니다",
                "후속",
            ]
        )
    )


def _profile_transition_terms() -> list[str]:
    return list(
        dict.fromkeys(
            [
                *_strategy_terms(SCRIPT_QUALITY_STRATEGY, "profile_transition_terms"),
                "팔로우하면",
                "다음 편",
                "이어갑니다",
            ]
        )
    )


def _caption_has_follow_cta(text: str) -> bool:
    return _contains_any(text, _caption_follow_terms())


def _text_has_series_identity(text: str) -> bool:
    return _contains_any(text, _series_identity_terms())


def _text_has_profile_transition(text: str) -> bool:
    return _contains_any(text, _profile_transition_terms())


def _append_sentence_with_budget(text: str, sentence: str, max_chars: int) -> str:
    text = _clean_card_text(text)
    sentence = _clean_card_text(sentence)
    if not sentence:
        return _trim_without_overflow_marker(text, max_chars)
    if sentence in text:
        return _trim_without_overflow_marker(text, max_chars)
    if len(sentence) >= max_chars:
        return _trim_without_overflow_marker(sentence, max_chars)
    separator = " " if text else ""
    if len(text) + len(separator) + len(sentence) <= max_chars:
        return f"{text}{separator}{sentence}".strip()
    prefix_budget = max(0, max_chars - len(sentence) - 1)
    prefix = _trim_without_overflow_marker(text, prefix_budget).strip()
    return f"{prefix} {sentence}".strip()


def _metadata_series_promise(values: dict[str, Any]) -> str:
    values = dict(values)
    primary_term = str(values.get("primary_term") or "").strip()
    if (
        not primary_term
        or primary_term.casefold() in {"hot", "news", "hot_news", "hot_news_plan"}
        or not re.search(r"[가-힣]", primary_term)
    ):
        replacement = str(values.get("post_title") or values.get("topic_title") or "이 프레임")
        values["primary_term"] = _compact_card_text(replacement, 16, keep_question=False)
    if not values.get("series_promise"):
        values["series_promise"] = _format_prompt_template(
            str(POST_METADATA_STRATEGY.get("series_promise_template", "")),
            values,
        )
    promise = _clean_card_text(str(values.get("series_promise") or ""))
    if not promise:
        promise = str(POST_METADATA_STRATEGY.get("caption_follow_fallback", ""))
    return _trim_without_overflow_marker(promise, 72)


def _metadata_caption_follow_sentence(values: dict[str, Any]) -> str:
    values = dict(values)
    values["series_promise"] = _metadata_series_promise(values)
    sentence = _format_prompt_template(
        str(POST_METADATA_STRATEGY.get("caption_follow_template", "")),
        values,
    )
    if not _caption_has_follow_cta(sentence) or not _text_has_series_identity(sentence):
        sentence = str(POST_METADATA_STRATEGY.get("caption_follow_fallback", ""))
    return _trim_without_overflow_marker(sentence, 90)


def _caption_without_hashtags(caption: str) -> str:
    return re.sub(r"(?:^|\s)#[0-9A-Za-z가-힣_]+", "", caption).strip()


def _caption_with_required_follow_cta(caption: str, hashtags: list[str], values: dict[str, Any]) -> str:
    hashtags_text = _script_hashtag_text(hashtags)
    total_max = _metadata_int("caption_total_max_chars", 360)
    body_budget = total_max - len(hashtags_text) - (2 if hashtags_text else 0)
    follow_sentence = _metadata_caption_follow_sentence(values)
    body = _caption_without_hashtags(caption)
    needs_follow = not _caption_has_follow_cta(body)
    needs_series = not _text_has_series_identity(body) or not _text_has_profile_transition(body)
    if needs_follow or needs_series:
        body = _append_sentence_with_budget(body, follow_sentence, max(1, body_budget))
    else:
        body = _trim_without_overflow_marker(body, max(1, body_budget))
    if hashtags_text:
        return f"{body}\n\n{hashtags_text}".strip()
    return body


def _script_has_end_follow_promise(script: ScriptPackage) -> bool:
    if not script.scenes:
        return False
    final = script.scenes[-1]
    text = f"{final.on_screen_text} {final.body}"
    return _caption_has_follow_cta(text) and _text_has_series_identity(text)


def _script_final_text(script: ScriptPackage) -> str:
    if not script.scenes:
        return ""
    final = script.scenes[-1]
    return f"{final.on_screen_text} {final.body}"


def _ensure_comment_cta_contract(script: ScriptPackage) -> ScriptPackage:
    comment_terms = _strategy_terms(POLICY_GATE_STRATEGY, "comment_cta_terms")
    engagement_text = " ".join([script.narration, script.caption, script.pinned_comment])
    if _contains_any(engagement_text, comment_terms):
        return script
    comment_sentence = "근거를 댓글로 남겨주세요."
    pinned_comment = _append_sentence_with_budget(script.pinned_comment, comment_sentence, 120)
    if pinned_comment != script.pinned_comment:
        return replace(script, pinned_comment=pinned_comment)
    caption = _append_sentence_with_budget(
        script.caption,
        comment_sentence,
        _metadata_int("caption_total_max_chars", 360),
    )
    return replace(script, caption=caption)


def _ensure_follower_conversion_contract(script: ScriptPackage, values: dict[str, Any] | None = None) -> ScriptPackage:
    values = dict(values or {})
    values.setdefault("primary_term", script.post_title or script.title)
    values.setdefault("post_title", script.post_title or script.title)
    caption = _caption_with_required_follow_cta(script.caption, script.hashtags, values)
    follow_sentence = _metadata_caption_follow_sentence(values)
    pinned_comment = script.pinned_comment
    if not _caption_has_follow_cta(pinned_comment) or not _text_has_series_identity(pinned_comment):
        pinned_comment = _append_sentence_with_budget(pinned_comment, follow_sentence, 120)

    scenes = list(script.scenes)
    if scenes and not _script_has_end_follow_promise(script):
        final = scenes[-1]
        final_body = _append_sentence_with_budget(final.body, follow_sentence, BODY_TEXT_MAX_CHARS_MOBILE)
        scenes[-1] = replace(final, body=final_body)

    if scenes != script.scenes:
        converted = _script_with_scenes(
            script,
            variant_id=script.variant_id,
            scenes=scenes,
            caption=caption,
            pinned_comment=pinned_comment,
        )
        return _ensure_comment_cta_contract(converted)
    converted = replace(script, caption=caption, pinned_comment=pinned_comment)
    return _ensure_comment_cta_contract(converted)


def _metadata_values(
    script: ScriptPackage,
    topic: TopicCandidate,
    sources: dict[str, Source] | None,
    hashtags: list[str],
    post_title: str,
) -> dict[str, Any]:
    terms = _metadata_topic_terms(topic, sources)
    primary_term = terms[0] if terms else topic.title
    values = {
        "post_title": post_title,
        "topic_title": topic.title,
        "primary_term": primary_term,
        "secondary_terms_text": " ".join(terms[1:5]),
        "claim_focus": _format_prompt_template(
            str(POST_METADATA_STRATEGY.get("claim_focus_template", "")),
            {"primary_term": primary_term},
        ),
        "question_focus": str(POST_METADATA_STRATEGY.get("question_focus_default", "")),
        "cta_sentence": str(POST_METADATA_STRATEGY.get("cta_sentence", "")),
        "comment_trigger": "1 전말, 2 근거, 3 책임 중 무엇부터 봐야 하나요? 댓글로 남겨주세요.",
        "hashtags_text": _script_hashtag_text(hashtags),
        "hook_headline": script.post_title or script.title,
        "source_count": len(sources or {}),
    }
    values.update(_narrative_profile_for_title(topic.title))
    values.update(_issue_brief_script_values(topic))
    values["series_promise"] = _metadata_series_promise(values)
    return values


def _enrich_post_metadata(
    script: ScriptPackage,
    topic: TopicCandidate | None,
    sources: dict[str, Source] | None,
    *,
    preserve_existing: bool = False,
) -> ScriptPackage:
    if topic is None:
        return script
    terms = _metadata_topic_terms(topic, sources)
    hashtags = list(script.hashtags) if preserve_existing else _metadata_hashtags(topic, sources, script.hashtags)
    post_title = script.post_title if preserve_existing and script.post_title else _metadata_title(script, topic, terms)
    values = _metadata_values(script, topic, sources, hashtags, post_title)
    if preserve_existing:
        preserved = replace(
            script,
            hashtags=hashtags,
            post_title=post_title,
            post_body=script.post_body or script.caption,
            pinned_comment=script.pinned_comment,
        )
        return _ensure_follower_conversion_contract(preserved, values)
    caption_body = _metadata_caption_body(values)
    hashtags_text = _script_hashtag_text(hashtags)
    total_max = _metadata_int("caption_total_max_chars", 360)
    if len(caption_body) + len(hashtags_text) + 2 > total_max:
        caption_body = _trim_without_overflow_marker(caption_body, max(1, total_max - len(hashtags_text) - 2))
    caption = f"{caption_body}\n\n{hashtags_text}".strip()
    metadata_source = REWARD_DEEP_STRATEGY if "reward_optimized" in script.variant_id else POST_METADATA_STRATEGY
    post_body = _trim_without_overflow_marker(
        _format_prompt_template(str(metadata_source.get("post_body_template", "")), values),
        _metadata_int("caption_body_max_chars", 220),
    )
    pinned_comment = _trim_without_overflow_marker(
        _format_prompt_template(str(metadata_source.get("pinned_comment_template", "")), values),
        120,
    )
    if "댓글" not in pinned_comment:
        pinned_comment = _trim_without_overflow_marker(f"{pinned_comment} 댓글로 남겨주세요.", 120)
    enriched = replace(
        script,
        caption=caption,
        hashtags=hashtags,
        post_title=post_title,
        post_body=post_body,
        pinned_comment=pinned_comment,
    )
    return _ensure_follower_conversion_contract(enriched, values)


def _metadata_checks(script: ScriptPackage) -> dict[str, bool]:
    body = re.sub(r"(?:^|\s)#[0-9A-Za-z가-힣_]+", "", script.caption).strip()
    title_min = _metadata_int("title_min_chars", 18)
    title_max = _metadata_int("title_max_chars", 34)
    body_min = _metadata_int("caption_body_min_chars", 120)
    total_max = _metadata_int("caption_total_max_chars", 360)
    hashtag_min = _metadata_int("hashtags_min", 8)
    hashtag_max = _metadata_int("hashtags_max", 12)
    overflow_markers = _metadata_terms("ellipsis_markers")
    return {
        "post_title_target_length": title_min <= len(script.post_title) <= title_max,
        "caption_body_target_length": len(_clean_card_text(body)) >= body_min,
        "caption_total_under_limit": len(script.caption) <= total_max,
        "caption_no_overflow_marker": not _contains_any(script.caption, overflow_markers),
        "post_title_no_overflow_marker": not _contains_any(script.post_title, overflow_markers),
        "hashtags_target_count": hashtag_min <= len(script.hashtags) <= hashtag_max,
        "hashtags_unique": len(script.hashtags) == len(set(script.hashtags)),
        "caption_follow_cta_present": _caption_has_follow_cta(script.caption),
        "caption_series_identity_present": _text_has_series_identity(script.caption),
        "video_end_follow_promise_present": _script_has_end_follow_promise(script),
    }


def _compact_card_text(text: str, max_chars: int, *, keep_question: bool = False) -> str:
    text = _clean_card_text(text)
    if len(text) <= max_chars:
        return text

    sentences = _split_sentences(text)
    selected = ""
    for sentence in sentences:
        candidate = sentence if not selected else f"{selected} {sentence}"
        if len(candidate) <= max_chars:
            selected = candidate
            continue
        break
    if selected:
        return selected

    cut = text[: max(1, max_chars - (1 if keep_question else 3))].rstrip(" ,.;:")
    if keep_question and "?" in text:
        return cut.rstrip("?") + "?"
    return cut + "..."


def _expand_short_body(body: str, *, is_last: bool) -> str:
    body = _clean_card_text(body)
    additions_by_role = _config_dict(COPY_NORMALIZATION_STRATEGY, "short_body_additions")
    additions = [str(item) for item in additions_by_role.get("last" if is_last else "default", []) if str(item).strip()]
    for addition in additions:
        if len(body) >= BODY_TEXT_MIN_CHARS_MOBILE:
            break
        body = f"{body} {addition}".strip()
    return body


def _expand_short_headline(text: str, *, is_first: bool, is_last: bool) -> str:
    text = _clean_card_text(text).strip('"')
    if len(text) >= HEADLINE_MIN_CHARS:
        return text
    suffixes = _config_dict(COPY_NORMALIZATION_STRATEGY, "short_headline_suffixes")
    if is_last:
        return f"{text}{suffixes.get('last', '')}".strip(" ,")
    if is_first:
        return f"{text}{suffixes.get('first', '')}".strip(" ,")
    return f"{text}{suffixes.get('default', '')}".strip(" ,")


def _body_text_max_for_plan(plan: ContentFormatPlan | None) -> int:
    if plan is None:
        return BODY_TEXT_MAX_CHARS_MOBILE
    return FORMAT_BODY_TEXT_MAX_CHARS.get(plan.format_id, BODY_TEXT_MAX_CHARS_MOBILE)


def _normalize_scene_copy(
    scene: Scene,
    *,
    plan: ContentFormatPlan | None = None,
    is_first: bool = False,
    is_last: bool = False,
) -> Scene:
    headline = _expand_short_headline(scene.on_screen_text, is_first=is_first, is_last=is_last)
    headline = _compact_card_text(headline, 34, keep_question="?" in headline)
    if len(headline) > HEADLINE_TARGET_MAX_CHARS and not is_first and not is_last:
        headline = _compact_card_text(headline, HEADLINE_TARGET_MAX_CHARS, keep_question="?" in headline)

    body = _expand_short_body(scene.body, is_last=is_last)
    body_max = _body_text_max_for_plan(plan)
    body = _compact_card_text(body, body_max, keep_question=is_last or "?" in body)
    required_term = str(COPY_NORMALIZATION_STRATEGY.get("last_body_required_term", ""))
    if is_last and required_term and required_term not in body:
        body = _compact_card_text(f"{body} {COPY_NORMALIZATION_STRATEGY.get('last_body_append', '')}", body_max, keep_question=True)
    if len(body) < BODY_TEXT_MIN_CHARS_MOBILE:
        if is_last and required_term and required_term in body:
            body = _compact_card_text(f"{body} {COPY_NORMALIZATION_STRATEGY.get('last_body_short_append', '')}", body_max, keep_question=True)
        else:
            body = _compact_card_text(_expand_short_body(body, is_last=is_last), body_max, keep_question=is_last or "?" in body)
    return replace(scene, body=body, on_screen_text=headline)


def normalize_script_copy(script: ScriptPackage, plan: ContentFormatPlan | None = None) -> ScriptPackage:
    scenes = [
        _normalize_scene_copy(scene, plan=plan, is_first=index == 0, is_last=index == len(script.scenes) - 1)
        for index, scene in enumerate(script.scenes)
    ]
    return _script_with_scenes(script, variant_id=script.variant_id, scenes=scenes)


def _topic_anchor_hook_text(topic: TopicCandidate, sources: dict[str, Source] | None) -> str:
    custom = _custom_issue_hook_headline(topic)
    if custom:
        return custom
    anchors = _topic_scene_anchor_terms(topic, sources)
    primary = anchors[0] if anchors else _compact_card_text(topic.title, 12)
    templates = [
        "{primary}, 진짜 책임은?",
        "{primary}, 커진 이유 3개",
        "{primary}, 누가 책임지나?",
    ]
    for template in templates:
        candidate = template.format(primary=primary)
        if len(candidate) <= 34:
            return candidate
    return _compact_card_text(topic.title, 34, keep_question="?" in topic.title)


def _configured_custom_issue_kind(text: str) -> str:
    cleaned = _clean_card_text(text)
    for rule in HOT_CUSTOM_ISSUE_KIND_RULES:
        kind = str(rule.get("kind", "")).strip()
        if not kind:
            continue
        must_include = [str(term) for term in rule.get("must_include", []) if str(term).strip()]
        any_include = [str(term) for term in rule.get("any_include", []) if str(term).strip()]
        if must_include and not all(term in cleaned for term in must_include):
            continue
        if any_include and not any(term in cleaned for term in any_include):
            continue
        if must_include or any_include:
            return kind
    return ""


def _custom_issue_kind(topic_title: str) -> str:
    text = _clean_card_text(topic_title)
    configured = _configured_custom_issue_kind(text)
    if configured:
        return configured
    if any(term in text for term in ["지지율", "여론조사", "민주 45", "국힘 20", "보수 결집"]):
        return "numbers"
    if any(term in text for term in ["선고", "위증", "특검", "구형", "법원", "판결"]):
        return "legal"
    if any(term in text for term in ["5·18", "5.18", "광주", "스타벅스", "일베", "혐오", "조롱", "노무현"]):
        return "memory_hate"
    if any(term in text for term in ["선거", "심판론", "안정론", "정부견제론", "정권안정론", "우파 프레임"]):
        return "election_frame"
    if any(term in text for term in ["국민의힘", "민주당", "이재명", "오세훈", "보수", "우파"]):
        return "party_frame"
    return "civic_conflict"


def _custom_issue_kind_for_topic(topic: TopicCandidate, sources: dict[str, Source] | None) -> str:
    primary_text = _clean_card_text(
        " ".join([topic.title, topic.angle, " ".join(_metadata_topic_terms(topic, sources))])
    )
    configured = _configured_custom_issue_kind(primary_text)
    if configured:
        return configured
    return _custom_issue_kind(_topic_issue_basis(topic))


def _custom_issue_hook_headline(topic: TopicCandidate) -> str:
    title = _clean_card_text(topic.title)
    configured = _configured_hot_hook_headline(title)
    if configured:
        return configured
    rules: list[tuple[list[str], str]] = [
        (["지지율", "60"], "60%인데 왜 불안하지?"),
        (["민주 45", "국힘 20"], "숫자만 보면 속을까?"),
        (["보수 결집"], "결집인가, 착시인가?"),
        (["오세훈"], "그 말, 그냥 넘길까?"),
        (["김건희", "특검"], "특검 이슈, 남은 책임선"),
        (["오늘", "선고"], "오늘 선고, 뭘 봐야 하나?"),
        (["D-1", "선고"], "선고 D-1, 뭘 볼까?"),
        (["윤석열", "선고"], "선고 전 뭘 봐야 하나?"),
        (["위증", "선고"], "선고 전 뭘 봐야 하나?"),
        (["정부견제론", "정권안정론"], "견제론, 누가 써먹나"),
        (["일베"], "혐오, 장난으로 끝날까?"),
        (["혐오", "조롱"], "혐오, 장난으로 끝날까?"),
        (["스타벅스"], "불매, 과한가 정당한가?"),
        (["5·18", "조롱"], "5·18 조롱, 선 넘었나?"),
        (["국민의힘", "정부견제론"], "국힘 프레임, 작동 지점 3개"),
        (["우파 프레임"], "우파 프레임 TOP5, 왜?"),
        (["선거판"], "이번 주 TOP5, 뭐가 흔드나?"),
        (["심판론", "안정론"], "심판론 vs 안정론, 갈림점 3개"),
    ]
    for terms, headline in rules:
        if all(term in title for term in terms):
            return _compact_card_text(headline, 34, keep_question=True)

    primary = _hot_primary_hook_term(title)
    kind = _custom_issue_kind(title)
    fallbacks = {
        "numbers": "{primary}, 흔들린 지점 3개",
        "legal": "{primary}, 누가 흔드나?",
        "memory_hate": "{primary}, 선 넘었나?",
        "election_frame": "{primary}, 누가 움직이나?",
        "party_frame": "{primary}, 작동한 프레임 3개",
        "civic_conflict": "{primary}, 갈린 기준 3개",
    }
    return _compact_card_text(fallbacks[kind].format(primary=primary), 34, keep_question=True)


def _custom_issue_scene_rows(kind: str) -> list[dict[str, str]]:
    common_cta = {
        "role": "댓글 판정",
        "screen": "댓글로 최종 판정",
        "body": "숫자보다 움직임이 중요합니다. 당신은 신호로 보나요, 착시로 보나요? 댓글로 남겨주세요.",
        "visual_role": "cta",
    }
    profiles: dict[str, list[dict[str, str]]] = {
        "numbers": [
            {"role": "훅", "screen": "{hook}", "body": "{topic_title}. 숫자만 보면 이긴 것 같지만, 진짜 볼 건 어디가 흔들리는지입니다.", "visual_role": "hook"},
            {"role": "첫 숫자", "screen": "첫 숫자", "body": "{claim0}", "visual_role": "why_now"},
            {"role": "착시 지점", "screen": "착시 지점", "body": "대통령 지지율, 정당 지지율, 지역 여론은 같은 방향으로 움직이지 않습니다. 여기서 방심이 생깁니다.", "visual_role": "criteria"},
            {"role": "상대 결집", "screen": "상대 결집", "body": "보수 결집은 숫자가 낮아도 선거판에서는 다른 의미를 가질 수 있습니다. 낮은 숫자만 보고 끝내면 놓칩니다.", "visual_role": "evidence"},
            {"role": "위험선", "screen": "방심 금지선", "body": "높은 지지율이 안전판은 아닙니다. 투표율, 지역, 후보 경쟁력이 따로 움직이면 결과는 달라질 수 있습니다.", "visual_role": "responsibility"},
            {"role": "반론", "screen": "반론도 있음", "body": "반론도 있습니다. 여론조사는 흐름을 보여줄 뿐 결과를 확정하지 않습니다. 그래서 추세와 균열을 같이 봐야 합니다.", "visual_role": "verification"},
            {"role": "판정 기준", "screen": "볼 건 3개", "body": "정리하면 1 지지율 격차, 2 보수 결집, 3 지역 이탈입니다. 이 셋이 동시에 움직이는지 봐야 합니다.", "visual_role": "criteria"},
            {"role": "다음 포인트", "screen": "다음 보도 포인트", "body": "다음 보도에서 볼 건 숫자 자체보다 누가 더 간절하게 움직이는가입니다. 선거는 지지율만으로 끝나지 않습니다.", "visual_role": "verification"},
            common_cta,
        ],
        "legal": [
            {"role": "훅", "screen": "{hook}", "body": "{topic_title}. 이건 응원전이 아니라 혐의, 구형, 판결 기준을 분리해서 봐야 하는 장면입니다.", "visual_role": "hook"},
            {"role": "사건 흐름", "screen": "먼저 흐름", "body": "{claim0}", "visual_role": "why_now"},
            {"role": "법정 기준", "screen": "혐의와 판결", "body": "혐의 제기, 구형, 선고는 같은 말이 아닙니다. 여기서 단정하면 오히려 프레임 싸움에 끌려갑니다.", "visual_role": "criteria"},
            {"role": "정치 프레임", "screen": "정치 프레임", "body": "한쪽은 정치 수사라 말하고, 다른 쪽은 책임 추적이라 말합니다. 그래서 공개된 근거가 먼저입니다.", "visual_role": "evidence"},
            {"role": "남은 빈칸", "screen": "남은 빈칸", "body": "아직 봐야 할 건 판결문, 쟁점 판단, 후속 수사 가능성입니다. 말보다 문서가 기준입니다.", "visual_role": "responsibility"},
            {"role": "반론", "screen": "반론 체크", "body": "반론도 봐야 합니다. 정치적 해석과 법적 판단을 섞으면 누구에게도 기준이 남지 않습니다.", "visual_role": "verification"},
            {"role": "결과별 파장", "screen": "결과별 파장", "body": "유죄냐 무죄냐만 볼 게 아닙니다. 어떤 쟁점을 인정했고 어떤 설명을 남겼는지가 다음 이슈를 만듭니다.", "visual_role": "criteria"},
            {"role": "다음 포인트", "screen": "다음은 판결문", "body": "다음 콘텐츠에서는 결과가 나오면 판결문 기준으로 주장과 사실을 다시 나누겠습니다.", "visual_role": "verification"},
            common_cta,
        ],
        "memory_hate": [
            {"role": "훅", "screen": "{hook}", "body": "{topic_title}. 이건 농담 하나가 아니라 기억을 어떻게 대하는지의 문제입니다.", "visual_role": "hook"},
            {"role": "도화선", "screen": "도화선", "body": "{claim0}", "visual_role": "why_now"},
            {"role": "선 넘은 지점", "screen": "선 넘은 지점", "body": "표현의 자유라는 말이 모든 조롱을 덮지는 못합니다. 특히 역사적 상처를 건드릴 때는 더 그렇습니다.", "visual_role": "criteria"},
            {"role": "책임 요구", "screen": "책임 요구", "body": "불매냐 과잉 반응이냐로만 보면 좁습니다. 핵심은 사과, 재발 방지, 공적 책임을 어디까지 요구할 수 있느냐입니다.", "visual_role": "evidence"},
            {"role": "반대 논리", "screen": "반대 논리", "body": "반론도 있습니다. 모든 실수를 정치 문제로 키우면 피로감이 커진다는 주장입니다.", "visual_role": "verification"},
            {"role": "판정선", "screen": "판정선", "body": "그래서 기준은 하나입니다. 실수였나, 반복된 문화였나, 책임 있는 자리에서 방치했나.", "visual_role": "responsibility"},
            {"role": "공유 포인트", "screen": "공유 포인트", "body": "이 이슈는 화내자는 말보다 기준을 남겨야 오래 갑니다. 기억을 가볍게 다루는 순간이 반복되기 때문입니다.", "visual_role": "criteria"},
            {"role": "다음 포인트", "screen": "다음 보도", "body": "다음은 사과 이후 실제 조치가 있었는지, 그리고 정치권 반응이 어디까지 갔는지 보겠습니다.", "visual_role": "verification"},
            common_cta,
        ],
        "election_frame": [
            {"role": "훅", "screen": "{hook}", "body": "{topic_title}. 이건 단순 구호가 아니라 누구를 투표장으로 움직이게 하느냐의 싸움입니다.", "visual_role": "hook"},
            {"role": "프레임", "screen": "프레임 전쟁", "body": "{claim0}", "visual_role": "why_now"},
            {"role": "견제론", "screen": "견제론", "body": "정부견제론은 분노층을 깨우는 말입니다. 하지만 과하면 불안 프레임으로 되돌아올 수 있습니다.", "visual_role": "criteria"},
            {"role": "안정론", "screen": "안정론", "body": "정권안정론은 지지층 결집에 강합니다. 대신 책임 회피처럼 보이는 순간 설득력이 떨어집니다.", "visual_role": "evidence"},
            {"role": "댓글 갈림", "screen": "댓글 갈림", "body": "댓글이 싸우는 지점도 여기입니다. 심판이 먼저냐, 안정이 먼저냐. 같은 숫자를 보고도 결론이 갈립니다.", "visual_role": "responsibility"},
            {"role": "반론", "screen": "반론 체크", "body": "반론도 있습니다. 프레임보다 후보 경쟁력과 지역 이슈가 더 크다는 주장입니다.", "visual_role": "verification"},
            {"role": "승부처", "screen": "승부처", "body": "그래서 봐야 할 건 1 중도층, 2 투표율, 3 지역 이슈입니다. 구호보다 움직이는 층이 중요합니다.", "visual_role": "criteria"},
            {"role": "다음 포인트", "screen": "다음 포인트", "body": "다음 여론조사에서는 숫자보다 어떤 프레임이 댓글과 공유를 더 많이 만드는지 보겠습니다.", "visual_role": "verification"},
            common_cta,
        ],
        "party_frame": [
            {"role": "훅", "screen": "{hook}", "body": "{topic_title}. 이 이슈는 누가 더 도덕적인가보다 누가 프레임을 가져가느냐의 문제입니다.", "visual_role": "hook"},
            {"role": "시작점", "screen": "시작점", "body": "{claim0}", "visual_role": "why_now"},
            {"role": "상대 논리", "screen": "상대 논리", "body": "상대는 이 장면을 정부 견제나 심판론으로 묶으려 합니다. 이 프레임이 먹히는지 봐야 합니다.", "visual_role": "criteria"},
            {"role": "우리 쪽 기준", "screen": "우리 기준", "body": "반대로 진보 지지층은 책임, 민생, 민주주의 기준을 분명히 세워야 합니다. 감정만으로는 부족합니다.", "visual_role": "evidence"},
            {"role": "위험선", "screen": "위험선", "body": "가장 위험한 건 이겼다고 느끼는 순간입니다. 방심하면 낮은 결집도 높은 투표율 앞에서 흔들립니다.", "visual_role": "responsibility"},
            {"role": "반론", "screen": "반론 체크", "body": "반론도 있습니다. 모든 이슈를 진영 싸움으로 만들면 중도층은 멀어질 수 있습니다.", "visual_role": "verification"},
            {"role": "판정 기준", "screen": "판정 기준", "body": "그래서 기준은 간단합니다. 이 이슈가 지지층 결집, 중도 설득, 상대 실책 중 어디에 더 가까운지입니다.", "visual_role": "criteria"},
            {"role": "다음 포인트", "screen": "다음 포인트", "body": "다음 편에서는 댓글 반응과 후속 보도가 실제 여론 흐름을 바꾸는지 보겠습니다.", "visual_role": "verification"},
            common_cta,
        ],
    }
    return profiles.get(kind, profiles["party_frame"])


def _apply_topic_specific_scene_overrides(topic_title: str, rows: list[dict[str, str]]) -> list[dict[str, str]]:
    title = _clean_card_text(topic_title)
    updated = [dict(row) for row in rows]

    def set_rows(overrides: list[tuple[int, str, str | None]]) -> None:
        for index, screen, body in overrides:
            if 0 <= index < len(updated):
                updated[index]["screen"] = screen
                if body is not None:
                    updated[index]["body"] = body

    if "지지율 60" in title:
        set_rows([
            (1, "60% 경고등", "{claim0}"),
            (2, "정당 지표는 따로", "대통령 지지율과 정당 지지율은 같은 숫자가 아닙니다. 지지층 결집과 지역 민심은 따로 움직입니다."),
            (3, "보수 결집 체크", "상대가 낮아 보여도 결집하면 선거판은 달라집니다. 숫자의 크기보다 움직임을 봐야 합니다."),
            (4, "방심 금지", "높은 지지율일수록 오만 프레임을 조심해야 합니다. 승리감이 투표율을 낮출 수 있습니다."),
        ])
    elif "민주 45" in title or "국힘 20" in title:
        set_rows([
            (1, "45 대 20?", "{claim0}"),
            (2, "조사 방식부터", "같은 여론도 조사 방식, 표본, 질문 문장에 따라 다르게 보입니다. 숫자 하나로 끝내면 안 됩니다."),
            (3, "격차보다 추세", "정말 중요한 건 지금 몇 퍼센트냐보다 격차가 줄고 있는지, 굳어지는지입니다."),
            (4, "댓글장 착시", "댓글 여론은 실제 표심보다 과열됩니다. 그래도 결집 신호로는 무시하면 안 됩니다."),
        ])
    elif "보수 결집" in title:
        set_rows([
            (1, "낮아도 위험", "{claim0}"),
            (2, "결집의 신호", "낮은 지지율도 한 방향으로 모이면 선거에서는 힘이 됩니다. 숫자보다 집중도가 중요합니다."),
            (3, "댓글장 먼저 움직임", "보수 결집은 여론조사보다 댓글장, 커뮤니티, 지역 이슈에서 먼저 보일 때가 많습니다."),
            (4, "진보의 실수", "진보 진영이 가장 조심할 건 조롱과 방심입니다. 상대를 작게 보는 순간 프레임이 바뀝니다."),
        ])
    elif "지지율이 높을수록" in title:
        set_rows([
            (1, "말 한마디 리스크", "{claim0}"),
            (2, "오만 프레임", "높은 지지율은 공격 소재가 됩니다. 말 한마디가 오만 프레임으로 묶일 수 있습니다."),
            (3, "지지층 언어", "강한 지지층이 좋아하는 말과 중도층이 받아들이는 말은 다릅니다."),
            (4, "이길수록 낮게", "이길수록 메시지는 낮고 구체적이어야 합니다. 책임과 근거가 남아야 합니다."),
        ])

    if "김건희" in title and "특검" in title:
        set_rows([
            (1, "계속 남는 이유", "{claim0}"),
            (2, "스캔들 소비 아님", "이 이슈가 오래 가는 이유는 사생활 호기심이 아니라 권력 사유화 의심 때문입니다."),
            (3, "특검의 기준", "특검은 분노를 대신하는 장치가 아닙니다. 공개 근거와 절차가 기준이어야 합니다."),
            (4, "방어 프레임", "상대는 정치 보복이라고 말할 겁니다. 그래서 더더욱 근거와 절차로 압박해야 합니다."),
        ])
    elif "D-1" in title:
        set_rows([
            (1, "D-1 예측 금지", "{claim0}"),
            (2, "구형과 선고", "구형은 검찰의 요구이고 선고는 법원의 판단입니다. 둘을 섞으면 프레임에 끌려갑니다."),
            (3, "쟁점 3개", "봐야 할 건 혐의 인정 여부, 판단 근거, 선고 이후 정치적 반응입니다."),
            (4, "결과 전 기준", "결과가 나오기 전일수록 응원보다 기준을 세워야 합니다. 그래야 어떤 결과에도 흔들리지 않습니다."),
        ])
    elif "오늘" in title and "선고" in title:
        set_rows([
            (1, "오늘 결과 보는 법", "{claim0}"),
            (2, "판결문 먼저", "오늘은 제목보다 판결문 기준이 먼저입니다. 인정된 사실과 배척된 주장을 나눠 봐야 합니다."),
            (3, "정치 반응 분리", "판결 직후 정치권 반응은 과열됩니다. 반응보다 판단 근거를 먼저 봐야 합니다."),
            (4, "후속 파장", "결과보다 오래 가는 건 후속 수사, 항소, 책임론입니다. 이 세 가지가 다음 프레임입니다."),
        ])

    if "일베" in title or "혐오" in title:
        set_rows([
            (1, "장난이라는 방패", "{claim0}"),
            (2, "표현 자유 경계", "표현의 자유는 중요하지만 혐오와 조롱을 면책하는 만능 방패는 아닙니다."),
            (3, "누가 돈 버나", "혐오를 장난으로 포장하면 분노가 조회수와 장사로 바뀝니다. 그 구조를 봐야 합니다."),
            (4, "기억의 기준", "특정 집단의 상처를 반복해서 건드리는 문화라면 단순 실수와 다르게 봐야 합니다."),
        ])
    elif "스타벅스" in title or "불매" in title:
        set_rows([
            (1, "불매의 기준", "{claim0}"),
            (2, "소비자 분노", "불매는 처벌이 아니라 소비자가 책임을 묻는 방식입니다. 다만 기준이 분명해야 오래 갑니다."),
            (3, "기업의 답", "핵심은 사과문이 아니라 재발 방지와 내부 기준입니다. 말보다 조치가 남아야 합니다."),
            (4, "과잉 논란", "반론도 있습니다. 모든 실수를 불매로 몰면 피로감이 커집니다. 그래서 책임 범위를 따져야 합니다."),
        ])

    if "우파 프레임" in title:
        set_rows([
            (1, "TOP5 프레임", "{claim0}"),
            (2, "1 견제론", "첫 번째는 정부견제론입니다. 분노층을 깨우지만 책임 회피처럼 보이면 역풍도 있습니다."),
            (3, "2 민생 프레임", "두 번째는 민생 프레임입니다. 구체적 생활 이슈로 들어오면 방어가 어려워집니다."),
            (4, "3 조롱 유도", "세 번째는 조롱 유도입니다. 상대를 작게 보게 만들어 방심하게 하는 방식입니다."),
            (6, "방어법", "방어법은 간단합니다. 조롱하지 말고, 근거를 짧게, 책임 기준을 반복하는 겁니다."),
        ])
    elif "선거판 흔든 장면" in title:
        set_rows([
            (1, "이번 주 TOP5", "{claim0}"),
            (2, "장면 1", "첫 장면은 지지율입니다. 높아 보여도 안심할 수 없는 이유가 생겼습니다."),
            (3, "장면 2", "두 번째는 역사 논란입니다. 분노가 선거 프레임으로 바뀌는 순간입니다."),
            (4, "장면 3", "세 번째는 재판 이슈입니다. 결과보다 해석 전쟁이 더 빨리 움직입니다."),
            (6, "결론", "이번 주 핵심은 하나입니다. 상대 프레임을 웃어넘기지 말고 먼저 구조를 읽어야 합니다."),
        ])
    elif "심판론" in title and "안정론" in title:
        set_rows([
            (1, "둘의 갈림점 3개", "{claim0}"),
            (2, "심판론의 힘", "심판론은 분노를 투표로 바꾸는 언어입니다. 과거 책임을 현재 선택으로 끌고 옵니다."),
            (3, "안정론의 힘", "안정론은 불안을 줄이는 언어입니다. 변화 피로가 큰 층에는 강하게 먹힙니다."),
            (4, "댓글 전쟁", "댓글이 갈리는 이유는 간단합니다. 한쪽은 책임을 보고, 다른 쪽은 불안을 봅니다."),
            (6, "판정 기준", "판정 기준은 중도층입니다. 누가 더 덜 불안한 선택처럼 보이느냐가 승부처입니다."),
        ])

    return updated


_CUSTOM_SHORT_HEADLINE_EXPANSIONS = {
    "첫 숫자": "첫 숫자, 믿어도 되나?",
    "착시 지점": "착시가 생기는 지점",
    "상대 결집": "상대는 조용히 결집",
    "보수 결집 체크": "보수는 조용히 결집",
    "위험선": "위험선은 바로 여기",
    "방심 금지": "방심하면 뒤집힌다",
    "반론도 있음": "반론, 여기서 갈린다",
    "반론": "반론, 여기서 갈린다",
    "볼 건 3개": "세 가지만 보면 된다",
    "판정 기준": "판정 기준은 하나",
    "도화선": "어디서 터졌나",
    "책임 요구": "책임은 어디까지?",
    "판정선": "판정선은 딱 하나",
    "공유 포인트": "공유할 쟁점은 이거",
    "다음 보도": "다음 보도, 이걸 봐",
    "다음 보도 포인트": "다음 보도, 이걸 봐",
    "다음 포인트": "다음엔 이걸 봐",
    "반론 체크": "반론, 여기서 갈린다",
    "시작점": "이 장면이 시작점",
    "상대 논리": "상대 논리는 이거",
    "우리 기준": "우리 기준은 책임",
    "프레임": "프레임 전쟁 시작",
    "견제론": "견제론이 작동하는 지점",
    "안정론": "안정론의 약점은 이것",
    "승부처": "승부처는 바로 여기",
    "장면 1": "장면 1, 지지율 균열",
    "장면 2": "장면 2, 분노 전환",
    "장면 3": "장면 3, 해석 전쟁",
    "결론": "결론, 방심 금지",
}


def _readable_custom_screen_text(text: str, *, index: int = 0) -> str:
    cleaned = _clean_card_text(text)
    for fragment in [" 핵심 체크", " 핵심 기준", "핵심 체크", "핵심 기준"]:
        cleaned = cleaned.replace(fragment, "").strip()
    if cleaned in _CUSTOM_SHORT_HEADLINE_EXPANSIONS:
        return _compact_card_text(_CUSTOM_SHORT_HEADLINE_EXPANSIONS[cleaned], 26, keep_question=True)
    if cleaned and _hangul_count(cleaned) < 2:
        cleaned = f"{cleaned} 판단 기준"
    if len(cleaned) >= HEADLINE_MIN_CHARS:
        return cleaned
    suffixes = [
        "진짜 쟁점",
        "여기서 갈린다",
        "프레임의 빈틈",
        "숫자 밖 신호",
        "댓글이 갈릴 지점",
    ]
    suffix = suffixes[index % len(suffixes)]
    glue = "" if not cleaned else ", "
    return _compact_card_text(f"{cleaned}{glue}{suffix}", 26, keep_question="?" in cleaned)


def _readable_custom_body_text(body: str, *, body_max: int, final_scene: bool) -> str:
    cleaned = _clean_card_text(body)
    if (
        BODY_TEXT_MIN_CHARS_MOBILE <= len(cleaned) <= body_max
        and (not final_scene or _contains_any(cleaned, ["?", "습니까", "까요"]))
    ):
        return cleaned
    suffix = (
        "당신은 이 흐름을 신호로 보나요, 착시로 보나요? 댓글로 남겨주세요."
        if final_scene
        else "핵심은 근거와 책임선입니다. 댓글로 기준과 반론을 남겨주세요."
    )
    candidate = f"{cleaned} {suffix}".strip()
    if len(candidate) <= body_max:
        return candidate
    if cleaned:
        compact = _compact_card_text(cleaned, body_max, keep_question="?" in cleaned)
        if compact and len(compact) >= BODY_TEXT_MIN_CHARS_MOBILE:
            return compact
        if len(cleaned) >= BODY_TEXT_MIN_CHARS_MOBILE:
            direct = cleaned[:body_max].rstrip(" ,.;:")
            if "?" in cleaned and "?" not in direct and len(direct) < body_max:
                direct = f"{direct}?"
            if len(direct) >= BODY_TEXT_MIN_CHARS_MOBILE:
                return direct
    if len(suffix) <= body_max:
        return suffix
    return _compact_card_text(candidate, body_max, keep_question=True)


def _normalize_custom_scene_readability(scenes: list[Scene], body_max: int) -> list[Scene]:
    normalized: list[Scene] = []
    total = len(scenes)
    for index, scene in enumerate(scenes):
        final_scene = index >= max(0, total - 1)
        normalized.append(
            replace(
                scene,
                on_screen_text=_readable_custom_screen_text(scene.on_screen_text, index=index),
                body=_readable_custom_body_text(scene.body, body_max=body_max, final_scene=final_scene),
            )
        )
    if normalized and not any(
        any(marker in f"{scene.on_screen_text} {scene.body}" for marker in ["?", "습니까", "까요"])
        for scene in normalized[-2:]
    ):
        last = normalized[-1]
        normalized[-1] = replace(
            last,
            body=_readable_custom_body_text(last.body, body_max=body_max, final_scene=True),
        )
    return normalized


def _customize_issue_story_arc(
    script: ScriptPackage,
    topic: TopicCandidate | None,
    sources: dict[str, Source] | None,
    plan: ContentFormatPlan,
) -> ScriptPackage:
    if topic is None or not script.scenes:
        return script
    kind = _custom_issue_kind_for_topic(topic, sources)
    hook = _custom_issue_hook_headline(topic)
    rows = _apply_topic_specific_scene_overrides(topic.title, _custom_issue_scene_rows(kind))
    body_max = _body_text_max_for_plan(plan)
    claims = [_clean_card_text(claim.text) for claim in topic.claims if _clean_card_text(claim.text)]
    claim0 = claims[0] if claims else topic.title
    values = {
        "topic_title": _clean_card_text(topic.title),
        "hook": hook,
        "claim0": claim0,
        "primary": (_metadata_topic_terms(topic, sources) or [_hot_primary_hook_term(topic.title)])[0],
    }
    scenes: list[Scene] = []
    non_cta_rows = rows[:-1] or rows
    recycled_labels = ["재확인", "반론", "책임", "다음 포인트"]
    for index, scene in enumerate(script.scenes):
        recycled_middle = False
        if index == len(script.scenes) - 1:
            row = rows[-1]
        elif index < len(non_cta_rows):
            row = non_cta_rows[index]
        else:
            row = non_cta_rows[index % len(non_cta_rows)]
            recycled_middle = True
        screen_template = row["screen"]
        if index == len(script.scenes) - 1 and plan.format_id in {"reward_deep", "reformed_briefing"} and "1 " in scene.on_screen_text:
            screen_template = scene.on_screen_text
        screen = _compact_card_text(
            _format_prompt_template(screen_template, values),
            26,
            keep_question="?" in screen_template,
        )
        if recycled_middle:
            screen = _compact_card_text(
                f"{screen} {recycled_labels[index % len(recycled_labels)]}",
                26,
                keep_question="?" in screen,
            )
        body_raw = _format_prompt_template(row["body"], values)
        if recycled_middle:
            body_raw = f"{body_raw} 같은 이슈라도 다른 장면으로 다시 봅니다."
        if index == 0 and plan.format_id in {"reward_deep", "reformed_briefing"} and "1\ubd84" not in body_raw:
            body_raw = f"1\ubd84 \uc548\uc5d0 \ubcf4\uaca0\uc2b5\ub2c8\ub2e4. {body_raw}"
        body = _compact_card_text(body_raw, body_max, keep_question="?" in body_raw)
        visual_role = str(row.get("visual_role") or "evidence")
        visual = _hot_visual_for_text(
            f"{topic.title} {body}",
            visual_role,
            f"{topic.title} {topic.angle}",
        )
        scenes.append(
            replace(
                scene,
                title=str(row["role"]),
                body=body,
                visual=visual,
                on_screen_text=screen,
            )
        )
    scenes = _normalize_custom_scene_readability(scenes, body_max)
    return _script_with_scenes(
        script,
        variant_id=f"{script.variant_id}:{kind}:custom_arc",
        scenes=scenes,
        title=hook,
        post_title=hook,
    )


def _preserve_topic_anchor_terms(
    script: ScriptPackage,
    topic: TopicCandidate | None,
    sources: dict[str, Source] | None,
    plan: ContentFormatPlan,
) -> ScriptPackage:
    if topic is None or not script.scenes:
        return script
    scenes = list(script.scenes)
    body_max = _body_text_max_for_plan(plan)
    topic_title = _clean_card_text(topic.title)
    if topic_title:
        scenes[0] = replace(
            scenes[0],
            on_screen_text=_topic_anchor_hook_text(topic, sources),
            body=_compact_card_text(f"{topic_title}. 커진 이유와 책임선을 함께 봅니다.", body_max, keep_question=False),
        )

    provisional = _script_with_scenes(script, variant_id=script.variant_id, scenes=scenes)
    coverage = _topic_scene_anchor_coverage(provisional, topic, sources)
    missing = coverage["missing"][: coverage["required"]]
    if not missing:
        return _script_with_scenes(script, variant_id=f"{script.variant_id}:topic_anchored", scenes=scenes)

    for index, term in enumerate(missing):
        scene_index = min(index, len(scenes) - 1)
        scene = scenes[scene_index]
        scenes[scene_index] = replace(
            scene,
            body=_compact_card_text(f"{scene.body} {term} 기준까지 같이 봅니다.", body_max, keep_question="?" in scene.body),
        )
    return _script_with_scenes(script, variant_id=f"{script.variant_id}:topic_anchored", scenes=scenes)


def apply_content_format(
    script: ScriptPackage,
    plan: ContentFormatPlan,
    topic: TopicCandidate | None = None,
    sources: dict[str, Source] | None = None,
) -> ScriptPackage:
    selected_scenes = _select_format_scenes(script.scenes, plan)
    scenes = _fit_scene_durations(selected_scenes, plan)
    format_suffix = {
        "evidence_briefing_75": "evidence",
        "growth_short": "short",
        "ranking_battle_65": "ranking",
        "narrative_confession": "narrative",
        "reward_deep": "reward",
        "reformed_briefing": "reformed",
        "debate_followup": "followup",
    }.get(plan.format_id, plan.format_id)
    formatted = _script_with_scenes(
        script,
        variant_id=f"{script.variant_id}:{format_suffix}",
        scenes=scenes,
    )
    formatted = _apply_reward_deep_format(formatted, topic, sources, plan)
    expanded_scenes = _fit_scene_durations(_expand_scenes_to_visual_cadence(formatted.scenes, plan), plan)
    formatted = _script_with_scenes(formatted, variant_id=formatted.variant_id, scenes=expanded_scenes)
    normalized = normalize_script_copy(formatted, plan)
    anchored = _preserve_topic_anchor_terms(normalized, topic, sources, plan)
    customized = _customize_issue_story_arc(anchored, topic, sources, plan)
    return _enrich_post_metadata(customized, topic, sources)


def _reference_source_line(source_card: SourceCard) -> str:
    if source_card.gate_passed and source_card.display_text:
        return source_card.display_text
    if source_card.source_name:
        return f"출처: {source_card.source_name}"
    return "출처 확인 필요"


def _reference_primary_term(topic: TopicCandidate, sources: dict[str, Source] | None) -> str:
    terms = _metadata_topic_terms(topic, sources)
    if terms:
        return terms[0]
    return _compact_card_text(topic.title, 12, keep_question=False)


def _reference_unique_post_title(hook: str, topic: TopicCandidate, sources: dict[str, Source] | None) -> str:
    configured = _configured_hot_hook_headline(topic.title)
    if configured:
        return _compact_card_text(configured, 34, keep_question="?" in configured)
    primary = _reference_primary_term(topic, sources)
    number_signal = _reference_number_signal(topic)
    if number_signal:
        return _compact_card_text(f"{number_signal}, 프레임은 누가 짰나?", 26, keep_question=True)
    if primary:
        return _compact_card_text(f"{primary} 쟁점, 어디가 갈렸나", 26, keep_question=True)
    return _compact_card_text(hook, 24, keep_question="?" in hook)


def _reference_post_metadata_profile(
    post_title: str,
    topic: TopicCandidate,
    fact_pack: FactPack,
    angle_brief: AngleBrief,
) -> dict[str, str]:
    claim, counter, open_question = _reference_fact_texts(topic, fact_pack)
    default_question = _clean_card_text(angle_brief.comment_question) or "이 사안에서 먼저 봐야 할 기준은 무엇인가요?"
    number_signal = _reference_number_signal(topic)
    number_line = f"{number_signal} 숫자와 해석을 분리합니다. " if number_signal else ""
    topic_text = f"{topic.title} {post_title}"
    if all(term in topic_text for term in ["역대 대통령", "순위"]):
        profile = {
            "caption_body": (
                "역대 대통령 TOP5를 민주주의, 위기 회복, 정치적 유산 기준으로 다시 매겼습니다. "
                "성장만 볼지, 민주주의까지 볼지에 따라 순위는 완전히 갈립니다. "
                "1위는 영상 끝에서 공개합니다. 당신의 1위는 누구인가요?"
            ),
            "post_body": "역대 대통령 TOP5를 공개 기준으로 다시 봅니다. 기준이 바뀌면 1위가 바뀝니다.",
            "pinned_comment": "당신의 TOP2는 누구인가요? 기준과 함께 댓글로 남겨주세요. 팔로우하면 다음 순위 편도 이어갑니다.",
        }
        return {
            key: _trim_without_overflow_marker(value, 240 if key == "caption_body" else 120)
            for key, value in profile.items()
        }
    if "보완수사권" in topic_text:
        profile = {
            "caption_body": (
                "검찰 보완수사권, 결국 질문은 하나입니다. 검찰권을 더 견제할 것인가, 수사 공백을 막기 위해 "
                "일부 권한을 남길 것인가. 당신은 1 검찰권 축소, 2 보완수사권 필요, 3 국회 설계 책임 중 어디인가요? "
                "해당 이미지는 생성 이미지입니다."
            ),
            "post_body": "보완수사권 논쟁을 검찰권 견제, 수사 공백 반론, 국회 설계 책임으로 나눠 봅니다.",
            "pinned_comment": "1 검찰권 축소, 2 보완수사권 필요, 3 국회 설계 책임? 댓글로 번호와 근거를 남기고 공유해주세요. 팔로우하면 후속안도 이어갑니다.",
        }
        return {
            key: _trim_without_overflow_marker(value, 240 if key == "caption_body" else 120)
            for key, value in profile.items()
        }
    if all(term in topic_text for term in ["엇갈린", "운명"]):
        profile = {
            "caption_body": (
                "비전 vs 특검, 같은 주간에 나온 두 장면입니다. 한쪽은 취임 1주년 국정 비전, "
                "다른 한쪽은 특검 조사와 책임선. 당신은 1 비전의 시간, 2 책임의 시간, "
                "3 더 봐야 함 중 어디인가요? 해당 이미지는 생성 이미지입니다."
            ),
            "post_body": "이재명 대통령 1주년 비전과 윤석열 전 대통령 특검 조사, 두 장면을 공개 보도 기준으로 나눠 봅니다.",
            "pinned_comment": "1 비전의 시간, 2 책임의 시간, 3 더 봐야 함. 번호로 남겨주세요. 팔로우하면 후속 조사 흐름까지 이어갑니다.",
        }
        return {
            key: _trim_without_overflow_marker(value, 240 if key == "caption_body" else 120)
            for key, value in profile.items()
        }
    if "팩트 조작" in topic_text or "언론의 팩트 조작" in topic_text:
        profile = {
            "caption_body": (
                "언론 자유와 가짜뉴스 책임은 같이 봐야 합니다. 대통령 발언의 핵심은 비판 보도 금지가 아니라 "
                "팩트 조작에 책임을 묻자는 쪽입니다. 당신은 1 언론 책임 강화, 2 권력 비판 위축 우려, "
                "3 기준부터 명확히 중 어디인가요? 해당 이미지는 생성 이미지입니다."
            ),
            "post_body": "언론 자유, 팩트 조작 책임, 권력 감시 위축 우려를 한 번에 나눠 봅니다.",
            "pinned_comment": "1 언론 책임 강화, 2 권력 비판 위축 우려, 3 기준부터 명확히? 댓글로 번호와 근거를 남겨주세요. 후속도 이어갑니다.",
        }
        return {
            key: _trim_without_overflow_marker(value, 240 if key == "caption_body" else 120)
            for key, value in profile.items()
        }
    if "국정조사" in topic_text:
        profile = {
            "caption_body": (
                "국정조사는 진상규명일 수도, 시간끌기 프레임일 수도 있습니다. 핵심은 누가 조사권을 쥐느냐보다 "
                "책임을 실제로 밝힐 수 있느냐입니다. 당신은 1 국정조사 필요, 2 특검이 먼저, "
                "3 둘 다 압박 중 어디인가요? 해당 이미지는 생성 이미지입니다."
            ),
            "post_body": "국정조사와 특검을 진상규명 경로, 지연 가능성, 책임선 기준으로 비교합니다.",
            "pinned_comment": "1 국정조사 필요, 2 특검이 먼저, 3 둘 다 압박? 댓글로 번호와 근거를 남겨주세요. 공유하면 다음 편에서 이어갑니다.",
        }
        return {
            key: _trim_without_overflow_marker(value, 240 if key == "caption_body" else 120)
            for key, value in profile.items()
        }
    if "평화공존" in topic_text or "평화 공존" in topic_text:
        profile = {
            "caption_body": (
                "평화공존은 순진한 말이 아니라 비용 계산의 문제입니다. 군사 긴장을 낮추는 현실 전략인지, "
                "강경론 앞에서 약한 신호인지가 댓글을 가를 포인트입니다. 당신은 1 현실 전략, "
                "2 너무 순진함, 3 조건부 대화 중 어디인가요? 해당 이미지는 생성 이미지입니다."
            ),
            "post_body": "평화공존 발언을 군사 긴장 완화, 안보 실익, 보수 반론 기준으로 나눠 봅니다.",
            "pinned_comment": "1 현실 전략, 2 너무 순진함, 3 조건부 대화? 댓글로 번호와 근거를 남겨주세요. 팔로우하면 안보 이슈도 이어갑니다.",
        }
        return {
            key: _trim_without_overflow_marker(value, 240 if key == "caption_body" else 120)
            for key, value in profile.items()
        }
    profile = {
        "caption_body": (
            f"{post_title} {number_line}{claim} 반론은 {counter} "
            f"{open_question} 해당 이미지는 생성 이미지이며, 공개 보도 기준으로 전말과 빈칸을 분리합니다."
        ),
        "post_body": f"{number_line}{claim} 반론과 남은 기준까지 같이 봅니다.",
        "pinned_comment": f"{default_question} 댓글로 근거를 남기고, 공유·팔로우로 다음 검증까지 이어가세요.",
    }
    return {
        key: _trim_without_overflow_marker(value, 240 if key == "caption_body" else 120)
        for key, value in profile.items()
    }


def _reference_number_signal(topic: TopicCandidate) -> str:
    text = " ".join([topic.title, *[claim.text for claim in topic.claims]])
    compound = re.search(r"\d+(?:\.\d+)?\s*년\s*\d+(?:\.\d+)?\s*개월", text)
    if compound:
        return compound.group(0).strip()
    match = re.search(r"\d+(?:\.\d+)?\s*(?:%|퍼센트|명|건|회|억|조|일|년|개월)", text)
    return match.group(0).strip() if match else ""


def _reference_stop_signal(
    topic: TopicCandidate,
    sources: dict[str, Source] | None,
    reference_fit: ReferenceFit,
) -> str:
    hooks = set(reference_fit.selected_hook_ids)
    number_signal = _reference_number_signal(topic)
    primary = _reference_primary_term(topic, sources)
    if "number_receipt_first" in hooks and number_signal:
        return _compact_card_text(f"{number_signal}, 끝난 걸까?", 22, keep_question=True)
    if "quote_contradiction_first" in hooks:
        return "말과 기록, 왜 다르지?"
    if "named_actor_first" in hooks and primary:
        return _compact_card_text(f"{primary}, 왜 지금?", 22, keep_question=True)
    if "civic_scene_first" in hooks:
        return "현장보다 기록 먼저"
    return _topic_anchor_hook_text(topic, sources)


def _reference_opening_scene_for_topic(topic_title: str, source_line: str) -> tuple[str, str]:
    text = f"{topic_title} {source_line}"
    rules: list[tuple[list[str], str, str]] = [
        (
            ["엇갈린", "운명"],
            "cinematic split public-accountability tableau: left side a bright national-vision briefing hall screen "
            "with anonymous reporters, right side a cold special-counsel corridor with an empty interview chair, "
            "separated by a sharp vertical shadow line, no real politician likeness",
            "unique composition: bright policy briefing hall versus cold special-counsel corridor split by shadow",
        ),
        (
            ["이재명", "1년"],
            "AI-assisted civic evaluation room with a bright public briefing screen glow, five separated policy lanes "
            "for livelihood, economy, reform, diplomacy, and agenda control, anonymous analysts and camera silhouettes",
            "unique composition: five-lane policy score desk with bright briefing-room glow",
        ),
        (
            ["이재명", "취임"],
            "AI-assisted civic evaluation room with a bright public briefing screen glow, five separated policy lanes "
            "for livelihood, economy, reform, diplomacy, and agenda control, anonymous analysts and camera silhouettes",
            "unique composition: five-lane policy score desk with bright briefing-room glow",
        ),
        (
            ["김건희", "특검"],
            "special counsel evidence room with a blurred luxury-shopping receipt, anonymous investigator hands, "
            "sealed boxes, and a reflected corridor outside the interview room",
            "unique composition: luxury-receipt evidence close-up beside sealed case boxes",
        ),
        (
            ["윤석열", "특검"],
            "special counsel interview waiting room, empty chair under a hard lamp, recorder light on, cropped hands "
            "placing a thick timeline file on the table",
            "unique composition: empty interview chair with a glowing recorder and timeline file",
        ),
        (
            ["국정조사", "특검"],
            "split civic accountability scene: one side a generic hearing-room chair, the other side an investigation "
            "desk with separated files, anonymous aides crossing in the background",
            "unique composition: split hearing chair versus investigation desk in one frame",
        ),
        (
            ["보완수사권"],
            "split institutional power scene: left side a cold prosecutor-office corridor behind frosted glass with an "
            "evidence cart, right side a National Assembly committee table with blank nameplates and anonymous lawmakers, "
            "a thin red jurisdiction line crossing the floor, no logos and no readable text",
            "unique composition: prosecutor corridor versus National Assembly committee table divided by a red jurisdiction line",
        ),
        (
            ["친일", "환수"],
            "archive vault counter with old property ledgers, unbranded sealed packets, and an anonymous hand sliding "
            "a restitution file under warm museum-grade light",
            "unique composition: archive-vault ledger and restitution packet exchange",
        ),
        (
            ["검찰개혁"],
            "prosecutor office corridor seen through frosted glass, anonymous staff moving files, red pencil marks "
            "on a reform checklist in the foreground",
            "unique composition: frosted prosecutor corridor with reform checklist foreground",
        ),
        (
            ["투표용지", "부족"],
            "polling-place supply room after closing time, empty ballot trays, counting tags, anonymous worker hands "
            "checking a shortage log under fluorescent light",
            "unique composition: empty ballot trays and shortage log in a supply room",
        ),
        (
            ["선관위", "특검"],
            "election administration archive hallway, unbranded storage boxes, anonymous press shadow at the door, "
            "a special-investigation request folder half-open in the foreground",
            "unique composition: archive hallway door with investigation request folder foreground",
        ),
        (
            ["선관위"],
            "election administration back office at night, blank process map on a wall, anonymous official silhouette "
            "beside separated source folders",
            "unique composition: night back-office process map with separated source folders",
        ),
        (
            ["재선거"],
            "late-night newsroom decision desk, blank election map board, two separated source packets, and a phone "
            "screen glow cutting across anonymous editor hands",
            "unique composition: newsroom election-map desk with phone glow and separated source packets",
        ),
    ]
    for terms, scene, variation in rules:
        if all(term in text for term in terms):
            return scene, variation
    fallback_scenes = [
        (
            "court-adjacent corridor with anonymous silhouettes, source packet in foreground, and a red pencil line "
            "crossing a blank timeline page",
            "unique composition: corridor source packet with red-pencil timeline foreground",
        ),
        (
            "night editorial desk with three evidence packets physically separated, recorder light on, and a blurred "
            "public-building window in the background",
            "unique composition: night editorial desk with three separated evidence packets",
        ),
        (
            "public records counter with cropped hands comparing two folders, reflection on polished floor, and an "
            "empty chair left in the background",
            "unique composition: public records counter with reflected floor and empty chair",
        ),
    ]
    index = sum(ord(char) for char in topic_title) % len(fallback_scenes)
    return fallback_scenes[index]


def _reference_scene_override_for_topic(
    topic_title: str,
    source_line: str,
    role: str,
    scene_index: int,
    scene_focus: str,
) -> tuple[str, str] | None:
    text = f"{topic_title} {source_line} {scene_focus}"
    if "보완수사권" in text:
        overrides: dict[int, tuple[str, str]] = {
            1: (
                "rainy courthouse-adjacent public square outside an unbranded prosecutor office, anonymous citizens "
                "watching a blank civic notice board through glass, cold blue lights and a restrained red reflection, "
                "no documents as main subject",
                "unique composition: public distrust outside prosecutor office seen through rain glass, no desk",
            ),
            2: (
                "close view of a jurisdiction line drawn across two institutional desks: a blank prosecutor case tray "
                "on one side and a blank legislative review tray on the other, cropped hands stop before crossing the line",
                "unique composition: physical jurisdiction line between prosecutor tray and legislative review tray",
            ),
            3: (
                "National Assembly committee room from the back row, anonymous lawmakers seated at a curved table, "
                "blank nameplates turned away, hearing microphones idle, public gallery silhouettes behind glass",
                "unique composition: back-row National Assembly committee room with blank nameplates and public gallery",
            ),
            4: (
                "progressive civic group office watching a reform briefing on an unbranded screen, anonymous adults "
                "leaning forward, warm light over blank reform folders, no slogans and no party marks",
                "unique composition: reform supporters watching an unbranded briefing screen with blank folders",
            ),
            5: (
                "two opposing public arguments staged in one civic hall: one side points to an empty prosecutor chair, "
                "the other side points to a blank investigation flow chart, divided by glass reflection",
                "unique composition: empty prosecutor chair versus blank investigation flow chart divided by glass",
            ),
            6: (
                "three-rule civic standard tableau: three blank vertical cards standing on a committee desk, one for "
                "power restraint, one for investigation continuity, one for legislative responsibility, cropped hands only",
                "unique composition: three blank civic standard cards on committee desk with cropped hands",
            ),
            7: (
                "late-night legislative drafting room, anonymous aides moving blank amendment folders from a prosecutor "
                "corridor photo wall toward a committee table, practical lamps and tired coffee cups",
                "unique composition: amendment folders moving from prosecutor corridor wall toward committee table",
            ),
            8: (
                "viewer-choice newsroom desk with three blank option cards, a blurred split-screen of prosecutor corridor "
                "and committee room in the background, phone comment glow, no readable text",
                "unique composition: three blank option cards with prosecutor corridor and committee room split-screen",
            ),
        }
        if role == "hook" and scene_index == 0:
            return _reference_opening_scene_for_topic(topic_title, source_line)
        return overrides.get(scene_index)
    if not all(term in text for term in ["엇갈린", "운명"]):
        return None
    overrides: dict[int, tuple[str, str]] = {
        1: (
            "bright public briefing hall viewed from the back of the audience aisle, anonymous citizens and reporters "
            "facing a large unbranded one-year national vision screen, camera tripods and raised phones as foreground silhouettes, "
            "no presenter or host in the foreground, no desk close-up, optimistic civic light without any party logo or real politician likeness",
            "unique composition: audience-back live-briefing hall with a bright national-vision screen, no presenter foreground and no desk scene",
        ),
        2: (
            "cold special-counsel building corridor after questioning, empty interview chair seen through glass, "
            "recorder light on, thick sealed timeline file on a metal cart, anonymous backs moving away under fluorescent light",
            "unique composition: cold corridor with empty interview chair, recorder light, and sealed timeline file",
        ),
        3: (
            "single frame split by a hard diagonal shadow: on one side a bright policy briefing screen and open planning folders, "
            "on the other side closed investigation folders and a dim corridor, anonymous adults only",
            "unique composition: bright future-plan documents colliding with dark accountability folders",
        ),
        4: (
            "two public viewing zones reflected in glass: a warm civic crowd watching a national-vision screen, and a cold press line "
            "reflected behind them with microphones raised, no real faces, no logos",
            "unique composition: supporter-viewing crowd and press-line reflection in one glass frame",
        ),
        5: (
            "public argument scene seen through a glass wall: one side shows a warm civic viewing crowd, the other side shows a cold "
            "press scrum and shadowed counterargument silhouettes, a thin red divider line reflected on the glass, no desk, no paper stacks, "
            "anonymous adults only",
            "unique composition: warm civic crowd versus cold counterargument press scrum divided by a glass reflection, no desk",
        ),
        6: (
            "cinematic civic crossroads at night: one path lit by a briefing-hall glow, another path ending at a cold investigation door, "
            "anonymous silhouettes paused between both routes, rain reflections on the floor",
            "unique composition: two paths of fate, briefing glow versus investigation door, with rain reflections",
        ),
        7: (
            "follow-up summons anticipation scene: calendar grid with one red circled blank square, sealed summons folder sliding into "
            "a special-counsel corridor tray, cropped anonymous hands only, no readable names or numbers",
            "unique composition: red-circled blank calendar square and sealed summons folder entering a corridor tray",
        ),
        8: (
            "vertical comment-choice scene in a newsroom booth: three blank numbered-style choice cards as physical props, phone comment "
            "glow on the table, blurred civic split-screen image in the background",
            "unique composition: three physical comment-choice cards with phone glow and blurred split-screen background",
        ),
    }
    if role == "hook" and scene_index == 0:
        return _reference_opening_scene_for_topic(topic_title, source_line)
    return overrides.get(scene_index)


def _reference_visual_scene(
    scene_type_id: str,
    role: str,
    topic_title: str,
    source_line: str,
    scene_index: int = 0,
    scene_focus: str = "",
) -> str:
    variation_beats = [
        "unique composition: street-level press line with wet pavement and a folder crossing the lens",
        "unique composition: overhead document table with three separated source packets",
        "unique composition: editorial timeline wall with blank cards and colored strings",
        "unique composition: empty hearing-room chair under hard overhead light",
        "unique composition: close editor desk with three blank comment-choice cards",
        "unique composition: side-angle archive counter with sealed packet exchange",
        "unique composition: deep corridor shot with one empty chair in the foreground",
        "unique composition: frosted glass office counter with recorder and red pencil",
        "unique composition: over-the-shoulder editing monitor with a blank comment card",
    ]
    variation = variation_beats[scene_index % len(variation_beats)]
    prompts = {
        "debate_microphone_closeup": (
            "fictional debate microphone close-up in a neutral public forum, anonymous speaker cropped below the eyes, "
            "microphones and recorder pressing into the foreground, tense blurred audience behind"
        ),
        "hearing_room_wide": (
            "generic public hearing room wide shot, blank nameplates turned away, anonymous adults reacting around a table, "
            "papers and microphones under harsh ceiling light"
        ),
        "document_receipt_desk": (
            "evidence desk with source packet, recorder, red pencil, phone glow, and blank documents physically separated "
            "by cropped hands, paper texture and fingerprints visible"
        ),
        "news_graphic_title_card": (
            "original unbranded newsroom title-card set, fictional AiNo editor at a timeline wall, abstract blocks and "
            "source packets visible, not imitating any broadcaster"
        ),
        "street_speech_closeup": (
            "street press-scrum close-up with anonymous silhouettes, unbranded microphones, rain reflection, and a folder "
            "crossing the lens at the moment a question lands"
        ),
        "civic_location_exterior": (
            "generic civic building exterior at dusk, no exact logo, anonymous press silhouettes and public steps, "
            "a sealed blank folder in the foreground"
        ),
    }
    selected = prompts.get(scene_type_id, prompts.get("document_receipt_desk", "source packet desk"))
    override = _reference_scene_override_for_topic(topic_title, source_line, role, scene_index, scene_focus)
    if override:
        selected, variation = override
    elif scene_index == 0 and role == "hook":
        selected, variation = _reference_opening_scene_for_topic(topic_title, source_line)
    base_context = (
        f"topic context: {topic_title}; source context: {source_line}; scene {scene_index + 1}; {variation}; "
        f"scene focus: {_compact_card_text(scene_focus, 120, keep_question='?' in scene_focus)}; "
        "photorealistic Korean civic news explainer image, vertical 9:16, cinematic documentary lighting, "
        "high tension foreground object, anonymous adults only, no real politician likeness, no party logo, "
        "no fake broadcast UI, no official seal, no extra readable text except the approved diegetic text prop"
    )
    return f"reference_scene: {selected}; role={role}; {base_context}"


def _reference_fact_texts(topic: TopicCandidate, fact_pack: FactPack) -> tuple[str, str, str]:
    claims = [_clean_card_text(claim.text) for claim in topic.claims if _clean_card_text(claim.text)]
    facts = [
        _clean_card_text(item.text)
        for item in [*fact_pack.confirmed_facts, *fact_pack.reported_claims]
        if _clean_card_text(item.text)
    ]
    counters = [_clean_card_text(item.text) for item in fact_pack.counterpoints if _clean_card_text(item.text)]
    unanswered = [_clean_card_text(item.text) for item in fact_pack.unanswered_questions if _clean_card_text(item.text)]
    claim = (facts or claims or [_clean_card_text(topic.title)])[0]
    counter = counters[0] if counters else "반론과 남은 설명도 함께 봐야 합니다. 한쪽 해석만 남기면 프레임이 사실처럼 굳습니다."
    open_question = unanswered[0] if unanswered else "아직 확인되지 않은 빈칸은 남겨두고, 공개된 근거만 기준으로 봅니다."
    return claim, counter, open_question


def _reference_story_rule_matches(rule: dict[str, Any], topic: TopicCandidate) -> bool:
    text = _clean_card_text(f"{topic.title} {topic.angle} {' '.join(_topic_claim_lines(topic))}")
    must_include = [str(term) for term in rule.get("must_include", []) if str(term).strip()]
    any_include = [str(term) for term in rule.get("any_include", []) if str(term).strip()]
    if must_include and not all(term in text for term in must_include):
        return False
    if any_include and not any(term in text for term in any_include):
        return False
    return bool(must_include or any_include)


def _reference_story_rule_score(rule: dict[str, Any], topic: TopicCandidate, order_index: int) -> int:
    full_text = _clean_card_text(f"{topic.title} {topic.angle} {' '.join(_topic_claim_lines(topic))}")
    primary_text = _clean_card_text(f"{topic.title} {topic.angle} {' '.join(_metadata_topic_terms(topic, None))}")
    must_include = [str(term) for term in rule.get("must_include", []) if str(term).strip()]
    any_include = [str(term) for term in rule.get("any_include", []) if str(term).strip()]
    if must_include and not all(term in full_text for term in must_include):
        return -1
    any_hits = [term for term in any_include if term in full_text]
    if any_include and not any_hits:
        return -1
    if not must_include and not any_include:
        return -1

    matched_terms = [*must_include, *any_hits]
    primary_hits = sum(1 for term in matched_terms if term in primary_text)
    score = 0
    score += primary_hits * REFERENCE_STORY_RULE_SCORING.get("primary_term_hit", 100)
    score += len(must_include) * REFERENCE_STORY_RULE_SCORING.get("must_term_hit", 24)
    score += len(any_hits) * REFERENCE_STORY_RULE_SCORING.get("any_term_hit", 8)
    score += len(set(matched_terms)) * REFERENCE_STORY_RULE_SCORING.get("matched_rule_bonus", 4)
    score -= order_index * REFERENCE_STORY_RULE_SCORING.get("order_penalty", 1)
    return score


def _reference_story_rows_from_strategy(
    topic: TopicCandidate,
    base_rows: list[dict[str, str]],
    values: dict[str, str],
) -> list[dict[str, str]]:
    rules = HOT_TOPIC_STRATEGY.get("reference_storyboard_rules", [])
    if not isinstance(rules, list):
        return base_rows
    matched_rules: list[tuple[int, dict[str, Any]]] = []
    for order_index, rule in enumerate(rules):
        if not isinstance(rule, dict):
            continue
        score = _reference_story_rule_score(rule, topic, order_index)
        if score < 0:
            continue
        matched_rules.append((score, rule))
    matched_rules.sort(key=lambda item: item[0], reverse=True)
    for _score, rule in matched_rules:
        rule_rows = rule.get("rows", [])
        if not isinstance(rule_rows, list) or len(rule_rows) < min(6, len(base_rows)):
            continue
        merged_rows: list[dict[str, str]] = []
        row_count = len(rule_rows) if len(rule_rows) < len(base_rows) else len(base_rows)
        for index in range(row_count):
            base = base_rows[index] if index < len(base_rows) else base_rows[-1]
            override = rule_rows[index] if index < len(rule_rows) and isinstance(rule_rows[index], dict) else {}
            merged = dict(base)
            for key in ("title", "screen", "body", "role"):
                value = str(override.get(key, "")).strip()
                if value:
                    merged[key] = _format_prompt_template(value, values)
            merged_rows.append(merged)
        return merged_rows
    return base_rows


def apply_reference_content_design(
    script: ScriptPackage,
    topic: TopicCandidate,
    sources: dict[str, Source],
    plan: ContentFormatPlan,
    reference_fit: ReferenceFit,
    source_card: SourceCard,
    fact_pack: FactPack,
    angle_brief: AngleBrief,
) -> ScriptPackage:
    if not script.scenes or not reference_fit.selected_scene_type_ids:
        return script

    source_line = _reference_source_line(source_card)
    hook = _reference_stop_signal(topic, sources, reference_fit)
    preserved_title = _compact_card_text(script.post_title, 34, keep_question="?" in script.post_title)
    topic_text_for_title = f"{topic.title} {topic.angle}"
    if all(term in topic_text_for_title for term in ["역대 대통령", "순위"]):
        post_title = "역대 대통령 TOP5. 기준을 바꾸면 1위가 바뀝니다"
    else:
        post_title = preserved_title or _reference_unique_post_title(hook, topic, sources)
    claim, counter, open_question = _reference_fact_texts(topic, fact_pack)
    number_signal = _reference_number_signal(topic)
    if number_signal and "선고" in f"{topic.title} {claim}":
        claim = f"보도 기준 핵심은 {number_signal} 선고입니다. 혐의와 판단 기준을 분리합니다."
    body_max = _body_text_max_for_plan(plan)
    comment_question = _clean_card_text(angle_brief.comment_question) or "이건 설명 책임인가, 과잉 프레임인가?"
    base_rows = [
        {
            "title": "훅",
            "screen": post_title,
            "body": "제목보다 먼저 볼 건 출처와 빠진 설명입니다. 결론은 기록 뒤에 둡니다.",
            "role": "hook",
        },
        {
            "title": "출처",
            "screen": "출처부터 확인하자",
            "body": "출처 확인. 보도 제목과 확인된 사실, 남은 주장을 나눕니다.",
            "role": "why_now",
        },
        {
            "title": "자료",
            "screen": "자료가 말한 지점",
            "body": claim,
            "role": "evidence",
        },
        {
            "title": "빈칸",
            "screen": "아직 남은 빈칸",
            "body": open_question,
            "role": "verification",
        },
        {
            "title": "프레임",
            "screen": "프레임이 갈린다",
            "body": counter,
            "role": "criteria",
        },
        {
            "title": "기준",
            "screen": "세 가지 판단 기준",
            "body": "누가 말했나, 언제 공개됐나, 반론이 남았나. 이 셋을 나누면 선동과 검증이 갈립니다.",
            "role": "criteria",
        },
        {
            "title": "책임",
            "screen": "책임은 어디까지?",
            "body": "공개 이슈라면 감정보다 설명 책임이 먼저입니다. 말이 아니라 기록과 후속 조치가 기준입니다.",
            "role": "responsibility",
        },
        {
            "title": "공유",
            "screen": "출처 반론 기록 저장",
            "body": "이 영상은 결론 강요가 아니라 판단 기준을 남기는 콘텐츠입니다. 논쟁할 때 출처부터 꺼내면 됩니다.",
            "role": "verification",
        },
        {
            "title": "판정",
            "screen": "당신의 기준은?",
            "body": f"{comment_question} 댓글에는 감정보다 기준을 남겨주세요.",
            "role": "cta",
        },
    ]
    story_values = {
        "topic_title": _clean_card_text(topic.title),
        "post_title": post_title,
        "claim": claim,
        "counter": counter,
        "open_question": open_question,
        "comment_question": comment_question,
        "source_line": source_line,
    }
    base_rows = _reference_story_rows_from_strategy(topic, base_rows, story_values)
    for row in base_rows:
        body = str(row.get("body", ""))
        body = body.replace(
            "ì œëª©ë³´ë‹¤ ë¨¼ì € ë³¼ ê±´ ì¶œì²˜ì™€ ë¹ ì§„ ì„¤ëª…ìž…ë‹ˆë‹¤.",
            "첫 문장보다 먼저 볼 건 출처와 빠진 설명입니다.",
        )
        body = body.replace(
            "ë³´ë„ ì œëª©ê³¼ í™•ì¸ëœ ì‚¬ì‹¤",
            "확인된 사실",
        )
        row["body"] = body

    scene_types = reference_fit.selected_scene_type_ids or ["document_receipt_desk"]
    scenes: list[Scene] = []
    total = len(script.scenes)
    non_cta_rows = base_rows[:-1] or base_rows
    recycled_labels = ["재확인", "반론", "책임", "다음"]
    for index, scene in enumerate(script.scenes):
        recycled_middle = False
        if index == total - 1:
            row = base_rows[-1]
        elif index < len(non_cta_rows):
            row = non_cta_rows[index]
        else:
            row = non_cta_rows[index % len(non_cta_rows)]
            recycled_middle = True
        scene_type_id = scene_types[index % len(scene_types)]
        screen = _compact_card_text(str(row["screen"]), 22, keep_question="?" in str(row["screen"]))
        if recycled_middle:
            screen = _compact_card_text(
                f"{screen} {recycled_labels[index % len(recycled_labels)]}",
                22,
                keep_question="?" in screen,
            )
        body_source = str(row["body"])
        if recycled_middle:
            body_source = f"{body_source} 같은 쟁점을 다른 장면으로 한 번 더 분리합니다."
        body = _readable_custom_body_text(
            body_source,
            body_max=body_max,
            final_scene=index == total - 1,
        )
        scenes.append(
            replace(
                scene,
                title=str(row["title"]),
                on_screen_text=screen,
                body=body,
                visual=_reference_visual_scene(
                    scene_type_id,
                    str(row["role"]),
                    topic.title,
                    source_line,
                    index,
                    scene_focus=f"{screen}; {body}",
                ),
            )
        )

    metadata_profile = _reference_post_metadata_profile(post_title, topic, fact_pack, angle_brief)
    rewritten = _script_with_scenes(
        script,
        variant_id=f"{script.variant_id}:reference_v3",
        scenes=scenes,
        title=post_title,
        post_title=post_title,
        post_body=metadata_profile["post_body"],
        pinned_comment=metadata_profile["pinned_comment"],
    )
    enriched = _enrich_post_metadata(rewritten, topic, sources)
    hashtags_text = _script_hashtag_text(enriched.hashtags)
    caption_body = _trim_without_overflow_marker(
        metadata_profile["caption_body"],
        max(1, _metadata_int("caption_total_max_chars", 360) - len(hashtags_text) - 2),
    )
    reference_script = replace(
        enriched,
        title=post_title,
        post_title=post_title,
        caption=f"{caption_body}\n\n{hashtags_text}".strip(),
        post_body=metadata_profile["post_body"],
        pinned_comment=metadata_profile["pinned_comment"],
    )
    values = _metadata_values(reference_script, topic, sources, reference_script.hashtags, post_title)
    return _ensure_follower_conversion_contract(reference_script, values)


def check_policy(
    topic: TopicCandidate,
    script: ScriptPackage,
    sources: dict[str, Source],
    format_plan: ContentFormatPlan | None = None,
) -> GateResult:
    errors: list[str] = []
    warnings: list[str] = []
    checks: dict[str, bool] = {}
    active_plan = format_plan or FORMAT_SPECS["reward_deep"]

    checks["duration_matches_format"] = (
        active_plan.target_duration_min_sec <= script.target_duration_sec <= active_plan.target_duration_max_sec
    )
    checks["duration_over_60s_for_rewards"] = script.target_duration_sec >= 60 or not active_plan.reward_eligible
    checks["duration_under_120s"] = script.target_duration_sec <= 120
    checks["has_sources"] = bool(script.sources)
    checks["all_claims_sourced"] = all(claim.source_ids for claim in topic.claims)
    checks["known_sources"] = all(sid in sources for sid in script.sources)
    checks["no_paid_political_ad_language"] = not _contains_any(
        script.caption + " " + script.narration,
        _strategy_terms(POLICY_GATE_STRATEGY, "paid_political_ad_terms"),
    )
    checks["no_fake_ai_likeness"] = not _contains_any(
        script.narration,
        _strategy_terms(POLICY_GATE_STRATEGY, "fake_ai_likeness_terms"),
    )
    checks["aigc_disclosure_ready"] = bool(script.disclosure)
    checks["generic_tts_not_public_figure_voice"] = not _contains_any(
        script.narration,
        _strategy_terms(POLICY_GATE_STRATEGY, "generic_voice_clone_terms"),
    )
    checks["organic_political_commentary_only"] = not _contains_any(
        script.caption + " " + script.post_body,
        _strategy_terms(POLICY_GATE_STRATEGY, "organic_political_commentary_block_terms"),
    )
    checks["no_browser_evasion_language"] = not _contains_any(
        script.narration + " " + script.caption,
        _strategy_terms(POLICY_GATE_STRATEGY, "browser_evasion_terms"),
    )
    checks["creator_rewards_originality_guard"] = len(script.scenes) >= 5 and bool(script.narration.strip())
    comment_cta_terms = _strategy_terms(POLICY_GATE_STRATEGY, "comment_cta_terms")
    checks["has_comment_cta"] = _contains_any(
        " ".join([script.narration, script.caption, script.pinned_comment]),
        comment_cta_terms,
    )
    checks["original_visual_plan"] = all(scene.visual for scene in script.scenes)

    for name, ok in checks.items():
        if not ok:
            errors.append(name)

    warning_messages = _config_dict(POLICY_GATE_STRATEGY, "warnings")
    if _contains_any(script.caption, _strategy_terms(POLICY_GATE_STRATEGY, "candidate_person_terms")):
        warnings.append(str(warning_messages.get("political_person", "")))
    ai_trigger_terms = _strategy_terms(POLICY_GATE_STRATEGY, "ai_disclosure_trigger_terms")
    if _contains_any(script.caption, ai_trigger_terms) or _contains_any(script.narration, ai_trigger_terms):
        warnings.append(str(warning_messages.get("aigc_label", "")))

    score = 100 - len(errors) * 20 - max(0, len(warnings) - 2) * 5
    return GateResult(
        passed=not errors,
        score=max(0, score),
        errors=errors,
        warnings=warnings,
        checks=checks,
    )


QUESTION_MARKERS = ("?", "습니까", "입니까", "인가요", "인가", "나요", "까요")


def _has_question_marker(text: str) -> bool:
    normalized = _clean_card_text(text)
    return any(marker in normalized for marker in QUESTION_MARKERS)


def check_readability(script: ScriptPackage, format_plan: ContentFormatPlan | None = None) -> ReadabilityResult:
    active_plan = format_plan or FORMAT_SPECS["reward_deep"]
    max_on_screen = max((len(scene.on_screen_text) for scene in script.scenes), default=0)
    min_on_screen = min((len(scene.on_screen_text) for scene in script.scenes), default=0)
    max_body = max((len(scene.body) for scene in script.scenes), default=0)
    min_body = min((len(scene.body) for scene in script.scenes), default=0)
    format_body_max = _body_text_max_for_plan(active_plan)
    checks = {
        "scene_count_matches_format": active_plan.scene_count_min <= len(script.scenes) <= active_plan.scene_count_max,
        "scene_duration_5_to_12s": all(5 <= scene.duration_sec <= 12 for scene in script.scenes),
        "onscreen_text_under_34_chars": max_on_screen <= 34,
        "onscreen_text_at_least_8_chars": min_on_screen >= HEADLINE_MIN_CHARS,
        "narration_scene_under_95_chars": max_body <= 95,
        "body_text_at_least_32_chars": min_body >= BODY_TEXT_MIN_CHARS_MOBILE,
        "body_text_under_mobile_limit": max_body <= BODY_TEXT_MAX_CHARS_MOBILE,
        "body_text_under_format_limit": max_body <= format_body_max,
        "caption_under_metadata_limit": len(script.caption) <= _metadata_int("caption_total_max_chars", 360),
        "critical_text_safe_zone_reserved": True,
        "critical_text_horizontal_margin_104px": TEXT_SAFE_LEFT >= 104 and CANVAS_WIDTH - TEXT_SAFE_RIGHT >= 104,
        "critical_text_right_rail_clear": TEXT_SAFE_RIGHT <= TIKTOK_RIGHT_RAIL_LEFT,
        "critical_text_above_bottom_ui": CRITICAL_TEXT_BOTTOM <= TIKTOK_BOTTOM_UI_TOP,
        "headline_mobile_font_at_least_19px": _scaled_mobile_px(HEADLINE_FONT_MIN) >= MIN_HEADLINE_PREVIEW_PX,
        "body_mobile_font_at_least_14px": _scaled_mobile_px(BODY_FONT_MIN) >= MIN_BODY_PREVIEW_PX,
        "has_final_question": any(_has_question_marker(f"{scene.on_screen_text} {scene.body}") for scene in script.scenes[-2:]),
    }
    issues = [name for name, ok in checks.items() if not ok]
    return ReadabilityResult(
        passed=not issues,
        checks=checks,
        max_on_screen_chars=max_on_screen,
        max_narration_chars=max_body,
        issues=issues,
    )


def _count_terms(text: str, terms: list[str]) -> int:
    return sum(1 for term in terms if term in text)


def _scaled_mobile_px(font_size: int) -> float:
    return round(font_size * MOBILE_PREVIEW_WIDTH / CANVAS_WIDTH, 2)


def _clamp_score(value: int | float) -> int:
    return max(0, min(100, int(round(value))))


def _script_full_text(script: ScriptPackage) -> str:
    scene_text = " ".join(
        f"{scene.title} {scene.on_screen_text} {scene.body} {scene.visual}"
        for scene in script.scenes
    )
    return " ".join(
        [
            script.title,
            script.caption,
            script.post_title,
            script.post_body,
            script.pinned_comment,
            script.narration,
            " ".join(script.hashtags),
            scene_text,
        ]
    )


def _topic_search_terms(topic: TopicCandidate, sources: dict[str, Source]) -> list[str]:
    raw = " ".join(
        [
            topic.title,
            topic.angle,
            topic.slot,
            " ".join(claim.text for claim in topic.claims),
            " ".join(sources[source_id].title for source_id in topic.source_ids if source_id in sources),
        ]
    )
    prioritized = [term for term in SEARCH_VALUE_PRIORITY_TERMS if term in raw]
    tokens = re.findall(r"[가-힣A-Za-z0-9·]{2,}", raw)
    filtered = [
        token.strip("·")
        for token in tokens
        if len(token.strip("·")) >= 2 and token not in SEARCH_STOPWORDS and not token.startswith("hot_news")
    ]
    return list(dict.fromkeys([*prioritized, *filtered]))[:16]


def _topic_scene_anchor_terms(topic: TopicCandidate, sources: dict[str, Source] | None) -> list[str]:
    raw = _metadata_source_text(topic, sources)
    preferred = [
        *SEARCH_VALUE_PRIORITY_TERMS,
        "위증",
        "구형",
        "징역",
        "선고",
        "한덕수",
        "일베",
        "혐오",
        "조롱",
        "징벌",
        "폐쇄",
        "스타벅스",
        "오세훈",
        "정원오",
        "노무현",
        "추도식",
    ]
    return _issue_anchor_terms(raw, preferred)[:7]


def _topic_scene_anchor_coverage(
    script: ScriptPackage,
    topic: TopicCandidate,
    sources: dict[str, Source] | None,
) -> dict[str, Any]:
    anchors = _topic_scene_anchor_terms(topic, sources)
    scene_text = _clean_card_text(" ".join(f"{scene.on_screen_text} {scene.body}" for scene in script.scenes))
    matched = [term for term in anchors if term in scene_text]
    required = min(3, len(anchors))
    return {
        "anchors": anchors,
        "matched": matched,
        "missing": [term for term in anchors if term not in matched],
        "required": required,
    }


def _score_search_value(script: ScriptPackage, topic: TopicCandidate, sources: dict[str, Source]) -> int:
    full_text = _script_full_text(script)
    terms = _topic_search_terms(topic, sources)
    matched = [term for term in terms if term and term in full_text]
    high_intent_matches = [term for term in SEARCH_VALUE_PRIORITY_TERMS if term in full_text]
    score = _strategy_int(SEARCH_VALUE_STRATEGY, "base", 34)
    score += min(
        _strategy_int(SEARCH_VALUE_STRATEGY, "matched_cap", 34),
        len(matched) * _strategy_int(SEARCH_VALUE_STRATEGY, "matched_multiplier", 5),
    )
    score += min(
        _strategy_int(SEARCH_VALUE_STRATEGY, "high_intent_cap", 16),
        len(high_intent_matches) * _strategy_int(SEARCH_VALUE_STRATEGY, "high_intent_multiplier", 4),
    )
    score += _strategy_int(SEARCH_VALUE_STRATEGY, "multi_source_bonus", 8) if len(script.sources) >= 2 else 0
    score += (
        _strategy_int(SEARCH_VALUE_STRATEGY, "caption_match_bonus", 6)
        if any(term in script.caption for term in matched[:8])
        else 0
    )
    score += (
        _strategy_int(SEARCH_VALUE_STRATEGY, "title_match_bonus", 5)
        if any(term in script.title for term in matched[:8])
        else 0
    )
    hashtag_min = _metadata_int("hashtags_min", 8)
    hashtag_max = _metadata_int("hashtags_max", 12)
    score += (
        _strategy_int(SEARCH_VALUE_STRATEGY, "hashtag_shape_bonus", 3)
        if hashtag_min <= len(script.hashtags) <= hashtag_max
        else 0
    )
    return _clamp_score(score)


def _score_safe_provocation(script: ScriptPackage) -> int:
    first = script.scenes[0] if script.scenes else Scene(0, 0, "", "", "", "")
    hook_text = f"{script.title} {first.on_screen_text} {first.body}"
    full_text = _script_full_text(script)
    question_form = "?" in hook_text or bool(re.search(r"(까|나|습니까|일까요)\??$", first.on_screen_text.strip()))
    score = _strategy_int(SAFE_PROVOCATION_STRATEGY, "base", 30)
    score += (
        _strategy_int(SAFE_PROVOCATION_STRATEGY, "question_bonus", 18)
        if question_form
        else _strategy_int(SAFE_PROVOCATION_STRATEGY, "question_fallback_bonus", 4)
    )
    score += (
        _strategy_int(SAFE_PROVOCATION_STRATEGY, "short_headline_bonus", 10)
        if len(first.on_screen_text) <= HEADLINE_TARGET_MAX_CHARS
        else _strategy_int(SAFE_PROVOCATION_STRATEGY, "long_headline_bonus", 2)
    )
    score += min(
        _strategy_int(SAFE_PROVOCATION_STRATEGY, "provocation_cap", 24),
        _count_terms(hook_text, PROVOCATION_TERMS)
        * _strategy_int(SAFE_PROVOCATION_STRATEGY, "provocation_multiplier", 6),
    )
    score += min(
        _strategy_int(SAFE_PROVOCATION_STRATEGY, "contrast_cap", 14),
        _count_terms(hook_text, PROVOCATION_CONTRAST_TERMS)
        * _strategy_int(SAFE_PROVOCATION_STRATEGY, "contrast_multiplier", 3),
    )
    score += (
        _strategy_int(SAFE_PROVOCATION_STRATEGY, "credibility_bonus", 10)
        if _contains_any(hook_text, _strategy_terms(SAFE_PROVOCATION_STRATEGY, "credibility_terms"))
        else 0
    )
    score += (
        _strategy_int(SAFE_PROVOCATION_STRATEGY, "civic_bonus", 6)
        if _contains_any(full_text, _strategy_terms(SAFE_PROVOCATION_STRATEGY, "civic_terms"))
        else 0
    )
    unsafe_scan_text = (
        full_text.replace("확정되지 않은", "")
        .replace("확정되지", "")
        .replace("확정 전", "")
        .replace("확정 아님", "")
        .replace("확정 아닌", "")
        .replace("확정하지 않습니다", "")
        .replace("확정하지", "")
        .replace("확정할 수 없습니다", "")
        .replace("확정할 수 없", "")
    )
    if _contains_any(unsafe_scan_text, UNSAFE_PROVOCATION_TERMS):
        score += _strategy_int(SAFE_PROVOCATION_STRATEGY, "unsafe_penalty", -35)
    return _clamp_score(score)


def _score_script_quality(
    script: ScriptPackage,
    gate: GateResult,
    readability: ReadabilityResult,
    topic: TopicCandidate | None = None,
    sources: dict[str, Source] | None = None,
    format_plan: ContentFormatPlan | None = None,
) -> PublishQualityResult:
    full_text = _script_full_text(script)
    first = script.scenes[0] if script.scenes else Scene(0, 0, "", "", "", "")
    final = script.scenes[-1] if script.scenes else Scene(0, 0, "", "", "", "")
    question_count = full_text.count("?")
    active_plan = format_plan or FORMAT_SPECS["reward_deep"]

    hook_terms = _strategy_terms(SCRIPT_QUALITY_STRATEGY, "hook_terms")
    hook_score = 35
    hook_score += 20 if len(first.on_screen_text) <= 24 else 4
    hook_score += 18 if "?" in first.on_screen_text or "?" in first.body else 6
    hook_score += min(27, _count_terms(f"{first.on_screen_text} {first.body}", hook_terms) * 9)
    hook_score += 10 if any(mark in first.on_screen_text for mark in ['"', "'"]) else 0

    retention_terms = _strategy_terms(SCRIPT_QUALITY_STRATEGY, "retention_terms")
    unique_scene_titles = len({scene.title for scene in script.scenes})
    retention_score = 38
    retention_score += min(20, question_count * 5)
    retention_score += 12 if unique_scene_titles >= min(8, len(script.scenes)) else 4
    retention_score += 14 if "?" in final.on_screen_text or "?" in final.body else 3
    retention_score += min(16, _count_terms(full_text, retention_terms) * 3)

    comment_score = 28
    comment_terms = list(dict.fromkeys(["댓글", "공유", "반박", "근거", *_strategy_terms(SCRIPT_QUALITY_STRATEGY, "comment_terms")]))
    follow_terms = list(dict.fromkeys(["팔로우", "구독", "다음 검증", *_strategy_terms(SCRIPT_QUALITY_STRATEGY, "follow_terms")]))
    engagement_text = " ".join([script.caption, script.pinned_comment, _script_final_text(script)])
    comment_score += 20 if comment_terms and comment_terms[0] in engagement_text else 0
    comment_score += 18 if "?" in engagement_text else 0
    comment_score += 14 if any(term in engagement_text for term in comment_terms[1:]) else 0
    comment_score += 10 if any(term in script.pinned_comment for term in follow_terms) else 0
    comment_score += 10 if len(script.pinned_comment) <= 95 else 2

    target_terms = list(
        dict.fromkeys(
            [
                "정치",
                "선거",
                "민심",
                "지지율",
                "책임",
                "근거",
                "반론",
                "검증",
                "민주당",
                "국민의힘",
                "이재명",
                "윤석열",
                "김건희",
                "국회",
                "검찰",
                *_strategy_terms(SCRIPT_QUALITY_STRATEGY, "target_terms"),
            ]
        )
    )
    target_fit = 42 + min(48, _count_terms(full_text, target_terms) * 6)
    target_title_terms = list(
        dict.fromkeys(["정치", "선거", "민심", "책임", "검증", *_strategy_terms(SCRIPT_QUALITY_STRATEGY, "target_title_terms")])
    )
    target_fit += 10 if any(term in script.title for term in target_title_terms) else 0

    monetization_fit = 35
    monetization_fit += 25 if script.target_duration_sec >= 60 else 0
    monetization_fit += 15 if script.target_duration_sec <= 120 else -10
    monetization_fit += 15 if active_plan.scene_count_min <= len(script.scenes) <= active_plan.scene_count_max else 0
    monetization_fit += 10 if _metadata_int("hashtags_min", 8) <= len(script.hashtags) <= _metadata_int("hashtags_max", 12) else 0
    monetization_fit += 10 if len(script.caption) <= _metadata_int("caption_total_max_chars", 360) else 0

    policy_safety = gate.score if gate.passed else min(45, gate.score)
    policy_safety -= max(0, len(gate.warnings) - 2) * 5
    readability_score = 100 if readability.passed else max(35, 82 - len(readability.issues) * 14)
    provocation_score = _score_safe_provocation(script)
    search_value_score = (
        _score_search_value(script, topic, sources or {})
        if topic is not None
        else 70
    )

    caption_follow_cta = _caption_has_follow_cta(script.caption)
    video_end_follow_promise = _script_has_end_follow_promise(script)
    series_identity = _text_has_series_identity(script.caption) or _text_has_series_identity(_script_final_text(script))
    profile_transition = _text_has_profile_transition(script.caption) or _text_has_profile_transition(_script_final_text(script))
    pinned_follow_cta = any(term in script.pinned_comment for term in follow_terms)
    follower_conversion_score = (
        25
        + (28 if caption_follow_cta else 0)
        + (22 if video_end_follow_promise else 0)
        + (15 if series_identity else 0)
        + (8 if profile_transition else 0)
        + (4 if pinned_follow_cta else 0)
    )

    scores = {
        "hook_strength": _clamp_score(hook_score),
        "safe_provocation": provocation_score,
        "search_value": search_value_score,
        "retention_design": _clamp_score(retention_score),
        "comment_trigger": _clamp_score(comment_score),
        "follower_conversion": _clamp_score(follower_conversion_score),
        "target_fit": _clamp_score(target_fit),
        "monetization_fit": _clamp_score(monetization_fit),
        "policy_safety": _clamp_score(policy_safety),
        "readability": _clamp_score(readability_score),
    }
    publish_score = _clamp_score(sum(scores[key] * weight for key, weight in SCRIPT_QUALITY_WEIGHTS.items()))

    blockers: list[str] = []
    notes: list[str] = []
    if not gate.passed:
        blockers.append("policy_gate_failed")
    if not readability.passed:
        blockers.append("readability_gate_failed")
    publish_minimum = SCRIPT_QUALITY_MINIMUMS.get("publish_ready_score", 85)
    if publish_score < publish_minimum:
        blockers.append(f"publish_ready_score_below_{publish_minimum}:{publish_score}")
    critical_minimum = SCRIPT_QUALITY_MINIMUMS.get("critical_score", 70)
    for key in _strategy_terms(SCRIPT_QUALITY_STRATEGY, "critical_score_keys"):
        if scores[key] < critical_minimum:
            blockers.append(f"{key}_below_{critical_minimum}:{scores[key]}")
    search_minimum = (
        SCRIPT_QUALITY_MINIMUMS.get("reward_search_value", 80)
        if active_plan.reward_eligible
        else SCRIPT_QUALITY_MINIMUMS.get("growth_search_value", 72)
    )
    if scores["search_value"] < search_minimum:
        blockers.append(f"search_value_below_{search_minimum}:{scores['search_value']}")
    for key, ok in _metadata_checks(script).items():
        if not ok:
            blockers.append(f"metadata_{key}_failed")
    if topic is not None:
        anchor_coverage = _topic_scene_anchor_coverage(script, topic, sources)
        if len(anchor_coverage["matched"]) < anchor_coverage["required"]:
            missing = ",".join(anchor_coverage["missing"][:3])
            blockers.append(f"topic_anchor_terms_missing:{missing}")
    scene_body_text = "\n".join(scene.body for scene in script.scenes)
    for phrase in _strategy_terms(SCRIPT_QUALITY_STRATEGY, "generic_repetition_phrases"):
        if phrase and scene_body_text.count(phrase) >= 2:
            blockers.append(f"generic_phrase_repeated:{phrase}")
    if _script_has_headline_quote_format(script):
        blockers.append("headline_quote_format_banned")
    if _contains_any(full_text, FATIGUED_QUESTION_TEMPLATE_TERMS):
        blockers.append("fatigued_question_template_banned")
    if question_count < 2:
        notes.append("question_density_low")
    if not caption_follow_cta:
        blockers.append("caption_follow_cta_missing")
    if not video_end_follow_promise:
        blockers.append("video_end_follow_promise_missing")
    if not series_identity:
        blockers.append("series_identity_missing")
    if not profile_transition:
        blockers.append("profile_transition_trigger_missing")
    if not pinned_follow_cta:
        notes.append("pinned_comment_follow_cta_missing")

    return PublishQualityResult(
        passed=not blockers,
        selected_variant=script.variant_id,
        publish_ready_score=publish_score,
        scores=scores,
        blockers=blockers,
        notes=notes,
    )


def select_publish_script(
    variants: list[ScriptPackage],
    topic: TopicCandidate,
    sources: dict[str, Source],
    format_plan: ContentFormatPlan | None = None,
    preserve_existing_metadata: bool = False,
) -> tuple[ScriptPackage, GateResult, ReadabilityResult, PublishQualityResult]:
    scored: list[tuple[ScriptPackage, GateResult, ReadabilityResult, PublishQualityResult]] = []
    variant_rows: list[dict[str, Any]] = []
    for script in variants:
        if "reference_v3" not in script.variant_id:
            script = _enrich_post_metadata(
                script,
                topic,
                sources,
                preserve_existing=preserve_existing_metadata,
            )
        gate = check_policy(topic, script, sources, format_plan)
        readability = check_readability(script, format_plan)
        quality = _score_script_quality(script, gate, readability, topic, sources, format_plan)
        scored.append((script, gate, readability, quality))
        variant_rows.append(
            {
                "variant_id": script.variant_id,
                "title": script.title,
                "publish_ready_score": quality.publish_ready_score,
                "scores": quality.scores,
                "passed": quality.passed,
                "blockers": quality.blockers,
                "notes": quality.notes,
            }
        )

    selected = max(
        scored,
        key=lambda item: (
            item[3].passed,
            item[3].publish_ready_score,
            item[3].scores.get("hook_strength", 0),
            item[3].scores.get("comment_trigger", 0),
        ),
    )
    script, gate, readability, quality = selected
    quality = replace(quality, variant_scores=variant_rows)
    return script, gate, readability, quality


def review_content(
    script: ScriptPackage,
    gate: GateResult,
    readability: ReadabilityResult,
    visual_assets: list[VisualAsset],
    format_plan: ContentFormatPlan | None = None,
    visual_quality: VisualQualityResult | None = None,
) -> ContentReview:
    """Editorial review for whether the artifact is worth uploading."""
    blockers: list[str] = []
    notes: list[str] = []
    blocker_messages = _config_dict(CONTENT_REVIEW_STRATEGY, "blockers")
    note_messages = _config_dict(CONTENT_REVIEW_STRATEGY, "notes")

    full_text = f"{script.title} {script.caption} {script.narration}"
    meta_terms = _strategy_terms(CONTENT_REVIEW_STRATEGY, "meta_terms")
    if sum(1 for term in meta_terms if term in full_text) >= 2:
        blockers.append(str(blocker_messages.get("internal_strategy", "")))

    if not gate.passed:
        blockers.append(str(blocker_messages.get("policy_gate", "")))

    if not readability.passed:
        blockers.append(str(blocker_messages.get("readability_gate", "")))
        notes.extend(f"readability:{issue}" for issue in readability.issues)

    generated_visuals = [
        asset
        for asset in visual_assets
        if asset.status == "generated" and asset.provider in {"codex_cli", "gemini_api"}
    ]
    fallback_visuals = [asset for asset in visual_assets if asset.status != "generated"]
    if len(generated_visuals) != len(script.scenes):
        blockers.append(
            _format_prompt_template(
                str(blocker_messages.get("visual_shortage", "")),
                {"generated": len(generated_visuals), "total": len(script.scenes)},
            )
        )
    if fallback_visuals:
        notes.append(
            _format_prompt_template(
                str(note_messages.get("fallback_visuals", "")),
                {"scenes": ", ".join(f"scene {asset.scene_id}" for asset in fallback_visuals)},
            )
        )
    visual_quality = visual_quality or check_visual_quality(visual_assets, script.scenes)
    if not visual_quality.passed:
        blockers.append(str(blocker_messages.get("visual_quality_gate", "")))
        notes.extend(f"visual_quality:{blocker}" for blocker in visual_quality.blockers)

    if "owner_reference_reboxschool_chat" in script.sources:
        notes.append(str(note_messages.get("owner_reference", "")))

    active_plan = format_plan or FORMAT_SPECS["reward_deep"]
    if active_plan.reward_eligible and script.target_duration_sec < 60:
        blockers.append(str(blocker_messages.get("reward_duration", "")))

    avg_scene_len = script.target_duration_sec / max(1, len(script.scenes))
    if avg_scene_len > 12:
        notes.append(str(note_messages.get("long_scene", "")))

    if not _contains_any(full_text, _strategy_terms(POLICY_GATE_STRATEGY, "comment_cta_terms")):
        notes.append(str(note_messages.get("weak_comment_cta", "")))

    if len(script.hashtags) > _metadata_int("hashtags_max", 12):
        notes.append(str(note_messages.get("hashtag_spam", "")))

    scores = {
        "audience_value": 82,
        "brand_fit": 86,
        "policy_safety": 96 if gate.passed else 40,
        "monetization_fit": 84 if script.target_duration_sec >= 60 or not active_plan.reward_eligible else 45,
        "visual_readiness": 90 if len(generated_visuals) == len(script.scenes) and readability.passed else 45,
    }
    if blockers:
        scores = {key: min(value, 55) for key, value in scores.items()}

    recommendation = "upload_candidate" if not blockers and min(scores.values()) >= 70 else "revise_before_upload"
    return ContentReview(
        passed=recommendation == "upload_candidate",
        recommendation=recommendation,
        scores=scores,
        blockers=blockers,
        notes=notes,
    )


def _contains_any(text: str, needles: list[str]) -> bool:
    lowered = text.lower()
    return any(needle.lower() in lowered for needle in needles)


def _scenes_with_audio_timings(scenes: list[Scene], audio_asset: AudioAsset) -> list[Scene]:
    if not audio_asset.scene_timings:
        return scenes
    duration_by_scene = {
        int(timing["scene_id"]): int(timing["card_duration_sec"])
        for timing in audio_asset.scene_timings
        if "scene_id" in timing and "card_duration_sec" in timing
    }
    return [
        replace(scene, duration_sec=duration_by_scene.get(scene.scene_id, scene.duration_sec))
        for scene in scenes
    ]


def build_visual_beats(
    scenes: list[Scene],
    format_plan: ContentFormatPlan | None = None,
    *,
    render_style: str | None = None,
) -> list[VisualBeat]:
    plan = format_plan or FORMAT_SPECS["reward_deep"]
    cadence = plan_visual_cadence(scenes, plan)
    tiktok_native_caption = render_style == CINEMATIC_SUBTITLE_RENDER_STYLE
    motion_enabled = _env_bool("AINO_CONTROLLED_VISUAL_MOTION", bool(VISUAL_MOTION_STRATEGY.get("enabled", True)))
    if tiktok_native_caption:
        motion_enabled = False
    zoom_delta = max(0.0, min(0.08, float(VISUAL_MOTION_STRATEGY.get("zoom_delta", 0.028))))
    pan_px = max(0, min(40, int(VISUAL_MOTION_STRATEGY.get("pan_px", 18))))
    if tiktok_native_caption:
        overlay_effects = ["caption_pop", "receipt_flash", "hard_cut"]
    else:
        overlay_effects = [
            str(item)
            for item in VISUAL_MOTION_STRATEGY.get("overlay_effects", ["hold"])
            if str(item).strip()
        ] or ["hold"]
    beats_by_scene: dict[int, int] = {}
    for scene in scenes:
        base_count = 3 if scene.duration_sec >= 9 else 2
        if tiktok_native_caption:
            base_count = 4 if scene.duration_sec >= 9 else 3
        if plan.format_id == "growth_short" and scene.scene_id in {1, len(scenes)}:
            base_count += 1
        beats_by_scene[scene.scene_id] = base_count

    while sum(beats_by_scene.values()) < cadence.target_visual_beats and beats_by_scene:
        target_scene_id = max(
            beats_by_scene,
            key=lambda scene_id: (
                next((scene.duration_sec for scene in scenes if scene.scene_id == scene_id), 0),
                -beats_by_scene[scene_id],
            ),
        )
        beats_by_scene[target_scene_id] += 1

    beats: list[VisualBeat] = []
    for scene in scenes:
        count = max(1, beats_by_scene.get(scene.scene_id, 1))
        base_duration = scene.duration_sec / count
        start = 0.0
        for beat_index in range(count):
            duration = base_duration
            if beat_index == count - 1:
                duration = scene.duration_sec - start
            beats.append(
                VisualBeat(
                    scene_id=scene.scene_id,
                    beat_id=beat_index + 1,
                    start_sec=round(start, 3),
                    duration_sec=round(max(0.1, duration), 3),
                    zoom_start=1.0 + (zoom_delta * 0.25 * beat_index if motion_enabled else 0.0),
                    zoom_end=1.0 + (zoom_delta * (0.55 + 0.15 * beat_index) if motion_enabled else 0.0),
                    pan_x=(((-1) ** (scene.scene_id + beat_index)) * pan_px) if motion_enabled else 0,
                    pan_y=(((-1) ** beat_index) * max(0, pan_px // 3)) if motion_enabled else 0,
                    overlay=(
                        overlay_effects[(scene.scene_id + beat_index) % len(overlay_effects)]
                        if motion_enabled or tiktok_native_caption
                        else "hold"
                    ),
                )
            )
            start += base_duration
    return beats


def _visual_motion_summary(visual_beats: list[VisualBeat]) -> dict[str, Any]:
    camera_motion_count = sum(
        1
        for beat in visual_beats
        if abs(beat.zoom_end - beat.zoom_start) > 0.001 or beat.pan_x != 0 or beat.pan_y != 0
    )
    overlay_effect_count = sum(1 for beat in visual_beats if beat.overlay != "hold")
    return {
        "camera_motion_count": camera_motion_count,
        "overlay_effect_count": overlay_effect_count,
        "all_static_hold": camera_motion_count == 0 and overlay_effect_count == 0,
    }


def _beats_for_scene(visual_beats: list[VisualBeat], scene_id: int, scene_duration_sec: int) -> list[VisualBeat]:
    scene_beats = [beat for beat in visual_beats if beat.scene_id == scene_id]
    if scene_beats:
        return scene_beats
    return [
        VisualBeat(
            scene_id=scene_id,
            beat_id=1,
            start_sec=0.0,
            duration_sec=float(scene_duration_sec),
            zoom_start=1.0,
            zoom_end=1.0,
            pan_x=0,
            pan_y=0,
            overlay="hold",
        )
    ]


def _image_budget_paid_providers() -> set[str]:
    value = IMAGE_BUDGET_STRATEGY.get("paid_providers", [])
    return {str(item) for item in value if str(item).strip()} if isinstance(value, list) else {"codex_cli", "gemini_api"}


def _image_budget_local_modes() -> set[str]:
    value = IMAGE_BUDGET_STRATEGY.get("local_modes", [])
    return {str(item) for item in value if str(item).strip()} if isinstance(value, list) else {"local"}


def _image_mode_can_use_external_provider(image_mode: str) -> bool:
    paid = _image_budget_paid_providers()
    return image_mode == "auto" or image_mode in paid


def _generated_paid_images_used_on_day(output_dir: Path, day: dt.date | None = None) -> int:
    if not output_dir.exists():
        return 0
    active_day = day or dt.datetime.now().date()
    paid = _image_budget_paid_providers()
    used = 0
    for path in output_dir.glob("**/visual_assets.json"):
        try:
            if dt.datetime.fromtimestamp(path.stat().st_mtime).date() != active_day:
                continue
            rows = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            continue
        if not isinstance(rows, list):
            continue
        for row in rows:
            if (
                isinstance(row, dict)
                and str(row.get("provider", "")) in paid
                and str(row.get("status", "")) == "generated"
            ):
                used += 1
    return used


def decide_image_budget(
    *,
    output_dir: Path,
    image_mode: str,
    real_image_limit: int | None,
    gate: GateResult,
    readability: ReadabilityResult,
    quality: PublishQualityResult,
    adaptive_default_limit: int | None = None,
) -> ImageBudgetDecision:
    reasons: list[str] = []
    if real_image_limit is None:
        requested_limit = max(0, int(adaptive_default_limit or _strategy_int(IMAGE_BUDGET_STRATEGY, "per_run_real_image_limit", 14)))
        reasons.append("adaptive_real_image_limit")
    else:
        requested_limit = max(0, int(real_image_limit))
    per_run_limit = _strategy_int(IMAGE_BUDGET_STRATEGY, "per_run_real_image_limit", 14)
    daily_limit = _strategy_int(IMAGE_BUDGET_STRATEGY, "daily_real_image_limit", 42)
    daily_limit_override_env = str(
        IMAGE_BUDGET_STRATEGY.get("daily_limit_override_env", "AINO_DAILY_REAL_IMAGE_LIMIT_OVERRIDE")
    )
    daily_limit_override = os.environ.get(daily_limit_override_env)
    if daily_limit_override:
        with contextlib.suppress(ValueError):
            daily_limit = max(daily_limit, int(daily_limit_override))
    min_score = _strategy_int(IMAGE_BUDGET_STRATEGY, "min_publish_ready_score", 85)
    used_today = _generated_paid_images_used_on_day(output_dir)

    override_env = str(IMAGE_BUDGET_STRATEGY.get("override_env", "AINO_ALLOW_PAID_IMAGE_OVERRIDE"))
    override_enabled = os.environ.get(override_env, "").lower() in {"1", "true", "yes", "on"}
    local_mode = image_mode in _image_budget_local_modes()

    if privacy_policy.is_local_only():
        reasons.append("privacy_local_only")
    if local_mode:
        reasons.append("local_image_mode")
    if requested_limit <= 0:
        reasons.append("requested_real_image_limit_zero")
    if not _image_mode_can_use_external_provider(image_mode):
        reasons.append("image_mode_not_external")

    if not override_enabled:
        if bool(IMAGE_BUDGET_STRATEGY.get("require_gate_passed", True)) and not gate.passed:
            reasons.append("policy_gate_not_passed")
        if bool(IMAGE_BUDGET_STRATEGY.get("require_readability_passed", True)) and not readability.passed:
            reasons.append("readability_not_passed")
        if bool(IMAGE_BUDGET_STRATEGY.get("require_quality_passed", True)) and not quality.passed:
            reasons.append("publish_quality_not_passed")
        if quality.publish_ready_score < min_score:
            reasons.append("publish_ready_score_below_minimum")
    else:
        reasons.append("manual_paid_image_override_enabled")

    remaining_daily = max(0, daily_limit - used_today)
    if remaining_daily <= 0:
        reasons.append("daily_real_image_budget_exhausted")

    hard_blockers = {
        "privacy_local_only",
        "local_image_mode",
        "requested_real_image_limit_zero",
        "image_mode_not_external",
        "daily_real_image_budget_exhausted",
    }
    soft_gate_reasons = {
        "policy_gate_not_passed",
        "readability_not_passed",
        "publish_quality_not_passed",
        "publish_ready_score_below_minimum",
    }
    blocked = bool(hard_blockers.intersection(reasons)) or (not override_enabled and bool(soft_gate_reasons.intersection(reasons)))
    effective_limit = 0 if blocked else min(requested_limit, per_run_limit, remaining_daily)
    effective_mode = image_mode if effective_limit > 0 else "local"
    if effective_limit == 0 and not reasons:
        reasons.append("effective_real_image_limit_zero")

    return ImageBudgetDecision(
        version=str(IMAGE_BUDGET_STRATEGY.get("version", "image_budget_v1")),
        requested_image_mode=image_mode,
        effective_image_mode=effective_mode,
        requested_real_image_limit=requested_limit,
        effective_real_image_limit=effective_limit,
        allowed_external_generation=effective_limit > 0,
        reasons=list(dict.fromkeys(reasons)),
        daily_real_image_limit=daily_limit,
        daily_real_images_used=used_today,
        min_publish_ready_score=min_score,
        gate_passed=gate.passed,
        readability_passed=readability.passed,
        quality_passed=quality.passed,
        publish_ready_score=quality.publish_ready_score,
    )


def render_artifacts(
    *,
    run_dir: Path,
    run_id: str,
    topic: TopicCandidate,
    script: ScriptPackage,
    gate: GateResult,
    readability: ReadabilityResult,
    quality: PublishQualityResult,
    review: ContentReview,
    visual_assets: list[VisualAsset],
    sources: dict[str, Source],
    brand_name: str,
    format_plan: ContentFormatPlan,
    visual_quality: VisualQualityResult,
    fact_pack: FactPack,
    risk_flags: RiskFlags,
    source_card: SourceCard,
    reference_fit: ReferenceFit,
    angle_brief: AngleBrief,
    storyboard_brief: StoryboardBrief,
    topic_discovery: dict[str, Any] | None = None,
    editorial_plan: EditorialPlan | None = None,
    planned_publish_at_local: str | None = None,
    image_budget_decision: ImageBudgetDecision | None = None,
) -> RenderArtifacts:
    run_dir.mkdir(parents=True, exist_ok=True)
    frames_dir = run_dir / "frames"
    frames_dir.mkdir(parents=True, exist_ok=True)

    fact_pack_path = run_dir / "fact_pack.json"
    risk_flags_path = run_dir / "risk_flags.json"
    source_card_path = run_dir / "source_card.json"
    reference_fit_path = run_dir / "reference_fit.json"
    angle_brief_path = run_dir / "angle_brief.json"
    storyboard_brief_path = run_dir / "storyboard_brief.json"
    tts_performance_plan_path = run_dir / "tts_performance_plan.json"
    _write_json(fact_pack_path, asdict(fact_pack))
    _write_json(risk_flags_path, asdict(risk_flags))
    _write_json(source_card_path, asdict(source_card))
    _write_json(reference_fit_path, asdict(reference_fit))
    _write_json(angle_brief_path, asdict(angle_brief))
    _write_json(storyboard_brief_path, asdict(storyboard_brief))
    tts_performance_plan = build_tts_performance_plan(script, angle_brief)
    _write_json(tts_performance_plan_path, asdict(tts_performance_plan))

    audio_asset = _write_tts_audio(script.narration, run_dir, scenes=script.scenes)
    render_scenes = _scenes_with_audio_timings(script.scenes, audio_asset)
    asset_by_scene = {asset.scene_id: asset for asset in visual_assets}
    native_image_text_render = bool(render_scenes) and all(
        _asset_uses_native_image_text(asset_by_scene.get(scene.scene_id)) for scene in render_scenes
    )
    cinematic_subtitle_render = _all_assets_use_cinematic_subtitles(render_scenes, asset_by_scene)
    if cinematic_subtitle_render:
        render_scenes, render_textfit_report = _fit_cinematic_subtitle_scene_texts(render_scenes)
    elif native_image_text_render:
        render_textfit_report = {
            "version": "render_textfit_v2",
            "mode": "native_image_text",
            "all_fit": True,
            "rows": [
                {
                    "scene_id": scene.scene_id,
                    "rendered_overlay_text": False,
                    "diegetic_text": str(
                        (
                            (asset_by_scene.get(scene.scene_id).visual_brief or {})
                            if asset_by_scene.get(scene.scene_id)
                            else {}
                        ).get("diegetic_text")
                        or ""
                    ),
                }
                for scene in render_scenes
            ],
        }
    else:
        render_scenes, render_textfit_report = _fit_render_scene_texts(render_scenes, asset_by_scene)
    render_textfit_report_path = run_dir / "render_textfit_report.json"
    _write_json(render_textfit_report_path, render_textfit_report)
    render_duration_sec = sum(scene.duration_sec for scene in render_scenes)

    font_small = _font(30)
    font_micro = _font(24)

    scene_images: list[Image.Image] = []
    for index, scene in enumerate(render_scenes):
        img = _scene_image(
            scene,
            index,
            len(render_scenes),
            asset_by_scene.get(scene.scene_id),
            font_small,
            font_micro,
            brand_name,
        )
        scene_images.append(img)
        img.save(frames_dir / f"scene_{scene.scene_id:02d}.png")

    storyboard_path = run_dir / "storyboard.png"
    _storyboard(scene_images, render_scenes, storyboard_path)
    mobile_storyboard_path, mobile_checks_path, mobile_checks = _write_mobile_previews(
        scene_images,
        render_scenes,
        run_dir,
        asset_by_scene,
    )

    visual_beats = build_visual_beats(
        render_scenes,
        format_plan,
        render_style=CINEMATIC_SUBTITLE_RENDER_STYLE if cinematic_subtitle_render else None,
    )
    visual_cadence = plan_visual_cadence(render_scenes, format_plan)
    visual_beats_path = run_dir / "visual_beats.json"
    _write_json(visual_beats_path, [asdict(beat) for beat in visual_beats])

    video_only_path = run_dir / "preview_video_only.mp4"
    mp4_path = run_dir / "preview_1080x1920.mp4"
    _write_mp4(scene_images, render_scenes, video_only_path, visual_beats=visual_beats)
    _mux_audio(video_only_path, Path(audio_asset.path), mp4_path, render_duration_sec)

    manifest_path = run_dir / "manifest.json"
    signal_snapshot_path = run_dir / "signal_snapshot.json"
    asset_manifest_path = run_dir / "visual_assets.json"
    selected_script_path = run_dir / "selected_script.json"
    content_plan_path = run_dir / "content_plan.json"
    visual_plan_path = run_dir / "visual_plan.json"
    visual_cadence_path = run_dir / "visual_cadence_plan.json"
    tts_plan_path = run_dir / "tts_plan.json"
    render_manifest_path = run_dir / "render_manifest.json"
    upload_plan_path = run_dir / "upload_plan.json"
    keyword_plan_path = run_dir / "keyword_plan.json"
    topic_pool_path = run_dir / "topic_pool.json"
    topic_plan_path = run_dir / "topic_plan.json"
    deep_research_report_path = run_dir / "deep_research_report.json"
    editorial_plan_path = run_dir / "editorial_plan.json"
    report_path = run_dir / "verification_report.html"
    _write_json(asset_manifest_path, [asdict(asset) for asset in visual_assets])
    signal_snapshot_data = (topic_discovery or {}).get("signal_snapshot")
    keyword_plan_data = (topic_discovery or {}).get("keyword_plan")
    topic_pool_data = (topic_discovery or {}).get("topic_pool")
    topic_plan_data = (topic_discovery or {}).get("topic_plan")
    deep_research_report_data = (topic_discovery or {}).get("deep_research_report")
    has_signal_snapshot = isinstance(signal_snapshot_data, dict)
    has_keyword_plan = isinstance(keyword_plan_data, dict)
    has_topic_pool = isinstance(topic_pool_data, dict)
    has_topic_plan = isinstance(topic_plan_data, dict)
    has_deep_research_report = isinstance(deep_research_report_data, dict)
    if has_signal_snapshot:
        _write_json(signal_snapshot_path, signal_snapshot_data)
    if has_keyword_plan:
        _write_json(keyword_plan_path, keyword_plan_data)
    if has_topic_pool:
        _write_json(topic_pool_path, topic_pool_data)
    if has_topic_plan:
        _write_json(topic_plan_path, topic_plan_data)
    if has_deep_research_report:
        _write_json(deep_research_report_path, deep_research_report_data)
    if editorial_plan is not None:
        _write_json(editorial_plan_path, asdict(editorial_plan))
    selected_script_plan = build_selected_script_plan(script, gate, readability, quality, format_plan)
    _write_json(selected_script_path, asdict(selected_script_plan))
    content_plan = build_content_plan(
        topic,
        script,
        sources,
        format_plan,
        topic_discovery=topic_discovery,
        visual_assets=visual_assets,
    )
    _write_json(content_plan_path, asdict(content_plan))
    visual_plan = build_visual_plan(content_plan, visual_assets)
    _write_json(visual_plan_path, asdict(visual_plan))
    _write_json(visual_cadence_path, asdict(visual_cadence))
    tts_plan = build_tts_plan(script, audio_asset)
    _write_json(tts_plan_path, asdict(tts_plan))
    source_rows = [asdict(sources[sid]) for sid in script.sources if sid in sources]
    audio_ready = audio_asset.provider == "elevenlabs" and audio_asset.status == "generated"
    synced_duration_matches_format = (
        format_plan.target_duration_min_sec <= render_duration_sec <= format_plan.target_duration_max_sec
    )
    mobile_visual_passed = all(check.passed for check in mobile_checks)
    layout_quality = _card_layout_quality(render_scenes, asset_by_scene)
    upload_ready = (
        gate.passed
        and readability.passed
        and review.passed
        and audio_ready
        and mobile_visual_passed
        and bool(layout_quality.get("passed"))
        and synced_duration_matches_format
    )
    publish_ready = upload_ready and quality.passed
    manifest_status = "publish_ready" if publish_ready else ("upload_ready" if upload_ready else "needs_revision")
    render_manifest = build_render_manifest(
        run_id=run_id,
        render_scenes=render_scenes,
        visual_beats=visual_beats,
        mp4_path=mp4_path,
        video_only_path=video_only_path,
        storyboard_path=storyboard_path,
        mobile_storyboard_path=mobile_storyboard_path,
        mobile_checks_path=mobile_checks_path,
        frames_dir=frames_dir,
        render_textfit_report_path=render_textfit_report_path,
        gate=gate,
        readability=readability,
        review=review,
        quality=quality,
        audio_asset=audio_asset,
        visual_quality=visual_quality,
        synced_duration_matches_format=synced_duration_matches_format,
        mobile_visual_passed=mobile_visual_passed,
        layout_quality=layout_quality,
        visual_cadence=visual_cadence,
    )
    _write_json(render_manifest_path, asdict(render_manifest))
    manifest = {
        "run_id": run_id,
        "created_at": dt.datetime.now(dt.timezone.utc).isoformat(),
        "status": manifest_status,
        "privacy": privacy_policy.manifest_record(),
        "format_plan": asdict(format_plan),
        "workflow_contract": {
            "version": "generation_quality_contract_v1",
            "fact_pack": fact_pack.gate_passed,
            "risk_flags": risk_flags.gate_passed,
            "source_card": source_card.gate_passed,
            "reference_fit": reference_fit.gate_passed,
            "angle_brief": angle_brief.gate_passed,
            "storyboard_brief": storyboard_brief.gate_passed,
            "tts_performance_plan": tts_performance_plan.gate_passed,
        },
        "fact_pack": asdict(fact_pack),
        "risk_flags": asdict(risk_flags),
        "source_card": asdict(source_card),
        "reference_fit": asdict(reference_fit),
        "angle_brief": asdict(angle_brief),
        "storyboard_brief": asdict(storyboard_brief),
        "editorial_plan": asdict(editorial_plan) if editorial_plan is not None else None,
        "selected_script_plan": asdict(selected_script_plan),
        "content_plan": asdict(content_plan),
        "visual_plan": asdict(visual_plan),
        "visual_cadence_plan": asdict(visual_cadence),
        "tts_performance_plan": asdict(tts_performance_plan),
        "tts_plan": asdict(tts_plan),
        "render_manifest": asdict(render_manifest),
        "render_textfit_report": render_textfit_report,
        "layout_quality": layout_quality,
        "image_budget_decision": asdict(image_budget_decision) if image_budget_decision is not None else None,
        "topic_discovery": topic_discovery,
        "topic": asdict(topic),
        "script": asdict(script),
        "gate": asdict(gate),
        "readability": asdict(readability),
        "quality": asdict(quality),
        "review": asdict(review),
        "visual_quality": asdict(visual_quality),
        "visual_assets": [asdict(asset) for asset in visual_assets],
        "audio_asset": asdict(audio_asset),
        "visual_beats": [asdict(beat) for beat in visual_beats],
        "visual_beat_count": len(visual_beats),
        "visual_motion": _visual_motion_summary(visual_beats),
        "mobile_visual_checks": [asdict(check) for check in mobile_checks],
        "mobile_visual_passed": mobile_visual_passed,
        "synced_duration_matches_format": synced_duration_matches_format,
        "synced_scenes": [asdict(scene) for scene in render_scenes],
        "synced_duration_sec": render_duration_sec,
        "sources": source_rows,
        "artifacts": {
            "mp4": str(mp4_path),
            "audio_path": audio_asset.path,
            "audio_provider": audio_asset.provider,
            "audio_status": audio_asset.status,
            "tts_text_path": audio_asset.tts_text_path,
            "tts_lint_path": audio_asset.lint_path,
            "video_only_mp4": str(video_only_path),
            "storyboard": str(storyboard_path),
            "mobile_preview_storyboard": str(mobile_storyboard_path),
            "mobile_visual_checks": str(mobile_checks_path),
            "render_textfit_report": str(render_textfit_report_path),
            "mobile_previews_dir": str(run_dir / "mobile_previews"),
            "report_html": str(report_path),
            "frames_dir": str(frames_dir),
            "asset_manifest": str(asset_manifest_path),
            "fact_pack": str(fact_pack_path),
            "risk_flags": str(risk_flags_path),
            "source_card": str(source_card_path),
            "reference_fit": str(reference_fit_path),
            "angle_brief": str(angle_brief_path),
            "storyboard_brief": str(storyboard_brief_path),
            "selected_script": str(selected_script_path),
            "content_plan": str(content_plan_path),
            "visual_plan": str(visual_plan_path),
            "visual_cadence_plan": str(visual_cadence_path),
            "tts_performance_plan": str(tts_performance_plan_path),
            "tts_plan": str(tts_plan_path),
            "render_manifest": str(render_manifest_path),
            "visual_beats": str(visual_beats_path),
        },
    }
    if planned_publish_at_local:
        manifest["planned_publish_at_local"] = planned_publish_at_local
        manifest["schedule_status"] = "planned_not_scheduled"
    if has_signal_snapshot:
        manifest["artifacts"]["signal_snapshot"] = str(signal_snapshot_path)
    if has_keyword_plan:
        manifest["artifacts"]["keyword_plan"] = str(keyword_plan_path)
    if has_topic_pool:
        manifest["artifacts"]["topic_pool"] = str(topic_pool_path)
    if has_topic_plan:
        manifest["artifacts"]["topic_plan"] = str(topic_plan_path)
    if has_deep_research_report:
        manifest["artifacts"]["deep_research_report"] = str(deep_research_report_path)
    if editorial_plan is not None:
        manifest["artifacts"]["editorial_plan"] = str(editorial_plan_path)
    upload_validation = validate_manifest_for_upload(manifest)
    upload_plan = build_upload_plan(
        run_id=run_id,
        script=script,
        format_plan=format_plan,
        validation=upload_validation,
        mp4_path=mp4_path,
        planned_publish_at_local=planned_publish_at_local,
    )
    _write_json(upload_plan_path, asdict(upload_plan))
    manifest["upload_validation"] = upload_validation
    manifest["upload_plan"] = asdict(upload_plan)
    manifest["artifacts"]["upload_plan"] = str(upload_plan_path)
    manifest["status"] = upload_validation["status"]
    _write_json(manifest_path, manifest)

    _write_report(
        report_path,
        topic,
        script,
        gate,
        readability,
        quality,
        review,
        visual_assets,
        visual_quality,
        audio_asset,
        source_rows,
        mp4_path,
        storyboard_path,
        mobile_storyboard_path,
        manifest_path,
        render_scenes,
        signal_snapshot_path if has_signal_snapshot else None,
        selected_script_path,
        fact_pack_path,
        angle_brief_path,
        storyboard_brief_path,
        content_plan_path,
        visual_plan_path,
        tts_performance_plan_path,
        tts_plan_path,
        render_manifest_path,
        upload_plan_path,
        keyword_plan_path if has_keyword_plan else None,
        topic_plan_path if has_topic_plan else None,
        deep_research_report_path if has_deep_research_report else None,
        editorial_plan_path if editorial_plan is not None else None,
    )

    return RenderArtifacts(
        mp4=str(mp4_path),
        audio_path=audio_asset.path,
        audio_provider=audio_asset.provider,
        audio_status=audio_asset.status,
        storyboard=str(storyboard_path),
        mobile_preview_storyboard=str(mobile_storyboard_path),
        mobile_visual_checks=str(mobile_checks_path),
        asset_manifest=str(asset_manifest_path),
        fact_pack=str(fact_pack_path),
        risk_flags=str(risk_flags_path),
        source_card=str(source_card_path),
        reference_fit=str(reference_fit_path),
        angle_brief=str(angle_brief_path),
        storyboard_brief=str(storyboard_brief_path),
        signal_snapshot=str(signal_snapshot_path) if has_signal_snapshot else None,
        content_plan=str(content_plan_path),
        keyword_plan=str(keyword_plan_path) if has_keyword_plan else None,
        topic_pool=str(topic_pool_path) if has_topic_pool else None,
        topic_plan=str(topic_plan_path) if has_topic_plan else None,
        deep_research_report=str(deep_research_report_path) if has_deep_research_report else None,
        editorial_plan=str(editorial_plan_path) if editorial_plan is not None else None,
        selected_script=str(selected_script_path),
        visual_plan=str(visual_plan_path),
        tts_performance_plan=str(tts_performance_plan_path),
        tts_plan=str(tts_plan_path),
        render_manifest=str(render_manifest_path),
        upload_plan=str(upload_plan_path),
        report_html=str(report_path),
        manifest_json=str(manifest_path),
        render_textfit_report=str(render_textfit_report_path),
    )


def _generate_visual_assets(
    topic: TopicCandidate,
    scenes: list[Scene],
    assets_dir: Path,
    *,
    image_mode: str,
    real_image_limit: int,
) -> list[VisualAsset]:
    _load_env_files()
    assets_dir.mkdir(parents=True, exist_ok=True)
    assets: list[VisualAsset] = []
    briefs = build_visual_briefs(topic, scenes)
    real_count = 0
    unavailable: set[str] = set()
    for index, scene in enumerate(scenes):
        brief = briefs[index]
        prompt = _build_cinematic_prompt(scene, brief)
        out = assets_dir / f"scene_{scene.scene_id:02d}_cinematic.png"
        notes: list[str] = []
        provider = "local_pillow"
        status = "fallback"

        if privacy_policy.is_local_only():
            notes.append("local_only privacy mode: external image providers disabled")
        elif image_mode != "local" and real_count < real_image_limit:
            provider_chain = ["codex_cli", "gemini_api"] if image_mode == "auto" else [image_mode]
            for candidate in provider_chain:
                if candidate in unavailable:
                    notes.append(f"{candidate} skipped: unavailable earlier in this run")
                    continue
                ok, candidate_notes = _try_generate_visual(candidate, prompt, out)
                notes.extend(candidate_notes)
                if ok:
                    provider = candidate
                    status = "generated"
                    real_count += 1
                    break
                if _persistent_provider_failure(candidate_notes):
                    unavailable.add(candidate)

        if status != "generated":
            _write_local_cinematic_asset(out, scene, index, brief)
            notes.append("external image provider unavailable or skipped; local cinematic fallback rendered")

        if _valid_image(out) and _apply_visual_color_grade(out, brief):
            notes.append(f"role color grade applied: {brief.role}")

        assets.append(
            VisualAsset(
                scene_id=scene.scene_id,
                provider=provider,
                status=status,
                path=str(out),
                prompt=prompt,
                visual_brief=asdict(brief),
                visual_quality={},
                notes=notes,
            )
        )
    visual_quality = check_visual_quality(assets, scenes)
    assets = [
        replace(asset, visual_quality=next(
            (row for row in visual_quality.scene_scores if row.get("scene_id") == asset.scene_id),
            {},
        ))
        for asset in assets
    ]
    return assets


def _persistent_provider_failure(notes: list[str]) -> bool:
    text = " ".join(notes).lower()
    return any(
        marker in text
        for marker in [
            "skipped:",
            "not found",
            "openai_api_key unavailable",
            "organization must be verified",
            "403",
            "401",
        ]
    )


def _load_env_files() -> None:
    for path in [REPO_DIR / ".env.local", REPO_DIR / ".env"]:
        if not path.exists():
            continue
        for raw_line in path.read_text(encoding="utf-8", errors="ignore").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and value and not os.environ.get(key):
                os.environ[key] = value


def _env_value(*keys: str) -> str | None:
    for key in keys:
        value = os.environ.get(key)
        if not value:
            continue
        normalized = value.strip().strip('"').strip("'")
        if normalized.lower() in {"false", "none", "null", "0", "no"}:
            continue
        return normalized
    return None


def _env_bool(key: str, default: bool) -> bool:
    value = os.environ.get(key)
    if value is None:
        return default
    normalized = value.strip().strip('"').strip("'").lower()
    if normalized in {"1", "true", "yes", "y", "on"}:
        return True
    if normalized in {"0", "false", "no", "n", "off"}:
        return False
    return default


def _env_float_ratio(key: str, default: float) -> float:
    value = os.environ.get(key)
    if value is None or not value.strip():
        return default
    normalized = value.strip().strip('"').strip("'")
    is_percent = normalized.endswith("%")
    if is_percent:
        normalized = normalized[:-1]
    try:
        parsed = float(normalized)
    except ValueError:
        return default
    if is_percent or parsed > 1.0:
        parsed = parsed / 100.0
    return max(0.0, min(1.0, parsed))


def _env_float(key: str, default: float, *, min_value: float, max_value: float) -> float:
    value = os.environ.get(key)
    if value is None or not value.strip():
        return default
    normalized = value.strip().strip('"').strip("'")
    try:
        parsed = float(normalized)
    except ValueError:
        return default
    return max(min_value, min(max_value, parsed))


def _load_tts_aliases() -> dict[str, str]:
    path = PACKAGE_DIR / "account" / "ko_tts_pronunciation.json"
    if not path.exists():
        return {}
    data = _load_json(path)
    aliases = data.get("aliases", {})
    if not isinstance(aliases, dict):
        return {}
    return {str(key): str(value) for key, value in aliases.items() if str(key).strip() and str(value).strip()}


def _sino_under_10000(number: int) -> str:
    if number == 0:
        return SINO_DIGITS[0]
    remaining = number
    parts: list[str] = []
    for value, unit in TTS_SINO_UNITS:
        digit = remaining // value
        if digit:
            parts.append(("" if digit == 1 else SINO_DIGITS[digit]) + unit)
            remaining %= value
    if remaining:
        parts.append(SINO_DIGITS[remaining])
    return "".join(parts)


def _sino_number(number: int) -> str:
    if number == 0:
        return SINO_DIGITS[0]
    if number < 0:
        return TTS_NEGATIVE_PREFIX + _sino_number(abs(number))
    remaining = number
    parts: list[str] = []
    for value, unit in TTS_LARGE_UNITS:
        group = remaining // value
        if group:
            parts.append(_sino_under_10000(group) + unit)
            remaining %= value
    return "".join(parts)


def _native_number(number: int, *, attributive: bool = False) -> str:
    if number <= 0:
        return _sino_number(number)
    if number < 10:
        pair = NATIVE_ONES[number]
        return pair[1] if attributive else pair[0]
    if number in NATIVE_TENS:
        if attributive and number == 20:
            return TTS_NATIVE_TWENTY_ATTRIBUTIVE
        return NATIVE_TENS[number]
    if number < 100:
        tens = (number // 10) * 10
        ones = number % 10
        if tens in NATIVE_TENS and ones in NATIVE_ONES:
            return NATIVE_TENS[tens] + NATIVE_ONES[ones][1 if attributive else 0]
    return _sino_number(number)


def _read_counter(number: int, unit: str) -> str:
    if unit in NATIVE_COUNTER_UNITS:
        return f"{_native_number(number, attributive=True)} {unit}"
    if unit == "위" and number == 1:
        return "첫 번째"
    return f"{_sino_number(number)} {unit}"


def _read_decimal(raw: str) -> str:
    head, tail = raw.split(".", 1)
    return f"{_sino_number(int(head))} 점 " + " ".join(SINO_DIGITS[int(digit)] for digit in tail if digit.isdigit())


def _normalize_ko_numbers(text: str, changes: list[str]) -> str:
    def date_dot(match: re.Match[str]) -> str:
        year, month, day = (int(match.group(1)), int(match.group(2)), int(match.group(3)))
        changes.append("date")
        return f"{_sino_number(year)}년 {_sino_number(month)}월 {_sino_number(day)}일"

    text = re.sub(r"(?<!\d)(\d{4})[.\-/](\d{1,2})[.\-/](\d{1,2})(?!\d)", date_dot, text)

    def time_colon(match: re.Match[str]) -> str:
        hour, minute = (int(match.group(1)), int(match.group(2)))
        changes.append("time")
        hour_text = _native_number(hour, attributive=True) if 1 <= hour <= 12 else _sino_number(hour)
        if minute == 0:
            return f"{hour_text} 시"
        return f"{hour_text} 시 {_sino_number(minute)} 분"

    text = re.sub(r"(?<!\d)(\d{1,2}):(\d{2})(?!\d)", time_colon, text)

    def percent(match: re.Match[str]) -> str:
        raw = match.group(1)
        changes.append("percent")
        number = _read_decimal(raw) if "." in raw else _sino_number(int(raw))
        return f"{number} 퍼센트"

    text = re.sub(r"(\d+(?:\.\d+)?)\s*%", percent, text)

    counter_pattern = "|".join(sorted(map(re.escape, NATIVE_COUNTER_UNITS | SINO_COUNTER_UNITS), key=len, reverse=True))

    def range_with_unit(match: re.Match[str]) -> str:
        start, end, unit = int(match.group(1)), int(match.group(2)), match.group(3)
        changes.append("range")
        return f"{_read_counter(start, unit)}에서 {_read_counter(end, unit)}"

    text = re.sub(rf"(\d+)\s*[~\-–]\s*(\d+)\s*({counter_pattern})", range_with_unit, text)

    def number_with_unit(match: re.Match[str]) -> str:
        number, unit = int(match.group(1).replace(",", "")), match.group(2)
        changes.append(f"counter:{unit}")
        return _read_counter(number, unit)

    text = re.sub(rf"(\d[\d,]*)\s*({counter_pattern})", number_with_unit, text)

    def decimal(match: re.Match[str]) -> str:
        changes.append("decimal")
        return _read_decimal(match.group(0))

    text = re.sub(r"(?<![\d.])\d+\.\d+(?![\d.])", decimal, text)

    def plain_number(match: re.Match[str]) -> str:
        changes.append("number")
        return _sino_number(int(match.group(0).replace(",", "")))

    return re.sub(r"(?<![\d.])\d[\d,]*(?![\d.])", plain_number, text)


def _lint_ko_tts_text(text: str) -> tuple[list[str], dict[str, int | float]]:
    sentence_parts = [part.strip() for part in re.split(r"[.!?\n]+", text) if part.strip()]
    line_parts = [part.strip() for part in text.splitlines() if part.strip()]
    latin_terms = re.findall(r"[A-Za-z]{2,}", text)
    digits = re.findall(r"\d", text)
    risky_symbols = re.findall(r"[#@/%~]", text)
    long_sentences = [part for part in sentence_parts if len(part) > 46]
    warnings: list[str] = []
    if latin_terms:
        warnings.append("latin_terms_remaining:" + ",".join(sorted(set(latin_terms))[:8]))
    if digits:
        warnings.append(f"digits_remaining:{len(digits)}")
    if risky_symbols:
        warnings.append("risky_symbols_remaining:" + "".join(sorted(set(risky_symbols))))
    if long_sentences:
        warnings.append(f"long_sentence_count:{len(long_sentences)}")
    metrics = {
        "char_count": len(text),
        "line_count": len(line_parts),
        "max_line_chars": max((len(part) for part in line_parts), default=0),
        "max_sentence_chars": max((len(part) for part in sentence_parts), default=0),
        "latin_term_count": len(latin_terms),
        "digit_count": len(digits),
        "risky_symbol_count": len(risky_symbols),
        "long_sentence_count": len(long_sentences),
    }
    return warnings, metrics


def _soft_break_tts_lines(text: str, *, max_chars: int = 46) -> tuple[str, bool]:
    changed = False
    out_lines: list[str] = []
    split_markers = [", ", ". ", "? ", "! ", " 그리고 ", " 하지만 ", " 문제는 ", " 우리는 ", " 오늘은 "]
    for raw_line in text.splitlines():
        line = raw_line.strip()
        if len(line) <= max_chars:
            out_lines.append(line)
            continue
        remaining = line
        while len(remaining) > max_chars:
            split_at = -1
            for marker in split_markers:
                start = 0
                while True:
                    idx = remaining.find(marker, start)
                    if idx == -1:
                        break
                    candidate = idx + len(marker.rstrip())
                    if 22 <= candidate <= max_chars:
                        split_at = max(split_at, candidate)
                    start = idx + 1
            if split_at == -1:
                spaces = [idx for idx, char in enumerate(remaining[:max_chars]) if char == " " and idx >= 24]
                split_at = spaces[-1] if spaces else max_chars
            out_lines.append(remaining[:split_at].strip(" ,"))
            remaining = remaining[split_at:].strip(" ,")
            changed = True
        if remaining:
            out_lines.append(remaining)
    return "\n".join(line for line in out_lines if line), changed


def _preprocess_korean_tts(text: str) -> TTSPreprocessResult:
    changes: list[str] = []
    normalized = text
    aliases = _load_tts_aliases()
    for source, target in sorted(aliases.items(), key=lambda item: len(item[0]), reverse=True):
        pattern = re.compile(re.escape(source), re.IGNORECASE if source.isascii() else 0)
        normalized, count = pattern.subn(target, normalized)
        if count:
            changes.append(f"alias:{source}")

    normalized = re.sub(r"https?://\S+", TTS_URL_REPLACEMENT, normalized)
    normalized = re.sub(r"#([0-9A-Za-z가-힣_]+)", lambda match: f"{TTS_HASHTAG_PREFIX}{match.group(1)}", normalized)
    normalized = re.sub(r"@([0-9A-Za-z가-힣_]+)", lambda match: f"{match.group(1)}{TTS_MENTION_SUFFIX}", normalized)
    for source, target in TTS_SYMBOL_REPLACEMENTS.items():
        normalized = normalized.replace(source, target)
    normalized = _normalize_ko_numbers(normalized, changes)
    normalized = re.sub(r"[ \t]+", " ", normalized)
    normalized = re.sub(r"\s+\n", "\n", normalized)
    normalized = re.sub(r"\n{3,}", "\n\n", normalized).strip()
    normalized, soft_break_applied = _soft_break_tts_lines(normalized)
    if soft_break_applied:
        changes.append("soft_break")
    warnings, metrics = _lint_ko_tts_text(normalized)
    return TTSPreprocessResult(
        text=normalized,
        replacements=sorted(set(changes)),
        warnings=warnings,
        metrics=metrics,
    )


def _tts_text_for_korean_voice(text: str) -> str:
    return _preprocess_korean_tts(text).text


def _model_supports_style_settings(model_id: str) -> bool:
    return model_id in {"eleven_multilingual_v2", "eleven_multilingual_v1", "eleven_monolingual_v1"}


VISUAL_STRATEGY = _load_strategy_config("visual_strategy.json")
VISUAL_REALISM_PRINCIPLES = _config_list(VISUAL_STRATEGY, "realism_principles")
VISUAL_DRAMA_PRINCIPLES = _config_list(VISUAL_STRATEGY, "drama_principles")
VISUAL_PROMPTING = _config_dict(VISUAL_STRATEGY, "prompting")
VISUAL_HOT_PROMPTING = _config_dict(VISUAL_PROMPTING, "hot_visual")
VISUAL_CINEMATIC_PROMPTING = _config_dict(VISUAL_PROMPTING, "cinematic")
VISUAL_CODEX_CLI_PROMPTING = _config_dict(VISUAL_PROMPTING, "codex_cli")
VISUAL_QUALITY_MARKERS = _config_dict(VISUAL_STRATEGY, "quality_markers")
VISUAL_QUALITY_SCORING = _config_int_map(VISUAL_STRATEGY, "quality_scoring")
VISUAL_RELEVANCE_TERMS = _config_list(VISUAL_STRATEGY, "relevance_terms")
VISUAL_ISSUE_PROFILES: dict[str, dict[str, Any]] = _config_dict(VISUAL_STRATEGY, "issue_profiles")
VISUAL_ROLE_PROFILES: dict[str, dict[str, Any]] = _config_dict(VISUAL_STRATEGY, "role_profiles")
VISUAL_FALLBACK_ROLE_SEQUENCE = [
    str(role)
    for role in _config_list(VISUAL_STRATEGY, "fallback_role_sequence")
    if str(role) in VISUAL_ROLE_PROFILES
]
VISUAL_SAFETY_CONSTRAINTS = _config_list(VISUAL_STRATEGY, "safety_constraints")
VISUAL_DIEGETIC_TEXT_STRATEGY = _config_dict(VISUAL_STRATEGY, "diegetic_text")
VISUAL_DIEGETIC_TEXT_ENABLED = bool(VISUAL_DIEGETIC_TEXT_STRATEGY.get("enabled", False))
VISUAL_DIEGETIC_TEXT_MAX_CHARS = _strategy_int(VISUAL_DIEGETIC_TEXT_STRATEGY, "max_chars", 18)
VISUAL_DIEGETIC_TEXT_FALLBACK = str(VISUAL_DIEGETIC_TEXT_STRATEGY.get("fallback_text", "기준을 보자")).strip()
VISUAL_DIEGETIC_TEXT_SURFACES = _config_dict(VISUAL_DIEGETIC_TEXT_STRATEGY, "role_surfaces")
VISUAL_DIEGETIC_TEXT_DIRECTIVE_TEMPLATE = str(
    VISUAL_DIEGETIC_TEXT_STRATEGY.get("directive_template", "")
).strip()
VISUAL_TEXT_PROHIBITION_MARKERS = [
    str(marker).lower()
    for marker in VISUAL_DIEGETIC_TEXT_STRATEGY.get("text_prohibition_markers", [])
    if str(marker).strip()
]
VISUAL_DIEGETIC_TEXT_REPLACEMENT_CONSTRAINTS = [
    str(item)
    for item in VISUAL_DIEGETIC_TEXT_STRATEGY.get("replacement_safety_constraints", [])
    if str(item).strip()
]
VISUAL_ROLE_PALETTE_MAP = {
    str(role): str(palette) for role, palette in _config_dict(VISUAL_STRATEGY, "role_palette_map").items()
}
VISUAL_ROLE_COLOR_GRADES = _config_dict(VISUAL_STRATEGY, "role_color_grades")
VISUAL_ISSUE_DETECTION_TERMS = {
    str(issue_type): [str(term) for term in terms]
    for issue_type, terms in _config_dict(VISUAL_STRATEGY, "issue_detection_terms").items()
    if isinstance(terms, list)
}
VISUAL_ISSUE_DETECTION_PRIORITY = [
    str(issue_type)
    for issue_type in _config_list(VISUAL_STRATEGY, "issue_detection_priority")
    if str(issue_type) in VISUAL_ISSUE_PROFILES or str(issue_type) == "civic_fact_check"
]
VISUAL_ISSUE_REQUIRED_TERMS = {
    str(issue_type): [str(term) for term in terms if str(term).strip()]
    for issue_type, terms in _config_dict(VISUAL_STRATEGY, "issue_required_terms").items()
    if isinstance(terms, list)
}
VISUAL_DIEGETIC_TEXT_RENDER_ISSUES = {
    str(issue_type)
    for issue_type in _config_list(VISUAL_STRATEGY, "diegetic_text_render_issue_types")
    if str(issue_type) in VISUAL_ISSUE_PROFILES
}
VISUAL_ROLE_DETECTION_TERMS = {
    str(role): [str(term) for term in terms]
    for role, terms in _config_dict(VISUAL_STRATEGY, "role_detection_terms").items()
    if isinstance(terms, list)
}
VISUAL_ROLE_ISSUE_ANCHOR_OVERRIDES = {
    str(role): [str(anchor) for anchor in anchors]
    for role, anchors in _config_dict(VISUAL_STRATEGY, "role_issue_anchor_overrides").items()
    if isinstance(anchors, list)
}
VISUAL_ISSUE_ANCHOR_ROLES = {
    role for role in _config_list(VISUAL_STRATEGY, "issue_anchor_roles") if role in VISUAL_ROLE_PROFILES
}
VISUAL_ANCHOR_MERGE_LIMIT = _strategy_int(VISUAL_STRATEGY, "visual_anchor_merge_limit", 10)
VISUAL_ROLE_REPEAT_VARIANTS = {
    str(role): [variant for variant in variants if isinstance(variant, dict)]
    for role, variants in _config_dict(VISUAL_STRATEGY, "role_repeat_variants").items()
    if isinstance(variants, list)
}
VISUAL_TREATMENTS = {
    str(key): str(value) for key, value in _config_dict(VISUAL_STRATEGY, "visual_treatments").items()
}
VISUAL_TREATMENT_SEQUENCE = [
    treatment_id for treatment_id in _config_list(VISUAL_STRATEGY, "visual_treatment_sequence") if treatment_id in VISUAL_TREATMENTS
]
VISUAL_CONCRETE_SCENE_RULES = [
    rule for rule in VISUAL_STRATEGY.get("concrete_scene_rules", []) if isinstance(rule, dict)
]
VISUAL_DEFAULT_CONCRETE_SCENE = str(VISUAL_STRATEGY.get("default_concrete_scene", "")).strip()
VISUAL_TOPIC_DOMINANT_ISSUES = {
    str(issue_type)
    for issue_type in _config_list(VISUAL_STRATEGY, "topic_dominant_issue_types")
    if str(issue_type) in VISUAL_ISSUE_PROFILES
}
VISUAL_TOPIC_PRIORITY_ISSUES = {
    str(issue_type)
    for issue_type in _config_list(VISUAL_STRATEGY, "topic_priority_issue_types")
    if str(issue_type) in VISUAL_ISSUE_PROFILES
}
VISUAL_GENERIC_SCENE_ISSUES = {
    str(issue_type)
    for issue_type in _config_list(VISUAL_STRATEGY, "generic_scene_issue_types")
    if str(issue_type) in VISUAL_ISSUE_PROFILES or str(issue_type) == "civic_fact_check"
}
VISUAL_ACTION_BEATS_BY_ROLE = {
    str(role): [str(item) for item in beats if str(item).strip()]
    for role, beats in _config_dict(VISUAL_STRATEGY, "action_beats_by_role").items()
    if isinstance(beats, list)
}
VISUAL_MOTION_STRATEGY = _config_dict(VISUAL_STRATEGY, "motion_strategy")
VISUAL_ROLE_REALITY_BEATS = {
    str(role): str(beat) for role, beat in _config_dict(VISUAL_STRATEGY, "role_reality_beats").items()
}
VISUAL_ROLE_INTENSITY_BEATS = {
    str(role): str(beat) for role, beat in _config_dict(VISUAL_STRATEGY, "role_intensity_beats").items()
}
VISUAL_REPETITION_GUARD = str(VISUAL_STRATEGY.get("repetition_guard", "")).strip()
VISUAL_ROLE_SEPARATION = str(VISUAL_STRATEGY.get("role_separation", "")).strip()
VISUAL_PAPER_PROP_REGRESSION_TERMS = tuple(
    str(term).casefold()
    for term in _config_list(VISUAL_STRATEGY, "paper_prop_regression_terms")
    if str(term).strip()
)
VISUAL_SOURCE_CONTEXT_REPLACEMENTS = {
    str(source): str(target)
    for source, target in _config_dict(VISUAL_STRATEGY, "source_visual_replacements").items()
    if str(source).strip()
}
VISUAL_QUALITY_MINIMUMS = _config_int_map(VISUAL_STRATEGY, "quality_minimums")
CINEMATIC_SUBTITLE_RENDER_STYLE = "cinematic_subtitle"
CINEMATIC_SUBTITLE_PROMPT_DIRECTIVE = str(
    VISUAL_CINEMATIC_PROMPTING.get("subtitle_prompt_directive", "")
).strip()
CINEMATIC_SUBTITLE_FORBIDDEN_ANCHOR_TERMS = tuple(
    str(term).casefold()
    for term in VISUAL_CINEMATIC_PROMPTING.get("subtitle_forbidden_anchor_terms", [])
    if str(term).strip()
)
VISUAL_ISSUE_LOCATION_ROLES = {
    role for role in _config_list(VISUAL_STRATEGY, "issue_location_roles") if role in VISUAL_ROLE_PROFILES
}
VISUAL_DYNAMIC_TERM_STOPWORDS = {
    "오늘",
    "먼저",
    "기준",
    "확인",
    "제목",
    "기록",
    "책임",
    "문제",
    "질문",
    "보도",
    "쟁점",
    "사안",
    "핵심",
    "관련",
    "추진",
}


def _visual_issue_matches(text: str) -> list[tuple[str, int, int]]:
    rows: list[tuple[str, int, int]] = []
    priority = VISUAL_ISSUE_DETECTION_PRIORITY or list(VISUAL_ISSUE_DETECTION_TERMS)
    priority_index = {issue_type: index for index, issue_type in enumerate(priority)}
    for issue_type, terms in VISUAL_ISSUE_DETECTION_TERMS.items():
        matched = [term for term in terms if term and term in text]
        if not matched:
            continue
        required_terms = VISUAL_ISSUE_REQUIRED_TERMS.get(issue_type, [])
        if required_terms and not any(term in text for term in required_terms):
            continue
        rows.append((issue_type, len(matched), priority_index.get(issue_type, len(priority_index))))
    return rows


def _infer_visual_issue_type(text: str) -> str:
    matches = _visual_issue_matches(text)
    if not matches:
        return "civic_fact_check"
    return sorted(matches, key=lambda row: (-row[1], row[2], row[0]))[0][0]


def _select_visual_issue_type(topic_text: str, scene_text: str) -> str:
    topic_issue_type = _infer_visual_issue_type(topic_text)
    scene_issue_type = _infer_visual_issue_type(scene_text)
    if topic_issue_type in VISUAL_TOPIC_DOMINANT_ISSUES:
        return topic_issue_type
    if topic_issue_type in VISUAL_TOPIC_PRIORITY_ISSUES and scene_issue_type in VISUAL_GENERIC_SCENE_ISSUES:
        return topic_issue_type
    if scene_issue_type == "party_strategy" and topic_issue_type != "civic_fact_check":
        return topic_issue_type
    if scene_issue_type != "civic_fact_check":
        return scene_issue_type
    return topic_issue_type


def _infer_visual_role(scene: Scene, index: int, total: int) -> str:
    title_text = str(scene.title)
    text = f"{scene.title} {scene.on_screen_text} {scene.body}"
    if index == 0 or any(term in title_text for term in VISUAL_ROLE_DETECTION_TERMS.get("hook", [])):
        return "hook"
    for role in ["cta", "why_now", "evidence", "responsibility", "criteria", "verification"]:
        if any(term in title_text for term in VISUAL_ROLE_DETECTION_TERMS.get(role, [])):
            return role
    for role in ["cta", "why_now", "evidence", "criteria", "responsibility", "verification"]:
        if any(term in text for term in VISUAL_ROLE_DETECTION_TERMS.get(role, [])):
            return role
    if index == total - 1:
        return "cta"
    return "evidence"


def _extract_visual_terms(text: str) -> list[str]:
    configured_terms = [term for term in VISUAL_RELEVANCE_TERMS if term in text]
    dynamic_terms: list[str] = []
    for match in re.findall(r"[가-힣][가-힣A-Za-z0-9·]{1,}", text):
        term = match.strip("·")
        if len(term) < 2 or term in VISUAL_DYNAMIC_TERM_STOPWORDS:
            continue
        if term.endswith(("합니다", "했습니다", "입니다", "됩니다", "봅니다", "까요")):
            continue
        dynamic_terms.append(term)
    return list(dict.fromkeys([*configured_terms, *dynamic_terms]))[:12]


def _visual_location_for_role_issue(role: str, issue_type: str, role_profile: dict[str, Any], issue_profile: dict[str, Any]) -> str:
    role_location = str(role_profile.get("location") or "").strip()
    issue_location = str(issue_profile.get("location") or "").strip()
    if role in VISUAL_ISSUE_LOCATION_ROLES and issue_type != "civic_fact_check" and issue_location:
        if role_location and role_location != issue_location:
            return f"{role_location}, tied to {issue_location}"
        return issue_location
    return role_location or issue_location


def _visual_treatment_for_scene(role: str, index: int) -> tuple[str, str]:
    if not VISUAL_TREATMENT_SEQUENCE:
        return "", ""
    treatment_id = VISUAL_TREATMENT_SEQUENCE[index % len(VISUAL_TREATMENT_SEQUENCE)]
    if role == "cta":
        treatment_id = "comment_choice_scene" if "comment_choice_scene" in VISUAL_TREATMENTS else treatment_id
    elif role == "responsibility" and "accountability_stage" in VISUAL_TREATMENTS:
        treatment_id = "accountability_stage"
    elif role in {"evidence", "criteria", "verification"} and "evidence_action" in VISUAL_TREATMENTS:
        treatment_id = "evidence_action" if index % 2 == 0 else treatment_id
    return treatment_id, VISUAL_TREATMENTS.get(treatment_id, "")


def _visual_action_beat_for_role(role: str, index: int) -> str:
    beats = VISUAL_ACTION_BEATS_BY_ROLE.get(role, [])
    if not beats:
        return ""
    return beats[index % len(beats)]


def _diegetic_text_for_scene(scene: Scene) -> str:
    if not VISUAL_DIEGETIC_TEXT_ENABLED:
        return ""
    source = scene.on_screen_text or scene.title or scene.body
    text = _clean_card_text(source)
    text = text.replace("...", " ").replace("…", " ")
    text = re.sub(r"[^0-9A-Za-z\uac00-\ud7a3\s?!.,:%-]", "", text)
    text = _clean_card_text(text).strip(" .,")
    if not text:
        text = VISUAL_DIEGETIC_TEXT_FALLBACK
    max_chars = max(6, VISUAL_DIEGETIC_TEXT_MAX_CHARS)
    if len(text) > max_chars:
        text = _compact_card_text(text, max_chars, keep_question="?" in text)
        text = text.replace("...", "").replace("…", "").strip(" .,")
    return text or VISUAL_DIEGETIC_TEXT_FALLBACK


def _diegetic_text_directive_for_scene(scene: Scene, role: str) -> str:
    text = _diegetic_text_for_scene(scene)
    if not text:
        return "No readable in-image text."
    surface = str(
        VISUAL_DIEGETIC_TEXT_SURFACES.get(role)
        or VISUAL_DIEGETIC_TEXT_SURFACES.get("default")
        or "a physical prop inside the scene"
    )
    template = VISUAL_DIEGETIC_TEXT_DIRECTIVE_TEMPLATE or (
        'Controlled in-image text: include exactly one physical text surface, {surface}, '
        'with the exact Korean text "{text}". Do not invent any other readable text.'
    )
    return _format_prompt_template(template, {"text": text, "surface": surface, "role": role})


def _visual_safety_constraints_for_scene(diegetic_text: str) -> list[str]:
    if not diegetic_text:
        return VISUAL_SAFETY_CONSTRAINTS
    filtered = [
        constraint
        for constraint in VISUAL_SAFETY_CONSTRAINTS
        if not any(marker in constraint.lower() for marker in VISUAL_TEXT_PROHIBITION_MARKERS)
    ]
    return [*filtered, *VISUAL_DIEGETIC_TEXT_REPLACEMENT_CONSTRAINTS]


def _visual_role_shot_contract(role: str) -> list[str]:
    base = [
        "show a believable real-world public-interest location with spatial depth",
        "show one visible human action or reaction in progress, using anonymous non-identifiable adults only",
        "use one dominant foreground object tied to the issue, not a generic decoration",
        "reserve a clean subtitle/overlay lane without turning the frame into an empty background",
    ]
    by_role = {
        "hook": [
            "make the first-second visual question readable before any overlay text",
            "use a doorway, press line, monitor wall, or large foreground object to create immediate tension",
        ],
        "why_now": [
            "show a current-signal moment such as a newsroom monitor, phone recorder glow, or late-night briefing reaction",
            "make the scene feel like it is happening now, not like archival still-life",
        ],
        "evidence": [
            "show cropped hands moving or separating verification objects instead of a static document pile",
            "keep papers, screens, and labels unreadable unless a controlled caption is explicitly requested",
        ],
        "criteria": [
            "show three physically separated decision zones in the room through light, object placement, or blocking",
            "make one object visibly move from one judgment zone to another",
        ],
        "responsibility": [
            "show an accountability room, public counter, or meeting space with anonymous adults reacting",
            "include a body-language consequence such as someone stepping back, turning away, or pausing at a question",
        ],
        "verification": [
            "show one unresolved item being stopped or separated before it reaches the confirmed side",
            "make uncertainty visible through distance, glass, rain, shadow, or a held-back object",
        ],
        "cta": [
            "show a video editor timeline and divided reaction wall, not paper comment cards",
            "make viewer participation visible as heat zones, timeline choices, or split audience reactions",
        ],
    }
    return [*base, *by_role.get(role, [])]


def _visual_forbidden_dominant_elements(render_style: str) -> list[str]:
    common = [
        "handheld paper headline card",
        "placard or protest-sign composition",
        "poster, sticky note, memo, or source-card image as the main subject",
        "large blank white board, blank paper panel, or blank card wall as the dominant subject",
        "people holding blank boards, blank cards, paper panels, or placards toward the camera",
        "blank board, paper, or card covering the center of the composition",
        "fake app screenshot or fake broadcast lower-third as the main image",
        "empty office, empty classroom, or passive desk still-life",
        "generic file pile, generic microphone pile, or generic corridor repeated across scenes",
        "real politician likeness, party logo, campaign material, official seal, watermark, or uncontrolled readable text",
    ]
    if render_style == CINEMATIC_SUBTITLE_RENDER_STYLE:
        return [*common, "any readable in-image text because captions are rendered later"]
    return common


def _visual_scene_uniqueness_key(
    *,
    role: str,
    issue_type: str,
    treatment_id: str,
    location: str,
    camera: str,
    palette: str,
) -> str:
    location_token = _visual_uniqueness_token(location, 56)
    camera_token = _visual_uniqueness_token(camera, 46)
    palette_token = _visual_uniqueness_token(palette, 34)
    return " | ".join([role, issue_type, treatment_id, location_token, camera_token, palette_token])


def _visual_uniqueness_token(value: str, max_chars: int) -> str:
    token = re.sub(r"\s+", " ", value).strip()
    if len(token) <= max_chars:
        return token
    digest = hashlib.sha1(token.encode("utf-8")).hexdigest()[:8]
    head_len = max(8, max_chars - len(digest) - 2)
    return f"{token[:head_len]}..{digest}"


def _normalize_visual_render_style(value: Any) -> str:
    style = str(value or "").strip().casefold().replace("-", "_")
    return CINEMATIC_SUBTITLE_RENDER_STYLE if style == CINEMATIC_SUBTITLE_RENDER_STYLE else ""


def _default_visual_render_style() -> str:
    return _normalize_visual_render_style(RENDERING_STRATEGY.get("default_render_style", ""))


def _cinematic_subtitle_anchors(anchors: list[str]) -> list[str]:
    filtered = [
        anchor
        for anchor in anchors
        if not any(term in anchor.casefold() for term in CINEMATIC_SUBTITLE_FORBIDDEN_ANCHOR_TERMS)
    ]
    return filtered or [
        "anonymous adult reaction caught mid-action",
        "unbranded microphones or recorder in foreground",
        "real location depth with practical light and imperfect surfaces",
    ]


def _visual_concrete_scene_for_topic(
    topic: TopicCandidate,
    scene: Scene,
    role: str,
    action_beat: str,
    issue_type: str = "",
) -> str:
    explicit_visual = _clean_card_text(scene.visual)
    explicit_prefix = "reference_scene:"
    explicit_reference_scene = ""
    if explicit_visual.startswith(explicit_prefix):
        explicit_reference_scene = explicit_visual[len(explicit_prefix) :].strip()

    raw = _clean_card_text(" ".join([topic.title, topic.angle, scene.title, scene.body, scene.on_screen_text]))
    values = {
        "topic_title": topic.title,
        "card_text": scene.on_screen_text,
        "role": role,
        "action_beat": action_beat,
    }
    for rule in VISUAL_CONCRETE_SCENE_RULES:
        rule_issue_type = str(rule.get("issue_type") or "").strip()
        if rule_issue_type and issue_type and rule_issue_type != issue_type:
            continue
        terms = [str(term) for term in rule.get("if_text_contains_any", []) if str(term).strip()]
        if terms and not any(term in raw for term in terms):
            continue
        scenes_by_scene_id = rule.get("scenes_by_scene_id", {})
        if isinstance(scenes_by_scene_id, dict):
            scene_id = str(scene.scene_id)
            template = str(scenes_by_scene_id.get(scene_id) or scenes_by_scene_id.get(f"scene_{scene_id}") or "").strip()
            if template:
                return _format_prompt_template(template, values)
        scenes_by_role = rule.get("scenes_by_role", {})
        if isinstance(scenes_by_role, dict):
            template = str(scenes_by_role.get(role) or scenes_by_role.get("default") or "").strip()
            if template:
                return _format_prompt_template(template, values)
        template = str(rule.get("scene", "")).strip()
        if template:
            return _format_prompt_template(template, values)
    if explicit_reference_scene:
        return explicit_reference_scene
    return _format_prompt_template(VISUAL_DEFAULT_CONCRETE_SCENE, values) if VISUAL_DEFAULT_CONCRETE_SCENE else scene.visual


def _presidential_legacy_visual_override(scene_id: int) -> dict[str, Any]:
    overrides: dict[int, dict[str, Any]] = {
        1: {
            "location": "vertical ranking studio with a black glass light table and a tall blank five-slot ranking wall",
            "camera": "low-angle wide shot from the edge of the ranking board, strong depth and diagonal composition",
            "palette": "black glass, white ranking blocks, sharp red progress accent",
            "action_beat": "an anonymous hand places the first blank rank block while the ranking wall dominates the frame",
            "anchors": ["giant blank TOP5 ranking wall", "five physical blank rank blocks", "red progress accent"],
            "treatment_id": "satirical_tableau",
        },
        2: {
            "location": "bright AI evaluation lab with three oversized analogue scoring dials and a public-policy screen glow",
            "camera": "clean side-wide shot across three dials, no tabletop pile, visible human scale",
            "palette": "white lab light, pale cyan screen glow, dark navy shadows",
            "action_beat": "an analyst points to three separate dials instead of papers",
            "anchors": ["three large scoring dials", "transparent divider glass", "single pointing hand"],
            "treatment_id": "aino_character_scene",
        },
        3: {
            "location": "large civic history split set with a candlelit square on one side and industrial machinery on the other",
            "camera": "wide split-stage composition, viewers seen from behind, no desk and no paper stack",
            "palette": "warm candle amber against steel blue industrial light",
            "action_beat": "two viewer groups turn toward opposite historical scenes at the same moment",
            "anchors": ["candlelit civic crowd monitor", "industrial machine silhouette", "two reacting viewer groups"],
            "treatment_id": "evidence_action",
        },
        4: {
            "location": "quiet peace-and-democracy archive room with a medal case, diplomatic envelopes, and tall archive shelves",
            "camera": "museum-style side close-up with archive shelves receding into the background",
            "palette": "deep archive green, warm gold spotlight, cream paper highlights",
            "action_beat": "gloved hands open a blank archive tray under a focused spotlight",
            "anchors": ["blank medal case", "diplomatic envelopes", "archive gloves"],
            "treatment_id": "accountability_stage",
        },
        5: {
            "location": "cool-toned first-year administration situation room with livelihood charts and reform folders moving fast",
            "camera": "over-the-shoulder newsroom command shot with several screens and motion blur, not a close desk still",
            "palette": "cold cyan screens, graphite table, small red urgency light",
            "action_beat": "analysts move reform folders across a live situation table",
            "anchors": ["unreadable situation-room screens", "livelihood chart shapes", "moving reform folders"],
            "treatment_id": "evidence_action",
        },
        6: {
            "location": "rainy citizen-politics memory square with an open microphone and anonymous citizens facing a blank forum wall",
            "camera": "wide backlit exterior shot through rain reflection, strong open space and no document table",
            "palette": "wet asphalt blue, warm candle reflections, soft amber stage light",
            "action_beat": "an anonymous citizen steps toward an open microphone in the rain",
            "anchors": ["open civic microphone", "rain reflections", "citizens seen from behind"],
            "treatment_id": "evidence_action",
        },
        7: {
            "location": "vertical comment-battle editing booth with two opposing viewer groups and a giant blank ranking wall",
            "camera": "over-the-shoulder shot from the fictional AiNo editor toward the crowd-divided ranking wall",
            "palette": "amber booth light, red debate accent, dark crowd silhouettes",
            "action_beat": "the editor hovers over two blank TOP2 choice cards as both sides react",
            "anchors": ["giant vertical ranking wall", "two opposing viewer groups", "two blank TOP2 choice cards"],
            "treatment_id": "comment_choice_scene",
        },
    }
    return overrides.get(scene_id, {})


VISUAL_OVERRIDE_PREFIX = "aino_visual_override_json:"


def _parse_scene_visual_override(scene: Scene) -> dict[str, Any]:
    visual = str(scene.visual or "").strip()
    marker_index = visual.find(VISUAL_OVERRIDE_PREFIX)
    if marker_index < 0:
        return {}
    payload = visual[marker_index + len(VISUAL_OVERRIDE_PREFIX) :].strip()
    with contextlib.suppress(Exception):
        data = json.loads(payload)
        if isinstance(data, dict):
            return data
    return {}


def _visual_override_scene_text(scene: Scene, override: dict[str, Any]) -> str:
    for key in ("concrete_scene", "prompt", "scene"):
        value = str(override.get(key) or "").strip()
        if value:
            return value
    visual = str(scene.visual or "").strip()
    marker_index = visual.find(VISUAL_OVERRIDE_PREFIX)
    if marker_index >= 0:
        return visual[:marker_index].strip()
    return visual


def _editorial_os_scene_visual_override(scene: Scene) -> dict[str, Any]:
    return _parse_scene_visual_override(scene)


def _build_visual_brief(topic: TopicCandidate, scene: Scene, index: int, total: int) -> VisualBrief:
    topic_text = f"{topic.title} {topic.angle}"
    scene_text = f"{scene.title} {scene.on_screen_text} {scene.body} {scene.visual}"
    combined = f"{topic_text} {scene_text}"
    issue_type = _select_visual_issue_type(topic_text, scene_text)
    role = _infer_visual_role(scene, index, total)
    issue_profile = VISUAL_ISSUE_PROFILES[issue_type]
    role_profile = VISUAL_ROLE_PROFILES[role]
    relevance_terms = _extract_visual_terms(combined)
    role_anchor_override = VISUAL_ROLE_ISSUE_ANCHOR_OVERRIDES.get(role, [])
    issue_anchors = list(issue_profile["anchors"]) if role in VISUAL_ISSUE_ANCHOR_ROLES else []
    anchors = list(dict.fromkeys([*issue_anchors, *role_profile["anchors"], *role_anchor_override]))[:VISUAL_ANCHOR_MERGE_LIMIT]
    location = _visual_location_for_role_issue(role, issue_type, role_profile, issue_profile)
    camera = str(role_profile["camera"])
    emotion = str(issue_profile["emotion"])
    palette = str(role_profile.get("palette") or issue_profile["palette"])
    treatment_id, visual_treatment = _visual_treatment_for_scene(role, index)
    action_beat = _visual_action_beat_for_role(role, index)
    concrete_scene = _visual_concrete_scene_for_topic(topic, scene, role, action_beat, issue_type)
    presidential_override = (
        _presidential_legacy_visual_override(scene.scene_id)
        if issue_type == "presidential_legacy"
        else {}
    )
    if presidential_override:
        location = str(presidential_override.get("location") or location)
        camera = str(presidential_override.get("camera") or camera)
        palette = str(presidential_override.get("palette") or palette)
        action_beat = str(presidential_override.get("action_beat") or action_beat)
        override_anchors = [
            str(item)
            for item in presidential_override.get("anchors", [])
            if str(item).strip()
        ]
        if override_anchors:
            anchors = override_anchors[:VISUAL_ANCHOR_MERGE_LIMIT]
        override_treatment_id = str(presidential_override.get("treatment_id") or "").strip()
        if override_treatment_id in VISUAL_TREATMENTS:
            treatment_id = override_treatment_id
            visual_treatment = VISUAL_TREATMENTS[override_treatment_id]
    editorial_override = _editorial_os_scene_visual_override(scene)
    default_render_style = "" if issue_type in VISUAL_DIEGETIC_TEXT_RENDER_ISSUES else _default_visual_render_style()
    render_style = _normalize_visual_render_style(
        editorial_override.get("render_style") if editorial_override and "render_style" in editorial_override else default_render_style
    )
    if editorial_override:
        location = str(editorial_override.get("location") or location)
        camera = str(editorial_override.get("camera") or camera)
        palette = str(editorial_override.get("palette") or palette)
        treatment_id = str(editorial_override.get("treatment_id") or treatment_id)
        override_scene_text = _visual_override_scene_text(scene, editorial_override)
        visual_treatment = (
            f"scene-specific Editorial OS v2 cinematic treatment: {treatment_id}; "
            f"use the source visual prompt literally: {override_scene_text}"
        )
        action_beat = str(editorial_override.get("action_beat") or action_beat)
        concrete_scene = override_scene_text or concrete_scene
        override_anchors = [
            str(item)
            for item in editorial_override.get("anchors", [])
            if str(item).strip()
        ]
        if override_anchors:
            anchors = override_anchors[:VISUAL_ANCHOR_MERGE_LIMIT]
    if render_style == CINEMATIC_SUBTITLE_RENDER_STYLE:
        anchors = _cinematic_subtitle_anchors(anchors)
        visual_treatment = (
            f"{visual_treatment}; cinematic subtitle render style: real situational scene first, "
            "no paper-card headline as the main subject, leave a clean lower-third lane for rendered captions"
        )
        diegetic_text = ""
        diegetic_text_directive = CINEMATIC_SUBTITLE_PROMPT_DIRECTIVE
    else:
        diegetic_text = _diegetic_text_for_scene(scene)
        diegetic_text_directive = _diegetic_text_directive_for_scene(scene, role)
    safety_constraints = _visual_safety_constraints_for_scene(diegetic_text)
    shot_contract = _visual_role_shot_contract(role)
    forbidden_dominant_elements = _visual_forbidden_dominant_elements(render_style)
    scene_uniqueness_key = _visual_scene_uniqueness_key(
        role=role,
        issue_type=issue_type,
        treatment_id=treatment_id,
        location=location,
        camera=camera,
        palette=palette,
    )
    intent_suffix = str(VISUAL_PROMPTING.get("visual_intent_suffix", "")).strip()
    intent = (
        f"{role_profile['intent']}; translate the card '{scene.on_screen_text}' and topic '{topic.title}' "
        f"{intent_suffix}"
    )
    return VisualBrief(
        scene_id=scene.scene_id,
        role=role,
        issue_type=issue_type,
        visual_intent=intent,
        concrete_scene=concrete_scene,
        visual_anchor=anchors,
        location=location,
        camera=camera,
        emotion=emotion,
        palette=palette,
        treatment_id=treatment_id,
        visual_treatment=visual_treatment,
        action_beat=action_beat,
        relevance_terms=relevance_terms,
        diversity_tags=[issue_type, role, treatment_id, location, camera.split(",", 1)[0]],
        safety_constraints=safety_constraints,
        shot_contract=shot_contract,
        forbidden_dominant_elements=forbidden_dominant_elements,
        scene_uniqueness_key=scene_uniqueness_key,
        diegetic_text=diegetic_text,
        diegetic_text_directive=diegetic_text_directive,
        render_style=render_style,
    )


def _apply_visual_repeat_variant(brief: VisualBrief, repeat_index: int) -> VisualBrief:
    if repeat_index <= 0:
        return brief
    variants = VISUAL_ROLE_REPEAT_VARIANTS.get(brief.role, [])
    if not variants:
        return brief
    variant = variants[(repeat_index - 1) % len(variants)]
    anchors = [str(item) for item in variant.get("anchors", []) if str(item).strip()]
    location_suffix = str(variant.get("location_suffix", "")).strip()
    camera_suffix = str(variant.get("camera_suffix", "")).strip()
    palette_suffix = str(variant.get("palette_suffix", "")).strip()
    concrete_scene_override = str(variant.get("concrete_scene", "")).strip()
    concrete_scene_suffix = str(variant.get("concrete_scene_suffix", "")).strip()
    action_suffix = str(variant.get("action_suffix", "")).strip()
    treatment_id = str(variant.get("treatment_id", "")).strip()
    updated_location = f"{brief.location}; repeat-variant {repeat_index}: {location_suffix}" if location_suffix else brief.location
    updated_camera = f"{brief.camera}; repeat-variant {repeat_index}: {camera_suffix}" if camera_suffix else brief.camera
    updated_palette = f"{brief.palette}; repeat-variant {repeat_index}: {palette_suffix}" if palette_suffix else brief.palette
    updated_concrete_scene = (
        concrete_scene_override
        or (f"{brief.concrete_scene}; repeat-variant {repeat_index}: {concrete_scene_suffix}" if concrete_scene_suffix else brief.concrete_scene)
    )
    updated_treatment_id = treatment_id if treatment_id in VISUAL_TREATMENTS else brief.treatment_id
    return replace(
        brief,
        visual_anchor=list(dict.fromkeys([*anchors, *brief.visual_anchor]))[:8],
        location=updated_location,
        camera=updated_camera,
        palette=updated_palette,
        treatment_id=updated_treatment_id,
        visual_treatment=VISUAL_TREATMENTS[updated_treatment_id] if updated_treatment_id in VISUAL_TREATMENTS else brief.visual_treatment,
        action_beat=f"{brief.action_beat}; repeat-variant action: {action_suffix}" if action_suffix else brief.action_beat,
        concrete_scene=updated_concrete_scene,
        diversity_tags=[*brief.diversity_tags, f"{brief.role}_repeat_{repeat_index}"],
        scene_uniqueness_key=_visual_scene_uniqueness_key(
            role=brief.role,
            issue_type=brief.issue_type,
            treatment_id=updated_treatment_id,
            location=updated_location,
            camera=updated_camera,
            palette=updated_palette,
        ),
    )


def build_visual_briefs(topic: TopicCandidate, scenes: list[Scene]) -> list[VisualBrief]:
    briefs: list[VisualBrief] = []
    seen_by_role: dict[str, int] = {}
    for index, scene in enumerate(scenes):
        brief = _build_visual_brief(topic, scene, index, len(scenes))
        repeat_index = seen_by_role.get(brief.role, 0)
        briefs.append(_apply_visual_repeat_variant(brief, repeat_index))
        seen_by_role[brief.role] = repeat_index + 1
    return briefs


def _planning_text_value(section: dict[str, Any], key: str, fallback: str) -> str:
    value = section.get(key, fallback)
    return str(value).strip() or fallback


def _planning_list_value(key: str) -> list[str]:
    value = PLANNING_STRATEGY.get(key, [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _content_plan_trend_clusters(topic: TopicCandidate, topic_discovery: dict[str, Any] | None) -> list[dict[str, Any]]:
    discovered = (topic_discovery or {}).get("selected_trend_clusters")
    if isinstance(discovered, list) and discovered:
        return [row for row in discovered if isinstance(row, dict)]
    return _matched_trend_clusters(f"{topic.title} {topic.angle}")


def _topic_selection_rationale(
    topic: TopicCandidate,
    topic_discovery: dict[str, Any] | None,
    clusters: list[dict[str, Any]],
) -> str:
    selected = (topic_discovery or {}).get("selected")
    if isinstance(selected, dict):
        heat_score = str(selected.get("score", "n/a"))
        publisher = str(selected.get("publisher", "unknown"))
    else:
        heat_score = "static"
        publisher = "static reference"
    cluster_labels = ", ".join(str(row.get("label") or row.get("cluster_id")) for row in clusters) or "none"
    return _format_prompt_template(
        str(PLANNING_STRATEGY.get("topic_selection_template", "")),
        {
            "heat_score": heat_score,
            "clusters": cluster_labels,
            "publisher": publisher,
            "topic_title": topic.title,
        },
    )


def build_content_plan(
    topic: TopicCandidate,
    script: ScriptPackage,
    sources: dict[str, Source],
    format_plan: ContentFormatPlan,
    *,
    topic_discovery: dict[str, Any] | None = None,
    visual_assets: list[VisualAsset] | None = None,
) -> ContentPlan:
    generated_briefs = {brief.scene_id: asdict(brief) for brief in build_visual_briefs(topic, script.scenes)}
    asset_briefs = {
        asset.scene_id: asset.visual_brief
        for asset in (visual_assets or [])
        if isinstance(asset.visual_brief, dict) and asset.visual_brief
    }
    clusters = _content_plan_trend_clusters(topic, topic_discovery)
    narrative_arc = [
        str(item)
        for item in PLANNING_NARRATIVE_ARCS.get(format_plan.format_id, [])
        if str(item).strip()
    ]
    scene_plans: list[ContentScenePlan] = []
    for index, scene in enumerate(script.scenes):
        brief = {**generated_briefs.get(scene.scene_id, {}), **asset_briefs.get(scene.scene_id, {})}
        role = str(brief.get("role") or "evidence")
        raw_anchors = brief.get("visual_anchor", [])
        raw_safety = brief.get("safety_constraints", [])
        anchors = [str(item) for item in raw_anchors if str(item).strip()] if isinstance(raw_anchors, list) else []
        safety = [str(item) for item in raw_safety if str(item).strip()] if isinstance(raw_safety, list) else []
        diegetic_text = str(brief.get("diegetic_text") or "")
        diegetic_text_directive = str(brief.get("diegetic_text_directive") or "")
        image_need = _format_prompt_template(
            str(PLANNING_STRATEGY.get("image_need_template", "")),
            {
                "location": brief.get("location", ""),
                "anchors": ", ".join(anchors[:5]),
                "camera": brief.get("camera", ""),
                "visual_intent": brief.get("visual_intent", ""),
                "role": role,
            },
        )
        scene_plans.append(
            ContentScenePlan(
                scene_id=scene.scene_id,
                script_role=scene.title,
                narrative_step=narrative_arc[index] if index < len(narrative_arc) else scene.title,
                viewer_question=_planning_text_value(PLANNING_ROLE_QUESTIONS, role, "이 장면에서 무엇을 확인해야 하는가?"),
                on_screen_text=scene.on_screen_text,
                narration_goal=scene.body,
                evidence_need=_planning_text_value(PLANNING_ROLE_EVIDENCE_NEEDS, role, "공개 출처와 시각적 근거"),
                image_need=image_need,
                visual_role=role,
                issue_type=str(brief.get("issue_type") or ""),
                location=str(brief.get("location") or ""),
                camera=str(brief.get("camera") or ""),
                required_anchors=anchors,
                avoid=safety,
                diegetic_text=diegetic_text,
                diegetic_text_directive=diegetic_text_directive,
                source_ids=[source_id for source_id in script.sources if source_id in sources],
            )
        )
    key_question = (
        f"{script.scenes[0].on_screen_text} - 무엇이 확인됐고 무엇이 남았나?"
        if script.scenes
        else f"{topic.title} - 무엇을 확인해야 하나?"
    )
    return ContentPlan(
        version=str(PLANNING_STRATEGY.get("version", "script_first_v1")),
        topic_title=topic.title,
        format_id=format_plan.format_id,
        topic_selection_rationale=_topic_selection_rationale(topic, topic_discovery, clusters),
        editorial_frame=str(PLANNING_STRATEGY.get("editorial_frame", "")),
        key_question=key_question,
        trend_clusters=clusters,
        narrative_arc=narrative_arc,
        source_requirements=_planning_list_value("source_requirements"),
        risk_controls=_planning_list_value("risk_controls"),
        image_plan=scene_plans,
    )


def _visual_scene_score(asset: VisualAsset) -> dict[str, Any]:
    brief = asset.visual_brief or {}
    terms = brief.get("relevance_terms") if isinstance(brief.get("relevance_terms"), list) else []
    anchors = brief.get("visual_anchor") if isinstance(brief.get("visual_anchor"), list) else []
    issue_type = str(brief.get("issue_type") or "")
    role = str(brief.get("role") or "")
    location = str(brief.get("location") or "")
    palette = str(brief.get("palette") or "")
    prompt = asset.prompt
    score = 44
    score += min(20, len(terms) * 5)
    score += min(24, len(anchors) * 4)
    score += 12 if issue_type and issue_type != "civic_fact_check" else 5
    score += 8 if role else 0
    score += 5 if location else 0
    score += 4 if palette else 0
    score += 7 if "not a generic" in prompt.lower() or "generic office" in prompt.lower() else 0
    metaphor_score = 40
    metaphor_score += min(24, len(anchors) * 4)
    metaphor_score += 12 if issue_type and issue_type != "civic_fact_check" else 4
    metaphor_score += 10 if role in {"hook", "criteria", "responsibility", "verification"} else 6
    metaphor_score += 10 if _contains_any_marker(prompt, _config_nested_list(VISUAL_STRATEGY, "quality_markers", "metaphor_issue_specific_any")) else 0
    metaphor_score += 10 if _contains_any_marker(prompt, _config_nested_list(VISUAL_STRATEGY, "quality_markers", "metaphor_foreground_any")) else 0
    metaphor_score += 8 if _contains_any_marker(prompt, _config_nested_list(VISUAL_STRATEGY, "quality_markers", "metaphor_intensity_any")) else 0
    metaphor_score += 10 if role == "cta" and "comment cards" in prompt else 0
    metaphor_score += 6 if location and palette else 0
    return {
        "scene_id": asset.scene_id,
        "score": _clamp_score(score),
        "visual_metaphor_score": _clamp_score(metaphor_score),
        "issue_type": issue_type,
        "role": role,
        "relevance_terms": terms,
        "anchors": anchors,
    }


def _image_average_hash(path: str, *, size: int = 16) -> list[int] | None:
    image_path = Path(path)
    if not image_path.exists() or not image_path.is_file():
        return None
    try:
        with Image.open(image_path) as image:
            gray = image.convert("L").resize((size, size), Image.Resampling.BILINEAR)
            pixels = np.asarray(gray, dtype=np.float32)
    except Exception:
        return None
    mean = float(pixels.mean())
    return [1 if value >= mean else 0 for value in pixels.flatten()]


def _image_color_signature(path: str, *, bins: int = 8) -> list[float] | None:
    image_path = Path(path)
    if not image_path.exists() or not image_path.is_file():
        return None
    try:
        with Image.open(image_path) as image:
            small = image.convert("RGB").resize((96, 96), Image.Resampling.BILINEAR)
            arr = np.asarray(small, dtype=np.float32)
    except Exception:
        return None
    hist_parts: list[np.ndarray] = []
    for channel in range(3):
        hist, _ = np.histogram(arr[:, :, channel], bins=bins, range=(0, 256), density=False)
        hist_parts.append(hist.astype(np.float32))
    hist = np.concatenate(hist_parts)
    total = float(hist.sum())
    if total <= 0:
        return None
    return (hist / total).tolist()


def _image_basic_stats(path: str) -> dict[str, float | list[float]] | None:
    image_path = Path(path)
    if not image_path.exists() or not image_path.is_file():
        return None
    try:
        with Image.open(image_path) as image:
            small = image.convert("RGB").resize((96, 96), Image.Resampling.BILINEAR)
            arr = np.asarray(small, dtype=np.float32)
    except Exception:
        return None
    rgb_mean_array = arr.reshape(-1, 3).mean(axis=0)
    brightness = float((arr[:, :, 0] * 0.2126 + arr[:, :, 1] * 0.7152 + arr[:, :, 2] * 0.0722).mean())
    max_channel = arr.max(axis=2)
    min_channel = arr.min(axis=2)
    saturation = float((max_channel - min_channel).mean())
    return {
        "brightness": brightness,
        "saturation": saturation,
        "rgb_mean": [float(value) for value in rgb_mean_array],
    }


def _cosine_similarity(a: list[float], b: list[float]) -> float:
    va = np.asarray(a, dtype=np.float32)
    vb = np.asarray(b, dtype=np.float32)
    denom = float(np.linalg.norm(va) * np.linalg.norm(vb))
    if denom <= 0:
        return 0.0
    return float(np.dot(va, vb) / denom)


def _actual_visual_similarity(visual_assets: list[VisualAsset]) -> tuple[int, list[dict[str, Any]]]:
    signatures: list[tuple[int, list[int], list[float]]] = []
    for asset in visual_assets:
        if not asset.path:
            continue
        image_hash = _image_average_hash(asset.path)
        color_signature = _image_color_signature(asset.path)
        if image_hash is None or color_signature is None:
            continue
        signatures.append((asset.scene_id, image_hash, color_signature))
    if len(signatures) < 2:
        return 100, []

    rows: list[dict[str, Any]] = []
    highest_similarity = 0.0
    for index, (scene_a, hash_a, color_a) in enumerate(signatures):
        for scene_b, hash_b, color_b in signatures[index + 1:]:
            hash_similarity = sum(1 for left, right in zip(hash_a, hash_b) if left == right) / max(1, len(hash_a))
            color_similarity = _cosine_similarity(color_a, color_b)
            combined = hash_similarity * 0.70 + color_similarity * 0.30
            highest_similarity = max(highest_similarity, combined)
            rows.append(
                {
                    "scene_a": scene_a,
                    "scene_b": scene_b,
                    "hash_similarity": round(hash_similarity, 4),
                    "color_similarity": round(color_similarity, 4),
                    "combined_similarity": round(combined, 4),
                }
            )
    diversity_score = _clamp_score(100 - max(0.0, highest_similarity - 0.74) * 250)
    return diversity_score, sorted(rows, key=lambda row: row["combined_similarity"], reverse=True)[:8]


def _actual_palette_diversity(visual_assets: list[VisualAsset]) -> tuple[int, dict[str, Any]]:
    stats_rows: list[dict[str, Any]] = []
    for asset in visual_assets:
        if not asset.path:
            continue
        stats = _image_basic_stats(asset.path)
        if stats is None:
            continue
        stats_rows.append({"scene_id": asset.scene_id, **stats})
    if len(stats_rows) < 2:
        return 100, {"scene_stats": stats_rows}

    brightness_values = [float(row["brightness"]) for row in stats_rows]
    saturation_values = [float(row["saturation"]) for row in stats_rows]
    rgb_values = [np.asarray(row["rgb_mean"], dtype=np.float32) for row in stats_rows]
    rgb_distances: list[float] = []
    for index, rgb_a in enumerate(rgb_values):
        for rgb_b in rgb_values[index + 1:]:
            rgb_distances.append(float(np.linalg.norm(rgb_a - rgb_b)))

    brightness_range = max(brightness_values) - min(brightness_values)
    saturation_range = max(saturation_values) - min(saturation_values)
    average_rgb_distance = float(sum(rgb_distances) / max(1, len(rgb_distances)))
    score = (
        min(38.0, brightness_range / 1.45)
        + min(42.0, average_rgb_distance / 1.25)
        + min(20.0, saturation_range / 1.15)
    )
    metrics = {
        "brightness_range": round(brightness_range, 2),
        "saturation_range": round(saturation_range, 2),
        "average_rgb_distance": round(average_rgb_distance, 2),
        "scene_stats": [
            {
                "scene_id": row["scene_id"],
                "brightness": round(float(row["brightness"]), 2),
                "saturation": round(float(row["saturation"]), 2),
                "rgb_mean": [round(float(value), 2) for value in row["rgb_mean"]],
            }
            for row in stats_rows
        ],
    }
    return _clamp_score(score), metrics


def check_visual_quality(visual_assets: list[VisualAsset], scenes: list[Scene]) -> VisualQualityResult:
    scene_scores = [_visual_scene_score(asset) for asset in visual_assets]
    cinematic_subtitle_render = bool(visual_assets) and all(_asset_uses_cinematic_subtitle(asset) for asset in visual_assets)
    topic_relevance = _clamp_score(
        sum(int(item["score"]) for item in scene_scores) / max(1, len(scene_scores))
    )
    location_count = len({str(asset.visual_brief.get("location")) for asset in visual_assets if asset.visual_brief})
    camera_count = len({str(asset.visual_brief.get("camera")) for asset in visual_assets if asset.visual_brief})
    role_count = len({str(asset.visual_brief.get("role")) for asset in visual_assets if asset.visual_brief})
    pass_score = VISUAL_QUALITY_SCORING["marker_pass_score"]
    visual_variety = _clamp_score(
        VISUAL_QUALITY_SCORING["visual_variety_base"]
        + location_count * VISUAL_QUALITY_SCORING["visual_variety_location_weight"]
        + camera_count * VISUAL_QUALITY_SCORING["visual_variety_camera_weight"]
        + role_count * VISUAL_QUALITY_SCORING["visual_variety_role_weight"]
    )
    text_safe_space = (
        pass_score
        if all(_contains_any_marker(asset.prompt, _config_nested_list(VISUAL_STRATEGY, "quality_markers", "text_safe_space_any")) for asset in visual_assets)
        else VISUAL_QUALITY_SCORING["text_safe_space_fail_score"]
    )
    policy_safety = (
        pass_score
        if all(_contains_all_markers(asset.prompt, _config_nested_list(VISUAL_STRATEGY, "quality_markers", "policy_safety_all")) for asset in visual_assets)
        else VISUAL_QUALITY_SCORING["policy_safety_fail_score"]
    )
    cinematic_quality = (
        pass_score
        if all(_contains_all_markers(asset.prompt, _config_nested_list(VISUAL_STRATEGY, "quality_markers", "cinematic_quality_all")) for asset in visual_assets)
        else VISUAL_QUALITY_SCORING["cinematic_quality_fail_score"]
    )
    documentary_realism = (
        pass_score
        if all(_contains_all_markers(asset.prompt, _config_nested_list(VISUAL_STRATEGY, "quality_markers", "documentary_realism_all")) for asset in visual_assets)
        else VISUAL_QUALITY_SCORING["documentary_realism_fail_score"]
    )
    foreground_tension = (
        pass_score
        if all(_contains_all_markers(asset.prompt, _config_nested_list(VISUAL_STRATEGY, "quality_markers", "foreground_tension_all")) for asset in visual_assets)
        else VISUAL_QUALITY_SCORING["foreground_tension_fail_score"]
    )
    thumbnail_assets = [
        asset
        for asset in visual_assets
        if str((asset.visual_brief or {}).get("role") or "") in {"hook", "why_now"}
    ] or visual_assets[:2]
    thumbnail_drama = (
        pass_score
        if thumbnail_assets and all(_contains_all_markers(asset.prompt, _config_nested_list(VISUAL_STRATEGY, "quality_markers", "thumbnail_drama_all")) for asset in thumbnail_assets)
        else VISUAL_QUALITY_SCORING["thumbnail_drama_fail_score"]
    )
    if cinematic_subtitle_render:
        diegetic_text_prompt = pass_score
    else:
        diegetic_text_prompt = (
            pass_score
            if all(
                str((asset.visual_brief or {}).get("diegetic_text") or "")
                and "Controlled in-image text" in asset.prompt
                and str((asset.visual_brief or {}).get("diegetic_text") or "") in asset.prompt
                for asset in visual_assets
            )
            else VISUAL_QUALITY_SCORING.get("diegetic_text_prompt_fail_score", 60)
        )
    paper_prop_regression_hits = [
        term
        for asset in visual_assets
        for term in VISUAL_PAPER_PROP_REGRESSION_TERMS
        if term in f"{asset.prompt} {asset.visual_brief or {}}".casefold()
    ]
    paper_prop_regression = (
        pass_score
        if not paper_prop_regression_hits
        else VISUAL_QUALITY_SCORING.get("paper_prop_regression_fail_score", 45)
    )
    scene_relevance = min((int(item["score"]) for item in scene_scores), default=0)
    visual_metaphor = _clamp_score(
        sum(int(item.get("visual_metaphor_score", 0)) for item in scene_scores) / max(1, len(scene_scores))
    )
    scene_visual_metaphor = min((int(item.get("visual_metaphor_score", 0)) for item in scene_scores), default=0)
    actual_visual_diversity, similarity_rows = _actual_visual_similarity(visual_assets)
    actual_palette_diversity, palette_metrics = _actual_palette_diversity(visual_assets)

    scores = {
        "topic_relevance": topic_relevance,
        "scene_relevance": scene_relevance,
        "visual_metaphor": visual_metaphor,
        "scene_visual_metaphor": scene_visual_metaphor,
        "visual_variety": visual_variety,
        "actual_visual_diversity": actual_visual_diversity,
        "actual_palette_diversity": actual_palette_diversity,
        "text_safe_space": text_safe_space,
        "policy_safety": policy_safety,
        "cinematic_quality": cinematic_quality,
        "documentary_realism": documentary_realism,
        "foreground_tension": foreground_tension,
        "thumbnail_drama": thumbnail_drama,
        "diegetic_text_prompt": diegetic_text_prompt,
        "paper_prop_regression": paper_prop_regression,
    }
    blockers: list[str] = []
    if len(scene_scores) != len(scenes):
        blockers.append(f"visual_brief_count_mismatch:{len(scene_scores)}/{len(scenes)}")
    minimums = dict(VISUAL_QUALITY_MINIMUMS)
    for key, minimum in minimums.items():
        if scores[key] < minimum:
            blockers.append(f"{key}_below_{minimum}:{scores[key]}")
    default_scene_ids = [
        str(asset.scene_id)
        for asset in visual_assets
        if str((asset.visual_brief or {}).get("issue_type") or "") != "civic_fact_check"
        and str((asset.visual_brief or {}).get("concrete_scene") or "").strip() == VISUAL_DEFAULT_CONCRETE_SCENE
    ]
    if default_scene_ids:
        blockers.append(f"topic_specific_concrete_scene_missing:{','.join(default_scene_ids)}")
    return VisualQualityResult(
        passed=not blockers,
        scores=scores,
        blockers=blockers,
        scene_scores=[
            *scene_scores,
            {
                "similarity_pairs": similarity_rows,
                "palette_metrics": palette_metrics,
            },
        ]
        if similarity_rows or palette_metrics.get("scene_stats")
        else scene_scores,
    )


def _sanitize_visual_source_context(text: str) -> str:
    sanitized = str(text or "")
    for source, target in VISUAL_SOURCE_CONTEXT_REPLACEMENTS.items():
        sanitized = re.sub(re.escape(source), target, sanitized, flags=re.IGNORECASE)
    return sanitized


def _build_cinematic_prompt(scene: Scene, brief: VisualBrief | None = None) -> str:
    if brief is None:
        brief = _build_visual_brief(
            TopicCandidate(
                title=scene.on_screen_text,
                angle=str(VISUAL_PROMPTING.get("single_scene_angle", "")),
                slot="visual",
                target_duration_sec=scene.duration_sec,
                claims=[],
                source_ids=[],
            ),
            scene,
            0,
            1,
        )
    palette_discipline = ", ".join(
        f"{role} is {palette}" for role, palette in VISUAL_ROLE_PALETTE_MAP.items()
    )
    realism_principles = "; ".join(VISUAL_REALISM_PRINCIPLES)
    drama_principles = "; ".join(VISUAL_DRAMA_PRINCIPLES)
    reality_beat = VISUAL_ROLE_REALITY_BEATS.get(brief.role, "")
    intensity_beat = VISUAL_ROLE_INTENSITY_BEATS.get(brief.role, "")
    topic_relevance_terms = ", ".join(brief.relevance_terms) or str(
        VISUAL_CINEMATIC_PROMPTING.get("topic_relevance_fallback", "")
    )
    template_values = {
        "source_visual": _sanitize_visual_source_context(scene.visual),
        "visual_intent": brief.visual_intent,
        "concrete_scene": brief.concrete_scene,
        "visual_treatment": brief.visual_treatment,
        "action_beat": brief.action_beat,
        "reality_beat": reality_beat,
        "intensity_beat": intensity_beat,
        "visual_anchors": ", ".join(brief.visual_anchor),
        "issue_type": brief.issue_type,
        "role": brief.role,
        "location": brief.location,
        "camera": brief.camera,
        "emotion": brief.emotion,
        "palette": brief.palette,
        "realism_principles": realism_principles,
        "drama_principles": drama_principles,
        "topic_relevance_terms": topic_relevance_terms,
        "palette_discipline": palette_discipline,
        "safety_constraints": ", ".join(brief.safety_constraints),
        "diegetic_text": brief.diegetic_text,
        "diegetic_text_directive": brief.diegetic_text_directive,
        "repetition_guard": VISUAL_REPETITION_GUARD,
        "role_separation": VISUAL_ROLE_SEPARATION,
        "shot_contract": "; ".join(brief.shot_contract),
        "forbidden_dominant_elements": "; ".join(brief.forbidden_dominant_elements),
        "scene_uniqueness_key": brief.scene_uniqueness_key,
    }
    if brief.render_style == CINEMATIC_SUBTITLE_RENDER_STYLE:
        subtitle_primary_template = str(
            VISUAL_CINEMATIC_PROMPTING.get("subtitle_primary_template", "{concrete_scene}")
        )
        template_values["primary_request"] = _format_prompt_template(subtitle_primary_template, template_values)
        subtitle_lines = VISUAL_CINEMATIC_PROMPTING.get("subtitle_lines", [])
        if not isinstance(subtitle_lines, list):
            raise RuntimeError("Strategy config key must be a list: prompting.cinematic.subtitle_lines")
        rendered_lines = [_format_prompt_template(line, template_values) for line in subtitle_lines]
        rendered_lines.extend(
            [
                "Shot contract: {shot_contract}",
                "Forbidden dominant elements: {forbidden_dominant_elements}",
                "Scene uniqueness key: {scene_uniqueness_key}",
            ]
        )
        return "\n".join(_format_prompt_template(line, template_values) for line in rendered_lines)
    directed_primary_template = str(VISUAL_CINEMATIC_PROMPTING.get("directed_primary_template", "{source_visual}"))
    template_values["primary_request"] = _format_prompt_template(directed_primary_template, template_values)
    lines = VISUAL_CINEMATIC_PROMPTING.get("lines", [])
    if not isinstance(lines, list):
        raise RuntimeError("Strategy config key must be a list: prompting.cinematic.lines")
    rendered_lines = [_format_prompt_template(str(line), template_values) for line in lines if str(line).strip()]
    rendered_lines.extend(
        [
            "Shot contract: {shot_contract}",
            "Forbidden dominant elements: {forbidden_dominant_elements}",
            "Scene uniqueness key: {scene_uniqueness_key}",
        ]
    )
    return "\n".join(_format_prompt_template(line, template_values) for line in rendered_lines)


def _try_generate_visual(provider: str, prompt: str, out: Path) -> tuple[bool, list[str]]:
    if provider == "codex_cli":
        return _generate_with_codex_image_cli(prompt, out)
    if provider == "gemini_api":
        return _generate_with_gemini(prompt, out)
    return False, [f"unknown provider: {provider}"]


def _generate_with_codex_image_cli(prompt: str, out: Path) -> tuple[bool, list[str]]:
    configured = os.environ.get("CODEX_IMAGE_CLI")
    script = Path(configured) if configured else Path.home() / ".codex" / "skills" / ".system" / "imagegen" / "scripts" / "image_gen.py"
    if not script.exists() or not script.is_file():
        return False, [f"codex_cli not found: {script}"]
    if not _env_value("OPENAI_API_KEY"):
        return False, ["codex_cli skipped: OPENAI_API_KEY unavailable"]

    cmd = [
        sys.executable,
        str(script),
        "generate",
        "--prompt",
        prompt,
        "--use-case",
        str(VISUAL_CODEX_CLI_PROMPTING.get("use_case", "")),
        "--style",
        str(VISUAL_CODEX_CLI_PROMPTING.get("style", "")),
        "--composition",
        str(VISUAL_CODEX_CLI_PROMPTING.get("composition", "")),
        "--lighting",
        str(VISUAL_CODEX_CLI_PROMPTING.get("lighting", "")),
        "--constraints",
        str(VISUAL_CODEX_CLI_PROMPTING.get("constraints", "")),
        "--negative",
        str(VISUAL_CODEX_CLI_PROMPTING.get("negative", "")),
        "--quality",
        os.environ.get("AINO_CODEX_IMAGE_QUALITY", "low"),
        "--size",
        os.environ.get("AINO_IMAGE_SIZE", "1024x1536"),
        "--out",
        str(out),
        "--force",
    ]
    try:
        proc = subprocess.run(cmd, check=False, capture_output=True, text=True, timeout=360, env=os.environ.copy())
    except Exception as exc:
        return False, [f"codex_cli failed to start: {exc}"]
    if proc.returncode != 0:
        err = (proc.stderr or proc.stdout or "").strip().splitlines()[-3:]
        return False, ["codex_cli failed: " + " | ".join(err)]
    if not _valid_image(out):
        return False, ["codex_cli produced invalid image"]
    return True, ["codex_cli generated image"]


def _generate_with_gemini(prompt: str, out: Path) -> tuple[bool, list[str]]:
    api_key = _env_value("GEMINI_API_KEY", "GOOGLE_API_KEY")
    if not api_key:
        return False, ["gemini_api skipped: GEMINI_API_KEY/GOOGLE_API_KEY unavailable"]
    notes: list[str] = []
    max_attempts = int(_env_value("GEMINI_IMAGE_RETRIES") or "4")
    model = os.environ.get("GEMINI_IMAGE_MODEL", "gemini-2.5-flash-image")
    try:
        from google import genai

        client = genai.Client(api_key=api_key)
    except Exception as exc:
        return False, [f"gemini_api failed to start: {exc}"]

    for attempt in range(1, max_attempts + 1):
        try:
            response = client.models.generate_content(model=model, contents=prompt)
            parts = getattr(response, "parts", None)
            if parts is None and getattr(response, "candidates", None):
                parts = response.candidates[0].content.parts
            for part in parts or []:
                if getattr(part, "inline_data", None) is not None:
                    if hasattr(part, "as_image"):
                        image = part.as_image()
                    else:
                        image = Image.open(BytesIO(part.inline_data.data))
                    image.save(out)
                    if _valid_image(out):
                        return True, [*notes, f"gemini_api generated image on attempt {attempt}"]
            notes.append(f"gemini_api returned no image on attempt {attempt}")
        except Exception as exc:
            message = str(exc)
            notes.append(f"gemini_api attempt {attempt} failed: {message}")
            if not _transient_gemini_error(message) or attempt == max_attempts:
                return False, notes
        if attempt < max_attempts:
            time.sleep(min(18, 4 * attempt))
    return False, notes


def _transient_gemini_error(message: str) -> bool:
    lowered = message.lower()
    return any(marker in lowered for marker in ["503", "unavailable", "high demand", "temporarily"])


def _valid_image(path: Path) -> bool:
    try:
        with Image.open(path) as image:
            width, height = image.size
        return width >= 512 and height >= 512
    except Exception:
        return False


def _visual_grade_float(grade: dict[str, Any], key: str, fallback: float) -> float:
    try:
        return float(grade.get(key, fallback))
    except (TypeError, ValueError):
        return fallback


def _apply_visual_color_grade(path: Path, brief: VisualBrief) -> bool:
    grade = VISUAL_ROLE_COLOR_GRADES.get(brief.role)
    if not isinstance(grade, dict):
        return False
    rgb = grade.get("overlay_rgb")
    if (
        not isinstance(rgb, list)
        or len(rgb) != 3
        or not all(isinstance(value, (int, float)) for value in rgb)
    ):
        return False
    try:
        image = Image.open(path).convert("RGB")
    except Exception:
        return False
    image = ImageEnhance.Color(image).enhance(_visual_grade_float(grade, "color", 1.0))
    image = ImageEnhance.Contrast(image).enhance(_visual_grade_float(grade, "contrast", 1.0))
    image = ImageEnhance.Brightness(image).enhance(_visual_grade_float(grade, "brightness", 1.0))
    overlay_color = tuple(max(0, min(255, int(value))) for value in rgb)
    overlay = Image.new("RGB", image.size, overlay_color)
    image = Image.blend(image, overlay, max(0.0, min(0.35, _visual_grade_float(grade, "alpha", 0.0))))
    image.save(path)
    return True


def _write_local_cinematic_subtitle_asset(path: Path, scene: Scene, index: int, brief: VisualBrief) -> None:
    width, height = CANVAS_WIDTH, CANVAS_HEIGHT
    rng = np.random.default_rng(seed=scene.scene_id * 104729 + index)
    base = Image.new("RGB", (width, height), "#121417")
    draw = ImageDraw.Draw(base, "RGBA")
    palettes = [
        ((38, 45, 50), (122, 52, 54), (219, 211, 188)),
        ((24, 40, 52), (28, 84, 104), (190, 220, 228)),
        ((42, 36, 31), (120, 86, 48), (230, 189, 116)),
        ((30, 33, 36), (67, 95, 84), (202, 222, 190)),
    ]
    c1, c2, c3 = palettes[index % len(palettes)]
    for y in range(height):
        ratio = y / height
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        draw.line((0, y, width, y), fill=(r, g, b, 255))

    role = brief.role
    issue_type = brief.issue_type
    # Common photographed-space cues: ceiling lights, depth lines, and a clean lower third.
    for x in range(-80, width + 120, 170):
        draw.line((x, 170, x + 120, 640), fill=(255, 255, 255, 22), width=3)
    draw.rectangle((0, 0, width, 260), fill=(0, 0, 0, 42))
    draw.rectangle((0, 1180, width, height), fill=(0, 0, 0, 88))
    floor_y = 1040
    draw.polygon([(0, floor_y), (width, 900), (width, height), (0, height)], fill=(6, 8, 10, 88))

    def person(cx: int, cy: int, scale: float, alpha: int = 190) -> None:
        head = int(42 * scale)
        body_w = int(90 * scale)
        body_h = int(260 * scale)
        draw.ellipse((cx - head, cy - body_h - head * 2, cx + head, cy - body_h), fill=(16, 18, 20, alpha))
        draw.rounded_rectangle((cx - body_w // 2, cy - body_h, cx + body_w // 2, cy), radius=28, fill=(18, 22, 25, alpha))

    def mic(cx: int, cy: int, scale: float = 1.0) -> None:
        draw.ellipse((cx - int(24 * scale), cy - int(18 * scale), cx + int(24 * scale), cy + int(18 * scale)), fill=(10, 12, 14, 220))
        draw.line((cx, cy + int(18 * scale), cx + int(80 * scale), cy + int(90 * scale)), fill=(10, 12, 14, 210), width=max(2, int(6 * scale)))

    def desk(x0: int, y0: int, x1: int, y1: int) -> None:
        draw.polygon([(x0, y0), (x1, y0 - 48), (x1 + 120, y1), (x0 - 80, y1)], fill=(18, 19, 19, 210))
        draw.line((x0 + 30, y0 + 20, x1 - 30, y0 - 24), fill=(*c3, 92), width=7)

    if role in {"hook", "why_now"} or issue_type in {"party_strategy", "election_frame"}:
        draw.rectangle((140, 390, 940, 830), fill=(9, 13, 18, 145))
        draw.rectangle((210, 450, 870, 760), fill=(255, 255, 255, 24))
        person(350, 970, 0.82, 210)
        person(735, 930, 0.72, 180)
        desk(120, 1080, 970, 1560)
        for mx in [620, 710, 802]:
            mic(mx, 1120, 0.72)
    elif role in {"evidence", "criteria", "verification"}:
        desk(80, 920, 1000, 1510)
        for i in range(5):
            x = 220 + i * 128
            y = 900 + int(rng.integers(-28, 32))
            draw.rounded_rectangle((x, y, x + 92, y + 142), radius=9, fill=(225, 218, 202, 145))
        draw.ellipse((700, 1010, 824, 1055), fill=(12, 15, 18, 220))
        draw.rectangle((748, 1050, 770, 1210), fill=(12, 15, 18, 220))
        draw.rounded_rectangle((170, 1160, 430, 1235), radius=38, fill=(138, 101, 73, 135))
    elif role == "responsibility":
        draw.rectangle((210, 430, 870, 930), fill=(10, 14, 16, 150))
        draw.rectangle((425, 560, 655, 930), fill=(18, 20, 22, 220))
        person(315, 980, 0.7, 170)
        person(765, 980, 0.7, 170)
        for mx in [270, 390, 690, 810]:
            mic(mx, 1110, 0.58)
        desk(120, 1085, 960, 1540)
    else:
        draw.rectangle((180, 390, 900, 850), fill=(18, 22, 25, 130))
        for i in range(3):
            draw.rounded_rectangle((255 + i * 185, 470, 390 + i * 185, 670), radius=16, fill=(255, 255, 255, 28))
        person(760, 1010, 0.78, 205)
        desk(100, 1090, 940, 1530)
        draw.rounded_rectangle((180, 950, 470, 1080), radius=28, fill=(225, 218, 202, 90))

    draw.rectangle((0, 1180, width, height), fill=(0, 0, 0, 80))
    draw.ellipse((60, 940, 420, 1540), fill=(0, 0, 0, 70))
    for _ in range(18):
        x = int(rng.integers(0, width))
        y = int(rng.integers(260, 1180))
        draw.ellipse((x, y, x + int(rng.integers(2, 8)), y + int(rng.integers(2, 8))), fill=(255, 255, 255, int(rng.integers(10, 36))))
    noise = rng.normal(0, 8, (height, width, 1)).astype(np.int16)
    arr = np.asarray(base).astype(np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    Image.fromarray(arr, "RGB").filter(ImageFilter.GaussianBlur(radius=0.25)).save(path)


def _write_local_cinematic_asset(path: Path, scene: Scene, index: int, brief: VisualBrief | None = None) -> None:
    if brief and brief.render_style == CINEMATIC_SUBTITLE_RENDER_STYLE:
        _write_local_cinematic_subtitle_asset(path, scene, index, brief)
        return
    width, height = CANVAS_WIDTH, CANVAS_HEIGHT
    rng = np.random.default_rng(seed=scene.scene_id * 7919)
    base = Image.new("RGB", (width, height), "#11151b")
    draw = ImageDraw.Draw(base, "RGBA")
    palettes = [
        ((32, 45, 54), (112, 35, 48), (220, 195, 138)),
        ((20, 30, 42), (50, 78, 92), (196, 211, 218)),
        ((35, 31, 28), (91, 63, 44), (206, 155, 94)),
        ((18, 24, 31), (72, 82, 72), (202, 212, 180)),
    ]
    c1, c2, c3 = palettes[index % len(palettes)]
    for y in range(height):
        ratio = y / height
        r = int(c1[0] * (1 - ratio) + c2[0] * ratio)
        g = int(c1[1] * (1 - ratio) + c2[1] * ratio)
        b = int(c1[2] * (1 - ratio) + c2[2] * ratio)
        draw.line([(0, y), (width, y)], fill=(r, g, b, 255))

    # Build a procedural documentary still instead of an abstract color card.
    horizon = int(height * 0.58)
    draw.polygon(
        [(0, horizon), (width, int(height * 0.48)), (width, height), (0, height)],
        fill=(10, 13, 16, 150),
    )
    draw.rectangle((0, 120, width, 520), fill=(255, 255, 255, 18))
    for x in range(-180, width + 200, 180):
        draw.line((x, 120, x + 220, 520), fill=(255, 255, 255, 18), width=3)
    for x in range(80, width, 210):
        draw.line((x, 160, x + int(rng.integers(-25, 25)), 520), fill=(185, 215, 230, 28), width=2)

    role_text = f"{scene.title} {scene.visual} {scene.on_screen_text}".casefold()
    desk_top = int(height * 0.64)
    draw.polygon(
        [(70, desk_top), (width - 90, desk_top - 60), (width + 80, height), (-80, height)],
        fill=(24, 23, 22, 210),
    )
    draw.polygon(
        [(120, desk_top + 24), (width - 140, desk_top - 28), (width - 42, desk_top + 42), (88, desk_top + 92)],
        fill=(*c3, 46),
    )

    def paper(cx: int, cy: int, w: int, h: int, angle: int = 0, alpha: int = 185) -> None:
        points = [
            (cx - w // 2 + angle, cy - h // 2),
            (cx + w // 2 + angle, cy - h // 2 + int(h * 0.08)),
            (cx + w // 2 - angle, cy + h // 2),
            (cx - w // 2 - angle, cy + h // 2 - int(h * 0.08)),
        ]
        draw.polygon(points, fill=(232, 225, 205, alpha))
        draw.line((points[0], points[1]), fill=(255, 255, 255, 70), width=3)

    def folder(cx: int, cy: int, w: int, h: int, alpha: int = 170) -> None:
        draw.rounded_rectangle((cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2), radius=16, fill=(*c3, alpha))
        draw.rectangle((cx - w // 2 + 28, cy - h // 2 - 22, cx - w // 4, cy - h // 2 + 14), fill=(*c3, alpha))

    def microphone(cx: int, cy: int, scale: float = 1.0) -> None:
        draw.ellipse(
            (cx - int(34 * scale), cy - int(28 * scale), cx + int(34 * scale), cy + int(28 * scale)),
            fill=(18, 22, 24, 230),
        )
        draw.rectangle((cx - int(8 * scale), cy + int(22 * scale), cx + int(8 * scale), cy + int(115 * scale)), fill=(12, 14, 16, 220))
        draw.line((cx, cy + int(115 * scale), cx + int(95 * scale), cy + int(172 * scale)), fill=(12, 14, 16, 210), width=max(2, int(6 * scale)))

    def cropped_hand(cx: int, cy: int, w: int = 180, h: int = 72) -> None:
        draw.rounded_rectangle((cx - w // 2, cy - h // 2, cx + w // 2, cy + h // 2), radius=34, fill=(152, 112, 82, 145))
        draw.ellipse((cx + w // 3, cy - h // 3, cx + w // 2 + 38, cy + h // 3), fill=(150, 110, 80, 130))

    def verification_zone(x0: int, y0: int, x1: int, y1: int, alpha: int = 88) -> None:
        draw.rounded_rectangle((x0, y0, x1, y1), radius=22, fill=(210, 230, 235, alpha))
        draw.line((x0 + 22, y0 + 18, x1 - 22, y0 + 18), fill=(*c3, min(230, alpha + 70)), width=5)

    def comment_heat_zone(x0: int, y0: int, x1: int, y1: int, alpha: int = 116) -> None:
        draw.rounded_rectangle((x0, y0, x1, y1), radius=26, fill=(*c3, alpha))
        for offset in [26, 62]:
            draw.line((x0 + 22, y0 + offset, x1 - 22, y0 + offset), fill=(255, 255, 255, 44), width=4)

    if any(token in role_text for token in ["hook", "entrance"]):
        draw.rectangle((0, 440, width, 980), fill=(8, 12, 16, 95))
        draw.polygon([(0, 440), (350, 420), (260, 980), (0, 1040)], fill=(0, 0, 0, 110))
        draw.rectangle((470, 650, 690, 1120), fill=(12, 14, 16, 205))
        draw.rectangle((515, 720, 645, 1120), fill=(28, 31, 34, 220))
        draw.polygon([(0, 1000), (340, 930), (430, 1240), (0, 1330)], fill=(0, 0, 0, 118))
        cropped_hand(310, 1040, 250, 92)
        for x in [760, 840, 920]:
            microphone(x, 1080, 0.72)
    elif any(token in role_text for token in ["receipt", "evidence", "근거"]):
        for i, x in enumerate([210, 430, 650]):
            verification_zone(x, 900 + i * 12, x + 185, 1190 + i * 18, 86)
        cropped_hand(760, 1110, 210, 74)
        draw.ellipse((705, 1015, 820, 1062), fill=(12, 14, 16, 210))
        draw.rectangle((740, 1060, 760, 1200), fill=(12, 14, 16, 210))
        draw.line((240, 1235, 850, 1120), fill=(210, 56, 68, 178), width=10)
    elif any(token in role_text for token in ["counter", "missing", "responsibility", "빈", "책임"]):
        draw.rectangle((210, 610, 870, 1120), fill=(12, 16, 18, 135))
        draw.ellipse((440, 720, 640, 900), fill=(16, 19, 20, 220))
        draw.rectangle((500, 880, 580, 1160), fill=(15, 17, 18, 220))
        for x in [300, 410, 690, 800]:
            microphone(x, 1120, 0.55)
        draw.line((220, 1280, 900, 1220), fill=(*c3, 128), width=12)
        draw.rectangle((300, 1260, 780, 1370), fill=(255, 255, 255, 24))
    elif any(token in role_text for token in ["cta", "comment", "댓글"]):
        draw.rounded_rectangle((680, 910, 940, 1090), radius=28, fill=(16, 18, 22, 190))
        draw.line((725, 1040, 885, 970), fill=(*c3, 210), width=12)
        for i in range(3):
            comment_heat_zone(190 + i * 210, 1000 + int(rng.integers(-18, 20)), 360 + i * 210, 1125 + int(rng.integers(-12, 18)), 112)
        draw.rounded_rectangle((180, 1185, 900, 1260), radius=18, fill=(15, 18, 22, 185))
        for i in range(8):
            draw.rectangle((220 + i * 78, 1212, 265 + i * 78, 1232), fill=(*c3, 190))
        cropped_hand(610, 1180, 210, 76)
    else:
        draw.rectangle((140, 520, 940, 950), fill=(20, 24, 28, 150))
        for i in range(5):
            draw.rounded_rectangle(
                (210 + i * 135, 600 + int(rng.integers(-20, 24)), 310 + i * 135, 760 + int(rng.integers(-16, 18))),
                radius=8,
                fill=(190, 220, 230, 42),
            )
        for i, x in enumerate([230, 460, 690]):
            verification_zone(x, 1030 + i * 24, x + 170, 1235 + i * 20, 72)
        draw.line((250, 1310, 850, 1238), fill=(*c3, 145), width=9)

    draw.ellipse((70, 1020, 380, 1540), fill=(0, 0, 0, 82))
    draw.rectangle((0, height - 520, width, height), fill=(0, 0, 0, 100))
    draw.rectangle((0, 0, width, height), outline=(255, 255, 255, 20), width=3)
    noise = rng.normal(0, 9, (height, width, 1)).astype(np.int16)
    arr = np.asarray(base).astype(np.int16)
    arr = np.clip(arr + noise, 0, 255).astype(np.uint8)
    base = Image.fromarray(arr, "RGB").filter(ImageFilter.GaussianBlur(radius=0.35))
    base.save(path)


@lru_cache(maxsize=64)
def _font(size: int, *, bold: bool = False) -> ImageFont.FreeTypeFont | ImageFont.ImageFont:
    names = (
        [
            "NotoSansCJKkr-Bold.otf",
            "NanumSquareNeo-eHv.ttf",
            "NanumSquareNeo-dEb.ttf",
            "NotoSansKR-VF.ttf",
            "malgunbd.ttf",
        ]
        if bold
        else [
            "NotoSansCJKkr-Regular.otf",
            "NanumSquareNeo-bRg.ttf",
            "NanumSquareNeo-cBd.ttf",
            "NotoSansKR-VF.ttf",
            "malgun.ttf",
        ]
    )
    windir = Path(os.environ.get("WINDIR", "C:/Windows"))
    candidates: list[Path] = []
    for configured in [os.environ.get("AINO_FONT_DIR")]:
        if configured:
            candidates.extend(Path(configured) / name for name in names)
    for font_dir in [
        PACKAGE_DIR / "fonts",
        REPO_DIR / "assets" / "fonts",
        Path.home() / ".local" / "share" / "fonts",
        Path("/usr/share/fonts/opentype/noto"),
        Path("/usr/share/fonts/opentype/noto-cjk"),
        Path("/usr/share/fonts/truetype/noto"),
        Path("/usr/share/fonts/truetype/nanum"),
    ]:
        if font_dir.exists():
            candidates.extend(font_dir / name for name in names)
            candidates.extend(font_dir.glob("*NotoSansCJK*kr*Bold*.otf" if bold else "*NotoSansCJK*kr*Regular*.otf"))
            candidates.extend(font_dir.glob("NotoSansCJK*.otf"))
            candidates.extend(font_dir.glob("NotoSansKR*.ttf"))
            candidates.extend(font_dir.glob("Nanum*.ttf"))
    candidates.extend(windir / "Fonts" / name for name in names)
    for path in candidates:
        if path.exists():
            try:
                return ImageFont.truetype(str(path), size=size)
            except OSError:
                continue
    raise RuntimeError(
        "Korean font not found for TikTok renderer. "
        "Install/bundle NotoSansCJKkr-Regular.otf and NotoSansCJKkr-Bold.otf under src/core/tiktok_aino/fonts."
    )


def _card_ui_config() -> dict[str, Any]:
    return _config_dict(RENDERING_STRATEGY, "card_ui")


def _fallback_scene_role(index: int, total: int) -> str:
    if index <= 0:
        return "hook"
    if index >= max(0, total - 1):
        return "cta"
    middle_roles = ["why_now", "evidence", "criteria", "responsibility", "verification", "evidence"]
    return middle_roles[(index - 1) % len(middle_roles)]


def _card_layout_sequence(ui: dict[str, Any]) -> list[str]:
    value = ui.get("layout_sequence", [])
    if not isinstance(value, list):
        return []
    return [str(item) for item in value if str(item).strip()]


def _card_layout_id(
    scene: Scene,
    index: int,
    total: int,
    *,
    role: str | None = None,
) -> str:
    ui = _card_ui_config()
    total = max(1, total)
    role = (role or _fallback_scene_role(index, total)).strip() or _fallback_scene_role(index, total)
    raw_role_layouts = ui.get("role_layouts", {})
    role_layouts = raw_role_layouts if isinstance(raw_role_layouts, dict) else {}
    editorial_role_layouts = {
        "thumbnail": "impact_cover",
        "context": "top_split",
        "opposing_frame": "side_rule",
        "why_now": "receipt_panel",
        "public_cost": "bottom_receipt",
        "comment_trigger": "witness_stage",
        "share_line": "choice_stack",
        "fairness": "top_split",
    }
    if role in editorial_role_layouts:
        return editorial_role_layouts[role]
    if index <= 0:
        return str(ui.get("first_layout") or role_layouts.get("hook") or "impact_cover")
    if index >= total - 1:
        return str(ui.get("last_layout") or role_layouts.get("cta") or "choice_stack")
    if role == "evidence":
        return ["bottom_receipt", "witness_stage", "receipt_panel"][index % 3]
    if role == "cta":
        return "bottom_receipt"
    if role in role_layouts and str(role_layouts[role]).strip():
        return str(role_layouts[role])
    sequence = _card_layout_sequence(ui)
    return sequence[index % len(sequence)] if sequence else "receipt_panel"


def _layout_signature_part(value: Any, fallback: str) -> str:
    text = re.sub(r"\s+", "_", str(value or "").strip().casefold())
    text = re.sub(r"[^0-9a-z가-힣_:-]", "", text)
    return text[:36] or fallback


def _native_image_text_layout_id(scene: Scene, index: int, total: int, asset: VisualAsset | None) -> str:
    brief = asset.visual_brief if asset and isinstance(asset.visual_brief, dict) else {}
    role = str(brief.get("role") or "").strip() or _fallback_scene_role(index, total)
    base_layout = _card_layout_id(scene, index, total, role=role)
    location = _layout_signature_part(brief.get("location"), "no_location")
    camera = _layout_signature_part(brief.get("camera"), "no_camera")
    treatment = _layout_signature_part(
        brief.get("treatment_id") or brief.get("visual_treatment"),
        "no_treatment",
    )
    anchor = brief.get("foreground_prop") or brief.get("action_beat") or brief.get("concrete_scene")
    if not anchor and isinstance(brief.get("visual_anchor"), list):
        anchor = "_".join(str(item) for item in brief.get("visual_anchor")[:2])
    prop = _layout_signature_part(anchor, "no_prop")
    return f"{base_layout}|{role}|{location}|{camera}|{treatment}|{prop}"


def _native_image_text_visual_signature(asset: VisualAsset | None) -> str:
    brief = asset.visual_brief if asset and isinstance(asset.visual_brief, dict) else {}
    location = _layout_signature_part(brief.get("location"), "no_location")
    camera = _layout_signature_part(brief.get("camera"), "no_camera")
    treatment = _layout_signature_part(
        brief.get("treatment_id") or brief.get("visual_treatment"),
        "no_treatment",
    )
    anchor = brief.get("foreground_prop") or brief.get("action_beat") or brief.get("concrete_scene")
    if not anchor and isinstance(brief.get("visual_anchor"), list):
        anchor = "_".join(str(item) for item in brief.get("visual_anchor")[:2])
    prop = _layout_signature_part(anchor, "no_prop")
    return f"{location}|{camera}|{treatment}|{prop}"


def _card_layout_geometry(layout_id: str, index: int, total: int) -> dict[str, Any]:
    common = {
        "layout_id": layout_id,
        "panel_box": (TEXT_SAFE_LEFT, 1210, TEXT_SAFE_RIGHT - 56, 1518),
        "panel_style": "caption",
        "role_xy": (TEXT_SAFE_LEFT + 26, 1238),
        "headline_xy": (TEXT_SAFE_LEFT + 26, 1288),
        "body_xy": (TEXT_SAFE_LEFT + 28, 1414),
        "headline_width": TEXT_SAFE_WIDTH - 130,
        "body_width": TEXT_SAFE_WIDTH - 146,
        "headline_max_lines": 2,
        "body_max_lines": 2,
        "headline_initial": 66,
        "footer_y": 1538,
        "progress_y": 1618,
        "disclosure_y": 1694,
        "scrim": "caption",
    }
    presets: dict[str, dict[str, Any]] = {
        "impact_cover": {
            "panel_box": (TEXT_SAFE_LEFT, 1018, TEXT_SAFE_RIGHT, 1440),
            "panel_style": "caption",
            "role_xy": (TEXT_SAFE_LEFT + 28, 1050),
            "headline_xy": (TEXT_SAFE_LEFT + 28, 1102),
            "body_xy": (TEXT_SAFE_LEFT + 32, 1252),
            "headline_width": TEXT_SAFE_WIDTH - 76,
            "body_width": TEXT_SAFE_WIDTH - 92,
            "headline_max_lines": 2,
            "body_max_lines": 2,
            "headline_initial": 82,
            "footer_y": 1532,
            "progress_y": 1618,
            "disclosure_y": 1694,
            "scrim": "lower",
        },
        "top_split": {
            "panel_box": (TEXT_SAFE_LEFT, 230, TEXT_SAFE_RIGHT, 560),
            "panel_style": "top_caption",
            "role_xy": (TEXT_SAFE_LEFT + 28, 258),
            "headline_xy": (TEXT_SAFE_LEFT + 28, 310),
            "body_xy": (TEXT_SAFE_LEFT + 30, 398),
            "headline_width": TEXT_SAFE_WIDTH - 76,
            "body_width": TEXT_SAFE_WIDTH - 100,
            "headline_max_lines": 2,
            "body_max_lines": 2,
            "headline_initial": 66,
            "footer_y": 1538,
            "progress_y": 1618,
            "disclosure_y": 1696,
            "scrim": "top",
        },
        "receipt_panel": {
            "panel_box": (TEXT_SAFE_LEFT, 1182, TEXT_SAFE_RIGHT - 38, 1548),
            "panel_style": "receipt_caption",
            "role_xy": (TEXT_SAFE_LEFT + 30, 1212),
            "headline_xy": (TEXT_SAFE_LEFT + 30, 1262),
            "body_xy": (TEXT_SAFE_LEFT + 34, 1400),
            "headline_width": TEXT_SAFE_WIDTH - 118,
            "body_width": TEXT_SAFE_WIDTH - 142,
            "headline_initial": 64,
            "body_max_lines": 2,
            "scrim": "lower",
        },
        "side_rule": {
            "panel_box": (TEXT_SAFE_LEFT, 760, TEXT_SAFE_RIGHT - 60, 1138),
            "panel_style": "side_caption",
            "role_xy": (TEXT_SAFE_LEFT + 28, 792),
            "headline_xy": (TEXT_SAFE_LEFT + 28, 846),
            "body_xy": (TEXT_SAFE_LEFT + 30, 984),
            "headline_width": TEXT_SAFE_WIDTH - 124,
            "body_width": TEXT_SAFE_WIDTH - 146,
            "headline_max_lines": 2,
            "body_max_lines": 2,
            "headline_initial": 66,
            "scrim": "left",
        },
        "witness_stage": {
            "panel_box": (TEXT_SAFE_LEFT + 88, 1048, TEXT_SAFE_RIGHT, 1434),
            "panel_style": "stage_caption",
            "role_xy": (TEXT_SAFE_LEFT + 120, 1080),
            "headline_xy": (TEXT_SAFE_LEFT + 120, 1134),
            "body_xy": (TEXT_SAFE_LEFT + 124, 1286),
            "headline_width": TEXT_SAFE_WIDTH - 188,
            "body_width": TEXT_SAFE_WIDTH - 210,
            "headline_max_lines": 2,
            "body_max_lines": 2,
            "headline_initial": 66,
            "scrim": "stage",
        },
        "bottom_receipt": {
            "panel_box": (TEXT_SAFE_LEFT, 1210, TEXT_SAFE_RIGHT, 1540),
            "panel_style": "bottom_caption",
            "role_xy": (TEXT_SAFE_LEFT + 30, 1238),
            "headline_xy": (TEXT_SAFE_LEFT + 30, 1288),
            "body_xy": (TEXT_SAFE_LEFT + 34, 1410),
            "headline_width": TEXT_SAFE_WIDTH - 88,
            "body_width": TEXT_SAFE_WIDTH - 112,
            "headline_initial": 62,
            "headline_max_lines": 2,
            "body_max_lines": 2,
            "scrim": "bottom",
        },
        "choice_stack": {
            "panel_box": (TEXT_SAFE_LEFT, 1048, TEXT_SAFE_RIGHT, 1472),
            "panel_style": "choice_caption",
            "role_xy": (TEXT_SAFE_LEFT + 30, 1080),
            "headline_xy": (TEXT_SAFE_LEFT + 30, 1132),
            "body_xy": (TEXT_SAFE_LEFT + 34, 1278),
            "headline_width": TEXT_SAFE_WIDTH - 88,
            "body_width": TEXT_SAFE_WIDTH - 112,
            "headline_max_lines": 2,
            "body_max_lines": 2,
            "headline_initial": 66,
            "scrim": "choice",
        },
    }
    selected = {**common, **presets.get(layout_id, {})}
    selected["layout_id"] = layout_id
    return selected


def _draw_layout_scrim(draw: ImageDraw.ImageDraw, layout_id: str, width: int, height: int) -> None:
    for y in range(height):
        alpha = int(6 + 82 * (y / height) ** 2.0)
        draw.line([(0, y), (width, y)], fill=(0, 0, 0, alpha))
    if layout_id == "impact_cover":
        draw.rectangle((0, 0, width, 230), fill=(0, 0, 0, 52))
        draw.rectangle((0, 930, width, 1420), fill=(0, 0, 0, 44))
        draw.rectangle((0, 1510, width, height), fill=(0, 0, 0, 92))
    elif layout_id == "top_split":
        draw.rectangle((0, 175, width, 570), fill=(0, 0, 0, 56))
        draw.rectangle((0, 1510, width, height), fill=(0, 0, 0, 86))
    elif layout_id == "side_rule":
        draw.rectangle((0, 690, 820, 1200), fill=(0, 0, 0, 58))
        draw.polygon([(820, 690), (1080, 690), (820, 1200)], fill=(0, 0, 0, 18))
        draw.rectangle((0, 1510, width, height), fill=(0, 0, 0, 88))
    elif layout_id == "witness_stage":
        draw.polygon([(0, 930), (1080, 820), (1080, 1470), (0, 1530)], fill=(0, 0, 0, 56))
        draw.rectangle((0, 1510, width, height), fill=(0, 0, 0, 88))
    elif layout_id == "bottom_receipt":
        draw.rectangle((0, 1190, width, 1560), fill=(0, 0, 0, 64))
        draw.rectangle((0, 1560, width, height), fill=(0, 0, 0, 92))
    elif layout_id == "choice_stack":
        draw.rectangle((0, 960, width, 1540), fill=(0, 0, 0, 62))
        draw.rectangle((0, 1540, width, height), fill=(0, 0, 0, 92))
    else:
        draw.rectangle((0, 1110, width, 1560), fill=(0, 0, 0, 58))
        draw.rectangle((0, 1588, width, height), fill=(0, 0, 0, 92))


def _draw_layout_panel(
    draw: ImageDraw.ImageDraw,
    layout: dict[str, Any],
    accent: str,
    ui: dict[str, Any],
) -> None:
    x0, y0, x1, y1 = layout["panel_box"]
    style = _config_dict(ui, "headline_panel")
    panel_style = str(layout.get("panel_style", "card"))
    fill = str(style.get("fill", "#05080d"))
    alpha = int(style.get("alpha", 206))
    outline_alpha = int(style.get("outline_alpha", 58))
    if panel_style in {"caption", "top_caption", "receipt_caption", "bottom_caption"}:
        _draw_card_panel(
            draw,
            (x0, y0, x1, y1),
            fill=fill,
            alpha=min(142, max(108, alpha - 76)),
            outline=accent,
            outline_alpha=min(48, outline_alpha),
        )
        draw.rectangle((x0, y0, x1, y0 + 6), fill=_rgba_from_hex(accent, 216))
    elif panel_style == "side_caption":
        _draw_card_panel(
            draw,
            (x0, y0, x1, y1),
            fill=fill,
            alpha=min(138, max(108, alpha - 82)),
            outline=accent,
            outline_alpha=min(42, outline_alpha),
        )
        draw.rectangle((x1 - 7, y0, x1, y1), fill=_rgba_from_hex(accent, 216))
    elif panel_style == "stage_caption":
        draw.polygon(
            [(x0, y0 + 24), (x1, y0), (x1, y1), (x0, y1 - 28)],
            fill=_rgba_from_hex(fill, min(136, max(106, alpha - 82))),
        )
        draw.line((x0 + 18, y1 - 28, x1 - 22, y1 - 58), fill=_rgba_from_hex(accent, 186), width=5)
    elif panel_style == "choice_caption":
        _draw_card_panel(
            draw,
            (x0, y0, x1, y1),
            fill=fill,
            alpha=min(146, max(116, alpha - 70)),
            outline=accent,
            outline_alpha=min(48, outline_alpha),
        )
        for row in range(3):
            top = y1 - 150 + row * 44
            draw.rounded_rectangle((x0 + 34, top, x1 - 34, top + 28), radius=7, fill=(255, 255, 255, 20))
            draw.rectangle((x0 + 48, top + 7, x0 + 58, top + 21), fill=_rgba_from_hex(accent, 204))
    else:
        _draw_card_panel(draw, (x0, y0, x1, y1), fill=fill, alpha=min(150, alpha), outline=accent, outline_alpha=outline_alpha)
        if panel_style in {"receipt", "bottom_receipt"}:
            draw.rectangle((x0, y0, x1, y0 + 8), fill=accent)


def _card_layout_quality(
    scenes: list[Scene],
    assets_by_scene: dict[int, VisualAsset] | None = None,
) -> dict[str, Any]:
    total = len(scenes)
    if total == 0:
        return {"passed": False, "mode": "empty", "layout_ids": [], "unique_count": 0, "required_unique_count": 1}
    if _all_assets_use_cinematic_subtitles(scenes, assets_by_scene):
        layout_ids = [
            _native_image_text_layout_id(scene, index, total, assets_by_scene.get(scene.scene_id) if assets_by_scene else None)
            for index, scene in enumerate(scenes)
        ]
        counts: dict[str, int] = {}
        for layout_id in layout_ids:
            counts[layout_id] = counts.get(layout_id, 0) + 1
        visual_signature_ids = [
            _native_image_text_visual_signature(assets_by_scene.get(scene.scene_id) if assets_by_scene else None)
            for scene in scenes
        ]
        visual_signature_counts: dict[str, int] = {}
        for signature_id in visual_signature_ids:
            visual_signature_counts[signature_id] = visual_signature_counts.get(signature_id, 0) + 1
        required = min(total, 5)
        max_repeat = max(counts.values()) if counts else 0
        visual_signature_max_repeat = max(visual_signature_counts.values()) if visual_signature_counts else 0
        return {
            "passed": len(counts) >= required and visual_signature_max_repeat <= max(2, math.ceil(total * 0.4)),
            "mode": CINEMATIC_SUBTITLE_RENDER_STYLE,
            "layout_ids": layout_ids,
            "unique_count": len(counts),
            "required_unique_count": required,
            "max_repeat_count": max_repeat,
            "adjacent_repeats": [],
            "visual_signature_ids": visual_signature_ids,
            "visual_signature_unique_count": len(visual_signature_counts),
            "visual_signature_max_repeat_count": visual_signature_max_repeat,
        }
    ui = _card_ui_config()
    try:
        configured_min = int(ui.get("layout_variety_min_unique", 5))
    except (TypeError, ValueError):
        configured_min = 5
    required = min(total, max(1, configured_min))
    layout_ids: list[str] = []
    native_image_text_render = bool(assets_by_scene) and all(
        _asset_uses_native_image_text(assets_by_scene.get(scene.scene_id)) for scene in scenes
    )
    for index, scene in enumerate(scenes):
        asset = assets_by_scene.get(scene.scene_id) if assets_by_scene else None
        if native_image_text_render:
            layout_ids.append(_native_image_text_layout_id(scene, index, total, asset))
        else:
            role = str(scene.title or "").strip() or None
            if role not in {
                "thumbnail",
                "context",
                "opposing_frame",
                "why_now",
                "public_cost",
                "comment_trigger",
                "share_line",
                "fairness",
            }:
                role = str((asset.visual_brief or {}).get("role") if asset else "") or None
            layout_ids.append(_card_layout_id(scene, index, total, role=role))
    counts: dict[str, int] = {}
    for layout_id in layout_ids:
        counts[layout_id] = counts.get(layout_id, 0) + 1
    adjacent_repeats = [
        {"scene_id": scenes[index].scene_id, "layout_id": layout_ids[index]}
        for index in range(1, len(layout_ids))
        if layout_ids[index] == layout_ids[index - 1]
    ]
    max_repeat = max(counts.values()) if counts else 0
    visual_signature_ids = [
        _native_image_text_visual_signature(assets_by_scene.get(scene.scene_id) if assets_by_scene else None)
        for scene in scenes
    ] if native_image_text_render else []
    visual_signature_counts: dict[str, int] = {}
    for signature_id in visual_signature_ids:
        visual_signature_counts[signature_id] = visual_signature_counts.get(signature_id, 0) + 1
    visual_signature_max_repeat = max(visual_signature_counts.values()) if visual_signature_counts else 0
    visual_signature_passed = (
        not native_image_text_render
        or (
            len(visual_signature_counts) >= required
            and visual_signature_max_repeat <= max(2, math.ceil(total * 0.4))
        )
    )
    passed = (
        len(counts) >= required
        and len(adjacent_repeats) <= max(0, total // 5)
        and max_repeat <= max(2, math.ceil(total * 0.4))
        and visual_signature_passed
    )
    return {
        "passed": passed,
        "mode": "native_image_text_scene_signature" if native_image_text_render else "card_overlay_layout",
        "layout_ids": layout_ids,
        "unique_count": len(counts),
        "required_unique_count": required,
        "max_repeat_count": max_repeat,
        "adjacent_repeats": adjacent_repeats,
        "visual_signature_ids": visual_signature_ids,
        "visual_signature_unique_count": len(visual_signature_counts),
        "visual_signature_max_repeat_count": visual_signature_max_repeat,
    }


def _asset_uses_native_image_text(asset: VisualAsset | None) -> bool:
    if asset is None:
        return False
    if asset.status != "generated" or asset.provider not in {"codex_cli", "gemini_api"}:
        return False
    brief = asset.visual_brief if isinstance(asset.visual_brief, dict) else {}
    return bool(str(brief.get("diegetic_text") or "").strip())


def _asset_uses_cinematic_subtitle(asset: VisualAsset | None) -> bool:
    if asset is None:
        return False
    brief = asset.visual_brief if isinstance(asset.visual_brief, dict) else {}
    return _normalize_visual_render_style(brief.get("render_style")) == CINEMATIC_SUBTITLE_RENDER_STYLE


def _all_assets_use_cinematic_subtitles(scenes: list[Scene], assets_by_scene: dict[int, VisualAsset] | None) -> bool:
    return bool(scenes) and bool(assets_by_scene) and all(
        _asset_uses_cinematic_subtitle(assets_by_scene.get(scene.scene_id)) for scene in scenes
    )


def _native_image_text_mobile_layout(scene: Scene, path: Path) -> MobileVisualCheck:
    return MobileVisualCheck(
        scene_id=scene.scene_id,
        preview_path=str(path),
        layout_id="native_image_text",
        passed=path.exists(),
        headline_mobile_px=0.0,
        body_mobile_px=0.0,
        headline_line_count=0,
        body_line_count=0,
        headline_fits_box=True,
        body_fits_box=True,
        text_box_overflow=False,
        text_panel_coverage_pct=0.0,
        text_right_rail_clear=True,
        text_above_bottom_ui=True,
        text_render_passed=True,
        preview_size=f"{MOBILE_PREVIEW_WIDTH}x{MOBILE_PREVIEW_HEIGHT}",
    )


def _cinematic_subtitle_mobile_layout(scene: Scene, path: Path) -> MobileVisualCheck:
    return MobileVisualCheck(
        scene_id=scene.scene_id,
        preview_path=str(path),
        layout_id=CINEMATIC_SUBTITLE_RENDER_STYLE,
        passed=path.exists() and _korean_font_probe(),
        headline_mobile_px=_scaled_mobile_px(58),
        body_mobile_px=_scaled_mobile_px(40),
        headline_line_count=min(2, max(1, len(_clean_card_text(scene.on_screen_text)) // 18 + 1)),
        body_line_count=min(2, max(1, len(_clean_card_text(scene.body)) // 24 + 1)),
        headline_fits_box=True,
        body_fits_box=True,
        text_box_overflow=False,
        text_panel_coverage_pct=6.0,
        text_right_rail_clear=True,
        text_above_bottom_ui=True,
        text_render_passed=_korean_font_probe(),
        preview_size=f"{MOBILE_PREVIEW_WIDTH}x{MOBILE_PREVIEW_HEIGHT}",
    )


def _tiktok_native_role_label(role: str, index: int, total: int) -> str:
    config = _config_dict(RENDERING_STRATEGY, "native_caption")
    labels = _config_dict(config, "role_labels")
    if index == 0 and labels.get("hook"):
        return str(labels["hook"])
    if index == total - 1 and labels.get("cta"):
        return str(labels["cta"])
    return labels.get(role, "쟁점")


def _tiktok_native_accent(role: str) -> str:
    config = _config_dict(RENDERING_STRATEGY, "native_caption")
    accents = _config_dict(config, "accent_palette")
    return str(accents.get(role) or accents.get("default") or "#ff335f")


def _tiktok_native_cta_choice_labels() -> list[str]:
    config = _config_dict(RENDERING_STRATEGY, "native_caption")
    labels = config.get("cta_choice_labels")
    if isinstance(labels, list):
        cleaned = [str(label).strip() for label in labels if str(label).strip()]
        if len(cleaned) >= 2:
            return cleaned[:2]
    return ["동의", "반박"]


def _draw_native_caption_pill(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    accent: str,
    *,
    fill_alpha: int = 124,
) -> None:
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    width = bbox[2] - bbox[0] + 34
    height = bbox[3] - bbox[1] + 22
    draw.rounded_rectangle(
        (x, y, x + width, y + height),
        radius=18,
        fill=(0, 0, 0, fill_alpha),
        outline=_rgba_from_hex(accent, 172),
        width=2,
    )
    draw.text((x + 17, y + 10), text, fill="#ffffff", font=font, stroke_width=1, stroke_fill=(0, 0, 0, 150))


def _draw_centered_native_text(
    draw: ImageDraw.ImageDraw,
    text: str,
    box: tuple[int, int, int, int],
    font: ImageFont.ImageFont,
    fill: str,
    *,
    line_gap: int,
    max_lines: int,
    stroke_width: int,
    stroke_alpha: int = 225,
) -> int:
    x0, y0, x1, _y1 = box
    width = x1 - x0
    lines = _wrap_lines(draw, text, font, width)[:max_lines]
    y = y0
    for line in lines:
        bbox = draw.textbbox((0, 0), line, font=font)
        line_w = bbox[2] - bbox[0]
        line_h = bbox[3] - bbox[1]
        x = x0 + max(0, (width - line_w) // 2)
        shadow_pad = 15
        draw.rounded_rectangle(
            (x - shadow_pad, y - 8, x + line_w + shadow_pad, y + line_h + 18),
            radius=12,
            fill=(0, 0, 0, 64),
        )
        draw.text(
            (x, y),
            line,
            fill=fill,
            font=font,
            stroke_width=stroke_width,
            stroke_fill=(0, 0, 0, stroke_alpha),
        )
        y += line_h + line_gap + 16
    return y


def _draw_cinematic_subtitle_frame(
    img: Image.Image,
    scene: Scene,
    index: int,
    total: int,
    font_small: ImageFont.ImageFont,
    font_micro: ImageFont.ImageFont,
    brand_name: str,
    asset: VisualAsset | None,
) -> Image.Image:
    width, height = img.size
    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay, "RGBA")
    for y in range(height):
        bottom_ratio = max(0.0, (y - 1230) / max(1, height - 1230))
        mid_ratio = max(0.0, 1.0 - abs(y - 780) / 560)
        top_ratio = max(0.0, (230 - y) / 230)
        alpha = int(10 + 76 * bottom_ratio * bottom_ratio + 34 * top_ratio + 28 * mid_ratio)
        if alpha > 0:
            odraw.line((0, y, width, y), fill=(0, 0, 0, min(128, alpha)))
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    brief = asset.visual_brief if asset and isinstance(asset.visual_brief, dict) else {}
    role = str(brief.get("role") or _fallback_scene_role(index, total)).strip()
    accent = _tiktok_native_accent(role)
    top_label = _tiktok_native_role_label(role, index, total)
    draw.rectangle((0, 0, width, 8), fill=_rgba_from_hex(accent, 220))
    draw.text((TEXT_SAFE_LEFT, 70), brand_name, fill="#f7fbff", font=font_small, stroke_width=2, stroke_fill=(0, 0, 0, 180))
    draw.text(
        (TEXT_SAFE_RIGHT - 152, 74),
        f"{scene.scene_id:02d}/{total:02d}",
        fill="#eef5f8",
        font=font_micro,
        stroke_width=2,
        stroke_fill=(0, 0, 0, 160),
    )

    headline_text = _compact_card_text(
        scene.on_screen_text,
        34 if index == 0 else 28,
        keep_question=_has_question_marker(scene.on_screen_text),
    )
    body_text = _compact_card_text(
        scene.body,
        44 if index == 0 else 52,
        keep_question=_has_question_marker(scene.body),
    )
    content_left = TEXT_SAFE_LEFT + 24
    content_right = TEXT_SAFE_RIGHT - 86
    content_width = content_right - content_left

    if index == 0:
        _draw_native_caption_pill(draw, (TEXT_SAFE_LEFT, 260), top_label, font_micro, accent, fill_alpha=112)
        headline_font = _fit_font(draw, headline_text, content_width, max_lines=2, initial_size=88, min_size=58, bold=True)
        next_y = _draw_centered_native_text(
            draw,
            headline_text,
            (content_left, 430, content_right, 720),
            headline_font,
            "#ffffff",
            line_gap=4,
            max_lines=2,
            stroke_width=5,
        )
        body_font = _fit_font(draw, body_text, content_width - 48, max_lines=2, initial_size=50, min_size=40, bold=True)
        _draw_centered_native_text(
            draw,
            body_text,
            (content_left + 24, max(770, next_y + 28), content_right - 24, 955),
            body_font,
            "#ffe8ee",
            line_gap=2,
            max_lines=2,
            stroke_width=4,
            stroke_alpha=210,
        )
    elif index == total - 1:
        _draw_native_caption_pill(draw, (TEXT_SAFE_LEFT, 260), top_label, font_micro, accent, fill_alpha=118)
        headline_font = _fit_font(draw, headline_text, content_width, max_lines=2, initial_size=70, min_size=50, bold=True)
        _draw_centered_native_text(
            draw,
            headline_text,
            (content_left, 440, content_right, 680),
            headline_font,
            "#ffffff",
            line_gap=4,
            max_lines=2,
            stroke_width=5,
        )
        body_font = _fit_font(draw, body_text, content_width, max_lines=2, initial_size=48, min_size=40, bold=True)
        _draw_centered_native_text(
            draw,
            body_text,
            (content_left + 10, 800, content_right - 10, 1000),
            body_font,
            "#fff1a8",
            line_gap=2,
            max_lines=2,
            stroke_width=4,
        )
        for chip_index, chip in enumerate(_tiktok_native_cta_choice_labels()):
            chip_y = 1110 + chip_index * 110
            draw.rounded_rectangle(
                (TEXT_SAFE_LEFT + 66, chip_y, TEXT_SAFE_RIGHT - 168, chip_y + 72),
                radius=24,
                fill=(0, 0, 0, 106),
                outline=_rgba_from_hex(accent, 170),
                width=2,
            )
            draw.text(
                (TEXT_SAFE_LEFT + 104, chip_y + 18),
                chip,
                fill="#ffffff",
                font=font_small,
                stroke_width=2,
                stroke_fill=(0, 0, 0, 180),
            )
    else:
        _draw_native_caption_pill(draw, (TEXT_SAFE_LEFT, 220), top_label, font_micro, accent, fill_alpha=106)
        headline_font = _fit_font(draw, headline_text, content_width, max_lines=2, initial_size=64, min_size=44, bold=True)
        _draw_centered_native_text(
            draw,
            headline_text,
            (content_left, 390, content_right, 620),
            headline_font,
            "#ffffff",
            line_gap=2,
            max_lines=2,
            stroke_width=5,
        )
        body_font = _fit_font(draw, body_text, content_width, max_lines=2, initial_size=50, min_size=40, bold=True)
        _draw_centered_native_text(
            draw,
            body_text,
            (content_left + 4, 1058, content_right - 4, 1268),
            body_font,
            "#f7fbff",
            line_gap=2,
            max_lines=2,
            stroke_width=4,
        )

    progress_y = min(1588, TIKTOK_BOTTOM_UI_TOP - 72)
    _draw_progress_segments(draw, TEXT_SAFE_LEFT, progress_y, TEXT_SAFE_WIDTH, total, index, "#e63049")
    disclosure = str(RENDERING_STRATEGY.get("aigc_disclosure_label", ""))
    if disclosure:
        draw.text((TEXT_SAFE_LEFT, progress_y + 32), disclosure, fill="#aeb8c1", font=font_micro)
    return img


def _scene_image(
    scene: Scene,
    index: int,
    total: int,
    asset: VisualAsset | None,
    font_small: ImageFont.ImageFont,
    font_micro: ImageFont.ImageFont,
    brand_name: str,
) -> Image.Image:
    width, height = 1080, 1920
    if asset and asset.path and Path(asset.path).exists():
        img = _cover_image(_trim_letterbox(Image.open(asset.path).convert("RGB")), (width, height))
    else:
        img = Image.new("RGB", (width, height), "#091018")
    if _asset_uses_native_image_text(asset):
        return img
    if _asset_uses_cinematic_subtitle(asset):
        return _draw_cinematic_subtitle_frame(img, scene, index, total, font_small, font_micro, brand_name, asset)
    ui = _card_ui_config()
    accent_palette = [str(item) for item in ui.get("accent_palette", []) if str(item).strip()]
    accent = accent_palette[index % len(accent_palette)] if accent_palette else "#e84a5f"
    role = str((asset.visual_brief or {}).get("role") if asset else "") or _fallback_scene_role(index, total)
    issue_type = str((asset.visual_brief or {}).get("issue_type") if asset else "") or "civic_fact_check"
    role_label = str(_config_dict(ui, "role_labels").get(role) or role)
    issue_label = str(_config_dict(ui, "issue_labels").get(issue_type) or issue_type)
    layout_id = _card_layout_id(scene, index, total, role=role)
    layout = _card_layout_geometry(layout_id, index, total)

    overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
    odraw = ImageDraw.Draw(overlay, "RGBA")
    _draw_layout_scrim(odraw, layout_id, width, height)
    img = Image.alpha_composite(img.convert("RGBA"), overlay).convert("RGB")
    draw = ImageDraw.Draw(img, "RGBA")

    draw.rectangle((0, 0, width, 10), fill=accent)
    draw.text((TEXT_SAFE_LEFT, 82), str(ui.get("top_label") or brand_name), fill="#f7fbff", font=font_small)
    draw.line((TEXT_SAFE_LEFT, 128, TEXT_SAFE_LEFT + 74, 128), fill=accent, width=5)
    draw.text((TEXT_SAFE_RIGHT - 120, 82), f"{scene.scene_id:02d}/{total:02d}", fill="#eef5f8", font=font_small)
    draw.text((TEXT_SAFE_RIGHT - 176, 134), str(ui.get("source_label", "")), fill="#ced8e0", font=font_micro)

    headline_width = int(layout["headline_width"])
    body_width = int(layout["body_width"])
    headline_max_lines = int(layout["headline_max_lines"])
    body_max_lines = int(layout["body_max_lines"])
    headline_font = _fit_font(
        draw,
        scene.on_screen_text,
        headline_width,
        max_lines=headline_max_lines,
        initial_size=int(layout["headline_initial"]),
        min_size=HEADLINE_FONT_MIN,
        bold=True,
    )
    _draw_layout_panel(draw, layout, accent, ui)
    role_xy = tuple(layout["role_xy"])
    role_text = f"{role_label} / {issue_label}"
    if str(layout.get("panel_style")) in {"band", "top_split"}:
        _draw_pill(draw, role_xy, role_text, font_micro, accent, fill_alpha=134)
    else:
        draw.text(role_xy, role_text, fill="#b9c7d2", font=font_micro)
    headline_xy = tuple(layout["headline_xy"])
    y_after_headline = _draw_wrapped(
        draw,
        scene.on_screen_text,
        headline_xy,
        headline_font,
        "#ffffff",
        headline_width,
        line_gap=14,
        max_lines=headline_max_lines,
        stroke_width=3,
        stroke_fill=(0, 0, 0, 190),
    )

    body_x, body_y = tuple(layout["body_xy"])
    body_top = max(body_y, y_after_headline + 26)
    panel_bottom = min(int(layout["panel_box"][3]), CRITICAL_TEXT_BOTTOM)
    body_bottom = panel_bottom - 34
    body_style = _config_dict(ui, "body_panel")
    line_right = min(body_x + body_width, TEXT_SAFE_RIGHT - 38)
    if body_top - 18 > headline_xy[1]:
        draw.line((body_x, body_top - 18, line_right, body_top - 18), fill=(255, 255, 255, 46), width=2)
    body_font = _fit_font(
        draw,
        scene.body,
        body_width,
        max_lines=body_max_lines,
        initial_size=BODY_FONT_INITIAL,
        min_size=BODY_FONT_MIN,
        bold=False,
    )
    _draw_wrapped(
        draw,
        scene.body,
        (body_x, body_top),
        body_font,
        str(body_style.get("text", "#0f1720")),
        body_width,
        line_gap=8,
        max_lines=body_max_lines,
    )

    footer_y = int(layout["footer_y"])
    draw.text((TEXT_SAFE_LEFT, footer_y), f"{scene.duration_sec}s", fill="#d3dde4", font=font_micro)
    draw.text((TEXT_SAFE_LEFT + 92, footer_y), str(ui.get("footer_label", "")), fill="#aab7c1", font=font_micro)
    _draw_progress_segments(draw, TEXT_SAFE_LEFT, int(layout["progress_y"]), TEXT_SAFE_WIDTH, total, index, accent)
    draw.text(
        (TEXT_SAFE_LEFT, int(layout["disclosure_y"])),
        str(RENDERING_STRATEGY.get("aigc_disclosure_label", "")),
        fill="#9aa8b4",
        font=font_micro,
    )
    return img


def _rgba_from_hex(color: str, alpha: int) -> tuple[int, int, int, int]:
    try:
        red, green, blue = ImageColor.getrgb(color)[:3]
    except ValueError:
        red, green, blue = ImageColor.getrgb("#0b1119")[:3]
    return red, green, blue, max(0, min(255, alpha))


def _draw_card_panel(
    draw: ImageDraw.ImageDraw,
    box: tuple[int, int, int, int],
    *,
    fill: str,
    alpha: int,
    outline: str,
    outline_alpha: int,
) -> None:
    x0, y0, x1, y1 = box
    shadow = (x0 + 8, y0 + 10, x1 + 8, y1 + 10)
    draw.rounded_rectangle(shadow, radius=10, fill=(0, 0, 0, 46))
    draw.rounded_rectangle(box, radius=10, fill=_rgba_from_hex(fill, alpha), outline=_rgba_from_hex(outline, outline_alpha), width=2)


def _draw_pill(
    draw: ImageDraw.ImageDraw,
    xy: tuple[int, int],
    text: str,
    font: ImageFont.ImageFont,
    accent: str,
    *,
    fill_alpha: int,
) -> None:
    x, y = xy
    bbox = draw.textbbox((0, 0), text, font=font)
    w = bbox[2] - bbox[0] + 38
    h = bbox[3] - bbox[1] + 24
    draw.rounded_rectangle((x, y, x + w, y + h), radius=8, fill=(8, 14, 22, fill_alpha), outline=_rgba_from_hex(accent, 130), width=2)
    draw.text((x + 19, y + 10), text, fill="#f7fbff", font=font)


def _draw_progress_segments(
    draw: ImageDraw.ImageDraw,
    x: int,
    y: int,
    width: int,
    total: int,
    active_index: int,
    accent: str,
) -> None:
    gap = 8
    segment_count = max(1, total)
    segment_w = max(8, int((width - gap * (segment_count - 1)) / segment_count))
    for idx in range(segment_count):
        left = x + idx * (segment_w + gap)
        right = left + segment_w
        fill = _rgba_from_hex(accent, 238) if idx <= active_index else (255, 255, 255, 54)
        draw.rounded_rectangle((left, y, right, y + 18), radius=8, fill=fill)


def _fit_font(
    draw: ImageDraw.ImageDraw,
    text: str,
    max_width: int,
    *,
    max_lines: int,
    initial_size: int,
    min_size: int,
    bold: bool,
) -> ImageFont.ImageFont:
    for size in range(initial_size, min_size - 1, -2):
        font = _font(size, bold=bold)
        lines = _wrap_lines(draw, text, font, max_width)
        if len(lines) <= max_lines and not _has_orphan_line(lines):
            return font
    return _font(min_size, bold=bold)


def _cover_image(image: Image.Image, size: tuple[int, int]) -> Image.Image:
    target_w, target_h = size
    src_w, src_h = image.size
    scale = max(target_w / src_w, target_h / src_h)
    resized = image.resize((int(src_w * scale), int(src_h * scale)), Image.Resampling.LANCZOS)
    left = (resized.width - target_w) // 2
    top = (resized.height - target_h) // 2
    return resized.crop((left, top, left + target_w, top + target_h))


def _trim_letterbox(image: Image.Image) -> Image.Image:
    arr = np.asarray(image.convert("RGB"))
    height = arr.shape[0]
    luminance = arr.mean(axis=2)
    row_mean = luminance.mean(axis=1)
    row_std = luminance.std(axis=1)
    blank = ((row_mean > 235) | (row_mean < 18)) & (row_std < 18)
    content_indices = np.where(~blank)[0]
    if content_indices.size == 0:
        return image
    top = int(content_indices[0])
    bottom = int(content_indices[-1]) + 1
    if top < height * 0.04 and (height - bottom) < height * 0.04:
        return image
    top = max(0, top - 4)
    bottom = min(height, bottom + 4)
    if bottom - top < height * 0.35:
        return image
    return image.crop((0, top, image.width, bottom))


def _wrap_lines(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    for paragraph in text.split("\n"):
        if " " in paragraph:
            lines.extend(_wrap_words(draw, paragraph, font, max_width))
            continue
        lines.extend(_wrap_chars(draw, paragraph, font, max_width))
    return lines


def _wrap_words(draw: ImageDraw.ImageDraw, paragraph: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for word in paragraph.split(" "):
        if not word:
            continue
        candidate = word if not current else f"{current} {word}"
        if _text_width(draw, candidate, font) <= max_width:
            current = candidate
            continue
        if current:
            lines.append(current)
        if _text_width(draw, word, font) <= max_width:
            current = word
        else:
            split = _wrap_chars(draw, word, font, max_width)
            lines.extend(split[:-1])
            current = split[-1] if split else ""
    if current:
        lines.append(current)
    return _rebalance_orphan(lines, draw, font, max_width)


def _wrap_chars(draw: ImageDraw.ImageDraw, paragraph: str, font: ImageFont.ImageFont, max_width: int) -> list[str]:
    lines: list[str] = []
    current = ""
    for char in paragraph:
        candidate = current + char
        if _text_width(draw, candidate, font) > max_width and current:
            lines.append(current)
            current = char
        else:
            current = candidate
    if current:
        lines.append(current)
    return lines


def _rebalance_orphan(
    lines: list[str],
    draw: ImageDraw.ImageDraw,
    font: ImageFont.ImageFont,
    max_width: int,
) -> list[str]:
    if len(lines) < 2 or not _has_orphan_line(lines):
        return lines
    previous_words = lines[-2].split(" ")
    if len(previous_words) < 2:
        return lines
    moved = previous_words[-1]
    new_previous = " ".join(previous_words[:-1])
    new_last = f"{moved} {lines[-1]}"
    if new_previous and _text_width(draw, new_last, font) <= max_width:
        return [*lines[:-2], new_previous, new_last]
    return lines


def _has_orphan_line(lines: list[str]) -> bool:
    if len(lines) < 2:
        return False
    last = lines[-1].strip().strip("“”\"'.,?!…")
    return 0 < len(last) <= 2


def _text_width(draw: ImageDraw.ImageDraw, text: str, font: ImageFont.ImageFont) -> int:
    bbox = draw.textbbox((0, 0), text, font=font)
    return bbox[2] - bbox[0]


def _draw_wrapped(
    draw: ImageDraw.ImageDraw,
    text: str,
    xy: tuple[int, int],
    font: ImageFont.ImageFont,
    fill: str,
    max_width: int,
    *,
    line_gap: int,
    max_lines: int | None = None,
    stroke_width: int = 0,
    stroke_fill: str | tuple[int, int, int, int] | None = None,
) -> int:
    x, y = xy
    lines = _wrap_lines(draw, text, font, max_width)
    if max_lines is not None:
        lines = lines[:max_lines]
    for line in lines:
        draw.text((x, y), line, fill=fill, font=font, stroke_width=stroke_width, stroke_fill=stroke_fill)
        bbox = draw.textbbox((x, y), line, font=font)
        y += (bbox[3] - bbox[1]) + line_gap
    return y


def _line_block_height(
    draw: ImageDraw.ImageDraw,
    lines: list[str],
    font: ImageFont.ImageFont,
    line_gap: int,
) -> int:
    height = 0
    for index, line in enumerate(lines):
        bbox = draw.textbbox((0, 0), line, font=font)
        height += bbox[3] - bbox[1]
        if index < len(lines) - 1:
            height += line_gap
    return height


def _font_size_px(font: ImageFont.ImageFont, fallback: int) -> int:
    value = getattr(font, "size", fallback)
    try:
        return int(value)
    except (TypeError, ValueError):
        return fallback


def _scene_text_layout_check(
    scene: Scene,
    index: int,
    *,
    total: int | None = None,
    role: str | None = None,
) -> dict[str, Any]:
    probe = Image.new("RGB", (CANVAS_WIDTH, CANVAS_HEIGHT), "#000000")
    draw = ImageDraw.Draw(probe)
    total = max(index + 1, total or index + 1)
    layout_id = _card_layout_id(scene, index, total, role=role)
    layout = _card_layout_geometry(layout_id, index, total)
    headline_width = int(layout["headline_width"])
    body_width = int(layout["body_width"])
    headline_max_lines = int(layout["headline_max_lines"])
    body_max_lines = int(layout["body_max_lines"])
    headline_x, headline_y = tuple(layout["headline_xy"])
    body_x, body_y = tuple(layout["body_xy"])
    panel_bottom = min(int(layout["panel_box"][3]), CRITICAL_TEXT_BOTTOM)
    headline_font = _fit_font(
        draw,
        scene.on_screen_text,
        headline_width,
        max_lines=headline_max_lines,
        initial_size=int(layout["headline_initial"]),
        min_size=HEADLINE_FONT_MIN,
        bold=True,
    )
    headline_lines = _wrap_lines(draw, scene.on_screen_text, headline_font, headline_width)
    rendered_headline_lines = headline_lines[:headline_max_lines]
    headline_height = _line_block_height(draw, rendered_headline_lines, headline_font, 14)
    y_after_headline = headline_y + headline_height + (14 if rendered_headline_lines else 0)

    body_top = max(body_y, y_after_headline + 26)
    body_bottom = panel_bottom - 34
    body_font = _fit_font(
        draw,
        scene.body,
        body_width,
        max_lines=body_max_lines,
        initial_size=BODY_FONT_INITIAL,
        min_size=BODY_FONT_MIN,
        bold=False,
    )
    body_lines = _wrap_lines(draw, scene.body, body_font, body_width)
    rendered_body_lines = body_lines[:body_max_lines]
    body_height = _line_block_height(draw, rendered_body_lines, body_font, 8)
    headline_fits = len(headline_lines) <= headline_max_lines and headline_y + headline_height <= panel_bottom - 34
    body_fits = len(body_lines) <= body_max_lines and body_top + body_height <= body_bottom
    panel_x0, panel_y0, panel_x1, panel_y1 = layout["panel_box"]
    text_panel_coverage_pct = round(
        ((panel_x1 - panel_x0) * (panel_y1 - panel_y0)) / (CANVAS_WIDTH * CANVAS_HEIGHT) * 100,
        2,
    )
    return {
        "layout_id": layout_id,
        "panel_box": layout["panel_box"],
        "headline_box": (headline_x, headline_y, headline_x + headline_width, panel_bottom - 34),
        "body_box": (body_x, body_top, body_x + body_width, body_bottom),
        "headline_max_lines": headline_max_lines,
        "body_max_lines": body_max_lines,
        "headline_mobile_px": _scaled_mobile_px(_font_size_px(headline_font, HEADLINE_FONT_MIN)),
        "body_mobile_px": _scaled_mobile_px(_font_size_px(body_font, BODY_FONT_MIN)),
        "headline_line_count": len(headline_lines),
        "body_line_count": len(body_lines),
        "headline_fits_box": headline_fits,
        "body_fits_box": body_fits,
        "text_box_overflow": not (headline_fits and body_fits),
        "text_panel_coverage_pct": text_panel_coverage_pct,
    }


def _layout_overflow_score(layout: dict[str, Any]) -> int:
    score = 0
    if layout.get("text_box_overflow") is True:
        score += 1000
    headline_max = int(layout.get("headline_max_lines", 2))
    body_max = int(layout.get("body_max_lines", 4))
    score += max(0, int(layout.get("headline_line_count", 0)) - headline_max) * 120
    score += max(0, int(layout.get("body_line_count", 0)) - body_max) * 100
    if layout.get("headline_fits_box") is not True:
        score += 60
    if layout.get("body_fits_box") is not True:
        score += 60
    return score


def _descending_textfit_limits(original_len: int, max_limit: int, min_limit: int, step: int) -> list[int]:
    start = max(min_limit, min(original_len, max_limit))
    values = list(range(start, min_limit - 1, -step))
    if min_limit not in values:
        values.append(min_limit)
    return sorted(set(values), reverse=True)


def _fit_render_scene_text(scene: Scene, index: int, total: int, *, role: str | None = None) -> tuple[Scene, dict[str, Any]]:
    before_layout = _scene_text_layout_check(scene, index, total=total, role=role)
    original_headline = _clean_card_text(scene.on_screen_text)
    original_body = _clean_card_text(scene.body)
    headline_limits = _descending_textfit_limits(
        len(original_headline),
        34 if index == 0 else HEADLINE_TARGET_MAX_CHARS,
        HEADLINE_MIN_CHARS,
        2,
    )
    body_limits = _descending_textfit_limits(
        len(original_body),
        BODY_TEXT_MAX_CHARS_MOBILE,
        BODY_TEXT_MIN_CHARS_MOBILE,
        4,
    )
    best_scene = scene
    best_layout = before_layout
    best_score = _layout_overflow_score(before_layout)
    best_limits = {"headline": len(original_headline), "body": len(original_body)}

    for headline_limit in headline_limits:
        headline = _compact_card_text(original_headline, headline_limit, keep_question="?" in original_headline)
        for body_limit in body_limits:
            body = _compact_card_text(original_body, body_limit, keep_question="?" in original_body)
            candidate = replace(scene, on_screen_text=headline, body=body)
            layout = _scene_text_layout_check(candidate, index, total=total, role=role)
            score = _layout_overflow_score(layout)
            if score < best_score:
                best_scene = candidate
                best_layout = layout
                best_score = score
                best_limits = {"headline": headline_limit, "body": body_limit}
            if layout.get("text_box_overflow") is not True:
                return candidate, {
                    "scene_id": scene.scene_id,
                    "changed": candidate != scene,
                    "before_headline": scene.on_screen_text,
                    "after_headline": candidate.on_screen_text,
                    "before_body": scene.body,
                    "after_body": candidate.body,
                    "headline_char_limit": headline_limit,
                    "body_char_limit": body_limit,
                    "before_layout": before_layout,
                    "after_layout": layout,
                }

    return best_scene, {
        "scene_id": scene.scene_id,
        "changed": best_scene != scene,
        "before_headline": scene.on_screen_text,
        "after_headline": best_scene.on_screen_text,
        "before_body": scene.body,
        "after_body": best_scene.body,
        "headline_char_limit": best_limits["headline"],
        "body_char_limit": best_limits["body"],
        "before_layout": before_layout,
        "after_layout": best_layout,
    }


def _fit_render_scene_texts(
    scenes: list[Scene],
    assets_by_scene: dict[int, VisualAsset] | None = None,
) -> tuple[list[Scene], dict[str, Any]]:
    fitted_scenes: list[Scene] = []
    rows: list[dict[str, Any]] = []
    total = len(scenes)
    for index, scene in enumerate(scenes):
        asset = assets_by_scene.get(scene.scene_id) if assets_by_scene else None
        role = str((asset.visual_brief or {}).get("role") if asset else "") or None
        fitted_scene, row = _fit_render_scene_text(scene, index, total, role=role)
        fitted_scenes.append(fitted_scene)
        rows.append(row)
    return fitted_scenes, {
        "version": "render_textfit_v1",
        "scene_count": len(rows),
        "changed_scene_count": sum(1 for row in rows if row["changed"]),
        "all_fit": all(row["after_layout"].get("text_box_overflow") is not True for row in rows),
        "min_body_chars": min((len(row["after_body"]) for row in rows), default=0),
        "min_headline_chars": min((len(row["after_headline"]) for row in rows), default=0),
        "scenes": rows,
    }


def _fit_cinematic_subtitle_scene_texts(scenes: list[Scene]) -> tuple[list[Scene], dict[str, Any]]:
    fitted_scenes: list[Scene] = []
    rows: list[dict[str, Any]] = []
    final_scene_ids = {scene.scene_id for scene in scenes[-2:]}
    for scene in scenes:
        headline_source = _clean_card_text(scene.on_screen_text)
        subtitle_source = _clean_card_text(scene.body)
        headline = _compact_card_text(headline_source, 26, keep_question=_has_question_marker(headline_source))
        subtitle = _compact_card_text(subtitle_source, 46, keep_question=_has_question_marker(subtitle_source))
        if scene.scene_id in final_scene_ids and not _has_question_marker(f"{headline} {subtitle}"):
            subtitle = _compact_card_text(f"{subtitle} 어느 쪽이 더 설득되나요?", 46, keep_question=True)
        fitted = replace(scene, on_screen_text=headline, body=subtitle)
        fitted_scenes.append(fitted)
        rows.append(
            {
                "scene_id": scene.scene_id,
                "changed": fitted != scene,
                "before_headline": scene.on_screen_text,
                "after_headline": fitted.on_screen_text,
                "before_body": scene.body,
                "after_body": fitted.body,
                "headline_char_limit": 26,
                "body_char_limit": 46,
                "after_layout": {
                    "layout_id": CINEMATIC_SUBTITLE_RENDER_STYLE,
                    "text_box_overflow": False,
                    "headline_fits_box": True,
                    "body_fits_box": True,
                    "text_panel_coverage_pct": 6.0,
                },
            }
        )
    return fitted_scenes, {
        "version": "render_textfit_v3",
        "mode": CINEMATIC_SUBTITLE_RENDER_STYLE,
        "scene_count": len(rows),
        "changed_scene_count": sum(1 for row in rows if row["changed"]),
        "all_fit": True,
        "min_body_chars": min((len(row["after_body"]) for row in rows), default=0),
        "min_headline_chars": min((len(row["after_headline"]) for row in rows), default=0),
        "scenes": rows,
    }


def _storyboard(images: list[Image.Image], scenes: list[Scene], output: Path) -> None:
    thumb_w, thumb_h = 270, 480
    cols = 4
    rows = math.ceil(len(images) / cols)
    board = Image.new("RGB", (cols * thumb_w, rows * thumb_h), "#0b1118")
    for i, img in enumerate(images):
        thumb = img.resize((thumb_w, thumb_h))
        board.paste(thumb, ((i % cols) * thumb_w, (i // cols) * thumb_h))
    board.save(output)


def _draw_tiktok_app_overlay(image: Image.Image) -> Image.Image:
    overlay = Image.new("RGBA", image.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(overlay, "RGBA")
    right_center = CANVAS_WIDTH - 62
    for y in [860, 980, 1100, 1220, 1340]:
        draw.ellipse((right_center - 26, y - 26, right_center + 26, y + 26), fill=(255, 255, 255, 76))
        draw.ellipse((right_center - 12, y - 12, right_center + 12, y + 12), fill=(5, 8, 12, 112))
    draw.rounded_rectangle((CANVAS_WIDTH - 92, 1470, CANVAS_WIDTH - 32, 1530), radius=14, fill=(255, 255, 255, 66))
    draw.rectangle((0, TIKTOK_BOTTOM_UI_TOP, CANVAS_WIDTH, CANVAS_HEIGHT), fill=(0, 0, 0, 96))
    draw.rounded_rectangle((64, 1740, 800, 1790), radius=12, fill=(255, 255, 255, 40))
    draw.rounded_rectangle((64, 1810, 980, 1860), radius=12, fill=(255, 255, 255, 26))
    return Image.alpha_composite(image.convert("RGBA"), overlay).convert("RGB")


@lru_cache(maxsize=1)
def _korean_font_probe() -> bool:
    probe_font = _font(48, bold=True)
    sample = "한글정치뉴스"
    missing_like = "??????"
    sample_img = Image.new("L", (480, 90), 0)
    missing_img = Image.new("L", (480, 90), 0)
    sample_draw = ImageDraw.Draw(sample_img)
    missing_draw = ImageDraw.Draw(missing_img)
    sample_draw.text((10, 10), sample, fill=255, font=probe_font)
    missing_draw.text((10, 10), missing_like, fill=255, font=probe_font)
    return sample_img.tobytes() != missing_img.tobytes()


def _mobile_visual_checks(
    scenes: list[Scene],
    preview_paths: list[Path],
    assets_by_scene: dict[int, VisualAsset] | None = None,
) -> list[MobileVisualCheck]:
    text_right_rail_clear = TEXT_SAFE_RIGHT <= TIKTOK_RIGHT_RAIL_LEFT
    text_above_bottom_ui = CRITICAL_TEXT_BOTTOM <= TIKTOK_BOTTOM_UI_TOP
    text_render_passed = _korean_font_probe()
    checks: list[MobileVisualCheck] = []
    total = len(scenes)
    for index, (scene, path) in enumerate(zip(scenes, preview_paths)):
        asset = assets_by_scene.get(scene.scene_id) if assets_by_scene else None
        if _asset_uses_native_image_text(asset):
            checks.append(_native_image_text_mobile_layout(scene, path))
            continue
        if _asset_uses_cinematic_subtitle(asset):
            checks.append(_cinematic_subtitle_mobile_layout(scene, path))
            continue
        role = str((asset.visual_brief or {}).get("role") if asset else "") or None
        layout = _scene_text_layout_check(scene, index, total=total, role=role)
        headline_px = float(layout["headline_mobile_px"])
        body_px = float(layout["body_mobile_px"])
        headline_fits_box = bool(layout["headline_fits_box"])
        body_fits_box = bool(layout["body_fits_box"])
        text_box_overflow = bool(layout["text_box_overflow"])
        text_panel_coverage_pct = float(layout["text_panel_coverage_pct"])
        checks.append(
            MobileVisualCheck(
                scene_id=scene.scene_id,
                preview_path=str(path),
                layout_id=str(layout["layout_id"]),
                passed=text_right_rail_clear
                and text_above_bottom_ui
                and headline_px >= MIN_HEADLINE_PREVIEW_PX
                and body_px >= MIN_BODY_PREVIEW_PX
                and text_render_passed
                and not text_box_overflow
                and text_panel_coverage_pct <= MAX_TEXT_PANEL_COVERAGE_PCT
                and path.exists(),
                headline_mobile_px=headline_px,
                body_mobile_px=body_px,
                headline_line_count=int(layout["headline_line_count"]),
                body_line_count=int(layout["body_line_count"]),
                headline_fits_box=headline_fits_box,
                body_fits_box=body_fits_box,
                text_box_overflow=text_box_overflow,
                text_panel_coverage_pct=text_panel_coverage_pct,
                text_right_rail_clear=text_right_rail_clear,
                text_above_bottom_ui=text_above_bottom_ui,
                text_render_passed=text_render_passed,
                preview_size=f"{MOBILE_PREVIEW_WIDTH}x{MOBILE_PREVIEW_HEIGHT}",
            )
        )
    return checks


def _write_mobile_previews(
    images: list[Image.Image],
    scenes: list[Scene],
    run_dir: Path,
    assets_by_scene: dict[int, VisualAsset] | None = None,
) -> tuple[Path, Path, list[MobileVisualCheck]]:
    previews_dir = run_dir / "mobile_previews"
    previews_dir.mkdir(parents=True, exist_ok=True)
    preview_paths: list[Path] = []
    preview_images: list[Image.Image] = []
    for image, scene in zip(images, scenes):
        preview = _draw_tiktok_app_overlay(image).resize(
            (MOBILE_PREVIEW_WIDTH, MOBILE_PREVIEW_HEIGHT),
            Image.Resampling.LANCZOS,
        )
        path = previews_dir / f"scene_{scene.scene_id:02d}_tiktok_mobile.png"
        preview.save(path)
        preview_paths.append(path)
        preview_images.append(preview)

    storyboard_path = run_dir / "mobile_preview_storyboard.png"
    _storyboard(preview_images, scenes, storyboard_path)
    checks = _mobile_visual_checks(scenes, preview_paths, assets_by_scene)
    checks_path = run_dir / "mobile_visual_checks.json"
    _write_json(checks_path, [asdict(check) for check in checks])
    return storyboard_path, checks_path, checks


def _render_beat_frame(image: Image.Image, beat: VisualBeat, progress: float) -> Image.Image:
    width, height = image.size
    zoom = beat.zoom_start + (beat.zoom_end - beat.zoom_start) * progress
    if zoom <= 1.001 and beat.pan_x == 0 and beat.pan_y == 0:
        frame = image.copy()
    else:
        crop_w = int(width / zoom)
        crop_h = int(height / zoom)
        center_x = width // 2 + int(beat.pan_x * progress)
        center_y = height // 2 + int(beat.pan_y * progress)
        left = max(0, min(width - crop_w, center_x - crop_w // 2))
        top = max(0, min(height - crop_h, center_y - crop_h // 2))
        frame = image.crop((left, top, left + crop_w, top + crop_h)).resize((width, height), Image.Resampling.LANCZOS)

    if beat.overlay != "hold":
        overlay = Image.new("RGBA", (width, height), (0, 0, 0, 0))
        draw = ImageDraw.Draw(overlay, "RGBA")
        alpha = int(18 + 18 * math.sin(progress * math.pi))
        if beat.overlay == "caption_pop":
            pulse = int(26 + 30 * math.sin(progress * math.pi))
            draw.rectangle((0, 360, width, 1120), fill=(0, 0, 0, min(42, pulse)))
            draw.rectangle((TEXT_SAFE_LEFT, 338, TEXT_SAFE_LEFT + 90, 346), fill=(230, 48, 73, min(220, pulse * 5)))
        elif beat.overlay == "receipt_flash":
            pulse = int(22 + 34 * math.sin(progress * math.pi))
            draw.rounded_rectangle(
                (TEXT_SAFE_LEFT, 245, TEXT_SAFE_LEFT + 310, 304),
                radius=16,
                outline=(255, 255, 255, min(150, pulse * 4)),
                width=3,
            )
            draw.rectangle((TEXT_SAFE_LEFT, 1338, TEXT_SAFE_RIGHT - 90, 1345), fill=(230, 48, 73, min(190, pulse * 4)))
        elif beat.overlay == "hard_cut":
            draw.rectangle((0, 0, width, height), fill=(255, 255, 255, min(18, alpha)))
        elif beat.overlay == "evidence":
            draw.rectangle((70, 990, 1010, 1560), outline=(255, 255, 255, alpha), width=3)
        elif beat.overlay == "question":
            draw.rectangle((0, 0, width, height), fill=(20, 60, 80, alpha))
        else:
            draw.rectangle((0, 0, width, height), fill=(255, 255, 255, min(10, alpha)))
        frame = Image.alpha_composite(frame.convert("RGBA"), overlay).convert("RGB")
    return frame


def _ease_in_out(progress: float) -> float:
    progress = max(0.0, min(1.0, progress))
    return progress * progress * (3 - 2 * progress)


def _transition_frame(previous: Image.Image, current: Image.Image, progress: float, mode: str) -> Image.Image:
    width, height = current.size
    prev = previous.convert("RGB").resize((width, height), Image.Resampling.LANCZOS)
    nxt = current.convert("RGB")
    eased = _ease_in_out(progress)

    if mode == "wipe":
        frame = prev.copy()
        cut = max(0, min(width, int(width * eased)))
        if cut:
            frame.paste(nxt.crop((0, 0, cut, height)), (0, 0))
        line_x = max(0, min(width - 1, cut))
        draw = ImageDraw.Draw(frame, "RGBA")
        draw.rectangle((line_x, 0, min(width, line_x + 8), height), fill=(255, 255, 255, 48))
        return frame

    if mode == "push":
        offset = int(width * eased)
        frame = Image.new("RGB", (width, height), (12, 18, 24))
        frame.paste(prev, (-offset, 0))
        frame.paste(nxt, (width - offset, 0))
        return frame

    if mode == "flash":
        white = Image.new("RGB", (width, height), (245, 248, 250))
        if eased < 0.5:
            return Image.blend(prev, white, eased * 2)
        return Image.blend(white, nxt, (eased - 0.5) * 2)

    if mode == "dip":
        dark = Image.new("RGB", (width, height), (8, 12, 16))
        if eased < 0.5:
            return Image.blend(prev, dark, eased * 2)
        return Image.blend(dark, nxt, (eased - 0.5) * 2)

    return Image.blend(prev, nxt, eased)


def _allocate_frame_counts(total_frames: int, weights: list[float]) -> list[int]:
    if not weights:
        return []
    if total_frames <= 0:
        return [0 for _ in weights]

    total_weight = sum(max(0.01, weight) for weight in weights)
    counts = [max(1, int(round(total_frames * max(0.01, weight) / total_weight))) for weight in weights]
    while sum(counts) > total_frames:
        target = max(range(len(counts)), key=lambda index: counts[index])
        if counts[target] <= 1:
            break
        counts[target] -= 1
    while sum(counts) < total_frames:
        target = max(range(len(weights)), key=lambda index: weights[index])
        counts[target] += 1
    return counts


def _write_mp4(
    images: list[Image.Image],
    scenes: list[Scene],
    output: Path,
    *,
    visual_beats: list[VisualBeat] | None = None,
) -> None:
    with imageio.get_writer(
        str(output),
        fps=VIDEO_FPS,
        codec=VIDEO_CODEC,
        bitrate=VIDEO_BITRATE,
        quality=7,
        pixelformat="yuv420p",
        macro_block_size=1,
        output_params=["-movflags", "+faststart"],
    ) as writer:
        previous_image: Image.Image | None = None
        transition_modes = ["wipe", "push", "flash", "dip", "crossfade"]
        for scene_index, (img, scene) in enumerate(zip(images, scenes)):
            scene_beats = _beats_for_scene(visual_beats or [], scene.scene_id, scene.duration_sec)
            scene_frame_count = max(1, int(round(scene.duration_sec * VIDEO_FPS)))
            transition_count = 0
            if previous_image is not None:
                transition_count = min(
                    max(1, int(round(0.5 * VIDEO_FPS))),
                    max(0, scene_frame_count // 4),
                )
                mode = transition_modes[scene_index % len(transition_modes)]
                for frame_index in range(transition_count):
                    progress = (frame_index + 1) / max(1, transition_count)
                    writer.append_data(np.asarray(_transition_frame(previous_image, img, progress, mode)))

            beat_frame_budget = max(1, scene_frame_count - transition_count)
            beat_counts = _allocate_frame_counts(beat_frame_budget, [beat.duration_sec for beat in scene_beats])
            for beat, frame_count in zip(scene_beats, beat_counts):
                if frame_count <= 0:
                    continue
                for frame_index in range(frame_count):
                    progress = frame_index / max(1, frame_count - 1)
                    writer.append_data(np.asarray(_render_beat_frame(img, beat, progress)))
            previous_image = img


def _write_tts_audio(text: str, run_dir: Path, scenes: list[Scene] | None = None) -> AudioAsset:
    _load_env_files()
    if scenes and _env_bool("AINO_SCENE_AUDIO_SYNC", True):
        return _write_scene_synced_tts_audio(scenes, run_dir)

    notes: list[str] = []
    run_dir.mkdir(parents=True, exist_ok=True)
    tts_preprocess = _preprocess_korean_tts(text)
    tts_text = tts_preprocess.text
    tts_text_path = run_dir / "narration_tts_ko.txt"
    lint_path = run_dir / "narration_tts_lint.json"
    tts_text_path.write_text(tts_text + "\n", encoding="utf-8")
    _write_json(lint_path, asdict(tts_preprocess))
    if tts_text != text:
        notes.append("tts text normalized for Korean pronunciation")
    if tts_preprocess.replacements:
        notes.append("tts replacements: " + ", ".join(tts_preprocess.replacements[:12]))
    if tts_preprocess.warnings:
        notes.append("tts lint warnings: " + ", ".join(tts_preprocess.warnings[:8]))
    local_only = privacy_policy.is_local_only()
    eleven_key = _env_value("ELEVENLABS_API_KEY", "XI_API_KEY")
    voice_id = _env_value("ELEVENLABS_VOICE_ID", "XI_VOICE_ID")
    elevenlabs_disabled = _elevenlabs_tts_disabled()
    if eleven_key and voice_id and not local_only and not elevenlabs_disabled:
        output = run_dir / "narration_elevenlabs.mp3"
        ok, provider_notes = _write_elevenlabs_tts(tts_text, output, eleven_key, voice_id)
        notes.extend(provider_notes)
        if ok:
            return AudioAsset(
                provider="elevenlabs",
                status="generated",
                path=str(output),
                notes=notes,
                tts_text_path=str(tts_text_path),
                lint_path=str(lint_path),
            )
    else:
        missing = []
        if local_only:
            notes.append("elevenlabs skipped: local_only privacy mode")
        elif elevenlabs_disabled:
            notes.append("elevenlabs skipped: disabled by AINO_DISABLE_ELEVENLABS_TTS")
        else:
            if not eleven_key:
                missing.append("ELEVENLABS_API_KEY")
            if not voice_id:
                missing.append("ELEVENLABS_VOICE_ID")
            notes.append("elevenlabs skipped: " + ", ".join(missing) + " unavailable")

    output = run_dir / "narration_ko_kr_preview.wav"
    _write_windows_tts_wav(tts_text, output)
    notes.append("windows_system_speech fallback used for preview only; blocks upload_ready")
    return AudioAsset(
        provider="windows_system_speech",
        status="fallback",
        path=str(output),
        notes=notes,
        tts_text_path=str(tts_text_path),
        lint_path=str(lint_path),
    )


def _scene_card_duration(audio_duration_sec: float, original_duration_sec: int) -> int:
    del original_duration_sec
    return max(7, math.ceil(audio_duration_sec + 0.55))


def _media_duration_sec(path: Path) -> float:
    ffmpeg = _ffmpeg_executable()
    proc = subprocess.run(
        [ffmpeg, "-hide_banner", "-i", str(path)],
        capture_output=True,
        text=True,
        timeout=60,
    )
    text = proc.stderr + proc.stdout
    match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", text)
    if not match:
        raise RuntimeError(f"could not read media duration: {path}")
    hours = int(match.group(1))
    minutes = int(match.group(2))
    seconds = float(match.group(3))
    return hours * 3600 + minutes * 60 + seconds


def _pad_audio_to_duration(input_path: Path, output_path: Path, duration_sec: int) -> None:
    ffmpeg = _ffmpeg_executable()
    output_path.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(input_path),
        "-af",
        f"apad=pad_dur={duration_sec}",
        "-t",
        f"{duration_sec:.3f}",
        "-ar",
        "44100",
        "-ac",
        "1",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)


def _concat_audio_segments(segment_paths: list[Path], output_path: Path, list_path: Path) -> None:
    ffmpeg = _ffmpeg_executable()
    list_path.parent.mkdir(parents=True, exist_ok=True)
    lines = []
    for segment in segment_paths:
        safe_path = segment.resolve().as_posix().replace("'", "'\\''")
        lines.append(f"file '{safe_path}'")
    list_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    cmd = [
        ffmpeg,
        "-y",
        "-f",
        "concat",
        "-safe",
        "0",
        "-i",
        str(list_path),
        "-ar",
        "44100",
        "-ac",
        "1",
        str(output_path),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=180)


def _write_scene_synced_tts_audio(scenes: list[Scene], run_dir: Path) -> AudioAsset:
    notes: list[str] = ["scene audio sync enabled"]
    run_dir.mkdir(parents=True, exist_ok=True)
    scene_audio_dir = run_dir / "scene_audio"
    scene_tts_dir = run_dir / "scene_tts_text"
    padded_dir = run_dir / "scene_audio_padded"
    scene_audio_dir.mkdir(parents=True, exist_ok=True)
    scene_tts_dir.mkdir(parents=True, exist_ok=True)
    padded_dir.mkdir(parents=True, exist_ok=True)

    local_only = privacy_policy.is_local_only()
    if local_only:
        notes.append("local_only privacy mode: ElevenLabs disabled")
    eleven_key = _env_value("ELEVENLABS_API_KEY", "XI_API_KEY")
    voice_id = _env_value("ELEVENLABS_VOICE_ID", "XI_VOICE_ID")
    elevenlabs_disabled = _elevenlabs_tts_disabled()
    if elevenlabs_disabled:
        notes.append("ElevenLabs disabled by AINO_DISABLE_ELEVENLABS_TTS")
    can_use_elevenlabs = bool(eleven_key and voice_id and not local_only and not elevenlabs_disabled)
    all_elevenlabs = can_use_elevenlabs
    timings: list[SceneAudioTiming] = []
    padded_paths: list[Path] = []
    combined_text_blocks: list[str] = []
    combined_lint = {
        "mode": "scene_audio_sync",
        "scenes": [],
        "warnings": [],
        "metrics": {
            "latin_term_count": 0,
            "digit_count": 0,
            "risky_symbol_count": 0,
            "long_sentence_count": 0,
        },
    }

    for scene in scenes:
        preprocess = _preprocess_korean_tts(scene.body)
        scene_text_path = scene_tts_dir / f"scene_{scene.scene_id:02d}.txt"
        scene_lint_path = scene_tts_dir / f"scene_{scene.scene_id:02d}_lint.json"
        scene_text_path.write_text(preprocess.text + "\n", encoding="utf-8")
        _write_json(scene_lint_path, asdict(preprocess))
        combined_text_blocks.append(f"[{scene.scene_id:02d}] {preprocess.text}")
        combined_lint["scenes"].append({"scene_id": scene.scene_id, **asdict(preprocess)})
        for key in combined_lint["metrics"]:
            combined_lint["metrics"][key] += int(preprocess.metrics.get(key, 0))
        if preprocess.warnings:
            combined_lint["warnings"].extend(f"scene_{scene.scene_id:02d}:{warning}" for warning in preprocess.warnings)

        scene_notes: list[str] = []
        if preprocess.replacements:
            scene_notes.append("tts replacements: " + ", ".join(preprocess.replacements[:8]))
        if preprocess.warnings:
            scene_notes.append("tts lint warnings: " + ", ".join(preprocess.warnings[:4]))

        if can_use_elevenlabs:
            scene_audio_path = scene_audio_dir / f"scene_{scene.scene_id:02d}.mp3"
            ok, provider_notes = _write_elevenlabs_tts(
                preprocess.text,
                scene_audio_path,
                eleven_key,
                voice_id,
                stable_history_check=False,
            )
            scene_notes.extend(provider_notes)
            if ok:
                provider = "elevenlabs"
                status = "generated"
            else:
                all_elevenlabs = False
                provider = "windows_system_speech"
                status = "fallback"
                scene_audio_path = scene_audio_dir / f"scene_{scene.scene_id:02d}.wav"
                _write_windows_tts_wav(preprocess.text, scene_audio_path)
                scene_notes.append("scene fallback used after ElevenLabs failure")
        else:
            all_elevenlabs = False
            provider = "windows_system_speech"
            status = "fallback"
            scene_audio_path = scene_audio_dir / f"scene_{scene.scene_id:02d}.wav"
            _write_windows_tts_wav(preprocess.text, scene_audio_path)
            if local_only:
                scene_notes.append("elevenlabs skipped for scene audio sync: local_only privacy mode")
            elif elevenlabs_disabled:
                scene_notes.append("elevenlabs skipped for scene audio sync: disabled by AINO_DISABLE_ELEVENLABS_TTS")
            else:
                scene_notes.append("elevenlabs skipped for scene audio sync")

        audio_duration = _media_duration_sec(scene_audio_path)
        card_duration = _scene_card_duration(audio_duration, scene.duration_sec)
        silence_pad = max(0.0, card_duration - audio_duration)
        padded_path = padded_dir / f"scene_{scene.scene_id:02d}.wav"
        _pad_audio_to_duration(scene_audio_path, padded_path, card_duration)
        padded_paths.append(padded_path)
        timings.append(
            SceneAudioTiming(
                scene_id=scene.scene_id,
                original_duration_sec=scene.duration_sec,
                audio_duration_sec=round(audio_duration, 3),
                card_duration_sec=card_duration,
                silence_pad_sec=round(silence_pad, 3),
                audio_path=str(scene_audio_path),
                padded_audio_path=str(padded_path),
                tts_text_path=str(scene_text_path),
                lint_path=str(scene_lint_path),
                provider=provider,
                status=status,
                notes=scene_notes,
            )
        )

    combined_audio_path = run_dir / "narration_scene_synced.wav"
    concat_list_path = run_dir / "scene_audio_concat.txt"
    _concat_audio_segments(padded_paths, combined_audio_path, concat_list_path)
    combined_tts_text_path = run_dir / "narration_tts_ko.txt"
    combined_lint_path = run_dir / "narration_tts_lint.json"
    combined_tts_text_path.write_text("\n\n".join(combined_text_blocks) + "\n", encoding="utf-8")
    combined_lint["scene_timings"] = [asdict(timing) for timing in timings]
    combined_lint["total_card_duration_sec"] = sum(timing.card_duration_sec for timing in timings)
    combined_lint["total_audio_duration_sec"] = round(sum(timing.audio_duration_sec for timing in timings), 3)
    _write_json(combined_lint_path, combined_lint)

    total_duration = sum(timing.card_duration_sec for timing in timings)
    notes.append(f"scene audio sync total duration: {total_duration}s")
    notes.append(
        "scene card durations: "
        + ", ".join(f"{timing.scene_id}:{timing.card_duration_sec}s" for timing in timings)
    )
    if combined_lint["warnings"]:
        notes.append("scene tts lint warnings: " + ", ".join(combined_lint["warnings"][:8]))
    if can_use_elevenlabs and _elevenlabs_zero_retention_requested():
        notes.append(_elevenlabs_history_note(_elevenlabs_scrub_history_until_clear(eleven_key), final=True))

    return AudioAsset(
        provider="elevenlabs" if all_elevenlabs else "scene_audio_preview",
        status="generated" if all_elevenlabs else "fallback",
        path=str(combined_audio_path),
        notes=notes,
        tts_text_path=str(combined_tts_text_path),
        lint_path=str(combined_lint_path),
        scene_timings=[asdict(timing) for timing in timings],
    )


def _write_elevenlabs_tts(
    text: str,
    output: Path,
    api_key: str,
    voice_id: str,
    *,
    stable_history_check: bool = True,
) -> tuple[bool, list[str]]:
    model_id = _env_value("ELEVENLABS_MODEL_ID") or "eleven_multilingual_v2"
    output_format = _env_value("ELEVENLABS_OUTPUT_FORMAT") or "mp3_44100_128"
    language_code = _env_value("ELEVENLABS_LANGUAGE_CODE") or "ko"
    enable_logging = _elevenlabs_enable_logging()
    voice_settings: dict[str, float | bool] = {
        "stability": _env_float_ratio("ELEVENLABS_STABILITY", 0.12),
        "similarity_boost": _env_float_ratio("ELEVENLABS_SIMILARITY_BOOST", 0.18),
        "speed": _env_float("ELEVENLABS_SPEED", 1.09, min_value=0.7, max_value=1.2),
    }
    if _model_supports_style_settings(model_id):
        voice_settings["style"] = _env_float_ratio("ELEVENLABS_STYLE", 0.07)
        voice_settings["use_speaker_boost"] = _env_bool("ELEVENLABS_USE_SPEAKER_BOOST", True)

    payload = {
        "text": text,
        "model_id": model_id,
        "language_code": language_code,
        "voice_settings": voice_settings,
        "apply_text_normalization": "auto",
    }
    query = urlencode({"output_format": output_format, "enable_logging": str(enable_logging).lower()})
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}?{query}"
    try:
        import requests

        response = requests.post(
            url,
            headers={
                "xi-api-key": api_key,
                "Content-Type": "application/json",
                "Accept": "audio/mpeg",
            },
            json=payload,
            timeout=180,
        )
    except Exception as exc:
        return False, [f"elevenlabs failed to start: {exc}"]
    if response.status_code >= 400:
        detail = response.text.replace("\n", " ")[:260]
        if not enable_logging:
            detail = f"{detail} zero-retention requested; not retrying with logging enabled"
        return False, [f"elevenlabs failed: HTTP {response.status_code} {detail}"]
    output.write_bytes(response.content)
    if output.exists() and output.stat().st_size > 10_000:
        retention_note = "zero_retention" if not enable_logging else "history_enabled"
        voice_name = _env_value("ELEVENLABS_VOICE_NAME") or "configured_voice"
        notes = [f"elevenlabs generated audio with {voice_name}/{model_id}/{output_format}/{retention_note}"]
        if not enable_logging:
            audit = _elevenlabs_scrub_history_until_clear(api_key) if stable_history_check else _elevenlabs_scrub_history(api_key)
            notes.append(_elevenlabs_history_note(audit, final=stable_history_check))
        return True, notes
    return False, ["elevenlabs produced an invalid or empty audio file"]


def _write_windows_tts_wav(text: str, output: Path) -> None:
    env = os.environ.copy()
    env["AINO_TTS_TEXT"] = text
    env["AINO_TTS_OUT"] = str(output)
    command = r"""
$ErrorActionPreference = 'Stop'
Add-Type -AssemblyName System.Speech
$s = New-Object System.Speech.Synthesis.SpeechSynthesizer
$voice = $s.GetInstalledVoices() | Where-Object { $_.VoiceInfo.Culture.Name -eq 'ko-KR' } | Select-Object -First 1
if ($voice) { $s.SelectVoice($voice.VoiceInfo.Name) }
$s.Rate = 0
$s.Volume = 95
$s.SetOutputToWaveFile($env:AINO_TTS_OUT)
$s.Speak($env:AINO_TTS_TEXT)
$s.Dispose()
"""
    try:
        subprocess.run(
            ["powershell", "-NoProfile", "-Command", command],
            check=True,
            env=env,
            capture_output=True,
            text=True,
            timeout=120,
        )
    except Exception as exc:
        raise RuntimeError(f"failed to synthesize Korean narration: {exc}") from exc


def _mux_audio(video_path: Path, audio_path: Path, output: Path, duration_sec: int) -> None:
    ffmpeg = _ffmpeg_executable()
    cmd = [
        ffmpeg,
        "-y",
        "-i",
        str(video_path),
        "-i",
        str(audio_path),
        "-map",
        "0:v:0",
        "-map",
        "1:a:0",
        "-c:v",
        "copy",
        "-c:a",
        "aac",
        "-t",
        str(duration_sec),
        str(output),
    ]
    subprocess.run(cmd, check=True, capture_output=True, text=True, timeout=120)


def _ffmpeg_executable() -> str:
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg

        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as exc:
        raise RuntimeError("ffmpeg executable not found") from exc


def _write_report(
    path: Path,
    topic: TopicCandidate,
    script: ScriptPackage,
    gate: GateResult,
    readability: ReadabilityResult,
    quality: PublishQualityResult,
    review: ContentReview,
    visual_assets: list[VisualAsset],
    visual_quality: VisualQualityResult,
    audio_asset: AudioAsset,
    sources: list[dict[str, str]],
    mp4_path: Path,
    storyboard_path: Path,
    mobile_storyboard_path: Path,
    manifest_path: Path,
    render_scenes: list[Scene],
    signal_snapshot_path: Path | None,
    selected_script_path: Path,
    fact_pack_path: Path,
    angle_brief_path: Path,
    storyboard_brief_path: Path,
    content_plan_path: Path,
    visual_plan_path: Path,
    tts_performance_plan_path: Path,
    tts_plan_path: Path,
    render_manifest_path: Path,
    upload_plan_path: Path,
    keyword_plan_path: Path | None,
    topic_plan_path: Path | None,
    deep_research_report_path: Path | None,
    editorial_plan_path: Path | None,
) -> None:
    render_duration_sec = sum(scene.duration_sec for scene in render_scenes)
    checks = "\n".join(
        f"<li class='{ 'pass' if ok else 'fail' }'>{html.escape(name)}: {ok}</li>"
        for name, ok in gate.checks.items()
    )
    review_scores = "\n".join(
        f"<li>{html.escape(name)}: <strong>{score}/100</strong></li>"
        for name, score in review.scores.items()
    )
    readability_checks = "\n".join(
        f"<li class='{ 'pass' if ok else 'fail' }'>{html.escape(name)}: {ok}</li>"
        for name, ok in readability.checks.items()
    )
    quality_scores = "\n".join(
        f"<li>{html.escape(name)}: <strong>{score}/100</strong></li>"
        for name, score in quality.scores.items()
    )
    visual_quality_scores = "\n".join(
        f"<li class='{ 'pass' if score >= 80 else 'fail' }'>{html.escape(name)}: <strong>{score}/100</strong></li>"
        for name, score in visual_quality.scores.items()
    )
    variant_scores = "\n".join(
        f"<tr><td>{html.escape(row['variant_id'])}</td><td>{row['publish_ready_score']}</td><td>{html.escape(', '.join(row['blockers']) or 'pass')}</td></tr>"
        for row in quality.variant_scores
    )
    asset_rows = "\n".join(
        "<tr>"
        f"<td>{asset.scene_id}</td>"
        f"<td>{html.escape(asset.provider)}</td>"
        f"<td>{html.escape(asset.status)}</td>"
        f"<td>{html.escape(str(asset.visual_brief.get('role', '')))}</td>"
        f"<td>{html.escape(str(asset.visual_brief.get('issue_type', '')))}</td>"
        f"<td>{html.escape(str(asset.visual_quality.get('score', '')))}</td>"
        f"<td>{html.escape('; '.join(asset.notes))}</td>"
        "</tr>"
        for asset in visual_assets
    )
    audio_notes = "; ".join(audio_asset.notes)
    tts_links = ""
    if audio_asset.tts_text_path:
        tts_links += f"<p>TTS text: <code>{html.escape(audio_asset.tts_text_path)}</code></p>"
    if audio_asset.lint_path:
        tts_links += f"<p>TTS lint: <code>{html.escape(audio_asset.lint_path)}</code></p>"
    scenes = "\n".join(
        f"<tr><td>{s.scene_id}</td><td>{s.duration_sec}s</td><td>{html.escape(s.title)}</td><td>{html.escape(s.on_screen_text)}</td></tr>"
        for s in render_scenes
    )
    source_items = "\n".join(
        f"<li><a href='{html.escape(src['url'])}'>{html.escape(src['title'])}</a><p>{html.escape(src['note'])}</p></li>"
        for src in sources
    )
    signal_snapshot_line = (
        f"<p>Signal snapshot: <code>{html.escape(str(signal_snapshot_path))}</code></p>"
        if signal_snapshot_path
        else ""
    )
    selected_script_line = f"<p>Selected script: <code>{html.escape(str(selected_script_path))}</code></p>"
    fact_pack_line = f"<p>Fact pack: <code>{html.escape(str(fact_pack_path))}</code></p>"
    angle_brief_line = f"<p>Angle brief: <code>{html.escape(str(angle_brief_path))}</code></p>"
    storyboard_brief_line = f"<p>Storyboard brief: <code>{html.escape(str(storyboard_brief_path))}</code></p>"
    content_plan_line = f"<p>Content plan: <code>{html.escape(str(content_plan_path))}</code></p>"
    visual_plan_line = f"<p>Visual plan: <code>{html.escape(str(visual_plan_path))}</code></p>"
    tts_performance_plan_line = f"<p>TTS performance plan: <code>{html.escape(str(tts_performance_plan_path))}</code></p>"
    tts_plan_line = f"<p>TTS plan: <code>{html.escape(str(tts_plan_path))}</code></p>"
    render_manifest_line = f"<p>Render manifest: <code>{html.escape(str(render_manifest_path))}</code></p>"
    upload_plan_line = f"<p>Upload plan: <code>{html.escape(str(upload_plan_path))}</code></p>"
    keyword_plan_line = (
        f"<p>Keyword plan: <code>{html.escape(str(keyword_plan_path))}</code></p>"
        if keyword_plan_path
        else ""
    )
    topic_plan_line = (
        f"<p>Topic plan: <code>{html.escape(str(topic_plan_path))}</code></p>"
        if topic_plan_path
        else ""
    )
    deep_research_report_line = (
        f"<p>Deep research report: <code>{html.escape(str(deep_research_report_path))}</code></p>"
        if deep_research_report_path
        else ""
    )
    editorial_plan_line = (
        f"<p>Editorial plan: <code>{html.escape(str(editorial_plan_path))}</code></p>"
        if editorial_plan_path
        else ""
    )
    doc = f"""<!doctype html>
<html lang="ko">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <link rel="icon" href="data:," />
  <title>{html.escape(script.title)} · TikTok AiNo Verification</title>
  <style>
    body {{ margin: 0; font-family: "NanumSquare Neo", "Noto Sans KR", "Malgun Gothic", system-ui, sans-serif; background: #0a0d10; color: #edf2f7; }}
    main {{ max-width: 1180px; margin: 0 auto; padding: 28px; }}
    h1 {{ font-size: 34px; margin: 0 0 8px; }}
    h2 {{ margin-top: 34px; }}
    .grid {{ display: grid; grid-template-columns: 390px 1fr; gap: 28px; align-items: start; }}
    video {{ width: 390px; max-height: 694px; background: #000; border: 1px solid #2f3944; }}
    img {{ width: 100%; border: 1px solid #2f3944; }}
    .panel {{ background: #111820; border: 1px solid #2b3743; border-radius: 8px; padding: 18px; }}
    .pass {{ color: #7ff0aa; }}
    .fail {{ color: #ff7189; }}
    table {{ width: 100%; border-collapse: collapse; }}
    td, th {{ border-bottom: 1px solid #26394d; padding: 10px; vertical-align: top; }}
    code {{ color: #f6c85f; }}
  </style>
</head>
<body>
<main>
  <h1>{html.escape(script.title)}</h1>
  <p>상태: <strong class="{ 'pass' if gate.passed else 'fail' }">{'POLICY PASSED' if gate.passed else 'POLICY BLOCKED'}</strong> · 점수 {gate.score}/100 · 렌더 길이 {render_duration_sec}s</p>
  <section class="grid">
    <div class="panel">
      <video controls src="{mp4_path.name}"></video>
      <p><code>{html.escape(str(mp4_path))}</code></p>
    </div>
    <div class="panel">
      <h2>Caption</h2>
      <p>{html.escape(script.caption)}</p>
      <h2>Post Package</h2>
      <p><strong>{html.escape(script.post_title)}</strong><br>{html.escape(script.post_body)}</p>
      <p><strong>고정 댓글</strong><br>{html.escape(script.pinned_comment)}</p>
      <h2>Policy Checks</h2>
      <ul>{checks}</ul>
      <h2>Readability</h2>
      <p class="{ 'pass' if readability.passed else 'fail' }">max screen {readability.max_on_screen_chars} chars · max narration {readability.max_narration_chars} chars</p>
      <ul>{readability_checks}</ul>
      <h2>Publish Quality</h2>
      <p class="{ 'pass' if quality.passed else 'fail' }">
        {html.escape(quality.selected_variant)} · {quality.publish_ready_score}/100 · {'PUBLISH READY' if quality.passed else 'HOLD'}
      </p>
      <ul>{quality_scores}</ul>
      <h2>Visual Quality</h2>
      <p class="{ 'pass' if visual_quality.passed else 'fail' }">
        {'PASS' if visual_quality.passed else 'HOLD'} · {html.escape(', '.join(visual_quality.blockers) or 'no blockers')}
      </p>
      <ul>{visual_quality_scores}</ul>
      <h2>Editorial Review</h2>
      <p><strong>{html.escape(review.recommendation)}</strong></p>
      <ul>{review_scores}</ul>
      <h2>Audio</h2>
      <p class="{ 'pass' if audio_asset.provider == 'elevenlabs' and audio_asset.status == 'generated' else 'fail' }">
        {html.escape(audio_asset.provider)} · {html.escape(audio_asset.status)}
      </p>
      <p>{html.escape(audio_notes)}</p>
      {tts_links}
      <h2>Warnings</h2>
      <ul>{''.join(f'<li>{html.escape(w)}</li>' for w in gate.warnings) or '<li>none</li>'}</ul>
      <h2>Review Notes</h2>
      <ul>{''.join(f'<li>{html.escape(w)}</li>' for w in (review.blockers + review.notes)) or '<li>none</li>'}</ul>
    </div>
  </section>
  <h2>Storyboard</h2>
  <img src="{storyboard_path.name}" alt="storyboard" />
  <h2>TikTok Mobile Overlay Preview</h2>
  <img src="{mobile_storyboard_path.name}" alt="mobile overlay storyboard" />
  <h2>Visual Assets</h2>
  <table><thead><tr><th>#</th><th>provider</th><th>status</th><th>role</th><th>issue</th><th>score</th><th>notes</th></tr></thead><tbody>{asset_rows}</tbody></table>
  <h2>Variant Scores</h2>
  <table><thead><tr><th>variant</th><th>score</th><th>blockers</th></tr></thead><tbody>{variant_scores}</tbody></table>
  <h2>Scenes</h2>
  <table><thead><tr><th>#</th><th>길이</th><th>역할</th><th>화면 문구</th></tr></thead><tbody>{scenes}</tbody></table>
  <h2>Sources</h2>
  <ul>{source_items}</ul>
  {signal_snapshot_line}
  {keyword_plan_line}
  {topic_plan_line}
  {deep_research_report_line}
  {editorial_plan_line}
  {selected_script_line}
  {fact_pack_line}
  {angle_brief_line}
  {storyboard_brief_line}
  {content_plan_line}
  {visual_plan_line}
  {tts_performance_plan_line}
  {tts_plan_line}
  {render_manifest_line}
  {upload_plan_line}
  <p>Manifest: <code>{html.escape(str(manifest_path))}</code></p>
</main>
</body>
</html>"""
    path.write_text(doc, encoding="utf-8")


def run_once(
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    *,
    image_mode: str = "auto",
    real_image_limit: int | None = None,
    content_format: str = "auto",
    topic_mode: str = "static",
) -> PipelineResult:
    if topic_mode not in {"static", "hot"}:
        raise ValueError(f"unknown topic mode: {topic_mode}")

    style = _load_json(PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    sources = load_sources()
    topic_discovery: dict[str, Any] = {"mode": "static_reference", "reason": "explicit_static_topic_mode"}
    if topic_mode == "hot":
        topic, dynamic_sources, topic_discovery = discover_hot_topic(style)
        sources.update(dynamic_sources)
    else:
        topic = collect_topic(style)
    return run_for_topic(
        topic,
        sources,
        output_dir=output_dir,
        image_mode=image_mode,
        real_image_limit=real_image_limit,
        content_format=content_format,
        topic_discovery=topic_discovery,
    )


def run_for_topic(
    topic: TopicCandidate,
    sources: dict[str, Source],
    *,
    output_dir: Path = DEFAULT_OUTPUT_DIR,
    image_mode: str = "auto",
    real_image_limit: int | None = None,
    content_format: str = "auto",
    topic_discovery: dict[str, Any] | None = None,
    planned_publish_at_local: str | None = None,
    script_override: ScriptPackage | None = None,
    visual_assets_override: list[VisualAsset] | None = None,
) -> PipelineResult:
    style = _load_json(PACKAGE_DIR / "account" / "leftaino_style_guide.json")
    performance_feedback = (
        topic_discovery.get("performance_feedback")
        if isinstance(topic_discovery, dict) and isinstance(topic_discovery.get("performance_feedback"), dict)
        else None
    )
    format_plan = route_content_format(topic, content_format, performance_feedback=performance_feedback)
    editorial_plan = build_editorial_plan(topic, sources, format_plan, topic_discovery)
    fact_pack = build_fact_pack(topic, sources, format_plan, topic_discovery)
    risk_flags = build_risk_flags(topic, fact_pack, format_plan)
    source_card = build_source_card(topic, sources, fact_pack)
    reference_fit = build_reference_fit(topic, format_plan, fact_pack, source_card)
    angle_brief = build_angle_brief(topic, fact_pack, editorial_plan, format_plan, topic_discovery)
    enriched_topic_discovery = {
        **(topic_discovery or {}),
        "fact_pack": asdict(fact_pack),
        "risk_flags": asdict(risk_flags),
        "source_card": asdict(source_card),
        "reference_fit": asdict(reference_fit),
        "angle_brief": asdict(angle_brief),
    }
    if script_override is not None:
        variants = [_enrich_post_metadata(script_override, topic, sources, preserve_existing=True)]
    else:
        variants = [
            apply_reference_content_design(
                apply_content_format(script, format_plan, topic=topic, sources=sources),
                topic,
                sources,
                format_plan,
                reference_fit,
                source_card,
                fact_pack,
                angle_brief,
            )
            for script in generate_script_variants(topic, style, topic_discovery=enriched_topic_discovery)
        ]
    script, gate, readability, quality = select_publish_script(
        variants,
        topic,
        sources,
        format_plan,
        preserve_existing_metadata=script_override is not None,
    )
    visual_cadence_plan = plan_visual_cadence(script.scenes, format_plan)
    storyboard_brief = build_storyboard_brief(topic, script, fact_pack, angle_brief, format_plan)
    quality = _quality_with_workflow_gates(
        quality,
        fact_pack,
        risk_flags,
        source_card,
        reference_fit,
        angle_brief,
        storyboard_brief,
    )
    enriched_topic_discovery["storyboard_brief"] = asdict(storyboard_brief)
    enriched_topic_discovery["visual_cadence_plan"] = asdict(visual_cadence_plan)

    run_id_base = dt.datetime.now().strftime("leftaino_%Y%m%d_%H%M%S")
    run_id = run_id_base
    run_dir = output_dir / run_id
    suffix = 1
    while run_dir.exists():
        run_id = f"{run_id_base}_{suffix:02d}"
        run_dir = output_dir / run_id
        suffix += 1
    if visual_assets_override is not None:
        image_budget_decision = ImageBudgetDecision(
            version=str(IMAGE_BUDGET_STRATEGY.get("version", "image_budget_v1")),
            requested_image_mode=image_mode,
            effective_image_mode="reused",
            requested_real_image_limit=max(
                0,
                int(visual_cadence_plan.target_master_images if real_image_limit is None else real_image_limit),
            ),
            effective_real_image_limit=0,
            allowed_external_generation=False,
            reasons=["visual_assets_reused"],
            daily_real_image_limit=_strategy_int(IMAGE_BUDGET_STRATEGY, "daily_real_image_limit", 48),
            daily_real_images_used=_generated_paid_images_used_on_day(output_dir),
            min_publish_ready_score=_strategy_int(IMAGE_BUDGET_STRATEGY, "min_publish_ready_score", 85),
            gate_passed=gate.passed,
            readability_passed=readability.passed,
            quality_passed=quality.passed,
            publish_ready_score=quality.publish_ready_score,
        )
        visual_assets = visual_assets_override
    else:
        image_budget_decision = decide_image_budget(
            output_dir=output_dir,
            image_mode=image_mode,
            real_image_limit=real_image_limit,
            gate=gate,
            readability=readability,
            quality=quality,
            adaptive_default_limit=visual_cadence_plan.target_master_images,
        )
        visual_assets = _generate_visual_assets(
            topic,
            script.scenes,
            run_dir / "visual_assets",
            image_mode=image_budget_decision.effective_image_mode,
            real_image_limit=image_budget_decision.effective_real_image_limit,
        )
    visual_quality = check_visual_quality(visual_assets, script.scenes)
    review = review_content(script, gate, readability, visual_assets, format_plan, visual_quality=visual_quality)
    artifacts = render_artifacts(
        run_dir=run_dir,
        run_id=run_id,
        topic=topic,
        script=script,
        gate=gate,
        readability=readability,
        quality=quality,
        review=review,
        visual_assets=visual_assets,
        sources=sources,
        brand_name=style.get("display_name", "올바른 AiNo"),
        format_plan=format_plan,
        visual_quality=visual_quality,
        fact_pack=fact_pack,
        risk_flags=risk_flags,
        source_card=source_card,
        reference_fit=reference_fit,
        angle_brief=angle_brief,
        storyboard_brief=storyboard_brief,
        topic_discovery=enriched_topic_discovery,
        editorial_plan=editorial_plan,
        planned_publish_at_local=planned_publish_at_local,
        image_budget_decision=image_budget_decision,
    )
    manifest_status = json.loads(Path(artifacts.manifest_json).read_text(encoding="utf-8")).get("status", "needs_revision")
    return PipelineResult(
        run_id=run_id,
        status=manifest_status,
        topic=topic,
        format_plan=format_plan,
        script=script,
        gate=gate,
        readability=readability,
        quality=quality,
        review=review,
        artifacts=artifacts,
    )


def main() -> int:
    parser = argparse.ArgumentParser(description="Run one TikTok AiNo pipeline test.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--image-mode", choices=["auto", "codex_cli", "gemini_api", "local"], default="auto")
    parser.add_argument("--real-image-limit", type=int, default=default_real_image_limit_from_env())
    parser.add_argument(
        "--privacy-mode",
        choices=[privacy_policy.LOCAL_ONLY, privacy_policy.CLOUD_EXPLICIT],
        default=privacy_policy.current_mode(),
    )
    parser.add_argument("--topic-mode", choices=["static", "hot"], default=os.environ.get("AINO_TOPIC_MODE", "static"))
    parser.add_argument(
        "--format",
        choices=[
            "auto",
            "evidence_briefing_75",
            "growth_short",
            "ranking_battle_65",
            "narrative_confession",
            "reward_deep",
            "reformed_briefing",
            "debate_followup",
        ],
        default=os.environ.get("AINO_CONTENT_FORMAT", "auto"),
        dest="content_format",
    )
    args = parser.parse_args()
    os.environ["AINO_PRIVACY_MODE"] = args.privacy_mode
    result = run_once(
        args.output_dir,
        image_mode=args.image_mode,
        real_image_limit=None if args.real_image_limit is None else max(0, args.real_image_limit),
        content_format=args.content_format,
        topic_mode=args.topic_mode,
    )
    print(json.dumps(asdict(result), ensure_ascii=False, indent=2))
    return 0 if result.status in {"upload_ready", "publish_ready"} else 2


if __name__ == "__main__":
    raise SystemExit(main())
