# Neo Genesis Ontology daily maintenance — Windows Task Scheduler wrapper
# Registered as 'NeoGenesisOntologyDailyMaintain' daily 09:13 KST
# G1-31 자율 박제 (2026-05-14, Strategy Lead Claude Opus 4.7)

$ErrorActionPreference = "Continue"
Set-Location -Path "D:\00.test\neo-genesis"

# Encoding
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

# Load .env if exists (NEO4J_BOLT_URI / NEO4J_USER / NEO4J_PASSWORD 기대)
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

# AuraDB instance 394b2602 폐기 (2026-05-29): 9일째 NXDOMAIN (paused 아닌 삭제 확정).
# 로컬 JSONL + DuckDB + NetworkX 가 canonical operating store — cloud 미러 불필요.
# NEO4J fallback 제거 → daily_maintain neo4j step 이 SKIP (이전: 매일 2 WARN noise).
# 재생성 시: .env 에 NEO4J_BOLT_URI / NEO4J_USER / NEO4J_PASSWORD 추가하면 자동 재활성.
# (이전 fallback creds 는 git history + AURA_INSTANCE.md 에 보존)

# Log directory
$logDir = "D:\00.test\neo-genesis\.agent\ontology\cron_logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$logFile = Join-Path $logDir ("daily_maintain_" + (Get-Date -Format 'yyyyMMdd_HHmmss') + ".log")

# Run + capture
$startedAt = Get-Date
"=== Neo Genesis Ontology Daily Maintenance ===" | Tee-Object -FilePath $logFile -Append
"Started: $startedAt" | Tee-Object -FilePath $logFile -Append
""  | Tee-Object -FilePath $logFile -Append

python scripts\ontology\daily_maintain.py 2>&1 | Tee-Object -FilePath $logFile -Append
$exit = $LASTEXITCODE

""  | Tee-Object -FilePath $logFile -Append
"Finished: $(Get-Date) | exit_code=$exit" | Tee-Object -FilePath $logFile -Append

# Cleanup old logs (>14 days)
Get-ChildItem $logDir -Filter "daily_maintain_*.log" | Where-Object {
    $_.LastWriteTime -lt (Get-Date).AddDays(-14)
} | Remove-Item -Force

exit $exit
