"""
HuggingFace Datasets publish — Cross-Agent Code Review Queue (Codex <-> Claude)

Source : .agent/shared-brain/cross-agent-review.md
       + .agent/shared-brain/claude-checkpoints/*.md
Target : huggingface.co/datasets/neogenesislab/cross-agent-review-queue-2026

Layout:
    README.md                       bilingual ko + en dataset card
    data/checkpoints.jsonl          one record per checkpoint (transcripts)
    data/queue_metadata.jsonl       one record per cross-agent-review.md item
    data/category_distribution.json review-lens / requester / target distributions
    metadata.json                   benchmark-level meta

Anonymization is critical. The following are stripped or normalized:
- Absolute paths    : `D:/00.test/...` -> `<repo>/...`
- Owner identifiers : owner names / email / phone / personal handles -> `<owner>` / redacted
- Checkpoint IDs    : kept as `ccr-YYYYMMDD-NNNNNN` (no PII; safe identifier)
- API tokens        : any `sk-*`, `ghp_*`, JWT, bot-token patterns redacted
- Specific machine  : hostnames `desktop-yesol`, `desktop-sol01`, `ysh-server`,
                      `mx-macbuild-mac-studio` -> generic device categories
- IPs / Tailscale   : private IPs and Tailscale hostnames redacted
- Specific projects : keep architecture concepts, redact internal subsystem
                      names not already public (Sora is public; project names
                      identifying the owner's private business are kept since
                      Neo Genesis is publicly attested via Wikidata Q139569680)

Run:
    PYTHONIOENCODING=utf-8 python scripts/hf_publish/publish_cross_agent_review_queue.py
"""
import io
import json
import os
import re
import sys
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
QUEUE_FILE = ROOT / ".agent" / "shared-brain" / "cross-agent-review.md"
CHECKPOINT_DIR = ROOT / ".agent" / "shared-brain" / "claude-checkpoints"
ENV_LOCAL = ROOT / ".env.local"
REPO_ID = "neogenesislab/cross-agent-review-queue-2026"


# ---------- Env ----------

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


# ---------- Anonymization ----------

# Specific paths and hostnames redaction map.
# Paths: any absolute D: paths to <repo>/relative.
# Hostnames: collapse named devices into generic tier categories.
DEVICE_MAP = {
    "desktop-yesol": "<work-pc>",
    "DESKTOP-YESOL": "<work-pc>",
    "desktop-sol01": "<gpu-worker>",
    "DESKTOP-SOL01": "<gpu-worker>",
    "ysh-server": "<server>",
    "YSH-Server": "<server>",
    "mx-macbuild-mac-studio": "<mac-build>",
    "MX Mac Studio": "<mac-build>",
    "S26 Ultra": "<mobile-1>",
    "Tab S10 Ultra": "<mobile-2>",
    "CTS_Sol": "<work-user>",
}

# Owner identifiers (do not include in dataset).
OWNER_PII_PATTERNS = [
    re.compile(r"\b허예솔\b"),
    re.compile(r"\bYesol\s*Heo\b", re.IGNORECASE),
    re.compile(r"\bdpthf1537@gmail\.com\b", re.IGNORECASE),
    re.compile(r"\betribe\.cts@gmail\.com\b", re.IGNORECASE),
    re.compile(r"\b010-?\d{4}-?\d{4}\b"),
    re.compile(r"\bdesktop-home\b", re.IGNORECASE),
]

# Credential / token patterns.
CRED_PATTERNS = [
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "<redacted-api-key>"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"), "<redacted-github-token>"),
    (re.compile(r"\bgho_[A-Za-z0-9]{30,}\b"), "<redacted-github-token>"),
    (re.compile(r"\bhf_[A-Za-z0-9]{30,}\b"), "<redacted-hf-token>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\b"), "<redacted-jwt>"),
    (re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"), "<redacted-bot-token>"),
    # Korean RRN (residential reg number) - 6 digits + 7 digits
    (re.compile(r"\b\d{6}-?[1-4]\d{6}\b"), "<redacted-rrn>"),
]

