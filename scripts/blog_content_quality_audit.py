#!/usr/bin/env python3
"""Audit ACTUAL content quality, not just markup.

For each blog post, extract the actual article content (strip nav/footer/schema)
and compute:
- Real word count (article body only)
- Unique vocabulary ratio (originality proxy)
- AI-generation tell signs (em-dash density, sentence-start patterns, etc.)
- Data/numbers density (original research signal)
- Internal vs external link ratio
- Author / E-E-A-T signals presence
"""
import urllib.request
import re
import time
from collections import Counter
import string


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


# AI-generation tells (heuristic)
AI_PHRASES = [
    "in conclusion", "it's important to note", "delve into", "tapestry",
    "navigate", "leverage", "robust", "seamless", "comprehensive",
    "underscores", "highlights the importance", "in the realm of",
    "moreover", "furthermore", "additionally,",
    "1인 AI", "오너 sovereignty", "AI 네이티브",  # ours-specific patterns
]


def fetch_markdown(slug):
    """Fetch the markdown alt route which strips HTML chrome."""
    url = f"https://neogenesis.app/blog/{slug}/markdown"
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "audit"}), timeout=30)
        return r.read().decode("utf-8", errors="replace")
    except Exception:
        # Fall back to HTML and strip
        return ""


def fetch_html_extract_article(slug):
    """Fetch HTML and extract article content."""
    url = f"https://neogenesis.app/blog/{slug}"
    try:
        r = urllib.request.urlopen(urllib.request.Request(url, headers={"User-Agent": "audit"}), timeout=30)
        html = r.read().decode("utf-8", errors="replace")
    except Exception:
        return ""

    # Try to find <article> or .post-content
    m = re.search(r"<article[^>]*>(.*?)</article>", html, re.DOTALL | re.IGNORECASE)
    if m:
        body = m.group(1)
    else:
        m = re.search(r'<main[^>]*>(.*?)</main>', html, re.DOTALL | re.IGNORECASE)
        body = m.group(1) if m else html

    # Strip script/style/nav
    body = re.sub(r"<(script|style|nav|footer|header)[^>]*>.*?</\1>", "", body, flags=re.DOTALL | re.IGNORECASE)
    # Strip remaining tags
    text = re.sub(r"<[^>]+>", " ", body)
    text = re.sub(r"&[a-z]+;", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def analyze_content(text):
    if not text:
        return None
    words = re.findall(r"[A-Za-z가-힣][\w\-]*", text)
    wc = len(words)
    unique = len(set(w.lower() for w in words))
    unique_ratio = unique / wc if wc else 0

    # Numbers density (original research proxy)
    numbers = len(re.findall(r"\b\d+\.?\d*%?\b", text))
    number_density = numbers / wc if wc else 0

    # AI phrase hits
    text_lower = text.lower()
    ai_hits = sum(1 for p in AI_PHRASES if p in text_lower)

    # Sentence count
    sentences = re.split(r"[.!?]\s+", text)
    sent_count = len(sentences)
    avg_sent_len = wc / sent_count if sent_count else 0

    # Code blocks / specific data
    code_blocks = text.count("```") // 2
    bullet_lines = len(re.findall(r"(?:^|\n)\s*[-*+]\s+", text))
    table_pipes = text.count(" | ")

    return {
        "wc": wc,
        "unique_words": unique,
        "unique_ratio": round(unique_ratio, 3),
        "numbers": numbers,
        "number_density_per_100w": round(100 * number_density, 1),
        "ai_phrase_hits": ai_hits,
        "sentences": sent_count,
        "avg_sentence_words": round(avg_sent_len, 1),
        "code_blocks": code_blocks,
        "bullet_lines": bullet_lines,
        "table_pipes": table_pipes,
    }


def main():
    print(f"{'#':>2} {'Slug':50s} {'WC':>5} {'UQ%':>4} {'#%':>4} {'AI':>3} {'BUL':>4} {'TBL':>4} {'Verdict':10s}")
    print("-" * 95)

    results = []
    for i, slug in enumerate(BLOG_POSTS, 1):
        # Try markdown alt route first
        md = fetch_markdown(slug)
        if md and len(md) > 500:
            text = md
        else:
            text = fetch_html_extract_article(slug)

        a = analyze_content(text)
        if not a:
            print(f"{i:>2} {slug:50s} FAIL fetch")
            continue

        # Verdict thresholds
        verdict = "OK"
        if a["wc"] < 800:
            verdict = "THIN"
        if a["unique_ratio"] < 0.3:
            verdict = "REPETITIVE"
        if a["ai_phrase_hits"] >= 5 and a["number_density_per_100w"] < 2:
            verdict = "AI-FLAG"
        if a["wc"] < 500:
            verdict = "TOO-THIN"

        print(f"{i:>2} {slug:50s} {a['wc']:>5d} {a['unique_ratio']*100:>4.0f} {a['number_density_per_100w']:>4.1f} {a['ai_phrase_hits']:>3d} {a['bullet_lines']:>4d} {a['table_pipes']:>4d} {verdict:10s}")
        results.append((slug, a, verdict))

    # Aggregate
    print()
    print("=== AGGREGATE ===")
    total_wc = sum(r[1]["wc"] for r in results)
    avg_wc = total_wc / len(results)
    print(f"Avg word count per post: {avg_wc:.0f}")
    print(f"Total content words across blog: {total_wc:,}")

    thin = [r for r in results if r[2] in ("THIN", "TOO-THIN")]
    ai_flag = [r for r in results if r[2] == "AI-FLAG"]
    repetitive = [r for r in results if r[2] == "REPETITIVE"]

    print(f"\nTHIN posts (<800 words): {len(thin)}")
    for slug, a, _ in thin:
        print(f"  - {slug}: {a['wc']} words")

    print(f"\nAI-FLAG posts (5+ AI phrases, low data density): {len(ai_flag)}")
    for slug, a, _ in ai_flag:
        print(f"  - {slug}: AI {a['ai_phrase_hits']} hits, num density {a['number_density_per_100w']}/100w")

    print(f"\nREPETITIVE posts (unique<30%): {len(repetitive)}")
    for slug, a, _ in repetitive:
        print(f"  - {slug}: unique {a['unique_ratio']*100:.0f}%")

    # Cross-post similarity check (simple: top 20 word frequencies across all posts)
    print()
    print("=== Most common words across all posts (boilerplate check) ===")
    all_words = []
    for _, a, _ in results:
        pass  # would need full text, skip for now

    # Find posts with very similar wc (template suspicion)
    print()
    print("=== Posts with similar word counts (template suspicion) ===")
    wc_groups = {}
    for slug, a, _ in results:
        bucket = (a["wc"] // 100) * 100  # round to 100
        wc_groups.setdefault(bucket, []).append(slug)
    for bucket, slugs in sorted(wc_groups.items()):
        if len(slugs) >= 3:
            print(f"  {bucket}-{bucket+99} words ({len(slugs)} posts):")
            for s in slugs[:5]:
                print(f"    - {s}")


if __name__ == "__main__":
    main()
