# Neo Genesis daily AI ops brief pipeline.
param(
    [switch]$SkipTelegram
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot

function Import-DotEnv {
    param(
        [Parameter(Mandatory = $true)]
        [string]$Path
    )

    if (-not (Test-Path $Path)) {
        return
    }

    foreach ($line in Get-Content $Path) {
        $trimmed = $line.Trim()
        if (-not $trimmed -or $trimmed.StartsWith("#")) {
            continue
        }

        if ($trimmed.StartsWith("export ")) {
            $trimmed = $trimmed.Substring(7).Trim()
        }

        $parts = $trimmed -split "=", 2
        if ($parts.Count -ne 2) {
            continue
        }

        $name = $parts[0].Trim()
        $value = $parts[1].Trim()
        if ($value.StartsWith('"') -and $value.EndsWith('"') -and $value.Length -ge 2) {
            $value = $value.Substring(1, $value.Length - 2)
        }
        elseif ($value.StartsWith("'") -and $value.EndsWith("'") -and $value.Length -ge 2) {
            $value = $value.Substring(1, $value.Length - 2)
        }

        if ($name) {
            Set-Item -Path "Env:$name" -Value $value
        }
    }
}

Import-DotEnv (Join-Path $ProjectRoot ".env")
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

$Python = (Get-Command python -ErrorAction SilentlyContinue).Source
if (-not $Python) {
    $Python = (Get-Command py -ErrorAction SilentlyContinue).Source
}
if (-not $Python) {
    throw "Python executable not found."
}

$BriefDir = Join-Path $ProjectRoot "data\automation\ai_ops_brief"
if (-not (Test-Path $BriefDir)) {
    New-Item -ItemType Directory -Path $BriefDir -Force | Out-Null
}

$LockPath = Join-Path $BriefDir "daily_ai_ops_brief.lock"
$LockTimeoutMinutes = 90
$LockStream = $null

try {
    if (Test-Path $LockPath) {
        $lockAge = (Get-Date) - (Get-Item $LockPath).LastWriteTime
        if ($lockAge.TotalMinutes -gt $LockTimeoutMinutes) {
            Remove-Item $LockPath -Force -ErrorAction SilentlyContinue
        }
    }

    $LockStream = [System.IO.File]::Open($LockPath, [System.IO.FileMode]::CreateNew, [System.IO.FileAccess]::Write, [System.IO.FileShare]::None)
    $LockPayload = [System.Text.Encoding]::UTF8.GetBytes(("pid={0}`nstarted_at={1:o}`n" -f $PID, (Get-Date)))
    $LockStream.Write($LockPayload, 0, $LockPayload.Length)
    $LockStream.Flush()
}
catch {
    Write-Output "ai_ops_brief_skipped=lock_exists"
    exit 0
}

$Stamp = Get-Date -Format "yyyyMMdd_HHmmss"
$BriefPath = Join-Path $BriefDir "$Stamp`_brief.md"
$ArchiveDir = Join-Path $BriefDir "archive"

try {
    & $Python "scripts\build_ai_ops_brief.py" --output-file $BriefPath --archive-dir $ArchiveDir
    $pushArgs = @("scripts\push_ai_ops_brief_to_sora.py", "--input-file", $BriefPath, "--timeout-sec", "45")
    if ($SkipTelegram) {
        $pushArgs += "--skip-telegram"
    }
    & $Python @pushArgs
}
finally {
    if ($LockStream) {
        $LockStream.Close()
    }
    Remove-Item $LockPath -Force -ErrorAction SilentlyContinue
}
