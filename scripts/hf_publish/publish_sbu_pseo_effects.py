"""
HuggingFace Datasets publish — SBU Programmatic SEO Effects (April 2026)

Publishes the operational publish/refresh effects of running 8 active SBUs
(programmatic-SEO multi-tenant blogs) under one solo founder, aggregated to
per-SBU-per-snapshot rows. NO user IDs, NO IP addresses, NO author identities,
NO Supabase row IDs, NO commit SHAs, NO post slugs, NO URLs — only counts.

Data sources (D:/00.test/neo-genesis/data/sbu-growth/):
  - quality-repair-*.json   one row per SBU per run with weakPostsExpanded /
                            weakPostsReinforced / internalLinksAdded /
                            intentRoutesAdded / filesChanged
  - control-tower-latest.json   per-SBU enrichment (category, posts.total,
                                avgWords, ctaCoverage, internalLinkCoverage,
                                modeledMau)

Target : huggingface.co/datasets/neogenesislab/sbu-pseo-effects-2026-04

Layout:
  README.md                   bilingual ko + en dataset card with YAML frontmatter
  data/snapshots.jsonl        aggregated per-SBU-per-snapshot rows
  data/aggregate_summary.json totals + per-SBU averages
  metadata.json               benchmark meta (name / version / schema / etc.)

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/publish_sbu_pseo_effects.py
"""
from __future__ import annotations

import io
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = ROOT / ".env.local"
SBU_GROWTH_DIR = ROOT / "data" / "sbu-growth"
REPO_ID = "neogenesislab/sbu-pseo-effects-2026-04"

# Allowed SBU slugs (anonymization whitelist — anything outside is dropped).
KNOWN_SBUS = {
    "toolpick",
    "aiforge",
    "finstack",
    "sellkit",
    "deploystack",
    "craftdesk",
    "reviewlab",
    "ur-wrong",
}

# Per-SBU canonical category (filled from control-tower or fallback table).
DEFAULT_CATEGORY_BY_SBU = {
    "toolpick": "comparison",
    "aiforge": "ai_tools",
    "finstack": "fintech",
    "sellkit": "ecommerce",
    "deploystack": "devops",
    "craftdesk": "design",
    "reviewlab": "reviews",
    "ur-wrong": "general",
}


def load_env(path: Path) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def parse_snapshot_date(filename: str) -> str | None:
    """quality-repair-2026-04-27T13-22-13-09-00.json -> '2026-04-27'."""
    m = re.match(r"quality-repair-(\d{4}-\d{2}-\d{2})T", filename)
    if not m:
        return None
    return m.group(1)


def parse_snapshot_iso(filename: str) -> str | None:
    """quality-repair-2026-04-27T13-22-13-09-00.json -> '2026-04-27T13:22:13+09:00'."""
    m = re.match(
        r"quality-repair-(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-(\d{2})-(\d{2})-(\d{2})\.json",
        filename,
    )
    if not m:
        return None
    date, hh, mm, ss, oh, omm = m.groups()
    return f"{date}T{hh}:{mm}:{ss}+{oh}:{omm}"


def safe_int(v) -> int:
    try:
        n = int(v)
        return n if n >= 0 else 0
    except (TypeError, ValueError):
        return 0


def safe_float(v) -> float | None:
    try:
        f = float(v)
        if f != f:  # NaN guard
            return None
        return f
    except (TypeError, ValueError):
        return None


