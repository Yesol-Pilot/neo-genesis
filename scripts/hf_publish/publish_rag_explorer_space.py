"""
HuggingFace Spaces publish — Korean RAG SSOT Golden 50 Explorer (Gradio)

Source : tests/rag_golden/ssot_korean_v2.json (read for verification only — Space pulls from HF dataset at runtime)
Dataset: huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50 (already published)
Target : huggingface.co/spaces/neogenesislab/korean-rag-ssot-golden-50-explorer

Layout (uploaded to the Space repo):
    README.md          Space metadata (YAML frontmatter for HF Spaces)
    app.py             Gradio interface — browse, filter, BM25 demo retrieval, recall@10 calculation
    requirements.txt   gradio + datasets + pandas + rank_bm25
    .gitattributes     text auto

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/publish_rag_explorer_space.py
"""
import io
import json
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SOURCE = ROOT / "tests" / "rag_golden" / "ssot_korean_v2.json"
ENV_LOCAL = ROOT / ".env.local"
SPACE_ID = "neogenesislab/korean-rag-ssot-golden-50-explorer"
DATASET_ID = "neogenesislab/korean-rag-ssot-golden-50"


def load_env(path: Path) -> None:
    if not path.exists():
        return
    with path.open(encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            os.environ.setdefault(k, v)


# ---------------------------------------------------------------------------
# Space artifacts
# ---------------------------------------------------------------------------

APP_PY = '''"""
Korean RAG SSOT Golden 50 — Interactive Explorer
================================================

Browse, filter, and demo a BM25 baseline retrieval against the
``neogenesislab/korean-rag-ssot-golden-50`` benchmark.

Built by Neo Genesis (https://neogenesis.app) — a 1-person AI-native
operator running 11 production AI business units. Source SSOT lives at
``.agent/`` of the private monorepo. This benchmark is a 50-task slice
released for public evaluation under CC-BY-4.0.
"""
from __future__ import annotations

import re
from typing import Iterable

import gradio as gr
import pandas as pd
from datasets import load_dataset
from rank_bm25 import BM25Okapi

DATASET_ID = "neogenesislab/korean-rag-ssot-golden-50"

# ---------------------------------------------------------------------------
# Data loading (one-shot at Space cold start)
# ---------------------------------------------------------------------------
ds = load_dataset(DATASET_ID, split="train")
TASKS = list(ds)

CATEGORY_OF = {
    "rag_v2_design": list(range(0, 18)),
    "quant_v11": list(range(18, 26)),
    "ssot_governance": list(range(26, 38)),
    "security_pii": list(range(38, 44)),
    "operations": list(range(44, 50)),
}


def task_category(task_id: str) -> str:
    """Recover the category for a task id from the published id ranges.

    The dataset card encodes the layout as 18+8+12+6+6 = 50 in fixed order, so
    we can map by index without re-reading the metadata.json.
    """
    try:
        idx = int(task_id.split("-")[-1]) - 1
    except Exception:
        return "unknown"
    for cat, idxs in CATEGORY_OF.items():
        if idx in idxs:
            return cat
    return "unknown"


# ---------------------------------------------------------------------------
# BM25 baseline retriever
#
# Corpus = the union of all ``expected_chunks`` paths across the 50 tasks.
# We tokenize on whitespace + path separators so file paths like
# ``.agent/knowledge/rag-master/08_rollout_24w.md`` get split into the
# domain words (``agent``, ``knowledge``, ``rag-master``, ``rollout``).
# This is intentionally a *demo* baseline — the production stack uses
# kiwipiepy + KURE-v1 + BGE Reranker v2-m3 (see dataset card §Evaluation).
# ---------------------------------------------------------------------------
ALL_CHUNKS = sorted(
    {chunk for t in TASKS for chunk in t["expected_chunks"]}
)


_TOK = re.compile(r"[\\w\\u3131-\\uD79D]+", re.UNICODE)


def tokenize(text: str) -> list[str]:
    """Light hybrid tokenizer: splits on path separators + Hangul/Latin words.

    Lower-cases ASCII so query ``QDRANT`` matches path ``qdrant``.
    """
    text = text.replace("/", " ").replace("_", " ").replace("-", " ").replace(".", " ")
    return [m.group(0).lower() for m in _TOK.finditer(text)]


CORPUS_TOKENS = [tokenize(c) for c in ALL_CHUNKS]
BM25 = BM25Okapi(CORPUS_TOKENS)


def bm25_topk(query: str, k: int = 10) -> list[tuple[str, float]]:
    if not query.strip():
        return []
    scores = BM25.get_scores(tokenize(query))
    pairs = sorted(zip(ALL_CHUNKS, scores), key=lambda x: -x[1])
    return [(p, s) for p, s in pairs[:k] if s > 0.0]


def recall_at_k(retrieved_paths: Iterable[str], expected_chunks: Iterable[str], k: int = 10) -> float:
    retrieved_set = set(list(retrieved_paths)[:k])
    expected_set = set(expected_chunks)
    if not expected_set:
        return 0.0
    return len(retrieved_set & expected_set) / len(expected_set)


# ---------------------------------------------------------------------------
# Gradio UI handlers
# ---------------------------------------------------------------------------

def filter_tasks(category: str) -> pd.DataFrame:
    rows = []
    for t in TASKS:
        cat = task_category(t["id"])
        if category != "all" and cat != category:
            continue
        rows.append({
            "id": t["id"],
            "category": cat,
            "query": t["query"],
            "expected_source_type": t["expected_source_type"],
            "expected_chunks": " | ".join(t["expected_chunks"][:3]) + (
                f" (+{len(t['expected_chunks']) - 3} more)" if len(t["expected_chunks"]) > 3 else ""
            ),
            "expected_substrings": ", ".join(t["expected_answer_substrings"][:5]),
            "max_latency_ms": t["max_latency_ms"],
        })
    return pd.DataFrame(rows)


def run_bm25_demo(query: str, k: int):
    """Return (markdown summary, retrieval dataframe, oracle recall card)."""
    if not query or not query.strip():
        return (
            "_Enter a query above to run the BM25 baseline._",
            pd.DataFrame(columns=["rank", "score", "chunk_path"]),
            "—",
        )
    hits = bm25_topk(query, k=k)
    if not hits:
        return (
            "_No chunks scored > 0 for this query. Try a Korean keyword from the dataset card._",
            pd.DataFrame(columns=["rank", "score", "chunk_path"]),
            "—",
        )
    df = pd.DataFrame(
        [{"rank": i + 1, "score": f"{s:.3f}", "chunk_path": p} for i, (p, s) in enumerate(hits)]
    )

    # Oracle recall — if the user pasted exactly one of the dataset queries,
    # report recall@k against that task. Otherwise report the best-matching
    # task by query equality (case-insensitive substring).
    oracle = None
    q_lower = query.strip().lower()
    for t in TASKS:
        if t["query"].strip().lower() == q_lower or q_lower in t["query"].lower():
            oracle = t
            break

    if oracle is None:
        oracle_md = "_Query did not match any benchmark task verbatim — recall@k oracle unavailable._"
    else:
        retrieved_paths = [p for p, _ in hits]
        r_at_k = recall_at_k(retrieved_paths, oracle["expected_chunks"], k=k)
        expected_md = "\\n".join(f"- `{c}`" for c in oracle["expected_chunks"])
        oracle_md = (
            f"### Oracle match: `{oracle['id']}` ({task_category(oracle['id'])})\\n\\n"
            f"**Recall@{k}** = `{r_at_k:.3f}` "
            f"(target ≥ 0.85 with the production stack — BM25 alone is the baseline floor)\\n\\n"
            f"**Expected chunks ({len(oracle['expected_chunks'])}):**\\n{expected_md}"
        )

    summary = (
        f"### BM25 baseline returned {len(hits)} chunks (top {k})\\n\\n"
        f"Query: `{query}`\\n\\n"
        f"Corpus size: {len(ALL_CHUNKS)} unique chunk paths "
        f"across the {len(TASKS)} benchmark tasks."
    )
    return summary, df, oracle_md


def task_detail(task_id: str) -> str:
    if not task_id:
        return "_Pick a task id above (e.g. `kor-001`)._"
    for t in TASKS:
        if t["id"] == task_id.strip():
            cat = task_category(t["id"])
            chunks = "\\n".join(f"- `{c}`" for c in t["expected_chunks"])
            substrs = ", ".join(f"`{s}`" for s in t["expected_answer_substrings"])
            return (
                f"### {t['id']} — {cat}\\n\\n"
                f"**Query**: {t['query']}\\n\\n"
                f"**Expected collections**: {', '.join(f'`{c}`' for c in t['expected_collections'])}\\n\\n"
                f"**Expected source type**: `{t['expected_source_type']}`\\n\\n"
                f"**Max latency**: `{t['max_latency_ms']} ms`\\n\\n"
                f"**Expected chunks ({len(t['expected_chunks'])}):**\\n{chunks}\\n\\n"
                f"**Expected answer substrings**: {substrs}"
            )
    return f"_Task `{task_id}` not found. Try `kor-001` through `kor-050`._"


# ---------------------------------------------------------------------------
# Gradio app
# ---------------------------------------------------------------------------

INTRO_MD = f"""
# Korean RAG SSOT Golden 50 — Interactive Explorer

A 50-task Korean retrieval-augmented generation evaluation set extracted from the live
SSOT (`.agent/`) of [Neo Genesis](https://neogenesis.app) — a 1-person AI-native company
running **11 production AI business units**.

Unlike Wikipedia-style QA benchmarks, this dataset stress-tests retrieval against
**operational governance text** (design docs, runbooks, policy YAML, incident logs)
where the answer is grounded in human-authored SSOT rather than encyclopedic facts.

- **Dataset card**: [`{DATASET_ID}`](https://huggingface.co/datasets/{DATASET_ID})
- **License**: CC-BY-4.0 (data) · MIT (this Space's app code)
- **Wikidata**: [Q139569680 (Neo Genesis)](https://www.wikidata.org/wiki/Q139569680)
- **Production stack**: kiwipiepy + KURE-v1 + BGE Reranker v2-m3 (target Recall@10 ≥ 0.85)
- **This Space's baseline**: pure BM25 over chunk paths — a demo floor, not the production retriever
"""

CATEGORIES = ["all"] + list(CATEGORY_OF.keys())

with gr.Blocks(title="Korean RAG SSOT Golden 50 Explorer", theme=gr.themes.Soft()) as demo:
    gr.Markdown(INTRO_MD)

    with gr.Tab("Browse tasks"):
        with gr.Row():
            cat_dd = gr.Dropdown(
                choices=CATEGORIES,
                value="all",
                label="Category filter",
                info="18 rag_v2_design + 8 quant_v11 + 12 ssot_governance + 6 security_pii + 6 operations = 50",
            )
        task_table = gr.DataFrame(
            value=filter_tasks("all"),
            label="Tasks",
            wrap=True,
            interactive=False,
        )
        cat_dd.change(filter_tasks, inputs=cat_dd, outputs=task_table)

    with gr.Tab("Task detail"):
        gr.Markdown("Pick a task id (e.g. `kor-001`) to see the full schema.")
        with gr.Row():
            task_id_in = gr.Textbox(
                label="Task id",
                placeholder="kor-001",
                value="kor-001",
                scale=1,
            )
            view_btn = gr.Button("Show task", scale=0)
        detail_md = gr.Markdown(task_detail("kor-001"))
        view_btn.click(task_detail, inputs=task_id_in, outputs=detail_md)
        task_id_in.submit(task_detail, inputs=task_id_in, outputs=detail_md)

    with gr.Tab("BM25 retrieval demo"):
        gr.Markdown(
            "Run a pure-BM25 baseline against the corpus of all expected chunk paths. "
            "Paste one of the benchmark queries (or a Korean keyword like "
            "`Qdrant 컨테이너`, `Kill Switch 9-Layer`, `주민번호 redaction`) "
            "to see the retrieved paths and, when the query matches a benchmark task, "
            "the oracle Recall@k."
        )
        with gr.Row():
            query_in = gr.Textbox(
                label="Query (Korean)",
                placeholder="예: Phase 0 Day 1 작업 중 Qdrant 컨테이너를 어디에 띄우는가?",
                lines=2,
                scale=4,
            )
            k_in = gr.Slider(
                minimum=1, maximum=20, value=10, step=1, label="Top-k", scale=1
            )
            run_btn = gr.Button("Run BM25", variant="primary", scale=1)
        summary_md = gr.Markdown()
        with gr.Row():
            hits_df = gr.DataFrame(
                value=pd.DataFrame(columns=["rank", "score", "chunk_path"]),
                label="Retrieved chunks",
                wrap=True,
                interactive=False,
            )
        oracle_md = gr.Markdown()
        run_btn.click(run_bm25_demo, inputs=[query_in, k_in], outputs=[summary_md, hits_df, oracle_md])
        query_in.submit(run_bm25_demo, inputs=[query_in, k_in], outputs=[summary_md, hits_df, oracle_md])

    with gr.Tab("About"):
        gr.Markdown(
            f"""
### Dataset summary

| | |
|---|---|
| **Tasks** | {len(TASKS)} |
| **Unique chunk paths** | {len(ALL_CHUNKS)} |
| **Languages** | Korean (queries) + Korean/English (corpus paths) |
| **License** | CC-BY-4.0 |
| **Curator** | Yesol Heo (Neo Genesis) |

### Citation

```bibtex
@misc{{neogenesis_korean_rag_ssot_golden_50,
  title  = {{Korean RAG SSOT Golden 50: An operational retrieval evaluation set in Korean}},
  author = {{Heo, Yesol}},
  year   = {{2026}},
  url    = {{https://huggingface.co/datasets/{DATASET_ID}}}
}}
```

### Why operational SSOT, not Wikipedia?

Production AI agents need to retrieve from **the same governance text humans use to operate the
business** — design docs, runbooks, policy YAML, incident logs. KorQuAD / KLUE-MRC / MIRACL-ko
all evaluate factual QA over Wikipedia or news; they don't measure whether your retriever can
trust a human-authored design decision over a synthetic LLM summary that happens to sit nearby.
Every task in this benchmark carries `expected_source_type` (`human` / `llm_output` /
`external_citation` / `tool_log`) precisely so this can be measured.
"""
        )

if __name__ == "__main__":
    # Gradio 5.x auto-detects HF Spaces (binds 0.0.0.0:7860 from env).
    demo.queue().launch()
'''

REQUIREMENTS_TXT = """gradio==5.9.1
datasets>=2.21,<4
pandas>=2.0
rank-bm25>=0.2.2
"""

GITATTRIBUTES = "* text=auto eol=lf\n"


def build_space_readme() -> str:
    """README with HF Spaces YAML frontmatter.

    Gradio 5.x is pinned because the HF Spaces base image runs Python 3.13, which
    removed ``audioop`` from stdlib — Gradio 4.x's pydub dep cannot import. Gradio 5.x
    handles 3.13 natively. The DataFrame component API is the same shape we use here
    (value=DataFrame, label, wrap, interactive), so no app.py changes were needed.
    """
    yaml_front = """---
title: Korean RAG SSOT Golden 50 Explorer
emoji: 🔍
colorFrom: indigo
colorTo: pink
sdk: gradio
sdk_version: 5.9.1
app_file: app.py
pinned: false
license: mit
short_description: Browse and BM25-test the Neo Genesis Korean RAG benchmark.
tags:
- korean
- rag
- evaluation
- retrieval-augmented-generation
- agent-evaluation
- governance
datasets:
- neogenesislab/korean-rag-ssot-golden-50
---
"""
    body = """
# Korean RAG SSOT Golden 50 — Interactive Explorer

This Space provides a Gradio UI to browse, filter, and run a BM25 baseline against the
[`neogenesislab/korean-rag-ssot-golden-50`](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50)
benchmark — 50 hand-curated Korean retrieval-evaluation tasks extracted from the live
SSOT of [Neo Genesis](https://neogenesis.app), a 1-person AI-native company operating
**11 production AI business units**.

## Why
Most Korean RAG benchmarks (KorQuAD, KLUE-MRC, MIRACL-ko) evaluate factual QA over
Wikipedia. Production agents instead retrieve from **operational governance text** —
design docs, runbooks, policy YAML, incident logs — where the answer is grounded in
human-authored SSOT rather than encyclopedic facts. This dataset measures that.

## Tabs
1. **Browse tasks** — paginated table with category filter (18 + 8 + 12 + 6 + 6 = 50).
2. **Task detail** — full schema for any `kor-001` … `kor-050` task.
3. **BM25 retrieval demo** — pure-BM25 baseline + oracle Recall@k when the query matches
   a benchmark task verbatim.
4. **About** — dataset stats + citation.

## Stack
- `gradio==5.9.1` (Python 3.13 compatible)
- `datasets` (loads the parent dataset at cold start)
- `rank_bm25` (BM25Okapi baseline)
- `pandas`

## License
- App code: **MIT** (this Space)
- Data: **CC-BY-4.0** (parent dataset)

## Cite
```bibtex
@misc{neogenesis_korean_rag_ssot_golden_50,
  title  = {Korean RAG SSOT Golden 50: An operational retrieval evaluation set in Korean},
  author = {Heo, Yesol},
  year   = {2026},
  url    = {https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50}
}
```
"""
    return yaml_front + body


# ---------------------------------------------------------------------------
# Publish
# ---------------------------------------------------------------------------

def main() -> int:
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN not found in env", file=sys.stderr)
        return 1

    if not SOURCE.exists():
        print(f"ERROR: source verification file not found: {SOURCE}", file=sys.stderr)
        return 1

    # Sanity-check the source dataset has 50 tasks (parent dataset already published).
    with SOURCE.open(encoding="utf-8") as f:
        meta = json.load(f)
    n_tasks = len(meta.get("tasks", []))
    if n_tasks != 50:
        print(f"WARN: parent dataset has {n_tasks} tasks (expected 50)", file=sys.stderr)
    else:
        print(f"OK: parent dataset has {n_tasks} tasks")

    # Build artifacts in-memory.
    readme = build_space_readme()
    print(f"prepared README.md ({len(readme):,} bytes)")
    print(f"prepared app.py ({len(APP_PY):,} bytes)")
    print(f"prepared requirements.txt ({len(REQUIREMENTS_TXT):,} bytes)")
    print(f"prepared .gitattributes ({len(GITATTRIBUTES):,} bytes)")

    # Push to HF Spaces.
    from huggingface_hub import HfApi

    api = HfApi(token=token)

    print(f"create_repo {SPACE_ID} (space, gradio, public)")
    api.create_repo(
        repo_id=SPACE_ID,
        repo_type="space",
        space_sdk="gradio",
        exist_ok=True,
        private=False,
    )

    uploads = [
        ("README.md", readme),
        ("app.py", APP_PY),
        ("requirements.txt", REQUIREMENTS_TXT),
        (".gitattributes", GITATTRIBUTES),
    ]

    for path_in_repo, content in uploads:
        print(f"upload {path_in_repo} ({len(content):,} bytes)")
        api.upload_file(
            path_or_fileobj=io.BytesIO(content.encode("utf-8")),
            path_in_repo=path_in_repo,
            repo_id=SPACE_ID,
            repo_type="space",
            commit_message=f"add {path_in_repo}",
        )

    url = f"https://huggingface.co/spaces/{SPACE_ID}"
    print()
    print("PUBLISHED:", url)

    # Best-effort runtime status check (Spaces auto-build on first push).
    try:
        info = api.space_info(repo_id=SPACE_ID)
        runtime = getattr(info, "runtime", None)
        stage = getattr(runtime, "stage", None) if runtime else None
        hardware = getattr(runtime, "hardware", None) if runtime else None
        print(f"runtime.stage = {stage}")
        print(f"runtime.hardware = {hardware}")
    except Exception as exc:  # noqa: BLE001
        print(f"(non-fatal) space_info() not yet available: {exc}")

    # Live HTTP HEAD verification.
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"HEAD {url} -> {resp.status}")
    except Exception as exc:  # noqa: BLE001
        print(f"(non-fatal) HEAD check failed: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
