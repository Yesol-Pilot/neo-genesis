# SSH Reverse Tunnel keeper — desktop-home Ollama (11434) -> ysh-server
# 2026-05-20 v4: PowerShell (batch 중첩 quoting 불안정 → 폐기). Task Scheduler 5분 트리거.
#
# 동작:
#   1. 11434 reverse-tunnel ssh 프로세스 존재 → no-op (살아있음)
#   2. 없으면: Ollama 죽었으면 살리고 → ssh -fN reverse tunnel 새로 연결
#
# 검증: ssh ysh-server "curl -s http://localhost:11434/api/version"

$ErrorActionPreference = 'SilentlyContinue'

# 1) 기존 터널 ssh 프로세스 확인
$tun = Get-CimInstance Win32_Process -Filter "Name='ssh.exe'" |
    Where-Object { $_.CommandLine -like '*11434*' }
if ($tun) {
    # 살아있음 — no-op
    exit 0
}

# 2) Ollama 살아있는지 — 죽었으면 기동
$oll = Get-Process ollama -ErrorAction SilentlyContinue
if (-not $oll) {
    Start-Process -FilePath 'ollama' -ArgumentList 'serve' -WindowStyle Hidden
    Start-Sleep -Seconds 5
}

# 3) reverse tunnel (fork, 백그라운드 persist)
Start-Process -FilePath 'ssh' -ArgumentList @(
    '-fN',
    '-o', 'ServerAliveInterval=30',
    '-o', 'ServerAliveCountMax=3',
    '-o', 'ExitOnForwardFailure=yes',
    '-o', 'StrictHostKeyChecking=accept-new',
    '-R', '0.0.0.0:11434:localhost:11434',
    'ysh-server'
) -WindowStyle Hidden
exit 0
