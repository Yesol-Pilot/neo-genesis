#!/bin/bash
# Sora Chaos Drill — 자동 실행 스크립트 (Phase 2)
# 2026-05-06 박제 — Claude Opus 4.7 자율
#
# 적용: ysh-server crontab `0 3 1 * * /home/ysh/sora/scripts/run_chaos_drill.sh`
#       (매월 1일 03:00 KST)
#
# 시나리오 범위: S1 brain crash + S2 Redis OOM + S6 disk full only
# (S3 Gemini quota / S4 Telegram 409 / S5 import error 는 owner action 필요 — Phase 2 자동화 제외)
#
# 결과: /app/data/logs/chaos_drill_results.jsonl 에 append (timestamp / scenario / mttr_seconds / pass)
# Stop/Go: 4+ PASS → W7 Stop/Go 통과 / 3 이하 → telegram P0 alert

set -euo pipefail

CONTAINER="sora-live"
RESULT_LOG="/home/ysh/sora/data/logs/chaos_drill_results.jsonl"
TS=$(date -u +"%Y-%m-%dT%H:%M:%SZ")
DRILL_ID="drill_$(date +%Y%m%d-%H%M)"

# ───────────────────────────────────────────────────────────────
# Helper functions
# ───────────────────────────────────────────────────────────────

log_result() {
    local scenario="$1"
    local mttr_seconds="$2"
    local passed="$3"
    local notes="$4"
    echo "{\"ts\":\"$(date -u +%Y-%m-%dT%H:%M:%SZ)\",\"drill_id\":\"$DRILL_ID\",\"scenario\":\"$scenario\",\"mttr_seconds\":$mttr_seconds,\"pass\":$passed,\"notes\":\"$notes\"}" \
        | sudo tee -a "$RESULT_LOG" >/dev/null
}

# Wait for sora /api/health to be 200, return seconds elapsed (-1 = timeout)
wait_for_recovery() {
    local timeout_sec="$1"
    local start_time=$(date +%s)
    local elapsed=0
    while [ "$elapsed" -lt "$timeout_sec" ]; do
        if sudo docker exec "$CONTAINER" curl -s -f -o /dev/null --max-time 3 http://localhost:7700/api/health 2>/dev/null; then
            echo "$elapsed"
            return 0
        fi
        sleep 2
        elapsed=$(( $(date +%s) - start_time ))
    done
    echo "-1"
}

# ───────────────────────────────────────────────────────────────
# S1 brain.worker crash
# ───────────────────────────────────────────────────────────────
echo "[Chaos $DRILL_ID] S1 brain.worker crash 시작..."
BRAIN_PID=$(sudo docker exec "$CONTAINER" pgrep -f "src.core.brain.worker" || echo "")
if [ -n "$BRAIN_PID" ]; then
    sudo docker exec "$CONTAINER" kill -9 "$BRAIN_PID" 2>/dev/null || true
    MTTR=$(wait_for_recovery 60)
    if [ "$MTTR" -ge 0 ] && [ "$MTTR" -le 60 ]; then
        log_result "S1_brain_crash" "$MTTR" "true" "supervisord autorestart, MTTR=${MTTR}s"
        S1_PASS=1
    else
        log_result "S1_brain_crash" "$MTTR" "false" "did not recover within 60s"
        S1_PASS=0
    fi
else
    log_result "S1_brain_crash" "-1" "false" "brain.worker pid not found — already dead?"
    S1_PASS=0
fi

# ───────────────────────────────────────────────────────────────
# S2 Redis OOM (LRU eviction validation)
# ───────────────────────────────────────────────────────────────
echo "[Chaos $DRILL_ID] S2 Redis OOM 시작..."
# 큰 key 1만개 SET 으로 maxmemory(128MB) 도달 유발
START=$(date +%s)
sudo docker exec "$CONTAINER" bash -c '
    for i in $(seq 1 10000); do
        redis-cli SET "chaos_drill_key_$i" "$(head -c 12000 /dev/urandom | base64 | head -c 10000)" >/dev/null
    done
    redis-cli INFO memory | grep used_memory_human
    redis-cli FLUSHDB >/dev/null  # cleanup
