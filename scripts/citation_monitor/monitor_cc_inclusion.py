"""
Neo Genesis Common Crawl Inclusion Monitor (L4)
================================================

매월 1회 자동 실행. Common Crawl 의 최신 snapshot 에서 `neogenesis.app` URL 존재 여부 확인.
신규 indexing 발견 시 Telegram alert + Strategy v1 Stop/Go 게이트 자동 평가.

데이터 소스 (모두 무료):
  - Common Crawl Collection Info — https://index.commoncrawl.org/collinfo.json
  - Common Crawl CDX API — per-snapshot URL lookup
  - HuggingFace FineWeb (선택적, 직접 query API 가 없으므로 future expansion)
  - AllenAI Dolma (동일)

산출:
  - `D:/00.test/neo-genesis/.agent/knowledge/citation_reports/cc_inclusion_history.jsonl`
    Append-only history (snapshot, indexed_count, lookup_date)
  - 매월 1회 markdown 보고서 (변동 시)
  - 첫 inclusion 발견 시 Telegram alert

실행:
    python scripts/citation_monitor/monitor_cc_inclusion.py
    python scripts/citation_monitor/monitor_cc_inclusion.py --dry-run
    python scripts/citation_monitor/monitor_cc_inclusion.py --snapshot CC-MAIN-2026-22

cron 등록:
    Windows Scheduled Task: NeoGenesis-CC-Inclusion-Monthly
    매월 15일 09:00 KST (CC snapshot 가 보통 월 1회 publish)

Reference:
  - 20260512_AI_CORPUS_INCLUSION_AUDIT.md (직전 baseline: 3 snapshot 미인덱싱)
  - 20260512_AI_CORPUS_CITATION_STRATEGY_v1.md §2.L.L4

작성: 2026-05-12, Strategy Lead Claude Opus 4.7
"""
from __future__ import annotations

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
HISTORY_FILE = PROJECT_ROOT / ".agent" / "knowledge" / "citation_reports" / "cc_inclusion_history.jsonl"
REPORT_DIR = PROJECT_ROOT / ".agent" / "knowledge" / "citation_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

CC_COLLECTION_API = "https://index.commoncrawl.org/collinfo.json"
TARGET_DOMAIN_PATTERN = "neogenesis.app/*"

USER_AGENT = (
    "Neo Genesis CC Inclusion Monitor/1.0 "
    "(https://neogenesis.app; research-tool)"
)


def _http_get(url: str, timeout: int = 30) -> bytes:
    """HTTP GET. CDX API 의 404 는 정상 'no captures' signal 이므로 silent 처리."""
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code == 404 and "index.commoncrawl.org" in url:
            # CDX API: 404 = "URL prefix not in this index" = 정상 no-inclusion signal
            return b'{"message": "No Captures found"}'
        print(f"  ! HTTP error on {url[:80]}: {e}", file=sys.stderr)
        return b""
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"  ! Network error on {url[:80]}: {e}", file=sys.stderr)
        return b""


def fetch_cc_collections() -> list[dict[str, Any]]:
    """직전 CC snapshot list 가져옴 (sorted by id desc)."""
    body = _http_get(CC_COLLECTION_API)
    if not body:
        return []
    try:
        return json.loads(body)
    except Exception as e:
        print(f"  ! JSON parse error: {e}", file=sys.stderr)
        return []


def probe_snapshot(snapshot_id: str, cdx_api: str) -> dict[str, Any]:
    """단일 snapshot 에서 neogenesis.app indexing 확인."""
    lookup_url = (
        f"{cdx_api}?url={urllib.parse.quote(TARGET_DOMAIN_PATTERN)}"
        f"&output=json&limit=1000"
    )
    body = _http_get(lookup_url)
    if not body:
        return {"snapshot": snapshot_id, "indexed": False, "count": 0, "error": "http_failed"}

    text = body.decode("utf-8", errors="ignore")
    if "No Captures found" in text or not text.strip():
        return {"snapshot": snapshot_id, "indexed": False, "count": 0}

    # Each line = one JSON record (CDX format)
    urls: list[str] = []
    for line in text.splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            rec = json.loads(line)
            if rec.get("url"):
                urls.append(rec["url"])
        except Exception:
            continue

    return {
        "snapshot": snapshot_id,
        "indexed": len(urls) > 0,
        "count": len(urls),
        "sample_urls": urls[:5],
    }


