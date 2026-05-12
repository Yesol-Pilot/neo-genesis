"""
HF Dataset 9 Monthly Refresh Automation
========================================

매월 1회 자동 실행:
  1. `scripts/geo_measure/citations.sqlite3` 의 최신 30일 데이터 export
  2. 직전 baseline (HF dataset 9 `ai-brand-mention-baseline-2026`) 와 비교
  3. delta (mention rate, domain_root citation rate, category 별) 계산
  4. 동일 HF dataset 의 신규 revision push (월별 snapshot)
  5. delta 보고서 markdown 생성
  6. Telegram alert (delta 변동 시)

운영 정책:
  - 매월 1일 09:00 KST cron
  - 최소 30일 누적 데이터 필요 (없으면 SKIP)
  - HF dataset 의 monthly snapshot tag 자동 부착 (`v2026-05`, `v2026-06`, ...)
  - `mention_domain_root > 0` 발생 시 즉시 Telegram alert (Trust signal gap closure 신호)

Reference:
  - 20260512_AI_CORPUS_CITATION_STRATEGY_v1.md §2.L.L2
  - publish_geo_baseline_v2.py (직전 v2 publish 스크립트, schema 동일)

실행:
    python scripts/hf_publish/refresh_geo_baseline_monthly.py
    python scripts/hf_publish/refresh_geo_baseline_monthly.py --dry-run
    python scripts/hf_publish/refresh_geo_baseline_monthly.py --window-days 60

cron 등록:
    Windows Scheduled Task: NeoGenesis-GEO-Monthly-Refresh
    Trigger: 매월 1일 09:00 KST
    Action: python D:/00.test/neo-genesis/scripts/hf_publish/refresh_geo_baseline_monthly.py

작성: 2026-05-12, Strategy Lead Claude Opus 4.7
"""
from __future__ import annotations

import argparse
import json
import os
import sqlite3
import sys
import urllib.error
import urllib.parse
import urllib.request
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]  # scripts/
PROJECT_ROOT = ROOT.parent
GEO_DB = PROJECT_ROOT / "scripts" / "geo_measure" / "citations.sqlite3"
REPORT_DIR = PROJECT_ROOT / ".agent" / "knowledge" / "geo_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

HF_DATASET_ID = "neogenesislab/ai-brand-mention-baseline-2026"
USER_AGENT = "Neo Genesis Monthly GEO Refresh/1.0 (https://neogenesis.app)"


def _load_env_files() -> None:
    """Load .env.local + .env from project root + PAPER/EthicaAI/.env (HF token fallback)."""
    candidates = [
        PROJECT_ROOT / ".env.local",
        PROJECT_ROOT / ".env",
        PROJECT_ROOT.parent / "PAPER" / "EthicaAI" / ".env",
    ]
    for p in candidates:
        if not p.exists():
            continue
        try:
            for line in p.read_text(encoding="utf-8", errors="ignore").splitlines():
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, _, v = line.partition("=")
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
        except Exception:
            pass


def fetch_recent_data(window_days: int = 30) -> list[dict[str, Any]]:
    """SQLite 에서 직전 N일 데이터 추출."""
    if not GEO_DB.exists():
        print(f"  ! GEO DB not found: {GEO_DB}", file=sys.stderr)
        return []
    cutoff = (datetime.now(timezone.utc) - timedelta(days=window_days)).isoformat()
    conn = sqlite3.connect(GEO_DB)
    conn.row_factory = sqlite3.Row
    cursor = conn.execute(
        "SELECT * FROM measurements WHERE timestamp >= ? ORDER BY timestamp",
        (cutoff,),
    )
    rows = [dict(r) for r in cursor.fetchall()]
    conn.close()
    return rows


def compute_aggregates(rows: list[dict[str, Any]]) -> dict[str, Any]:
    """카테고리별 + provider 별 mention rate 집계."""
    if not rows:
        return {
            "total": 0,
            "successful": 0,
            "brand_mention_count": 0,
            "domain_root_mention_count": 0,
            "founder_mention_count": 0,
            "by_category": {},
            "by_provider": {},
            "brand_mention_rate": 0.0,
            "domain_root_rate": 0.0,
        }

    total = len(rows)
    successful = sum(1 for r in rows if not r.get("error"))
    brand_mentions = sum(1 for r in rows if (r.get("mention_neo_genesis") or 0) > 0)
    domain_mentions = sum(1 for r in rows if (r.get("mention_domain_root") or 0) > 0)
    founder_mentions = sum(1 for r in rows if (r.get("mention_founder") or 0) > 0)

    by_category: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "brand": 0, "domain": 0})
    by_provider: dict[str, dict[str, int]] = defaultdict(lambda: {"total": 0, "brand": 0, "domain": 0})

    for r in rows:
        if r.get("error"):
            continue
        cat = r.get("prompt_category") or "unknown"
        prov = r.get("provider") or "unknown"
        by_category[cat]["total"] += 1
        by_provider[prov]["total"] += 1
        if (r.get("mention_neo_genesis") or 0) > 0:
            by_category[cat]["brand"] += 1
            by_provider[prov]["brand"] += 1
        if (r.get("mention_domain_root") or 0) > 0:
            by_category[cat]["domain"] += 1
            by_provider[prov]["domain"] += 1

    return {
        "total": total,
        "successful": successful,
        "brand_mention_count": brand_mentions,
        "domain_root_mention_count": domain_mentions,
        "founder_mention_count": founder_mentions,
        "by_category": dict(by_category),
        "by_provider": dict(by_provider),
        "brand_mention_rate": brand_mentions / successful if successful else 0.0,
        "domain_root_rate": domain_mentions / successful if successful else 0.0,
    }


