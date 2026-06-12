# Neo Genesis Revenue OS budget pacer Windows Task Scheduler wrapper
# Registered as 'NeoGenesisBudgetPacer' daily 09:30 KST

$ErrorActionPreference = "Stop"

$repoRoot = "D:\00.test\neo-genesis"
$pythonExe = "C:\Users\yesol\miniconda3\python.exe"
$scriptPath = "scripts\revenue_os\gemini_budget_pacer.py"
$jobName = "budget_pacer"

Set-Location -Path $repoRoot

[Console]::OutputEncoding = [System.Text.UTF8Encoding]::new($false)
$OutputEncoding = [Console]::OutputEncoding
$env:PYTHONIOENCODING = "utf-8"
$env:PYTHONUTF8 = "1"

foreach ($envFile in @(".env", ".env.local")) {
    $path = Join-Path $repoRoot $envFile
    if (Test-Path $path) {
        Get-Content -Encoding UTF8 $path | ForEach-Object {
            if ($_ -match "^\s*#") { return }
            if ($_ -match "^\s*$") { return }
            if ($_ -match "^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$") {
                $key = $matches[1]
                $value = $matches[2].Trim().Trim('"').Trim("'")
                [Environment]::SetEnvironmentVariable($key, $value, "Process")
            }
        }
    }
}

$logDir = Join-Path $repoRoot "output\revenue_os\cron_logs"
New-Item -ItemType Directory -Path $logDir -Force | Out-Null
$stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$logFile = Join-Path $logDir "$($jobName)_$stamp.log"
$stdoutFile = Join-Path $logDir "$($jobName)_$stamp.stdout.tmp"
$stderrFile = Join-Path $logDir "$($jobName)_$stamp.stderr.tmp"

try {
    "=== Neo Genesis Revenue OS Budget Pacer ===" | Tee-Object -FilePath $logFile -Append
    "Started: $(Get-Date -Format o)" | Tee-Object -FilePath $logFile -Append
    "Python: $pythonExe" | Tee-Object -FilePath $logFile -Append
    "Script: $scriptPath" | Tee-Object -FilePath $logFile -Append
    "" | Tee-Object -FilePath $logFile -Append

    if (-not (Test-Path $pythonExe)) {
        throw "Python executable not found: $pythonExe"
    }
    if (-not (Test-Path (Join-Path $repoRoot $scriptPath))) {
        throw "Script not found: $scriptPath"
    }

    $proc = Start-Process -FilePath $pythonExe `
        -ArgumentList @($scriptPath) `
        -WorkingDirectory $repoRoot `
        -NoNewWindow `
        -PassThru `
        -Wait `
        -RedirectStandardOutput $stdoutFile `
        -RedirectStandardError $stderrFile

    if (Test-Path $stdoutFile) {
        Get-Content -Encoding UTF8 $stdoutFile | Tee-Object -FilePath $logFile -Append
    }
    if (Test-Path $stderrFile) {
        Get-Content -Encoding UTF8 $stderrFile | Tee-Object -FilePath $logFile -Append
    }

    $exitCode = $proc.ExitCode
}
catch {
    "ERROR: $($_.Exception.Message)" | Tee-Object -FilePath $logFile -Append
    $exitCode = 1
}
finally {
    "" | Tee-Object -FilePath $logFile -Append
    "Finished: $(Get-Date -Format o) | exit_code=$exitCode" | Tee-Object -FilePath $logFile -Append
    Remove-Item -LiteralPath $stdoutFile,$stderrFile -Force -ErrorAction SilentlyContinue
    Get-ChildItem $logDir -Filter "$($jobName)_*.log" | Where-Object {
        $_.LastWriteTime -lt (Get-Date).AddDays(-30)
    } | Remove-Item -Force
}

exit $exitCode
