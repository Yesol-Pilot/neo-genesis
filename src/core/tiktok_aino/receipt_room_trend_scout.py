from __future__ import annotations

import argparse
import datetime as dt
import email.utils
import html
import json
import os
import re
import textwrap
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from src.core.tiktok_aino import privacy as privacy_policy
from src.core.tiktok_aino import receipt_room_planner as planner

CONFIG_PATH = planner.CONFIG_PATH


@dataclass(frozen=True)
class FeedItem:
    title: str
    link: str
    summary: str
    published_at: str | None
    source_id: str
    source_name: str
    feed_name: str
    query: str | None = None


@dataclass(frozen=True)
class ScoutResult:
    generated_at: str
    fetched_items: int
    candidate_count: int
    selected_count: int
    plans: list[dict[str, Any]]
    sources: list[dict[str, str]]
    errors: list[str] = field(default_factory=list)
    privacy: dict[str, Any] = field(default_factory=dict)


def _strategy() -> dict[str, Any]:
    return planner.load_strategy(CONFIG_PATH)


def _now_utc() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)


def _parse_datetime(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    normalized = value.strip()
    try:
        iso_value = normalized.replace("Z", "+00:00")
        parsed_iso = dt.datetime.fromisoformat(iso_value)
        if parsed_iso.tzinfo is None:
            return parsed_iso.replace(tzinfo=dt.timezone.utc)
        return parsed_iso.astimezone(dt.timezone.utc)
    except ValueError:
        pass
    try:
        parsed = email.utils.parsedate_to_datetime(normalized)
    except (TypeError, ValueError, IndexError, OverflowError):
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=dt.timezone.utc)
    return parsed.astimezone(dt.timezone.utc)


def _fetch_url(url: str, *, user_agent: str, timeout_sec: int) -> bytes:
    request = urllib.request.Request(url, headers={"User-Agent": user_agent})
    with urllib.request.urlopen(request, timeout=timeout_sec) as response:
        return response.read()


def _strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", value or "")
    text = html.unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def _child_text(element: ET.Element, name: str) -> str:
    child = element.find(name)
    if child is not None and child.text:
        return child.text.strip()
    return ""


def _source_from_alias(raw: str, strategy: dict[str, Any], fallback: str = "unknown") -> str:
    text = raw.lower()
    for row in strategy["trend_scout"].get("source_aliases", []):
        if str(row.get("match", "")).lower() in text:
            return str(row.get("source_id", fallback))
    return fallback


def _parse_rss(raw: bytes, feed_name: str, default_source_id: str, strategy: dict[str, Any], query: str | None = None) -> list[FeedItem]:
    root = ET.fromstring(raw)
    items = root.findall(".//item")
    parsed: list[FeedItem] = []
    for item in items:
        title = _strip_html(_child_text(item, "title"))
        link = _child_text(item, "link")
        summary = _strip_html(_child_text(item, "description"))
        pub_date = _child_text(item, "pubDate") or _child_text(item, "published")
        source_node = item.find("source")
        source_name = source_node.text.strip() if source_node is not None and source_node.text else feed_name
        source_hint = " ".join([source_name, link, title])
        source_id = _source_from_alias(source_hint, strategy, default_source_id)
        if title and link:
            parsed.append(
                FeedItem(
                    title=title,
                    link=link,
                    summary=summary,
                    published_at=_parse_datetime(pub_date).isoformat() if _parse_datetime(pub_date) else None,
                    source_id=source_id,
                    source_name=source_name,
                    feed_name=feed_name,
                    query=query,
                )
            )
    return parsed


def _google_news_url(query: str) -> str:
    encoded = urllib.parse.quote(query)
    return f"https://news.google.com/rss/search?q={encoded}&hl=en-US&gl=US&ceid=US:en"


