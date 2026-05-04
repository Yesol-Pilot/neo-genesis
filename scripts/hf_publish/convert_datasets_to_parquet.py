"""
HuggingFace Dataset Viewer Activator — JSONL to Parquet Converter

Iterates over the 8 Neo Genesis datasets and ensures each one has Parquet files
under `data/*.parquet` so the Dataset Viewer widget activates on the HF UI. Only
the JSONL files (the tabular content) are converted; the auxiliary aggregate
JSONs and metadata.json are left in place to preserve documentation and
non-tabular context. The README.md YAML frontmatter is rewritten to point
`configs[*].data_files[*].path` at the new Parquet files.

Idempotent:
- If `data/<base>.parquet` already exists for every JSONL, the dataset is skipped (NOOP).
- Re-running rewrites Parquet from latest JSONL contents and keeps original JSONL.

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/convert_datasets_to_parquet.py
    --dry-run     scan only, no uploads
    --datasets    comma-separated subset of repo IDs

Source of truth:
- HF_TOKEN read from D:/00.test/neo-genesis/.env.local
"""
from __future__ import annotations

import argparse
import io
import json
import os
import re
import shutil
import sys
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Optional

ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = ROOT / ".env.local"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v.strip().strip('"').strip("'"))


# Per-dataset config: which JSONL files to convert and which split they map to.
# `split` is informational only when there is a single config; with multiple JSONL
# we promote each JSONL into its own config_name so the Viewer renders tabs.
DATASETS = [
    {
        "repo_id": "neogenesislab/korean-rag-ssot-golden-50",
        "configs": [
            {"name": "default", "split": "train", "jsonl": "data/tasks.jsonl"},
        ],
    },
    {
        "repo_id": "neogenesislab/ethicaai-mixed-safe-evidence",
        "configs": [
            {"name": "meltingpot_results", "split": "train",
             "jsonl": "data/meltingpot_results.jsonl"},
        ],
    },
    {
        "repo_id": "neogenesislab/whylab-gemini-2-5-docker-validation",
        "configs": [
            {"name": "episodes", "split": "train", "jsonl": "data/episodes.jsonl"},
        ],
    },
    {
        "repo_id": "neogenesislab/sbu-pseo-effects-2026-04",
        "configs": [
            {"name": "default", "split": "train", "jsonl": "data/snapshots.jsonl"},
        ],
    },
    {
        "repo_id": "neogenesislab/cross-agent-review-queue-2026",
        # Multiple table configs -> separate Parquet for each, separate config_name.
        "configs": [
            {"name": "queue_metadata", "split": "train",
             "jsonl": "data/queue_metadata.jsonl"},
            {"name": "checkpoints", "split": "train",
             "jsonl": "data/checkpoints.jsonl"},
        ],
    },
    {
        "repo_id": "neogenesislab/korean-llm-citation-baseline-2026",
        "configs": [
            {"name": "measurements", "split": "train",
             "jsonl": "data/measurements.jsonl"},
        ],
    },
    {
        "repo_id": "neogenesislab/sora-multi-device-orchestration-2026",
        "configs": [
            {"name": "default", "split": "train", "jsonl": "data/sections.jsonl"},
        ],
    },
    {
        "repo_id": "neogenesislab/quant-v11-ensemble-6alpha-specs-2026",
        "configs": [
            {"name": "default", "split": "train", "jsonl": "data/sections.jsonl"},
        ],
    },
]


def parquet_path_for(jsonl: str) -> str:
    """Map data/foo.jsonl -> data/foo.parquet (preserves directory)."""
    p = Path(jsonl)
    return str(p.with_suffix(".parquet")).replace("\\", "/")


def jsonl_to_parquet(jsonl_path: Path, parquet_path: Path) -> int:
    """Convert JSONL file to Parquet, return row count."""
    import pandas as pd
    df = pd.read_json(jsonl_path, lines=True, dtype=False)
    # Convert any complex object columns to JSON strings for Parquet stability.
    # Pandas usually handles nested dicts/lists fine via pyarrow inference, but
    # rows with mixed schemas (e.g. eval_rewards: [...] vs {...}) can fail.
    for col in df.columns:
        if df[col].dtype == object:
            sample = df[col].dropna().head(20).tolist()
            mixed = any(isinstance(x, (dict, list)) for x in sample) and any(
                not isinstance(x, (dict, list)) for x in sample
            )
            if mixed:
                df[col] = df[col].apply(lambda v: json.dumps(v, ensure_ascii=False)
                                         if isinstance(v, (dict, list)) else v)
    df.to_parquet(parquet_path, index=False, engine="pyarrow", compression="snappy")
    return len(df)


