"""
HuggingFace Spaces publish — Cross-Agent Review Queue Explorer (Gradio)

Source dataset : huggingface.co/datasets/neogenesislab/cross-agent-review-queue-2026
                 (config="transcripts", 37 rows, 18 cols, anonymized)
Target Space   : huggingface.co/spaces/neogenesislab/cross-agent-review-queue-explorer

Layout uploaded to the Space repo:
    README.md          Space metadata (YAML frontmatter for HF Spaces)
    app.py             Gradio interface — browse, detail, statistics, about
    requirements.txt   gradio + datasets + pandas + plotly
    .gitattributes     text auto

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/publish_cross_agent_explorer_space.py
"""
from __future__ import annotations

import io
import os
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = ROOT / ".env.local"
SPACE_ID = "neogenesislab/cross-agent-review-queue-explorer"
DATASET_ID = "neogenesislab/cross-agent-review-queue-2026"
DATASET_CONFIG = "transcripts"


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
Cross-Agent Review Queue Explorer
=================================

Browse, filter, and analyze 37 anonymized cross-agent code-review checkpoints
from the Neo Genesis monorepo (Codex <-> Claude, 2026-04-08 ~ 2026-04-14).

Data source: ``neogenesislab/cross-agent-review-queue-2026`` (config=transcripts)
"""
from __future__ import annotations

import collections
import re
from typing import Any

import gradio as gr
import pandas as pd
import plotly.express as px
from datasets import load_dataset

DATASET_ID = "neogenesislab/cross-agent-review-queue-2026"
DATASET_CONFIG = "transcripts"

# ---------------------------------------------------------------------------
# Cold-start data load
# ---------------------------------------------------------------------------
ds = load_dataset(DATASET_ID, DATASET_CONFIG, split="train")
ROWS: list[dict[str, Any]] = list(ds)


def _year_month(checkpoint_id: str) -> str:
    """Parse ``ccr-20260408-121555`` -> ``2026-04``."""
    m = re.search(r"(\\d{4})(\\d{2})\\d{2}", checkpoint_id or "")
    if m:
        return f"{m.group(1)}-{m.group(2)}"
    return "unknown"


def _word_count(text: str | None) -> int:
    if not text:
        return 0
    return len(str(text).split())


# Pre-compute derived columns once.
for r in ROWS:
    r["year_month"] = _year_month(r.get("id", ""))
    r["prompt_words"] = _word_count(r.get("prompt"))
    r["response_words"] = _word_count(r.get("response"))


REVIEW_LENSES = sorted({r.get("review_lens", "") or "" for r in ROWS})
TARGET_AGENTS = sorted({r.get("target", "") or "" for r in ROWS})
RESULTS = sorted({r.get("result", "") or "" for r in ROWS})
YEAR_MONTHS = sorted({r["year_month"] for r in ROWS})

ALL_FILTER = "all"


# ---------------------------------------------------------------------------
# Tab 1: Browse
# ---------------------------------------------------------------------------

def filter_rows(
    review_lens: str,
    target_agent: str,
    result: str,
    year_month: str,
) -> pd.DataFrame:
    out = []
    for r in ROWS:
        if review_lens != ALL_FILTER and (r.get("review_lens") or "") != review_lens:
            continue
        if target_agent != ALL_FILTER and (r.get("target") or "") != target_agent:
            continue
        if result != ALL_FILTER and (r.get("result") or "") != result:
            continue
        if year_month != ALL_FILTER and r["year_month"] != year_month:
            continue
        title = (r.get("title") or "").strip()
        if len(title) > 80:
            title = title[:77] + "..."
        out.append({
            "id": r.get("id"),
            "year_month": r["year_month"],
            "target": r.get("target"),
            "model": r.get("model"),
            "review_lens": (r.get("review_lens") or "")[:50],
            "result": r.get("result"),
            "title": title,
            "response_words": r.get("response_words"),
        })
    return pd.DataFrame(out)


# ---------------------------------------------------------------------------
# Tab 2: Detail
# ---------------------------------------------------------------------------

def review_detail(checkpoint_id: str) -> str:
    if not checkpoint_id:
        return "_Pick a checkpoint id (e.g. `ccr-20260408-121555`)._"
    cid = checkpoint_id.strip()
    for r in ROWS:
        if r.get("id") == cid:
            parts = []
            parts.append(f"## {r.get('id')}")
            parts.append("")
            parts.append(f"**created_at**: `{r.get('created_at')}`  ")
            parts.append(f"**requester** -> **target**: `{r.get('requester')}` -> `{r.get('target')}`  ")
            parts.append(f"**mode**: `{r.get('mode')}` | **model**: `{r.get('model')}` | **scope**: `{r.get('scope')}`  ")
            parts.append(f"**review_lens**: `{r.get('review_lens')}` | **result**: `{r.get('result')}`  ")
            parts.append("")
            if r.get("title"):
                parts.append(f"### Title")
                parts.append(f"> {r.get('title')}")
                parts.append("")
            if r.get("owner_goal"):
                parts.append(f"### Owner goal")
                parts.append(f"> {r.get('owner_goal')}")
                parts.append("")
            if r.get("owner_intent"):
                parts.append(f"### Owner intent")
                parts.append(f"> {r.get('owner_intent')}")
                parts.append("")
            if r.get("constraints"):
                parts.append(f"### Constraints")
                parts.append(f"> {r.get('constraints')}")
                parts.append("")
            if r.get("success_criteria"):
                parts.append(f"### Success criteria")
                parts.append(f"> {r.get('success_criteria')}")
                parts.append("")
            if r.get("ask"):
                parts.append(f"### Ask")
                parts.append(f"> {r.get('ask')}")
                parts.append("")
            if r.get("prompt"):
                parts.append(f"### Prompt ({r.get('prompt_words')} words)")
                parts.append("```")
                parts.append(str(r.get("prompt")))
                parts.append("```")
                parts.append("")
            if r.get("response"):
                parts.append(f"### Response ({r.get('response_words')} words)")
                parts.append("")
                parts.append(str(r.get("response")))
                parts.append("")
            return "\\n".join(parts)
    return f"_Checkpoint `{cid}` not found in the {len(ROWS)}-row dataset._"


# ---------------------------------------------------------------------------
# Tab 3: Statistics
# ---------------------------------------------------------------------------

def _bar_chart(counter: collections.Counter, title: str, x_label: str):
    if not counter:
        return None
    items = counter.most_common()
    df = pd.DataFrame(items, columns=[x_label, "count"])
    fig = px.bar(df, x=x_label, y="count", title=title, text="count")
    fig.update_traces(textposition="outside")
    fig.update_layout(
        margin=dict(l=20, r=20, t=50, b=20),
        height=380,
    )
    return fig


def stats_review_lens():
    return _bar_chart(
        collections.Counter(r.get("review_lens") or "(empty)" for r in ROWS),
        "Reviews by review_lens",
        "review_lens",
    )


def stats_target_agent():
    return _bar_chart(
        collections.Counter(r.get("target") or "(empty)" for r in ROWS),
        "Reviews by target agent",
        "target",
    )


def stats_result():
    return _bar_chart(
        collections.Counter(r.get("result") or "(empty)" for r in ROWS),
        "Outcome distribution",
        "result",
    )


def stats_model():
    return _bar_chart(
        collections.Counter(r.get("model") or "(empty)" for r in ROWS),
        "Reviews by Claude model",
        "model",
    )


def stats_year_month():
    return _bar_chart(
        collections.Counter(r["year_month"] for r in ROWS),
        "Reviews by month",
        "year_month",
    )


def stats_summary_md() -> str:
    n = len(ROWS)
    avg_resp = sum(r["response_words"] for r in ROWS) / n if n else 0
    avg_prompt = sum(r["prompt_words"] for r in ROWS) / n if n else 0
    new_signal = sum(1 for r in ROWS if r.get("result") == "new_signal")
    no_new_signal = sum(1 for r in ROWS if r.get("result") == "no_new_signal")
    failed = sum(1 for r in ROWS if r.get("result") == "failed")
    opus = sum(1 for r in ROWS if r.get("model") == "opus")
    sonnet = sum(1 for r in ROWS if r.get("model") == "sonnet")
    return (
        f"### Quick stats\\n\\n"
        f"| metric | value |\\n"
        f"|---|---|\\n"
        f"| Total reviews | **{n}** |\\n"
        f"| Avg prompt length | {avg_prompt:.1f} words |\\n"
        f"| Avg response length | {avg_resp:.1f} words |\\n"
        f"| Result: new_signal | {new_signal} ({new_signal/n*100:.1f}%) |\\n"
        f"| Result: no_new_signal | {no_new_signal} ({no_new_signal/n*100:.1f}%) |\\n"
        f"| Result: failed | {failed} ({failed/n*100:.1f}%) |\\n"
        f"| Model: opus | {opus} |\\n"
        f"| Model: sonnet | {sonnet} |\\n"
    )


# ---------------------------------------------------------------------------
# Gradio app
# ---------------------------------------------------------------------------

INTRO_MD = f"""
# Cross-Agent Review Queue Explorer

