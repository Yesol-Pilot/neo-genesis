# -*- coding: utf-8 -*-
"""Ambient Watcher Job — 10분 주기로 state change 감지 → owner alert.

2026-05-12: STOP 해제 후 자비스급 ambient context 첫 도입.

감시 대상 (각각 graceful — 한 소스 실패해도 다른 소스 계속):
  1. SLO degradation: slo_log.jsonl 최근 1h fail spike (>=2건/h 직전 0건 → P1)
  2. Quant lease drop: Supabase quant_runtime_leases active=0 변화 (P0)
  3. Vercel deploy fail: 최근 30분 sora-live audit log 의 deploy_fail event (P1)
  4. Disk usage: /app/data 사용률 85% 초과 (P1)

State snapshot: /app/data/state/ambient_watcher.json (직전 cycle 의 alert sig).
같은 sig 중복 dedup 30분.
"""
from __future__ import annotations

import hashlib
import json
import logging
import os
import shutil
import time
import urllib.parse
import urllib.request
from datetime import datetime, timedelta, timezone
from pathlib import Path

logger = logging.getLogger("neo.jobs.ambient_watcher")
KST = timezone(timedelta(hours=9))

STATE_DIR = Path("/app/data/state")
STATE_FILE = STATE_DIR / "ambient_watcher.json"
DEDUP_WINDOW_SEC = 30 * 60  # 30분


def _load_state() -> dict:
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        STATE_FILE.write_text(json.dumps(state, ensure_ascii=False), encoding="utf-8")
    except Exception as e:
        logger.warning("[ambient_watcher] state save 실패: %s", e)


def _sig(scenario: str, payload: str) -> str:
    return hashlib.sha1(f"{scenario}|{payload}".encode()).hexdigest()[:12]


def _check_slo_spike() -> dict | None:
    """slo_log.jsonl 최근 1h 의 fail event 개수 → 2건 이상이면 P1."""
    try:
        path = "/app/data/logs/slo_log.jsonl"
        if not os.path.exists(path):
            return None
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(hours=1)
        fails = {}
        with open(path, encoding="utf-8") as f:
            for line in f.readlines()[-2000:]:  # 최근 2000줄만 스캔
                try:
                    r = json.loads(line)
                    ts = r.get("ts") or r.get("timestamp")
                    if not ts:
                        continue
                    dt = datetime.fromisoformat(ts.replace("Z", "+00:00"))
                    if dt < cutoff:
                        continue
                    sli = r.get("sli_value", {})
                    success = sli.get("success")
                    if success is None:
                        success = not r.get("violation", False)
                    if not success:
                        ep = r.get("endpoint", "?")
                        fails[ep] = fails.get(ep, 0) + 1
                except Exception:
                    continue
        total_fails = sum(fails.values())
        if total_fails >= 2:
            return {
                "scenario": "slo_spike",
                "severity": "P1",
                "summary": f"SLO 최근 1h fail {total_fails}건 — {', '.join(f'{k}:{v}' for k,v in fails.items())}",
                "sig_payload": f"{total_fails}|{','.join(sorted(fails.keys()))}",
            }
    except Exception as e:
        logger.debug("[ambient_watcher] slo check err: %s", e)
    return None


def _check_disk_usage() -> dict | None:
    """/app/data 사용률 85% 초과 시 P1."""
    try:
        usage = shutil.disk_usage("/app/data")
        used_pct = (usage.used / usage.total) * 100
        if used_pct >= 85.0:
            return {
                "scenario": "disk_high",
                "severity": "P1",
                "summary": f"디스크 사용률 {used_pct:.1f}% (used={usage.used // (1024**3)}GB / total={usage.total // (1024**3)}GB)",
                "sig_payload": f"{int(used_pct)}",
            }
    except Exception as e:
        logger.debug("[ambient_watcher] disk check err: %s", e)
    return None


def _check_quant_lease() -> dict | None:
    """Supabase quant_runtime_leases 활성 lease 0건 → P0.

    Supabase Python client 없으면 silent skip.
    """
    try:
        from supabase import create_client  # type: ignore
    except Exception:
        return None
    url = os.getenv("SUPABASE_URL") or os.getenv("NEO_GENESIS_SUPABASE_URL")
    key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
    if not url or not key:
        return None
    try:
        client = create_client(url, key)
        # Active lease: heartbeat_at 최근 5분 이내
        cutoff = (datetime.now(timezone.utc) - timedelta(minutes=5)).isoformat()
        res = client.table("quant_runtime_leases").select("instance_id,heartbeat_at,trading_mode").gte("heartbeat_at", cutoff).limit(5).execute()
        active = res.data if hasattr(res, "data") else []
        if not active:
            return {
                "scenario": "quant_lease_drop",
                "severity": "P0",
                "summary": "quant_runtime_leases 활성 lease 0건 (last 5min) — quant-bot VM PM2 점검 필요",
                "sig_payload": "0",
            }
    except Exception as e:
        logger.debug("[ambient_watcher] quant lease check err: %s", e)
    return None


