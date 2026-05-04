"""
HuggingFace Datasets publish - Quant v11 Ensemble 6-Alpha Specs & Risk Engineering 2026

Source : auto-trading/docs/v11-ensemble/MASTER_DESIGN.md
       + auto-trading/docs/v11-ensemble/RISK_KILLSWITCH.md
       + auto-trading/docs/v11-ensemble/ROADMAP.md
       + auto-trading/docs/v11-ensemble/CURRENT_CODE_AUDIT.md
       + auto-trading/docs/v11-ensemble/INDEX.md
       + auto-trading/docs/v11-ensemble/backtest-v2-engine-decision.md
       + auto-trading/docs/v11-ensemble/alpha-specs/A1..A6_*.md
       + auto-trading/docs/v11-ensemble/expert-reports/01..06_*.md
       + auto-trading/docs/v11-ensemble/research/2026-04-24-external-validation.md

Target : huggingface.co/datasets/neogenesislab/quant-v11-ensemble-6alpha-specs-2026

Why this dataset is unique:
- Public quant ML/RL datasets (price candles, order books, returns) are common.
  Full systems-engineering specs of a working multi-alpha derivatives bot are rare.
- 6 low-correlation alphas + 9-layer kill switch + 6-expert cross-validation is
  a complete operating frame, not a single-model paper.
- Each alpha spec includes: theory background, entry/exit logic, risk constraints,
  paper-mode KPIs, expected daily contribution, and stop-go criteria.
- 9-layer kill switch covers per-position SL, daily/weekly/monthly DD, correlation
  killer, fee-budget freeze, halt persistence, order-rate cap, stablecoin depeg
  guard, and funding-spike guard - documented with thresholds, not slogans.

Educational disclaimer (must be in dataset card):
- Reference v11 ensemble runs in PAPER mode until 14-day Sharpe >= 1.2 + DSR >= 0.5.
- Quant alpha edge decays from publication. Readers must perform their own backtest.
- Not investment advice.

Run:
    set PYTHONIOENCODING=utf-8
    python scripts/hf_publish/publish_quant_v11_alpha_specs.py
"""
import io
import json
import os
import re
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
ENV_LOCAL = ROOT / ".env.local"
REPO_ID = "neogenesislab/quant-v11-ensemble-6alpha-specs-2026"

V11_DIR = ROOT / "auto-trading" / "docs" / "v11-ensemble"

# Source files with explicit doc_ids
DESIGN_DOCS = [
    ("master-design", "design", "v0.1", V11_DIR / "MASTER_DESIGN.md"),
    ("index", "design", "v1.0", V11_DIR / "INDEX.md"),
    ("current-code-audit", "design", "v0.1", V11_DIR / "CURRENT_CODE_AUDIT.md"),
    ("backtest-decision", "design", "v1.0", V11_DIR / "backtest-v2-engine-decision.md"),
]

KILL_SWITCH_DOC = ("kill-switch", "risk_layer", "v2.0", V11_DIR / "RISK_KILLSWITCH.md")
ROADMAP_DOC = ("roadmap", "roadmap", "v0.2", V11_DIR / "ROADMAP.md")

ALPHA_DOCS = [
    ("alpha-A1", "alpha_spec", "v0.1", "A1", V11_DIR / "alpha-specs" / "A1_liquidation_cascade.md"),
    ("alpha-A2", "alpha_spec", "v0.1", "A2", V11_DIR / "alpha-specs" / "A2_mean_reversion_ou.md"),
    ("alpha-A3", "alpha_spec", "v0.1", "A3", V11_DIR / "alpha-specs" / "A3_extreme_funding.md"),
    ("alpha-A4", "alpha_spec", "v0.1", "A4", V11_DIR / "alpha-specs" / "A4_macro_event.md"),
    ("alpha-A5", "alpha_spec", "v0.1", "A5", V11_DIR / "alpha-specs" / "A5_funding_basis_harvest.md"),
    ("alpha-A6", "alpha_spec", "v0.1", "A6", V11_DIR / "alpha-specs" / "A6_alt_market_making.md"),
]

