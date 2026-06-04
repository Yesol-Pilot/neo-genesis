param(
  [ValidateSet("control", "generate", "upload", "monitor")]
  [string]$Role = "upload",
  [string]$StateDir = "",
  [string]$NodeId = "",
  [ValidateSet("", "prepare", "schedule", "publish")]
  [string]$UploadMode = "",
  [int]$IntervalSeconds = 60,
  [switch]$DisableLocalFallback,
  [switch]$Once
)

$ErrorActionPreference = "Stop"
$Root = Split-Path -Parent (Split-Path -Parent $MyInvocation.MyCommand.Path)
Set-Location -LiteralPath $Root

if ($StateDir) { $env:AINO_HA_STATE_DIR = $StateDir }
if ($NodeId) { $env:AINO_NODE_ID = $NodeId }
if (-not $env:AINO_HA_ENABLED) { $env:AINO_HA_ENABLED = "true" }
$CredentialFile = Join-Path $HOME ".neo-genesis\credentials.env"
if (Test-Path -LiteralPath $CredentialFile) {
  Get-Content -LiteralPath $CredentialFile | ForEach-Object {
    $line = $_.Trim()
    if (-not $line -or $line.StartsWith("#") -or -not $line.Contains("=")) { return }
    $key, $value = $line.Split("=", 2)
    $key = $key.Trim()
    $value = $value.Trim().Trim('"').Trim("'")
    if ($key -and -not [Environment]::GetEnvironmentVariable($key, "Process")) {
      [Environment]::SetEnvironmentVariable($key, $value, "Process")
    }
  }
}
$Python = if ($env:AINO_PYTHON) { $env:AINO_PYTHON } else { "python" }

$LogDir = Join-Path $Root "output\tiktok_aino_ha_state\worker_logs"
New-Item -ItemType Directory -Force -Path $LogDir | Out-Null
$LogPath = Join-Path $LogDir ("worker_{0:yyyyMMdd}.log" -f (Get-Date))

function Write-WorkerLog {
  param([string]$Message)
  $stamp = (Get-Date).ToString("yyyy-MM-ddTHH:mm:sszzz")
  Add-Content -LiteralPath $LogPath -Encoding UTF8 -Value "[$stamp][$Role] $Message"
}

function Invoke-HaPublisherJson {
  param(
    [string[]]$Arguments,
    [switch]$AllowFailure
  )
  Write-WorkerLog ("RUN python -m src.core.tiktok_aino.ha_publisher {0}" -f ($Arguments -join " "))
  $output = @(& $Python -m src.core.tiktok_aino.ha_publisher @Arguments 2>&1)
  $exitCode = if ($null -ne $LASTEXITCODE) { [int]$LASTEXITCODE } else { 0 }
  $text = ($output | ForEach-Object { $_.ToString() }) -join "`n"
  if ($text.Trim()) { Write-WorkerLog $text }
  $json = $null
  try {
    $json = $text | ConvertFrom-Json -ErrorAction Stop
  } catch {
    Write-WorkerLog ("JSON parse failed: {0}" -f $_.Exception.Message)
  }
  if ($exitCode -ne 0 -and -not $AllowFailure) {
    throw "ha_publisher exited with code $exitCode"
  }
  [PSCustomObject]@{
    ExitCode = $exitCode
    Json = $json
    Text = $text
  }
}

if ($Role -in @("generate", "monitor")) {
  Invoke-HaPublisherJson -Arguments @("release-node-leases", "--operation", $Role) | Out-Null
}

do {
  if ($Role -ne "upload") {
    Invoke-HaPublisherJson -Arguments @("heartbeat", "--capability", $Role) | Out-Null
  }
  if ($Role -eq "control") {
    Invoke-HaPublisherJson -Arguments @("controller-once") | Out-Null
  } elseif ($Role -eq "upload") {
    $effectiveNodeId = if ($env:AINO_NODE_ID) { $env:AINO_NODE_ID } else { $env:COMPUTERNAME.ToLower() }
    $mode = if ($UploadMode) { $UploadMode } elseif ($env:AINO_UPLOAD_MODE) { $env:AINO_UPLOAD_MODE } else { "schedule" }
    $remoteEnabledValue = [Environment]::GetEnvironmentVariable("AINO_REMOTE_UPLOAD_ENABLED", "Process")
    $remoteEnabled = $remoteEnabledValue -and $remoteEnabledValue.ToLowerInvariant() -in @("1", "true", "yes", "on")
    $remoteOk = $false
    if ($remoteEnabled) {
      $remote = Invoke-HaPublisherJson -Arguments @("--node-id", $effectiveNodeId, "remote-batch-upload", "--upload-mode", $mode) -AllowFailure
      $remoteActionCount = 0
      if ($null -ne $remote.Json) {
        foreach ($field in @("scheduled", "published", "prepared")) {
          if ($null -ne $remote.Json.$field) { $remoteActionCount += [int]$remote.Json.$field }
        }
      }
      $remoteOk = ($remote.ExitCode -eq 0 -and $null -ne $remote.Json -and $remote.Json.ok -eq $true -and $remoteActionCount -gt 0)
    } else {
      Write-WorkerLog "Remote upload path disabled; using local HA state."
    }
    if (-not $remoteOk) {
      if ($remoteEnabled) {
        Write-WorkerLog "Remote upload path unavailable or returned ok=false."
      }
      if ($DisableLocalFallback) {
        throw "remote upload failed and local fallback is disabled"
      }
      $postingGate = [Environment]::GetEnvironmentVariable("AINO_UPLOAD_AUTOMATION_ENABLED", "Process")
      $gateEnabled = $postingGate -and $postingGate.ToLowerInvariant() -in @("1", "true", "yes", "on")
      $localMode = $mode
      if ($mode -in @("schedule", "publish") -and -not $gateEnabled) {
        $localMode = "prepare"
        Write-WorkerLog "Posting gate is disabled; local fallback downgraded to prepare mode."
      }
      Invoke-HaPublisherJson -Arguments @("--node-id", $effectiveNodeId, "worker-once", "--operation", "upload", "--upload-mode", $localMode) | Out-Null
    }
  } else {
    Invoke-HaPublisherJson -Arguments @("worker-once", "--operation", $Role) | Out-Null
  }
  if ($Once) { break }
  Start-Sleep -Seconds ([Math]::Max(15, $IntervalSeconds))
} while ($true)
