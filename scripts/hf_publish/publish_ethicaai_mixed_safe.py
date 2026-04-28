"""
HuggingFace Datasets publish — EthicaAI Mixed-Safe Multi-Environment Evidence

3 environments × statistical validation evidence (NeurIPS 2026 underlying data):
  1. Melting Pot mixed-safe (50 seed × floor_prob, t-test + p-value)
  2. Coin Game deep (160-seed selfish vs MACCL comparison)
  3. Fishery 300-seed Nash trap (300 seeds, ecological model)

Source paper : Heo, Yesol. "EthicaAI: Mixed-Safe Boundary-Consistent Evidence
                for Multi-Agent Cooperative Constraint Learning" (NeurIPS 2026 submission)
Target       : huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/publish_ethicaai_mixed_safe.py
"""
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = ROOT / ".env.local"
PAPER_DIR = ROOT.parent / "PAPER" / "EthicaAI" / "NeurIPS2026_final_submission" / "code" / "outputs"

SOURCES = {
    "meltingpot_merged": PAPER_DIR / "meltingpot" / "meltingpot_final_results_merged.json",
    "coin_game_deep": PAPER_DIR / "coin_game_deep" / "coin_game_deep_results.json",
    "fishery_default": PAPER_DIR / "fishery" / "fishery_results.json",
    "fishery_300seed": PAPER_DIR / "review85" / "fishery_300seed_300ep.json",
}

REPO_ID = "neogenesislab/ethicaai-mixed-safe-evidence"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_all_sources() -> dict:
    out = {}
    for name, path in SOURCES.items():
        if not path.exists():
            print(f"  WARN: source missing: {path}")
            continue
        with path.open(encoding="utf-8") as f:
            out[name] = json.load(f)
        print(f"  loaded {name}: {path.stat().st_size:,} bytes")
    return out


def build_artifacts(data: dict) -> list[tuple[str, str]]:
    """Return list of (path_in_repo, content_string)."""
    artifacts = []

    # 1) Melting Pot results JSONL (50 lines per result)
    mp = data.get("meltingpot_merged", {})
    if "results" in mp:
        jsonl = "\n".join(
            json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in mp["results"]
        ) + "\n"
        artifacts.append(("data/meltingpot_results.jsonl", jsonl))

    # 2) Melting Pot stats + config (paper-level evidence)
    mp_meta = {
        "experiment": mp.get("experiment"),
        "config": mp.get("config"),
        "statistics": mp.get("statistics"),
        "source_summary": mp.get("source_summary"),
    }
    artifacts.append(("data/meltingpot_statistics.json", json.dumps(mp_meta, ensure_ascii=False, indent=2)))

    # 3) Coin Game deep
    cg = data.get("coin_game_deep", {})
    cg_clean = {k: v for k, v in cg.items() if k != "results" or v}  # keep selfish + maccl
    artifacts.append(("data/coin_game_deep.json", json.dumps(cg_clean, ensure_ascii=False, indent=2)))

    # 4) Fishery default
    fd = data.get("fishery_default", {})
    artifacts.append(("data/fishery_default.json", json.dumps(fd, ensure_ascii=False, indent=2)))

    # 5) Fishery 300-seed
    f300 = data.get("fishery_300seed", {})
    artifacts.append(("data/fishery_300seed.json", json.dumps(f300, ensure_ascii=False, indent=2)))

    return artifacts