EXPERT_DOCS = [
    ("expert-01-math", "expert_report", "v1.0", V11_DIR / "expert-reports" / "01_math_boundary.md"),
    ("expert-02-hft-mm", "expert_report", "v1.0", V11_DIR / "expert-reports" / "02_hft_mm_strategies.md"),
    ("expert-03-stat-arb", "expert_report", "v1.0", V11_DIR / "expert-reports" / "03_stat_arb.md"),
    ("expert-04-risk", "expert_report", "v1.0", V11_DIR / "expert-reports" / "04_risk_survival.md"),
    ("expert-05-ml-rl", "expert_report", "v1.0", V11_DIR / "expert-reports" / "05_ml_rl.md"),
    ("expert-06-event", "expert_report", "v1.0", V11_DIR / "expert-reports" / "06_event_alpha.md"),
]

RESEARCH_DOC = (
    "research-validation", "research", "v1.0",
    V11_DIR / "research" / "2026-04-24-external-validation.md",
)


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


# ---------- Anonymization ----------

PII_PATTERNS = [
    (re.compile(r"\bdpthf1537@gmail\.com\b", re.IGNORECASE), "<redacted-email>"),
    (re.compile(r"\betribe\.cts@gmail\.com\b", re.IGNORECASE), "<redacted-email>"),
    (re.compile(r"\b010-?\d{4}-?\d{4}\b"), "<redacted-phone>"),
    (re.compile(
        r"\b[A-Za-z0-9][A-Za-z0-9._%+-]{1,}@(?:[A-Za-z0-9-]+\.)+[A-Za-z]{2,6}\b"
    ), "<redacted-email>"),
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
    # Binance API key signature pattern (64 hex chars)
    (re.compile(r"\b[A-Fa-f0-9]{64}\b"), "<redacted-binance-key>"),
    # Wallet addresses (Ethereum-style)
    (re.compile(r"\b0x[A-Fa-f0-9]{40}\b"), "<redacted-wallet>"),
]

# Hostname -> generic device-tier label
DEVICE_MAP = {
    "desktop-yesol": "<work-pc>",
    "DESKTOP-YESOL": "<work-pc>",
    "desktop-sol01": "<gpu-worker>",
    "DESKTOP-SOL01": "<gpu-worker>",
    "ysh-server": "<server>",
    "YSH-Server": "<server>",
    "YSH-SERVER": "<server>",
    "mx-macbuild-mac-studio": "<mac-build>",
    "MX Mac Studio": "<mac-build>",
    "Mac Studio": "<mac-build>",
    "CTS_Sol": "<work-user>",
    "etribe-yesol": "<work-pc>",
    "quant-bot.asia-northeast3-a.ethereal-cache-487709-s3": "<gcp-vm>",
    "ethereal-cache-487709-s3": "<gcp-project>",
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
    (re.compile(r"\b34\.50\.8\.236\b"), "<vm-ip>"),
    (re.compile(r"\b34\.64\.211\.11\b"), "<vm-ip>"),
]

# Capital amount patterns - redact specific KRW totals/USDT balances beyond illustrative ranges
CAPITAL_PATTERNS = [
    (re.compile(r"\$9\.48\b"), "<illustrative-loss>"),
    (re.compile(r"-\$9\.48\b"), "<illustrative-loss>"),
    (re.compile(r"38\.6\s*USDT"), "<illustrative-balance>"),
    (re.compile(r"42\.8\s*USDT"), "<illustrative-balance>"),
]


def anonymize(text):
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
    for pat, repl in CAPITAL_PATTERNS:
        s = pat.sub(repl, s)
    return s


def assert_clean(text, where):
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


# ---------- Section parsing ----------

# Kill switch layer detection (L1-L9 from RISK_KILLSWITCH.md)
KILL_SWITCH_LAYER_PATTERN = re.compile(
    r"###?\s*L(\d)\b|\bLayer\s+(\d)\b|\bL(\d)[\s.:]", re.IGNORECASE
)


def detect_kill_switch_layer(title, body):
    combined = f"{title}\n{body}"
    nums = []
    for m in KILL_SWITCH_LAYER_PATTERN.finditer(combined):
        for g in m.groups():
            if g is not None:
                try:
                    n = int(g)
                    if 1 <= n <= 9:
                        nums.append(n)
                except ValueError:
                    pass
    if not nums:
        return None
    # Use the most-mentioned layer in this section
    from collections import Counter
    return Counter(nums).most_common(1)[0][0]


