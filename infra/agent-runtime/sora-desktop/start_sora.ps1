# =============================================================================
# start_sora.ps1 — Sora daemon WSL2 부팅 자동 기동 스크립트
# =============================================================================
#
# [용도]
#   Windows Task Scheduler 에서 호출해 PC 부팅 시 WSL2 sora daemon 을 자동 기동.
#   이미 떠 있으면 skip 하고 정상 종료 (idempotent).
#
# [Task Scheduler 등록 예시 — owner/메인이 검토 후 실행]
#   # 주의: 아래 명령은 스크립트 작성 참고용이며, 실제 등록은 하지 않음.
#   # owner 가 아래 명령을 관리자 PowerShell 에서 실행해야 한다.
#
#   $action  = New-ScheduledTaskAction `
#                -Execute "powershell.exe" `
#                -Argument "-NoProfile -ExecutionPolicy Bypass -File D:\00.test\neo-genesis\infra\agent-runtime\sora-desktop\start_sora.ps1"
#
#   $trigger = New-ScheduledTaskTrigger -AtStartup
#
#   $settings = New-ScheduledTaskSettingsSet `
#                 -ExecutionTimeLimit (New-TimeSpan -Minutes 5) `
#                 -RestartCount 2 `
#                 -RestartInterval (New-TimeSpan -Minutes 1)
#
#   $principal = New-ScheduledTaskPrincipal `
#                  -UserId "$env:USERDOMAIN\$env:USERNAME" `
#                  -LogonType Interactive `
#                  -RunLevel Highest
#
#   Register-ScheduledTask `
#     -TaskName "NeoGenesis-Sora-Startup" `
#     -Action $action `
#     -Trigger $trigger `
#     -Settings $settings `
#     -Principal $principal `
#     -Description "Neo Genesis sora daemon WSL2 부팅 자동 기동"
#
# [수동 실행]
#   powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\start_sora.ps1
#
# [롤백]
#   wsl.exe -- bash -lc "pkill -f neo_genesis_daemon"
#   # Task Scheduler 에서 등록했다면:
#   # Unregister-ScheduledTask -TaskName "NeoGenesis-Sora-Startup" -Confirm:$false
#
# =============================================================================

$ErrorActionPreference = "Stop"

$SCRIPT_NAME = "start_sora.ps1"
$SORA_DIR    = "/root/sora-live"
$DAEMON_BIN  = "venv/bin/python"
$DAEMON_MAIN = "neo_genesis_daemon.py"
$LOG_FILE    = "/root/sora-live/daemon.log"

Write-Host "[$SCRIPT_NAME] Sora daemon 기동 확인 시작..."

# --- 가드: 이미 떠 있으면 skip ---
$alreadyRunning = wsl.exe -- bash -lc "pgrep -fc $DAEMON_MAIN 2>/dev/null || echo 0"
$count = [int]($alreadyRunning.Trim())

if ($count -gt 0) {
    Write-Host "[$SCRIPT_NAME] sora daemon 이미 실행 중 (pgrep count=$count). skip."
    exit 0
}

Write-Host "[$SCRIPT_NAME] daemon 미실행 감지. WSL2 에서 기동 시작..."

# --- sora daemon 기동 (nohup + setsid, 완전히 분리된 백그라운드) ---
wsl.exe -- bash -lc @"
cd $SORA_DIR && \
TELEGRAM_POLLING=1 \
setsid nohup $DAEMON_BIN $DAEMON_MAIN > $LOG_FILE 2>&1 < /dev/null &
echo "daemon PID=\$!"
"@

Start-Sleep -Seconds 3

# --- 기동 확인 ---
$afterCount = wsl.exe -- bash -lc "pgrep -fc $DAEMON_MAIN 2>/dev/null || echo 0"
$afterCount = [int]($afterCount.Trim())

if ($afterCount -gt 0) {
    Write-Host "[$SCRIPT_NAME] sora daemon 기동 성공 (pgrep count=$afterCount)."
    exit 0
} else {
    Write-Error "[$SCRIPT_NAME] sora daemon 기동 실패. 로그 확인: wsl -- tail -30 $LOG_FILE"
    exit 1
}
