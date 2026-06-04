#!/usr/bin/env python3
"""Strategy v1.5 — re-analyze existing 786 measurements with expanded detection.

Improvements over original analyze():
1. URL detection: capture HF/Wikidata/GitHub/heoyesol.kr in addition to neogenesis.app
2. Same-window comparison (pre 6d vs post 6d, not asymmetric)
3. Search-mode tagging (perplexity=search, others=no-search by default)
4. Subdomain-specific SBU tracking
5. Bare hostname detection (no https:// prefix)
"""
from __future__ import annotations

import json
import os
import re
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path


ROOT = Path(__file__).resolve().parent
DB = ROOT / "citations.sqlite3"

# Expanded URL patterns
URL_RE = re.compile(r"https?://[^\s\)\]\>\"]+")
BARE_HOST_RE = re.compile(r"\b([a-z0-9][a-z0-9-]*\.)+(?:app|com|kr|dev|org|io|co)\b", re.IGNORECASE)

# Expanded brand patterns (Strategy v1.5)
BRAND_PATTERNS_V1_5 = {
    "neo_genesis":      re.compile(r"\b(neo[\s-]?genesis|네오제네시스)\b", re.IGNORECASE),
    "neogenesislab":    re.compile(r"\bneogenesislab\b", re.IGNORECASE),  # HF/GitHub org
    "domain_root":      re.compile(r"\bneogenesis\.app\b", re.IGNORECASE),
    "domain_subs":      re.compile(r"\b\w+\.neogenesis\.app\b", re.IGNORECASE),
    "heoyesol":         re.compile(r"\bheoyesol\.kr\b", re.IGNORECASE),
    "wikidata_qid":     re.compile(r"Q1395696[18]0|Q13956971[68]", re.IGNORECASE),
    "hf_neogenesislab": re.compile(r"huggingface\.co/(?:datasets/)?neogenesislab/", re.IGNORECASE),
    "github_yesol":     re.compile(r"github\.com/Yesol-Pilot\b", re.IGNORECASE),
    # SBU-specific
    "toolpick":         re.compile(r"\btoolpick(\.dev)?\b", re.IGNORECASE),
    "kott":             re.compile(r"\bk[\s-]?ott(\.kr)?\b", re.IGNORECASE),
    "ur_wrong":         re.compile(r"\bur[\s-]?wrong(\.com)?\b", re.IGNORECASE),
    "whylab":           re.compile(r"\bwhylab\b", re.IGNORECASE),
    "ethicaai":         re.compile(r"\bethica[\s-]?ai\b", re.IGNORECASE),
    "aiforge":          re.compile(r"\baiforge\b", re.IGNORECASE),
    "craftdesk":        re.compile(r"\bcraftdesk\b", re.IGNORECASE),
    "deploystack":      re.compile(r"\bdeploystack\b", re.IGNORECASE),
    "finstack":         re.compile(r"\bfinstack\b", re.IGNORECASE),
    "sellkit":          re.compile(r"\bsellkit\b", re.IGNORECASE),
    "reviewlab":        re.compile(r"\b(reviewlab|review[\s-]?lab)\b", re.IGNORECASE),
    "founder":          re.compile(r"\b(yesol[\s-]?heo|허예솔|heo[\s-]?yesol)\b", re.IGNORECASE),
}

# All URL patterns we want to capture
URL_BRAND_KEYWORDS = [
    "neogenesis", "neogenesislab",
    "toolpick.dev", "ur-wrong.com", "kott.kr",
    "heoyesol.kr",
    "huggingface.co/datasets/neogenesislab",
    "wikidata.org/wiki/Q139569680",
    "wikidata.org/wiki/Q139569716",
    "wikidata.org/wiki/Q139569718",
    "github.com/Yesol-Pilot",
    "github.com/neogenesislab",
]


# Provider → search-mode classification
PROVIDER_SEARCH_MODE = {
    "perplexity": "search",
    "openai": "no-search",  # gpt-4o without web tool
    "anthropic": "no-search",  # Claude without web search
    "gemini": "no-search",  # Gemini default no grounding
}


