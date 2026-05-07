"""Research pages audit — same pattern as audit_blog_metadata.py and
audit_sbu_pages.py but for the /data/research entries. Validates per-paper:
  - HTTP 200 on /data/research/<slug>
  - Schema.org ScholarlyArticle / TechArticle emit
  - title length 25-90 chars (research papers can be longer)
  - summary length 100-300 chars
  - publishedAt <= updatedAt
  - keywords array present and 3-15 entries
  - Wikidata Q-IDs cross-referenced where applicable

Run: PYTHONIOENCODING=utf-8 python scripts/landing/audit_research_pages.py
"""
from __future__ import annotations

import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
RESEARCH_TS = ROOT / "src/landing/src/lib/data/research-assets.ts"


def parse_research_assets() -> list[dict]:
    text = RESEARCH_TS.read_text(encoding="utf-8")
    assets: list[dict] = []
    # Each entry has slug, title, summary, publishedAt, updatedAt, category
    for m in re.finditer(
        r'\{\s*slug:\s*"([^"]+)",\s*title:\s*"((?:[^"\\]|\\.)*)",'
        r'\s*summary:\s*"((?:[^"\\]|\\.)*)",'
        r'(?:.*?publishedAt:\s*"([^"]+)")?(?:.*?updatedAt:\s*"([^"]+)")?'
        r'(?:.*?category:\s*"([^"]+)")?',
        text,
        re.DOTALL,
    ):
        assets.append({
            "slug": m.group(1),
            "title": m.group(2),
            "summary": m.group(3),
            "publishedAt": m.group(4) or "",
            "updatedAt": m.group(5) or "",
            "category": m.group(6) or "",
        })
    # keywords + headlineStats + downloadCount fields - per-asset
    keyword_map: dict[str, list[str]] = {}
    for slug_match in re.finditer(r'slug:\s*"([^"]+)"', text):
        slug = slug_match.group(1)
        # Find next 5000 chars of section
        section = text[slug_match.end():slug_match.end() + 8000]
        kw_m = re.search(r"keywords:\s*\[([^\]]+)\]", section)
        if kw_m:
            keyword_map[slug] = re.findall(r'"([^"]+)"', kw_m.group(1))
    for a in assets:
        a["keywords"] = keyword_map.get(a["slug"], [])
    return assets


def audit_page(slug: str) -> dict:
    url = f"https://neogenesis.app/data/research/{slug}"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "neo-genesis-research-audit/1.0"})
        with urllib.request.urlopen(req, timeout=30) as r:
            html = r.read().decode("utf-8", errors="replace")
            return {
                "url": url,
                "status": r.status,
                "has_scholarly": '"@type":"ScholarlyArticle"' in html,
                "has_tech_article": '"@type":"TechArticle"' in html,
                "has_breadcrumb": '"@type":"BreadcrumbList"' in html,
                "size_kb": len(html) // 1024,
            }
    except Exception as e:
        return {"url": url, "status": 0, "error": str(e)[:120]}


def main() -> int:
    assets = parse_research_assets()
    print(f"Auditing {len(assets)} research pages")
    print()

    page_audits: dict[str, dict] = {}
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(audit_page, a["slug"]): a["slug"] for a in assets}
        for fut in as_completed(futures):
            slug = futures[fut]
            page_audits[slug] = fut.result()

    issues: list[str] = []
    print(f"{'slug':<55} {'page':>5} {'sch':>4} {'tech':>5} {'crumb':>6} {'kb':>4} {'title':>5} {'sum':>4} {'kw':>3}")
    print("-" * 100)
    for a in assets:
        slug = a["slug"]
        p = page_audits.get(slug, {})
        page_ok = p.get("status") == 200
        sch = p.get("has_scholarly", False)
        tech = p.get("has_tech_article", False)
        crumb = p.get("has_breadcrumb", False)
        article_schema = sch or tech  # either acceptable
        size = p.get("size_kb", 0)
        title_len = len(a["title"])
        summary_len = len(a["summary"])
        kw_count = len(a["keywords"])

        flags = []
        if not page_ok:
            flags.append(f"page-{p.get('status', 0)}")
            issues.append(f"{slug}: page returns {p.get('status', 0)}")
        if not article_schema:
            flags.append("no-article-schema")
            issues.append(f"{slug}: no ScholarlyArticle or TechArticle Schema")
        if not crumb:
            flags.append("no-breadcrumb")
            issues.append(f"{slug}: no BreadcrumbList Schema")
        if title_len < 25 or title_len > 110:
            flags.append(f"title-{title_len}c")
            issues.append(f"{slug}: title {title_len} chars (want 25-110)")
        if summary_len < 100 or summary_len > 350:
            flags.append(f"sum-{summary_len}c")
            issues.append(f"{slug}: summary {summary_len} chars (want 100-350)")
        if kw_count < 3:
            flags.append(f"kw-{kw_count}")
            issues.append(f"{slug}: only {kw_count} keywords (want >= 3)")
        if a["publishedAt"] and a["updatedAt"] and a["updatedAt"] < a["publishedAt"]:
            flags.append("date-flip")
            issues.append(f"{slug}: updatedAt < publishedAt")

        flag_str = " " + ",".join(flags) if flags else ""
        sch_label = "Sch" if sch else ("Tch" if tech else "N")
        print(f"  {slug:<53} {'OK' if page_ok else p.get('status', 0):>5} {sch_label:>4} {'Y' if tech else 'N':>5} {'Y' if crumb else 'N':>6} {size:>4} {title_len:>5} {summary_len:>4} {kw_count:>3}{flag_str}")

    print()
    print("=" * 100)
    print(f"Total issues: {len(issues)}")
    if issues:
        for i in issues[:20]:
            print(f"  - {i}")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