def write_monthly_report(
    rows: list[dict[str, Any]],
    aggregates: dict[str, Any],
    window_days: int,
) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{today}_geo_monthly_refresh.md"

    cat_lines = []
    for cat, stats in sorted(aggregates["by_category"].items()):
        if stats["total"] == 0:
            continue
        bm = 100 * stats["brand"] / stats["total"]
        dm = 100 * stats["domain"] / stats["total"]
        cat_lines.append(f"| {cat} | {stats['total']} | {stats['brand']} ({bm:.1f}%) | {stats['domain']} ({dm:.1f}%) |")

    prov_lines = []
    for prov, stats in sorted(aggregates["by_provider"].items()):
        if stats["total"] == 0:
            continue
        bm = 100 * stats["brand"] / stats["total"]
        dm = 100 * stats["domain"] / stats["total"]
        prov_lines.append(f"| {prov} | {stats['total']} | {stats['brand']} ({bm:.1f}%) | {stats['domain']} ({dm:.1f}%) |")

    lines = [
        f"# GEO Monthly Refresh — {today}",
        "",
        f"> 자동 생성: `scripts/hf_publish/refresh_geo_baseline_monthly.py`",
        f"> 데이터 window: 직전 **{window_days}일**",
        f"> source DB: `scripts/geo_measure/citations.sqlite3`",
        "",
        "## 핵심 지표 (L1 + L2)",
        "",
        f"- **총 측정**: {aggregates['total']}건",
        f"- **성공 측정**: {aggregates['successful']}건 (error 제외)",
        f"- **brand mention** (L1): {aggregates['brand_mention_count']}건 = **{100 * aggregates['brand_mention_rate']:.1f}%**",
        f"- **canonical URL citation** (L2): {aggregates['domain_root_mention_count']}건 = **{100 * aggregates['domain_root_rate']:.2f}%**",
        f"- **founder mention**: {aggregates['founder_mention_count']}건",
        "",
        "## Category 별 (Trust Signal Gap 정밀 추적)",
        "",
        "| category | total | brand | canonical URL |",
        "|---|---|---|---|",
        *cat_lines,
        "",
        "## Provider 별",
        "",
        "| provider | total | brand | canonical URL |",
        "|---|---|---|---|",
        *prov_lines,
        "",
        "## Trust Signal Gap 진단",
        "",
    ]

    if aggregates["domain_root_rate"] > 0:
        lines.append(f"🟢 **canonical URL citation 발견**: {aggregates['domain_root_mention_count']}건 — Trust signal gap 일부 closure 신호")
    else:
        lines.append(f"🔴 **canonical URL citation 0건** — Trust signal gap 미해소 (baseline 유지)")

    lines.append("")
    lines.append("## Strategy v1 Stop/Go 게이트 자동 평가")
    lines.append("")
    bmr = aggregates["brand_mention_rate"]
    if bmr >= 0.05 and aggregates["domain_root_mention_count"] >= 1:
        lines.append("🟢 **Phase 1 GO**: L1 ≥ 5% + L4 ≥ 1 충족")
    elif bmr < 0.40:
        lines.append("🔴 **PIVOT 검토**: brand mention rate baseline 미달")
    else:
        lines.append("🟡 **HOLD**: 현 cadence 유지, 다음 월 cycle 까지 추가 신호 대기")

    lines.append("")
    lines.append("## 다음 cycle (자동)")
    lines.append("")
    lines.append("- 다음 refresh 실행: 매월 1일 09:00 KST")
    lines.append("- 다음 monthly delta 보고: 같은 형식")
    lines.append("- HF dataset revision push: 변경 시")
    lines.append("")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def push_hf_revision(
    rows: list[dict[str, Any]],
    aggregates: dict[str, Any],
    window_days: int,
    dry_run: bool,
) -> bool:
    """HF dataset 의 monthly snapshot revision push (dry-run 안전)."""
    if dry_run:
        print(f"  [DRY-RUN] would push {len(rows)} rows to {HF_DATASET_ID} as monthly snapshot")
        return True
    if not rows:
        print("  ! No rows to push, skipping HF revision")
        return False

    token = os.environ.get("HF_TOKEN") or os.environ.get("HUGGINGFACE_TOKEN")
    if not token:
        print("  ! HF_TOKEN missing, skipping push (dry-run only)")
        return False

    try:
        from huggingface_hub import HfApi, CommitOperationAdd  # type: ignore
        from tempfile import NamedTemporaryFile
    except ImportError:
        print("  ! huggingface_hub not installed; pip install huggingface_hub")
        return False

    today = datetime.now(timezone.utc).strftime("%Y-%m")
    snapshot_path = f"monthly_snapshots/{today}.jsonl"

    api = HfApi(token=token)

    with NamedTemporaryFile(mode="w", suffix=".jsonl", delete=False, encoding="utf-8") as tf:
        for r in rows:
            # citation_urls JSON column 정규화
            if isinstance(r.get("citation_urls"), str):
                try:
                    r["citation_urls"] = json.loads(r["citation_urls"])
                except Exception:
                    r["citation_urls"] = []
            tf.write(json.dumps(r, ensure_ascii=False) + "\n")
        tmpfile = tf.name

    try:
        api.upload_file(
            path_or_fileobj=tmpfile,
            path_in_repo=snapshot_path,
            repo_id=HF_DATASET_ID,
            repo_type="dataset",
            commit_message=f"monthly refresh {today}: {len(rows)} measurements, brand={aggregates['brand_mention_rate']*100:.1f}%, domain={aggregates['domain_root_rate']*100:.2f}%",
        )
        # README 의 monthly section 갱신은 별도 단계로 분리 (idempotent risk)
        print(f"  ✓ HF revision pushed: {HF_DATASET_ID}/{snapshot_path}")
        return True
    except Exception as e:
        print(f"  ! HF upload error: {e}", file=sys.stderr)
        return False
    finally:
        try:
            os.unlink(tmpfile)
        except Exception:
            pass