def fetch_feed_items(strategy: dict[str, Any] | None = None) -> tuple[list[FeedItem], list[str]]:
    strategy = strategy or _strategy()
    scout = strategy["trend_scout"]
    user_agent = str(scout["user_agent"])
    timeout_sec = int(scout["timeout_sec"])
    max_items = int(scout["max_items_per_feed"])
    items: list[FeedItem] = []
    errors: list[str] = []

    for feed in scout.get("direct_feeds", []):
        try:
            raw = _fetch_url(str(feed["url"]), user_agent=user_agent, timeout_sec=timeout_sec)
            parsed = _parse_rss(raw, str(feed["name"]), str(feed["source_id"]), strategy)
            items.extend(parsed[:max_items])
        except (urllib.error.URLError, TimeoutError, ET.ParseError, KeyError, ValueError) as exc:
            errors.append(f"{feed.get('name', 'feed')}: {type(exc).__name__}: {exc}")

    for query in scout.get("google_news_queries", []):
        try:
            raw = _fetch_url(_google_news_url(str(query)), user_agent=user_agent, timeout_sec=timeout_sec)
            parsed = _parse_rss(raw, f"Google News: {query}", "google_news", strategy, query=str(query))
            items.extend(parsed[:max_items])
        except (urllib.error.URLError, TimeoutError, ET.ParseError, ValueError) as exc:
            errors.append(f"Google News query={query}: {type(exc).__name__}: {exc}")

    return _dedupe_items(_filter_items(items, strategy), strategy), errors


def _filter_items(items: list[FeedItem], strategy: dict[str, Any]) -> list[FeedItem]:
    scout = strategy["trend_scout"]
    lookback_hours = int(scout["lookback_hours"])
    cutoff = _now_utc() - dt.timedelta(hours=lookback_hours)
    block_terms = [str(term).lower() for term in scout.get("candidate_title_block_terms", [])]
    noise_terms = [str(term).lower() for term in scout.get("candidate_noise_terms", [])]
    kept: list[FeedItem] = []
    for item in items:
        item_text = " ".join([item.title, item.summary, item.source_name]).lower()
        if any(term in item_text for term in block_terms):
            continue
        if any(term in item_text for term in noise_terms):
            continue
        published = _parse_datetime(item.published_at)
        if published and published < cutoff:
            continue
        kept.append(item)
    return kept


def _normalize_title(title: str) -> str:
    lowered = re.sub(r"[^a-z0-9가-힣 ]+", " ", title.lower())
    tokens = [token for token in lowered.split() if token not in {"the", "a", "an", "and", "or", "to", "of", "with", "for"}]
    return " ".join(tokens[:14])


def _token_overlap(left: str, right: str) -> float:
    a = set(_normalize_title(left).split())
    b = set(_normalize_title(right).split())
    if not a or not b:
        return 0.0
    return len(a & b) / max(len(a), len(b))


def _dedupe_items(items: list[FeedItem], strategy: dict[str, Any]) -> list[FeedItem]:
    deduped: list[FeedItem] = []
    for item in sorted(items, key=lambda row: row.published_at or "", reverse=True):
        duplicate_index = None
        for index, current in enumerate(deduped):
            if _normalize_title(item.title) == _normalize_title(current.title) or _token_overlap(item.title, current.title) >= 0.72:
                duplicate_index = index
                break
        if duplicate_index is None:
            deduped.append(item)
            continue
        current = deduped[duplicate_index]
        current_reliability = int(strategy["source_registry"].get(current.source_id, {}).get("reliability", 0))
        item_reliability = int(strategy["source_registry"].get(item.source_id, {}).get("reliability", 0))
        if item_reliability > current_reliability:
            deduped[duplicate_index] = item
    return deduped


def _extract_entities(text: str, strategy: dict[str, Any]) -> list[str]:
    stopwords = {str(item).lower() for item in strategy["trend_scout"].get("entity_stopwords", [])}
    candidates = re.findall(r"\b(?:[A-Z][a-zA-Z'’.-]+)(?:\s+[A-Z][a-zA-Z'’.-]+){0,3}\b", text)
    clean: list[str] = []
    for value in candidates:
        normalized = value.strip(" -:|")
        if len(normalized) < 3:
            continue
        if normalized.lower() in stopwords:
            continue
        if normalized.lower() in {"watch", "latest", "exclusive", "photos", "video"}:
            continue
        clean.append(normalized)
    return list(dict.fromkeys(clean))[:4]


