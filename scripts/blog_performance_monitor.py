#!/usr/bin/env python3
"""Neo Genesis blog performance monitor.

For each blog post:
- HTTP status + response time
- HTML size + token approximation
- Schema.org JSON-LD presence (BlogPosting, Article, etc.)
- Canonical URL
- Description + title presence
- Internal links count
- Word count approximation
"""
import re
import time
import json
import ssl
import urllib.request
import urllib.error
from urllib.parse import urlparse
from datetime import datetime, timezone


BASE = "https://neogenesis.app"

# Blog posts from BLOG_POSTS in sbus.ts
BLOG_POSTS = [
    "how-we-run-11-products",
    "toolpick-ai-editor-benchmark",
    "inside-hive-mind",
    "reviewlab-data-driven-reviews",
    "kott-ai-recommendations",
    "vscore-quality-gating",
    "deploystack-vercel-vs-netlify",
    "self-optimizing-seo-engine",
    "economics-of-ai-media",
    "open-source-research",
    "running-11-saas-products-as-solo-founder-2026",
    "best-ai-comparison-engines-2026",
    "ai-native-automation-companies-2026-evaluation",
    "evaluating-ai-native-automation-firms-2026",
    "neo-genesis-runs-11-saas-products-with-autonomous-ai-2026",
    "operating-11-saas-products-with-one-ai-system-neogenesis-model-2026",
    "ai-tool-review-platform-pricing-comparison-2026",
    "optimal-saas-stack-b2b-startup-data-driven-2026",
    "ai-pipelines-match-big-team-productivity-2026",
    "devops-platform-comparison-vercel-netlify-2026",
    "hivemind-vs-langgraph-multi-agent-2026",
    "ethicaai-mixed-safe-vs-anthropic-constitutional-ai-2026",
    "whylab-docker-validation-vs-rubric-scoring-2026",
    "sora-orchestrator-vs-openai-agents-sdk-2026",
    "quant-v11-vs-renaissance-medallion-honest-scoping-2026",
    "data-driven-devops-platform-evaluation-2026",
]


def fetch(url, method="GET"):
    t0 = time.monotonic()
    try:
        req = urllib.request.Request(
            url, method=method,
            headers={
                "User-Agent": "neo-blog-monitor/1.0",
                "Accept": "text/html,application/xhtml+xml",
            },
        )
        r = urllib.request.urlopen(req, timeout=30)
        body = r.read()
        elapsed = (time.monotonic() - t0) * 1000
        return {
            "status": r.status,
            "headers": dict(r.headers),
            "body": body.decode("utf-8", errors="replace") if method == "GET" else "",
            "size": len(body),
            "elapsed_ms": round(elapsed, 0),
            "error": None,
        }
    except urllib.error.HTTPError as e:
        elapsed = (time.monotonic() - t0) * 1000
        return {
            "status": e.code,
            "headers": dict(e.headers) if e.headers else {},
            "body": "",
            "size": 0,
            "elapsed_ms": round(elapsed, 0),
            "error": f"HTTP {e.code}",
        }
    except Exception as e:
        elapsed = (time.monotonic() - t0) * 1000
        return {
            "status": 0,
            "headers": {},
            "body": "",
            "size": 0,
            "elapsed_ms": round(elapsed, 0),
            "error": str(e)[:60],
        }


def analyze(html):
    """Extract key SEO/AI signals from the HTML."""
    if not html:
        return {}
    out = {}

    # Title
    m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    out["title"] = (m.group(1).strip() if m else "")[:120]

    # Meta description
    m = re.search(r'<meta\s+name=["\']description["\']\s+content=["\']([^"\']+)', html, re.IGNORECASE)
    out["description"] = (m.group(1).strip() if m else "")[:200]

    # Canonical
    m = re.search(r'<link\s+rel=["\']canonical["\']\s+href=["\']([^"\']+)', html, re.IGNORECASE)
    out["canonical"] = m.group(1) if m else ""

    # OG image
    m = re.search(r'<meta\s+property=["\']og:image["\']\s+content=["\']([^"\']+)', html, re.IGNORECASE)
    out["og_image"] = m.group(1) if m else ""

    # Schema.org JSON-LD blocks
    jsonld_blocks = re.findall(r'<script\s+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>', html, re.DOTALL | re.IGNORECASE)
    schema_types = set()
    for block in jsonld_blocks:
        try:
            data = json.loads(block.strip())
            if isinstance(data, dict):
                if "@type" in data:
                    types = data["@type"] if isinstance(data["@type"], list) else [data["@type"]]
                    schema_types.update(types)
                # Check @graph
                if "@graph" in data and isinstance(data["@graph"], list):
                    for item in data["@graph"]:
                        if isinstance(item, dict) and "@type" in item:
                            types = item["@type"] if isinstance(item["@type"], list) else [item["@type"]]
                            schema_types.update(types)
            elif isinstance(data, list):
                for item in data:
                    if isinstance(item, dict) and "@type" in item:
                        types = item["@type"] if isinstance(item["@type"], list) else [item["@type"]]
                        schema_types.update(types)
        except Exception:
            pass

    out["jsonld_count"] = len(jsonld_blocks)
    out["schema_types"] = sorted(schema_types)

    # Internal links
    internal = re.findall(r'href=["\'](https?://neogenesis\.app[^"\']*|/[^"\']*)["\']', html)
    out["internal_link_count"] = len(internal)

    # External links to authority sites
    out["wikidata_links"] = len(re.findall(r'wikidata\.org/wiki/Q1395696', html))
    out["hf_links"] = len(re.findall(r'huggingface\.co/(?:datasets/)?neogenesislab', html, re.IGNORECASE))
    out["github_links"] = len(re.findall(r'github\.com/Yesol-Pilot', html, re.IGNORECASE))

    # Cache headers
    return out