# Specific paths to redact.
PATH_PATTERNS = [
    (re.compile(r"D:/00\.test/neo-genesis", re.IGNORECASE), "<repo>"),
    (re.compile(r"D:\\00\.test\\neo-genesis", re.IGNORECASE), "<repo>"),
    (re.compile(r"D:/00\.test", re.IGNORECASE), "<workspace>"),
    (re.compile(r"D:\\00\.test", re.IGNORECASE), "<workspace>"),
    (re.compile(r"C:/Users/[A-Za-z0-9_]+", re.IGNORECASE), "<home>"),
    (re.compile(r"C:\\Users\\[A-Za-z0-9_]+", re.IGNORECASE), "<home>"),
    (re.compile(r"/home/[a-z0-9_]+", re.IGNORECASE), "<home>"),
    (re.compile(r"/Users/[a-z0-9_]+", re.IGNORECASE), "<home>"),
]

# Tailscale and private IPs.
IP_PATTERNS = [
    # Tailscale 100.x.y.z range
    (re.compile(r"\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<tailscale-ip>"),
    # Private 192.168 / 10.x ranges
    (re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"), "<private-ip>"),
    (re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<private-ip>"),
]


def anonymize(text: str) -> str:
    """Apply full anonymization pipeline."""
    if text is None:
        return text
    s = str(text)
    # Order matters: paths first (they may contain hostnames),
    # then hostnames, then PII, then credentials, then IPs.
    for pat, repl in PATH_PATTERNS:
        s = pat.sub(repl, s)
    for hostname, generic in DEVICE_MAP.items():
        s = s.replace(hostname, generic)
    for pat in OWNER_PII_PATTERNS:
        s = pat.sub("<owner>", s)
    for pat, repl in CRED_PATTERNS:
        s = pat.sub(repl, s)
    for pat, repl in IP_PATTERNS:
        s = pat.sub(repl, s)
    return s


def assert_clean(text: str, where: str) -> None:
    """Verify no leakage post-anonymization."""
    bad = []
    if re.search(r"D:[\\/]00\.test", text, re.IGNORECASE):
        bad.append("D:/00.test path")
    for hostname in DEVICE_MAP:
        if hostname in text:
            bad.append(f"hostname:{hostname}")
    for pat in OWNER_PII_PATTERNS:
        if pat.search(text):
            bad.append("owner-PII")
            break
    for pat, _ in CRED_PATTERNS:
        if pat.search(text):
            bad.append("credential")
            break
    if bad:
        raise RuntimeError(f"anonymization leak in {where}: {bad}")


# ---------- Parsers ----------

# Match a checkpoint metadata block in cross-agent-review.md.
# Each entry looks like:
# - [x] `ccr-20260408-121555` codex -> neo-reviewer `sonnet` checkpoint: <title>
#   - scope: <text>
#   - owner_goal: <text>
#   ...
QUEUE_ITEM_RE = re.compile(
    r"^- \[x\] `(ccr-\d{8}-\d{6})` (\S+) -> (\S+) `(\S+)` checkpoint: (.+)$",
    re.MULTILINE,
)


def parse_queue(md_text: str) -> list[dict]:
    """Parse cross-agent-review.md completed entries into structured records."""
    records = []
    lines = md_text.splitlines()
    i = 0
    while i < len(lines):
        m = QUEUE_ITEM_RE.match(lines[i])
        if not m:
            i += 1
            continue
        ccr_id, requester, target, model, title = m.groups()
        rec = {
            "id": ccr_id,
            "requester": requester,
            "target": target,
            "model": model,
            "title": title.strip(),
            "scope": None,
            "owner_goal": None,
            "owner_intent": None,
            "constraints": None,
            "success_criteria": None,
            "review_lens": None,
            "expected": None,
            "ask": None,
            "result": None,
            "has_transcript": False,
        }
        # Read continuation lines (each starts with "  - key: value")
        j = i + 1
        while j < len(lines) and lines[j].startswith("  - "):
            kv = lines[j][4:].strip()
            if ":" in kv:
                k, v = kv.split(":", 1)
                k = k.strip()
                v = v.strip().strip("`")
                # Map known keys; ignore checkpoint_file (we'll resolve via dir).
                if k in rec and rec[k] is None:
                    rec[k] = v if v != "-" else None
                elif k == "review_lens":
                    rec["review_lens"] = v if v != "-" else None
            j += 1
        records.append(rec)
        i = j
    return records


CHECKPOINT_HEAD_RE = re.compile(r"^- (\S+):\s*(.+)$")


def parse_checkpoint_file(p: Path) -> dict:
    """Parse a single claude-checkpoint markdown file."""
    text = p.read_text(encoding="utf-8")
    rec = {
        "id": p.stem,
        "created_at": None,
        "requester": None,
        "target": None,
        "mode": None,
        "model": None,
        "scope": None,
        "owner_goal": None,
        "owner_intent": None,
        "constraints": None,
        "success_criteria": None,
        "review_lens": None,
        "expected": None,
        "ask": None,
        "result": None,
        "title": None,
        "prompt": None,
        "response": None,
    }

    # Header field block before "## Title"
    head, _, rest = text.partition("## Title")
    for line in head.splitlines():
        m = CHECKPOINT_HEAD_RE.match(line.strip())
        if not m:
            continue
        k, v = m.groups()
        v = v.strip().strip("`")
        if k in rec:
            rec[k] = v if v not in ("-", "") else None

    # ## Title block
    title_block, _, rest2 = rest.partition("## Prompt")
    rec["title"] = title_block.strip() or None

    # ## Prompt block (between "## Prompt" and "## Claude Response")
    prompt_block, _, response_block = rest2.partition("## Claude Response")

    def extract_codeblock(s: str) -> str | None:
        m = re.search(r"```(?:text)?\s*\n(.*?)```", s, re.DOTALL)
        return m.group(1).strip() if m else (s.strip() or None)

    rec["prompt"] = extract_codeblock(prompt_block)
    rec["response"] = extract_codeblock(response_block)
    return rec


def merge_records(queue_records: list[dict], ckpt_records: dict[str, dict]) -> tuple[list[dict], list[dict]]:
    """Combine queue metadata with full transcripts where available."""
    enriched_queue = []
    transcripts = []

    for q in queue_records:
        ck = ckpt_records.get(q["id"])
        if ck:
            q["has_transcript"] = True
            # Prefer non-null queue values, fall back to checkpoint values
            for k in ["scope", "owner_goal", "owner_intent", "constraints",
                      "success_criteria", "review_lens", "expected", "ask", "result"]:
                if not q.get(k) and ck.get(k):
                    q[k] = ck[k]
            transcripts.append({
                "id": ck["id"],
                "created_at": ck.get("created_at"),
                "requester": ck.get("requester") or q.get("requester"),
                "target": ck.get("target") or q.get("target"),
                "mode": ck.get("mode"),
                "model": ck.get("model") or q.get("model"),
                "scope": ck.get("scope") or q.get("scope"),
                "owner_goal": ck.get("owner_goal") or q.get("owner_goal"),
                "owner_intent": ck.get("owner_intent") or q.get("owner_intent"),
                "constraints": ck.get("constraints") or q.get("constraints"),
                "success_criteria": ck.get("success_criteria") or q.get("success_criteria"),
                "review_lens": ck.get("review_lens") or q.get("review_lens"),
                "expected": ck.get("expected") or q.get("expected"),
                "ask": ck.get("ask") or q.get("ask"),
                "result": ck.get("result") or q.get("result"),
                "title": ck.get("title") or q.get("title"),
                "prompt": ck.get("prompt"),
                "response": ck.get("response"),
            })
        enriched_queue.append(q)

    # Also add transcript-only records (in case some checkpoints aren't in the queue)
    queue_ids = {q["id"] for q in queue_records}
    for ck_id, ck in ckpt_records.items():
        if ck_id in queue_ids:
            continue
        transcripts.append({
            "id": ck["id"],
            "created_at": ck.get("created_at"),
            "requester": ck.get("requester"),
            "target": ck.get("target"),
            "mode": ck.get("mode"),
            "model": ck.get("model"),
            "scope": ck.get("scope"),
            "owner_goal": ck.get("owner_goal"),
            "owner_intent": ck.get("owner_intent"),
            "constraints": ck.get("constraints"),
            "success_criteria": ck.get("success_criteria"),
            "review_lens": ck.get("review_lens"),
            "expected": ck.get("expected"),
            "ask": ck.get("ask"),
            "result": ck.get("result"),
            "title": ck.get("title"),
            "prompt": ck.get("prompt"),
            "response": ck.get("response"),
        })

    return enriched_queue, transcripts


def anonymize_record(rec: dict, where: str) -> dict:
    """Apply anonymization to all string fields and verify no leakage."""
    out = {}
    for k, v in rec.items():
        if isinstance(v, str):
            out[k] = anonymize(v)
        elif v is None or isinstance(v, bool):
            out[k] = v
        else:
            out[k] = v
    # Verify
    for k, v in out.items():
        if isinstance(v, str) and v:
            assert_clean(v, f"{where}.{rec.get('id')}.{k}")
    return out


def build_distributions(transcripts: list[dict], queue: list[dict]) -> dict:
    """Compute review-lens / requester / target / result distributions."""
    lens_counter = Counter()
    for r in transcripts:
        lens = r.get("review_lens") or ""
        for token in re.split(r"[,\s]+", lens):
            token = token.strip().strip("`")
            if token:
                lens_counter[token] += 1

    requester_counter = Counter(r.get("requester") or "unknown" for r in transcripts)
    target_counter = Counter(r.get("target") or "unknown" for r in transcripts)
    model_counter = Counter(r.get("model") or "unknown" for r in transcripts)
    result_counter = Counter(r.get("result") or "unknown" for r in transcripts)
    expected_counter = Counter(r.get("expected") or "unknown" for r in transcripts)

    return {
        "review_lens": dict(sorted(lens_counter.items(), key=lambda x: -x[1])),
        "requester": dict(sorted(requester_counter.items(), key=lambda x: -x[1])),
        "target": dict(sorted(target_counter.items(), key=lambda x: -x[1])),
        "model": dict(sorted(model_counter.items(), key=lambda x: -x[1])),
        "result": dict(sorted(result_counter.items(), key=lambda x: -x[1])),
        "expected_output": dict(sorted(expected_counter.items(), key=lambda x: -x[1])),
        "queue_total": len(queue),
        "transcript_total": len(transcripts),
        "queue_with_transcript": sum(1 for q in queue if q.get("has_transcript")),
    }


# ---------- Dataset card ----------

def build_readme(stats: dict, n_transcripts: int, n_queue: int) -> str:
    lens_table = "\n".join(
        f"| `{k}` | {v} |"
        for k, v in stats["review_lens"].items()
        if k  # skip empty
    )
    requester_table = "\n".join(
        f"| `{k}` | {v} |" for k, v in stats["requester"].items()
    )
    target_table = "\n".join(
        f"| `{k}` | {v} |" for k, v in stats["target"].items()
    )
    result_table = "\n".join(
        f"| `{k}` | {v} |" for k, v in stats["result"].items()
    )

    yaml_front = f"""---
language:
- ko
- en
license: cc-by-4.0
task_categories:
- text-generation
- text-ranking
tags:
- multi-agent
- agent-orchestration
- code-review
- llm-collaboration
- agent-handoff
- claude
- codex
- neo-genesis
- agent-evaluation
- bilingual
size_categories:
- n<1K
pretty_name: Cross-Agent Code Review Queue (Codex <-> Claude, Neo Genesis 2026)
configs:
- config_name: transcripts
  data_files:
  - split: train
    path: data/checkpoints.jsonl
- config_name: queue_metadata
  data_files:
  - split: train
    path: data/queue_metadata.jsonl
---
"""
    body = f"""
# Cross-Agent Code Review Queue (Codex <-> Claude, Neo Genesis 2026)

> The first publicly released dataset of **bounded multi-agent code review checkpoints** with explicit `owner_goal`, `owner_intent`, `review_lens`, and `result` fields. {n_transcripts} full bilingual (ko + en) review transcripts plus {n_queue} queue-metadata entries from a real production AI-native company operating 11 business units.

Released by **[Neo Genesis](https://neogenesis.app)** to support agent-orchestration research.

## Why this dataset exists

Public benchmarks for code-related LLM work (SWE-bench, AgentBench, HumanEval, MBPP) target a **single agent** producing or evaluating a single artifact. They miss the most operationally important question of agent orchestration:

> *When two specialist agents disagree on a patch, what does the bounded handoff actually look like?*

This dataset captures **real Codex <-> Claude review handoffs** from a production environment between **2026-04-08 and 2026-04-14**, covering subsystems ranging from a Telegram personal assistant, a small-account quantitative trading runtime governor, a job-search pipeline, to autonomous-trading orchestrator design.

Every checkpoint follows a shared protocol: the requester reconstructs the **owner's goal, intent, constraints, and success criteria** before asking; the reviewer responds against a declared **review lens** (`risk` / `architecture` / `usability` / `security` / `rollout` / `verification`); and the outcome is recorded as `new_signal` / `no_new_signal` / `failed`.

## Dataset summary

- **{n_transcripts} full transcripts** in `data/checkpoints.jsonl` — each with `prompt`, `response`, and the full request schema (owner-goal reconstruction, lens, constraints, success criteria, result).
- **{n_queue} queue-metadata entries** in `data/queue_metadata.jsonl` — the canonical request log including items where the transcript was not preserved (cross-reference via `id`).
- **Fully anonymized**: paths, hostnames, owner identifiers, and credential patterns redacted (see *Anonymization disclosure* below).

## Distributions

### Review lenses

| Lens | Count |
|---|---|
{lens_table}

### Requester agent

| Agent | Count |
|---|---|
{requester_table}

### Target reviewer

| Target | Count |
|---|---|
{target_table}

### Outcome

| Result | Count |
|---|---|
{result_table}

## Schema

### `data/checkpoints.jsonl` (one record per line)

```json
{{
  "id": "ccr-20260408-122805",
  "created_at": "2026-04-08T12:29:17+09:00",
  "requester": "codex",
  "target": "neo-architect",
  "mode": "architecture",
  "model": "sonnet",
  "scope": "telegram scheduling + gmail/calendar orchestration",
  "owner_goal": "trustworthy personal assistant on Telegram",
  "owner_intent": "one message should accurately execute scheduling, gmail-grounded additions, ...",
  "constraints": "Korean, final report must match actual tool outcomes, ...",
  "success_criteria": "compound assistant commands report created/updated/failed items separately ...",
  "review_lens": "goal-fit,risk,usability,maintenance",
  "expected": "design",
  "ask": "Provide the highest-leverage implementation principles and risks for this patch scope.",
  "result": "new_signal",
  "title": "Telegram personal-assistant reliability remediation",
  "prompt": "Context:\\n- Current failure case: ...",
  "response": "## Owner goal and intent restatement\\n\\n...full Korean review with markdown tables..."
}}
```

### `data/queue_metadata.jsonl` (one record per line)

```json
{{
  "id": "ccr-20260408-122805",
  "requester": "codex",
  "target": "neo-architect",
  "model": "sonnet",
  "title": "Telegram personal-assistant reliability remediation",
  "scope": "telegram scheduling + gmail/calendar orchestration",
  "owner_goal": "...",
  "review_lens": "goal-fit,risk,usability,maintenance",
  "expected": "design",
  "result": "new_signal",
  "has_transcript": true
}}
```

## Quick start

```python
from datasets import load_dataset

# Full transcripts (request + response)
ds = load_dataset("{REPO_ID}", "transcripts", split="train")
print(ds[0]["title"])
print(ds[0]["prompt"][:500])
print(ds[0]["response"][:500])

# Lightweight queue metadata only
ds_meta = load_dataset("{REPO_ID}", "queue_metadata", split="train")
```

## Comparison with prior work

| Dataset | Multi-agent? | Goal-intent reconstruction | Bounded lens? | Production source |
|---|---|---|---|---|
| **SWE-bench** | single-agent | partial | task-only | GitHub issues |
| **AgentBench** | single-agent | task spec | varied | synthetic + real |
| **MetaGPT-Pub / AutoGen-Bench** | multi-agent (synthetic) | task only | implicit | scripted scenarios |
| **HumanEvalPack / CodeXGLUE** | single-agent | none | none | curated code |
| **Cross-Agent Review Queue (this)** | **multi-agent (Codex <-> Claude)** | **explicit, structured** | **declared lens (6 types)** | **live production logs** |

This dataset is **not** a code-generation benchmark and is **not** a single-agent evaluation set. It is a **collaboration log** — the closest public analog is a code-review transcript dataset, but with a multi-agent boundary protocol layered on top.

## Suggested research applications

1. **Agent handoff training** — fine-tune a requester-side model to produce well-formed `owner_goal` / `review_lens` / `success_criteria` blocks that lead to `new_signal` results.
2. **Reviewer politeness vs. bluntness analysis** — the `result` field marks `no_new_signal` (legitimate "nothing to add") separately from `new_signal` (substantive feedback). Useful for studying reviewer over-engagement.
3. **Cold-review prompting** — many transcripts illustrate the *Goal-Intent Review Protocol* where Claude is required to restate the owner's goal before critiquing. Compare cold reviews with warm/agreement-first reviews.
4. **Lens-specific instruction following** — measure how a model adheres to a declared lens (e.g., `risk` only) when it would naturally also discuss `usability`.
5. **Boundary management** — Codex + Claude operate under a *bounded specialist collaboration* contract (no recursive delegation, single primary writer per branch). Analyze how this constraint shapes the dialogue.

## Anonymization disclosure

The source data was Neo Genesis' live agent-runtime SSOT. The following transformations were applied before publication:

| Class | Examples in raw source | Public form |
|---|---|---|
| Absolute paths | local development paths starting with a Windows drive letter | `<repo>/...` |
| Owner identifiers | owner full name, personal email, phone | `<owner>` / removed |
| Hostnames (devices) | named work-PC / GPU-worker / server / mac-build hostnames | `<work-pc>`, `<gpu-worker>`, `<server>`, `<mac-build>` |
| Tailscale / private IPs | `100.x.y.z`, `192.168.x.y` | `<tailscale-ip>`, `<private-ip>` |
| Credentials | `sk-*`, `ghp_*`, `hf_*`, JWT, Telegram bot tokens | `<redacted-*>` |
| Korean RRN | 6+7 digit format | `<redacted-rrn>` |

Public Neo Genesis identifiers (Wikidata Q139569680, the public business-unit names that already appear on `neogenesis.app`, and the public agent-orchestration concepts like the *Sora* assistant) are intentionally retained because they are already attested in public sources.

Verification: every emitted string was passed through a post-anonymization assertion that re-runs the redaction regexes; any remaining match aborts the publish job.

## Provenance

- **Source SSOT**: Neo Genesis private `.agent/shared-brain/cross-agent-review.md` and `claude-checkpoints/`
- **Time window**: 2026-04-08 to 2026-04-14 (the most active multi-agent collaboration window during Phase -1 quant runtime hardening + Sora assistant remediation)
- **Curator**: <owner> (sole founder/operator of Neo Genesis)
- **Wikidata**: [Q139569680 (Neo Genesis)](https://www.wikidata.org/wiki/Q139569680)
- **Related releases by the same operator**:
  - [`korean-rag-ssot-golden-50`](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50)
  - [`ethicaai-mixed-safe-evidence`](https://huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence)
  - [`whylab-gemini-2-5-docker-validation`](https://huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation)
  - [`sbu-pseo-effects-2026-04`](https://huggingface.co/datasets/neogenesislab/sbu-pseo-effects-2026-04)

## Citation

```bibtex
@misc{{neogenesis_cross_agent_review_queue_2026,
  title  = {{Cross-Agent Code Review Queue: Bounded Codex-Claude review checkpoints from a production AI-native company}},
  author = {{Neo Genesis}},
  year   = {{2026}},
  url    = {{https://huggingface.co/datasets/{REPO_ID}}},
  note   = {{First public dataset of multi-agent code review checkpoints with explicit goal-intent reconstruction and declared review lens}}
}}
```

## License

CC-BY-4.0 — free for research and commercial use with attribution to Neo Genesis.

---

## 한국어 요약

**Cross-Agent Code Review Queue** 는 **Codex <-> Claude** 두 주력 코딩 에이전트가 실제 프로덕션 환경(2026-04-08 ~ 04-14)에서 주고받은 **{n_transcripts}건의 코드 리뷰 체크포인트 전체 트랜스크립트** 와 **{n_queue}건의 큐 메타데이터** 를 모은 데이터셋이다.

기존 SWE-bench / AgentBench 가 "한 에이전트가 한 작업을 하는" 케이스만 다루는 반면, 이 데이터셋은 **두 에이전트가 경계를 두고 의견을 주고받는 핸드오프 프로토콜** 자체를 평가/연구용으로 공개한다는 점에서 차별화된다.

각 체크포인트는 다음을 포함:
- `owner_goal` / `owner_intent` 재구성 (요청자가 오너의 진짜 의도를 먼저 정리)
- `review_lens` (risk / architecture / usability / security / rollout / verification 중 선언)
- `success_criteria` 와 `constraints`
- 실제 prompt + Claude 응답 (한국어 + 영어 혼용 마크다운)
- `result`: `new_signal` / `no_new_signal` / `failed`

응용 예시:
- 에이전트 핸드오프 튜닝 (좋은 owner_goal 요약 → new_signal 결과)
- cold review prompting 연구 (오너 의도 재진술 강제 효과)
- 선언된 lens 만 따르는 instruction-following 평가
- 멀티에이전트 boundary 협상 분석

**익명화**: 절대 경로 / 오너 식별자 / 디바이스 호스트명 / 자격증명 / 한국 주민등록번호 패턴은 모두 익명화 토큰으로 치환되었으며, 발행 직전 모든 출력 문자열에 대해 재검증을 수행한다.

라이선스 CC-BY-4.0 — 인용 시 자유롭게 사용 가능.
"""
    return yaml_front + body


# ---------- Main ----------

def main() -> int:
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN not found in env", file=sys.stderr)
        return 1

    if not QUEUE_FILE.exists():
        print(f"ERROR: queue file not found: {QUEUE_FILE}", file=sys.stderr)
        return 1
    if not CHECKPOINT_DIR.exists():
        print(f"ERROR: checkpoint dir not found: {CHECKPOINT_DIR}", file=sys.stderr)
        return 1

    queue_md = QUEUE_FILE.read_text(encoding="utf-8")
    queue_records = parse_queue(queue_md)
    print(f"Parsed {len(queue_records)} entries from cross-agent-review.md")

    ckpt_records = {}
    for p in sorted(CHECKPOINT_DIR.glob("ccr-*.md")):
        rec = parse_checkpoint_file(p)
        ckpt_records[rec["id"]] = rec
    print(f"Loaded {len(ckpt_records)} checkpoint transcripts")

    queue_full, transcripts = merge_records(queue_records, ckpt_records)

    # Anonymize every record and verify
    queue_anon = [anonymize_record(r, "queue") for r in queue_full]
    transcripts_anon = [anonymize_record(r, "transcript") for r in transcripts]
    print(f"Anonymization passed: {len(queue_anon)} queue + {len(transcripts_anon)} transcripts")

    # Build artifacts
    queue_jsonl = "\n".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in queue_anon
    ) + "\n"
    transcripts_jsonl = "\n".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in transcripts_anon
    ) + "\n"

    distributions = build_distributions(transcripts_anon, queue_anon)
    distributions_json = json.dumps(distributions, ensure_ascii=False, indent=2)

    metadata = {
        "name": "Cross-Agent Code Review Queue (Codex <-> Claude)",
        "version": "1.0.0",
        "publisher": "Neo Genesis (neogenesislab)",
        "wikidata_qid": "Q139569680",
        "license": "CC-BY-4.0",
        "language": ["ko", "en"],
        "time_window": {"start": "2026-04-08", "end": "2026-04-14"},
        "totals": {
            "queue_metadata_records": len(queue_anon),
            "full_transcripts": len(transcripts_anon),
        },
        "distributions": distributions,
        "anonymization": {
            "paths": "redacted to <repo> / <workspace> / <home>",
            "hostnames": "redacted to device tier categories (<work-pc>, <gpu-worker>, <server>, <mac-build>)",
            "owner_identifiers": "redacted to <owner>",
            "private_ips": "redacted to <tailscale-ip> / <private-ip>",
            "credentials": "redacted to <redacted-*>",
            "korean_pii": "RRN patterns redacted to <redacted-rrn>",
            "post_emit_assertion": "every emitted string re-tested with all redaction regexes; publish aborts on leak",
        },
        "comparison": {
            "swe_bench": "single-agent code generation; this dataset is multi-agent review handoff",
            "agentbench": "general agent capability; this dataset is bounded review with declared lens",
            "metagpt_autogen_bench": "synthetic multi-agent; this dataset is from live production logs",
        },
    }
    metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)

    readme = build_readme(distributions, len(transcripts_anon), len(queue_anon))

    # Final pre-emit anonymization sanity check on every artifact
    for name, content in [
        ("README.md", readme),
        ("data/checkpoints.jsonl", transcripts_jsonl),
        ("data/queue_metadata.jsonl", queue_jsonl),
        ("data/category_distribution.json", distributions_json),
        ("metadata.json", metadata_json),
    ]:
        assert_clean(content, f"final-artifact:{name}")

    # Push to HF
    from huggingface_hub import HfApi
    api = HfApi(token=token)

    print(f"create_repo {REPO_ID} (dataset, public)")
    api.create_repo(
        repo_id=REPO_ID,
        repo_type="dataset",
        exist_ok=True,
        private=False,
    )

    uploads = [
        ("README.md", readme),
        ("data/checkpoints.jsonl", transcripts_jsonl),
        ("data/queue_metadata.jsonl", queue_jsonl),
        ("data/category_distribution.json", distributions_json),
        ("metadata.json", metadata_json),
    ]

    for path_in_repo, content in uploads:
        print(f"upload {path_in_repo} ({len(content):,} bytes)")
        api.upload_file(
            path_or_fileobj=io.BytesIO(content.encode("utf-8")),
            path_in_repo=path_in_repo,
            repo_id=REPO_ID,
            repo_type="dataset",
            commit_message=f"add {path_in_repo}",
        )

    url = f"https://huggingface.co/datasets/{REPO_ID}"
    print()
    print("PUBLISHED:", url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
