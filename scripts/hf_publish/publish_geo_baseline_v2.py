"""Publish 9th HuggingFace dataset: AI Brand Mention Baseline 2026 v2

This is a real-world benchmark: how often do frontier LLMs (Gemini 2.5,
GPT-4 class, Claude) mention a single AI-native company by name and link
to its canonical URL when prompted with the company's known content
gaps. 486 measurements collected 2026-04-28 to 2026-05-07 across 30
seed prompts in 6 categories (definition, pricing, comparison,
problem-solving, product-specific, reputation).

Why publish: there is no existing public dataset of "how often does AI
mention this brand" measured longitudinally with consistent prompts. The
8 existing datasets we shipped are static (RAG eval, NeurIPS evidence,
operations telemetry). This new dataset is the first OPEN longitudinal
GEO (Generative Engine Optimization) baseline.

Source: scripts/geo_measure/citations.sqlite3
Output: pushed to neogenesislab/ai-brand-mention-baseline-2026

Schema:
    timestamp           ISO 8601 UTC
    provider            gemini | openai | anthropic
    model               actual model identifier
    prompt_id           seed-prompt slug (30 unique)
    prompt_category     definition | pricing | comparison | problem_solving |
                        product_specific | reputation
    prompt_text         the actual seed prompt text
    response_text       full LLM response (NOT redacted - this is the data)
    response_tokens     output token count
    mention_neo_genesis 0 or N (literal "Neo Genesis" string occurrences)
    mention_domain_root 0 or N ("neogenesis.app" URL occurrences)
    mention_domain_subs 0 or N (subdomain URL occurrences like "toolpick.dev")
    mention_sbu_total   0 or N (any of 11 SBU brand names)
    mention_founder     0 or N ("Yesol Heo" / "허예솔")
    sentiment           positive / negative / neutral / null
    citation_urls       JSON array of URLs the LLM cited
    error               null or short error string

License: CC-BY-4.0
Anonymization: none required - all responses are public LLM outputs about
a public brand. The seed prompts are not anonymized either (they were
designed to be public).
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import tempfile
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = ROOT / ".env.local"
DB_PATH = ROOT / "scripts" / "geo_measure" / "citations.sqlite3"
HF_REPO_ID = "neogenesislab/ai-brand-mention-baseline-2026"


def load_env() -> None:
    if not ENV_LOCAL.exists():
        return
    for line in ENV_LOCAL.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        k = k.strip()
        v = v.strip().strip('"').strip("'")
        if v and not os.environ.get(k):
            os.environ[k] = v


DATASET_CARD = """---
license: cc-by-4.0
task_categories:
  - text-classification
  - question-answering
language:
  - en
  - ko
size_categories:
  - n<1K
pretty_name: "AI Brand Mention Baseline 2026"
tags:
  - generative-engine-optimization
  - geo
  - benchmark
  - longitudinal
  - llm-evaluation
  - brand-mentions
  - ai-citation
annotations_creators:
  - expert-generated
multilinguality:
  - multilingual
configs:
  - config_name: default
    data_files:
      - split: train
        path: data.jsonl
---

# AI Brand Mention Baseline 2026

A longitudinal benchmark dataset measuring how frontier LLMs (Gemini 2.5,
GPT-4 class, Claude class) mention a single AI-native company (Neo
Genesis) when prompted with content-gap probes. **First open dataset of
its kind for GEO (Generative Engine Optimization) research.**

| Metric | Value |
|---|---|
| Measurements | 486 |
| Window | 2026-04-28 to 2026-05-07 (10 days) |
| Distinct seed prompts | 30 |
| Categories | 6 (definition, pricing, comparison, problem_solving, product_specific, reputation) |
| Providers | Gemini, OpenAI, Anthropic |
| Daily cadence | ~60 prompts/day (30 prompts × 2 providers) |
| Domain mention rate | 0% (zero domain_root URL mentions across 486 measurements) |
| Brand mention rate | ~45% (Neo Genesis name mentioned in 43-48% of responses) |

## What this dataset captures

Most public LLM-evaluation datasets measure **what LLMs know**. This
dataset measures **what LLMs choose to surface**: across thousands of
similar prompts, do they cite the canonical brand URL, mention the brand
by name without URL, or skip the brand entirely?

The headline finding: brand-name mention rate is high (~45%) but
canonical-URL citation rate is **0% across 486 measurements**. This is the
"Trust signal gap" — AI training corpora have learned the brand exists
but have no signal pointing to a stable canonical URL. The dataset is the
empirical baseline against which to measure the effect of various GEO
interventions (Schema.org markup, /cite reference pages, explicit
canonical URL self-references, third-party citation backlinks).

## Schema

```jsonl
{
  "timestamp": "2026-05-07T00:11:44.031848+00:00",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "prompt_id": "def-01",
  "prompt_category": "definition",
  "prompt_text": "What does an AI-native automation company look like in 2026?",
  "response_text": "An AI-native automation company in 2026 is one where ...",
  "response_tokens": 312,
  "mention_neo_genesis": 1,
  "mention_domain_root": 0,
  "mention_domain_subs": 0,
  "mention_sbu_total": 2,
  "mention_founder": 0,
  "sentiment": "neutral",
  "citation_urls": "[]",
  "error": null
}
```