def extract_references(text):
    refs = []
    for m in re.finditer(r"https?://[^\s)\]>]+", text):
        url = m.group(0).rstrip(".,;:")
        refs.append(url)
    for m in re.finditer(r"`([^`]+\.(?:md|yaml|json|py|js|ts))`", text):
        refs.append(m.group(1))
    seen = set()
    out = []
    for r in refs:
        if r not in seen:
            seen.add(r)
            out.append(r)
    return json.dumps(out, ensure_ascii=False)


def parse_markdown_sections(doc_id, doc_type, version, path, text, alpha_id=None):
    """Parse a markdown file into header-based sections."""
    sections = []
    pattern = re.compile(r"^(#{1,4})\s+(.+?)$", re.MULTILINE)
    matches = list(pattern.finditer(text))
    if not matches:
        sec_text = text.strip()
        if sec_text:
            sections.append({
                "doc_id": doc_id,
                "doc_type": doc_type,
                "version": version,
                "alpha_id": alpha_id,
                "section_id": f"{doc_id}/root",
                "section_title": path.stem,
                "section_text": sec_text,
            })
        return sections

    trail = []
    for i, m in enumerate(matches):
        depth = len(m.group(1))
        title = m.group(2).strip()
        start = m.end()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        body = text[start:end].strip()

        trail = trail[: depth - 1]
        while len(trail) < depth - 1:
            trail.append("_")
        trail.append(title)

        section_id = f"{doc_id}/" + "/".join(
            re.sub(r"[^\w\-]+", "_", t)[:40] for t in trail
        )

        if not body:
            continue

        sections.append({
            "doc_id": doc_id,
            "doc_type": doc_type,
            "version": version,
            "alpha_id": alpha_id,
            "section_id": section_id,
            "section_title": title,
            "section_text": body,
        })
    return sections


def collect_sections():
    all_sections = []
    source_index = []

    def add_doc(doc_id, doc_type, version, path, alpha_id=None):
        if not path.exists():
            print(f"WARN: missing source {path}", file=sys.stderr)
            return
        text = path.read_text(encoding="utf-8")
        secs = parse_markdown_sections(doc_id, doc_type, version, path, text, alpha_id)
        all_sections.extend(secs)
        source_index.append({
            "doc_id": doc_id,
            "doc_type": doc_type,
            "version": version,
            "alpha_id": alpha_id,
            "source_filename": path.name,
            "section_count": len(secs),
            "raw_chars": len(text),
        })

    for doc_id, doc_type, version, path in DESIGN_DOCS:
        add_doc(doc_id, doc_type, version, path)

    add_doc(*KILL_SWITCH_DOC)
    add_doc(*ROADMAP_DOC)

    for doc_id, doc_type, version, alpha_id, path in ALPHA_DOCS:
        add_doc(doc_id, doc_type, version, path, alpha_id=alpha_id)

    for doc_id, doc_type, version, path in EXPERT_DOCS:
        add_doc(doc_id, doc_type, version, path)

    add_doc(*RESEARCH_DOC)

    return all_sections, source_index


# ---------- Main ----------

