<#
Sora PC Agent - boot-time persistence installer (B2)

Purpose: Replace logon-based Startup vbs with boot-time Task Scheduler trigger,
so the agent runs from system boot even when owner is not logged in.

Install (admin OR current user, S4U logon does not require password):
  powershell.exe -ExecutionPolicy Bypass -File install_pc_agent_boot.ps1

Uninstall:
  powershell.exe -ExecutionPolicy Bypass -File install_pc_agent_boot.ps1 -Uninstall
#>
param([switch]$Uninstall)

$ErrorActionPreference = "Stop"
$TaskName = "SoraPCAgent"
$AgentPath = "D:\00.test\neo-genesis\scripts\sora_pc_agent.py"
$PythonW = "C:\Users\yesol\AppData\Local\Microsoft\WindowsApps\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\pythonw.exe"
$AgentArgs = '--id desktop-home --server ws://100.67.221.25:7700/ws/pc-agent --token sora-pc-agent-2026-yesol'

if ($Uninstall) {
    Write-Host "Uninstalling task '$TaskName'..."
    Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue
    Write-Host "Done."
    exit 0
}

# Pre-checks
if (-not (Test-Path $PythonW)) {
    Write-Error "pythonw.exe not found at: $PythonW"; exit 1
}
if (-not (Test-Path $AgentPath)) {
    Write-Error "agent script not found: $AgentPath"; exit 1
}

# Remove existing task with same name (allow reinstall)
Unregister-ScheduledTask -TaskName $TaskName -Confirm:$false -ErrorAction SilentlyContinue

# Action: run pythonw with agent script (no console)
$Action = New-ScheduledTaskAction -Execute $PythonW `
    -Argument "`"$AgentPath`" $AgentArgs"

# Trigger: at system startup + 60 sec delay (wait for network and Tailscale to stabilize)
$Trigger = New-ScheduledTaskTrigger -AtStartup
$Trigger.Delay = "PT60S"

# Principal: run as owner user with S4U logon (no password needed, no UI)
$Principal = New-ScheduledTaskPrincipal -UserId "yesol" -LogonType S4U -RunLevel Limited

# Settings: keep alive, restart on failure
$Settings = New-ScheduledTaskSettingsSet `
    -AllowStartIfOnBatteries `
    -DontStopIfGoingOnBatteries `
    -StartWhenAvailable `
    -ExecutionTimeLimit ([TimeSpan]::Zero) `
    -RestartCount 3 `
    -RestartInterval ([TimeSpan]::FromMinutes(1)) `
    -MultipleInstances IgnoreNew

Register-ScheduledTask -TaskName $TaskName `
    -Action $Action `
    -Trigger $Trigger `
    -Principal $Principal `
    -Settings $Settings `
    -Description "Sora PC Agent - Jarvis fabric persistent node (B2 boot-time)"

Write-Host ""
Write-Host "INSTALLED: $TaskName"
Write-Host "Trigger:   AtStartup + 60s delay"
Write-Host "Principal: yesol (S4U, no password)"
Write-Host "Restart:   3 attempts, 1 min interval"
Write-Host ""
Write-Host "Verify:   Get-ScheduledTask -TaskName $TaskName"
Write-Host "Manual:   Start-ScheduledTask -TaskName $TaskName"
Write-Host "Stop:     Stop-ScheduledTask -TaskName $TaskName"
Write-Host ""
Write-Host "Recommendation: delete Startup vbs to avoid duplicate agent:"
Write-Host "  Remove-Item `"$env:APPDATA\Microsoft\Windows\Start Menu\Programs\Startup\sora_pc_agent.vbs`""
