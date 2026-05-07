"""Daily Sora quality audit — runs over the last 24h of audit_log entries
and produces a single-line score plus a structured report.

Designed for cron: every morning at 09:00 KST this audits yesterday's
Telegram interactions and writes a report to data/logs/sora_quality_report.jsonl.
Optionally posts a summary to the owner's Telegram channel.

Run: PYTHONIOENCODING=utf-8 python scripts/sora/daily_quality_audit.py

Schedule: see crontab on ysh-server (root):
    0 0 * * * cd /home/ysh/sora && python3 scripts/sora/daily_quality_audit.py >> /home/ysh/sora/data/logs/sora_quality_cron.log 2>&1

The script is host-side - it expects to run inside or alongside the
sora-live container. On Windows it can also point at /app/data/logs over
SSH for remote audit.
"""
from __future__ import annotations

import datetime as dt
import json
import os
import sys
from pathlib import Path
from collections import Counter

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

# Default sora-live container paths (override with SORA_DATA_ROOT env)
DATA_ROOT = Path(os.environ.get("SORA_DATA_ROOT", "/app/data"))
AUDIT_LOG = DATA_ROOT / "logs" / "sora_audit.jsonl"
SLO_LOG = DATA_ROOT / "logs" / "slo_log.jsonl"
ALERTS_LOG = DATA_ROOT / "logs" / "alerts.jsonl"
REPORT_OUT = DATA_ROOT / "logs" / "sora_quality_report.jsonl"

# 24h window (UTC). Local cron runs at 09:00 KST = 00:00 UTC, so "yesterday"
# in KST aligns naturally with the previous-day window in UTC.
NOW = dt.datetime.now(dt.timezone.utc)
WINDOW_START = NOW - dt.timedelta(hours=24)


def parse_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return out


def in_window(record: dict, ts_field: str = "ts") -> bool:
    raw = record.get(ts_field) or record.get("timestamp")
    if not raw:
        return False
    try:
        # Handle both naive and aware ISO timestamps
        ts = dt.datetime.fromisoformat(raw.replace("Z", "+00:00"))
        if ts.tzinfo is None:
            ts = ts.replace(tzinfo=dt.timezone.utc)
        return WINDOW_START <= ts <= NOW
    except Exception:
        return False


def main() -> int:
    audits = [r for r in parse_jsonl(AUDIT_LOG) if in_window(r)]
    slo = [r for r in parse_jsonl(SLO_LOG) if in_window(r, "timestamp")]
    alerts = [r for r in parse_jsonl(ALERTS_LOG) if in_window(r, "timestamp")]

    # Audit metrics
    total_requests = len(audits)
    errors = [r for r in audits if r.get("error")]
    error_count = len(errors)
    durations = [r.get("duration_ms", 0) for r in audits if r.get("duration_ms")]
    durations.sort()
    p50 = durations[len(durations) // 2] if durations else 0
    p95 = durations[int(len(durations) * 0.95)] if durations else 0

    # Strategy distribution
    strategies = Counter(r.get("strategy", "unknown") for r in audits)

    # Tools usage
    tools_total = sum(r.get("tools_count", 0) for r in audits)

    # SLO health
    slo_violations = [r for r in slo if r.get("violation")]
    slo_endpoints = Counter(r.get("endpoint") for r in slo if r.get("endpoint"))
    slo_total = len(slo)
    slo_ok = slo_total - len(slo_violations)

    # Alerts severity breakdown
    alert_severities = Counter(r.get("severity", "unknown") for r in alerts)
    real_alerts = [r for r in alerts if not r.get("source", "").startswith("smoke_")]

    report = {
        "generated_at": NOW.isoformat(),
        "window_hours": 24,
        "audit": {
            "total_requests": total_requests,
            "errors": error_count,
            "error_rate_pct": round(error_count / total_requests * 100, 2) if total_requests else 0,
            "latency_p50_ms": p50,
            "latency_p95_ms": p95,
            "tools_total_calls": tools_total,
            "strategy_distribution": dict(strategies.most_common(5)),
        },
        "slo": {
            "total_probes": slo_total,
            "ok": slo_ok,
            "violations": len(slo_violations),
            "uptime_pct": round(slo_ok / slo_total * 100, 2) if slo_total else 0,
            "endpoints_probed": len(slo_endpoints),
        },
        "alerts": {
            "total": len(alerts),
            "real_alerts_excluding_smoke": len(real_alerts),
            "severity_distribution": dict(alert_severities),
        },
    }

    # Quality verdict: composite of error rate, p95 latency, slo uptime, alerts
    verdict_score = 100
    if total_requests and error_count / total_requests > 0.05:
        verdict_score -= 30
    if p95 and p95 > 10000:
        verdict_score -= 15
    if slo_total and len(slo_violations) / slo_total > 0.01:
        verdict_score -= 25
    if len(real_alerts) > 0:
        verdict_score -= len(real_alerts) * 5
    verdict_score = max(0, verdict_score)
    report["verdict"] = {
        "score": verdict_score,
        "label": "GREEN" if verdict_score >= 80 else "YELLOW" if verdict_score >= 60 else "RED",
    }

    # One-line stdout summary for cron log
    line = (
        f"[Sora-quality] {NOW.isoformat()} "
        f"reqs={total_requests} err={error_count} p50={p50}ms p95={p95}ms "
        f"slo={slo_ok}/{slo_total} alerts={len(real_alerts)} "
        f"verdict={report['verdict']['label']}({verdict_score})"
    )
    print(line)

    # Append structured report to JSONL for trend analysis
    REPORT_OUT.parent.mkdir(parents=True, exist_ok=True)
    with open(REPORT_OUT, "a", encoding="utf-8") as f:
        f.write(json.dumps(report, ensure_ascii=False) + "\n")

    # Optional: send to Telegram if NEO_ALERT_BOT_TOKEN + NEO_ALERT_CHAT_ID set
    bot_token = os.environ.get("NEO_ALERT_BOT_TOKEN", "").strip()
    chat_id = os.environ.get("NEO_ALERT_CHAT_ID", "").strip()
    if bot_token and chat_id and report["verdict"]["label"] != "GREEN":
        # Only send when not green to avoid noise
        try:
            import urllib.parse
            import urllib.request
            text = (
                f"Sora quality {report['verdict']['label']} ({verdict_score}/100)\n"
                f"  reqs/24h: {total_requests}, err: {error_count} ({report['audit']['error_rate_pct']}%)\n"
                f"  p50: {p50}ms, p95: {p95}ms\n"
                f"  SLO uptime: {report['slo']['uptime_pct']}%\n"
                f"  alerts (real): {len(real_alerts)}"
            )
            url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
            data = urllib.parse.urlencode({"chat_id": chat_id, "text": text}).encode()
            req = urllib.request.Request(url, data=data, method="POST")
            with urllib.request.urlopen(req, timeout=15) as r:
                pass
        except Exception:
            pass

    return 0 if report["verdict"]["label"] != "RED" else 1


if __name__ == "__main__":
    raise SystemExit(main())