def parse_readme(readme_text: str) -> tuple[str, str]:
    """Return (yaml_frontmatter, body) where yaml is between the two `---` lines."""
    if not readme_text.startswith("---"):
        return "", readme_text
    # Locate the closing ---
    parts = readme_text.split("\n---", 1)
    if len(parts) != 2:
        return "", readme_text
    front = parts[0].lstrip("-").lstrip("\n")
    rest = parts[1].lstrip("\n")
    return front, rest


def rebuild_configs_block(configs: list[dict]) -> str:
    """Build new YAML configs block pointing at Parquet files."""
    lines = ["configs:"]
    for cfg in configs:
        parquet = parquet_path_for(cfg["jsonl"])
        lines.append(f"- config_name: {cfg['name']}")
        lines.append("  data_files:")
        lines.append(f"  - split: {cfg['split']}")
        lines.append(f"    path: {parquet}")
    return "\n".join(lines)


def replace_configs_in_yaml(yaml_text: str, new_configs_block: str) -> str:
    """Replace existing `configs:` block in YAML frontmatter with new one.

    Preserves all other keys (license, language, tags, pretty_name, etc.).
    """
    # Match `configs:` to next top-level key or end of YAML.
    pattern = re.compile(
        r"^configs:\s*\n(?:[ \t-].*\n)+",
        re.MULTILINE,
    )
    if pattern.search(yaml_text):
        return pattern.sub(new_configs_block + "\n", yaml_text)
    # No existing block, append before final newline.
    return yaml_text.rstrip() + "\n" + new_configs_block + "\n"


def viewer_url(repo_id: str) -> str:
    return f"https://huggingface.co/datasets/{repo_id}"


def viewer_status(repo_id: str) -> str:
    """HEAD request the dataset page; HF returns 200 once Viewer ready."""
    url = viewer_url(repo_id)
    req = urllib.request.Request(url, method="HEAD")
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            return f"{resp.status}"
    except urllib.error.HTTPError as e:
        return f"HTTP_{e.code}"
    except Exception as e:
        return f"ERR_{type(e).__name__}"


