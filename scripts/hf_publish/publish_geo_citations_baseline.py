"""
HuggingFace Datasets publish — Korean LLM Citation Baseline (GEO/LLMO Measurement)

Source : scripts/geo_measure/citations.sqlite3
       + scripts/geo_measure/seed_prompts.json
Target : huggingface.co/datasets/neogenesislab/korean-llm-citation-baseline-2026

Layout:
    README.md                        bilingual ko + en dataset card
    data/measurements.jsonl          one record per LLM measurement (provider x prompt)
    data/seed_prompts.json           the 30 seed prompts (categorized)
    data/aggregate_by_provider.json  mention-rate stats per provider
    data/aggregate_by_category.json  mention-rate stats per prompt category
    metadata.json                    benchmark-level meta

Why this dataset is unique:
- Empirical Generative-Engine-Optimization (GEO) / Large-Language-Model-Optimization
  (LLMO) measurement dataset. Brand-mention rate observations across 3 frontier
  LLMs (gemini-2.5-flash, gpt-4o, claude-sonnet-4-6) for 30 brand-relevant prompts.
- Real industry-data is rare: most GEO research uses synthetic prompts.
- 30 prompts cover 6 intent categories: definition / comparison / problem_solving /
  pricing / reputation / product_specific.
- Includes both successful and errored (rate-limit / API failure) attempts so
  researchers can study coverage and reproducibility.

Anonymization:
- The PROMPTS reference Neo Genesis (publicly attested via Wikidata Q139569680)
  and SBU brands which are deliberate measurement targets, NOT PII.
- The RESPONSES contain LLM hallucinations including made-up biographical claims
  about the founder. These are PRESERVED as empirical observations of LLM
  behavior, but any real PII patterns (email / phone / RRN / API keys / paths)
  are stripped. The founder's NAME is preserved because it is the deliberate
  measurement target and is publicly attested via Wikidata Q139569708.
- Local file paths, hostnames, private IPs, and credentials are scrubbed.

Run:
    set PYTHONIOENCODING=utf-8
    python scripts/hf_publish/publish_geo_citations_baseline.py
"""
import io
import json
import os
import re
import sqlite3
import sys
from collections import Counter, defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
SQLITE_FILE = ROOT / "scripts" / "geo_measure" / "citations.sqlite3"
SEED_FILE = ROOT / "scripts" / "geo_measure" / "seed_prompts.json"
ENV_LOCAL = ROOT / ".env.local"
REPO_ID = "neogenesislab/korean-llm-citation-baseline-2026"


# ---------- Env ----------

def load_env(path: Path) -> None:
    if not path.exists():
        return
    text = path.read_text(encoding="utf-8")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k, v)


# ---------- PII / Credential redaction ----------
# NOTE: Owner's NAME ("Yesol Heo" / "허예솔") is INTENTIONALLY PRESERVED here
# because it is:
#   1. The deliberate measurement target (the prompt asks about the founder).
#   2. Publicly attested via Wikidata Q139569708 + Neo Genesis website.
# We strip only PII that is NOT public knowledge: email / phone / credentials /
# absolute paths / hostnames / RRN.

