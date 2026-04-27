"""
Neo Genesis GEO Citation 일일 / 주간 / 월간 리포트 생성

사용:
    python scripts/geo_measure/aggregate_report.py              # 어제 1일
    python scripts/geo_measure/aggregate_report.py --window 7   # 최근 7일
    python scripts/geo_measure/aggregate_report.py --window 28  # 최근 28일

출력: JSON (stdout) + Markdown (logs/geo_measure/report-YYYY-MM-DD.md)
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from datetime import datetime, timedelta, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent
DB_FILE = ROOT / "citations.sqlite3"
LOG_DIR = Path(__file__).resolve().parents[2] / "logs" / "geo_measure"
LOG_DIR.mkdir(parents=True, exist_ok=True)


def aggregate(window_days: int) -> dict:
    if not DB_FILE.exists():
        return {"error": "no measurements yet — run measure_citations.py first"}
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row
    since = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()

    rows = conn.execute(
        """SELECT provider, prompt_category,
                  COUNT(*) AS calls,
                  SUM(CASE WHEN error IS NOT NULL THEN 1 ELSE 0 END) AS errors,
                  SUM(CASE WHEN mention_neo_genesis > 0 OR mention_sbu_total > 0 THEN 1 ELSE 0 END) AS mentions,
                  SUM(mention_neo_genesis) AS sum_brand,
                  SUM(mention_domain_root) AS sum_domain_root,
                  SUM(mention_domain_subs) AS sum_domain_subs,
                  SUM(mention_sbu_total) AS sum_sbu,
                  SUM(mention_founder) AS sum_founder,
                  SUM(CASE WHEN sentiment='positive' THEN 1 ELSE 0 END) AS pos,
                  SUM(CASE WHEN sentiment='neutral' THEN 1 ELSE 0 END) AS neu,
                  SUM(CASE WHEN sentiment='negative' THEN 1 ELSE 0 END) AS neg
           FROM measurements
           WHERE timestamp >= ?
           GROUP BY provider, prompt_category
           ORDER BY provider, prompt_category""",
        (since,),
    ).fetchall()

    by_provider: dict = {}
    overall = {
        "calls": 0, "errors": 0, "mentions": 0,
        "sum_brand": 0, "sum_domain_root": 0, "sum_domain_subs": 0,
        "sum_sbu": 0, "sum_founder": 0,
        "pos": 0, "neu": 0, "neg": 0,
    }
    for r in rows:
        d = dict(r)
        prov = d.pop("provider")
        cat = d.pop("prompt_category")
        by_provider.setdefault(prov, {})[cat] = d
        for k in overall:
            overall[k] += d.get(k, 0) or 0

    citation_rate = (
        overall["mentions"] / overall["calls"] if overall["calls"] else 0
    )

    return {
        "window_days": window_days,
        "since": since,
        "overall": overall,
        "citation_rate": round(citation_rate, 4),
        "by_provider": by_provider,
    }


def to_markdown(report: dict) -> str:
    if "error" in report:
        return f"# GEO Report\n\n{report['error']}\n"
    o = report["overall"]
    lines = [
        f"# GEO Citation Report (지난 {report['window_days']}일)",
        f"",
        f"기준 시점: {report['since']}",
        f"",
        f"## Overall",
        f"- 총 호출: **{o['calls']}**",
        f"- 에러: {o['errors']}",
        f"- Neo Genesis 또는 SBU mention 발생 응답: **{o['mentions']}** ({report['citation_rate']*100:.1f}%)",
        f"- Neo Genesis 브랜드 mention 합계: {o['sum_brand']}",
        f"- 루트 도메인 mention 합계: {o['sum_domain_root']}",
        f"- SBU 도메인 mention 합계: {o['sum_domain_subs']}",
        f"- SBU 브랜드 mention 합계: {o['sum_sbu']}",
        f"- 창업자 mention 합계: {o['sum_founder']}",
        f"- Sentiment: positive {o['pos']} / neutral {o['neu']} / negative {o['neg']}",
        f"",
        f"## Provider × Category",
    ]
    for prov, cats in report["by_provider"].items():
        lines.append(f"### {prov}")
        lines.append("| Category | Calls | Errors | Mentions | Brand | Domain | SBU | Founder | Pos/Neu/Neg |")
        lines.append("|---|---|---|---|---|---|---|---|---|")
        for cat, d in cats.items():
            lines.append(
                f"| {cat} | {d['calls']} | {d['errors']} | {d['mentions']} | "
                f"{d['sum_brand']} | {d['sum_domain_root'] + d['sum_domain_subs']} | "
                f"{d['sum_sbu']} | {d['sum_founder']} | "
                f"{d['pos']}/{d['neu']}/{d['neg']} |"
            )
        lines.append("")
    return "\n".join(lines)


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--window", type=int, default=1)
    args = parser.parse_args()

    report = aggregate(args.window)
    md = to_markdown(report)
    out_md = LOG_DIR / f"report-{datetime.now().strftime('%Y-%m-%d')}-w{args.window}.md"
    out_md.write_text(md, encoding="utf-8")

    print(json.dumps(report, ensure_ascii=False, indent=2))
    print(f"\nMarkdown written to: {out_md}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