def process_dataset(api, repo_id: str, configs: list[dict], dry_run: bool) -> dict:
    """Convert all JSONL files in a dataset to Parquet and update README."""
    from huggingface_hub import hf_hub_download

    files = api.list_repo_files(repo_id, repo_type="dataset")
    file_set = set(files)

    # Skip if every expected Parquet already exists.
    target_parquets = [parquet_path_for(c["jsonl"]) for c in configs]
    if all(p in file_set for p in target_parquets):
        return {
            "repo_id": repo_id,
            "status": "NOOP",
            "rows": 0,
            "size_bytes": 0,
            "configs": [{"name": c["name"], "rows": "skipped"} for c in configs],
        }

    workdir = Path(tempfile.mkdtemp(prefix="hfparquet_"))
    try:
        results = []
        total_rows = 0
        total_size = 0
        for cfg in configs:
            jsonl_remote = cfg["jsonl"]
            parquet_remote = parquet_path_for(jsonl_remote)
            if parquet_remote in file_set:
                results.append({"name": cfg["name"], "rows": "exists",
                                "parquet_path": parquet_remote})
                continue
            if jsonl_remote not in file_set:
                results.append({"name": cfg["name"], "rows": 0,
                                "error": f"JSONL not found: {jsonl_remote}"})
                continue
            # Download JSONL.
            local_jsonl = Path(hf_hub_download(
                repo_id=repo_id, filename=jsonl_remote, repo_type="dataset",
                token=os.environ["HF_TOKEN"], cache_dir=str(workdir),
            ))
            local_parquet = workdir / Path(parquet_remote).name
            rows = jsonl_to_parquet(local_jsonl, local_parquet)
            size = local_parquet.stat().st_size
            total_rows += rows
            total_size += size
            results.append({
                "name": cfg["name"],
                "rows": rows,
                "size_bytes": size,
                "parquet_local": str(local_parquet),
                "parquet_remote": parquet_remote,
            })

        if dry_run:
            return {
                "repo_id": repo_id,
                "status": "DRY_RUN",
                "rows": total_rows,
                "size_bytes": total_size,
                "configs": results,
            }

        # Upload Parquet files.
        for r in results:
            if "parquet_local" not in r:
                continue
            for attempt in range(3):
                try:
                    api.upload_file(
                        path_or_fileobj=r["parquet_local"],
                        path_in_repo=r["parquet_remote"],
                        repo_id=repo_id,
                        repo_type="dataset",
                        commit_message=(
                            f"Add Parquet for {r['name']} (Dataset Viewer activation)"
                        ),
                    )
                    break
                except Exception as e:
                    if attempt == 2:
                        r["upload_error"] = str(e)
                    else:
                        time.sleep(2 ** attempt)

        # Rewrite README configs block.
        try:
            readme_local = Path(hf_hub_download(
                repo_id=repo_id, filename="README.md", repo_type="dataset",
                token=os.environ["HF_TOKEN"], cache_dir=str(workdir),
            ))
            readme_text = readme_local.read_text(encoding="utf-8")
            yaml_text, body = parse_readme(readme_text)
            if yaml_text:
                new_configs = rebuild_configs_block(configs)
                new_yaml = replace_configs_in_yaml(yaml_text, new_configs)
                new_readme = "---\n" + new_yaml.rstrip() + "\n---\n\n" + body.lstrip()
            else:
                # Build minimal frontmatter with just configs (rare path).
                new_configs = rebuild_configs_block(configs)
                new_readme = "---\n" + new_configs + "\n---\n\n" + readme_text

            readme_out = workdir / "README.md"
            readme_out.write_text(new_readme, encoding="utf-8")
            api.upload_file(
                path_or_fileobj=str(readme_out),
                path_in_repo="README.md",
                repo_id=repo_id,
                repo_type="dataset",
                commit_message="Point YAML configs at Parquet files for Viewer",
            )
        except Exception as e:
            results.append({"name": "_readme_update", "error": str(e)})

        return {
            "repo_id": repo_id,
            "status": "PARQUET_ADDED",
            "rows": total_rows,
            "size_bytes": total_size,
            "configs": results,
        }
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Convert locally only, do not upload.")
    parser.add_argument("--datasets", default="",
                        help="Comma-separated subset of repo IDs")
    parser.add_argument("--skip-viewer-check", action="store_true",
                        help="Skip viewer URL HEAD check at the end.")
    args = parser.parse_args()

    load_env(ENV_LOCAL)
    if not os.environ.get("HF_TOKEN"):
        print("HF_TOKEN missing in .env.local", file=sys.stderr)
        return 2

    from huggingface_hub import HfApi
    api = HfApi(token=os.environ["HF_TOKEN"])

    targets = [d for d in DATASETS
               if not args.datasets or d["repo_id"] in args.datasets.split(",")]

    print(f"Targets: {len(targets)} dataset(s)")
    print(f"Dry-run: {args.dry_run}")
    print("-" * 70)

    summary = []
    for d in targets:
        repo_id = d["repo_id"]
        print(f"-> {repo_id}")
        try:
            result = process_dataset(api, repo_id, d["configs"], args.dry_run)
        except Exception as e:
            result = {"repo_id": repo_id, "status": "FAILED", "error": str(e),
                      "rows": 0, "size_bytes": 0, "configs": []}
        summary.append(result)
        cfg_brief = ", ".join(f"{c.get('name','?')}={c.get('rows','?')}rows"
                              for c in result.get("configs", []))
        print(f"   {result['status']} | total_rows={result.get('rows',0)}"
              f" | size={result.get('size_bytes',0)} | {cfg_brief}")

    if not args.dry_run and not args.skip_viewer_check:
        print("-" * 70)
        print("Waiting 60s for HF to detect Parquet then probing Viewer URLs...")
        time.sleep(60)
        for s in summary:
            s["viewer_status"] = viewer_status(s["repo_id"])
            print(f"   viewer {s['repo_id']}: {s['viewer_status']}")

    print("-" * 70)
    print(json.dumps(summary, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