Browse, filter, and inspect **{len(ROWS)} anonymized cross-agent code-review checkpoints**
from the [Neo Genesis](https://neogenesis.app) monorepo, captured between
`2026-04-08` and `2026-04-14` (Codex requesting reviews from Claude
`neo-reviewer` / `neo-architect` agents).

Each row is a real bounded review request with:
- explicit **owner_goal** + **owner_intent** + **constraints** + **success_criteria**
- a single **review_lens** (risk, regression, goal-fit, etc.)
- a Claude **model** (sonnet / opus) and **mode** (review / architecture)
- the resulting **outcome** (`new_signal` / `no_new_signal` / `failed`)

This is the first publicly released dataset of bounded multi-agent code-review
transcripts. Read the full schema in the
[dataset card]({{}}). Use this Explorer to navigate and aggregate.

- **Dataset**: [`{DATASET_ID}`](https://huggingface.co/datasets/{DATASET_ID})
- **License**: CC-BY-4.0 (data) | MIT (this Space's app code)
- **Operator**: Yesol Heo / Neo Genesis
""".format(f"https://huggingface.co/datasets/{DATASET_ID}")


with gr.Blocks(title="Cross-Agent Review Queue Explorer", theme=gr.themes.Soft()) as demo:
    gr.Markdown(INTRO_MD)

    with gr.Tab("Browse"):
        gr.Markdown(
            "Filter the queue by review lens, target agent, outcome, or month. "
            "Click any row's `id` (e.g. `ccr-20260408-121555`) and paste it into "
            "the **Detail** tab to see the full transcript."
        )
        with gr.Row():
            lens_dd = gr.Dropdown(
                choices=[ALL_FILTER] + REVIEW_LENSES,
                value=ALL_FILTER,
                label="review_lens",
            )
            target_dd = gr.Dropdown(
                choices=[ALL_FILTER] + TARGET_AGENTS,
                value=ALL_FILTER,
                label="target agent",
            )
            result_dd = gr.Dropdown(
                choices=[ALL_FILTER] + RESULTS,
                value=ALL_FILTER,
                label="result",
            )
            ym_dd = gr.Dropdown(
                choices=[ALL_FILTER] + YEAR_MONTHS,
                value=ALL_FILTER,
                label="year-month",
            )
        table = gr.DataFrame(
            value=filter_rows(ALL_FILTER, ALL_FILTER, ALL_FILTER, ALL_FILTER),
            label=f"{len(ROWS)} reviews",
            wrap=True,
            interactive=False,
        )
        for c in (lens_dd, target_dd, result_dd, ym_dd):
            c.change(
                filter_rows,
                inputs=[lens_dd, target_dd, result_dd, ym_dd],
                outputs=table,
            )

    with gr.Tab("Detail"):
        gr.Markdown(
            "Paste a checkpoint id (e.g. `ccr-20260408-121555`) to see the full "
            "anonymized transcript: owner goal, constraints, prompt, and Claude's response."
        )
        with gr.Row():
            cid_in = gr.Textbox(
                label="Checkpoint id",
                placeholder="ccr-20260408-121555",
                value=ROWS[0]["id"] if ROWS else "",
                scale=4,
            )
            view_btn = gr.Button("Show review", variant="primary", scale=1)
        detail_md = gr.Markdown(
            review_detail(ROWS[0]["id"]) if ROWS else "_dataset is empty_"
        )
        view_btn.click(review_detail, inputs=cid_in, outputs=detail_md)
        cid_in.submit(review_detail, inputs=cid_in, outputs=detail_md)

    with gr.Tab("Statistics"):
        gr.Markdown(stats_summary_md())
        with gr.Row():
            gr.Plot(value=stats_review_lens())
            gr.Plot(value=stats_target_agent())
        with gr.Row():
            gr.Plot(value=stats_result())
            gr.Plot(value=stats_model())
        gr.Plot(value=stats_year_month())

    with gr.Tab("About"):
        gr.Markdown(
            f"""
### What is this?

A frozen, anonymized snapshot of {len(ROWS)} cross-agent code-review checkpoints
from the live SSOT (`.agent/shared-brain/cross-agent-review.md`) of
[Neo Genesis](https://neogenesis.app) — a 1-person AI-native operator running
**11 production AI business units**.

### Anonymization (6-tier)

The published dataset replaces:
- absolute file paths -> repo-relative paths
- internal hostnames / IPs -> tier names
- live API keys / tokens -> `[REDACTED]`
- personal contact info -> tier role names
- internal Telegram chat ids / Supabase project ids -> stable hashes
- secret-bearing scopes -> `[redacted-scope]`

while preserving the **structure of bounded reviews**: every transcript still
shows the owner_goal, the constraints, the review_lens, and the actual
prompt / response pair so you can study *how* the bounded-review protocol works.

### Why publish this?

Most multi-agent papers report aggregate metrics. The actual *transcripts* of
real bounded reviews — with explicit owner goals and review lenses — are rarely
public. This dataset is meant to be a working example for:

- agent-orchestration researchers studying handoff prompts
- code-review automation builders calibrating their own review schemas
- AI-governance teams evaluating bounded-review protocols against ad-hoc chats

### Resources

- **Dataset**: <https://huggingface.co/datasets/{DATASET_ID}>
- **Neo Genesis homepage**: <https://neogenesis.app>
- **Operator**: <https://huggingface.co/neogenesislab>
- **Wikidata**: [Q139569680](https://www.wikidata.org/wiki/Q139569680)

### Cite

```bibtex
@misc{{neogenesis_cross_agent_review_queue_2026,
  title  = {{Cross-Agent Code Review Queue: 37 anonymized Codex<->Claude bounded review checkpoints}},
  author = {{Heo, Yesol}},
  year   = {{2026}},
  url    = {{https://huggingface.co/datasets/{DATASET_ID}}}
}}
```
"""
        )


if __name__ == "__main__":
    demo.queue().launch()
'''

REQUIREMENTS_TXT = """gradio==5.9.1
datasets>=2.21,<4
pandas>=2.0
plotly>=5.20
"""

GITATTRIBUTES = "* text=auto eol=lf\n"


def build_space_readme() -> str:
    yaml_front = """---
title: Cross-Agent Review Queue Explorer
emoji: 🤝
colorFrom: purple
colorTo: blue
sdk: gradio
sdk_version: 5.9.1
app_file: app.py
pinned: false
license: mit
short_description: Browse 37 Codex-Claude review transcripts.
tags:
- multi-agent
- agent-orchestration
- code-review
- claude
- codex
- governance
datasets:
- neogenesislab/cross-agent-review-queue-2026
---
"""
    body = """
# Cross-Agent Review Queue Explorer

A Gradio UI to browse, filter, and inspect 37 real bounded code-review checkpoints
exchanged between Codex and Claude (`neo-reviewer` / `neo-architect`) inside the
[Neo Genesis](https://neogenesis.app) monorepo, captured between 2026-04-08 and 2026-04-14.

Data source: [`neogenesislab/cross-agent-review-queue-2026`](https://huggingface.co/datasets/neogenesislab/cross-agent-review-queue-2026)

## Tabs
1. **Browse** — paginated table with 4 filters (review_lens, target agent, outcome, year-month).
2. **Detail** — full anonymized transcript for any `ccr-YYYYMMDD-HHMMSS` checkpoint id.
3. **Statistics** — distribution charts for review_lens, target, outcome, model, month + summary table.
4. **About** — anonymization notes, citation, links to dataset card and Neo Genesis.

## Stack
- `gradio==5.9.1` (Python 3.13 compatible)
- `datasets` (loads the parent dataset at cold start, so dataset updates auto-reflect)
- `plotly` (statistics charts)
- `pandas`

## License
- App code: **MIT** (this Space)
- Data: **CC-BY-4.0** (parent dataset)

## Cite
```bibtex
@misc{neogenesis_cross_agent_review_queue_2026,
  title  = {Cross-Agent Code Review Queue: 37 anonymized Codex<->Claude bounded review checkpoints},
  author = {Heo, Yesol},
  year   = {2026},
  url    = {https://huggingface.co/datasets/neogenesislab/cross-agent-review-queue-2026}
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

    # Quick sanity check that the parent dataset is reachable.
    try:
        from datasets import load_dataset
        ds = load_dataset(DATASET_ID, DATASET_CONFIG, split="train")
        print(f"OK: parent dataset loaded ({len(ds)} rows, columns={ds.column_names})")
    except Exception as exc:
        print(f"WARN: could not pre-validate parent dataset: {exc}")

    readme = build_space_readme()
    print(f"prepared README.md ({len(readme):,} bytes)")
    print(f"prepared app.py ({len(APP_PY):,} bytes)")
    print(f"prepared requirements.txt ({len(REQUIREMENTS_TXT):,} bytes)")
    print(f"prepared .gitattributes ({len(GITATTRIBUTES):,} bytes)")

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

    # Best-effort runtime status check
    try:
        info = api.space_info(repo_id=SPACE_ID)
        runtime = getattr(info, "runtime", None)
        stage = getattr(runtime, "stage", None) if runtime else None
        hardware = getattr(runtime, "hardware", None) if runtime else None
        print(f"runtime.stage = {stage}")
        print(f"runtime.hardware = {hardware}")
    except Exception as exc:
        print(f"(non-fatal) space_info() not yet available: {exc}")

    # Live HTTP HEAD verification
    try:
        import urllib.request
        req = urllib.request.Request(url, method="HEAD")
        with urllib.request.urlopen(req, timeout=15) as resp:
            print(f"HEAD {url} -> {resp.status}")
    except Exception as exc:
        print(f"(non-fatal) HEAD check failed: {exc}")

    # Poll runtime stage until RUNNING (max 5 attempts, 30s each)
    print("polling runtime stage (max 5 x 30s)...")
    for attempt in range(1, 6):
        time.sleep(30)
        try:
            info = api.space_info(repo_id=SPACE_ID)
            runtime = getattr(info, "runtime", None)
            stage = getattr(runtime, "stage", None) if runtime else None
            print(f"  attempt {attempt}: runtime.stage = {stage}")
            if stage == "RUNNING":
                print("Space is RUNNING")
                break
            if stage in ("BUILD_ERROR", "RUNTIME_ERROR", "CONFIG_ERROR"):
                print(f"BUILD/RUNTIME ERROR detected at attempt {attempt}: stage={stage}")
                break
        except Exception as exc:
            print(f"  attempt {attempt}: space_info error: {exc}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