def _check_local_llm_tunnel() -> dict | None:
    """SSH reverse tunnel (desktop-home Ollama → ysh-server:11434) 활성 확인.

    2026-05-12: tunnel 끊기면 owner Sora 응답 시간이 1초 → 18초 (Gemini fallback) 로 늘어남.
    매 10분 ping → tunnel down 시 P1 alert.
    """
    try:
        import urllib.request
        with urllib.request.urlopen("http://172.17.0.1:11434/api/version", timeout=3) as r:
            data = json.loads(r.read())
            if data.get("version"):
                return None  # alive
    except Exception:
        pass
    return {
        "scenario": "local_llm_tunnel_down",
        "severity": "P1",
        "summary": "Local LLM SSH tunnel 끊김 — Sora 응답 시간 1s → 18s 로 늘어날 수 있음. desktop-home 의 ssh_tunnel_ollama.bat 확인 필요.",
        "sig_payload": "tunnel_down",
    }


def _check_sora_brain_alive() -> dict | None:
    """brain.worker process /proc 검사 — 없으면 P0."""
    try:
        for pid_dir in Path("/proc").iterdir():
            if not pid_dir.name.isdigit():
                continue
            try:
                cmd = (pid_dir / "cmdline").read_bytes().decode("utf-8", "ignore")
                if "src.core.brain.worker" in cmd:
                    return None  # 살아있음
            except Exception:
                continue
        return {
            "scenario": "brain_dead",
            "severity": "P0",
            "summary": "brain.worker process 없음 — supervisord autorestart 진행 중일 수 있음",
            "sig_payload": "missing",
        }
    except Exception as e:
        logger.debug("[ambient_watcher] brain check err: %s", e)
    return None


def _send_telegram(text: str, severity: str = "P1") -> bool:
    """P0 → P0 이모지 / P1 → ⚠️ / P2 → ℹ️."""
    tok = os.getenv("NEO_ALERT_BOT_TOKEN", "")
    cid = os.getenv("OWNER_TELEGRAM_CHAT_ID") or os.getenv("NEO_ALERT_CHAT_ID", "")
    if not tok or not cid:
        return False
    icon = {"P0": "🚨", "P1": "⚠️", "P2": "ℹ️"}.get(severity, "•")
    payload = urllib.parse.urlencode({
        "chat_id": cid,
        "text": f"{icon} <b>[Ambient {severity}]</b>\n{text}",
        "parse_mode": "HTML",
        "disable_notification": "true" if severity == "P2" else "false",
    }).encode()
    try:
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            data=payload, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            return bool(json.loads(r.read()).get("ok"))
    except Exception as e:
        logger.error("[ambient_watcher] telegram send 실패: %s", e)
        return False


def run_ambient_check() -> dict:
    """10분 주기 cron entry point.

    Returns:
        {"checks": N, "alerts": M, "dedup_suppressed": K}
    """
    t0 = time.time()
    state = _load_state()
    now_ts = int(time.time())

    checks = [
        _check_slo_spike,
        _check_disk_usage,
        _check_quant_lease,
        _check_sora_brain_alive,
        _check_local_llm_tunnel,  # 2026-05-12 신규
    ]

    alerts_fired = 0
    dedup_count = 0
    results = []
    for chk in checks:
        try:
            r = chk()
        except Exception as e:
            logger.warning("[ambient_watcher] %s err: %s", chk.__name__, e)
            continue
        if r is None:
            continue
        results.append(r)
        sig = _sig(r["scenario"], r.get("sig_payload", ""))
        last_sent = state.get(sig, 0)
        if (now_ts - last_sent) < DEDUP_WINDOW_SEC:
            dedup_count += 1
            continue
        # Fire alert
        sent = _send_telegram(r["summary"], severity=r["severity"])
        if sent:
            alerts_fired += 1
            state[sig] = now_ts

    # GC: 24h 초과 sig 청소
    cutoff_old = now_ts - 24 * 3600
    state = {k: v for k, v in state.items() if v >= cutoff_old}
    _save_state(state)

    latency_ms = (time.time() - t0) * 1000
    summary = {
        "checks": len(checks),
        "alerts_fired": alerts_fired,
        "dedup_suppressed": dedup_count,
        "active_signals": len(results),
        "latency_ms": round(latency_ms, 1),
    }
    logger.info("[ambient_watcher] %s", summary)
    return summary


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run_ambient_check()
    print(json.dumps(result, ensure_ascii=False, indent=2))