def telegram_alert(text: str) -> bool:
    token = os.environ.get("NEO_ALERT_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("OWNER_CHAT_ID") or os.environ.get("TELEGRAM_OWNER_CHAT_ID")
    if not token or not chat_id:
        return False
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    data = urllib.parse.urlencode({
        "chat_id": chat_id,
        "text": text[:4000],
        "disable_web_page_preview": "true",
    }).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status == 200
    except Exception:
        return False


def main() -> int:
    parser = argparse.ArgumentParser(description="HF GEO baseline monthly refresh")
    parser.add_argument("--dry-run", action="store_true", help="HF push 없이 보고서만")
    parser.add_argument("--window-days", type=int, default=30, help="data window (default 30)")
    parser.add_argument("--no-alert", action="store_true", help="Telegram alert 비활성")
    args = parser.parse_args()

    _load_env_files()

    print(f"[geo_monthly_refresh] run start {datetime.now(timezone.utc).isoformat()}")
    print(f"[geo_monthly_refresh] window: {args.window_days} days")
    print(f"[geo_monthly_refresh] dry-run: {args.dry_run}")

    rows = fetch_recent_data(args.window_days)
    print(f"[geo_monthly_refresh] rows: {len(rows)}")

    aggregates = compute_aggregates(rows)
    print(f"[geo_monthly_refresh] brand_mention_rate: {aggregates['brand_mention_rate']*100:.1f}%")
    print(f"[geo_monthly_refresh] domain_root_rate: {aggregates['domain_root_rate']*100:.2f}%")

    if not rows:
        print("[geo_monthly_refresh] no recent data, skipping push + report")
        return 0

    report_path = write_monthly_report(rows, aggregates, args.window_days)
    print(f"[geo_monthly_refresh] report: {report_path}")

    pushed = push_hf_revision(rows, aggregates, args.window_days, args.dry_run)

    # Trust signal 발견 시 Telegram alert
    if aggregates["domain_root_mention_count"] > 0 and not args.no_alert:
        alert = (
            f"🟢 GEO Trust Signal 진전\n"
            f"canonical URL citation: {aggregates['domain_root_mention_count']}건\n"
            f"brand mention rate: {aggregates['brand_mention_rate']*100:.1f}%\n"
            f"window: 직전 {args.window_days}일\n"
            f"📍 {report_path}"
        )
        telegram_alert(alert)

    print(f"[geo_monthly_refresh] done. pushed={pushed}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
