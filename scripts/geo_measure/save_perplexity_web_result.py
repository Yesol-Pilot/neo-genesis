#!/usr/bin/env python3
"""Save Perplexity web UI response to citations.sqlite3.

Usage:
    python save_perplexity_web_result.py --prompt-id def-01 --response-file response.txt

Or programmatic:
    save_response(prompt_id, prompt_text, prompt_category, response_text, citation_urls)
"""
from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timezone
from pathlib import Path

# Import analyze function from main script
ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
from measure_citations import analyze, BRAND_PATTERNS  # noqa: E402

DB = ROOT / "citations.sqlite3"


def save_response(
    prompt_id: str,
    prompt_text: str,
    prompt_category: str,
    response_text: str,
    citation_urls_external: list[str] | None = None,
    provider: str = "perplexity_web",
    model: str = "perplexity-sonar-web",
) -> dict:
    """Save a manually-captured web UI response with analysis."""
    analysis = analyze(response_text)
    # Merge external citation URLs (from Perplexity sources panel) with text-extracted URLs
    urls = sorted(set(analysis["urls"]) | set(citation_urls_external or []))

    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "provider": provider,
        "model": model,
        "prompt_id": prompt_id,
        "prompt_category": prompt_category,
        "prompt_text": prompt_text,
        "response_text": response_text,
        "response_tokens": len(response_text.split()),  # approx
        "mention_neo_genesis": analysis["counts"]["neo_genesis"],
        "mention_domain_root": analysis["counts"]["domain_root"],
        "mention_domain_subs": analysis["counts"]["domain_subs"],
        "mention_sbu_total": analysis["sbu_total"],
        "mention_founder": analysis["counts"]["founder"],
        "sentiment": analysis["sentiment"],
        "citation_urls": json.dumps(urls, ensure_ascii=False),
        "error": None,
    }

    con = sqlite3.connect(DB)
    con.execute(
        """INSERT INTO measurements (
            timestamp, provider, model, prompt_id, prompt_category, prompt_text,
            response_text, response_tokens,
            mention_neo_genesis, mention_domain_root, mention_domain_subs,
            mention_sbu_total, mention_founder, sentiment, citation_urls, error
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
        (
            record["timestamp"], record["provider"], record["model"],
            record["prompt_id"], record["prompt_category"], record["prompt_text"],
            record["response_text"], record["response_tokens"],
            record["mention_neo_genesis"], record["mention_domain_root"],
            record["mention_domain_subs"], record["mention_sbu_total"],
            record["mention_founder"], record["sentiment"],
            record["citation_urls"], record["error"],
        ),
    )
    con.commit()
    new_id = con.execute("SELECT last_insert_rowid()").fetchone()[0]
    con.close()

    return {
        "id": new_id,
        "mention_neo_genesis": record["mention_neo_genesis"],
        "mention_domain_root": record["mention_domain_root"],
        "mention_sbu_total": record["mention_sbu_total"],
        "urls": urls,
        "sentiment": record["sentiment"],
        "any_brand_signal": bool(
            record["mention_neo_genesis"] or record["mention_sbu_total"] or urls
        ),
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--prompt-id", required=True)
    p.add_argument("--prompt-text", required=True)
    p.add_argument("--prompt-category", required=True)
    p.add_argument("--response-text", required=True, help="Response text or @path/to/file")
    p.add_argument("--provider", default="perplexity_web")
    p.add_argument("--model", default="perplexity-sonar-web")
    args = p.parse_args()

    response_text = args.response_text
    if response_text.startswith("@"):
        response_text = Path(response_text[1:]).read_text(encoding="utf-8")

    result = save_response(
        prompt_id=args.prompt_id,
        prompt_text=args.prompt_text,
        prompt_category=args.prompt_category,
        response_text=response_text,
        provider=args.provider,
        model=args.model,
    )
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
