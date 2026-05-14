"""
Neo Genesis Blind Review Outcome Monitor
=========================================

매주 1회 자동 실행. 블라인드 심사 진행 중인 manuscripts 의 venue 결과 발표 시점을
자동 감지 + Telegram alert. 발견 시 자동 unhold queue 박제.

현재 추적 대상 (2026-05-12 기준):
  - EthicaAI: Mixed-Safe Boundary-Consistent Evidence (NeurIPS 2026 submission)
  - WhyLab: Gemini 2.5 Docker Validation (venue TBD)

데이터 소스 (모두 무료, API key 불필요):
  - NeurIPS 2026 dates page              — https://neurips.cc/Conferences/2026/Dates
  - OpenReview public reviews            — https://api2.openreview.net/notes
  - Semantic Scholar (post-publication)  — https://api.semanticscholar.org/graph/v1

산출:
  - `.agent/knowledge/citation_reports/blind_review_outcome_history.jsonl`
    Append-only history (date checked, status, evidence)
  - 상태 변화 시 (HOLD → READY_TO_UNHOLD) 즉시 Telegram alert
  - 매주 markdown 보고서 (변동 없어도 status confirmation)

실행:
    python scripts/citation_monitor/monitor_blind_review_outcome.py
    python scripts/citation_monitor/monitor_blind_review_outcome.py --dry-run
    python scripts/citation_monitor/monitor_blind_review_outcome.py --no-alert

cron 등록:
    Windows Scheduled Task: NeoGenesis-Blind-Review-Outcome-Weekly
    매주 월요일 10:00 KST (citation monitor + 30분 후)

Reference:
  - 20260512_AI_CORPUS_CITATION_STRATEGY_v1.md v1.4 (Blind Review HOLD policy)
  - 20260512_BLIND_REVIEW_ANONYMITY_AUDIT.md
  - PAPER/EthicaAI/arxiv_submission/ + PAPER/WhyLab/arxiv_submission/ (pre-built, unhold 시 즉시 publishable)

Unhold trigger conditions:
  - NeurIPS 2026 결과 발표 ≥ 2026-09-15 (예상)
  - OpenReview public review board scrape → submission ID 발견 시
  - Semantic Scholar 의 published version 등록 (review 종료 후)

작성: 2026-05-12, Strategy Lead Claude Opus 4.7
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass, asdict, field
from datetime import datetime, timezone, date
from pathlib import Path
from typing import Any, Optional

ROOT = Path(__file__).resolve().parent
PROJECT_ROOT = ROOT.parents[1]
HISTORY_FILE = PROJECT_ROOT / ".agent" / "knowledge" / "citation_reports" / "blind_review_outcome_history.jsonl"
REPORT_DIR = PROJECT_ROOT / ".agent" / "knowledge" / "citation_reports"
REPORT_DIR.mkdir(parents=True, exist_ok=True)

USER_AGENT = (
    "Neo Genesis Blind Review Outcome Monitor/1.0 "
    "(https://neogenesis.app; research-tool)"
)


# ──────────────────────────────────────────────
# Tracked manuscripts
# ──────────────────────────────────────────────

@dataclass
class TrackedManuscript:
    """A manuscript currently under blind review."""

    short_id: str
    title_keywords: list[str]
    expected_venue: str
    target_outcome_date: str  # ISO date (best-guess)
    associated_dataset: str
    notes: str = ""


TRACKED: list[TrackedManuscript] = [
    TrackedManuscript(
        short_id="ethicaai_mixed_safe",
        title_keywords=["mixed-safe", "boundary-consistent", "cooperative constraint"],
        expected_venue="NeurIPS 2026",
        target_outcome_date="2026-09-15",  # NeurIPS 2026 accept/reject ~mid-Sep
        associated_dataset="https://huggingface.co/datasets/neogenesislab/ethicaai-mixed-safe-evidence",
        notes="Coin Game 160 seeds + Melting Pot 50 seeds + Fishery 300 seeds = 510 rows",
    ),
    TrackedManuscript(
        short_id="whylab_docker_validation",
        title_keywords=["WhyLab", "Docker Validation", "selective adaptive C2", "SWE-bench"],
        expected_venue="TBD (likely NeurIPS Workshop or ICLR Workshop)",
        target_outcome_date="2026-10-01",
        associated_dataset="https://huggingface.co/datasets/neogenesislab/whylab-gemini-2-5-docker-validation",
        notes="67-problem prefilter, 402 episodes, honest null result",
    ),
]


# ──────────────────────────────────────────────
# Data sources
# ──────────────────────────────────────────────

def _http_get(url: str, timeout: int = 30) -> bytes:
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT})
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return resp.read()
    except urllib.error.HTTPError as e:
        if e.code in (404, 400):
            return b""
        print(f"  ! HTTP error on {url[:80]}: {e}", file=sys.stderr)
        return b""
    except (urllib.error.URLError, TimeoutError) as e:
        print(f"  ! Network error on {url[:80]}: {e}", file=sys.stderr)
        return b""


def check_neurips_dates(m: TrackedManuscript) -> dict[str, Any]:
    """Compare today vs target_outcome_date. Returns whether outcome window has passed."""
    today = date.today()
    target = date.fromisoformat(m.target_outcome_date)
    days_remaining = (target - today).days

    if days_remaining > 0:
        return {
            "source": "date_check",
            "status": "PENDING",
            "days_remaining": days_remaining,
            "target_date": m.target_outcome_date,
            "message": f"{m.expected_venue} outcome expected in {days_remaining} days",
        }
    elif days_remaining >= -30:
        return {
            "source": "date_check",
            "status": "WINDOW_OPEN",
            "days_past_target": -days_remaining,
            "target_date": m.target_outcome_date,
            "message": f"{m.expected_venue} outcome window OPEN (target was {-days_remaining}d ago)",
        }
    else:
        return {
            "source": "date_check",
            "status": "OVERDUE",
            "days_past_target": -days_remaining,
            "target_date": m.target_outcome_date,
            "message": f"{m.expected_venue} outcome OVERDUE by {-days_remaining}d — check status manually",
        }


def search_semantic_scholar(m: TrackedManuscript) -> dict[str, Any]:
    """Search Semantic Scholar for published version of the manuscript."""
    # Use the first 2 most-distinctive keywords as query
    query = " ".join(m.title_keywords[:2])
    enc = urllib.parse.quote(query)
    url = (
        f"https://api.semanticscholar.org/graph/v1/paper/search"
        f"?query={enc}&limit=5&fields=title,authors,year,venue,externalIds,publicationDate"
    )
    body = _http_get(url)
    if not body:
        return {"source": "semantic_scholar", "status": "API_UNAVAILABLE", "results": []}
    try:
        data = json.loads(body)
    except Exception:
        return {"source": "semantic_scholar", "status": "PARSE_ERROR", "results": []}

    hits = data.get("data", []) or []
    matches: list[dict[str, Any]] = []
    for hit in hits[:5]:
        title = (hit.get("title") or "").lower()
        # Score keywords: 키워드 N개 중 매치율
        kw_hits = sum(1 for k in m.title_keywords if k.lower() in title)
        if kw_hits >= 2:  # At least 2 keywords match → likely the same paper
            matches.append({
                "title": hit.get("title"),
                "year": hit.get("year"),
                "venue": hit.get("venue"),
                "authors": [a.get("name") for a in hit.get("authors", []) or []],
                "ext_ids": hit.get("externalIds"),
                "kw_match_count": kw_hits,
            })

    if matches:
        return {
            "source": "semantic_scholar",
            "status": "PUBLISHED_VERSION_FOUND",
            "results": matches,
        }
    return {"source": "semantic_scholar", "status": "NOT_FOUND", "results": []}


def search_openreview(m: TrackedManuscript) -> dict[str, Any]:
    """Search OpenReview public reviews for the manuscript (NeurIPS 2026 public review timing)."""
    # OpenReview API v2
    query = " ".join(m.title_keywords[:2])
    enc = urllib.parse.quote(query)
    url = (
        f"https://api2.openreview.net/notes/search?"
        f"term={enc}&limit=10&type=all"
    )
    body = _http_get(url)
    if not body:
        return {"source": "openreview", "status": "API_UNAVAILABLE", "results": []}
    try:
        data = json.loads(body)
    except Exception:
        return {"source": "openreview", "status": "PARSE_ERROR", "results": []}

    notes = (data.get("notes") or [])
    matches: list[dict[str, Any]] = []
    for note in notes[:5]:
        content = note.get("content", {}) or {}
        title = (content.get("title") or {}).get("value") if isinstance(content.get("title"), dict) else content.get("title") or ""
        title = title.lower() if isinstance(title, str) else ""
        kw_hits = sum(1 for k in m.title_keywords if k.lower() in title)
        if kw_hits >= 2:
            matches.append({
                "title": title,
                "venue": note.get("invitations") or note.get("invitation"),
                "kw_match_count": kw_hits,
            })

    if matches:
        return {"source": "openreview", "status": "PUBLIC_REVIEW_FOUND", "results": matches}
    return {"source": "openreview", "status": "NOT_FOUND", "results": []}


# ──────────────────────────────────────────────
# Aggregation
# ──────────────────────────────────────────────

def aggregate_status(m: TrackedManuscript) -> dict[str, Any]:
    """Combine signals: date check + semantic scholar + openreview."""
    date_check = check_neurips_dates(m)
    semantic = search_semantic_scholar(m)
    openreview = search_openreview(m)

    # Top-level status
    if semantic["status"] == "PUBLISHED_VERSION_FOUND":
        overall = "READY_TO_UNHOLD"
        reason = f"Semantic Scholar has published version with {len(semantic['results'])} matching paper(s)"
    elif openreview["status"] == "PUBLIC_REVIEW_FOUND":
        overall = "PUBLIC_REVIEW_ACTIVE"
        reason = f"OpenReview has public review thread for matching paper"
    elif date_check["status"] == "OVERDUE":
        overall = "OVERDUE_CHECK"
        reason = date_check["message"]
    elif date_check["status"] == "WINDOW_OPEN":
        overall = "OUTCOME_WINDOW"
        reason = date_check["message"]
    else:
        overall = "PENDING"
        reason = date_check["message"]

    return {
        "short_id": m.short_id,
        "expected_venue": m.expected_venue,
        "target_outcome_date": m.target_outcome_date,
        "overall_status": overall,
        "reason": reason,
        "signals": {
            "date_check": date_check,
            "semantic_scholar": semantic,
            "openreview": openreview,
        },
        "checked_at": datetime.now(timezone.utc).isoformat(),
    }


def append_history(record: dict[str, Any]) -> None:
    with HISTORY_FILE.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


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


def write_weekly_report(results: list[dict[str, Any]]) -> Path:
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    report_path = REPORT_DIR / f"{today}_blind_review_outcome.md"

    lines = [
        f"# Blind Review Outcome Monitor — {today}",
        "",
        f"> 자동 생성: `scripts/citation_monitor/monitor_blind_review_outcome.py`",
        f"> Tracked manuscripts: {len(results)}",
        "",
        "## 매뉴스크립트별 상태",
        "",
    ]
    for r in results:
        status_emoji = {
            "READY_TO_UNHOLD": "🟢",
            "PUBLIC_REVIEW_ACTIVE": "🟡",
            "OUTCOME_WINDOW": "🟡",
            "OVERDUE_CHECK": "🟠",
            "PENDING": "⏸️",
        }.get(r["overall_status"], "❓")
        lines.append(f"### {status_emoji} {r['short_id']}")
        lines.append("")
        lines.append(f"- **Status**: {r['overall_status']}")
        lines.append(f"- **Venue**: {r['expected_venue']}")
        lines.append(f"- **Target outcome date**: {r['target_outcome_date']}")
        lines.append(f"- **Reason**: {r['reason']}")
        lines.append(f"- **Semantic Scholar**: {r['signals']['semantic_scholar']['status']}")
        lines.append(f"- **OpenReview**: {r['signals']['openreview']['status']}")
        lines.append("")

    lines.append("## Trigger Actions (자동 / G2)")
    lines.append("")
    ready_to_unhold = [r for r in results if r["overall_status"] == "READY_TO_UNHOLD"]
    if ready_to_unhold:
        lines.append(f"🟢 **{len(ready_to_unhold)} manuscript(s) ready to UNHOLD**:")
        for r in ready_to_unhold:
            lines.append(f"- {r['short_id']}: {r['reason']}")
        lines.append("")
        lines.append("Next steps (owner G2):")
        lines.append("- (a) Confirm review outcome (accept/reject) via venue website")
        lines.append("- (b) If accept: restore author byline on all 8 surfaces (Strategy v1.4 anonymization reverse)")
        lines.append("- (c) If accept: arXiv release path opens (Strategy v1.4 §2.B.B10)")
        lines.append("- (d) If reject: owner G2 재검토 (다른 venue 재제출 vs arXiv 직접 vs workshop redirect)")
    else:
        lines.append("⏸️ 모든 manuscripts blind review hold 상태 유지. 다음 cycle (1 week) 재확인.")

    report_path.write_text("\n".join(lines), encoding="utf-8")
    return report_path


# ──────────────────────────────────────────────
# 메인
# ──────────────────────────────────────────────

def main() -> int:
    parser = argparse.ArgumentParser(description="Blind review outcome monitor")
    parser.add_argument("--dry-run", action="store_true", help="history file 저장 없이 보고만")
    parser.add_argument("--no-alert", action="store_true", help="Telegram alert 비활성")
    parser.add_argument("--manuscript", help="specific manuscript short_id only")
    args = parser.parse_args()

    print(f"[blind_review_monitor] run start {datetime.now(timezone.utc).isoformat()}")
    print(f"[blind_review_monitor] tracked: {[m.short_id for m in TRACKED]}")
    print(f"[blind_review_monitor] dry-run: {args.dry_run}")

    targets = TRACKED if not args.manuscript else [m for m in TRACKED if m.short_id == args.manuscript]
    if not targets:
        print(f"  ! No matching manuscript", file=sys.stderr)
        return 2

    # 직전 state 로드
    last_state: dict[str, str] = {}
    if HISTORY_FILE.exists():
        try:
            with HISTORY_FILE.open("r", encoding="utf-8") as f:
                for line in f:
                    try:
                        r = json.loads(line)
                        last_state[r["short_id"]] = r.get("overall_status", "UNKNOWN")
                    except Exception:
                        continue
        except Exception:
            pass

    results: list[dict[str, Any]] = []
    for m in targets:
        print(f"  → checking {m.short_id}")
        r = aggregate_status(m)
        results.append(r)
        time.sleep(2)  # rate-limit politeness

    # Status transition alerts
    alerts: list[str] = []
    for r in results:
        prev = last_state.get(r["short_id"], "PENDING")
        cur = r["overall_status"]
        if prev != cur and cur in ("READY_TO_UNHOLD", "PUBLIC_REVIEW_ACTIVE"):
            alerts.append(
                f"🟢 {r['short_id']} status change: {prev} → {cur}\n"
                f"   venue: {r['expected_venue']}\n"
                f"   reason: {r['reason']}"
            )

    # History append
    if not args.dry_run:
        for r in results:
            append_history(r)
        report_path = write_weekly_report(results)
        print(f"[blind_review_monitor] report: {report_path}")

    if alerts and not args.no_alert:
        alert_text = "🚨 Blind Review status 변화\n\n" + "\n\n".join(alerts)
        telegram_alert(alert_text)

    print(f"[blind_review_monitor] done {datetime.now(timezone.utc).isoformat()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