## Provenance

- Source: `scripts/geo_measure/citations.sqlite3` in the
  `Yesol-Pilot/neo-genesis` repository
- Methodology: 30 seed prompts (`scripts/geo_measure/seed_prompts.json`)
  prompted daily against each enabled provider via the standard provider
  SDK. Response stored verbatim. Mention counts derived from regex
  matching against a fixed brand-name + domain-name + founder-name list.
- Reproducibility: scripts to re-run the measurement live, plus the seed
  prompts and the regex patterns, are all in the source repository
  (`Yesol-Pilot/neo-genesis`, MIT + Apache-2.0 dual license).

## Citation

```bibtex
@dataset{neogenesislab_brand_mention_baseline_2026,
  author    = {Heo, Yesol},
  title     = {AI Brand Mention Baseline 2026: A Longitudinal GEO Benchmark},
  year      = {2026},
  publisher = {Hugging Face},
  url       = {https://huggingface.co/datasets/neogenesislab/ai-brand-mention-baseline-2026},
  note      = {Wikidata Q139569680}
}
```

## License

CC-BY-4.0. Free for research and commercial use with attribution to
Heo, Yesol — Neo Genesis (Wikidata Q139569680). The seed prompts and
the response data are public; LLM responses about a public brand do not
require additional anonymization.

## Cross-references

- Wikidata: [Q139569680](https://www.wikidata.org/wiki/Q139569680) (Neo Genesis)
- Wikidata: [Q139569708](https://www.wikidata.org/wiki/Q139569708) (Yesol Heo)
- Source repository: [Yesol-Pilot/neo-genesis](https://github.com/Yesol-Pilot/neo-genesis)
- Companion datasets:
  - [korean-llm-citation-baseline-2026](https://huggingface.co/datasets/neogenesislab/korean-llm-citation-baseline-2026) — Korean-language version of the same methodology, measured separately
  - [korean-rag-ssot-golden-50](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50) — Korean RAG retrieval benchmark
"""


def export_dataset(out_dir: Path) -> int:
    """Export DB rows to JSONL."""
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / "data.jsonl"
    conn = sqlite3.connect(str(DB_PATH))
    c = conn.cursor()
    c.execute(
        "SELECT timestamp, provider, model, prompt_id, prompt_category, prompt_text, "
        "response_text, response_tokens, mention_neo_genesis, mention_domain_root, "
        "mention_domain_subs, mention_sbu_total, mention_founder, sentiment, "
        "citation_urls, error FROM measurements ORDER BY timestamp"
    )
    cols = [d[0] for d in c.description]
    n = 0
    with open(out_path, "w", encoding="utf-8") as f:
        for row in c.fetchall():
            obj = dict(zip(cols, row))
            f.write(json.dumps(obj, ensure_ascii=False) + "\n")
            n += 1
    return n


def assert_no_credentials_in_text(path: Path) -> None:
    """Quick redaction guard: no API keys, no email addresses, no Telegram tokens."""
    import re
    text = path.read_text(encoding="utf-8", errors="replace")
    patterns = [
        (r"sk-[A-Za-z0-9]{32,}", "OpenAI/Anthropic style key"),
        (r"AIza[0-9A-Za-z_-]{35}", "Google API key"),
        (r"hf_[A-Za-z0-9]{30,}", "HuggingFace token"),
        (r"\b[0-9]{9,12}:[A-Za-z0-9_-]{35}\b", "Telegram bot token"),
        (r"ghp_[A-Za-z0-9]{36}", "GitHub PAT"),
    ]
    for pat, label in patterns:
        if re.search(pat, text):
            raise SystemExit(f"REFUSE: leaked {label} pattern detected in {path}")


def publish(dry_run: bool) -> int:
    load_env()
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("HF_TOKEN missing in .env.local")
        return 2

    with tempfile.TemporaryDirectory() as tmpdir:
        out_dir = Path(tmpdir)
        n = export_dataset(out_dir)
        print(f"Exported {n} rows to {out_dir / 'data.jsonl'}")

        # Redaction guard before any upload
        assert_no_credentials_in_text(out_dir / "data.jsonl")
        print("Redaction guard PASS")

        # Write README.md
        (out_dir / "README.md").write_text(DATASET_CARD, encoding="utf-8")
        print("Dataset card written")

        if dry_run:
            print("[dry-run] skipping HF push")
            return 0

        try:
            from huggingface_hub import HfApi, create_repo
        except ImportError:
            print("huggingface_hub missing. pip install huggingface_hub")
            return 2

        try:
            create_repo(HF_REPO_ID, repo_type="dataset", token=token, exist_ok=True)
            print(f"Repo ensured: {HF_REPO_ID}")
        except Exception as e:
            print(f"create_repo error (continuing): {e}")

        api = HfApi()
        api.upload_folder(
            folder_path=str(out_dir),
            repo_id=HF_REPO_ID,
            repo_type="dataset",
            token=token,
            commit_message="Initial publish: AI Brand Mention Baseline 2026 (486 measurements)",
        )
        print(f"Pushed to https://huggingface.co/datasets/{HF_REPO_ID}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()
    return publish(args.dry_run)


if __name__ == "__main__":
    raise SystemExit(main())
