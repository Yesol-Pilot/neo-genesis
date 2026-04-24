#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from email.utils import parsedate_to_datetime
from pathlib import Path
from typing import Iterable


PROJECT_ROOT = Path(__file__).resolve().parent.parent
ARTIFACT_DIR = PROJECT_ROOT / "data" / "automation" / "ai_ops_brief"
DEFAULT_ARCHIVE_DIR = ARTIFACT_DIR / "archive"
USER_AGENT = "NeoGenesisAIBrief/1.0"
MAX_ITEMS = 8
SOURCE_ITEM_LIMIT = 8
GLOBAL_SOURCE_LIMIT = 3
PAGE_CANDIDATE_LIMIT = 12
SUMMARY_LIMIT = 300
TITLE_LIMIT = 120
HISTORY_LOOKBACK_DAYS = 14
REPEAT_PENALTY_MAX = 12
FRESH_REPEAT_PENALTY_MAX = 6

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SOURCE_PAGES = [
    {"name": "OpenAI", "homepage": "https://openai.com/news/", "feed_url": "https://openai.com/news/rss.xml"},
    {"name": "Anthropic", "homepage": "https://www.anthropic.com/news"},
    {"name": "Google AI", "homepage": "https://blog.google/technology/ai/"},
    {"name": "DeepMind", "homepage": "https://deepmind.google/discover/blog/"},
    {"name": "Hugging Face", "homepage": "https://huggingface.co/blog"},
    {"name": "Microsoft Research", "homepage": "https://www.microsoft.com/en-us/research/blog/"},
]

SCORE_GROUPS = [
    (("introducing gpt", "gpt-5", "gpt‑5", "claude opus", "claude sonnet", "model", "models"), 8),
    (("agentic", "agent", "agents", "automation", "automations", "codex", "workflow", "workflows", "tool", "tools", "computer use"), 8),
    (("system card", "safety", "security", "cyber", "vulnerability", "vulnerabilities", "safeguard", "safeguards", "trusted access"), 8),
    (("benchmark", "evaluation", "eval", "failure mode", "failure modes", "debugging"), 6),
    (("domain adaptation", "rag", "fine-tuning", "memory"), 5),
    (("api", "deployment", "production", "latency", "cost", "pricing", "inference"), 4),
    (("multimodal", "design", "interactive", "visualization"), 3),
]

_FETCH_CACHE: dict[str, str] = {}


@dataclass
class BriefItem:
    source: str
    title: str
    url: str
    published: str = ""
    summary: str = ""
    relevance: str = ""
    decision: str = ""
    risk: str = ""
    suggested_action: str = ""
    priority: str = "monitor"
    score: int = 0
    effective_score: int = 0
    canonical_url: str = ""
    history_seen_count: int = 0
    history_last_seen: str = ""
    novelty: str = "new"
    signal_lane: str = ""
    authority_tier: str = ""
    action_gate: str = ""
    control_focus: str = ""
    eval_method: str = ""


def _fetch(url: str, timeout_sec: int = 15, retries: int = 2) -> str:
    if url in _FETCH_CACHE:
        return _FETCH_CACHE[url]

    last_error: Exception | None = None
    for attempt in range(retries + 1):
        req = urllib.request.Request(
            url,
            headers={
                "User-Agent": USER_AGENT,
                "Accept": "text/html,application/rss+xml,application/atom+xml,application/xml;q=0.9,*/*;q=0.8",
            },
        )
        try:
            with urllib.request.urlopen(req, timeout=timeout_sec) as response:
                charset = response.headers.get_content_charset() or "utf-8"
                body = response.read().decode(charset, errors="replace")
                _FETCH_CACHE[url] = body
                return body
        except urllib.error.URLError as exc:
            last_error = exc
            if attempt < retries:
                time.sleep(0.5 * (attempt + 1))

    assert last_error is not None
    raise last_error


def _discover_feed_url(page_html: str, base_url: str) -> str | None:
    patterns = [
        r'<link[^>]+rel=["\']alternate["\'][^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+href=["\']([^"\']+)["\']',
        r'<link[^>]+type=["\']application/(?:rss|atom)\+xml["\'][^>]+rel=["\']alternate["\'][^>]+href=["\']([^"\']+)["\']',
    ]
    for pattern in patterns:
        match = re.search(pattern, page_html, flags=re.I)
        if match:
            return urllib.parse.urljoin(base_url, match.group(1))
    return None


