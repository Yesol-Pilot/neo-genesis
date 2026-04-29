"""
HuggingFace Datasets publish — WhyLab Gemini 2.5 Flash Docker Validation (Honest Null Result)

Source paper : Heo, Yesol. "WhyLab: Causal Decision Intelligence Engine — Selective C2
                Real-Task Validation on SWE-bench" (NeurIPS 2026 submission, frozen anchor 88fa509)
Headline data: g25_flash_docker checkpoints (67 problems × 3 seeds × 2 conditions = 402 episodes)
Frame        : honest null result — selective adaptive C2 did NOT beat fixed C2 on
                SWE-bench selective slice. Published to support reproducibility and the
                paper's "phase-aware deployment" recalibration.
Target       : huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/publish_whylab_docker.py
"""
import io
import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = ROOT / ".env.local"
PAPER_RESULTS = ROOT.parent / "PAPER" / "WhyLab" / "experiments" / "results"

SOURCES = {
    "checkpoints_jsonl": PAPER_RESULTS / "g25_flash_docker" / "checkpoints.jsonl",
    "g25_flash_analysis": PAPER_RESULTS / "g25_flash_docker" / "g25_flash_analysis.json",
    "e10_simple_baselines": PAPER_RESULTS / "e10_simple_baselines.json",
    "why85_path": PAPER_RESULTS / "why85_path.json",
    "pareto_analysis": PAPER_RESULTS / "pareto_analysis" / "pareto_results.json",
    "cross_model_regression": PAPER_RESULTS / "cross_model_pivot" / "regression_summary_final.json",
    "e_value_comparison": PAPER_RESULTS / "e_value_comparison.json",
    "a1_violation_summary": PAPER_RESULTS / "a1_violation" / "a1_violation_summary.json",
}

REPO_ID = "neogenesislab/whylab-gemini-2-5-docker-validation"


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


def load_text(path: Path) -> str | None:
    if not path.exists():
        return None
    return path.read_text(encoding="utf-8")


def load_json(path: Path) -> dict | None:
    txt = load_text(path)
    if txt is None:
        return None
    return json.loads(txt)


def build_artifacts() -> tuple[list[tuple[str, bytes]], dict]:
    """Return (artifacts, summary). Each artifact is (path_in_repo, bytes)."""
    artifacts: list[tuple[str, bytes]] = []
    summary: dict = {}

    # 1) Headline: 67 problems × 402 episodes (Gemini 2.5 Flash Docker)
    chk_path = SOURCES["checkpoints_jsonl"]
    if chk_path.exists():
        raw = chk_path.read_bytes()
        artifacts.append(("data/episodes.jsonl", raw))
        summary["episodes_jsonl_bytes"] = len(raw)
        # Count lines
        text = chk_path.read_text(encoding="utf-8")
        summary["episode_lines"] = sum(1 for ln in text.splitlines() if ln.strip())
    else:
        print(f"WARN: missing {chk_path}")

    # 2) Aggregate analysis
    g25 = load_json(SOURCES["g25_flash_analysis"])
    if g25:
        artifacts.append(("data/g25_flash_analysis.json",
                         json.dumps(g25, ensure_ascii=False, indent=2).encode("utf-8")))
        summary["g25_flash_analysis"] = g25

    # 3) Simple baselines (E10)
    e10 = load_json(SOURCES["e10_simple_baselines"])
    if e10:
        artifacts.append(("data/e10_simple_baselines.json",
                         json.dumps(e10, ensure_ascii=False, indent=2).encode("utf-8")))
        summary["e10_methods"] = len(e10.get("methods", [])) if isinstance(e10.get("methods"), list) else "n/a"

    # 4) 8.5 path analysis (selective followup audit)
    w85 = load_json(SOURCES["why85_path"])
    if w85:
        artifacts.append(("data/why85_path_analysis.json",
                         json.dumps(w85, ensure_ascii=False, indent=2).encode("utf-8")))

    # 5) Pareto analysis
    pareto = load_json(SOURCES["pareto_analysis"])
    if pareto:
        artifacts.append(("data/pareto_results.json",
                         json.dumps(pareto, ensure_ascii=False, indent=2).encode("utf-8")))

    # 6) Cross-model regression
    crossm = load_json(SOURCES["cross_model_regression"])
    if crossm:
        artifacts.append(("data/cross_model_regression.json",
                         json.dumps(crossm, ensure_ascii=False, indent=2).encode("utf-8")))

    # 7) E-value comparison
    eval_cmp = load_json(SOURCES["e_value_comparison"])
    if eval_cmp:
        artifacts.append(("data/e_value_comparison.json",
                         json.dumps(eval_cmp, ensure_ascii=False, indent=2).encode("utf-8")))

    # 8) A1 violation summary
    a1v = load_json(SOURCES["a1_violation_summary"])
    if a1v:
        artifacts.append(("data/a1_violation_summary.json",
                         json.dumps(a1v, ensure_ascii=False, indent=2).encode("utf-8")))

    return artifacts, summary


