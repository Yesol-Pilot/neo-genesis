#!/usr/bin/env python3
"""Check if any AI responses in citations.sqlite3 cited Neo Genesis blog posts."""
import sqlite3
import json
from pathlib import Path

DB = Path(__file__).parent / "geo_measure" / "citations.sqlite3"

# Top 26 blog slugs we care about
SLUGS = [
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

# Keywords associated with each blog topic (search heuristic)
BLOG_KEYWORDS = {
    "vscore-quality-gating": ["V-Score", "184.5", "quality gating"],
    "inside-hive-mind": ["HIVE MIND", "hive mind"],
    "kott-ai-recommendations": ["K-OTT", "kott"],
    "deploystack-vercel-vs-netlify": ["DeployStack", "Vercel vs Netlify"],
    "hivemind-vs-langgraph-multi-agent-2026": ["LangGraph", "HIVE MIND"],
    "self-optimizing-seo-engine": ["self-optimizing SEO"],
    "open-source-research": ["NeurIPS", "Zenodo DOI"],
    "ethicaai-mixed-safe-vs-anthropic-constitutional-ai-2026": ["EthicaAI", "Constitutional AI"],
    "whylab-docker-validation-vs-rubric-scoring-2026": ["WhyLab", "Docker validation"],
    "sora-orchestrator-vs-openai-agents-sdk-2026": ["Sora Orchestrator", "Agents SDK"],
}


def main():
    if not DB.exists():
        print(f"DB not found: {DB}")
        return

    con = sqlite3.connect(DB)
    total = con.execute("SELECT COUNT(*) FROM measurements").fetchone()[0]
    print(f"Total measurements: {total}")
    print()

    # Check 1: any response that mentions specific blog URL?
    print("=== Check 1: Direct blog URL citations ===")
    direct_cites = 0
    for slug in SLUGS:
        url = f"neogenesis.app/blog/{slug}"
        c = con.execute(
            "SELECT COUNT(*) FROM measurements WHERE response_text LIKE ?",
            (f"%{url}%",),
        ).fetchone()[0]
        if c > 0:
            direct_cites += c
            print(f"  [{c:>3d} HITS] {slug}")
    if direct_cites == 0:
        print("  NO direct blog URL citations in 786 AI responses")

    # Check 2: keyword-based pickup (proxy for content topic recognition)
    print()
    print("=== Check 2: Keyword pickup (blog topic in AI response) ===")
    keyword_hits = []
    for slug, keywords in BLOG_KEYWORDS.items():
        for kw in keywords:
            c = con.execute(
                "SELECT COUNT(*) FROM measurements WHERE response_text LIKE ?",
                (f"%{kw}%",),
            ).fetchone()[0]
            if c > 0:
                keyword_hits.append((slug, kw, c))

    if keyword_hits:
        for slug, kw, c in sorted(keyword_hits, key=lambda x: -x[2]):
            print(f"  [{c:>3d} HITS] {kw!r} → topic: {slug}")
    else:
        print("  NO keyword pickup in 786 AI responses")

    # Check 3: SBU brand recognition (existing metric)
    print()
    print("=== Check 3: SBU brand mentions across all measurements ===")
    for kw in ("Neo Genesis", "ToolPick", "K-OTT", "UR WRONG", "WhyLab", "EthicaAI",
              "DeployStack", "SellKit", "FinStack", "AIForge", "CraftDesk", "ReviewLab"):
        c = con.execute(
            "SELECT COUNT(*) FROM measurements WHERE LOWER(response_text) LIKE ?",
            (f"%{kw.lower()}%",),
        ).fetchone()[0]
        rate = 100.0 * c / total if total else 0
        marker = "STRONG" if rate >= 10 else ("OK" if rate >= 3 else "WEAK")
        print(f"  [{rate:>5.1f}% {marker:>6s}] {kw!r}: {c}/{total} responses")

    # Check 4: HF dataset citations
    print()
    print("=== Check 4: Hugging Face dataset citations ===")
    hf_total = con.execute(
        "SELECT COUNT(*) FROM measurements WHERE response_text LIKE '%neogenesislab%'"
    ).fetchone()[0]
    print(f"  neogenesislab namespace mentions: {hf_total}/{total} ({100*hf_total/total:.1f}%)")
    for ds in ("korean-rag-ssot", "ethicaai-mixed-safe", "whylab-gemini-2-5", "sbu-pseo"):
        c = con.execute(
            "SELECT COUNT(*) FROM measurements WHERE response_text LIKE ?",
            (f"%{ds}%",),
        ).fetchone()[0]
        print(f"  Dataset {ds!r}: {c}")


if __name__ == "__main__":
    main()