def _text_from_html(raw: str) -> str:
    raw = re.sub(r"<script[\s\S]*?</script>", " ", raw, flags=re.I)
    raw = re.sub(r"<style[\s\S]*?</style>", " ", raw, flags=re.I)
    raw = re.sub(r"<[^>]+>", " ", raw)
    raw = html.unescape(raw)
    return re.sub(r"\s+", " ", raw).strip()


def _truncate(text: str, limit: int) -> str:
    text = re.sub(r"\s+", " ", text).strip()
    if len(text) <= limit:
        return text
    return text[: limit - 3].rstrip() + "..."


def _clean_title(title: str) -> str:
    title = _text_from_html(title)
    title = re.sub(r"^(Product|Announcements|Research|Company)\s+", "", title, flags=re.I)
    title = re.sub(r"^[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\s+", "", title)
    title = re.sub(r"\s+(Product|Announcements|Research)\s+[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\s+", " ", title)
    title = re.sub(r"\s+(?:\\|\||-)\s+(Anthropic|OpenAI|Microsoft Research|Google|Hugging Face)$", "", title)
    title = re.sub(r"\s+", " ", title).strip(" -|")
    return _truncate(title, TITLE_LIMIT)


def _date_from_text(text: str) -> str:
    text = _text_from_html(text)
    date_match = re.search(r"\b(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[a-z]*\s+\d{1,2},\s+20\d{2}\b", text)
    return date_match.group(0) if date_match else ""


def _normalize_url(url: str) -> str:
    parsed = urllib.parse.urlsplit(url)
    path = parsed.path.rstrip("/") or "/"
    return urllib.parse.urlunsplit((parsed.scheme, parsed.netloc.lower(), path, parsed.query, ""))


def _extract_meta(page_html: str, names: Iterable[str]) -> str:
    for name in names:
        patterns = [
            rf'<meta[^>]+property=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
            rf'<meta[^>]+name=["\']{re.escape(name)}["\'][^>]+content=["\']([^"\']+)["\']',
        ]
        for pattern in patterns:
            match = re.search(pattern, page_html, flags=re.I)
            if match:
                return html.unescape(match.group(1)).strip()
    if "title" in names:
        title_match = re.search(r"<title[^>]*>(.*?)</title>", page_html, flags=re.I | re.S)
        if title_match:
            return _text_from_html(title_match.group(1))
    return ""


def _extract_published(page_html: str) -> str:
    published = _extract_meta(
        page_html,
        (
            "article:published_time",
            "article:modified_time",
            "date",
            "dc.date",
            "publish_date",
            "og:updated_time",
        ),
    )
    if published:
        return published

    time_match = re.search(r"<time[^>]+datetime=[\"']([^\"']+)[\"']", page_html, flags=re.I)
    if time_match:
        return html.unescape(time_match.group(1)).strip()

    return _date_from_text(page_html)


def _parse_published(published: str) -> datetime | None:
    if not published:
        return None
    published = published.strip()
    try:
        parsed = parsedate_to_datetime(published)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed
    except (TypeError, ValueError):
        pass

    for fmt in ("%Y-%m-%dT%H:%M:%S%z", "%Y-%m-%dT%H:%M:%SZ", "%B %d, %Y", "%b %d, %Y"):
        try:
            normalized = published.replace("Z", "+0000") if fmt.endswith("%z") else published
            parsed = datetime.strptime(normalized, fmt)
            if parsed.tzinfo is None:
                parsed = parsed.replace(tzinfo=timezone.utc)
            return parsed
        except ValueError:
            continue
    return None


def _recency_adjustment(published: str) -> int:
    parsed = _parse_published(published)
    if not parsed:
        return 0
    now = datetime.now(timezone.utc)
    age_days = max(0, (now - parsed.astimezone(timezone.utc)).days)
    if age_days <= 3:
        return 6
    if age_days <= 7:
        return 4
    if age_days <= 14:
        return 2
    if age_days <= 30:
        return 0
    if age_days <= 60:
        return -18
    if age_days <= 90:
        return -24
    if age_days <= 365:
        return -32
    return -40