def build_readme(data: dict) -> str:
    mp = data.get("meltingpot_merged", {})
    n_mp = len(mp.get("results", []))
    mp_stats_eval = mp.get("statistics", {}).get("eval", {})
    mp_floor_mean = mp_stats_eval.get("floor_mean", "?")
    mp_baseline_mean = mp_stats_eval.get("baseline_mean", "?")
    mp_p = mp_stats_eval.get("p_value", "?")

    cg = data.get("coin_game_deep", {})
    cg_selfish = cg.get("selfish", {})
    cg_maccl = cg.get("maccl", {})
    cg_n = cg.get("config", {}).get("n_seeds", 160)

    f300 = data.get("fishery_300seed", {})
    f300_n = f300.get("config", {}).get("n_seeds", 300)

    yaml_front = """---
language:
- en
license: cc-by-4.0
task_categories:
- reinforcement-learning
- other
tags:
- multi-agent
- cooperation
- safety
- agent-evaluation
- mixed-safe
- ai-ethics
- melting-pot
- coin-game
- fishery
- nash-equilibrium
- ecological-model
- maccl
size_categories:
- n<1K
pretty_name: "EthicaAI Mixed-Safe Multi-Environment Evidence (NeurIPS 2026)"
---
"""
    body = f"""
# EthicaAI Mixed-Safe Multi-Environment Evidence (NeurIPS 2026)

> Underlying experimental evidence from **[Neo Genesis](https://neogenesis.app)**'s NeurIPS 2026 paper *"EthicaAI: Mixed-Safe Boundary-Consistent Evidence for Multi-Agent Cooperative Constraint Learning"* — released as an open dataset for community replication and AI safety research.

## What this dataset is

A **3-environment evidence bundle** showing how multi-agent reinforcement-learning agents behave under different cooperative-constraint regimes. Each environment was deliberately chosen to stress-test different aspects of the **mixed-safe** boundary thesis:

| Environment | What it tests | Sample size | Key statistic |
|---|---|---:|---|
| **Melting Pot (`clean_up`)** | Boundary-consistent cooperative learning under floor-probability sweep vs. baseline | **{n_mp} seed × floor_prob runs** | t-test eval: floor_mean = {mp_floor_mean}, baseline_mean = {mp_baseline_mean}, **p = {mp_p}** |
| **Coin Game Deep (adapted)** | Selfish equilibrium vs. MACCL (Multi-Agent Cooperative Constraint Learning) on 160 seeds | **{cg_n} seeds × 200 episodes** | MACCL survival ≫ selfish survival (paper-level finding) |
| **Fishery Nash Trap** | Ecological tragedy-of-commons with 300 seeds and tipping-point dynamics | **{f300_n} seeds × 300 episodes** | survival vs. harvest welfare frontier |

The three environments together form the **mixed-safe corpus** — the paper's central claim is that no single environment proves the thesis, but the **boundary consistency across three independently-designed substrates** does.

## Why publish the data

Most AI-safety papers expose plots and aggregate statistics but withhold seed-level results. This dataset releases:

- All **{n_mp} seed-level Melting Pot runs** with full `train_rewards` trajectories per seed
- The exact `late_train` and `eval` statistics used in the paper's t-tests, p-values, bootstrap CIs
- Coin Game `selfish` vs `maccl` aggregated per-seed metrics
- Fishery 300-seed survival/welfare results across `phi1` calibration values
- Source-file provenance (which results came from which compute node — Mac Studio head shard vs. Linux server tail shard)

This lets independent researchers:
1. Replicate the paper's claims by re-running the same seeds
2. Extend the analysis with their own cooperative-constraint variants
3. Use the seed-level data as a benchmark for new MARL methods

## Files

```
data/
├── meltingpot_results.jsonl       {n_mp} lines, one per (seed, floor_prob) combination
├── meltingpot_statistics.json     paper-grade t-test + bootstrap CI per condition
├── coin_game_deep.json            selfish vs maccl, 160 seeds × 200 episodes
├── fishery_default.json           default ecological config
└── fishery_300seed.json           300-seed phi1 sweep, 300 episodes per seed
```

## Schema (`meltingpot_results.jsonl`)

Each line is one (seed, floor_prob) run:

```json
{{
  "seed": 88409749,
  "floor_prob": 0.0,
  "train_rewards": [0.0, 0.0, 0.14, 2.71, ...],
  "eval_rewards": [...]
}}
```

`train_rewards` is the per-episode reward time series during training; `eval_rewards` is the held-out evaluation reward. `floor_prob = 0.0` corresponds to baseline (no cooperative floor); `floor_prob > 0` corresponds to mixed-safe condition.

## Quick start

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", split="train", data_files="data/meltingpot_results.jsonl")
print(len(ds), "Melting Pot runs")

# Per-condition statistics (already computed):
import json, urllib.request
url = "https://huggingface.co/datasets/{REPO_ID}/resolve/main/data/meltingpot_statistics.json"
stats = json.loads(urllib.request.urlopen(url).read())
print("eval floor_mean:", stats["statistics"]["eval"]["floor_mean"])
print("eval baseline_mean:", stats["statistics"]["eval"]["baseline_mean"])
print("p-value:", stats["statistics"]["eval"]["p_value"])
```

## Reproducing the paper's findings

The full reproduction code (RLlib + Melting Pot harness + Coin Game adapter + Fishery simulator) is referenced in the paper's appendix. The dataset above is the **frozen evidence snapshot** used in the camera-ready manuscript.

Statistical machinery (provided in `meltingpot_statistics.json`):
- Welch's t-test (unequal variance) for floor vs baseline mean reward
- Bootstrap 95% CI on the difference (resamples documented in `config`)
- Cohen's d effect size
- Per-shard provenance for distributed compute audit

## Related Neo Genesis assets

- 📄 **Paper (NeurIPS 2026 submission)** — see `https://neogenesis.app/data/research/ethicaai-melting-pot-mixed-safe`
- 🤗 **Companion dataset** — [`neogenesislab/korean-rag-ssot-golden-50`](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50)
- 🆔 **Wikidata** — [Q139569718 (EthicaAI)](https://www.wikidata.org/wiki/Q139569718) · [Q139569680 (Neo Genesis parent org)](https://www.wikidata.org/wiki/Q139569680)
- 🌐 **Org site** — https://neogenesis.app

## Citation

```bibtex
@inproceedings{{ethicaai_neurips2026_mixed_safe,
  title     = {{EthicaAI: Mixed-Safe Boundary-Consistent Evidence for Multi-Agent Cooperative Constraint Learning}},
  author    = {{Heo, Yesol}},
  booktitle = {{Submitted to NeurIPS 2026}},
  year      = {{2026}},
  url       = {{https://huggingface.co/datasets/{REPO_ID}}},
  note      = {{Underlying evidence dataset, CC-BY-4.0}}
}}
```

## License

CC-BY-4.0. Free for research and commercial use with attribution to **Neo Genesis** and the underlying paper.

## Provenance

- Compute nodes: Mac Studio (head shard `seed_indices 0-23`) + Linux server (tail shard `seed_indices 24-49`) — see `meltingpot_statistics.json` `source_summary`
- Curation: Yesol Heo (sole founder/operator, [neogenesis.app](https://neogenesis.app))
- Frozen 2026-04-15 (`meltingpot_n80_stats.json` paper-anchor revision)
- Released 2026-04-28
"""
    return yaml_front + body


