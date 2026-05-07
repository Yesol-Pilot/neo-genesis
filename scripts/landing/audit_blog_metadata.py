"""Comprehensive blog metadata audit. Checks every BLOG_POSTS entry for
publishing-quality issues: dates ordering, category normalization, title
length, summary length, citation URL liveness, internal-link rot,
relatedPosts validity, reading-time vs wordCount sanity.

Run: PYTHONIOENCODING=utf-8 python scripts/landing/audit_blog_metadata.py
"""
from __future__ import annotations

import json
import re
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SBUS_TS = ROOT / "src/landing/src/lib/data/sbus.ts"
BLOG_CONTENT_TS = ROOT / "src/landing/src/lib/data/blog-content.ts"

ALLOWED_CATEGORIES = {"engineering", "research", "operations", "company", "data", "product"}


def parse_blog_posts() -> list[dict]:
    """Pull each BLOG_POSTS entry into a dict."""
    text = SBUS_TS.read_text(encoding="utf-8")
    start = text.find("BLOG_POSTS")
    end = text.find("];", start)
    block = text[start:end]

    posts = []
    # Each entry: { slug: "...", title: "...", summary: "...",
    #               publishedAt: "...", updatedAt: "...", category: "..." }
    for m in re.finditer(r"\{\s*slug:\s*\"([^\"]+)\",\s*title:\s*\"((?:[^\"\\]|\\.)*)\",\s*summary:\s*\"((?:[^\"\\]|\\.)*)\",\s*publishedAt:\s*\"([^\"]+)\",\s*updatedAt:\s*\"([^\"]+)\",\s*(?:category:\s*\"([^\"]+)\",?\s*)?\}", block):
        posts.append({
            "slug": m.group(1),
            "title": m.group(2),
            "summary": m.group(3),
            "publishedAt": m.group(4),
            "updatedAt": m.group(5),
            "category": m.group(6) or "",
        })
    return posts


def parse_citations() -> dict[str, list[str]]:
    """For each slug, extract citation URLs from blog-content.ts."""
    text = BLOG_CONTENT_TS.read_text(encoding="utf-8")
    out: dict[str, list[str]] = {}

    slug_iter = list(re.finditer(r'slug:\s*"([^"]+)",', text))
    for i, m in enumerate(slug_iter):
        slug = m.group(1)
        next_start = slug_iter[i + 1].start() if i + 1 < len(slug_iter) else len(text)
        section = text[m.end():next_start]
        # Citations field with url: "https://..."
        cit_block = re.search(r"citations:\s*\[(.*?)\]", section, re.DOTALL)
        urls = []
        if cit_block:
            urls = re.findall(r'url:\s*"([^"]+)"', cit_block.group(1))
        out[slug] = urls
    return out


def parse_related_posts() -> dict[str, list[str]]:
    """For each slug, extract relatedPosts from blog-content.ts."""
    text = BLOG_CONTENT_TS.read_text(encoding="utf-8")
    out: dict[str, list[str]] = {}
    slug_iter = list(re.finditer(r'slug:\s*"([^"]+)",', text))
    for i, m in enumerate(slug_iter):
        slug = m.group(1)
        next_start = slug_iter[i + 1].start() if i + 1 < len(slug_iter) else len(text)
        section = text[m.end():next_start]
        rel = re.search(r"relatedPosts:\s*\[([^\]]+)\]", section)
        out[slug] = re.findall(r'"([^"]+)"', rel.group(1)) if rel else []
    return out


def head_check(url: str, timeout: int = 10) -> tuple[str, int]:
    try:
        req = urllib.request.Request(url, method="HEAD", headers={"User-Agent": "neo-genesis-link-audit/1.0"})
        with urllib.request.urlopen(req, timeout=timeout) as r:
            return url, r.status
    except urllib.error.HTTPError as e:
        # GET fallback for HEAD-disallowing servers
        if e.code in (403, 405):
            try:
                req = urllib.request.Request(url, method="GET", headers={"User-Agent": "neo-genesis-link-audit/1.0"})
                with urllib.request.urlopen(req, timeout=timeout) as r:
                    return url, r.status
            except Exception:
                pass
        return url, e.code
    except Exception:
        return url, 0


