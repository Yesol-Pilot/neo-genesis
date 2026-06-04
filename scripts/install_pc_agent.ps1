# Windows installer/launcher for Sora PC Agent.
# Token handling rule: keep PC_AGENT_TOKEN in the user environment, never in a
# process command line or scheduled-task action.
param(
    [Parameter(Mandatory = $true)]
    [string]$Id,

    [string]$Server = "",
    [string]$Token = "",
    [switch]$AutoStart
)

$ErrorActionPreference = "Stop"
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
$AgentScript = Join-Path $ProjectRoot "scripts\sora_pc_agent.py"

if (-not $Server) {
    $Server = [Environment]::GetEnvironmentVariable("SORA_PC_AGENT_SERVER", "User")
}
if (-not $Server) {
    $Server = $env:SORA_PC_AGENT_SERVER
}
if (-not $Server) {
    throw "SORA_PC_AGENT_SERVER is required. Pass -Server or set the user environment variable."
}

$EffectiveToken = $Token
if (-not $EffectiveToken) {
    $EffectiveToken = [Environment]::GetEnvironmentVariable("PC_AGENT_TOKEN", "User")
}
if (-not $EffectiveToken) {
    $EffectiveToken = $env:PC_AGENT_TOKEN
}
if (-not $EffectiveToken) {
    throw "PC_AGENT_TOKEN is required. Pass -Token once or set the user environment variable."
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  Sora PC Agent Installer" -ForegroundColor Cyan
Write-Host "========================================" -ForegroundColor Cyan
Write-Host "  PC ID:   $Id"
Write-Host "  Server:  $Server"
Write-Host "  Token:   present (not printed)"
Write-Host ""

Write-Host "[1/3] Installing Python packages..." -ForegroundColor Yellow
pip install websockets psutil pyperclip mss Pillow --quiet

if ($Token) {
    [Environment]::SetEnvironmentVariable("PC_AGENT_TOKEN", $EffectiveToken, "User")
    Write-Host "[2/3] PC_AGENT_TOKEN saved to the user environment" -ForegroundColor Green
}
else {
    Write-Host "[2/3] PC_AGENT_TOKEN already available" -ForegroundColor Green
}
[Environment]::SetEnvironmentVariable("SORA_PC_AGENT_SERVER", $Server, "User")
$env:PC_AGENT_TOKEN = $EffectiveToken
$env:SORA_PC_AGENT_SERVER = $Server
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

if ($AutoStart) {
    Write-Host "[3/3] Registering scheduled task..." -ForegroundColor Yellow

    $TaskName = "SoraPCAgent-$Id"
    $Action = New-ScheduledTaskAction `
        -Execute "python" `
        -Argument "`"$AgentScript`" --id `"$Id`" --server `"$Server`""
    $Trigger = New-ScheduledTaskTrigger -AtLogon
    $Settings = New-ScheduledTaskSettingsSet `
        -RestartCount 999 `
        -RestartInterval (New-TimeSpan -Minutes 1) `
        -MultipleInstances IgnoreNew `
        -Hidden

    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

    Register-ScheduledTask `
        -TaskName $TaskName `
        -Action $Action `
        -Trigger $Trigger `
        -Settings $Settings `
        -Description "Sora PC Agent ($Id) remote control bridge" `
        -RunLevel Highest | Out-Null

    Write-Host "  -> Registered scheduled task: $TaskName" -ForegroundColor Green
}
else {
    Write-Host "[3/3] Auto-start skipped. Use -AutoStart to register a scheduled task." -ForegroundColor DarkGray
}

Write-Host ""
Write-Host "========================================" -ForegroundColor Green
Write-Host "  Install complete" -ForegroundColor Green
Write-Host "========================================" -ForegroundColor Green
Write-Host ""
Write-Host "Run command:" -ForegroundColor Yellow
Write-Host "  python `"$AgentScript`" --id `"$Id`" --server `"$Server`""
Write-Host ""

Write-Host "Starting now..." -ForegroundColor Cyan
python "$AgentScript" --id $Id --server $Server
