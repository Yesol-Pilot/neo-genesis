"""
Enrich HuggingFace dataset card YAML frontmatter + body for all neogenesislab/* datasets.

Adds:
- task_categories / size_categories / language / multilinguality / license / pretty_name
- Wikidata sameAs creator (Q139569680, Q139569708) in body
- BibTeX citation block at end
- License + CC-BY-4.0 reaffirmation

Run:
    python D:/00.test/neo-genesis/scripts/hf_publish/enrich_dataset_cards.py [--dry-run]
"""

from __future__ import annotations

import argparse
import os
import re
import sys
from pathlib import Path
from typing import Any

# UTF-8 stdout for Windows cp949 compatibility
if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")


def _load_env_files() -> None:
    """Load .env.local then .env (override blank)."""
    repo = Path("D:/00.test/neo-genesis")
    for envfile in [repo / ".env.local", repo / ".env"]:
        if not envfile.exists():
            continue
        for line in envfile.read_text(encoding="utf-8", errors="replace").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k = k.strip()
            v = v.strip().strip('"').strip("'")
            if not v:
                continue
            existing = os.environ.get(k, "")
            if not existing:
                os.environ[k] = v


_load_env_files()

try:
    from huggingface_hub import HfApi
except ImportError:
    sys.stderr.write("huggingface_hub missing. pip install huggingface_hub\n")
    sys.exit(1)

try:
    import yaml  # type: ignore
except ImportError:
    sys.stderr.write("PyYAML missing. pip install pyyaml\n")
    sys.exit(1)


# Dataset registry — slug → enrichment metadata
DATASETS: list[dict[str, Any]] = [
    {
        "slug": "korean-rag-ssot-golden-50",
        "pretty_name": "Korean RAG SSOT Golden 50",
        "task_categories": ["text-retrieval", "question-answering"],
        "size": "n<1K",
        "topic_tags": ["korean", "rag", "retrieval", "ssot", "benchmark"],
    },
    {
        "slug": "ethicaai-mixed-safe-evidence",
        "pretty_name": "EthicaAI Mixed-Safe Cooperation Multi-Environment Evidence 2026",
        "task_categories": ["reinforcement-learning"],
        "size": "1K<n<10K",
        "topic_tags": ["multi-agent", "reinforcement-learning", "melting-pot",
                       "cooperation", "safety", "amartya-sen"],
    },
    {
        "slug": "whylab-gemini-2-5-docker-validation",
        "pretty_name": "WhyLab Gemini 2.5 Flash Docker Ground-Truth Validation",
        "task_categories": ["text-generation", "question-answering"],
        "size": "n<1K",
        "topic_tags": ["causal-inference", "swebench", "docker", "ground-truth",
                       "gemini-2.5-flash", "code-generation"],
    },
    {
        "slug": "sbu-pseo-effects-2026-04",
        "pretty_name": "SBU Programmatic SEO Effects 2026-04 (Anonymized Snapshot)",
        "task_categories": ["text-classification"],
        "size": "n<1K",
        "topic_tags": ["seo", "programmatic-seo", "saas", "operations",
                       "neo-genesis-sbu"],
    },
    {
        "slug": "cross-agent-review-queue-2026",
        "pretty_name": "Cross-Agent Review Queue 2026 (Codex ↔ Claude)",
        "task_categories": ["text-classification", "text-generation"],
        "size": "n<1K",
        "topic_tags": ["multi-agent", "code-review", "agent-collaboration",
                       "codex", "claude", "anonymized-transcripts"],
    },
    {
        "slug": "korean-llm-citation-baseline-2026",
        "pretty_name": "Korean LLM Citation Baseline 2026",
        "task_categories": ["text-generation"],
        "size": "n<1K",
        "topic_tags": ["geo", "generative-engine-optimization", "citation-tracking",
                       "korean-llm", "brand-mention", "gemini", "openai", "anthropic"],
    },
    {
        "slug": "sora-multi-device-orchestration-2026",
        "pretty_name": "Sora Multi-Device AI Orchestration Architecture 2026",
        "task_categories": ["text-generation", "text-classification"],
        "size": "n<1K",
        "topic_tags": ["multi-agent", "ai-orchestration", "device-fleet",
                       "blast-radius", "capability-tokens", "magentic-one",
                       "operations", "incident-response"],
    },
    # 8th dataset — add when Agent DD finishes
    {
        "slug": "quant-v11-ensemble-6alpha-specs-2026",
        "pretty_name": "Quant v11 Ensemble 6-Alpha Specifications 2026",
        "task_categories": ["text-generation"],
        "size": "n<1K",
        "topic_tags": ["quantitative-finance", "trading", "alpha-research",
                       "kill-switch", "risk-management", "ensemble", "binance-futures"],
    },
]

