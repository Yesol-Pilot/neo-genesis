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
DEDUP_WINDOW_SEC = 6 * 3600  # 2026-05-20: 30분 → 6시간 (노이즈 폭탄 차단)


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


# 2026-05-20: dedup scenario-only (payload 변동으로 인한 dedup 무력화 영구 fix).
def _sig(scenario: str, payload: str = "") -> str:
    return hashlib.sha1(f"{scenario}".encode()).hexdigest()[:12]


# 2026-05-20: 만성 미가동 endpoint = 이미 알려진 정상 상태 (owner alert 불필요).
# grafana/promtail/loki/tempo/cloudflare_tunnel = observability stack 미가동.
# telegram_bot_activity = mtime probe (간헐 fail 정상). qdrant/chromadb = RAG 미상주.
_KNOWN_DOWN_ENDPOINTS = {
    "grafana", "promtail", "loki", "tempo", "cloudflare_tunnel",
    "telegram_bot_activity", "qdrant_rag", "chromadb_legacy", "local_llm",
}


def _check_slo_spike() -> dict | None:
    """SLO 최근 1h fail 분석. 단 만성 미가동 endpoint 제외 + '항상 떠있어야 하는'
    핵심 endpoint (brain_worker / redis_bus / dashboard_api) 가 fail 일 때만 P2.

    2026-05-20: owner '불필요 메시지 너무 많이 와' 보고 후 전면 완화.
    이전: 모든 fail 합산 → 매 10분 count 변동 → dedup 무력화 → 61 msg 폭탄.
    이후: 핵심 endpoint 만 + scenario-only dedup 6h + P1→P2 (조용).
    """
    try:
        path = "/app/data/logs/slo_log.jsonl"
        if not os.path.exists(path):
            return None
        now_utc = datetime.now(timezone.utc)
        cutoff = now_utc - timedelta(hours=1)
        fails = {}
        with open(path, encoding="utf-8") as f:
            for line in f.readlines()[-2000:]:
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
                        if ep in _KNOWN_DOWN_ENDPOINTS:
                            continue  # 만성 미가동 제외
                        fails[ep] = fails.get(ep, 0) + 1
                except Exception:
                    continue
        # 핵심 endpoint 만 남았고, 그것도 1h 내 30회+ (= 거의 상시 down) 일 때만 alert
        critical_fails = {k: v for k, v in fails.items() if v >= 30}
        if critical_fails:
            return {
                "scenario": "slo_critical_down",
                "severity": "P2",  # 조용한 알림 (disable_notification)
                "summary": f"SLO 핵심 endpoint 지속 실패 — {', '.join(f'{k}:{v}회/h' for k, v in critical_fails.items())}",
                "sig_payload": "",
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
    """2026-05-20: owner alert 완전 제거 (DISABLED).

    이유: tunnel 이 끊겨도 Sora 는 Gemini fallback 으로 정상 작동 (응답만 느려짐, 동작 보장).
    즉 owner 가 손쓸 일이 없는 internal ops 상태인데 P1/P2 alert 가 폰 스팸이 됨.
    owner '이건 왜자꾸 오는거야' 보고 → tunnel 알림 자체를 owner 채널에서 제거.
    tunnel 영속성은 Windows Task Scheduler keeper 가 desktop-home 측에서 자율 관리.
    내부 진단이 필요하면 ssh ysh-server 'ss -tlnp | grep 11434' 로 직접 확인.
    """
    return None  # owner alert 안 함 (영구 disable)


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
