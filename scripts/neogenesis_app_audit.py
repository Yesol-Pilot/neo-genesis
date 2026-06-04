#!/usr/bin/env python3
"""neogenesis.app 본 사이트 종합 audit -- sitemap + AI agent surface + key pages."""
import urllib.request
import urllib.error
import xml.etree.ElementTree as ET
import re
import time
from collections import defaultdict


def fetch(url, method="GET"):
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(url, method=method, headers={"User-Agent": "neo-audit/1.0"})
        r = urllib.request.urlopen(req, timeout=30)
        body = r.read() if method == "GET" else b""
        return {
            "status": r.status,
            "size": len(body) if method == "GET" else int(r.headers.get("Content-Length", 0)),
            "ms": (time.monotonic() - t0) * 1000,
            "body": body.decode("utf-8", errors="replace") if method == "GET" else "",
            "headers": dict(r.headers),
        }
    except urllib.error.HTTPError as e:
        return {"status": e.code, "size": 0, "ms": (time.monotonic() - t0) * 1000, "body": "", "headers": {}}
    except Exception as e:
        return {"status": 0, "size": 0, "ms": (time.monotonic() - t0) * 1000, "body": "", "error": str(e)[:60]}


def main():
    print("=" * 80)
    print("Neo Genesis App -- Full Site Audit")
    print(f"Generated: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 80)

    # 1. AI agent surface files
    print("\n[1] AI AGENT SURFACE FILES")
    surface = {
        "/robots.txt": "AI bot allowlist (25 explicitly allowed)",
        "/llms.txt": "LLM-friendly site index",
        "/llms-full.txt": "Full content for AI agents (~80% token reduction)",
        "/sitemap.xml": "Sitemap (90 URLs)",
        "/rss.xml": "RSS feed",
        "/feed.json": "JSON feed",
        "/humans.txt": "Human-readable",
        "/.well-known/security.txt": "Security policy",
    }
    for path, desc in surface.items():
        r = fetch(f"https://neogenesis.app{path}")
        ok = "OK" if r["status"] == 200 else "FAIL"
        print(f"  [{ok:4s}] {r['status']} {r['ms']:>5.0f}ms {r['size']/1024:>5.1f}KB  {path:30s} | {desc}")

    # 2. robots.txt key directives
    r = fetch("https://neogenesis.app/robots.txt")
    if r["status"] == 200:
        ai_bots = re.findall(r"User-agent:\s*(\S+)", r["body"], re.IGNORECASE)
        ai_specific = [b for b in ai_bots if any(p in b.lower() for p in
                       ("gpt", "claude", "perplexity", "google", "bing", "bytespider",
                        "ccbot", "ai", "applebot", "openai", "duckduck", "yandex",
                        "naver", "kakao", "facebookbot"))]
        print(f"\n  AI bots explicitly listed in robots.txt: {len(ai_specific)}")
        for b in sorted(set(ai_specific))[:30]:
            print(f"    - {b}")

    # 3. llms.txt structure
    r = fetch("https://neogenesis.app/llms.txt")
    if r["status"] == 200:
        lines = r["body"].split("\n")
        sections = sum(1 for l in lines if l.startswith("## "))
        links = len(re.findall(r"\[.*?\]\(.*?\)", r["body"]))
        print(f"\n  llms.txt: {len(lines)} lines, {sections} sections, {links} links")

    # 4. llms-full.txt structure
    r = fetch("https://neogenesis.app/llms-full.txt")
    if r["status"] == 200:
        chars = len(r["body"])
        wc = len(r["body"].split())
        print(f"  llms-full.txt: {chars:,} chars, ~{wc:,} words")

    # 5. Core pages (non-blog)
    print("\n[2] CORE PAGES")
    pages = [
        ("/", "Homepage"),
        ("/about", "About / Founder"),
        ("/faq", "FAQ"),
        ("/cite", "Citation guide"),
        ("/press", "Press kit"),
        ("/awards", "Awards"),
        ("/data", "Research data hub"),
        ("/data/research", "Research papers"),
        ("/data/quant", "Quant data"),
        ("/blog", "Blog index"),
        ("/docs", "Docs index"),
        ("/wikipedia-drafts", "Wikipedia drafts"),
        ("/tools", "Tools (intent route)"),
        ("/sales", "Sales (intent route)"),
        ("/devops", "DevOps (intent route)"),
        ("/finance", "Finance (intent route)"),
        ("/ai", "AI (intent route)"),
        ("/ops", "Operations (intent route)"),
        ("/kr", "Korean (intent route)"),
        ("/labs", "Labs (intent route)"),
    ]

    for path, desc in pages:
        r = fetch(f"https://neogenesis.app{path}")
        if r["status"] == 200 and r["body"]:
            # Extract title + jsonld count + has Yesol
            m = re.search(r"<title[^>]*>(.*?)</title>", r["body"], re.IGNORECASE | re.DOTALL)
            title = (m.group(1).strip() if m else "")[:50].encode("ascii", "replace").decode("ascii")
            jsonld_count = len(re.findall(r'<script\s+type=["\']application/ld\+json', r["body"]))
            yesol_count = len(re.findall(r"Yesol\s*Heo|허예솔", r["body"]))
            print(f"  [{r['status']}] {r['ms']:>5.0f}ms {r['size']/1024:>5.1f}KB {jsonld_count:>2d}JL Y{yesol_count:>2d} {path:25s} | {title}")
        else:
            print(f"  [{r['status']}] {r['ms']:>5.0f}ms {'---':>10s} {path:25s} | {desc} (FAILED)")

    # 6. Wikipedia drafts (interesting)
    print("\n[3] WIKIPEDIA DRAFTS (notability seed)")
    r = fetch("https://neogenesis.app/wikipedia-drafts")
    if r["status"] == 200:
        # Find linked sub-pages
        sub_pages = re.findall(r'href="(/wikipedia-drafts/[^"]+)"', r["body"])
        sub_pages = sorted(set(sub_pages))
        print(f"  Found {len(sub_pages)} sub-pages:")
        for sp in sub_pages[:10]:
            r2 = fetch(f"https://neogenesis.app{sp}", method="HEAD")
            print(f"    [{r2['status']}] {sp}")


if __name__ == "__main__":
    main()
