"""주간 수익 리뷰 — Revenue OS §3 마지막 cron.

W4 예산 페이서 + W5 수익 텔레메트리 + git 진척을 묶어 엔진별 게이트 상태와
다음 주 우선순위를 한 리포트로. 거짓 메트릭 금지: 수집 불가는 no_data 그대로.

usage:
  python scripts/revenue_os/weekly_revenue_review.py [--no-telegram]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import subprocess
import sys
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
OUT_DIR = ROOT / "output" / "revenue_os"
BUDGET = OUT_DIR / "gemini_budget_status.json"
TELEMETRY = OUT_DIR / "revenue_telemetry_latest.json"
ENV = ROOT / ".env"

# 엔진별 다음 게이트 (정본: 20260612_AUTONOMOUS_REVENUE_OS_v1.md §2)
ENGINE_GATES = {
    "R1": "콘솔 앱 3개 검토 요청 제출 → 심사 통과 = 광고 수익 게이트 해제",
    "R2": "팔로워 10K + 30일 조회 10만 (Creator Rewards). 현재는 전환 성장 단계",
    "R3": "결제 수단 결정 (owner G2) — FINITE 트래픽 P0 세션 종료 후",
    "R4": "쿠팡 글 도메인 이전 + AdSense 상태 점검 (저노력)",
    "R5": "EP002 업로드 → 반응(팔로우·lore 댓글) 보고 EP003 자율 생산",
}


def _read_json(p: Path) -> dict | None:
    try:
        return json.loads(p.read_text(encoding="utf-8"))
    except Exception:
        return None


def _env() -> dict[str, str]:
    out: dict[str, str] = {}
    if not ENV.exists():
        return out
    for line in ENV.read_text(encoding="utf-8", errors="ignore").splitlines():
        if "=" in line and not line.strip().startswith("#"):
            k, _, v = line.partition("=")
            out[k.strip()] = v.strip().strip('"').strip("'")
    return out


def _git_week_commits() -> list[str]:
    try:
        r = subprocess.run(
            ["git", "log", "--since=7.days", "--oneline", "--no-merges"],
            cwd=str(ROOT), capture_output=True, text=True, timeout=30,
            encoding="utf-8", errors="replace",
        )
        return [ln for ln in r.stdout.splitlines() if ln.strip()][:40]
    except Exception:
        return []


def build_review(now: dt.datetime) -> dict:
    budget = _read_json(BUDGET) or {}
    telem = _read_json(TELEMETRY) or {}
    engines = telem.get("engines", []) if isinstance(telem, dict) else []

    # 엔진별 실수집 신호 집계 (no_data 정직 유지)
    by_engine: dict[str, dict] = {}
    for row in engines:
        eid = row.get("engine_id", "?")
        e = by_engine.setdefault(eid, {"engine_name": row.get("engine_name", eid), "live": [], "no_data": []})
        if row.get("status") == "no_data" or row.get("value") is None:
            e["no_data"].append(row.get("metric"))
        else:
            e["live"].append({"metric": row.get("metric"), "value": row.get("value"), "unit": row.get("unit")})

    commits = _git_week_commits()
    review = {
        "schema_version": "weekly_revenue_review_v1",
        "generated_at": now.isoformat(),
        "timezone": "Asia/Seoul",
        "budget": {
            "monthly_cap_krw": budget.get("monthly_cap_krw"),
            "month_to_date_krw": budget.get("month_to_date_krw"),
            "pct_of_cap": budget.get("pct_of_cap"),
            "alert_level": budget.get("alert_level"),
            "data_quality": budget.get("data_quality"),
        },
        "engines": [
            {
                "engine_id": eid,
                "engine_name": by_engine.get(eid, {}).get("engine_name", eid),
                "live_signals": by_engine.get(eid, {}).get("live", []),
                "no_data_count": len(by_engine.get(eid, {}).get("no_data", [])),
                "next_gate": gate,
            }
            for eid, gate in ENGINE_GATES.items()
        ],
        "week_commits": commits,
        "week_commit_count": len(commits),
        "honest_note": "수집 불가 메트릭은 no_data 유지. 직접 수익 라인은 콘솔 의존(R1 심사·광고)이라 자동 수집 불가 — owner 콘솔 확인 필요.",
    }
    return review


def to_telegram_text(r: dict) -> str:
    b = r["budget"]
    lines = ["[주간 수익 리뷰]"]
    cap = b.get("monthly_cap_krw") or 0
    mtd = b.get("month_to_date_krw") or 0
    lines.append(f"예산: 월 ₩{int(mtd):,}/₩{int(cap):,} ({b.get('alert_level','ok')})")
    lines.append(f"주간 커밋: {r['week_commit_count']}건")
    lines.append("")
    for e in r["engines"]:
        live = e["live_signals"]
        sig = ", ".join(f"{s['metric']}={s['value']}{s.get('unit','')}" for s in live[:2]) if live else "실수집 신호 없음"
        lines.append(f"{e['engine_id']} {e['engine_name']}: {sig}")
        lines.append(f"  다음게이트: {e['next_gate']}")
    return "\n".join(lines)


def send_telegram(text: str) -> bool:
    env = _env()
    tok = env.get("CODEX_ALERT_BOT_TOKEN")
    chat = env.get("OWNER_TELEGRAM_CHAT_ID") or env.get("NEO_ALERT_CHAT_ID")
    if not tok or not chat:
        return False
    data = urllib.parse.urlencode({"chat_id": chat, "text": text}).encode()
    try:
        r = urllib.request.urlopen(f"https://api.telegram.org/bot{tok}/sendMessage", data=data, timeout=20)
        return bool(json.loads(r.read()).get("ok"))
    except Exception:
        return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--no-telegram", action="store_true")
    ap.add_argument("--now", default=None, help="ISO local override for tests")
    args = ap.parse_args()

    if args.now:
        now = dt.datetime.fromisoformat(args.now)
    else:
        now = dt.datetime.now(dt.timezone(dt.timedelta(hours=9)))

    review = build_review(now)
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    latest = OUT_DIR / "weekly_revenue_review_latest.json"
    latest.write_text(json.dumps(review, ensure_ascii=False, indent=1), encoding="utf-8")
    stamp = OUT_DIR / f"weekly_revenue_review_{now:%Y%m%d}_KST.json"
    stamp.write_text(json.dumps(review, ensure_ascii=False, indent=1), encoding="utf-8")

    text = to_telegram_text(review)
    sent = False if args.no_telegram else send_telegram(text)
    print(json.dumps({"status": "ok", "path": str(latest), "telegram_sent": sent,
                      "engines": len(review["engines"]), "commits": review["week_commit_count"]},
                     ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