def load_control_tower_categories() -> dict[str, dict]:
    """Pull per-SBU enrichment (category proxy via topPosting category, modeledMau, etc.)."""
    out: dict[str, dict] = {}
    ct_path = SBU_GROWTH_DIR / "control-tower-latest.json"
    if not ct_path.exists():
        return out
    try:
        with ct_path.open(encoding="utf-8") as f:
            ct = json.load(f)
    except Exception:
        return out
    for site in ct.get("sites", []):
        sid = site.get("id")
        if sid not in KNOWN_SBUS:
            continue
        local = site.get("local", {}) or {}
        posts = local.get("posts", {}) or {}
        latest = posts.get("latest", {}) or {}
        out[sid] = {
            "category": (latest.get("category") or DEFAULT_CATEGORY_BY_SBU.get(sid, "general")).lower().replace(" ", "_"),
            "total_ready_posts": safe_int(posts.get("ready") or posts.get("total")),
            "avg_words": safe_int(posts.get("avgWords")),
            "category_count": safe_int(posts.get("categoryCount")),
            "cta_coverage": safe_float(posts.get("ctaCoverage")),
            "internal_link_coverage": safe_float(posts.get("internalLinkCoverage")),
            "frontmatter_coverage": safe_float(posts.get("frontmatterCoverage")),
            "modeled_mau": safe_int(posts.get("modeledMau")),
        }
    return out


