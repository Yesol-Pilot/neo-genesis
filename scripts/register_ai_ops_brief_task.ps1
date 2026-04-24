# Neo Genesis daily AI ops brief Task Scheduler registration.
$ErrorActionPreference = "Stop"

$taskName = "NeoGenesisDailyAIOpsBrief"
$projectRoot = "D:\00.test\neo-genesis"
$scriptPath = Join-Path $projectRoot "scripts\run_ai_ops_brief_pipeline.ps1"

$existing = Get-ScheduledTask -TaskName $taskName -ErrorAction SilentlyContinue
if ($existing) {
    Unregister-ScheduledTask -TaskName $taskName -Confirm:$false
}

$action = New-ScheduledTaskAction `
    -Execute "powershell.exe" `
    -Argument "-NoProfile -ExecutionPolicy Bypass -File `"$scriptPath`""
$trigger = New-ScheduledTaskTrigger -Daily -At 9:00AM
$settings = New-ScheduledTaskSettingsSet `
    -MultipleInstances IgnoreNew `
    -StartWhenAvailable:$false `
    -AllowStartIfOnBatteries

Register-ScheduledTask `
    -TaskName $taskName `
    -Action $action `
    -Trigger $trigger `
    -Settings $settings `
    -Force | Out-Null

Write-Host "Registered task: $taskName"