def _keywords_from_item(item: FeedItem, strategy: dict[str, Any]) -> list[str]:
    text = " ".join([item.title, item.summary, item.source_name, item.query or ""]).lower()
    keyword_sets = strategy["issue_scoring"]["keyword_bonuses"]
    found: list[str] = []
    for terms in keyword_sets.values():
        for term in terms:
            if str(term).lower() in text:
                found.append(str(term))
    return list(dict.fromkeys(found))[:12]


def _hours_old(item: FeedItem) -> float:
    published = _parse_datetime(item.published_at)
    if not published:
        return 72.0
    return max(0.0, (_now_utc() - published).total_seconds() / 3600)


def _signal_from_keywords(item: FeedItem, strategy: dict[str, Any], name: str, base: int) -> int:
    text = " ".join([item.title, item.summary, item.query or ""]).lower()
    hits = sum(1 for term in strategy["issue_scoring"]["keyword_bonuses"].get(name, []) if str(term).lower() in text)
    return max(0, min(100, base + hits * 12))


def item_to_candidate(item: FeedItem, strategy: dict[str, Any] | None = None) -> planner.IssueCandidate:
    strategy = strategy or _strategy()
    source_registry = strategy["source_registry"]
    source_reliability = int(source_registry.get(item.source_id, source_registry["unknown"]).get("reliability", 20))
    hours_old = _hours_old(item)
    freshness = max(20, min(100, 100 - int(hours_old * 1.4)))
    trend_velocity = max(20, min(100, int(source_reliability * 0.55 + freshness * 0.45)))
    entities = _extract_entities(item.title, strategy)
    keywords = _keywords_from_item(item, strategy)
    verified_level = "reported" if source_registry.get(item.source_id, {}).get("counts_as_verified") else "observed"
    summary = item.summary or f"Public entertainment headline from {item.source_name}."
    return planner.IssueCandidate(
        title=item.title,
        summary=summary[:320],
        entities=entities,
        source_ids=[item.source_id],
        evidence_items=[
            {
                "text": item.title,
                "url": item.link,
                "source_id": item.source_id,
                "source_name": item.source_name,
                "published_at": item.published_at,
            }
        ],
        claims=[
            planner.Claim(
                text=f"{item.source_name} reported: {item.title}",
                evidence_level=verified_level,
                sensitivity="ordinary",
                source_ids=[item.source_id],
            ),
            planner.Claim(
                text="Any relationship, motive, or body-language interpretation remains fan speculation unless a primary confirmation appears.",
                evidence_level="fan_speculation",
                sensitivity="ordinary",
                source_ids=[item.source_id],
            ),
        ],
        trend_signals={
            "trend_velocity": trend_velocity,
            "fandom_conflict": _signal_from_keywords(item, strategy, "fandom_conflict", 42),
            "visual_drama": _signal_from_keywords(item, strategy, "visual_drama", 38),
            "microdrama_fit": _signal_from_keywords(item, strategy, "microdrama_fit", 42),
            "search_intent": _signal_from_keywords(item, strategy, "search_intent", 40),
            "freshness": freshness,
            "originality": 62 if item.query else 54,
        },
        keywords=keywords,
        published_at=item.published_at,
    )