def collect_snapshots() -> tuple[list[dict], dict]:
    """Iterate quality-repair-*.json files, return per-SBU-per-snapshot rows + meta."""
    if not SBU_GROWTH_DIR.exists():
        raise SystemExit(f"ERROR: source dir not found: {SBU_GROWTH_DIR}")

    enrichment = load_control_tower_categories()

    rows: list[dict] = []
    seen_keys: set[tuple[str, str, str]] = set()  # (sbu, date, iso) dedup
    snapshot_dates: set[str] = set()
    file_count = 0

    for path in sorted(SBU_GROWTH_DIR.glob("quality-repair-*.json")):
        # Skip the "latest" symlink-style file — it duplicates the freshest timestamped file
        if path.name == "quality-repair-latest.json":
            continue
        date = parse_snapshot_date(path.name)
        iso = parse_snapshot_iso(path.name)
        if not date or not iso:
            continue
        try:
            with path.open(encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            print(f"WARN: failed to read {path.name}: {e}", file=sys.stderr)
            continue
        if data.get("dryRun") is True:
            # Dry-runs are simulated counts — not real publish effects. Skip them.
            continue
        file_count += 1
        snapshot_dates.add(date)

        for site in data.get("sites", []) or []:
            sbu = (site.get("site") or "").strip().lower()
            if sbu not in KNOWN_SBUS:
                continue  # anonymization whitelist
            key = (sbu, date, iso)
            if key in seen_keys:
                continue  # idempotent: drop exact duplicate writes from the same run
            seen_keys.add(key)

            enriched = enrichment.get(sbu, {})
            row = {
                "sbu_slug": sbu,
                "category": enriched.get("category") or DEFAULT_CATEGORY_BY_SBU.get(sbu, "general"),
                "snapshot_date": date,
                "snapshot_iso": iso,
                "weak_posts_expanded": safe_int(site.get("weakPostsExpanded")),
                "weak_posts_reinforced": safe_int(site.get("weakPostsReinforced")),
                "internal_links_added": safe_int(site.get("internalLinksAdded")),
                "intent_routes_added": safe_int(site.get("intentRoutesAdded")),
                "files_changed": safe_int(site.get("filesChanged")),
                "clusters_routed": safe_int(data.get("clustersRouted")),
                # SBU-level enrichment from control-tower-latest (snapshot scope = "current state")
                "total_ready_posts": enriched.get("total_ready_posts", 0),
                "avg_words": enriched.get("avg_words", 0),
                "category_count": enriched.get("category_count", 0),
                "cta_coverage": enriched.get("cta_coverage"),
                "internal_link_coverage": enriched.get("internal_link_coverage"),
                "frontmatter_coverage": enriched.get("frontmatter_coverage"),
                "modeled_mau": enriched.get("modeled_mau", 0),
            }
            rows.append(row)

    # Stable sort: snapshot_iso then sbu_slug
    rows.sort(key=lambda r: (r["snapshot_iso"], r["sbu_slug"]))

    meta = {
        "source_files_scanned": file_count,
        "snapshot_date_count": len(snapshot_dates),
        "snapshot_date_min": min(snapshot_dates) if snapshot_dates else None,
        "snapshot_date_max": max(snapshot_dates) if snapshot_dates else None,
        "row_count": len(rows),
        "sbus_present": sorted({r["sbu_slug"] for r in rows}),
        "enrichment_present_for": sorted(enrichment.keys()),
    }
    return rows, meta


def assert_anonymized(rows: list[dict]) -> None:
    """Defense-in-depth check: no obvious PII fields in the row payload."""
    forbidden_keys = {
        "user_id", "userId", "ip", "ip_address", "author", "author_email",
        "email", "supabase_id", "row_id", "commit", "commit_sha", "sha",
        "post_slug", "slug", "url", "post_url", "user", "username",
    }
    forbidden_value_patterns = [
        re.compile(r"^[a-f0-9]{40}$"),               # bare git SHA
        re.compile(r"@[a-z0-9.-]+\.[a-z]{2,}$", re.I),  # email-like
        re.compile(r"^https?://"),                    # URL
    ]
    for r in rows:
        for k, v in r.items():
            if k in forbidden_keys:
                raise SystemExit(f"ANON FAIL: forbidden key {k!r} in row")
            if isinstance(v, str):
                for pat in forbidden_value_patterns:
                    if pat.search(v):
                        raise SystemExit(f"ANON FAIL: value matches forbidden pattern in {k!r}: {v!r}")


def build_aggregate_summary(rows: list[dict], scan_meta: dict) -> dict:
    """Per-SBU rollup + global totals."""
    by_sbu: dict[str, dict] = {}
    for r in rows:
        s = by_sbu.setdefault(r["sbu_slug"], {
            "sbu_slug": r["sbu_slug"],
            "category": r["category"],
            "snapshot_count": 0,
            "weak_posts_expanded_total": 0,
            "weak_posts_reinforced_total": 0,
            "internal_links_added_total": 0,
            "intent_routes_added_total": 0,
            "files_changed_total": 0,
            "clusters_routed_total": 0,
            # Latest snapshot enrichment carried forward
            "latest_total_ready_posts": 0,
            "latest_avg_words": 0,
            "latest_category_count": 0,
            "latest_cta_coverage": None,
            "latest_internal_link_coverage": None,
            "latest_frontmatter_coverage": None,
            "latest_modeled_mau": 0,
        })
        s["snapshot_count"] += 1
        s["weak_posts_expanded_total"] += r["weak_posts_expanded"]
        s["weak_posts_reinforced_total"] += r["weak_posts_reinforced"]
        s["internal_links_added_total"] += r["internal_links_added"]
        s["intent_routes_added_total"] += r["intent_routes_added"]
        s["files_changed_total"] += r["files_changed"]
        s["clusters_routed_total"] += r["clusters_routed"]
        # Replace with latest each time (rows are pre-sorted by iso)
        s["latest_total_ready_posts"] = r["total_ready_posts"]
        s["latest_avg_words"] = r["avg_words"]
        s["latest_category_count"] = r["category_count"]
        s["latest_cta_coverage"] = r["cta_coverage"]
        s["latest_internal_link_coverage"] = r["internal_link_coverage"]
        s["latest_frontmatter_coverage"] = r["frontmatter_coverage"]
        s["latest_modeled_mau"] = r["modeled_mau"]

    # Per-SBU averages (per-snapshot)
    for s in by_sbu.values():
        n = max(1, s["snapshot_count"])
        s["weak_posts_expanded_avg_per_snapshot"] = round(s["weak_posts_expanded_total"] / n, 3)
        s["weak_posts_reinforced_avg_per_snapshot"] = round(s["weak_posts_reinforced_total"] / n, 3)
        s["files_changed_avg_per_snapshot"] = round(s["files_changed_total"] / n, 3)

    totals = {
        "total_rows": len(rows),
        "total_snapshots_scanned": scan_meta.get("source_files_scanned", 0),
        "snapshot_date_min": scan_meta.get("snapshot_date_min"),
        "snapshot_date_max": scan_meta.get("snapshot_date_max"),
        "weak_posts_expanded_total": sum(r["weak_posts_expanded"] for r in rows),
        "weak_posts_reinforced_total": sum(r["weak_posts_reinforced"] for r in rows),
        "internal_links_added_total": sum(r["internal_links_added"] for r in rows),
        "intent_routes_added_total": sum(r["intent_routes_added"] for r in rows),
        "files_changed_total": sum(r["files_changed"] for r in rows),
        "sbus_with_activity": sorted(by_sbu.keys()),
    }
    return {"totals": totals, "by_sbu": sorted(by_sbu.values(), key=lambda x: x["sbu_slug"])}


def build_metadata(rows: list[dict], summary: dict, scan_meta: dict) -> dict:
    return {
        "name": "Neo Genesis SBU Programmatic SEO Effects",
        "version": "2026-04",
        "release_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "license": "CC-BY-4.0",
        "languages": ["ko", "en"],
        "tags": [
            "programmatic-seo",
            "ai-content",
            "marketing-data",
            "multi-tenant-blog",
            "operations",
            "1-person-startup",
            "ko",
            "en",
        ],
        "schema": {
            "sbu_slug": "Active SBU identifier (one of toolpick / aiforge / finstack / sellkit / deploystack / craftdesk / reviewlab / ur-wrong)",
            "category": "Coarse content category proxy (e.g. comparison, ai_tools, fintech, ecommerce, devops, design)",
            "snapshot_date": "ISO date the publish/refresh batch ran (KST day)",
            "snapshot_iso": "Full ISO 8601 timestamp of the publish/refresh batch (KST tz)",
            "weak_posts_expanded": "Number of low-quality posts the auto-publisher expanded in this run",
            "weak_posts_reinforced": "Number of posts whose CTA / internal links were reinforced in this run",
            "internal_links_added": "Internal links inserted across the SBU in this run",
            "intent_routes_added": "Search-intent routes (category landings) added in this run",
            "files_changed": "MDX files modified in this run (publish + refresh combined)",
            "clusters_routed": "Topic clusters routed in this run (run-scope, repeated per SBU row)",
            "total_ready_posts": "Latest control-tower SBU-level: posts that pass the publish gate",
            "avg_words": "Latest control-tower SBU-level: average word count of MDX content",
            "category_count": "Latest control-tower SBU-level: distinct content categories on the site",
            "cta_coverage": "Latest control-tower SBU-level: 0..1 share of posts with a CTA block",
            "internal_link_coverage": "Latest control-tower SBU-level: 0..1 share of posts with internal links",
            "frontmatter_coverage": "Latest control-tower SBU-level: 0..1 share of posts with complete frontmatter",
            "modeled_mau": "Latest control-tower SBU-level: modeled monthly visits (350/post baseline)",
        },
        "anonymization": {
            "policy": "operational counts only",
            "stripped_fields": [
                "user_id", "ip_address", "author_identity",
                "supabase_row_id", "commit_sha", "post_slug", "url",
            ],
            "aggregation_grain": "per_sbu_per_snapshot",
        },
        "source": {
            "directory": "data/sbu-growth/",
            "input_files_scanned": scan_meta.get("source_files_scanned", 0),
            "input_pattern": "quality-repair-YYYY-MM-DDThh-mm-ss-09-00.json",
            "dry_run_files_excluded": True,
            "control_tower_enrichment": "control-tower-latest.json (snapshot scope = current state at publish time)",
        },
        "totals": summary["totals"],
        "row_count": len(rows),
    }


def build_readme(summary: dict, scan_meta: dict) -> str:
    n = summary["totals"]["total_rows"]
    sbus = summary["totals"]["sbus_with_activity"]
    sbu_count = len(sbus)
    date_min = summary["totals"].get("snapshot_date_min") or "n/a"
    date_max = summary["totals"].get("snapshot_date_max") or "n/a"
    snaps = summary["totals"]["total_snapshots_scanned"]

    by_sbu_rows = []
    for s in summary["by_sbu"]:
        by_sbu_rows.append(
            "| `{slug}` | `{cat}` | {snaps} | {expanded} | {reinforced} | {files} | {posts} | {mau:,} |".format(
                slug=s["sbu_slug"],
                cat=s["category"],
                snaps=s["snapshot_count"],
                expanded=s["weak_posts_expanded_total"],
                reinforced=s["weak_posts_reinforced_total"],
                files=s["files_changed_total"],
                posts=s["latest_total_ready_posts"],
                mau=s["latest_modeled_mau"],
            )
        )
    by_sbu_table = "\n".join(by_sbu_rows)

    sbu_links_md = "\n".join(
        f"- [`{slug}`](https://neogenesis.app/sbu/{slug}) (category: `{DEFAULT_CATEGORY_BY_SBU.get(slug, 'general')}`)"
        for slug in sbus
    )

    yaml_front = f"""---
language:
- ko
- en
license: cc-by-4.0
task_categories:
- tabular-classification
- tabular-regression
tags:
- programmatic-seo
- ai-content
- marketing-data
- multi-tenant-blog
- operations
- 1-person-startup
- ko
- en
size_categories:
- n<1K
pretty_name: Neo Genesis SBU Programmatic SEO Effects (April 2026)
configs:
- config_name: default
  data_files:
  - split: train
    path: data/snapshots.jsonl
---
"""

    body = f"""
# Neo Genesis SBU Programmatic SEO Effects (April 2026)

> A transparent operational dataset of how a **1-person AI company runs {sbu_count} active programmatic-SEO SBUs** ([Neo Genesis](https://neogenesis.app)), aggregated to **{n} per-SBU-per-snapshot rows** spanning **{date_min} → {date_max}**.

## Why this dataset exists

Most SEO datasets are scraped surface metrics (rankings, organic visits) or vendor case studies that hide the publishing pipeline.
This dataset shows the **other side** — the publish/refresh / weak-post-repair / internal-link operations that produce those rankings — for a real fleet of multi-tenant blogs that one founder operates with AI agents.

It is published as **operational data**, not a product benchmark. Treat it as a window into how programmatic-SEO content ops actually behave on a live, autonomously-managed multi-blog network.

## Dataset summary

- **{n} rows** (one per SBU per publish/refresh batch)
- **{sbu_count} active SBUs** covered: {", ".join(f"`{s}`" for s in sbus)}
- **{snaps} source snapshot files** scanned (`quality-repair-*.json`, dry-runs excluded)
- **Window**: {date_min} → {date_max}
- **Anonymization**: no user IDs, no IPs, no author identities, no Supabase row IDs, no commit SHAs, no post slugs, no URLs — only counts and per-SBU rollups
- **Aggregation grain**: per SBU per publish/refresh batch

## Per-SBU rollup

| SBU | Category | Snapshots | Weak-posts expanded | Weak-posts reinforced | Files changed | Latest ready posts | Latest modeled MAU |
|---|---|---|---|---|---|---|---|
{by_sbu_table}

## Active SBUs (live URLs)

{sbu_links_md}

## Schema

Each row in `data/snapshots.jsonl`:

```json
{{
  "sbu_slug": "toolpick",
  "category": "comparison",
  "snapshot_date": "2026-04-27",
  "snapshot_iso": "2026-04-27T13:23:01+09:00",
  "weak_posts_expanded": 2,
  "weak_posts_reinforced": 0,
  "internal_links_added": 0,
  "intent_routes_added": 0,
  "files_changed": 2,
  "clusters_routed": 0,
  "total_ready_posts": 379,
  "avg_words": 1350,
  "category_count": 60,
  "cta_coverage": 0.72,
  "internal_link_coverage": 0.887,
  "frontmatter_coverage": 1.0,
  "modeled_mau": 132650
}}
```

| Field | Meaning |
|---|---|
| `sbu_slug` | SBU identifier (one of `toolpick` / `aiforge` / `finstack` / `sellkit` / `deploystack` / `craftdesk` / `reviewlab` / `ur-wrong`) |
| `category` | Coarse content category proxy (`comparison`, `ai_tools`, `fintech`, `ecommerce`, `devops`, `design`, `reviews`, `general`) |
| `snapshot_date` | ISO date of the publish/refresh batch (KST day) |
| `snapshot_iso` | Full ISO 8601 timestamp (KST tz) |
| `weak_posts_expanded` | Low-quality posts expanded in this run |
| `weak_posts_reinforced` | Posts whose CTA / internal links were reinforced in this run |
| `internal_links_added` | Internal links inserted in this run |
| `intent_routes_added` | Search-intent routes (category landings) added in this run |
| `files_changed` | MDX files modified in this run |
| `clusters_routed` | Topic clusters routed in this run (run-scope) |
| `total_ready_posts` | Latest SBU-level: posts that pass the publish gate |
| `avg_words` | Latest SBU-level: average word count |
| `category_count` | Latest SBU-level: distinct content categories on the site |
| `cta_coverage` | Latest SBU-level: 0..1 share of posts with a CTA block |
| `internal_link_coverage` | Latest SBU-level: 0..1 share of posts with internal links |
| `frontmatter_coverage` | Latest SBU-level: 0..1 share with complete frontmatter |
| `modeled_mau` | Latest SBU-level: modeled monthly visits (350/post baseline) |

## Quick start

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", split="train")
print(ds[0])
# => {{'sbu_slug': 'toolpick', 'category': 'comparison', ...}}

# Total weak posts repaired across all SBUs in the window
print(sum(r["weak_posts_expanded"] + r["weak_posts_reinforced"] for r in ds))
```

## Anonymization & ethics

This dataset is published as transparent operational telemetry. The following are **never** included:

- user IDs, sessions, IPs, geo
- author identities, emails, usernames
- Supabase row IDs, internal database keys
- commit SHAs, branch names, deploy IDs
- post slugs, URLs, draft titles
- visitor analytics, GA4 / PostHog identifiers

Only **operational counts** (how many MDX files were touched, how many weak posts were expanded, how many internal links were added) and **SBU-level aggregates** (total ready posts, average word count, coverage ratios, modeled MAU) are exposed.

The aggregation grain is `per_sbu_per_snapshot` — there is no row that resolves to a single piece of content or a single user action.

## Use cases

- **Programmatic SEO research**: empirical baselines for "how many MDX files per SBU per refresh cycle"
- **AI content operations**: prior data for autonomous publishing pipelines (multi-tenant blog factories)
- **Founder ops benchmarking**: comparison data for solo / 1-person AI companies running content fleets
- **Marketing automation modeling**: input for CTA / internal-link coverage progression over time

## Comparison to typical SEO datasets

| Source | Surface metrics (rankings / GSC) | Publishing pipeline counts | Multi-tenant network | Anonymized | License |
|---|---|---|---|---|---|
| Ahrefs / Semrush case data | ✓ | — | — | partial | proprietary |
| Common Crawl WARC | ✓ (raw HTML) | — | — | — | open |
| GSC dumps | ✓ | — | per-domain | partial | private |
| **Neo Genesis SBU pSEO Effects** | — | **✓** | **✓** | **✓** | **CC-BY-4.0** |

## Provenance

- Source       : Neo Genesis live `data/sbu-growth/` operational logs
- Curator      : Yesol Heo (sole founder/operator, [neogenesis.app](https://neogenesis.app))
- Generator    : `sbu_growth_quality_repair.mjs` running under `sbu_autonomous_growth_runner.mjs`
- Wikidata     : [Q139569680 (Neo Genesis)](https://www.wikidata.org/wiki/Q139569680)
- Sister datasets:
  - [`neogenesislab/korean-rag-ssot-golden-50`](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50)
  - [`neogenesislab/ethicaai-mixed-safe-evidence`](https://huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence)
  - [`neogenesislab/whylab-gemini-2-5-docker-validation`](https://huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation)

## Citation

```bibtex
@misc{{neogenesis_sbu_pseo_effects_2026_04,
  title  = {{Neo Genesis SBU Programmatic SEO Effects (April 2026)}},
  author = {{Heo, Yesol}},
  year   = {{2026}},
  url    = {{https://huggingface.co/datasets/{REPO_ID}}},
  note   = {{Neo Genesis, an AI-native automation company running 11 live business units of which 8 are programmatic-SEO SBUs}}
}}
```

## License

**CC-BY-4.0** — free for research and commercial use with attribution to Neo Genesis.

---

## 한국어 요약

**SBU Programmatic SEO Effects (April 2026)** 는 1인 AI 자동화 기업 **[Neo Genesis](https://neogenesis.app)** 가 운영 중인 **{sbu_count}개 SBU 프로그래매틱 SEO 블로그**의 발행/리프레시 파이프라인 운영 데이터를 익명화 집계한 것이다.

기존 SEO 데이터셋이 `랭킹 / 트래픽` 같은 노출 지표만 다룬다면, 이 데이터셋은 그 결과를 만들어내는 **퍼블리싱 파이프라인 자체** (`약한 글 보강`, `내부 링크 삽입`, `MDX 파일 변경 수`) 를 SBU 단위로 보여준다.

집계 단위:
- 행 단위: **`SBU × 발행/리프레시 배치`**
- 발행 일자 범위: **{date_min} → {date_max}**
- 행 수: **{n}**
- 스캔된 원본 스냅샷 파일: **{snaps}**

익명화 정책:
- `user_id`, `ip`, `author`, `supabase_id`, `commit_sha`, `slug`, `url` 모두 제거
- SBU 단위 + 스냅샷 단위 집계만 공개

라이선스 CC-BY-4.0 — 인용 시 자유롭게 사용 가능.
"""
    return yaml_front + body


def main() -> int:
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN not found in env (.env.local)", file=sys.stderr)
        return 1

    print(f"Source dir: {SBU_GROWTH_DIR}")
    rows, scan_meta = collect_snapshots()
    if not rows:
        print("ERROR: no rows collected — check that quality-repair-*.json files exist and are not all dryRun", file=sys.stderr)
        return 1

    print(f"Collected {len(rows)} rows from {scan_meta['source_files_scanned']} non-dry-run snapshot files")
    print(f"  date range: {scan_meta['snapshot_date_min']} → {scan_meta['snapshot_date_max']}")
    print(f"  SBUs present: {', '.join(scan_meta['sbus_present'])}")

    # Anonymization defense-in-depth
    assert_anonymized(rows)
    print("Anonymization check: PASS")

    summary = build_aggregate_summary(rows, scan_meta)
    metadata = build_metadata(rows, summary, scan_meta)
    readme = build_readme(summary, scan_meta)

    snapshots_jsonl = "\n".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows
    ) + "\n"
    summary_json = json.dumps(summary, ensure_ascii=False, indent=2)
    metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)

    artifacts = [
        ("README.md", readme.encode("utf-8")),
        ("data/snapshots.jsonl", snapshots_jsonl.encode("utf-8")),
        ("data/aggregate_summary.json", summary_json.encode("utf-8")),
        ("metadata.json", metadata_json.encode("utf-8")),
    ]

    print("\nArtifact sizes:")
    for path, content in artifacts:
        print(f"  {path:32s} {len(content):>10,} bytes")

    from huggingface_hub import HfApi
    api = HfApi(token=token)

    print(f"\ncreate_repo {REPO_ID} (dataset, public, exist_ok=True)")
    api.create_repo(
        repo_id=REPO_ID,
        repo_type="dataset",
        exist_ok=True,
        private=False,
    )

    for path_in_repo, content in artifacts:
        print(f"upload {path_in_repo}")
        api.upload_file(
            path_or_fileobj=io.BytesIO(content),
            path_in_repo=path_in_repo,
            repo_id=REPO_ID,
            repo_type="dataset",
            commit_message=f"add {path_in_repo}",
        )

    url = f"https://huggingface.co/datasets/{REPO_ID}"
    print()
    print("PUBLISHED:", url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
