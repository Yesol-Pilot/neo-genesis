"""Topic gap analyzer.

Reads:
  - GEO citation SQLite DB (which prompts get 0% mention from LLMs)
  - Existing BLOG_POSTS slugs (avoid duplicates)
  - press-releases.ts slugs (avoid topical overlap)
  - research-assets.ts slugs (cross-link opportunities)

Returns priority-sorted topic candidates, with mention rate, sample prompt, and rationale.

Priority rules (high to low):
  1. GEO 0% category prompts (not yet covered by any blog) — highest leverage
  2. Recent press releases without paired blog explainer
  3. research-assets without /blog cross-link gravity
  4. Quarterly evergreen refresh (operations / engineering)
"""
from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Optional


REPO = Path(__file__).resolve().parents[2]
DB_FILE = REPO / "scripts" / "geo_measure" / "citations.sqlite3"
SBUS_TS = REPO / "src" / "landing" / "src" / "lib" / "data" / "sbus.ts"
PRESS_TS = REPO / "src" / "landing" / "src" / "lib" / "data" / "press-releases.ts"
RESEARCH_TS = REPO / "src" / "landing" / "src" / "lib" / "data" / "research-assets.ts"
BLOG_CONTENT_TS = REPO / "src" / "landing" / "src" / "lib" / "data" / "blog-content.ts"


SLUG_RE = re.compile(r'slug:\s*"([^"]+)"')
TITLE_RE = re.compile(r'title:\s*"([^"]+)"')


@dataclass
class TopicCandidate:
    priority: int  # 1 high, 5 low
    source: str  # "geo_zero" | "press_release" | "research_asset" | "evergreen"
    suggested_slug: str
    title_hint: str
    rationale: str
    sample_prompt: Optional[str] = None
    mention_rate_pct: Optional[float] = None
    related_links: list[str] = field(default_factory=list)
    target_locale: str = "en"  # "en" | "ko"


def parse_slugs_from_ts(path: Path) -> list[tuple[str, str]]:
    """Extract (slug, title) pairs from a TS file. Best-effort regex parse."""
    if not path.exists():
        return []
    text = path.read_text(encoding="utf-8")
    pairs: list[tuple[str, str]] = []
    # Match slug + title within ~600 char windows
    for m in SLUG_RE.finditer(text):
        slug = m.group(1)
        # find a title near this slug (within next 600 chars)
        nearby = text[m.end(): m.end() + 600]
        tm = TITLE_RE.search(nearby)
        title = tm.group(1) if tm else ""
        pairs.append((slug, title))
    return pairs


def load_existing_blog_slugs() -> set[str]:
    pairs = parse_slugs_from_ts(SBUS_TS)
    blog_slugs = set()
    text = SBUS_TS.read_text(encoding="utf-8") if SBUS_TS.exists() else ""
    # Limit to BLOG_POSTS section: scope after `BLOG_POSTS`
    idx = text.find("BLOG_POSTS")
    if idx >= 0:
        scoped = text[idx:]
        for m in SLUG_RE.finditer(scoped):
            blog_slugs.add(m.group(1))
    return blog_slugs


def load_press_release_slugs() -> list[tuple[str, str]]:
    return parse_slugs_from_ts(PRESS_TS)


def load_research_slugs() -> list[tuple[str, str]]:
    return parse_slugs_from_ts(RESEARCH_TS)