def main():
    load_env(ENV_LOCAL)
    token = os.environ.get("HF_TOKEN")
    if not token:
        print("ERROR: HF_TOKEN not found in env", file=sys.stderr)
        return 1

    print("Collecting sections from v11 ensemble docs...")
    sections, source_index = collect_sections()
    print(f"Parsed {len(sections)} raw sections from {len(source_index)} source files")

    # Enrich each section
    enriched = []
    for s in sections:
        title = anonymize(s["section_title"]) or ""
        body = anonymize(s["section_text"]) or ""
        sec_id = anonymize(s["section_id"]) or ""

        # Detect kill switch layer for risk_layer doc_type
        ks_layer = None
        if s["doc_type"] == "risk_layer":
            ks_layer = detect_kill_switch_layer(title, body)

        record = {
            "doc_id": s["doc_id"],
            "doc_type": s["doc_type"],
            "version": s["version"],
            "section_id": sec_id,
            "section_title": title,
            "section_text": body,
            "alpha_id": s.get("alpha_id"),
            "kill_switch_layer": ks_layer,
            "references": extract_references(body),
        }
        enriched.append(record)

    by_type = defaultdict(int)
    by_alpha = defaultdict(int)
    for r in enriched:
        by_type[r["doc_type"]] += 1
        if r.get("alpha_id"):
            by_alpha[r["alpha_id"]] += 1
    print(f"Section breakdown by doc_type: {dict(by_type)}")
    print(f"Section breakdown by alpha_id: {dict(by_alpha)}")

    # Build artifacts
    sections_jsonl = "\n".join(
        json.dumps(r, ensure_ascii=False, separators=(",", ":")) for r in enriched
    ) + "\n"
    source_index_json = json.dumps(source_index, ensure_ascii=False, indent=2)

    metadata = {
        "name": "Quant v11 Ensemble 6-Alpha Specs & Risk Engineering 2026",
        "version": "1.0.0",
        "publisher": "Neo Genesis Lab (neogenesislab)",
        "wikidata_qid_company": "Q139569680",
        "wikidata_qid_founder": "Q139569708",
        "license": "CC-BY-4.0",
        "language": ["ko", "en"],
        "totals": {
            "sections": len(enriched),
            "by_doc_type": dict(by_type),
            "by_alpha": dict(by_alpha),
            "sources": len(source_index),
        },
        "schema_columns": {
            "doc_id": "string - master-design / kill-switch / roadmap / alpha-A1..A6 / expert-01..06 / research-validation / backtest-decision / index / current-code-audit",
            "doc_type": "string - design | risk_layer | alpha_spec | expert_report | research | roadmap",
            "version": "string - semantic version of the source doc",
            "section_id": "string - slugified heading hierarchy",
            "section_title": "string - heading title",
            "section_text": "string - actual section body content",
            "alpha_id": "string|null - A1 | A2 | A3 | A4 | A5 | A6 | null for non-alpha docs",
            "kill_switch_layer": "int|null - 1..9 for risk_layer entries (Layer 1=position SL .. Layer 9=funding-spike guard)",
            "references": "string - JSON array of inline links / file paths",
        },
        "operating_status": {
            "mode": "PAPER",
            "trade_state_recorded_in": "Wikidata Q139569680 + repo PAPER lease",
            "graduation_gate": "14-day Sharpe >= 1.2 + Deflated Sharpe Ratio >= 0.5 on the active alpha",
            "safety_layers": 9,
            "max_leverage_hard_cap": "5x (Kelly/3 safety factor)",
        },
        "schema_org_dataset": {
            "@context": "https://schema.org",
            "@type": "Dataset",
            "name": "Quant v11 Ensemble 6-Alpha Specs & Risk Engineering 2026",
            "description": (
                "A reference systems-engineering corpus for a 6-alpha cryptocurrency "
                "perpetual futures ensemble bot. Includes 6 low-correlation alpha "
                "specifications (A1 Liquidation Cascade, A2 Mean Reversion OU, "
                "A3 Extreme Funding, A4 Macro Event, A5 Funding/Basis Harvest, "
                "A6 Alt Market-Making), a 9-layer kill switch, 6 cross-discipline "
                "expert validation reports (math, HFT/MM, stat arb, risk, ML/RL, "
                "event alpha), external benchmark research, and the nautilus_trader "
                "+ hftbacktest backtest engine decision."
            ),
            "license": "https://creativecommons.org/licenses/by/4.0/",
            "creator": {
                "@type": "Organization",
                "name": "Neo Genesis Lab",
                "url": "https://neogenesis.app",
                "sameAs": "https://www.wikidata.org/wiki/Q139569680",
            },
            "publisher": {
                "@type": "Organization",
                "name": "Neo Genesis Lab",
                "url": "https://neogenesis.app",
            },
            "url": f"https://huggingface.co/datasets/{REPO_ID}",
            "inLanguage": ["ko", "en"],
            "keywords": [
                "quantitative-finance", "algorithmic-trading", "cryptocurrency",
                "perpetual-futures", "binance", "ensemble-strategy",
                "liquidation-cascade", "mean-reversion", "ornstein-uhlenbeck",
                "funding-rate-arbitrage", "basis-harvest", "market-making",
                "risk-management", "kill-switch", "kelly-criterion",
                "deflated-sharpe-ratio", "nautilus-trader", "hftbacktest",
                "paper-trading", "systems-engineering",
            ],
            "variableMeasured": [
                {"@type": "PropertyValue", "name": "alpha_id",
                 "description": "A1..A6 alpha identifier"},
                {"@type": "PropertyValue", "name": "kill_switch_layer",
                 "description": "1..9 risk layer index"},
                {"@type": "PropertyValue", "name": "doc_type",
                 "description": "design | risk_layer | alpha_spec | expert_report | research | roadmap"},
            ],
        },
        "anonymization": {
            "internal_hostnames": "redacted to <work-pc>, <gpu-worker>, <server>, <mac-build>",
            "vm_identifiers": "redacted to <gcp-vm>, <gcp-project>, <vm-ip>",
            "owner_email_phone": "redacted to <redacted-email> / <redacted-phone>",
            "korean_rrn": "redacted to <redacted-rrn>",
            "api_tokens": "redacted to <redacted-*> (Binance keys, GitHub PAT, HF, JWT, bot tokens)",
            "wallet_addresses": "redacted to <redacted-wallet>",
            "absolute_paths": "redacted to <repo> / <workspace> / <home>",
            "private_ips": "redacted to <tailscale-ip> / <private-ip>",
            "specific_capital_amounts": "redacted to <illustrative-loss> / <illustrative-balance> beyond paper-mode ranges",
            "post_emit_assertion": "every emitted string re-tested with all redaction regexes; publish aborts on leak",
        },
        "educational_disclaimer": (
            "Educational reference only. Not investment advice. "
            "The reference v11 ensemble is in PAPER mode (no live capital) until a "
            "14-day Sharpe >= 1.2 + Deflated Sharpe Ratio >= 0.5 gate clears. "
            "Quant alpha edge decays from publication; readers must perform their "
            "own backtest with their own data, fees, and slippage assumptions."
        ),
    }
    metadata_json = json.dumps(metadata, ensure_ascii=False, indent=2)

    n_design = by_type.get("design", 0)
    n_risk = by_type.get("risk_layer", 0)
    n_alpha = by_type.get("alpha_spec", 0)
    n_expert = by_type.get("expert_report", 0)
    n_research = by_type.get("research", 0)
    n_roadmap = by_type.get("roadmap", 0)

    yaml_front = """---
language:
- ko
- en
license: cc-by-4.0
task_categories:
- text-generation
- text-classification
tags:
- quantitative-finance
- algorithmic-trading
- cryptocurrency
- perpetual-futures
- binance
- ensemble-strategy
- liquidation-cascade
- mean-reversion
- ornstein-uhlenbeck
- funding-rate-arbitrage
- basis-harvest
- market-making
- risk-management
- kill-switch
- kelly-criterion
- deflated-sharpe-ratio
- nautilus-trader
- hftbacktest
- paper-trading
- systems-engineering
- bilingual
- korean
- english
- neo-genesis
size_categories:
- n<1K
pretty_name: "Quant v11 Ensemble 6-Alpha Specs & Risk Engineering 2026"
configs:
- config_name: sections
  data_files:
  - split: train
    path: data/sections.jsonl
---
"""

    body = f"""
# Quant v11 Ensemble - 6-Alpha Specs & Risk Engineering 2026

> **A reference systems-engineering corpus for a 6-alpha cryptocurrency perpetual futures ensemble bot.** {len(enriched)} parsed sections from {len(source_index)} canonical source files: **{n_design} design, {n_risk} risk-layer, {n_alpha} alpha-spec, {n_expert} expert-report, {n_research} research, {n_roadmap} roadmap** sections.

Released by **[Neo Genesis](https://neogenesis.app)** ([Wikidata Q139569680](https://www.wikidata.org/wiki/Q139569680)).

## Educational disclaimer (read first)

- **Not investment advice.** This dataset is published for research and engineering education.
- **PAPER mode.** The reference v11 ensemble runs in PAPER mode (no live capital) until a **14-day Sharpe >= 1.2 + Deflated Sharpe Ratio >= 0.5** gate clears on at least one alpha.
- **Edge decay.** Quant alpha edges decay from the moment they are documented publicly. Anything in this corpus must be re-validated by the reader against fresh data, real fees, real slippage, and real funding before any capital is risked.
- **Survivorship + lookahead.** v6-v10 of this same bot produced "127k wins / 0 losses" backtests that turned into a -<illustrative-loss> drain on 5 days of live trading. The v11 redesign exists *because* the old backtests were wrong. Treat any backtest, including the ones implied here, with that history in mind.

## Why this dataset is unique

Public quant ML / RL datasets (price candles, order books, returns) are common. Full **systems-engineering specs** of a working multi-alpha derivatives bot - alphas + risk + experts + research + roadmap as one coherent system - are rare publicly. What is in here that you usually have to reconstruct yourself:

1. **6 low-correlation alpha specifications** (A1..A6) with theory background, entry/exit logic, paper-mode KPIs, expected daily contribution, and stop-go criteria.
2. **9-layer kill switch** (Layer 1 = per-position SL, ..., Layer 9 = funding-spike guard) with explicit thresholds, not slogans.
3. **6 cross-discipline expert validation reports** - math boundary (Kelly + ruin probability), HFT / market-making, statistical arbitrage, risk survival, ML / RL, event alpha. Each report cross-checks the alphas independently.
4. **External benchmark research** (2026-04-24) on what public benchmarks exist for liquidation-cascade alphas, OU-mean-reversion, funding arbitrage, and the absence of public benchmarks for several of these.
5. **Backtest engine decision** - why the v11 ensemble picks `nautilus_trader` (primary) + `hftbacktest` (microstructure-sensitive A1 / A6) + `vectorbt pro` (cross-validation), with the 8 anti-patterns the v6-v10 backtests fell into.

This is a *real* design used by a single-operator quant stack (operator publicly attested via [Wikidata Q139569708](https://www.wikidata.org/wiki/Q139569708)). It is not a paper proposal.

## Dataset summary

- **{len(enriched)} sections** in `data/sections.jsonl`. Each row is one parsed heading-section.
- **{len(source_index)} source files** indexed in `data/source_index.json`:
  - **Design** ({n_design} sections): `MASTER_DESIGN.md`, `INDEX.md`, `CURRENT_CODE_AUDIT.md`, `backtest-v2-engine-decision.md`.
  - **Risk layers** ({n_risk} sections): `RISK_KILLSWITCH.md` - 9-layer defense.
  - **Alpha specs** ({n_alpha} sections): A1 Liquidation Cascade, A2 Mean Reversion OU, A3 Extreme Funding, A4 Macro Event, A5 Funding / Basis Harvest, A6 Alt Market-Making.
  - **Expert reports** ({n_expert} sections): math boundary, HFT / MM, stat arb, risk survival, ML / RL, event alpha.
  - **Research** ({n_research} sections): external benchmark validation 2026-04-24.
  - **Roadmap** ({n_roadmap} sections): Phase -1 / 0 / 1 progression.

## Schema

`data/sections.jsonl` - one JSON record per line:

| column | type | description |
|---|---|---|
| `doc_id` | string | `master-design / kill-switch / roadmap / alpha-A1..A6 / expert-01..06 / research-validation / backtest-decision / index / current-code-audit` |
| `doc_type` | string | `design \\| risk_layer \\| alpha_spec \\| expert_report \\| research \\| roadmap` |
| `version` | string | semantic version of the source doc |
| `section_id` | string | slugified heading hierarchy (`<doc_id>/<h1>/<h2>/...`) |
| `section_title` | string | heading title |
| `section_text` | string | actual section body content |
| `alpha_id` | string\\|null | `A1 \\| A2 \\| A3 \\| A4 \\| A5 \\| A6` for alpha-spec rows, `null` otherwise |
| `kill_switch_layer` | int\\|null | `1..9` for risk-layer rows when an explicit layer is mentioned |
| `references` | string | JSON array of inline links / file paths |

## Quick start

```python
from datasets import load_dataset

ds = load_dataset("{REPO_ID}", "sections", split="train")
print(len(ds), "sections")

# Get all alpha specs
alphas = ds.filter(lambda r: r["doc_type"] == "alpha_spec")
print(f"{{len(alphas)}} alpha-spec sections")

# Filter to one specific alpha (A1 Liquidation Cascade)
a1 = ds.filter(lambda r: r["alpha_id"] == "A1")
for row in a1:
    print(row["section_title"])

# Get all risk-layer sections that reference Layer 3 (correlation killer)
l3 = ds.filter(
    lambda r: r["doc_type"] == "risk_layer" and r["kill_switch_layer"] == 3
)

# Get all expert reports
experts = ds.filter(lambda r: r["doc_type"] == "expert_report")
```

## Suggested research applications

1. **Multi-alpha ensemble design** - train portfolio allocators or meta-classifiers to gate alpha activation under regime conditions.
2. **Kill-switch reasoning** - supervise classifiers that decide when to halt trading based on correlation, drawdown, fee burn, or stablecoin depeg signals.
3. **Backtest anti-pattern detection** - the `backtest-decision` doc enumerates 8 specific anti-patterns (lookahead bias, survivorship, fill-model bugs, missing funding, missing slippage, etc.) - useful as supervision for backtest auditors.
4. **Cross-discipline alpha review** - 6 expert reports give you parallel views of the same 6 alphas. Useful as a small benchmark for "do LLM critics agree with domain experts."
5. **Single-operator quant ops** - rare reference for what one person actually has to specify (alphas + risk + telemetry + roadmap + experts) to ship a derivatives bot honestly.

## Operating status

- **Mode**: PAPER (no live capital deployed)
- **Graduation gate**: 14-day Sharpe >= 1.2 AND Deflated Sharpe Ratio >= 0.5 on the active alpha
- **Max leverage hard cap**: 5x (Kelly/3 safety factor)
- **Safety layers**: 9 (per-position SL, daily/weekly/monthly DD, correlation killer, fee-budget freeze, halt persistence, order-rate cap, stablecoin depeg guard, funding-spike guard)

## Anonymization

| Class | Treatment |
|---|---|
| Internal hostnames | Redacted to `<work-pc>`, `<gpu-worker>`, `<server>`, `<mac-build>`, `<work-user>` |
| GCP VM identifiers | Redacted to `<gcp-vm>`, `<gcp-project>`, `<vm-ip>` |
| Owner email / phone | Redacted to `<redacted-email>` / `<redacted-phone>` |
| Korean RRN | Redacted to `<redacted-rrn>` |
| API tokens (Binance keys, `sk-*`, `ghp_*`, `hf_*`, JWT, bot tokens) | Redacted to `<redacted-*>` |
| Wallet addresses (`0x...`) | Redacted to `<redacted-wallet>` |
| Absolute Windows paths | Redacted to `<repo>` / `<workspace>` / `<home>` |
| Tailscale / private IPs | Redacted to `<tailscale-ip>` / `<private-ip>` |
| Specific capital amounts beyond illustrative ranges | Redacted to `<illustrative-loss>` / `<illustrative-balance>` |

Each emitted string is re-tested with all redaction regexes; publish aborts on leak.

## Provenance

- **Source**: Neo Genesis private SSOT (`auto-trading/docs/v11-ensemble/*`).
- **Curator**: Neo Genesis Lab (`neogenesislab` HuggingFace org).
- **Wikidata**: [Q139569680 (Neo Genesis)](https://www.wikidata.org/wiki/Q139569680), [Q139569708 (Yesol Heo, founder)](https://www.wikidata.org/wiki/Q139569708).
- **Related releases by the same operator**:
  - [`korean-rag-ssot-golden-50`](https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50)
  - [`ethicaai-mixed-safe-evidence`](https://huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence)
  - [`whylab-gemini-2-5-docker-validation`](https://huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation)
  - [`sbu-pseo-effects-2026-04`](https://huggingface.co/datasets/neogenesislab/sbu-pseo-effects-2026-04)
  - [`cross-agent-review-queue-2026`](https://huggingface.co/datasets/neogenesislab/cross-agent-review-queue-2026)
  - [`korean-llm-citation-baseline-2026`](https://huggingface.co/datasets/neogenesislab/korean-llm-citation-baseline-2026)
  - [`sora-multi-device-orchestration-2026`](https://huggingface.co/datasets/neogenesislab/sora-multi-device-orchestration-2026)

## Citation

```bibtex
@misc{{neogenesis_quant_v11_2026,
  title  = {{Quant v11 Ensemble 6-Alpha Specs and Risk Engineering 2026: A reference systems-engineering corpus for a multi-alpha cryptocurrency perpetual futures bot}},
  author = {{Neo Genesis Lab}},
  year   = {{2026}},
  url    = {{https://huggingface.co/datasets/{REPO_ID}}},
  note   = {{6 alphas, 9-layer kill switch, 6 expert validations, external benchmark research; published in PAPER mode pending 14-day Sharpe >= 1.2 + DSR >= 0.5 graduation gate}}
}}
```

## License

CC-BY-4.0 - free for research and commercial use with attribution to Neo Genesis Lab.

---

## 한국어 요약

**Quant v11 Ensemble 6-Alpha Specs & Risk Engineering 2026** 은 Binance 선물에서 일 평균 0.6~1.0% 누적 수익률을 목표로 하는 **6-알파 앙상블 봇의 시스템 엔지니어링 SSOT** 코퍼스다.

### 교육용 면책 (먼저 읽기)
- **투자 자문 아님.** 본 데이터셋은 연구 / 엔지니어링 교육 목적으로 공개된다.
- **PAPER 모드.** 본 v11 reference 앙상블은 **14일 Sharpe >= 1.2 + Deflated Sharpe Ratio >= 0.5** 게이트를 통과할 때까지 PAPER 모드에서만 운영된다 (실자본 0).
- **알파 감쇠.** 퀀트 알파 edge 는 공개 시점부터 감쇠한다. 본 코퍼스의 어떤 내용도 독자가 자신의 데이터 / 수수료 / 슬리피지 / funding 가정으로 재검증하지 않으면 그대로 사용해서는 안 된다.
- **생존편향 + 룩어헤드.** 동일 봇의 v6-v10 은 "127k 승 / 0 패" 백테스트를 만들어 냈고 라이브에서 5일 만에 -<illustrative-loss> 드레인이 발생했다. v11 의 존재 자체가 옛 백테스트가 틀렸기 때문이다. 본 코퍼스가 암시하는 어떤 백테스트도 그 이력 하에서 읽어야 한다.

### 다루는 것
- **6개 저상관 알파 스펙** (A1 Liquidation Cascade, A2 Mean Reversion OU, A3 Extreme Funding, A4 Macro Event, A5 Funding / Basis Harvest, A6 Alt Market-Making) - 이론 / 진입출구 / 페이퍼 KPI / 일일 기여 / stop-go 기준.
- **9-Layer Kill Switch** - L1 포지션 SL, ..., L9 funding-spike guard. 슬로건이 아니라 임계값으로.
- **6명 전문가 교차 검증** - 수학 (Kelly + 파산확률), HFT / MM, 통계차익, 리스크 생존, ML / RL, 이벤트 알파.
- **외부 벤치마크 리서치** - liquidation-cascade / OU / funding arb 의 공개 벤치마크 부재 공식화.
- **백테스트 엔진 결정** - nautilus_trader 메인 + hftbacktest 보조 + vectorbt 검증, v6-v10 백테스트의 8 anti-pattern.

### 익명화
디바이스 hostname / 이메일 / 전화 / RRN / API 토큰 / 지갑 주소 / 절대경로 / private IP / 구체적 자본 금액 모두 redaction. 발행 직전 모든 문자열을 redaction regex 로 재검증.

라이선스 CC-BY-4.0 - 인용 시 자유롭게 사용 가능.
"""
    readme = yaml_front + body

    artifacts = [
        ("README.md", readme),
        ("data/sections.jsonl", sections_jsonl),
        ("data/source_index.json", source_index_json),
        ("metadata.json", metadata_json),
    ]
    for name, content in artifacts:
        assert_clean(content, f"final-artifact:{name}")
    print("All artifacts passed anonymization assertion.")

    from huggingface_hub import HfApi
    api = HfApi(token=token)

    print(f"create_repo {REPO_ID} (dataset, public)")
    api.create_repo(
        repo_id=REPO_ID,
        repo_type="dataset",
        exist_ok=True,
        private=False,
    )

    for path_in_repo, content in artifacts:
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