def _score_item(title: str, summary: str, published: str = "") -> int:
    text = f"{title} {summary}".lower()
    score = sum(weight for terms, weight in SCORE_GROUPS if any(term in text for term in terms))
    if any(term in text for term in ("open source", "open-source", "released", "launch")):
        score += 1
    if any(term in text for term in ("project glasswing", "cyber verification")):
        score += 3
    if any(term in text for term in ("introducing gpt", "gpt-5.5", "gpt‑5.5", "opus 4.7")):
        score += 4
    if title.strip().lower() == "automations":
        score += 5
    return max(0, score + _recency_adjustment(published))


def _relevance_hint(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if any(word in text for word in ("system card", "safety", "security", "cyber", "vulnerability", "safeguard", "policy")):
        return "운영 정책/보안/안전 게이트 기준에 영향"
    if any(word in text for word in ("agent", "tool", "workflow", "automation")):
        return "작업 자동화/에이전트 강화에 직접 영향"
    if any(word in text for word in ("api", "model", "benchmark", "pricing", "cost", "latency", "inference")):
        return "모델 선택/운영 비용/성능 판단에 영향"
    if any(word in text for word in ("evaluation", "eval", "domain adaptation", "rag", "fine-tuning")):
        return "평가/도메인 적응/품질 검증 체계에 영향"
    return "새 업데이트의 실무 적용 여지가 있음"


def _decision_hint(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if any(term in text for term in ("system card", "safety", "security", "cyber", "vulnerability", "safeguard")):
        return "운영 규칙과 승인 게이트에 반영 후보"
    if any(term in text for term in ("automation", "automations", "agent", "codex", "workflow", "computer use")):
        return "자동화/에이전트 실행 경로에 즉시 적용 후보"
    if any(term in text for term in ("benchmark", "evaluation", "eval", "domain adaptation", "rag", "fine-tuning")):
        return "모델 라우팅과 품질 평가 기준에 반영 후보"
    if any(term in text for term in ("pricing", "cost", "latency", "inference")):
        return "비용/속도 기준 재검토 후보"
    return "참고 관찰 후보"


def _risk_hint(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if any(term in text for term in ("system card", "safety", "security", "cyber", "vulnerability", "safeguard")):
        return "보안/오남용/권한 상승 경계 필요"
    if any(term in text for term in ("agent", "automation", "workflow", "computer use")):
        return "장기 실행 실패, 도구 오작동, 과도한 자율 실행 위험"
    if any(term in text for term in ("benchmark", "evaluation", "eval")):
        return "벤치마크 과신 및 실제 업무 전이 실패 위험"
    if any(term in text for term in ("domain adaptation", "rag", "fine-tuning")):
        return "도메인 적응 결과를 실데이터로 검증하지 못할 위험"
    if any(term in text for term in ("pricing", "cost", "latency", "inference")):
        return "비용 증가 또는 지연시간 악화 위험"
    return "실무 영향이 낮을 수 있어 후순위 검토"


def _suggested_action(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if any(term in text for term in ("system card", "safety", "security", "cyber", "vulnerability", "safeguard")):
        return "Sora/Codex 자동화의 권한, 보안, 실패 보고 규칙에 반영할 항목을 추출한다."
    if any(term in text for term in ("automation", "automations", "agent", "codex", "workflow")):
        return "반복 작업 1개를 선정해 스케줄/트리거/검증 결과까지 닫히는 자동화로 바꾼다."
    if any(term in text for term in ("benchmark", "evaluation", "eval", "domain adaptation")):
        return "현재 작업 유형별 모델 선택 기준과 실패 평가 항목을 업데이트한다."
    if any(term in text for term in ("multimodal", "design", "interactive")):
        return "대시보드/문서/프로토타입 생성 흐름에 적용 가능한지 별도 실험 후보로 둔다."
    return "링크를 보관하고 다음 브리프에서 반복 신호인지 확인한다."


def _signal_lane(title: str, summary: str) -> str:
    text = f"{title} {summary}".lower()
    if any(term in text for term in ("system card", "safety", "security", "cyber", "vulnerability", "safeguard", "trusted access")):
        return "security_governance"
    if any(term in text for term in ("failure mode", "failure modes", "debugging", "agentrx", "vakra", "tool", "tools", "agent", "agents", "workflow", "automation")):
        return "agent_reliability"
    if any(term in text for term in ("benchmark", "evaluation", "eval", "domain adaptation", "rag", "fine-tuning", "adele", "autoadapt")):
        return "model_routing_eval"
    if any(term in text for term in ("pricing", "cost", "latency", "inference", "api", "deployment", "production")):
        return "runtime_cost_ops"
    if any(term in text for term in ("gpt", "claude", "gemini", "model", "models")):
        return "model_watch"
    return "market_watch"


def _authority_tier_for_lane(lane: str) -> str:
    if lane in {"security_governance", "agent_reliability", "model_routing_eval"}:
        return "G2"
    if lane == "runtime_cost_ops":
        return "G3"
    return "G0"


def _action_gate_for_lane(lane: str) -> str:
    if lane == "security_governance":
        return "Local policy or prompt edits may proceed as G2; external enforcement, notifications, deploys, or credential changes require G4/G5 approval."
    if lane == "agent_reliability":
        return "Apply only to local prompt, trace, or test harness changes; stop before external API mutation, deployment, or notification."
    if lane == "model_routing_eval":
        return "Use local golden tasks and dry-runs before changing default model routing."
    if lane == "runtime_cost_ops":
        return "Measure latency/cost locally first; production runtime or budget changes require explicit scope."
    if lane == "model_watch":
        return "Observe only until API availability, cost, compatibility, and safety posture are verified."
    return "Archive unless the signal changes today's operating decision."


def _control_focus_for_lane(lane: str) -> str:
    controls = {
        "security_governance": "SEC-002, SEC-004, SEC-008",
        "agent_reliability": "SEC-007, SEC-010",
        "model_routing_eval": "SEC-010",
        "runtime_cost_ops": "SEC-007, SEC-010",
        "model_watch": "SEC-010",
    }
    return controls.get(lane, "SEC-001")


def _eval_method_for_lane(lane: str) -> str:
    methods = {
        "security_governance": "policy checklist + prompt-injection/security regression case",
        "agent_reliability": "Plan-Execute-Verify trace review + failure-mode regression",
        "model_routing_eval": "local golden task A/B with cost, latency, and failure-mode notes",
        "runtime_cost_ops": "local benchmark with budget guard and rollback note",
        "model_watch": "official-doc verification + compatibility watch",
    }
    return methods.get(lane, "manual triage; no action until repeated signal")


def _priority(score: int) -> str:
    if score >= 10:
        return "act_today"
    if score >= 6:
        return "test_this_week"
    if score >= 3:
        return "monitor"
    return "archive"


def _finalize_item(item: BriefItem) -> BriefItem:
    item.title = _clean_title(item.title)
    item.summary = _truncate(_text_from_html(item.summary), SUMMARY_LIMIT) if item.summary else ""
    item.canonical_url = _normalize_url(item.url.split("#", 1)[0])
    item.score = _score_item(item.title, item.summary, item.published)
    item.effective_score = item.score
    item.relevance = _relevance_hint(item.title, item.summary)
    item.decision = _decision_hint(item.title, item.summary)
    item.risk = _risk_hint(item.title, item.summary)
    item.suggested_action = _suggested_action(item.title, item.summary)
    item.signal_lane = _signal_lane(item.title, item.summary)
    item.authority_tier = _authority_tier_for_lane(item.signal_lane)
    item.action_gate = _action_gate_for_lane(item.signal_lane)
    item.control_focus = _control_focus_for_lane(item.signal_lane)
    item.eval_method = _eval_method_for_lane(item.signal_lane)
    item.priority = _priority(item.score)
    return item


def _hydrate_page_item(item: BriefItem) -> BriefItem:
    try:
        page_html = _fetch(item.url, timeout_sec=10)
    except urllib.error.URLError:
        return _finalize_item(item)

    meta_title = _extract_meta(page_html, ("og:title", "twitter:title", "title"))
    meta_summary = _extract_meta(page_html, ("og:description", "twitter:description", "description"))
    if meta_title:
        item.title = meta_title
    if meta_summary:
        item.summary = meta_summary
    if not item.published:
        item.published = _extract_published(page_html)
    return _finalize_item(item)


def _parse_feed_items(feed_xml: str, source: str, base_url: str) -> list[BriefItem]:
    items: list[BriefItem] = []
    try:
        root = ET.fromstring(feed_xml)
    except ET.ParseError:
        return items

    for entry in root.findall(".//item") + root.findall(".//{*}entry"):
        title = (entry.findtext("title") or "").strip()
        if not title:
            continue
        link = ""
        link_node = entry.find("link")
        if link_node is not None:
            link = (link_node.attrib.get("href") or link_node.text or "").strip()
        if not link:
            link = (entry.findtext("link") or "").strip()
        link = urllib.parse.urljoin(base_url, link)
        summary = (entry.findtext("description") or entry.findtext("{*}summary") or "").strip()
        if not summary:
            summary = (entry.findtext("{*}content") or "").strip()
        published = (
            entry.findtext("pubDate")
            or entry.findtext("{*}published")
            or entry.findtext("{*}updated")
            or ""
        ).strip()
        item = BriefItem(
            source=source,
            title=title,
            url=link,
            published=published,
            summary=summary,
        )
        items.append(_finalize_item(item))
    return items


def _parse_page_items(page_html: str, source: str, base_url: str) -> list[BriefItem]:
    items: list[BriefItem] = []
    anchors = re.findall(r'<a[^>]+href=["\']([^"\']+)["\'][^>]*>(.*?)</a>', page_html, flags=re.I | re.S)
    seen: set[str] = set()
    for href, inner_html in anchors:
        url = urllib.parse.urljoin(base_url, html.unescape(href))
        if not url.startswith("http"):
            continue
        if any(skip in url for skip in ("mailto:", "javascript:", "#")):
            continue
        if urllib.parse.urlparse(url).netloc != urllib.parse.urlparse(base_url).netloc:
            continue
        raw_title = _text_from_html(inner_html)
        title = _clean_title(raw_title)
        if len(title) < 24:
            continue
        if url in seen:
            continue
        seen.add(url)
        summary = ""
        items.append(
            _finalize_item(
                BriefItem(
                    source=source,
                    title=title,
                    url=url,
                    published=_date_from_text(raw_title),
                    summary=summary,
                )
            )
        )
    return items


def _collect_source(source: dict[str, str]) -> list[BriefItem]:
    homepage = source["homepage"]
    name = source["name"]
    items: list[BriefItem] = []

    feed_url = source.get("feed_url")
    if feed_url:
        try:
            items = _parse_feed_items(_fetch(feed_url), name, homepage)
        except urllib.error.URLError:
            items = []

    if not items:
        try:
            page_html = _fetch(homepage)
        except urllib.error.URLError:
            return []

        feed_url = _discover_feed_url(page_html, homepage)
        if feed_url:
            try:
                items = _parse_feed_items(_fetch(feed_url), name, homepage)
            except urllib.error.URLError:
                items = []

    if not items:
        page_items = _parse_page_items(page_html, name, homepage)
        candidates = _choose_items(page_items)[:PAGE_CANDIDATE_LIMIT]
        items = [_hydrate_page_item(item) for item in candidates]

    return _choose_items(items)[:SOURCE_ITEM_LIMIT]


def _history_stamp(path: Path) -> str:
    match = re.match(r"^(\d{8}_\d{6})_brief\.md$", path.name)
    if match:
        try:
            return datetime.strptime(match.group(1), "%Y%m%d_%H%M%S").replace(tzinfo=timezone.utc).isoformat()
        except ValueError:
            pass
    return datetime.fromtimestamp(path.stat().st_mtime, timezone.utc).isoformat()


def _load_recent_history(history_dir: Path, lookback_days: int = HISTORY_LOOKBACK_DAYS) -> dict[str, dict[str, object]]:
    if lookback_days <= 0 or not history_dir.exists():
        return {}

    cutoff = datetime.now(timezone.utc) - timedelta(days=lookback_days)
    history: dict[str, dict[str, object]] = {}
    for path in sorted(history_dir.glob("*_brief.md")):
        try:
            modified = datetime.fromtimestamp(path.stat().st_mtime, timezone.utc)
        except OSError:
            continue
        if modified < cutoff:
            continue
        try:
            text = path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            continue
        stamp = _history_stamp(path)
        for url in re.findall(r"(?m)^-\s+url:\s+(\S+)", text):
            key = _normalize_url(url.split("#", 1)[0])
            entry = history.setdefault(key, {"count": 0, "last_seen": ""})
            entry["count"] = int(entry["count"]) + 1
            if str(entry["last_seen"]) < stamp:
                entry["last_seen"] = stamp
    return history


def _is_fresh_item(item: BriefItem, max_age_days: int = 2) -> bool:
    parsed = _parse_published(item.published)
    if not parsed:
        return False
    age = datetime.now(timezone.utc) - parsed.astimezone(timezone.utc)
    return age <= timedelta(days=max_age_days)


def _history_penalty(item: BriefItem) -> int:
    if item.history_seen_count <= 0:
        return 0
    if item.history_seen_count == 1:
        penalty = 3
    elif item.history_seen_count == 2:
        penalty = 7
    else:
        penalty = REPEAT_PENALTY_MAX
    if _is_fresh_item(item):
        penalty = min(penalty, FRESH_REPEAT_PENALTY_MAX)
    return penalty


def _apply_history(items: list[BriefItem], history: dict[str, dict[str, object]]) -> list[BriefItem]:
    for item in items:
        key = item.canonical_url or _normalize_url(item.url.split("#", 1)[0])
        entry = history.get(key, {})
        item.history_seen_count = int(entry.get("count", 0) or 0)
        item.history_last_seen = str(entry.get("last_seen", "") or "")
        item.novelty = "new" if item.history_seen_count == 0 else f"repeat_{item.history_seen_count}"
        item.effective_score = max(0, item.score - _history_penalty(item))
        item.priority = _priority(item.effective_score)
    return items


def _ranking_score(item: BriefItem) -> tuple[int, int]:
    return (item.effective_score, item.score)


def _choose_items(items: list[BriefItem]) -> list[BriefItem]:
    deduped: dict[str, BriefItem] = {}
    for item in sorted(items, key=_ranking_score, reverse=True):
        key = item.canonical_url or _normalize_url(item.url.split("#", 1)[0])
        if key not in deduped:
            deduped[key] = item
    chosen = list(deduped.values())
    chosen.sort(key=_ranking_score, reverse=True)
    return chosen


def _choose_global_items(items: list[BriefItem], limit: int) -> list[BriefItem]:
    chosen: list[BriefItem] = []
    source_counts: dict[str, int] = {}
    for item in _choose_items(items):
        count = source_counts.get(item.source, 0)
        if count >= GLOBAL_SOURCE_LIMIT:
            continue
        chosen.append(item)
        source_counts[item.source] = count + 1
        if len(chosen) >= limit:
            break
    return chosen


def _item_record(item: BriefItem, collected_at: str, run_id: str) -> dict[str, object]:
    return {
        "collected_at": collected_at,
        "run_id": run_id,
        "source": item.source,
        "title": item.title,
        "url": item.url,
        "canonical_url": item.canonical_url or _normalize_url(item.url.split("#", 1)[0]),
        "published": item.published,
        "summary": item.summary,
        "priority": item.priority,
        "score": item.score,
        "effective_score": item.effective_score,
        "novelty": item.novelty,
        "history_seen_count": item.history_seen_count,
        "history_last_seen": item.history_last_seen,
        "signal_lane": item.signal_lane,
        "authority_tier": item.authority_tier,
        "action_gate": item.action_gate,
        "control_focus": item.control_focus,
        "eval_method": item.eval_method,
        "relevance": item.relevance,
        "decision": item.decision,
        "risk": item.risk,
        "suggested_action": item.suggested_action,
    }


def _load_json_object(path: Path) -> dict[str, object]:
    if not path.exists():
        return {}
    try:
        payload = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
    return payload if isinstance(payload, dict) else {}


def _archive_items(items: list[BriefItem], archive_dir: Path, run_id: str, selected: list[BriefItem]) -> dict[str, int]:
    archive_dir.mkdir(parents=True, exist_ok=True)
    daily_dir = archive_dir / "daily"
    daily_dir.mkdir(parents=True, exist_ok=True)

    collected_at = datetime.now(timezone.utc).isoformat()
    records = [_item_record(item, collected_at, run_id) for item in _choose_items(items)]
    selected_keys = {
        item.canonical_url or _normalize_url(item.url.split("#", 1)[0])
        for item in selected
    }
    for record in records:
        record["selected_for_brief"] = record["canonical_url"] in selected_keys

    observations_path = archive_dir / "observations.jsonl"
    with observations_path.open("a", encoding="utf-8") as fh:
        for record in records:
            fh.write(json.dumps(record, ensure_ascii=False, sort_keys=True) + "\n")

    index_path = archive_dir / "url_index.json"
    index = _load_json_object(index_path)
    urls = index.setdefault("urls", {})
    if not isinstance(urls, dict):
        urls = {}
        index["urls"] = urls

    new_urls = 0
    updated_urls = 0
    for record in records:
        key = str(record["canonical_url"])
        existing = urls.get(key)
        if not isinstance(existing, dict):
            urls[key] = {
                "first_seen": collected_at,
                "last_seen": collected_at,
                "seen_count": 1,
                "source": record["source"],
                "title": record["title"],
                "url": record["url"],
                "published": record["published"],
                "best_score": record["score"],
                "best_effective_score": record["effective_score"],
                "latest_priority": record["priority"],
                "latest_signal_lane": record["signal_lane"],
                "latest_authority_tier": record["authority_tier"],
                "selected_count": 1 if record.get("selected_for_brief") else 0,
            }
            new_urls += 1
            continue

        existing["last_seen"] = collected_at
        existing["seen_count"] = int(existing.get("seen_count", 0) or 0) + 1
        existing["title"] = record["title"]
        existing["source"] = record["source"]
        existing["url"] = record["url"]
        existing["published"] = record["published"]
        existing["best_score"] = max(int(existing.get("best_score", 0) or 0), int(record["score"]))
        existing["best_effective_score"] = max(
            int(existing.get("best_effective_score", 0) or 0),
            int(record["effective_score"]),
        )
        existing["latest_priority"] = record["priority"]
        existing["latest_signal_lane"] = record["signal_lane"]
        existing["latest_authority_tier"] = record["authority_tier"]
        if record.get("selected_for_brief"):
            existing["selected_count"] = int(existing.get("selected_count", 0) or 0) + 1
        updated_urls += 1

    index["updated_at"] = collected_at
    index["total_urls"] = len(urls)
    index["last_run_id"] = run_id
    index_path.write_text(json.dumps(index, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    daily_path = daily_dir / f"{run_id[:8]}.json"
    daily_payload = {
        "run_id": run_id,
        "collected_at": collected_at,
        "items": records,
        "selected_urls": sorted(selected_keys),
        "stats": {
            "observed": len(records),
            "selected": len(selected),
            "new_urls": new_urls,
            "updated_urls": updated_urls,
            "total_urls": len(urls),
        },
    }
    daily_path.write_text(json.dumps(daily_payload, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    return {
        "observed": len(records),
        "selected": len(selected),
        "new_urls": new_urls,
        "updated_urls": updated_urls,
        "total_urls": len(urls),
    }


def _format_brief(items: list[BriefItem]) -> str:
    now = datetime.now(timezone.utc).astimezone()
    lines = [
        "# AI Ops Brief",
        f"- generated_at: {now.strftime('%Y-%m-%d %H:%M %Z')}",
        "- goal: today's high-signal AI updates for Sora to review, report, and internalize",
        "- authority_reference: .agent/registries/agent_security_controls.json",
        "- safety_mode: report_only_until_owner_or_policy_gate_allows_external_side_effects",
        "- history_dedupe: recent URL repeats reduce effective_score before priority selection",
        "- authority_gate_g0_g1: observe, cite, and inspect only",
        "- authority_gate_g2_g3: local docs, prompt, code, trace, or eval changes require verification artifacts",
        "- authority_gate_g4_g5: external notification, deploy, credential, billing, DNS, production, or irreversible actions require owner approval",
        "",
        "## 오늘 결론",
        "- AI 업데이트는 뉴스가 아니라 자동화, 모델 라우팅, 보안 게이트, 운영 비용을 바꾸는 후보로만 검토한다.",
        "- 상위 항목은 `act_today`와 `test_this_week`만 보고 본문에 올리고, 나머지는 참고 링크로 낮춘다.",
        "",
        "## 실행 기준",
        "- act_today: 오늘 프롬프트, 자동화, 모델 선택, 보안 게이트 중 하나에 반영",
        "- test_this_week: 이번 주 실험으로 등록",
        "- monitor/archive: 반복 신호가 될 때까지 관찰 또는 링크 보관",
        "",
        "## 핵심 항목",
    ]
    if not items:
        lines.append("- no items collected")
        return "\n".join(lines).strip()

    for idx, item in enumerate(items, 1):
        lines.extend(
            [
                f"### {idx}. {item.title}",
                f"- source: {item.source}",
                f"- url: {item.url}",
                f"- priority: {item.priority}",
                f"- signal_lane: {item.signal_lane}",
                f"- authority_tier: {item.authority_tier}",
                f"- action_gate: {item.action_gate}",
                f"- control_focus: {item.control_focus}",
                f"- eval_method: {item.eval_method}",
                f"- novelty: {item.novelty}",
                f"- history_seen_count: {item.history_seen_count}",
            ]
        )
        if item.history_last_seen:
            lines.append(f"- history_last_seen: {item.history_last_seen}")
        if item.published:
            lines.append(f"- published: {item.published}")
        if item.summary:
            lines.append(f"- summary: {item.summary}")
        lines.append(f"- why_it_matters: {item.relevance}")
        lines.append(f"- decision: {item.decision}")
        lines.append(f"- risk: {item.risk}")
        lines.append(f"- suggested_action: {item.suggested_action}")
        lines.append(f"- score: {item.score}")
        lines.append(f"- effective_score: {item.effective_score}")
        lines.append("")

    lines.extend(
        [
            "## Sora briefing instructions",
            "- report only the highest-value 3~5 signals",
            "- separate stable patterns from changing facts",
            "- propose one action for today and 1~2 experiments for this week",
            "- suggest what should be internalized into prompts, automations, or environment settings",
            "- use authority_tier, action_gate, control_focus, and eval_method fields before proposing any execution",
            "- do not propose external side effects unless the item explicitly passes G4/G5 approval",
            "- discard hype and low-signal items",
        ]
    )
    return "\n".join(lines).strip()


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build a daily AI ops brief from official AI sources.")
    parser.add_argument("--limit", type=int, default=MAX_ITEMS)
    parser.add_argument("--output-file", help="Write the brief to a UTF-8 file instead of stdout.")
    parser.add_argument("--history-dir", default=str(ARTIFACT_DIR), help="Directory containing previous *_brief.md artifacts.")
    parser.add_argument("--history-days", type=int, default=HISTORY_LOOKBACK_DAYS, help="Lookback window for URL repeat penalties.")
    parser.add_argument("--no-history-dedupe", action="store_true", help="Disable repeat penalties from previous brief artifacts.")
    parser.add_argument("--archive-dir", default=str(DEFAULT_ARCHIVE_DIR), help="Directory for cumulative AI signal data.")
    parser.add_argument("--no-archive", action="store_true", help="Do not write cumulative archive files.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    items: list[BriefItem] = []
    for source in SOURCE_PAGES:
        items.extend(_collect_source(source))
    if not args.no_history_dedupe:
        history = _load_recent_history(Path(args.history_dir), args.history_days)
        items = _apply_history(items, history)
    chosen = _choose_global_items(items, max(1, args.limit))
    if not args.no_archive:
        run_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
        stats = _archive_items(items, Path(args.archive_dir), run_id, chosen)
        print(
            "ai_ops_archive="
            + " ".join(f"{key}={value}" for key, value in stats.items()),
            file=sys.stderr,
        )
    brief = _format_brief(chosen)
    if args.output_file:
        Path(args.output_file).write_text(brief + "\n", encoding="utf-8")
    else:
        print(brief)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