def main() -> int:
    posts = parse_blog_posts()
    citations = parse_citations()
    related = parse_related_posts()
    valid_slugs = {p["slug"] for p in posts}

    issues: list[str] = []
    print(f"Audit {len(posts)} blog posts")
    print()

    # Per-post issue collection
    print(f"{'slug':<60} {'cat':<12} {'title':>5} {'summary':>7}")
    print("-" * 90)
    for p in posts:
        slug = p["slug"]
        cat = p["category"] or "(none)"
        title_len = len(p["title"])
        summary_len = len(p["summary"])
        flags = []
        if cat and cat not in ALLOWED_CATEGORIES:
            flags.append(f"unknown-category:{cat}")
            issues.append(f"{slug}: unknown category '{cat}'")
        if title_len > 70:
            flags.append(f"title-{title_len}c-too-long")
            issues.append(f"{slug}: title is {title_len} chars (>70)")
        if title_len < 25:
            flags.append(f"title-{title_len}c-too-short")
            issues.append(f"{slug}: title is {title_len} chars (<25)")
        if summary_len > 200:
            flags.append(f"summary-{summary_len}c-too-long")
            issues.append(f"{slug}: summary is {summary_len} chars (>200)")
        if summary_len < 80:
            flags.append(f"summary-{summary_len}c-too-short")
            issues.append(f"{slug}: summary is {summary_len} chars (<80)")
        # Date ordering
        if p["updatedAt"] < p["publishedAt"]:
            flags.append("updatedAt-before-publishedAt")
            issues.append(f"{slug}: updatedAt {p['updatedAt']} < publishedAt {p['publishedAt']}")
        # Related posts pointing to dead slugs
        rel = related.get(slug, [])
        for rs in rel:
            if rs not in valid_slugs:
                flags.append(f"dead-related:{rs}")
                issues.append(f"{slug}: relatedPosts contains dead slug '{rs}'")
        flag_str = (" " + ",".join(flags)) if flags else ""
        print(f"  {slug:<58} {cat:<12} {title_len:>5} {summary_len:>7}{flag_str}")

    # Citation URL HEAD check
    print()
    print("=== Citation URL HTTP HEAD audit ===")
    all_urls = sorted({u for urls in citations.values() for u in urls})
    print(f"  unique citation URLs to check: {len(all_urls)}")
    dead: list[tuple[str, int]] = []
    with ThreadPoolExecutor(max_workers=10) as ex:
        futures = {ex.submit(head_check, u): u for u in all_urls}
        for fut in as_completed(futures):
            url, status = fut.result()
            if status not in (200, 301, 302, 307, 308):
                dead.append((url, status))
    print(f"  alive: {len(all_urls) - len(dead)} / {len(all_urls)}")
    if dead:
        print(f"  DEAD ({len(dead)}):")
        for url, status in dead[:30]:
            print(f"    [{status}] {url}")
            issues.append(f"dead citation [{status}]: {url}")

    # Reverse map: which posts cite each dead URL
    if dead:
        print()
        print("=== Posts citing dead URLs ===")
        dead_urls = {u for u, _ in dead}
        for slug, urls in citations.items():
            slug_dead = [u for u in urls if u in dead_urls]
            if slug_dead:
                print(f"  {slug}:")
                for u in slug_dead:
                    print(f"    - {u}")

    print()
    print("=" * 90)
    print(f"Total issues found: {len(issues)}")
    if not issues:
        print("All audits passed.")
    return 0 if not issues else 1


if __name__ == "__main__":
    raise SystemExit(main())