def build_readme(summary: dict) -> str:
    n_episodes = summary.get("episode_lines", "402")
    yaml_front = """---
language:
- en
- ko
license: cc-by-4.0
task_categories:
- other
tags:
- causal-inference
- llm-evaluation
- swe-bench
- docker
- gemini-2-5-flash
- code-generation
- ai-safety
- honest-null-result
- whylab
- selective-intervention
size_categories:
- 1K<n<10K
pretty_name: "WhyLab Gemini 2.5 Flash Docker Validation (Honest Null Result)"
---
"""
    body = f"""
# WhyLab Gemini 2.5 Flash Docker Validation (Honest Null Result)

> Underlying experimental evidence from **[Neo Genesis](https://neogenesis.app)**'s NeurIPS 2026 paper *"WhyLab: Causal Decision Intelligence Engine — Selective C2 Real-Task Validation on SWE-bench"* — released as an open dataset to support reproducibility and to document **an honest null result**.

## What this dataset is

The full episode-level evidence from a **Docker ground-truth validation** of WhyLab's adaptive C2 (Causal Constraint) method on SWE-bench, using **Gemini 2.5 Flash** as the underlying language model.

| Run | Configuration |
|---|---|
| Model | `gemini-2.5-flash` (Google) |
| Substrate | SWE-bench (selective slice — E9 baseline-fail subset) |
| Ground truth | Docker container test execution (not LLM judge) |
| Problems | 67 |
| Seeds | 3 (deterministic temperature, controlled seed sweep) |
| Conditions | `baseline` and `whylab_c2` |
| Total episodes | **{n_episodes}** |

## Why publish a null result

Most papers withhold experiments that don't support the headline claim. WhyLab took the opposite path: **the selective adaptive C2 follow-up did NOT beat fixed C2** on this slice. We publish the underlying episode-level data anyway because:

1. **Reproducibility matters more than narrative**. Other researchers can re-run `gemini-2.5-flash` on this exact 67-problem slice and check whether the null persists.
2. **The result drove a paper recalibration**. The original adaptive C2 promotion claim was demoted; the manuscript was reframed around **phase-aware deployment** and **selective intervention** rather than universal gain.
3. **Docker ground-truth integrity**. Unlike LLM-judge benchmarks, Docker container execution provides irreducible signal — if a code change breaks the test suite, the test fails. This dataset is one of the few publicly available Docker-grounded LLM evaluation corpora in this size class.

## Headline statistics

The companion `g25_flash_analysis.json` (paper-grade aggregate) reports the per-condition pass rate, oscillation rate, regression rate, and mean rejection count. The honest finding:

- **No significant net gain** of adaptive C2 over fixed C2 on `pass`, `oscillation`, or `regression` rates
- **Mean rejection count decreased** (adaptive C2 issued fewer rejections than fixed C2)
- The decrease in rejection count was **not** accompanied by a corresponding increase in pass rate — i.e. adaptive C2 was less aggressive but no more accurate

## Comparison table (paper-level, reconstructed from `e10_simple_baselines.json`)

| Method | Description | Net gain vs `simple_retry`? |
|---|---|---|
| `simple_retry` | Just retry on failure (no constraint) | — (baseline) |
| `fixed_c2` | Apply WhyLab's static C2 (Causal Constraint) on every attempt | Modest, environment-dependent |
| `adaptive_c2` | Adapt C2 strength based on phase signal | **No statistically defensible gain** on this Docker slice |

The full paper reports significance tests, oscillation analysis, and Pareto frontier comparison.

## Files

```
data/
├── episodes.jsonl               One JSONL line per episode (67 × 3 seeds × 2 conditions = 402)
├── g25_flash_analysis.json      Paper-grade aggregate per-condition statistics
├── e10_simple_baselines.json    Simple-baseline comparison (simple_retry / fixed C2 / adaptive C2)
├── why85_path_analysis.json     8.5 path audit (analyze_85_path output, paper-internal)
├── pareto_results.json          Pareto frontier: pass-rate vs rejection cost
├── cross_model_regression.json  Cross-model regression summary (final paper version)
├── e_value_comparison.json      E-value (anytime-valid) comparison vs t-test
└── a1_violation_summary.json    A1 (audit-1) violation rate summary from E6 traces
```

## Schema (`data/episodes.jsonl`)

Each line is one episode (one seed × one problem × one condition):

```json
{{
  "seed": 42,
  "problem_id": "django__django-12345",
  "condition": "whylab_c2",
  "passed": false,
  "attempts": 3,
  "rejections": 1,
  "oscillated": false,
  "regression": false,
  "trajectory": [...]
}}
```

Field semantics:
- `seed` — random seed controlling LLM sampling temperature
- `problem_id` — SWE-bench task ID (Django / SymPy / Sphinx / scikit-learn / etc.)
- `condition` — `"baseline"` (no constraint) or `"whylab_c2"` (adaptive C2)
- `passed` — Docker test suite verdict (true = all tests pass)
- `attempts` — number of LLM calls used before stopping
- `rejections` — count of audit-1 (A1) rejections issued by the C2 layer
- `oscillated` — true if the trajectory oscillated between two solutions
- `regression` — true if the trajectory introduced a new test failure
- `trajectory` — full agent trajectory (truncated for episode-level dataset; full traces available on request)

## Quick start

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", split="train", data_files="data/episodes.jsonl")
print(len(ds), "episodes")

# Per-condition pass rate
import collections
counts = collections.Counter()
for ep in ds:
    counts[(ep["condition"], ep["passed"])] += 1
for cond in ("baseline", "whylab_c2"):
    n = counts[(cond, True)] + counts[(cond, False)]
    p = counts[(cond, True)] / n if n else 0
    print(f"{{cond}}: pass rate = {{p:.3f}} ({{counts[(cond, True)]}} / {{n}})")
```

## Reproducing the paper's null result

The full experimental harness is documented in the WhyLab paper appendix (frozen anchor `88fa509` on `submission-freeze/whylab-20260414`). The selective-followup runner is `experiments/e9_swebench_selective.py`. Re-running it on `gemini-2.5-flash` with the same 67-problem slice and 3 seeds will produce statistically equivalent (null) results.

## Calibration history (paper-internal)

- `E5` — Stable-regime calibration sanity check (single-model, single-environment)
- `E7v2` — Initial pairwise-positive significance, 3-way underpowered
- `E9` — Original adaptive C2 promotion attempt → **demoted**
- `E10` — Simple baselines comparison (this dataset)
- `Gemini 2.5 Flash Docker` — **headline null** (this dataset)
- Outcome: paper reframed around `phase-aware deployment` + `selective intervention`, not universal gain

## Related Neo Genesis assets

- 📄 **Paper page** — https://neogenesis.app/data/research/whylab-gemini-2-5-docker-validation
- 🤗 **Companion datasets**:
  - [`neogenesislab/korean-rag-ssot-golden-50`](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50)
  - [`neogenesislab/ethicaai-mixed-safe-evidence`](https://huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence)
- 🆔 **Wikidata** — [Q139569716 (WhyLab)](https://www.wikidata.org/wiki/Q139569716) · [Q139569680 (Neo Genesis parent org)](https://www.wikidata.org/wiki/Q139569680)
- 🌐 **Org site** — https://neogenesis.app

## Citation

```bibtex
@inproceedings{{whylab_neurips2026_g25_docker,
  title     = {{WhyLab: Causal Decision Intelligence Engine — Selective C2 Real-Task Validation on SWE-bench (Honest Null Result)}},
  author    = {{Heo, Yesol}},
  booktitle = {{Submitted to NeurIPS 2026}},
  year      = {{2026}},
  url       = {{https://huggingface.co/datasets/{REPO_ID}}},
  note      = {{Underlying evidence dataset, CC-BY-4.0. Honest null result on Gemini 2.5 Flash Docker SWE-bench selective slice.}}
}}
```

## License

CC-BY-4.0. Free for research and commercial use with attribution to **Neo Genesis** and the underlying paper.

## Provenance

- Compute: YSH-Server (`16-core / 16 GiB`) — `/home/ysh/whylab_docker_g25_full/` workdir
- Launch: 2026-04-08 16:19:29 KST
- Curation: Yesol Heo (sole founder/operator, [neogenesis.app](https://neogenesis.app))
- Frozen anchor: `88fa509` on `submission-freeze/whylab-20260414` git ref
- Released: 2026-04-29

## 한국어 요약

**WhyLab Gemini 2.5 Flash Docker Validation** 은 **[Neo Genesis](https://neogenesis.app)** 의 NeurIPS 2026 논문 *"WhyLab: Causal Decision Intelligence Engine"* 의 핵심 실험 데이터를 공개한 것이다.

**핵심 메시지**: WhyLab 의 적응형 C2 방법이 SWE-bench 선택적 슬라이스에서 고정 C2 를 **이기지 못했다는 정직한 null 결과**다. 67 problems × 3 seeds × 2 conditions = 402 episodes 의 Docker 컨테이너 ground-truth 검증 데이터를 그대로 공개해 재현성을 보장한다.

이 결과로 인해 논문은 **단일 환경에서의 보편적 이득 주장 대신 `phase-aware deployment` 와 `selective intervention` 으로 재구성**됐다. Docker ground-truth 검증 데이터셋은 이 규모로 공개된 사례가 드물며, 다른 연구자가 같은 67 문제 슬라이스로 `gemini-2.5-flash` 를 재실행해 null 이 지속되는지 검증할 수 있다.

라이선스 CC-BY-4.0 — 인용 시 자유롭게 사용 가능.
"""
    return yaml_front + body