def discover_and_plan(
    limit: int = 5,
    strategy: dict[str, Any] | None = None,
    *,
    allow_network_research: bool = False,
) -> ScoutResult:
    strategy = strategy or _strategy()
    privacy = privacy_policy.manifest_record()
    if privacy_policy.is_local_only() and not allow_network_research:
        return ScoutResult(
            generated_at=_now_utc().isoformat(),
            fetched_items=0,
            candidate_count=0,
            selected_count=0,
            plans=[],
            sources=[],
            errors=["network_research_blocked_by_local_only_privacy_mode"],
            privacy=privacy,
        )
    items, errors = fetch_feed_items(strategy)
    plans: list[dict[str, Any]] = []
    seen_titles: set[str] = set()
    for item in items:
        candidate = item_to_candidate(item, strategy)
        plan = planner.plan_episode(candidate, strategy)
        plan["scout_source"] = asdict(item)
        plan["source_url"] = item.link
        key = _normalize_title(plan["episode_title"])
        if key in seen_titles:
            continue
        seen_titles.add(key)
        if plan["decision"] == "blocked":
            continue
        plans.append(plan)

    plans.sort(
        key=lambda row: (
            int(row["scorecard"]["total"]),
            int(row["scorecard"]["dimensions"].get("visual_drama", 0)),
            int(row["scorecard"]["dimensions"].get("fandom_conflict", 0)),
        ),
        reverse=True,
    )
    selected = plans[:limit]
    source_rows = []
    for plan in selected:
        source = plan["scout_source"]
        source_rows.append(
            {
                "title": str(plan["episode_title"]),
                "source_name": str(source["source_name"]),
                "source_id": str(source["source_id"]),
                "url": str(source["link"]),
            }
        )
    return ScoutResult(
        generated_at=_now_utc().isoformat(),
        fetched_items=len(items),
        candidate_count=len(plans),
        selected_count=len(selected),
        plans=selected,
        sources=source_rows,
        errors=errors,
        privacy=privacy,
    )


def write_report(result: ScoutResult, output_dir: Path) -> tuple[Path, Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = dt.datetime.now().strftime("%Y%m%d_%H%M%S")
    json_path = output_dir / f"receipt_room_trend_scout_{timestamp}.json"
    md_path = output_dir / f"receipt_room_trend_scout_{timestamp}.md"
    json_path.write_text(json.dumps(asdict(result), ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    lines = [
        "# Receipt Room 11:59 Trend Scout",
        "",
        f"- generated_at: `{result.generated_at}`",
        f"- fetched_items: `{result.fetched_items}`",
        f"- candidate_count: `{result.candidate_count}`",
        f"- selected_count: `{result.selected_count}`",
        "",
        "## Top Candidates",
        "",
    ]
    for index, plan in enumerate(result.plans, start=1):
        source = plan["scout_source"]
        lines.extend(
            [
                f"### {index}. {plan['episode_title']}",
                "",
                f"- decision: `{plan['decision']}`",
                f"- score: `{plan['scorecard']['total']}`",
                f"- format: `{plan['episode_format']}`",
                f"- source: [{source['source_name']}]({source['link']})",
                f"- hook: {plan['hook']}",
                f"- comment_prompt: {plan['publish_package']['comment_prompt']}",
                f"- characters: {', '.join(character['screen_character'] for character in plan['characters'])}",
                "",
            ]
        )
        first_shots = plan["shot_list"][:3]
        for shot in first_shots:
            caption = textwrap.shorten(str(shot["caption"]), width=120, placeholder="...")
            lines.append(f"  - `{shot['beat']}`: {caption}")
        lines.append("")
    if result.errors:
        lines.extend(["## Fetch Errors", ""])
        lines.extend(f"- {error}" for error in result.errors)
    md_path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")
    return json_path, md_path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Discover and rank live Receipt Room 11:59 pop-culture episode candidates.")
    parser.add_argument("--limit", type=int, default=5)
    parser.add_argument("--output-dir", type=Path)
    parser.add_argument(
        "--privacy-mode",
        choices=[privacy_policy.LOCAL_ONLY, privacy_policy.CLOUD_EXPLICIT],
        default=privacy_policy.current_mode(),
    )
    parser.add_argument("--allow-network-research", action="store_true")
    args = parser.parse_args(argv)
    os.environ["AINO_PRIVACY_MODE"] = args.privacy_mode
    strategy = _strategy()
    output_dir = args.output_dir or Path(str(strategy["trend_scout"]["output_dir"]))
    result = discover_and_plan(limit=args.limit, strategy=strategy, allow_network_research=args.allow_network_research)
    json_path, md_path = write_report(result, output_dir)
    print(json.dumps({"json": str(json_path), "markdown": str(md_path), "selected_count": result.selected_count}, ensure_ascii=False))
    return 0 if result.selected_count else 2


if __name__ == "__main__":
    raise SystemExit(main())