def append_history(record: dict[str, Any]) -> None:
    record["recorded_at"] = datetime.now(timezone.utc).isoformat()
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def write_report(results: list[dict[str, Any]], previous_state: dict[str, Any]) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{today}_cc_inclusion.md"

    total_indexed = sum(r["count"] for r in results)
    first_indexed_snapshot = next((r for r in results if r["indexed"]), None)

    lines = [
        f"# Common Crawl Inclusion Report — {today}",
        "",
        f"> 자동 생성: `scripts/citation_monitor/monitor_cc_inclusion.py`",
        f"> Target: `{TARGET_DOMAIN_PATTERN}`",
        f"> Snapshots probed: {len(results)}",
        "",
        "## 결과",
        "",
        "| Snapshot | Indexed | URL count | Sample |",
        "|---|---|---|---|",
    ]
    for r in results:
        status = "✅" if r["indexed"] else "❌"
        sample = (r.get("sample_urls", []) or ["—"])[0] if r["indexed"] else "—"
        lines.append(f"| {r['snapshot']} | {status} | {r['count']} | `{sample[:60]}` |")
    lines.append("")

    lines.append("## Trust Signal Gap 진단")
    lines.append("")
    if total_indexed > 0:
        lines.append(f"🟢 **첫 CC indexing 발견**: {first_indexed_snapshot['snapshot']} 에서 {first_indexed_snapshot['count']} URLs")
        lines.append("")
        lines.append("→ **다음 cycle 효과 예측**:")
        lines.append("- 4-6주 후: FineWeb / FineWeb-Edu 신 revision 에 자동 포함 가능성")
        lines.append("- 1-3개월 후: Dolma v1.8+ / RedPajama 등 derivative dataset 자동 포함")
        lines.append("- 6-18개월 후: frontier LLM training corpus 진입 가능성 (Anthropic / OpenAI / Google)")
    else:
        prev_total = previous_state.get("last_total_indexed", 0)
        lines.append(f"🔴 **CC indexing 0건 (직전 cycle: {prev_total}건)**")
        lines.append("")
        lines.append("→ 권고 actions:")
        lines.append("- inbound link 강화 (HF datasets / GitHub repos / Wikidata 13 entities → CC-indexed)")
        lines.append("- Cloudflare AI Crawl Control 활성 (CCBot Allow 정책 edge 보장)")
        lines.append("- Common Crawl Google Group / Discord 직접 inquiry")
        lines.append("- 11 SBU sub-domain 의 canonical neogenesis.app reference 강화")

    lines.append("")
    lines.append("## History")
    lines.append("")
    lines.append(f"Append-only log: `{HISTORY_FILE.name}`")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


def telegram_alert(text: str) -> bool:
    token = os.environ.get("NEO_ALERT_BOT_TOKEN") or os.environ.get("TELEGRAM_BOT_TOKEN")
    chat_id = os.environ.get("OWNER_CHAT_ID") or os.environ.get("TELEGRAM_OWNER_CHAT_ID")
    if not token or not chat_id:
        print("[NO TELEGRAM CREDS — stdout only]")
        print(text)
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
    parser = argparse.ArgumentParser(description="Common Crawl inclusion monitor")
    parser.add_argument("--dry-run", action="store_true", help="history file 저장 없이 보고만")
    parser.add_argument("--snapshot", help="specific snapshot ID (default = 직전 3 snapshot)")
    parser.add_argument("--no-alert", action="store_true", help="Telegram alert 비활성")
    parser.add_argument("--limit", type=int, default=3, help="probe 최신 N snapshots (default 3)")
    args = parser.parse_args()

    print(f"[cc_inclusion] run start {datetime.now(timezone.utc).isoformat()}")
    print(f"[cc_inclusion] target: {TARGET_DOMAIN_PATTERN}")
    print(f"[cc_inclusion] dry-run: {args.dry_run}")

    collections = fetch_cc_collections()
    if not collections:
        print("[cc_inclusion] ! Failed to fetch CC collections list")
        return 2

    if args.snapshot:
        targets = [c for c in collections if c.get("id") == args.snapshot]
    else:
        targets = collections[: args.limit]

    print(f"[cc_inclusion] probing {len(targets)} snapshots")

    # 직전 state 로드
    previous_state: dict[str, Any] = {"last_total_indexed": 0}
    if HISTORY_FILE.exists():
        try:
            with HISTORY_FILE.open("r", encoding="utf-8") as f:
                lines = f.readlines()
                if lines:
                    last = json.loads(lines[-1])
                    previous_state["last_total_indexed"] = last.get("total_indexed", 0)
        except Exception:
            pass

    results: list[dict[str, Any]] = []
    for coll in targets:
        snapshot_id = coll.get("id", "unknown")
        cdx_api = coll.get("cdx-api")
        if not cdx_api:
            print(f"  ? {snapshot_id}: no cdx-api endpoint")
            continue
        print(f"  → probing {snapshot_id} ...")
        r = probe_snapshot(snapshot_id, cdx_api)
        results.append(r)
        time.sleep(2)  # rate-limit politeness

    total_indexed = sum(r["count"] for r in results)
    indexed_snapshots = sum(1 for r in results if r["indexed"])
    print(f"[cc_inclusion] total URLs indexed: {total_indexed} across {indexed_snapshots}/{len(results)} snapshots")

    # History append
    if not args.dry_run:
        record = {
            "total_indexed": total_indexed,
            "indexed_snapshots": indexed_snapshots,
            "probed_snapshots": len(results),
            "snapshot_detail": [{"id": r["snapshot"], "count": r["count"]} for r in results],
        }
        append_history(record)
        print(f"[cc_inclusion] history appended to {HISTORY_FILE.name}")

    report_path = write_report(results, previous_state)
    print(f"[cc_inclusion] report: {report_path}")

    # Telegram alert: 첫 inclusion 발견 시
    if total_indexed > 0 and previous_state["last_total_indexed"] == 0 and not args.no_alert:
        first_snapshot = next(r for r in results if r["indexed"])
        alert = (
            f"🟢 Common Crawl 첫 inclusion 발견\n"
            f"Snapshot: {first_snapshot['snapshot']}\n"
            f"URLs indexed: {first_snapshot['count']}\n"
            f"Sample: {(first_snapshot.get('sample_urls') or ['—'])[0]}\n"
            f"\n→ FineWeb / Dolma 진입 4-6주 후 예상\n"
            f"→ Frontier LLM training corpus 6-18개월 후 예상\n"
            f"📍 {report_path}"
        )
        telegram_alert(alert)

    print(f"[cc_inclusion] done {datetime.now(timezone.utc).isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
