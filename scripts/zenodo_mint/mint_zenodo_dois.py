"""
Zenodo DOI minting — 8 HF datasets + 1 GitHub repo software release

Mint open-access DataCite DOIs (10.5281/zenodo.NNNNNNN) for all Neo Genesis
public research assets, so AI crawlers (Semantic Scholar, OpenAlex, Google
Scholar) treat them as citable research.

- Production endpoint: https://zenodo.org (sandbox uses a separate token domain
  and is not available with the current credential — production-only run).
- Token source: D:/00.test/PAPER/EthicaAI/.env  ZENODO_ACCESS_TOKEN
- Idempotent: existing DOIs in zenodo_dois.json are skipped.
- Metadata-only deposit: each upload is a tiny metadata.json describing the
  asset; the actual data lives on HF / GitHub. This is normal practice and the
  DOI still resolves through DataCite + indexes.

Run:
    PYTHONIOENCODING=utf-8 python scripts/zenodo_mint/mint_zenodo_dois.py [--dry-run]
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from urllib import request, error
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parents[2]
TOKEN_ENV = ROOT.parent / "PAPER" / "EthicaAI" / ".env"
LEDGER = ROOT / ".agent" / "knowledge" / "wikidata-entities" / "zenodo_dois.json"

ZENODO_BASE = "https://zenodo.org/api"

GITHUB_REPO = "https://github.com/Yesol-Pilot/neo-genesis"
WIKIDATA_PARENT = "https://www.wikidata.org/wiki/Q139569680"


@dataclass
class Asset:
    slug: str
    title: str
    description: str
    upload_type: str = "dataset"  # "dataset" or "software"
    keywords: list[str] = field(default_factory=list)
    hf_url: str | None = None
    github_url: str | None = None


# ---------------------------------------------------------------------------
# Asset registry — 8 HF datasets + 1 GitHub repo (9th)
# ---------------------------------------------------------------------------

ASSETS: list[Asset] = [
    Asset(
        slug="korean-rag-ssot-golden-50",
        title="Korean RAG SSOT Golden 50 (Neo Genesis)",
        description=(
            "<p>Korean-language Retrieval-Augmented Generation evaluation set of "
            "50 hand-curated tasks for stress-testing real-world RAG agents on "
            "agent governance, autonomous trading, and security/PII redaction "
            "scenarios. Published by <a href='https://neogenesis.app'>Neo Genesis</a>"
            " (Wikidata Q139569680). Five categories — rag_v2_design (18), "
            "quant_v11 (8), ssot_governance (12), security_pii (6), operations (6) "
            "— with primary metric recall@10 ≥ 0.85 and four secondary metrics. "
            "Bilingual ko/en card. Companion data on Hugging Face: "
            "<code>neogenesislab/korean-rag-ssot-golden-50</code>.</p>"
        ),
        upload_type="dataset",
        keywords=[
            "RAG", "retrieval-augmented generation", "Korean", "evaluation",
            "agent-evaluation", "neo-genesis", "wikidata-Q139569680",
            "yesol-heo-founder", "governance", "security",
        ],
        hf_url="https://huggingface.co/datasets/neogenesislab/korean-rag-ssot-golden-50",
    ),
    Asset(
        slug="ethicaai-mixed-safe-evidence",
        title="EthicaAI Mixed-Safe Multi-Environment Evidence (NeurIPS 2026)",
        description=(
            "<p>Multi-environment evidence dataset (510 rows) supporting the "
            "EthicaAI mixed-safe framing: 160-seed adapted Coin Game with "
            "MACCL=78.10% vs selfish=22.08% (d=7.15) and 300-seed Fishery Nash "
            "Trap with φ1=0.7 reaching 87.7% population survival under welfare-"
            "positive cooperation. Companion to NeurIPS 2026 EthicaAI submission. "
            "Hugging Face: <code>neogenesislab/ethicaai-mixed-safe-evidence</code>.</p>"
        ),
        upload_type="dataset",
        keywords=[
            "ethicaai", "multi-agent", "cooperative AI", "Melting Pot",
            "Coin Game", "Fishery Nash Trap", "neo-genesis", "wikidata-Q139569680",
            "NeurIPS 2026", "yesol-heo-founder",
        ],
        hf_url="https://huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence",
    ),
    Asset(
        slug="whylab-gemini-2-5-docker-validation",
        title="WhyLab Gemini 2.5 Flash Docker Validation (Honest Null Result)",
        description=(
            "<p>402-episode (67 problems × 3 seeds × 2 conditions) Docker "
            "ground-truth validation of WhyLab causal-audit C2 vs baseline on "
            "Gemini 2.5 Flash. Published as an honest null result — adaptive C2 "
            "did not outperform fixed C2 on the SWE-bench slice — to support "
            "calibration claims rather than overclaim. Companion to NeurIPS 2026 "
            "WhyLab submission. Hugging Face: "
            "<code>neogenesislab/whylab-gemini-2-5-docker-validation</code>.</p>"
        ),
        upload_type="dataset",
        keywords=[
            "WhyLab", "causal audit", "Docker validation", "null result",
            "Gemini 2.5 Flash", "SWE-bench", "neo-genesis",
            "wikidata-Q139569680", "NeurIPS 2026", "yesol-heo-founder",
        ],
        hf_url="https://huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation",
    ),
    Asset(
        slug="sbu-pseo-effects-2026-04",
        title="Neo Genesis SBU Programmatic SEO Effects (April 2026)",
        description=(
            "<p>Anonymized programmatic-SEO effect dataset across 6 Strategic "
            "Business Units of Neo Genesis: ToolPick, AIForge, FinStack, "
            "SellKit, CraftDesk, DeployStack. April 2026 snapshot of template "
            "page generation, indexation rates, and traffic outcomes. Useful "
            "for empirical solo-operator multi-SaaS SEO research. Hugging Face: "
            "<code>neogenesislab/sbu-pseo-effects-2026-04</code>.</p>"
        ),
        upload_type="dataset",
        keywords=[
            "programmatic SEO", "pSEO", "SaaS", "solo operator", "indexation",
            "traffic", "neo-genesis", "wikidata-Q139569680", "yesol-heo-founder",
        ],
        hf_url="https://huggingface.co/datasets/neogenesislab/sbu-pseo-effects-2026-04",
    ),
    Asset(
        slug="cross-agent-review-queue-2026",
        title="Cross-Agent Code Review Queue (Codex <-> Claude, Neo Genesis 2026)",
        description=(
            "<p>Real cross-agent code review handoff log between Codex and "
            "Claude Code on Neo Genesis production code. Each entry captures "
            "owner_goal, owner_intent, constraints, success_criteria, "
            "review_lens, and result (NEW_SIGNAL vs NO_NEW_SIGNAL). Published as "
            "empirical evidence of bounded specialist multi-agent collaboration. "
            "Hugging Face: <code>neogenesislab/cross-agent-review-queue-2026</code>.</p>"
        ),
        upload_type="dataset",
        keywords=[
            "multi-agent", "code review", "Codex", "Claude", "agent handoff",
            "neo-genesis", "wikidata-Q139569680", "yesol-heo-founder",
            "agent collaboration",
        ],
        hf_url="https://huggingface.co/datasets/neogenesislab/cross-agent-review-queue-2026",
    ),
    Asset(
        slug="korean-llm-citation-baseline-2026",
        title="Korean LLM Citation Baseline 2026 (Neo Genesis GEO Measurement)",
        description=(
            "<p>Generative Engine Optimization (GEO) measurement baseline: "
            "30 Korean+English seed prompts × 4 LLM platforms (Anthropic, "
            "OpenAI, Perplexity, Gemini) tracking citation rates of "
            "Neo Genesis SBUs and the Yesol Heo founder identity. April–May "
            "2026 baseline. First open Korean-context GEO measurement protocol. "
            "Hugging Face: <code>neogenesislab/korean-llm-citation-baseline-2026</code>.</p>"
        ),
        upload_type="dataset",
        keywords=[
            "GEO", "generative engine optimization", "LLM citation", "Korean",
            "Anthropic", "OpenAI", "Perplexity", "Gemini", "neo-genesis",
            "wikidata-Q139569680", "yesol-heo-founder",
        ],
        hf_url="https://huggingface.co/datasets/neogenesislab/korean-llm-citation-baseline-2026",
    ),
    Asset(
        slug="sora-multi-device-orchestration-2026",
        title="Sora Multi-Device Orchestration Architecture 2026",
        description=(
            "<p>Architecture and operational telemetry from Sora — a multi-"
            "device personal-assistant runtime that orchestrates 6 heterogeneous "
            "fleet devices (control plane, GPU worker, work PC, server, "
            "Mac Studio, mobile operator) under a single consent-and-disclosure "
            "policy with capability tokens, blast-radius tiering, and Magentic-"
            "One dual-ledger pattern. Hugging Face: "
            "<code>neogenesislab/sora-multi-device-orchestration-2026</code>.</p>"
        ),
        upload_type="dataset",
        keywords=[
            "Sora", "multi-device", "agent orchestration", "Magentic-One",
            "fleet", "neo-genesis", "wikidata-Q139569680", "yesol-heo-founder",
            "operator agent",
        ],
        hf_url="https://huggingface.co/datasets/neogenesislab/sora-multi-device-orchestration-2026",
    ),
    Asset(
        slug="quant-v11-ensemble-6alpha-specs-2026",
        title="Quant v11 Ensemble 6-Alpha Specs & Risk Engineering 2026",
        description=(
            "<p>Open specification of the Neo Genesis Quant v11 6-alpha ensemble "
            "(A1 Liquidation Cascade, A2 Mean Reversion OU, A3 Extreme Funding, "
            "A4 Macro Event, A5 Funding/Basis Harvest, A6 Alt MM) with a 9-Layer "
            "kill-switch (Order Rate Cap, Correlation Killer, Stablecoin Depeg "
            "Guard, Funding Spike Guard, ...). Includes the documented 5x "
            "leverage hard cap and the survival-probability matrix used to "
            "justify it. Hugging Face: "
            "<code>neogenesislab/quant-v11-ensemble-6alpha-specs-2026</code>.</p>"
        ),
        upload_type="dataset",
        keywords=[
            "quantitative trading", "alpha ensemble", "kill switch",
            "risk management", "leverage", "neo-genesis",
            "wikidata-Q139569680", "yesol-heo-founder", "v11",
        ],
        hf_url="https://huggingface.co/datasets/neogenesislab/quant-v11-ensemble-6alpha-specs-2026",
    ),
    # 9th: GitHub repo software release
    Asset(
        slug="neo-genesis-repo-v1",
        title="Neo Genesis: Solo-Operator AI-Native Conglomerate (Public Source Repository v1.0.0)",
        description=(
            "<p>Public source repository for Neo Genesis, a solo-operator "
            "AI-native conglomerate with 11 Strategic Business Units, a "
            "multi-device Sora orchestration runtime, the Quant v11 6-alpha "
            "trading ensemble, and the EthicaAI / WhyLab NeurIPS 2026 research "
            "tracks. Versioned snapshot v1.0.0 (May 2026). "
            "GitHub: <a href='https://github.com/Yesol-Pilot/neo-genesis'>"
            "Yesol-Pilot/neo-genesis</a>.</p>"
        ),
        upload_type="software",
        keywords=[
            "Neo Genesis", "solo operator", "multi-SaaS", "agent runtime",
            "MCP", "neo-genesis", "wikidata-Q139569680", "yesol-heo-founder",
            "v1.0.0",
        ],
        github_url=GITHUB_REPO,
    ),
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def load_zenodo_token() -> str:
    if not TOKEN_ENV.exists():
        raise SystemExit(f"[FATAL] Token env not found: {TOKEN_ENV}")
    for line in TOKEN_ENV.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line.startswith("ZENODO_ACCESS_TOKEN="):
            return line.split("=", 1)[1].strip()
    raise SystemExit("[FATAL] ZENODO_ACCESS_TOKEN not in env file")


def load_ledger() -> dict[str, Any]:
    if LEDGER.exists():
        return json.loads(LEDGER.read_text(encoding="utf-8"))
    return {"minted_at": None, "dois": []}


def save_ledger(ledger: dict[str, Any]) -> None:
    LEDGER.parent.mkdir(parents=True, exist_ok=True)
    LEDGER.write_text(json.dumps(ledger, indent=2, ensure_ascii=False) + "\n",
                      encoding="utf-8")


def already_minted(ledger: dict[str, Any], slug: str) -> dict | None:
    for d in ledger.get("dois", []):
        if d.get("slug") == slug:
            return d
    return None


def http_request(
    url: str,
    *,
    method: str = "GET",
    token: str,
    json_body: dict | None = None,
    raw_body: bytes | None = None,
    content_type: str | None = None,
) -> tuple[int, dict | bytes]:
    headers = {"Authorization": f"Bearer {token}"}
    data: bytes | None = None
    if json_body is not None:
        data = json.dumps(json_body).encode("utf-8")
        headers["Content-Type"] = "application/json"
    elif raw_body is not None:
        data = raw_body
        if content_type:
            headers["Content-Type"] = content_type
    req = request.Request(url, data=data, method=method, headers=headers)
    try:
        with request.urlopen(req, timeout=60) as r:
            body = r.read()
            try:
                return r.status, json.loads(body)
            except Exception:
                return r.status, body
    except error.HTTPError as e:
        body = e.read()
        try:
            payload = json.loads(body)
        except Exception:
            payload = {"raw": body[:500].decode("utf-8", errors="replace")}
        return e.code, payload


def build_metadata(asset: Asset) -> dict:
    related = [
        {"identifier": GITHUB_REPO, "relation": "isPartOf", "scheme": "url"},
        {"identifier": WIKIDATA_PARENT, "relation": "references", "scheme": "url"},
    ]
    if asset.hf_url:
        related.append({"identifier": asset.hf_url, "relation": "isVersionOf",
                        "scheme": "url"})
    if asset.github_url and asset.upload_type == "software":
        related.append({"identifier": asset.github_url, "relation": "isSupplementTo",
                        "scheme": "url"})

    md = {
        "title": asset.title,
        "upload_type": asset.upload_type,
        "description": asset.description,
        "creators": [
            {"name": "Heo, Yesol", "affiliation": "Neo Genesis"},
            {"name": "Neo Genesis Lab", "affiliation": "Neo Genesis"},
        ],
        "access_right": "open",
        "license": "cc-by-4.0",
        "keywords": asset.keywords,
        "related_identifiers": related,
        "publication_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "communities": [],
        "language": "eng",
    }
    return md


def build_metadata_file(asset: Asset, doi_placeholder: str = "pending") -> bytes:
    payload = {
        "schema": "neo-genesis-zenodo-asset@1",
        "slug": asset.slug,
        "title": asset.title,
        "upload_type": asset.upload_type,
        "license": "CC-BY-4.0",
        "huggingface_url": asset.hf_url,
        "github_url": asset.github_url or GITHUB_REPO,
        "publisher": "Neo Genesis",
        "publisher_wikidata": "Q139569680",
        "creator": {
            "name": "Heo, Yesol",
            "wikidata": "Q139569708",
            "affiliation": "Neo Genesis",
        },
        "doi": doi_placeholder,
        "keywords": asset.keywords,
        "minted_at_utc": datetime.now(timezone.utc).isoformat(),
        "note": "Metadata-only Zenodo deposit; primary data lives on Hugging Face / GitHub.",
    }
    return (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")


def mint_one(asset: Asset, *, token: str, dry_run: bool) -> dict | None:
    print(f"\n[{asset.slug}] start ({asset.upload_type})")

    if dry_run:
        print(f"  [DRY-RUN] would deposit '{asset.title}'")
        return None

    # 1. create draft deposition
    status, body = http_request(
        f"{ZENODO_BASE}/deposit/depositions",
        method="POST",
        token=token,
        json_body={"metadata": build_metadata(asset)},
    )
    if status not in (200, 201):
        print(f"  [ERROR] create draft -> HTTP {status}: {body}")
        return None
    dep_id = body["id"]
    bucket = body["links"]["bucket"]
    publish_url = body["links"]["publish"]
    print(f"  draft id={dep_id} bucket={bucket}")

    # 2. upload metadata.json file via bucket PUT
    file_bytes = build_metadata_file(asset)
    put_url = f"{bucket}/metadata.json"
    status, body = http_request(
        put_url,
        method="PUT",
        token=token,
        raw_body=file_bytes,
        content_type="application/octet-stream",
    )
    if status not in (200, 201):
        print(f"  [ERROR] upload file -> HTTP {status}: {body}")
        return None
    print(f"  uploaded metadata.json ({len(file_bytes)} bytes)")

    # 3. publish (irreversible)
    status, body = http_request(publish_url, method="POST", token=token)
    if status not in (200, 202):
        print(f"  [ERROR] publish -> HTTP {status}: {body}")
        return None
    doi = body["doi"]
    record_url = body["links"]["record_html"] if "record_html" in body["links"] \
        else f"https://zenodo.org/records/{dep_id}"
    print(f"  PUBLISHED doi={doi} url={record_url}")

    return {
        "slug": asset.slug,
        "title": asset.title,
        "upload_type": asset.upload_type,
        "doi": doi,
        "record_id": dep_id,
        "url": record_url,
        "huggingface_url": asset.hf_url,
        "github_url": asset.github_url,
        "minted_at_utc": datetime.now(timezone.utc).isoformat(),
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true",
                        help="Print plan only — no API writes")
    parser.add_argument("--only", nargs="*",
                        help="Restrict to specific slugs")
    args = parser.parse_args()

    token = load_zenodo_token()
    ledger = load_ledger()
    print(f"Loaded ledger with {len(ledger.get('dois', []))} prior DOIs")

    target_slugs = set(args.only) if args.only else None
    new_records: list[dict] = []
    for asset in ASSETS:
        if target_slugs is not None and asset.slug not in target_slugs:
            continue
        existing = already_minted(ledger, asset.slug)
        if existing:
            print(f"[{asset.slug}] SKIP — already minted: {existing.get('doi')}")
            continue
        record = mint_one(asset, token=token, dry_run=args.dry_run)
        if record:
            new_records.append(record)
            ledger.setdefault("dois", []).append(record)
            ledger["minted_at"] = datetime.now(timezone.utc).isoformat()
            save_ledger(ledger)
        # gentle pacing
        time.sleep(2)

    print(f"\nMinted {len(new_records)} new DOIs in this run.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