def main() -> int:
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN missing", file=sys.stderr)
        return 1

    print("Loading sources...")
    artifacts, summary = build_artifacts()
    if not artifacts:
        print("ERROR: no artifacts built — source files all missing", file=sys.stderr)
        return 1

    readme = build_readme(summary).encode("utf-8")
    artifacts.append(("README.md", readme))

    metadata = {
        "name": "WhyLab Gemini 2.5 Flash Docker Validation (Honest Null Result)",
        "version": "1.0",
        "released": "2026-04-29",
        "license": "CC-BY-4.0",
        "model": "gemini-2.5-flash",
        "substrate": "SWE-bench (selective slice, E9 baseline-fail)",
        "ground_truth": "Docker container test execution",
        "problems": 67,
        "seeds": 3,
        "conditions": ["baseline", "whylab_c2"],
        "episodes": summary.get("episode_lines", 402),
    }
    artifacts.append(("metadata.json", json.dumps(metadata, ensure_ascii=False, indent=2).encode("utf-8")))

    from huggingface_hub import HfApi
    api = HfApi(token=token)

    print(f"\ncreate_repo {REPO_ID}")
    api.create_repo(repo_id=REPO_ID, repo_type="dataset", exist_ok=True, private=False)

    for path_in_repo, content in artifacts:
        size = len(content)
        print(f"upload {path_in_repo} ({size:,} bytes)")
        api.upload_file(
            path_or_fileobj=io.BytesIO(content),
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