def analyze_v1_5(text: str) -> dict:
    """Expanded analysis."""
    counts = {k: len(p.findall(text)) for k, p in BRAND_PATTERNS_V1_5.items()}
    sbu_total = sum(
        counts[k] for k in (
            "toolpick", "kott", "ur_wrong", "whylab", "ethicaai",
            "aiforge", "craftdesk", "deploystack", "finstack", "sellkit", "reviewlab",
        )
    )
    # URL extraction with expanded filter
    found_urls = set()
    for url in URL_RE.findall(text):
        if any(kw.lower() in url.lower() for kw in URL_BRAND_KEYWORDS):
            found_urls.add(url)
    # Also catch bare hostnames in text (no https://)
    for match in BARE_HOST_RE.findall(text.lower() if False else text):
        pass  # match here is a tuple from BARE_HOST_RE groups
    bare_hosts = set()
    for full_match in BARE_HOST_RE.finditer(text):
        host = full_match.group(0).lower()
        if any(kw.lower() in host for kw in ["neogenesis", "toolpick.dev", "ur-wrong.com", "kott.kr", "heoyesol.kr"]):
            bare_hosts.add(host)
    return {
        "counts": counts,
        "sbu_total": sbu_total,
        "urls_found": sorted(found_urls),
        "bare_hosts_found": sorted(bare_hosts),
        "any_url_brand": bool(found_urls or bare_hosts),
    }