PII_PATTERNS = [
    # Owner's actual email and phone (NEVER public)
    (re.compile(r"\bdpthf1537@gmail\.com\b", re.IGNORECASE), "<redacted-email>"),
    (re.compile(r"\betribe\.cts@gmail\.com\b", re.IGNORECASE), "<redacted-email>"),
    (re.compile(r"\b010-?\d{4}-?\d{4}\b"), "<redacted-phone>"),
    # Generic email pattern (catches any email LLM might invent)
    (re.compile(r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b"), "<redacted-email>"),
    # Korean RRN (residential reg number) - 6 digits + 7 digits
    (re.compile(r"\b\d{6}-?[1-4]\d{6}\b"), "<redacted-rrn>"),
]

CRED_PATTERNS = [
    (re.compile(r"\bsk-[A-Za-z0-9_-]{20,}\b"), "<redacted-api-key>"),
    (re.compile(r"\bghp_[A-Za-z0-9]{30,}\b"), "<redacted-github-token>"),
    (re.compile(r"\bgho_[A-Za-z0-9]{30,}\b"), "<redacted-github-token>"),
    (re.compile(r"\bhf_[A-Za-z0-9]{30,}\b"), "<redacted-hf-token>"),
    (re.compile(r"\beyJ[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{20,}\.[A-Za-z0-9_-]{10,}\b"),
     "<redacted-jwt>"),
    (re.compile(r"\b\d{8,12}:[A-Za-z0-9_-]{30,}\b"), "<redacted-bot-token>"),
]

DEVICE_MAP = {
    "desktop-yesol": "<work-pc>",
    "DESKTOP-YESOL": "<work-pc>",
    "desktop-sol01": "<gpu-worker>",
    "DESKTOP-SOL01": "<gpu-worker>",
    "ysh-server": "<server>",
    "YSH-Server": "<server>",
    "mx-macbuild-mac-studio": "<mac-build>",
    "MX Mac Studio": "<mac-build>",
    "CTS_Sol": "<work-user>",
    "etribe-yesol": "<work-pc>",
}

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

IP_PATTERNS = [
    (re.compile(r"\b100\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<tailscale-ip>"),
    (re.compile(r"\b192\.168\.\d{1,3}\.\d{1,3}\b"), "<private-ip>"),
    (re.compile(r"\b10\.\d{1,3}\.\d{1,3}\.\d{1,3}\b"), "<private-ip>"),
]


def anonymize(text):
    """Apply redaction pipeline. Owner's name is preserved (measurement target)."""
    if text is None:
        return text
    s = str(text)
    for pat, repl in PATH_PATTERNS:
        s = pat.sub(repl, s)
    for hostname, generic in DEVICE_MAP.items():
        s = s.replace(hostname, generic)
    for pat, repl in PII_PATTERNS:
        s = pat.sub(repl, s)
    for pat, repl in CRED_PATTERNS:
        s = pat.sub(repl, s)
    for pat, repl in IP_PATTERNS:
        s = pat.sub(repl, s)
    return s


def assert_clean(text, where):
    """Verify no PII/credential leakage post-anonymization."""
    bad = []
    if re.search(r"D:[\\/]00\.test", text, re.IGNORECASE):
        bad.append("absolute-path")
    for hostname in DEVICE_MAP:
        if hostname in text:
            bad.append(f"hostname:{hostname}")
    for pat, _ in PII_PATTERNS:
        if pat.search(text):
            bad.append("pii-leak")
            break
    for pat, _ in CRED_PATTERNS:
        if pat.search(text):
            bad.append("credential")
            break
    for pat, _ in IP_PATTERNS:
        if pat.search(text):
            bad.append("private-ip")
            break
    if bad:
        raise RuntimeError(f"anonymization leak in {where}: {bad}")


# ---------- Data load ----------

def load_measurements(db_path):
    conn = sqlite3.connect(str(db_path))
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(
        "SELECT id, timestamp, provider, model, prompt_id, prompt_category, "
        "prompt_text, response_text, response_tokens, mention_neo_genesis, "
        "mention_domain_root, mention_domain_subs, mention_sbu_total, "
        "mention_founder, sentiment, citation_urls, error "
        "FROM measurements ORDER BY timestamp ASC, id ASC"
    )
    rows = []
    for r in cur.fetchall():
        rec = dict(r)
        # Parse citation_urls JSON if present
        if rec.get("citation_urls"):
            try:
                rec["citation_urls"] = json.loads(rec["citation_urls"])
            except Exception:
                rec["citation_urls"] = []
        else:
            rec["citation_urls"] = []
        # Drop sqlite internal id (use prompt_id + provider + timestamp as key)
        rec.pop("id", None)
        # Anonymize free-text fields (response_text + prompt_text + error)
        for field in ("prompt_text", "response_text", "error"):
            if rec.get(field):
                rec[field] = anonymize(rec[field])
        # Anonymize citation URLs (in case any leak)
        rec["citation_urls"] = [anonymize(u) for u in rec["citation_urls"]]
        rows.append(rec)
    conn.close()
    return rows


def load_seed_prompts(seed_path):
    with seed_path.open(encoding="utf-8") as f:
        return json.load(f)


# ---------- Aggregations ----------

def aggregate_by_provider(rows):
    """Mention-rate stats per provider."""
    by_provider = defaultdict(lambda: {
        "total_attempts": 0,
        "successful": 0,
        "errored": 0,
        "mentions_neo_genesis_total": 0,
        "mentions_sbu_total": 0,
        "mentions_founder_total": 0,
        "mentions_domain_root_total": 0,
        "mentions_domain_subs_total": 0,
        "prompts_with_any_mention": 0,
        "models": set(),
    })
    for r in rows:
        p = r["provider"]
        s = by_provider[p]
        s["total_attempts"] += 1
        s["models"].add(r.get("model") or "unknown")
        if r.get("error"):
            s["errored"] += 1
            continue
        s["successful"] += 1
        s["mentions_neo_genesis_total"] += r.get("mention_neo_genesis") or 0
        s["mentions_sbu_total"] += r.get("mention_sbu_total") or 0
        s["mentions_founder_total"] += r.get("mention_founder") or 0
        s["mentions_domain_root_total"] += r.get("mention_domain_root") or 0
        s["mentions_domain_subs_total"] += r.get("mention_domain_subs") or 0
        any_mention = (
            (r.get("mention_neo_genesis") or 0)
            + (r.get("mention_sbu_total") or 0)
            + (r.get("mention_founder") or 0)
            + (r.get("mention_domain_root") or 0)
            + (r.get("mention_domain_subs") or 0)
        )
        if any_mention > 0:
            s["prompts_with_any_mention"] += 1

    # Convert to plain dict + serialize sets
    out = {}
    for p, s in by_provider.items():
        s["models"] = sorted(s["models"])
        if s["successful"] > 0:
            s["mention_rate_any"] = round(
                s["prompts_with_any_mention"] / s["successful"], 4
            )
        else:
            s["mention_rate_any"] = 0.0
        out[p] = s
    return dict(sorted(out.items()))


def aggregate_by_category(rows):
    """Mention-rate stats per prompt category."""
    by_cat = defaultdict(lambda: {
        "total_attempts": 0,
        "successful": 0,
        "errored": 0,
        "any_mention_count": 0,
        "neo_genesis_mentions_sum": 0,
        "sbu_mentions_sum": 0,
        "founder_mentions_sum": 0,
    })
    for r in rows:
        c = r.get("prompt_category") or "unknown"
        s = by_cat[c]
        s["total_attempts"] += 1
        if r.get("error"):
            s["errored"] += 1
            continue
        s["successful"] += 1
        s["neo_genesis_mentions_sum"] += r.get("mention_neo_genesis") or 0
        s["sbu_mentions_sum"] += r.get("mention_sbu_total") or 0
        s["founder_mentions_sum"] += r.get("mention_founder") or 0
        any_mention = (
            (r.get("mention_neo_genesis") or 0)
            + (r.get("mention_sbu_total") or 0)
            + (r.get("mention_founder") or 0)
            + (r.get("mention_domain_root") or 0)
            + (r.get("mention_domain_subs") or 0)
        )
        if any_mention > 0:
            s["any_mention_count"] += 1

    out = {}
    for c, s in by_cat.items():
        if s["successful"] > 0:
            s["mention_rate_any"] = round(s["any_mention_count"] / s["successful"], 4)
        else:
            s["mention_rate_any"] = 0.0
        out[c] = s
    return dict(sorted(out.items()))


# ---------- Dataset card ----------

def build_readme(stats_provider, stats_category, n_rows, n_prompts, time_window):
    provider_table = "\n".join(
        f"| `{p}` | {s['successful']} / {s['total_attempts']} | "
        f"{s['mention_rate_any']*100:.1f}% | {s['mentions_neo_genesis_total']} | "
        f"{s['mentions_sbu_total']} | {s['mentions_founder_total']} |"
        for p, s in stats_provider.items()
    )
    category_table = "\n".join(
        f"| `{c}` | {s['successful']} / {s['total_attempts']} | "
        f"{s['mention_rate_any']*100:.1f}% |"
        for c, s in stats_category.items()
    )

    yaml_front = f"""---
language:
- ko
- en
license: cc-by-4.0
task_categories:
- text-generation
- text-classification
tags:
- generative-engine-optimization
- geo
- llmo
- llm-citation
- brand-mention
- benchmark
- evaluation
- multilingual
- bilingual
- korean
- english
- gemini
- gpt-4o
- claude
- neo-genesis
size_categories:
- n<1K
pretty_name: "Korean LLM Citation Baseline 2026 (Neo Genesis GEO Measurement)"
configs:
- config_name: measurements
  data_files:
  - split: train
    path: data/measurements.jsonl
---
"""
    body = f"""
# Korean LLM Citation Baseline 2026 (Neo Genesis GEO Measurement)

> A real, empirical Generative-Engine-Optimization (GEO) / LLM-Optimization (LLMO) measurement dataset. **{n_rows} brand-mention observations** across **3 frontier LLMs** (`gemini-2.5-flash`, `gpt-4o`, `claude-sonnet-4-6`) for **{n_prompts} bilingual brand-relevant prompts**, captured from {time_window['start']} to {time_window['end']}.

Released by **[Neo Genesis](https://neogenesis.app)** to support GEO/LLMO research. This is one of the few public datasets where the measurement target is a real, publicly attested company (Wikidata [Q139569680](https://www.wikidata.org/wiki/Q139569680)) instead of a synthetic brand.

## Why this dataset exists

GEO/LLMO research is dominated by:
- **Synthetic-prompt benchmarks** (no real brand involved).
- **Single-LLM probes** (does ChatGPT mention us?).
- **Self-report surveys** (anecdotal, not reproducible).

What is missing publicly:
- **Cross-LLM, multi-category, real-brand citation rates** measured under a fixed prompt protocol.
- **Both successful and errored attempts** preserved together (so researchers can study API coverage / rate-limiting / refusals).
- **Bilingual (ko + en) prompts** for the same brand, since global LLMs differ a lot between Korean and English citation behavior.

This dataset fills that gap with one company's real production GEO probe.

## Dataset summary

- **{n_rows} measurement rows** in `data/measurements.jsonl`. Each row is one (provider, model, prompt) attempt.
- **{n_prompts} seed prompts** across **6 intent categories** in `data/seed_prompts.json`:
  - `definition` (5 prompts) — "Who runs multiple SaaS with one autonomous AI?"
  - `comparison` (5) — "ToolPick vs G2 vs Capterra"
  - `problem_solving` (5) — "How do I run 10+ SaaS as a solo founder?"
  - `pricing` (3) — "ToolPick pricing vs G2 pricing"
  - `reputation` (3) — "Is Neo Genesis trustworthy?"
  - `product_specific` (9) — "WhyLab Gemini 2.5 Docker validation methodology"
- **3 LLMs** measured: `gemini-2.5-flash`, `gpt-4o`, `claude-sonnet-4-6`.
- **Mention counters** per row: `mention_neo_genesis`, `mention_domain_root` (neogenesis.app), `mention_domain_subs` (sbu domains), `mention_sbu_total` (named SBUs), `mention_founder`.
- **Errored attempts preserved** (`error` field) — including rate-limiting, credit-balance issues, and missing-key cases — so reproducibility studies are possible.

## Aggregate stats by provider

| Provider | Successful / Total | Any-mention rate | Neo Genesis mentions | SBU mentions | Founder mentions |
|---|---|---|---|---|---|
{provider_table}

## Aggregate stats by category

| Category | Successful / Total | Any-mention rate |
|---|---|---|
{category_table}

## Schema

### `data/measurements.jsonl` (one record per line)

```json
{{
  "timestamp": "2026-04-28T04:08:02.126309+00:00",
  "provider": "gemini",
  "model": "gemini-2.5-flash",
  "prompt_id": "spec-09",
  "prompt_category": "product_specific",
  "prompt_text": "Yesol Heo Neo Genesis founder background",
  "response_text": "<...full LLM response, may include hallucinations...>",
  "response_tokens": 542,
  "mention_neo_genesis": 4,
  "mention_domain_root": 0,
  "mention_domain_subs": 0,
  "mention_sbu_total": 0,
  "mention_founder": 2,
  "sentiment": "neutral",
  "citation_urls": [],
  "error": null
}}
```

### `data/seed_prompts.json`

The 30 seed prompts grouped by intent category. Bilingual (ko + en).

### `data/aggregate_by_provider.json` and `data/aggregate_by_category.json`

Pre-computed aggregations (counts, mention sums, mention rates).

## Quick start

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", "measurements", split="train")
print(ds[0]["prompt_text"])
print(ds[0]["mention_neo_genesis"])

# Filter to one provider
gemini_only = ds.filter(lambda r: r["provider"] == "gemini")
print(f"Gemini rows: {{len(gemini_only)}}")
```

## Suggested research applications

1. **GEO rate baselines** — establish how often a publicly-attested company is cited by frontier LLMs across English vs Korean prompts.
2. **Hallucination grounding** — the `response_text` field contains real LLM responses including factually incorrect claims about the founder. Useful for studying what frontier LLMs invent when probed about a real-but-niche entity.
3. **Cross-LLM consistency** — same prompt, three different LLMs. Measure agreement on whether to mention the brand and how.
4. **Bilingual asymmetry** — pairs of (English, Korean) prompts about the same entity, useful for studying multilingual citation gaps.
5. **Coverage / availability** — `error` rows preserve API-side failures (rate limit, credits, missing keys). Researchers can reason about reproducibility cost.

## Anonymization disclosure

The source data was a Neo Genesis production GEO probe.

| Class | Treatment |
|---|---|
| Founder name (`Yesol Heo`, `허예솔`) | **Preserved** — deliberate measurement target, publicly attested via Wikidata Q139569708 |
| Founder email / phone | Redacted to `<redacted-email>` / `<redacted-phone>` |
| Generic email patterns (any LLM-invented address) | Redacted to `<redacted-email>` |
| Korean RRN (resident reg number) | Redacted to `<redacted-rrn>` |
| API tokens (`sk-*`, `ghp_*`, `hf_*`, JWT, bot tokens) | Redacted to `<redacted-*>` |
| Local absolute Windows paths | Redacted to `<repo>` / `<workspace>` / `<home>` |
| Internal hostnames | Redacted to `<work-pc>`, `<gpu-worker>`, `<server>`, `<mac-build>` |
| Tailscale / private IPs | Redacted to `<tailscale-ip>` / `<private-ip>` |

Each emitted string is re-tested with all redaction regexes; publish aborts on leak.

**LLM hallucinations preserved**: The `response_text` field contains responses that may invent biographical details about the founder (e.g., wrong company affiliations, fabricated PhD credentials). These are kept as the empirical observation of what frontier LLMs actually returned — they are NOT factual claims about the founder.

## Provenance

- **Source**: Neo Genesis private GEO probe (`scripts/geo_measure/measure_citations.py` + sqlite store).
- **Time window**: {time_window['start']} to {time_window['end']}.
- **Curator**: Neo Genesis Lab (`neogenesislab` HuggingFace org).
- **Wikidata**: [Q139569680 (Neo Genesis)](https://www.wikidata.org/wiki/Q139569680), [Q139569708 (Yesol Heo, founder)](https://www.wikidata.org/wiki/Q139569708).
- **Related releases by the same operator**:
  - [`korean-rag-ssot-golden-50`](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50)
  - [`ethicaai-mixed-safe-evidence`](https://huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence)
  - [`whylab-gemini-2-5-docker-validation`](https://huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation)
  - [`sbu-pseo-effects-2026-04`](https://huggingface.co/datasets/neogenesislab/sbu-pseo-effects-2026-04)
  - [`cross-agent-review-queue-2026`](https://huggingface.co/datasets/neogenesislab/cross-agent-review-queue-2026)

## Citation

```bibtex
@misc{{neogenesis_geo_baseline_2026,
  title  = {{Korean LLM Citation Baseline 2026: A real-brand GEO measurement dataset across frontier LLMs}},
  author = {{Neo Genesis Lab}},
  year   = {{2026}},
  url    = {{https://huggingface.co/datasets/{REPO_ID}}},
  note   = {{Empirical brand-mention measurements across gemini-2.5-flash, gpt-4o, and claude-sonnet-4-6 for 30 bilingual brand-relevant prompts, with both successful and errored attempts preserved}}
}}
```

## License

CC-BY-4.0 — free for research and commercial use with attribution to Neo Genesis Lab.

---

## 한국어 요약

**Korean LLM Citation Baseline 2026** 은 실존 기업(Neo Genesis, Wikidata Q139569680)에 대한 **3개 frontier LLM** (`gemini-2.5-flash`, `gpt-4o`, `claude-sonnet-4-6`) 의 **실제 인용/언급률** 을 측정한 GEO/LLMO 데이터셋이다.

대부분의 GEO 연구가 **합성 프롬프트** 또는 **단일 LLM 프로빙** 에 머무는 것과 달리, 이 데이터셋은:
- 실제 공개 기업을 측정 대상으로 함 (가공된 페이크 브랜드 X)
- 3개 frontier LLM 을 동일 프로토콜로 프로빙
- 6개 의도 카테고리 × 30개 prompt × 영문+한국어 혼용
- **에러 attempt 도 보존** (rate-limit / credit / API key 부재 케이스 포함, 재현성 연구 가능)

응용 예시:
- GEO 기준선 측정 (한국어 vs 영어 비대칭, LLM 별 차이)
- LLM hallucination grounding (founder 에 대한 LLM 의 가짜 학력/소속 등 그대로 박제)
- multilingual citation gap 분석
- frontier LLM 의 niche-but-real entity 처리 행태 연구

**익명화**: 측정 대상인 창업자 이름은 의도적으로 유지 (Wikidata Q139569708 로 공개 attestation 됨). 그 외 이메일 / 전화 / 신용 / RRN / 절대 경로 / 호스트명 / private IP 는 모두 redaction. 발행 직전 모든 문자열에 대해 재검증.

라이선스 CC-BY-4.0 — 인용 시 자유롭게 사용 가능.
"""
    return yaml_front + body


# ---------- Main ----------

def main():
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN not found in env", file=sys.stderr)
        return 1

    if not SQLITE_FILE.exists():
        print(f"ERROR: sqlite file not found: {SQLITE_FILE}", file=sys.stderr)
        return 1
    if not SEED_FILE.exists():
        print(f"ERROR: seed prompts not found: {SEED_FILE}", file=sys.stderr)
        return 1

    rows = load_measurements(SQLITE_FILE)
    print(f"Loaded {len(rows)} measurement rows from sqlite")

    seed = load_seed_prompts(SEED_FILE)
    n_prompts = len(seed.get("prompts", []))
    print(f"Loaded {n_prompts} seed prompts")

    # Aggregations
    by_provider = aggregate_by_provider(rows)
    by_category = aggregate_by_category(rows)

    # Time window
    timestamps = [r["timestamp"] for r in rows if r.get("timestamp")]
    time_window = {
        "start": min(timestamps)[:10] if timestamps else "n/a",
        "end": max(timestamps)[:10] if timestamps else "n/a",
    }

    # Build artifacts
    measurements_jsonl = "\n".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in rows
    ) + "\n"

    seed_json = json.dumps(seed, ensure_ascii=False, indent=2)

    by_provider_json = json.dumps(by_provider, ensure_ascii=False, indent=2)
    by_category_json = json.dumps(by_category, ensure_ascii=False, indent=2)

    metadata = {
        "name": "Korean LLM Citation Baseline 2026 (Neo Genesis GEO Measurement)",
        "version": "1.0.0",
        "publisher": "Neo Genesis Lab (neogenesislab)",
        "wikidata_qid_company": "Q139569680",
        "wikidata_qid_founder": "Q139569708",
        "license": "CC-BY-4.0",
        "language": ["ko", "en"],
        "time_window": time_window,
        "providers": sorted({r["provider"] for r in rows}),
        "models": sorted({r.get("model") or "unknown" for r in rows}),
        "totals": {
            "measurement_rows": len(rows),
            "seed_prompts": n_prompts,
            "successful": sum(1 for r in rows if not r.get("error")),
            "errored": sum(1 for r in rows if r.get("error")),
        },
        "aggregate_by_provider": by_provider,
        "aggregate_by_category": by_category,
        "anonymization": {
            "founder_name": "preserved (deliberate measurement target, Wikidata Q139569708)",
            "founder_email_phone": "redacted to <redacted-email> / <redacted-phone>",
            "generic_email": "redacted to <redacted-email>",
            "korean_rrn": "redacted to <redacted-rrn>",
            "api_tokens": "redacted to <redacted-*>",
            "absolute_paths": "redacted to <repo> / <workspace> / <home>",
            "hostnames": "redacted to device-tier categories",
            "private_ips": "redacted to <tailscale-ip> / <private-ip>",
            "post_emit_assertion": "every emitted string re-tested; publish aborts on leak",
        },
        "comparison": {
            "synthetic_geo_benchmarks": "use fake brands; this dataset uses a publicly-attested real company",
            "single_llm_probes": "test one LLM; this dataset covers 3 frontier LLMs under fixed protocol",
            "self_report_surveys": "anecdotal; this dataset is reproducible from sqlite source",
        },
    }
    metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)

    readme = build_readme(by_provider, by_category, len(rows), n_prompts, time_window)

    # Final pre-emit anonymization sanity check
    for name, content in [
        ("README.md", readme),
        ("data/measurements.jsonl", measurements_jsonl),
        ("data/seed_prompts.json", seed_json),
        ("data/aggregate_by_provider.json", by_provider_json),
        ("data/aggregate_by_category.json", by_category_json),
        ("metadata.json", metadata_json),
    ]:
        assert_clean(content, f"final-artifact:{name}")
    print("All artifacts passed anonymization assertion.")

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
        ("data/measurements.jsonl", measurements_jsonl),
        ("data/seed_prompts.json", seed_json),
        ("data/aggregate_by_provider.json", by_provider_json),
        ("data/aggregate_by_category.json", by_category_json),
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
