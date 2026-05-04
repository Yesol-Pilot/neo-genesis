"""
Append DOI section to each HuggingFace dataset README using the live ledger.

Idempotent: if the DOI is already in the README it skips. Inserts a `## DOI`
section directly after the YAML frontmatter (before the first `# Title` H1).
"""
from __future__ import annotations

import json
import os
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
LEDGER = ROOT / ".agent" / "knowledge" / "wikidata-entities" / "zenodo_dois.json"
ENV = ROOT / ".env.local"


def load_env(p: Path) -> None:
    if not p.exists():
        return
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v.strip())


def build_doi_section(doi: str, url: str) -> str:
    badge = f"https://zenodo.org/badge/doi/{doi.replace('/', '%2F')}.svg"
    return (
        "## DOI\n\n"
        f"[![DOI]({badge})](https://doi.org/{doi})\n\n"
        f"This dataset is citable via DataCite DOI **`{doi}`** "
        f"([Zenodo record]({url})).\n\n"
        "**Cite as:**\n\n"
        "```bibtex\n"
        f"@dataset{{neogenesis_{doi.split('.')[-1]},\n"
        f"  author       = {{Heo, Yesol and Neo Genesis Lab}},\n"
        f"  title        = {{{{TITLE}}}},\n"
        f"  year         = 2026,\n"
        f"  publisher    = {{Zenodo}},\n"
        f"  doi          = {{{doi}}},\n"
        f"  url          = {{https://doi.org/{doi}}}\n"
        "}\n"
        "```\n\n"
    )


def main() -> int:
    load_env(ENV)
    try:
        from huggingface_hub import HfApi, hf_hub_download
    except ImportError:
        print("huggingface_hub not installed", file=sys.stderr)
        return 1

    ledger = json.loads(LEDGER.read_text(encoding="utf-8"))
    api = HfApi()

    updated, skipped, errors = 0, 0, 0
    for entry in ledger["dois"]:
        if entry["upload_type"] != "dataset":
            continue
        slug = entry["slug"]
        repo_id = f"neogenesislab/{slug}"
        doi = entry["doi"]
        url = entry["url"]
        title = entry["title"]
        print(f"\n[{slug}] doi={doi}")
        try:
            local = hf_hub_download(
                repo_id=repo_id,
                filename="README.md",
                repo_type="dataset",
            )
            text = Path(local).read_text(encoding="utf-8")
        except Exception as e:
            print(f"  [ERROR] download README: {e}")
            errors += 1
            continue

        if doi in text:
            print(f"  SKIP — DOI already in README")
            skipped += 1
            continue

        section = build_doi_section(doi, url).replace("{TITLE}", title)

        # Insert after YAML front-matter (closing `---`) and before first H1.
        m = re.match(r"(?s)^---\n.*?\n---\n", text)
        if m:
            head = text[:m.end()]
            rest = text[m.end():]
            new_text = head + "\n" + section + rest.lstrip("\n")
        else:
            new_text = section + "\n" + text

        try:
            api.upload_file(
                path_or_fileobj=new_text.encode("utf-8"),
                path_in_repo="README.md",
                repo_id=repo_id,
                repo_type="dataset",
                commit_message=f"docs: add Zenodo DOI {doi} citation block",
            )
            print(f"  UPDATED README.md")
            updated += 1
        except Exception as e:
            print(f"  [ERROR] upload README: {e}")
            errors += 1

    print(f"\nResult: updated={updated} skipped={skipped} errors={errors}")
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    sys.exit(main())