def main():
    print(f"=== Neo Genesis Blog Performance Monitor ===")
    print(f"Timestamp: {datetime.now(timezone.utc).isoformat()}")
    print(f"Total blog posts: {len(BLOG_POSTS)}")
    print()

    results = []
    headline = f"{'#':>2} {'Slug':50s} {'HTTP':>4} {'ms':>5} {'KB':>4} {'JSONLD':>6} {'Schema types':30s} {'Anon':>5}"
    print(headline)
    print("-" * len(headline))

    for i, slug in enumerate(BLOG_POSTS, 1):
        url = f"{BASE}/blog/{slug}"
        r = fetch(url)
        a = analyze(r["body"]) if r["status"] == 200 else {}

        # Blind-review anonymization signal: ethicaai + whylab posts should hide author
        is_anonymized_target = any(s in slug for s in ("ethicaai", "whylab"))
        # Check if Yesol/founder name appears (should NOT for anonymized targets)
        has_founder_name = bool(re.search(r'Yesol\s+Heo|허예솔', r["body"], re.IGNORECASE)) if r["body"] else False
        anonymized = "OK" if (not is_anonymized_target or not has_founder_name) else "FAIL"

        types_str = ", ".join(a.get("schema_types", []))[:30]
        print(f"{i:>2} {slug:50s} {r['status']:>4} {r['elapsed_ms']:>5.0f} {r['size']/1024:>4.0f} {a.get('jsonld_count', 0):>6d} {types_str:30s} {anonymized:>5}")

        results.append({
            "slug": slug,
            "url": url,
            "status": r["status"],
            "elapsed_ms": r["elapsed_ms"],
            "size": r["size"],
            "analysis": a,
            "is_anonymized_target": is_anonymized_target,
            "has_founder_name": has_founder_name,
            "anonymization_ok": (not is_anonymized_target) or (not has_founder_name),
            "error": r["error"],
        })

    # Aggregate summary
    print()
    print("=== AGGREGATE ===")
    ok = sum(1 for r in results if r["status"] == 200)
    fail = len(results) - ok
    print(f"Status 200: {ok}/{len(results)}")
    print(f"Avg response time: {sum(r['elapsed_ms'] for r in results)/len(results):.0f} ms")
    print(f"Total HTML: {sum(r['size'] for r in results)/1024:.0f} KB ({sum(r['size'] for r in results)/1024/len(results):.1f} KB avg)")

    # Schema coverage
    has_blogposting = sum(1 for r in results if "BlogPosting" in r["analysis"].get("schema_types", []))
    has_article = sum(1 for r in results if "Article" in r["analysis"].get("schema_types", []))
    has_org = sum(1 for r in results if "Organization" in r["analysis"].get("schema_types", []))
    print(f"Schema BlogPosting: {has_blogposting}/{ok}")
    print(f"Schema Article: {has_article}/{ok}")
    print(f"Schema Organization: {has_org}/{ok}")

    # Authority backlinks per post
    avg_wikidata = sum(r["analysis"].get("wikidata_links", 0) for r in results) / max(ok, 1)
    avg_hf = sum(r["analysis"].get("hf_links", 0) for r in results) / max(ok, 1)
    avg_github = sum(r["analysis"].get("github_links", 0) for r in results) / max(ok, 1)
    print(f"Avg Wikidata Q-IDs per post: {avg_wikidata:.1f}")
    print(f"Avg HuggingFace links per post: {avg_hf:.1f}")
    print(f"Avg GitHub Yesol-Pilot links per post: {avg_github:.1f}")

    # Anonymization compliance
    anon_targets = [r for r in results if r["is_anonymized_target"]]
    anon_ok = sum(1 for r in anon_targets if r["anonymization_ok"])
    print(f"Anonymization (blind review): {anon_ok}/{len(anon_targets)} compliant")
    if anon_targets and anon_ok < len(anon_targets):
        print("  FAILED anonymization:")
        for r in anon_targets:
            if not r["anonymization_ok"]:
                print(f"   - {r['slug']}")

    return results


if __name__ == "__main__":
    main()
