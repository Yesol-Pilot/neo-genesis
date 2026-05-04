"""
Append a Citation File Format (CFF) block to each HuggingFace dataset README
under neogenesislab/, using the live Zenodo DOI ledger.

Idempotent: if a `## Citation File Format` section already exists in the
README, the script SKIPs the dataset.

CFF v1.2.0 schema reference: https://citation-file-format.github.io/

The CFF block is appended at the END of the README so it does not disturb the
existing YAML front-matter, title, abstract, or DOI/BibTeX citation sections
already in place.
"""
from __future__ import annotations

import json
import os
import re
import sys
from datetime import date as _date
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / ".agent" / "knowledge" / "wikidata-entities" / "zenodo_dois.json"
ENV = ROOT / ".env.local"

# Map slug -> ISO release date. Falls back to ledger `minted_at_utc` date if
# the slug isn't here.
RELEASE_DATES = {
    "korean-rag-ssot-golden-50": "2026-04-28",
    "ethicaai-mixed-safe-evidence": "2026-04-28",
    "whylab-gemini-2-5-docker-validation": "2026-04-28",
    "sbu-pseo-effects-2026-04": "2026-04-29",
    "cross-agent-review-queue-2026": "2026-04-30",
    "korean-llm-citation-baseline-2026": "2026-05-01",
    "sora-multi-device-orchestration-2026": "2026-05-02",
    "quant-v11-ensemble-6alpha-specs-2026": "2026-05-03",
}

# Per-dataset keywords for the CFF block. Generic + dataset-specific.
KEYWORDS = {
    "korean-rag-ssot-golden-50": [
        "korean", "retrieval-augmented-generation", "rag",
        "evaluation", "ssot", "golden-set", "neo-genesis",
    ],
    "ethicaai-mixed-safe-evidence": [
        "multi-agent", "alignment", "constitutional-ai",
        "melting-pot", "coin-game", "fishery",
        "ethicaai", "neo-genesis", "neurips-2026",
    ],
    "whylab-gemini-2-5-docker-validation": [
        "llm-evaluation", "docker", "gemini", "swe-bench",
        "self-criticism", "audit", "whylab", "neo-genesis",
    ],
    "sbu-pseo-effects-2026-04": [
        "programmatic-seo", "search-engine-optimization",
        "saas", "neo-genesis", "ga4", "posthog",
        "ai-traffic", "case-study",
    ],
    "cross-agent-review-queue-2026": [
        "multi-agent", "code-review", "claude", "codex",
        "ai-collaboration", "checkpoints", "neo-genesis",
    ],
    "korean-llm-citation-baseline-2026": [
        "korean", "llm", "citation", "generative-engine-optimization",
        "geo", "openai", "anthropic", "perplexity", "gemini",
        "neo-genesis", "measurement",
    ],
    "sora-multi-device-orchestration-2026": [
        "multi-agent", "orchestration", "fleet", "edge-computing",
        "sora", "neo-genesis", "claude", "codex",
        "tailscale", "ssh",
    ],
    "quant-v11-ensemble-6alpha-specs-2026": [
        "quantitative-trading", "kill-switch", "ensemble",
        "liquidation-cascade", "funding-rate", "mean-reversion",
        "binance", "neo-genesis", "risk-engineering",
    ],
}


def load_env(p: Path) -> None:
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v.strip())