def main() -> None:
    if not DB.exists():
        print(f"DB not found: {DB}")
        return

    con = sqlite3.connect(DB)
    cur = con.execute(
        "SELECT id, timestamp, provider, prompt_id, prompt_category, response_text, "
        "mention_neo_genesis, mention_domain_root, citation_urls "
        "FROM measurements ORDER BY timestamp"
    )
    rows = cur.fetchall()
    print(f"Loaded {len(rows)} measurements")

    # Re-analyze with v1.5
    stats_pre = defaultdict(lambda: defaultdict(int))   # pre = before 2026-05-04
    stats_post = defaultdict(lambda: defaultdict(int))  # post = >= 2026-05-08 (6d window for symmetry)
    by_provider = defaultdict(lambda: defaultdict(lambda: defaultdict(int)))
    examples = []

    # Determine symmetric windows
    # Pre = 2026-04-28 to 2026-05-03 (6 days, before strategy v1.0)
    # Post = 2026-05-09 to 2026-05-14 (6 days, after strategy v1.0~v1.4)
    PRE_START, PRE_END = "2026-04-28", "2026-05-04"
    POST_START, POST_END = "2026-05-09", "2026-05-15"

    for rid, ts, prov, prompt_id, cat, response, m_neo_old, m_url_old, cit_old in rows:
        result = analyze_v1_5(response or "")
        window = None
        if PRE_START <= ts < PRE_END:
            window = "pre"
        elif POST_START <= ts < POST_END:
            window = "post"

        if window:
            bucket = stats_pre if window == "pre" else stats_post
            bucket[prov]["total"] += 1
            bucket[prov]["mention_neo"] += 1 if result["counts"]["neo_genesis"] > 0 else 0
            bucket[prov]["mention_url"] += 1 if result["counts"]["domain_root"] > 0 else 0
            bucket[prov]["mention_subs"] += 1 if result["counts"]["domain_subs"] > 0 else 0
            bucket[prov]["mention_hf"] += 1 if result["counts"]["hf_neogenesislab"] > 0 else 0
            bucket[prov]["mention_wikidata"] += 1 if result["counts"]["wikidata_qid"] > 0 else 0
            bucket[prov]["mention_github"] += 1 if result["counts"]["github_yesol"] > 0 else 0
            bucket[prov]["mention_heoyesol"] += 1 if result["counts"]["heoyesol"] > 0 else 0
            bucket[prov]["any_url_brand"] += 1 if result["any_url_brand"] else 0
            bucket[prov]["sbu_total_count"] += result["sbu_total"]
            bucket[prov]["mention_founder"] += 1 if result["counts"]["founder"] > 0 else 0

            # Track examples with URL or HF mentions (rare positive signal)
            if result["urls_found"] or result["bare_hosts_found"] or result["counts"]["hf_neogenesislab"] or result["counts"]["wikidata_qid"]:
                examples.append({
                    "ts": ts,
                    "provider": prov,
                    "prompt_id": prompt_id,
                    "urls": result["urls_found"][:3],
                    "bare_hosts": result["bare_hosts_found"][:3],
                    "hf_mentions": result["counts"]["hf_neogenesislab"],
                    "wikidata_mentions": result["counts"]["wikidata_qid"],
                    "github_mentions": result["counts"]["github_yesol"],
                    "response_snippet": (response or "")[:300],
                })

    # Print symmetric report
    print()
    print("=" * 80)
    print(f"STRATEGY v1.5 SAME-WINDOW REPORT")
    print(f"  PRE  window: {PRE_START} ~ {PRE_END}  (6 days, before v1.0)")
    print(f"  POST window: {POST_START} ~ {POST_END}  (6 days, after v1.0~v1.4)")
    print("=" * 80)

    for prov in ("openai", "gemini", "anthropic", "perplexity"):
        pre = stats_pre.get(prov, {})
        post = stats_post.get(prov, {})
        pre_n = pre.get("total", 0)
        post_n = post.get("total", 0)

        print(f"\n[{prov}]  pre_n={pre_n}  post_n={post_n}")
        if pre_n == 0 and post_n == 0:
            print(f"  *** NO MEASUREMENTS for this provider -- METHODOLOGY GAP ***")
            continue
        if pre_n == 0 or post_n == 0:
            print(f"  *** ASYMMETRIC SAMPLE -- cannot compute lift ***")
            continue

        for metric in ("mention_neo", "mention_url", "mention_subs", "mention_hf",
                       "mention_wikidata", "mention_github", "mention_heoyesol",
                       "any_url_brand", "mention_founder"):
            pre_rate = 100 * pre.get(metric, 0) / pre_n
            post_rate = 100 * post.get(metric, 0) / post_n
            lift = post_rate - pre_rate
            marker = "↑" if lift > 0 else ("↓" if lift < 0 else "·")
            print(f"  {metric:18s}  {pre_rate:5.1f}%  →  {post_rate:5.1f}%   {lift:+5.1f}pp {marker}")

    # Positive signal examples
    print()
    print("=" * 80)
    print(f"POSITIVE SIGNAL EXAMPLES (URL/HF/Wikidata mentions in any window)")
    print("=" * 80)
    print(f"Total positive examples found: {len(examples)}")
    for ex in examples[:5]:
        print(f"\n  [{ex['ts'][:19]}] {ex['provider']} / {ex['prompt_id']}")
        if ex['urls']:
            print(f"    URLs:        {ex['urls']}")
        if ex['bare_hosts']:
            print(f"    Bare hosts:  {ex['bare_hosts']}")
        if ex['hf_mentions']:
            print(f"    HF mentions: {ex['hf_mentions']}")
        if ex['wikidata_mentions']:
            print(f"    Wikidata:    {ex['wikidata_mentions']}")
        print(f"    Snippet:     {ex['response_snippet'][:200]}...")

    # Total summary
    print()
    print("=" * 80)
    print("AGGREGATE (all providers combined)")
    print("=" * 80)

    def agg(stats):
        out = defaultdict(int)
        for prov_stats in stats.values():
            for k, v in prov_stats.items():
                out[k] += v
        return out

    a_pre = agg(stats_pre)
    a_post = agg(stats_post)
    pre_n = a_pre["total"]
    post_n = a_post["total"]
    print(f"pre_n={pre_n}  post_n={post_n}")
    for metric in ("mention_neo", "mention_url", "mention_subs", "mention_hf",
                   "mention_wikidata", "any_url_brand", "mention_founder"):
        pre_rate = 100 * a_pre.get(metric, 0) / pre_n if pre_n else 0
        post_rate = 100 * a_post.get(metric, 0) / post_n if post_n else 0
        lift = post_rate - pre_rate
        marker = "UP" if lift > 0 else ("DOWN" if lift < 0 else "FLAT")
        print(f"  {metric:18s}  {pre_rate:5.1f}%  ->  {post_rate:5.1f}%   {lift:+5.1f}pp  {marker}")


if __name__ == "__main__":
    main()