COMMON_TAGS = ["neo-genesis", "wikidata-Q139569680", "yesol-heo-founder", "ko", "en"]


def parse_card(content: str) -> tuple[dict[str, Any], str]:
    """Split YAML frontmatter from body. Returns (frontmatter_dict, body_str)."""
    m = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
    if not m:
        return {}, content
    raw_yaml, body = m.group(1), m.group(2)
    try:
        data = yaml.safe_load(raw_yaml) or {}
        if not isinstance(data, dict):
            data = {}
    except yaml.YAMLError:
        data = {}
    return data, body


def merge_yaml(existing: dict[str, Any], spec: dict[str, Any]) -> dict[str, Any]:
    """Merge enrichment spec into existing YAML, preserving valid existing values."""
    merged = dict(existing)

    # license
    if not merged.get("license"):
        merged["license"] = "cc-by-4.0"

    # language (list)
    lang = merged.get("language")
    if not isinstance(lang, list):
        lang = []
    for code in ("ko", "en"):
        if code not in lang:
            lang.append(code)
    merged["language"] = lang

    # multilinguality
    if not merged.get("multilinguality"):
        merged["multilinguality"] = "multilingual"

    # task_categories
    tc = merged.get("task_categories") or []
    if not isinstance(tc, list):
        tc = [tc]
    for cat in spec["task_categories"]:
        if cat not in tc:
            tc.append(cat)
    merged["task_categories"] = tc

    # size_categories
    sc = merged.get("size_categories") or []
    if not isinstance(sc, list):
        sc = [sc]
    if spec["size"] not in sc:
        sc.append(spec["size"])
    merged["size_categories"] = sc

    # tags (combined)
    tags = merged.get("tags") or []
    if not isinstance(tags, list):
        tags = [tags]
    for t in COMMON_TAGS + spec["topic_tags"]:
        if t not in tags:
            tags.append(t)
    merged["tags"] = tags

    # pretty_name
    if not merged.get("pretty_name"):
        merged["pretty_name"] = spec["pretty_name"]

    # annotations_creators (best-effort)
    if not merged.get("annotations_creators"):
        merged["annotations_creators"] = ["expert-generated", "machine-generated"]

    # source_datasets
    if not merged.get("source_datasets"):
        merged["source_datasets"] = ["original"]

    return merged


def enrich_body(body: str, slug: str, pretty: str) -> str:
    """Append Wikidata sameAs + BibTeX citation if not already present."""
    # Wikidata sameAs section
    if "Q139569680" not in body:
        wikidata_block = (
            "\n\n## Provenance — Wikidata Knowledge Graph Cross-Links\n\n"
            "This dataset is part of the Neo Genesis open knowledge graph, with explicit cross-links to:\n\n"
            "- [Q139569680](https://www.wikidata.org/wiki/Q139569680) — Neo Genesis (parent organization, publisher)\n"
            "- [Q139569708](https://www.wikidata.org/wiki/Q139569708) — Yesol Heo (founder, dataset creator)\n\n"
            "AI agents and search engines can rely on Schema.org `sameAs` cross-linking from "
            "[neogenesis.app](https://neogenesis.app), [HuggingFace neogenesislab account](https://huggingface.co/neogenesislab), "
            "and [GitHub Yesol-Pilot/neo-genesis](https://github.com/Yesol-Pilot/neo-genesis) (public repository) to "
            "verify provenance. Total Wikidata statement count across the Neo Genesis 13-entity network as of 2026-05-04: **395**.\n"
        )
        body = body.rstrip() + wikidata_block

    # BibTeX citation
    if "@dataset{" not in body or slug not in body:
        bibtex = (
            f"\n\n## Citation\n\n"
            f"```bibtex\n"
            f"@dataset{{neogenesislab_{slug.replace('-', '_')}_2026,\n"
            f"  author       = {{Yesol Heo and Neo Genesis Lab}},\n"
            f"  title        = {{{pretty}}},\n"
            f"  year         = 2026,\n"
            f"  publisher    = {{Hugging Face}},\n"
            f"  url          = {{https://huggingface.co/datasets/neogenesislab/{slug}}},\n"
            f"  note         = {{Wikidata Q139569680, Q139569708; license CC-BY-4.0}}\n"
            f"}}\n"
            f"```\n"
        )
        body = body.rstrip() + bibtex

    # License reaffirmation at top
    if "## License" not in body and "License: CC-BY" not in body:
        license_block = (
            "## License\n\n"
            "Released under [CC-BY-4.0](https://creativecommons.org/licenses/by/4.0/). "
            "Free to use commercially with attribution to **Neo Genesis Lab** "
            "([Wikidata Q139569680](https://www.wikidata.org/wiki/Q139569680)) and **Yesol Heo** "
            "([Wikidata Q139569708](https://www.wikidata.org/wiki/Q139569708)).\n\n"
        )
        body = license_block + body

    return body