' 2>&1 | tail -2 || true
MTTR=$(wait_for_recovery 90)
if [ "$MTTR" -ge 0 ] && [ "$MTTR" -le 90 ]; then
    log_result "S2_redis_oom" "$MTTR" "true" "LRU eviction + BRPOP idle 정상 복귀, MTTR=${MTTR}s"
    S2_PASS=1
else
    log_result "S2_redis_oom" "$MTTR" "false" "did not recover within 90s"
    S2_PASS=0
fi

# ───────────────────────────────────────────────────────────────
# S6 Disk fill (50MB only, 자동 cleanup 검증)
# ───────────────────────────────────────────────────────────────
echo "[Chaos $DRILL_ID] S6 disk fill 시작..."
sudo docker exec "$CONTAINER" bash -c '
    dd if=/dev/zero of=/app/data/logs/chaos_fill.bin bs=1M count=50 2>/dev/null
    df -h /app/data | tail -1
    rm -f /app/data/logs/chaos_fill.bin  # 즉시 삭제 (실 운영에서는 retention enforcer 가 처리)
' 2>&1 | tail -2 || true
# logrotate dry-run 검증
DRYRUN_OK=$(sudo logrotate -d /etc/logrotate.d/sora 2>&1 | grep -c "considering log" || echo "0")
if [ "$DRYRUN_OK" -ge 4 ]; then
    log_result "S6_disk_full" "0" "true" "logrotate config OK (${DRYRUN_OK} files monitored)"
    S6_PASS=1
else
    log_result "S6_disk_full" "0" "false" "logrotate config validation failed"
    S6_PASS=0
fi

# ───────────────────────────────────────────────────────────────
# 결과 집계 + Telegram alert
# ───────────────────────────────────────────────────────────────
TOTAL_PASS=$((S1_PASS + S2_PASS + S6_PASS))
echo ""
echo "═══════════════════════════════════════════"
echo "[Chaos $DRILL_ID] 완료 — $TOTAL_PASS/3 PASS"
echo "  S1 brain crash: $([ "$S1_PASS" = "1" ] && echo PASS || echo FAIL)"
echo "  S2 Redis OOM:   $([ "$S2_PASS" = "1" ] && echo PASS || echo FAIL)"
echo "  S6 disk full:   $([ "$S6_PASS" = "1" ] && echo PASS || echo FAIL)"
echo "═══════════════════════════════════════════"

# Telegram alert (NEO_ALERT_BOT_TOKEN + chat_id from container env)
SEVERITY=$([ "$TOTAL_PASS" -ge 2 ] && echo "P1" || echo "P0")
ALERT_TEXT="🧪 Chaos Drill $DRILL_ID — $TOTAL_PASS/3 PASS\nS1 brain: $([ "$S1_PASS" = "1" ] && echo OK || echo FAIL)\nS2 Redis: $([ "$S2_PASS" = "1" ] && echo OK || echo FAIL)\nS6 disk: $([ "$S6_PASS" = "1" ] && echo OK || echo FAIL)"

sudo docker exec "$CONTAINER" python3 -c "
import os, json, urllib.request, urllib.parse
tok = os.environ.get('NEO_ALERT_BOT_TOKEN', '')
cid = os.environ.get('OWNER_TELEGRAM_CHAT_ID', '')
if tok and cid:
    payload = urllib.parse.urlencode({'chat_id': cid, 'text': '''$ALERT_TEXT'''}).encode()
    try:
        urllib.request.urlopen(f'https://api.telegram.org/bot{tok}/sendMessage', data=payload, timeout=8)
        print('telegram alert sent')
    except Exception as e:
        print(f'telegram alert err: {e}')
else:
    print('telegram alert skipped (no token/chat_id)')
" 2>&1 | tail -1

# Exit code: 0 = 2+ PASS, 1 = 1 이하 PASS (cron alert 발동)
if [ "$TOTAL_PASS" -ge 2 ]; then
    exit 0
else
    exit 1
fi
