# ============================================
# Sora PC Agent 설치 및 실행 (Windows PowerShell)
#
# 사용법:
#   # 집 PC에서:
#   .\scripts\install_pc_agent.ps1 -Id home-pc
#
#   # 회사 PC에서:
#   .\scripts\install_pc_agent.ps1 -Id work-pc
#
#   # 자동 시작 등록:
#   .\scripts\install_pc_agent.ps1 -Id home-pc -AutoStart
# ============================================
param(
    [Parameter(Mandatory=$true)]
    [string]$Id,

    [string]$Server = "wss://neo.heoyesol.kr/ws/pc-agent",
    [string]$Token = "sora-pc-agent-2026-yesol",
    [switch]$AutoStart
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Sora PC Agent Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PC ID:   $Id"
Write-Host "  Server:  $Server"
Write-Host ""

# 1. 필수 패키지 설치
Write-Host "[1/3] Python 패키지 설치..." -ForegroundColor Yellow
pip install websockets psutil pyperclip mss Pillow --quiet

# 2. 환경변수 설정
[Environment]::SetEnvironmentVariable("PC_AGENT_TOKEN", $Token, "User")
Write-Host "[2/3] 환경변수 PC_AGENT_TOKEN 설정 완료" -ForegroundColor Green

# 3. 시작 등록 (선택)
if ($AutoStart) {
    Write-Host "[3/3] 자동 시작 등록..." -ForegroundColor Yellow

    $AgentScript = Join-Path $ProjectRoot "scripts\sora_pc_agent.py"
    $TaskName = "SoraPCAgent-$Id"
    $Action = New-ScheduledTaskAction `
        -Execute "python" `
        -Argument "`"$AgentScript`" --id $Id --server $Server --token $Token"
    $Trigger = New-ScheduledTaskTrigger -AtLogon
    $Settings = New-ScheduledTaskSettingsSet -RestartCount 999 -RestartInterval (New-TimeSpan -Minutes 1)

    # 기존 태스크 제거
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "Sora PC Agent ($Id) - 클라우드 소라 원격 제어" `
        -RunLevel Highest

    Write-Host "  -> 작업 스케줄러 등록: $TaskName" -ForegroundColor Green
    Write-Host "  -> 로그온 시 자동 시작됩니다" -ForegroundColor Green
} else {
    Write-Host "[3/3] 자동 시작 건너뜀 (-AutoStart 플래그로 활성화)" -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  설치 완료!" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "실행 명령:" -ForegroundColor Yellow
Write-Host "  python $ProjectRoot\scripts\sora_pc_agent.py --id $Id --server $Server"
Write-Host ""

# 바로 실행
Write-Host "지금 바로 실행합니다..." -ForegroundColor Cyan
python "$ProjectRoot\scripts\sora_pc_agent.py" --id $Id --server $Server --token $Token