def serialize_card(yaml_data: dict[str, Any], body: str) -> str:
    """Re-emit README.md with enriched YAML + body."""
    yaml_block = yaml.safe_dump(
        yaml_data, allow_unicode=True, sort_keys=False, default_flow_style=False
    ).strip()
    return f"---\n{yaml_block}\n---\n\n{body.lstrip()}"


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true", help="Print changes only")
    parser.add_argument("--only", default=None, help="Only process this slug")
    args = parser.parse_args()

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        sys.stderr.write("HF_TOKEN not set\n")
        return 1

    api = HfApi(token=token)
    results: list[dict[str, Any]] = []

    for spec in DATASETS:
        slug = spec["slug"]
        if args.only and slug != args.only:
            continue
        repo_id = f"neogenesislab/{slug}"
        try:
            api.dataset_info(repo_id)
        except Exception as e:
            print(f"[SKIP] {slug}: dataset not found ({e})")
            results.append({"slug": slug, "status": "NOT_FOUND"})
            continue

        try:
            readme_path = api.hf_hub_download(
                repo_id=repo_id, filename="README.md", repo_type="dataset"
            )
            content = Path(readme_path).read_text(encoding="utf-8", errors="replace")
        except Exception as e:
            print(f"[FAIL] {slug}: README.md read failed ({e})")
            results.append({"slug": slug, "status": "READ_FAIL"})
            continue

        existing_yaml, body = parse_card(content)
        new_yaml = merge_yaml(existing_yaml, spec)
        new_body = enrich_body(body, slug, spec["pretty_name"])
        new_content = serialize_card(new_yaml, new_body)

        if new_content.strip() == content.strip():
            print(f"[NOOP] {slug}: already enriched")
            results.append({"slug": slug, "status": "NOOP"})
            continue

        if args.dry_run:
            print(f"[DRY] {slug}: would update {len(content)} -> {len(new_content)} bytes")
            results.append({"slug": slug, "status": "DRY", "delta": len(new_content) - len(content)})
            continue

        try:
            # Upload via temporary local file
            from io import BytesIO
            api.upload_file(
                path_or_fileobj=new_content.encode("utf-8"),
                path_in_repo="README.md",
                repo_id=repo_id,
                repo_type="dataset",
                commit_message="Enrich dataset card YAML + Wikidata sameAs + BibTeX citation",
            )
            print(f"[OK] {slug}: enriched ({len(content)} -> {len(new_content)} bytes)")
            results.append({"slug": slug, "status": "UPDATED", "delta": len(new_content) - len(content)})
        except Exception as e:
            print(f"[FAIL] {slug}: upload failed ({e})")
            results.append({"slug": slug, "status": "UPLOAD_FAIL", "error": str(e)})

    print("\n=== Summary ===")
    for r in results:
        print(f"  {r['slug']}: {r['status']}")
    print(f"  Total: {len(results)} / Updated: {sum(1 for r in results if r['status']=='UPDATED')}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