def analyze_geo_gaps(min_calls: int = 3) -> list[dict[str, Any]]:
    """Return prompts ranked by 0-mention rate. Skip prompts with too few calls."""
    if not DB_FILE.exists():
        return []
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT prompt_id,
               prompt_category,
               prompt_text,
               COUNT(*) AS calls,
               SUM(CASE WHEN mention_neo_genesis > 0
                          OR mention_sbu_total > 0
                          OR mention_domain_root > 0
                        THEN 1 ELSE 0 END) AS hits
        FROM measurements
        WHERE error IS NULL OR error = ''
        GROUP BY prompt_id, prompt_category, prompt_text
        HAVING calls >= ?
        ORDER BY (1.0 * hits / calls) ASC, calls DESC
        """,
        (min_calls,),
    ).fetchall()
    conn.close()
    out = []
    for r in rows:
        rate = r["hits"] / r["calls"] if r["calls"] else 0.0
        out.append({
            "prompt_id": r["prompt_id"],
            "prompt_category": r["prompt_category"],
            "prompt_text": r["prompt_text"],
            "calls": r["calls"],
            "hits": r["hits"],
            "mention_rate": rate,
        })
    return out


def slugify(text: str, max_len: int = 75) -> str:
    s = text.lower()
    # Drop non-ASCII (Korean, etc.) — URL slugs must be ASCII for cross-platform safety
    s = "".join(c if ord(c) < 128 else " " for c in s)
    s = re.sub(r"[^a-z0-9\s-]", "", s)
    s = re.sub(r"\s+", "-", s.strip())
    s = re.sub(r"-+", "-", s)
    s = s.strip("-")
    if not s:
        s = "topic"
    return s[:max_len].strip("-")


def build_candidates() -> list[TopicCandidate]:
    """Compose a sorted candidate list."""
    existing_blog = load_existing_blog_slugs()
    press = load_press_release_slugs()
    research = load_research_slugs()
    geo = analyze_geo_gaps(min_calls=2)

    candidates: list[TopicCandidate] = []

    # 1. GEO 0% — highest priority
    for g in geo:
        if g["mention_rate"] >= 0.5:
            continue  # already covered
        is_korean = bool(re.search(r"[가-힣]", g["prompt_text"]))
        slug = slugify(g["prompt_text"][:60]).replace("--", "-").strip("-")
        if not slug:
            slug = f"geo-{g['prompt_id']}"
        slug = f"answer-{slug}-2026"[:75].strip("-")
        if slug in existing_blog:
            continue
        related = []
        # Suggest related research slugs
        for rs, _ in research[:3]:
            related.append(f"/data/research/{rs}")
        candidates.append(TopicCandidate(
            priority=1 if g["mention_rate"] == 0.0 else 2,
            source="geo_zero",
            suggested_slug=slug,
            title_hint=g["prompt_text"],
            rationale=(
                f"GEO 측정 결과 prompt category={g['prompt_category']}, "
                f"mention rate={g['mention_rate']*100:.1f}% across {g['calls']} calls. "
                f"This blog post directly answers the LLM probe."
            ),
            sample_prompt=g["prompt_text"],
            mention_rate_pct=g["mention_rate"] * 100,
            related_links=related,
            target_locale="ko" if is_korean else "en",
        ))

    # 2. Press releases without blog explainer
    for slug, title in press:
        # Generate a paired blog slug
        paired = slugify(f"explainer-{title}"[:70])
        if paired in existing_blog:
            continue
        if any(c.suggested_slug == paired for c in candidates):
            continue
        candidates.append(TopicCandidate(
            priority=3,
            source="press_release",
            suggested_slug=paired,
            title_hint=f"Engineering explainer for: {title}",
            rationale=(
                f"Press release {slug} has no paired engineering explainer blog post. "
                f"Cross-linking opportunity to deepen entity graph."
            ),
            related_links=[f"/press/{slug}"],
        ))

    # 3. Research assets without strong /blog gravity
    for slug, title in research:
        paired = slugify(f"deep-dive-{title}"[:70])
        if paired in existing_blog:
            continue
        if any(c.suggested_slug == paired for c in candidates):
            continue
        candidates.append(TopicCandidate(
            priority=4,
            source="research_asset",
            suggested_slug=paired,
            title_hint=f"Operational deep-dive: {title}",
            rationale=(
                f"Research asset {slug} is a 1st-party citation source. "
                f"A blog post translates the research into operator-facing engineering takeaways."
            ),
            related_links=[f"/data/research/{slug}"],
        ))

    # 4. Evergreen fallback
    evergreen_topics = [
        ("how-we-measure-llm-citations-2026",
         "How We Measure LLM Citations Across 4 Providers (2026 methodology)"),
        ("autonomous-deploys-without-staging-2026",
         "Autonomous Deploys Without a Staging Environment: How and When"),
        ("idempotent-content-pipeline-design-2026",
         "Designing an Idempotent Content Pipeline for AI-Generated Posts"),
        ("indexnow-bing-coverage-2026",
         "IndexNow in 2026: What Yandex, Bing, and Naver Actually Index"),
        ("schema-org-blogposting-best-practices-2026",
         "Schema.org BlogPosting in 2026: What AI Search Engines Actually Read"),
    ]
    for slug, title in evergreen_topics:
        if slug in existing_blog:
            continue
        if any(c.suggested_slug == slug for c in candidates):
            continue
        candidates.append(TopicCandidate(
            priority=5,
            source="evergreen",
            suggested_slug=slug,
            title_hint=title,
            rationale="Evergreen topic for sustained AI search relevance.",
        ))

    # Sort by priority, then GEO calls desc
    candidates.sort(
        key=lambda c: (
            c.priority,
            -1 if c.source == "geo_zero" else 0,
            -(c.mention_rate_pct if c.mention_rate_pct is not None else 0),
        )
    )
    return candidates


def select_topic(candidates: list[TopicCandidate], existing_slugs: set[str]) -> Optional[TopicCandidate]:
    """Pick the first candidate not matching any existing slug."""
    for c in candidates:
        if c.suggested_slug in existing_slugs:
            continue
        return c
    return None


def main() -> int:
    candidates = build_candidates()
    existing = load_existing_blog_slugs()
    print(json.dumps({
        "existing_blog_count": len(existing),
        "candidate_count": len(candidates),
        "top_5": [
            {
                "priority": c.priority,
                "source": c.source,
                "slug": c.suggested_slug,
                "title_hint": c.title_hint,
                "rationale": c.rationale,
                "sample_prompt": c.sample_prompt,
                "mention_rate_pct": c.mention_rate_pct,
                "target_locale": c.target_locale,
            }
            for c in candidates[:5]
        ],
    }, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