def main() -> int:
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN missing", file=sys.stderr)
        return 1

    print("Loading sources...")
    data = load_all_sources()
    if "meltingpot_merged" not in data:
        print("ERROR: meltingpot_merged missing", file=sys.stderr)
        return 1

    print("\nBuilding artifacts...")
    artifacts = build_artifacts(data)
    readme = build_readme(data)
    artifacts.append(("README.md", readme))
    metadata = {
        "name": "EthicaAI Mixed-Safe Multi-Environment Evidence",
        "version": "1.0",
        "released": "2026-04-28",
        "license": "CC-BY-4.0",
        "environments": ["melting_pot_clean_up", "coin_game_deep", "fishery_nash_trap"],
    }
    artifacts.append(("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2)))

    from huggingface_hub import HfApi
    api = HfApi(token=token)
    print(f"\ncreate_repo {REPO_ID}")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True, private=False)

    for path_in_repo, content in artifacts:
        size = len(content.encode("utf-8")) if isinstance(content, str) else len(content)
        print(f"upload {path_in_repo} ({size:,} bytes)")
        api.upload_file(
            path_or_fileobj=io.BytesIO(content.encode("utf-8")),
            path_in_repo=path_in_repo,
            repo_id=REPO_ID,
            repo_type="dataset",
            commit_message=f"add {path_in_repo}",
        )

    url = f"https://huggingface.co/datasets/{REPO_ID}"
    print(f"\nPUBLISHED: {url}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
