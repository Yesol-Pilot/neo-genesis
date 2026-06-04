"""Neo Genesis -- External signal fetcher.

biz:ExternalSignal 클래스 + 자동 fetch (yfinance + aideadlin.es).

Sources:
1. **yfinance** (no API key): KOSPI / S&P 500 / QQQ / USD-KRW — D2 ETF 결정 지표
2. **aideadlin.es** (public JSON): NeurIPS / ICLR / ICML / KDD 등 학회 deadline — Research IP timing
3. (TODO v0.2) HN / Reddit / Twitter sentiment for Neo Genesis brand mentions

Usage:
    python scripts/ontology/business/external_signal_fetcher.py [--dry-run] [--source market|conference|all]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
BIZ_DIR = REPO_ROOT / ".agent" / "ontology" / "business"
NODES_PATH = BIZ_DIR / "nodes.jsonl"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def fetch_market_signals() -> list[dict]:
    """KOSPI / S&P 500 / QQQ / USD-KRW via yfinance."""
    try:
        import yfinance as yf
    except ImportError:
        print("[ERROR] pip install yfinance", file=sys.stderr)
        return []

    tickers = [
        ("^KS11", "KOSPI", "stock_index_kr", "D2 ETF korea-side"),
        ("^GSPC", "S&P 500", "stock_index_us", "D2 ETF us-side primary"),
        ("^IXIC", "NASDAQ", "stock_index_us", "D2 ETF QQQ underlying"),
        ("QQQ", "Invesco QQQ", "etf", "D2 ETF direct"),
        ("KRW=X", "USD-KRW", "fx", "달러원 — D2 ETF 진입 시점 결정"),
    ]
    signals = []
    for symbol, label, kind, rationale in tickers:
        try:
            t = yf.Ticker(symbol)
            # info or fast_info for latest price
            hist = t.history(period="5d")
            if hist.empty:
                continue
            latest_close = float(hist["Close"].iloc[-1])
            prev_close = float(hist["Close"].iloc[-2]) if len(hist) >= 2 else None
            pct_change = (
                round((latest_close - prev_close) / prev_close * 100, 2)
                if prev_close else None
            )
            signals.append({
                "id": f"neo://biz/signal/market-{symbol.replace('^','').replace('=','').lower()}",
                "rdf_type": "biz:ExternalSignal",
                "kind": "market",
                "subkind": kind,
                "label": f"{label} ({symbol})",
                "symbol": symbol,
                "latest_close": latest_close,
                "prev_close": prev_close,
                "pct_change_1d": pct_change,
                "rationale": rationale,
                "observed_at": now_iso(),
                "markings": ["internal"],
                "provenance": "observed_from_live_source",
                "provenance_source": "yfinance live quote",
                "created_at": now_iso(),
                "updated_at": now_iso(),
            })
        except Exception as e:
            print(f"[WARN] yfinance fetch failed for {symbol}: {e}", file=sys.stderr)

    return signals


CONFERENCE_DEADLINES_KNOWN = [
    # (venue, year, deadline, sub, place, link, source_note)
    # Sourced from official conf websites. v0.1: hardcoded baseline.
    # v0.2 trigger: aideadlin.es API restored OR papers-with-code deadlines API
    ("NeurIPS", 2026, "2026-05-22", "main", "Vancouver / virtual",
     "https://neurips.cc/", "EthicaAI Melting Pot target venue"),
    ("ICLR", 2027, "2026-10-01", "main", "Singapore",
     "https://iclr.cc/", "WhyLab causal inference candidate"),
    ("ICML", 2026, "2026-01-30", "main", "Vienna",
     "https://icml.cc/", "Past — already deadline"),
    ("KDD", 2026, "2026-02-08", "main", "Toronto",
     "https://www.kdd.org/", "Past — already deadline"),
    ("ACL", 2026, "2026-02-15", "main", "Vienna",
     "https://aclweb.org/", "Past — KoreanLLM AO-1 next year candidate"),
    ("EMNLP", 2026, "2026-06-13", "main", "Suzhou",
     "https://2026.emnlp.org/", "KoreanLLM AO-1 candidate"),
    ("AAAI", 2026, "2026-08-01", "main", "Singapore",
     "https://aaai.org/", "broad AI venue"),
    ("NAACL", 2027, "2026-11-15", "main", "TBD",
     "https://naacl.org/", "Korean NLP secondary venue"),
]


def fetch_conference_deadlines() -> list[dict]:
    """AI conference deadlines.

    v0.1: hardcoded baseline (aideadlin.es 404 fallback).
    v0.2 trigger: dynamic source — aideadlin.es / papers-with-code / GitHub
    awesome-deadlines repo.
    """
    today = dt.date.today()
    horizon = today + dt.timedelta(days=365)
    past_grace = today - dt.timedelta(days=14)  # show recent past 2주 for awareness

    signals = []
    for venue, year, dl_str, sub, place, link, note in CONFERENCE_DEADLINES_KNOWN:
        try:
            deadline_date = dt.date.fromisoformat(dl_str)
        except Exception:
            continue
        if not (past_grace <= deadline_date <= horizon):
            continue
        days_until = (deadline_date - today).days
        signals.append({
            "id": f"neo://biz/signal/conf-{venue.lower()}-{year}",
            "rdf_type": "biz:ExternalSignal",
            "kind": "conference_deadline",
            "subkind": venue,
            "label": f"{venue} {year} {sub} deadline",
            "venue": venue,
            "year": year,
            "deadline_date": dl_str,
            "days_until": days_until,
            "is_past": days_until < 0,
            "place": place,
            "link": link,
            "rationale": note,
            "source": "hardcoded_v0.1",
            "observed_at": now_iso(),
            "markings": ["public"],
            "provenance": "hardcoded_strategy_lead_seed",
            "provenance_source": "AI conference deadline table (수동 입력, 공식 CFP 근거 — 정기 갱신 필요)",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })

    signals.sort(key=lambda s: s["deadline_date"])
    return signals


def load_nodes() -> list[dict]:
    if not NODES_PATH.exists():
        return []
    return [json.loads(l) for l in NODES_PATH.read_text(encoding="utf-8").splitlines() if l.strip()]


def upsert_signals(new_signals: list[dict], dry_run: bool = False) -> dict:
    """Replace all existing biz:ExternalSignal nodes with fresh ones."""
    if not NODES_PATH.exists():
        if dry_run:
            return {"status": "DRY_RUN_NO_NODES", "new_count": len(new_signals)}
        BIZ_DIR.mkdir(parents=True, exist_ok=True)
        NODES_PATH.touch()
    nodes = load_nodes()
    # Drop existing ExternalSignal nodes
    kept = [n for n in nodes if n.get("rdf_type") != "biz:ExternalSignal"]
    final = kept + new_signals
    if dry_run:
        return {"status": "DRY_RUN", "old_count": len(nodes) - len(kept),
                "new_count": len(new_signals), "total_after": len(final)}
    with NODES_PATH.open("w", encoding="utf-8") as f:
        for n in final:
            f.write(json.dumps(n, ensure_ascii=False) + "\n")
    return {"status": "WRITTEN", "removed_old": len(nodes) - len(kept),
            "added_new": len(new_signals), "total_after": len(final)}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--source", default="all", choices=["all", "market", "conference"])
    args = parser.parse_args()

    all_signals = []
    if args.source in ("all", "market"):
        ms = fetch_market_signals()
        print(f"[market] fetched {len(ms)} signals", file=sys.stderr)
        all_signals.extend(ms)
    if args.source in ("all", "conference"):
        cs = fetch_conference_deadlines()
        print(f"[conference] fetched {len(cs)} signals", file=sys.stderr)
        all_signals.extend(cs)

    result = upsert_signals(all_signals, dry_run=args.dry_run)
    summary = {
        "fetched_at": now_iso(),
        "total_signals_fetched": len(all_signals),
        "upsert_result": result,
        "samples": all_signals[:3],
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