def build_cff_block(
    slug: str,
    title: str,
    doi: str,
    release_date: str,
    keywords: list[str],
) -> str:
    keyword_yaml = "\n".join(f"  - {k}" for k in keywords)
    cff_yaml = (
        "cff-version: 1.2.0\n"
        "message: \"If you use this dataset, please cite it as below.\"\n"
        f"title: \"{title}\"\n"
        "type: dataset\n"
        "authors:\n"
        "  - family-names: \"Heo\"\n"
        "    given-names: \"Yesol\"\n"
        "    affiliation: \"Neo Genesis Lab\"\n"
        f"date-released: \"{release_date}\"\n"
        "license: CC-BY-4.0\n"
        f"url: \"https://huggingface.co/datasets/neogenesislab/{slug}\"\n"
        f"repository: \"https://huggingface.co/datasets/neogenesislab/{slug}\"\n"
        "identifiers:\n"
        "  - type: doi\n"
        f"    value: \"{doi}\"\n"
        "    description: \"Zenodo DataCite DOI for this dataset\"\n"
        "  - type: other\n"
        "    value: \"Q139569680\"\n"
        "    description: \"Wikidata Q-ID of the publishing organization (Neo Genesis)\"\n"
        "keywords:\n"
        f"{keyword_yaml}\n"
        "preferred-citation:\n"
        "  type: dataset\n"
        f"  title: \"{title}\"\n"
        "  authors:\n"
        "    - family-names: \"Heo\"\n"
        "      given-names: \"Yesol\"\n"
        "      affiliation: \"Neo Genesis Lab\"\n"
        f"  doi: \"{doi}\"\n"
        f"  year: {release_date.split('-')[0]}\n"
        "  publisher:\n"
        "    name: \"Zenodo\"\n"
        f"  url: \"https://doi.org/{doi}\"\n"
    )
    return (
        "## Citation File Format\n\n"
        "GitHub, Zenodo, and other tooling can read the following CFF block "
        "to provide one-click citation export (BibTeX, APA, RIS, etc.). The "
        "[CFF specification](https://citation-file-format.github.io/) is "
        "v1.2.0.\n\n"
        "```yaml\n"
        f"{cff_yaml}"
        "```\n"
    )


def has_cff(text: str) -> bool:
    return "## Citation File Format" in text or "cff-version: 1.2.0" in text


def main() -> int:
    load_env(ENV)
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError:
        print("huggingface_hub not installed", file=sys.stderr)
        return 1

    if "HF_TOKEN" not in os.environ:
        print("HF_TOKEN not in env", file=sys.stderr)
        return 1

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    api = HfApi(token=os.environ["HF_TOKEN"])

    updated, skipped, errors = 0, 0, 0
    for entry in ledger["dois"]:
        if entry["upload_type"] != "dataset":
            continue
        slug = entry["slug"]
        repo_id = f"neogenesislab/{slug}"
        doi = entry["doi"]
        title = entry["title"]
        release_date = RELEASE_DATES.get(slug, entry["minted_at_utc"][:10])
        keywords = KEYWORDS.get(
            slug,
            ["dataset", "neo-genesis"],
        )

        print(f"\n[{slug}] doi={doi}")
        try:
            local = hf_hub_download(
                repo_id=repo_id,
                filename="README.md",
                repo_type="dataset",
                token=os.environ["HF_TOKEN"],
            )
            text = Path(local).read_text(encoding="utf-8")
        except Exception as e:
            print(f"  [ERROR] download README: {e}")
            errors += 1
            continue

        if has_cff(text):
            print("  SKIP — CFF block already in README")
            skipped += 1
            continue

        section = build_cff_block(slug, title, doi, release_date, keywords)

        # Append at END to avoid disturbing existing structure.
        if not text.endswith("\n"):
            text += "\n"
        if not text.endswith("\n\n"):
            text += "\n"
        new_text = text + section

        try:
            api.upload_file(
                path_or_fileobj=new_text.encode("utf-8"),
                path_in_repo="README.md",
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=(
                    "docs(cff): add Citation File Format v1.2.0 block "
                    f"for DOI {doi}"
                ),
                token=os.environ["HF_TOKEN"],
            )
            print("  UPDATED README.md (CFF appended)")
            updated += 1
        except Exception as e:
            print(f"  [ERROR] upload README: {e}")
            errors += 1

    print(
        f"\nResult: updated={updated} skipped={skipped} errors={errors}"
    )
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
