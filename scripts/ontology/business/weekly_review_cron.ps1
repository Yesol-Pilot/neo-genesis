# Strategy Lead Weekly Review — Monday 10:05 KST wrapper
$ErrorActionPreference = "Continue"
Set-Location -Path "D:\00.test\neo-genesis"

$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Load .env (NEO4J creds 등)
$envFile = "D:\00.test\neo-genesis\.env"
if (Test-Path $envFile) {
    Get-Content $envFile | ForEach-Object {
        if ($_ -match "^\s*#") { return }
        if ($_ -match "^\s*$") { return }
        if ($_ -match "^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

# AuraDB fallback (chat 노출, owner declined rotation)
if (-not $env:NEO4J_BOLT_URI) {
    $env:NEO4J_BOLT_URI = "neo4j+s://394b2602.databases.neo4j.io"
}
if (-not $env:NEO4J_USER) { $env:NEO4J_USER = "neo4j" }
if (-not $env:NEO4J_PASSWORD) {
    $env:NEO4J_PASSWORD = "ZX01fB7-azGowhcr3shImY5UHzhzefDPTJ1AdyE_Czs"
}

$logDir = "D:\00.test\neo-genesis\.agent\ontology\cron_logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logFile = Join-Path $logDir ("weekly_review_" + (Get-Date -Format 'yyyyMMdd_HHmmss') + ".log")

"=== Strategy Lead Weekly Review ===" | Tee-Object -FilePath $logFile -Append
"Started: $(Get-Date)" | Tee-Object -FilePath $logFile -Append

python scripts\ontology\business\strategy_lead_weekly_review.py 2>&1 | Tee-Object -FilePath $logFile -Append
$exit = $LASTEXITCODE

"Finished: $(Get-Date) | exit_code=$exit" | Tee-Object -FilePath $logFile -Append

Get-ChildItem $logDir -Filter "weekly_review_*.log" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-60)
} | Remove-Item -Force

exit $exit
