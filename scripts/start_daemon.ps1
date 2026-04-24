$ErrorActionPreference = "Continue"

$ProjectRoot = "D:\00.test\neo-genesis"
Set-Location $ProjectRoot

$MaxRetries = 5
$RetryDelay = 30
$FailCount = 0
$script:RuntimeOwned = $false
$script:RedisAvailable = $false

$DaemonPidFile = Join-Path $ProjectRoot "daemon.pid"
$DashPidFile = Join-Path $ProjectRoot "dashboard.pid"
$TunnelPidFile = Join-Path $ProjectRoot "tunnel.pid"
$CredentialWatcherPidFile = Join-Path $ProjectRoot "credential_watcher.pid"
$BrainPidFile = Join-Path $ProjectRoot "brain_worker.pid"
$MaintenanceFlag = Join-Path $ProjectRoot "daemon.maintenance"
$LogDir = Join-Path $ProjectRoot "logs"

$RedisPort = 6379
$RedisAuthFile = Join-Path $ProjectRoot "data\automation\redis_password.txt"
$RedisWslDistro = if ($env:SORA_WSL_DISTRO) { $env:SORA_WSL_DISTRO } else { "Ubuntu-24.04" }
$BootstrapPythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $BootstrapPythonExe) {
    $BootstrapPythonExe = "python.exe"
}
$script:ResolvedRedisUrl = $null
$RedisWslEnabled = if ($env:SORA_ENABLE_WSL_REDIS_BOOTSTRAP) {
    $env:SORA_ENABLE_WSL_REDIS_BOOTSTRAP -match '^(?i:1|true|yes|on)$'
} else {
    $true
}

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

if (-not (Test-Path $LogDir)) {
    New-Item -ItemType Directory -Path $LogDir -Force | Out-Null
}

function Write-Log($msg) {
    $ts = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    "[$ts] $msg" | Out-File -Append -FilePath (Join-Path $LogDir "daemon_wrapper.log") -Encoding UTF8
}

function New-RedisPassword {
    $bytes = New-Object byte[] 32
    $rng = [System.Security.Cryptography.RandomNumberGenerator]::Create()
    try {
        $rng.GetBytes($bytes)
        return (($bytes | ForEach-Object { $_.ToString("x2") }) -join "")
    }
    finally {
        $rng.Dispose()
    }
}

function Get-OrCreateRedisPassword {
    if ($env:SORA_REDIS_PASSWORD) {
        return $env:SORA_REDIS_PASSWORD
    }

    if (Test-Path $RedisAuthFile) {
        $existing = (Get-Content $RedisAuthFile -Raw -ErrorAction SilentlyContinue).Trim()
        if ($existing) {
            return $existing
        }
    }

    $authDir = Split-Path -Parent $RedisAuthFile
    if (-not (Test-Path $authDir)) {
        New-Item -ItemType Directory -Path $authDir -Force | Out-Null
    }

    $password = New-RedisPassword
    Set-Content -Path $RedisAuthFile -Value $password -Encoding ASCII
    return $password
}

function Format-LocalRedisUrl($redisHost) {
    return ("redis://:{0}@{1}:{2}/0" -f $script:RedisPassword, $redisHost, $RedisPort)
}

function Test-RedisUrlNeedsLocalAuth($redisUrl) {
    if (-not $redisUrl) {
        return $true
    }

    try {
        $uri = [System.Uri]$redisUrl
        return (
            $uri.Scheme -eq "redis" -and
            ($uri.Host -in @("localhost", "127.0.0.1", "::1")) -and
            -not $uri.UserInfo
        )
    }
    catch {
        return $false
    }
}

$script:RedisPassword = Get-OrCreateRedisPassword
if (Test-RedisUrlNeedsLocalAuth $env:REDIS_URL) {
    $env:REDIS_URL = Format-LocalRedisUrl "localhost"
}

function Format-RedisUrlForLog($redisUrl) {
    if (-not $redisUrl) {
        return ""
    }
    return ($redisUrl -replace '(redis://:)[^@]+@', '$1***@')
}

function Test-RedisUrl($redisUrl) {
    $script = @'
from redis import Redis
import sys

url = sys.argv[1]
client = Redis.from_url(url, socket_connect_timeout=2, socket_timeout=2, decode_responses=True)
try:
    print("ok" if client.ping() else "fail")
finally:
    try:
        client.close()
    except Exception:
        pass
'@
    try {
        $raw = $script | & $BootstrapPythonExe - $redisUrl 2>$null
        return @($raw) -contains "ok"
    }
    catch {
        return $false
    }
}

function Get-WslPrimaryIp {
    try {
        $raw = @(wsl.exe -d $RedisWslDistro -- bash -lc "hostname -I 2>/dev/null" 2>$null)
        if (-not $raw) {
            return $null
        }

        $joined = ($raw -join " ").Trim()
        if (-not $joined) {
            return $null
        }

        foreach ($token in ($joined -split '\s+')) {
            if ($token -match '^\d{1,3}(\.\d{1,3}){3}$') {
                return $token
            }
        }
    }
    catch {
    }

    return $null
}

function Invoke-PythonProcessScan($pattern) {
    $script = @'
import os
import psutil
import sys

pattern = sys.argv[1].lower()
for process in psutil.process_iter(["pid", "cmdline"]):
    if process.info["pid"] == os.getpid():
        continue
    cmdline = process.info.get("cmdline") or []
    if not cmdline:
        continue
    executable = (cmdline[0] or "").lower()
    if "python" not in executable and not executable.endswith("py"):
        continue
    joined = " ".join(cmdline).lower()
    if pattern in joined:
        print(process.info["pid"])
'@
    try {
        $raw = $script | & $BootstrapPythonExe - $pattern 2>$null
        return @($raw | Where-Object { $_ -match '^\d+$' } | ForEach-Object { [int]$_ })
    }
    catch {
        return @()
    }
}

function Get-MatchingPythonProcessIds($pattern) {
    $pythonMatches = @(Invoke-PythonProcessScan $pattern)
    if ($pythonMatches.Count -gt 0) {
        return $pythonMatches
    }

    @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match '^python' -and
            $_.CommandLine -and
            $_.CommandLine -like "*$pattern*"
        } |
        Select-Object -ExpandProperty ProcessId)
}

function Stop-MatchingPythonProcesses($pattern, $name) {
    $pids = Get-MatchingPythonProcessIds $pattern
    foreach ($procId in $pids) {
        try {
            Stop-Process -Id $procId -Force -ErrorAction SilentlyContinue
            Write-Log "Stopped $name (PID: $procId)"
        }
        catch {
        }
    }
}

function Stop-MatchingNamedProcesses($processName, $argumentPattern, $displayName) {
    $procs = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -like $processName -and
            $_.CommandLine -and
            $_.CommandLine -like "*$argumentPattern*"
        })
    foreach ($proc in $procs) {
        try {
            Stop-Process -Id $proc.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Log "Stopped $displayName (PID: $($proc.ProcessId))"
        }
        catch {
        }
    }
}

function Stop-ListeningPortProcess($port, $displayName) {
    $listeners = @(Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue)
    foreach ($listener in $listeners) {
        try {
            Stop-Process -Id $listener.OwningProcess -Force -ErrorAction SilentlyContinue
            Write-Log "Stopped $displayName via port $port (PID: $($listener.OwningProcess))"
        }
        catch {
        }
    }
}

function Test-TcpPort($hostname, $port, $timeoutMs = 1500) {
    $client = New-Object System.Net.Sockets.TcpClient
    try {
        $async = $client.BeginConnect($hostname, $port, $null, $null)
        if (-not $async.AsyncWaitHandle.WaitOne($timeoutMs, $false)) {
            return $false
        }
        $null = $client.EndConnect($async)
        return $true
    }
    catch {
        return $false
    }
    finally {
        $client.Close()
    }
}

function Invoke-WslRedisBootstrap {
    if (-not $RedisWslEnabled) {
        Write-Log "Redis bootstrap skipped: SORA_ENABLE_WSL_REDIS_BOOTSTRAP disabled"
        return $false
    }

    $distros = @(wsl.exe -l -q 2>$null)
    if (-not $distros -or -not ($distros -contains $RedisWslDistro)) {
        Write-Log "Redis bootstrap skipped: WSL distro '$RedisWslDistro' not found"
        return $false
    }

    $script = @'
set -e
if command -v sudo >/dev/null 2>&1; then
  SUDO="sudo -n"
else
  SUDO=""
fi

if ! command -v redis-server >/dev/null 2>&1; then
  export DEBIAN_FRONTEND=noninteractive
  if [ -n "$SUDO" ]; then
    $SUDO apt-get update >/dev/null
    $SUDO apt-get install -y redis-server >/dev/null
  else
    apt-get update >/dev/null
    apt-get install -y redis-server >/dev/null
  fi
fi

REDIS_PASSWORD="$(tr -d '\r\n' < "__REDIS_PASSWORD_FILE__")"
if [ -z "$REDIS_PASSWORD" ]; then
  echo "missing redis password" >&2
  exit 1
fi

if command -v systemctl >/dev/null 2>&1; then
  if [ -n "$SUDO" ]; then
    $SUDO systemctl stop redis-server || true
  else
    systemctl stop redis-server || true
  fi
fi

if command -v service >/dev/null 2>&1; then
  if [ -n "$SUDO" ]; then
    $SUDO service redis-server stop || true
  else
    service redis-server stop || true
  fi
fi

if pgrep -x redis-server >/dev/null 2>&1; then
  if command -v redis-cli >/dev/null 2>&1; then
    redis-cli --no-auth-warning -a "$REDIS_PASSWORD" -p __REDIS_PORT__ shutdown nosave >/dev/null 2>&1 || true
    redis-cli -p __REDIS_PORT__ shutdown nosave >/dev/null 2>&1 || true
  fi
  if [ -n "$SUDO" ]; then
    $SUDO pkill -x redis-server >/dev/null 2>&1 || true
  else
    pkill -x redis-server >/dev/null 2>&1 || true
  fi
  sleep 1
fi

# WSL localhost forwarding is most reliable with wildcard bind.
# Redis also requires a runtime-local password because this queue carries Sora work decisions.
cat > /tmp/neo_genesis_redis.conf <<EOF
bind 0.0.0.0 ::
protected-mode yes
port __REDIS_PORT__
daemonize yes
requirepass $REDIS_PASSWORD
EOF
redis-server /tmp/neo_genesis_redis.conf
'@
    $script = $script.Replace("__REDIS_PORT__", [string]$RedisPort)
    $script = $script.Replace("__REDIS_PASSWORD_FILE__", (Convert-ToWslPath $RedisAuthFile))
    $scriptPath = Join-Path $LogDir "redis_bootstrap.sh"

    try {
        Set-Content -Path $scriptPath -Value $script -Encoding UTF8
        $wslScriptPath = Convert-ToWslPath $scriptPath
        $null = wsl.exe -d $RedisWslDistro -u root -- bash $wslScriptPath
        Start-Sleep -Seconds 2
        return (Test-RedisUrl (Format-LocalRedisUrl "localhost"))
    }
    catch {
        Write-Log "Redis bootstrap via WSL failed: $_"
        return $false
    }
}

function Get-RedisCandidateUrls {
    $candidates = New-Object System.Collections.Generic.List[string]
    if ($env:REDIS_URL) {
        $candidates.Add($env:REDIS_URL)
    }

    $localhostUrl = Format-LocalRedisUrl "localhost"
    if (-not $candidates.Contains($localhostUrl)) {
        $candidates.Add($localhostUrl)
    }

    $wslIp = Get-WslPrimaryIp
    if ($wslIp) {
        $wslUrl = Format-LocalRedisUrl $wslIp
        if (-not $candidates.Contains($wslUrl)) {
            $candidates.Add($wslUrl)
        }
    }

    return $candidates.ToArray()
}

function Ensure-RedisAvailable {
    foreach ($candidateUrl in (Get-RedisCandidateUrls)) {
        if (Test-RedisUrl $candidateUrl) {
            $script:ResolvedRedisUrl = $candidateUrl
            $env:REDIS_URL = $candidateUrl
            Write-Log "Redis already available via $(Format-RedisUrlForLog $candidateUrl)"
            return $true
        }
    }

    Write-Log "Redis unavailable on known URLs - attempting bootstrap"
    if (Invoke-WslRedisBootstrap) {
        foreach ($candidateUrl in (Get-RedisCandidateUrls)) {
            if (Test-RedisUrl $candidateUrl) {
                $script:ResolvedRedisUrl = $candidateUrl
                $env:REDIS_URL = $candidateUrl
                Write-Log "Redis bootstrap succeeded via $(Format-RedisUrlForLog $candidateUrl)"
                return $true
            }
        }

        Write-Log "Redis bootstrap completed but no candidate URL responded"
    }

    if ($script:ResolvedRedisUrl) {
        if (Test-RedisUrl $script:ResolvedRedisUrl) {
            $env:REDIS_URL = $script:ResolvedRedisUrl
            Write-Log "Redis fallback reused last known good URL $(Format-RedisUrlForLog $script:ResolvedRedisUrl)"
            return $true
        }
    }

    Write-Log "Redis bootstrap failed"
    return $false
}

function Convert-ToWslPath($windowsPath) {
    $normalized = $windowsPath -replace '\\', '/'
    if ($normalized -match '^([A-Za-z]):/(.*)$') {
        return "/mnt/$($matches[1].ToLower())/$($matches[2])"
    }
    throw "failed to convert Windows path to WSL path: $windowsPath"
}

function Test-DaemonWrapperCommandLine($commandLine) {
    if (-not $commandLine) {
        return $false
    }

    $normalized = $commandLine -replace '/', '\'
    if ($normalized -match '(?i)(^|\s)-Command(\s|$)') {
        return $false
    }
    return $normalized -match '(?i)(^|\s)-File\s+["'']?[^"''\s]*scripts\\start_daemon\.ps1["'']?'
}

function Stop-StaleDaemonWrappers {
    $currentWrapperPid = $PID
    $wrappers = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match 'powershell' -and
            $_.ProcessId -ne $currentWrapperPid -and
            (Test-DaemonWrapperCommandLine $_.CommandLine)
        })

    foreach ($wrapper in $wrappers) {
        $children = @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
            Where-Object { $_.ParentProcessId -eq $wrapper.ProcessId })
        foreach ($child in $children) {
            try {
                Stop-Process -Id $child.ProcessId -Force -ErrorAction SilentlyContinue
                Write-Log "Stopped stale wrapper child (PID: $($child.ProcessId), Parent: $($wrapper.ProcessId))"
            }
            catch {
            }
        }
        try {
            Stop-Process -Id $wrapper.ProcessId -Force -ErrorAction SilentlyContinue
            Write-Log "Stopped stale daemon wrapper (PID: $($wrapper.ProcessId))"
        }
        catch {
        }
    }
}

function Get-OtherDaemonWrappers {
    $currentWrapperPid = $PID
    @(Get-CimInstance Win32_Process -ErrorAction SilentlyContinue |
        Where-Object {
            $_.Name -match 'powershell' -and
            $_.ProcessId -ne $currentWrapperPid -and
            (Test-DaemonWrapperCommandLine $_.CommandLine)
        })
}

function Stop-ChildProcess($pidFile, $name) {
    if (Test-Path $pidFile) {
        $childPid = Get-Content $pidFile -ErrorAction SilentlyContinue
        if ($childPid) {
            $null = Stop-ProcessRobust $childPid $name
        }
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    }
}

function Stop-ProcessRobust($processId, $displayName, $timeoutSec = 5) {
    if (-not $processId) {
        return $true
    }

    $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if (-not $proc) {
        return $true
    }

    try {
        Stop-Process -Id $processId -Force -ErrorAction SilentlyContinue
        Wait-Process -Id $processId -Timeout $timeoutSec -ErrorAction SilentlyContinue
    }
    catch {
    }

    $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if (-not $proc) {
        Write-Log "Stopped $displayName (PID: $processId)"
        return $true
    }

    try {
        $cimProc = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
        if ($cimProc) {
            $result = Invoke-CimMethod -InputObject $cimProc -MethodName Terminate -ErrorAction SilentlyContinue
            Write-Log "Terminate requested for $displayName (PID: $processId, return=$($result.ReturnValue))"
        }
        Wait-Process -Id $processId -Timeout $timeoutSec -ErrorAction SilentlyContinue
    }
    catch {
    }

    $proc = Get-Process -Id $processId -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Log "WARN: failed to stop $displayName (PID: $processId)"
        return $false
    }

    Write-Log "Stopped $displayName (PID: $processId)"
    return $true
}

function Stop-PythonProcessesRobust($pattern, $name) {
    $pids = @(Get-MatchingPythonProcessIds $pattern)
    foreach ($procId in $pids) {
        $null = Stop-ProcessRobust $procId $name
    }
}

function Stop-AllChildren {
    if (-not $script:RuntimeOwned) {
        Write-Log "== Cleanup skipped: runtime not owned by this wrapper =="
        return
    }
    Write-Log "== Cleanup: stopping child processes =="
    Stop-ChildProcess $DashPidFile "Dashboard"
    Stop-ChildProcess $TunnelPidFile "Tunnel"
    Stop-ChildProcess $CredentialWatcherPidFile "CredentialWatcher"
    Stop-ChildProcess $BrainPidFile "BrainWorker"
    Stop-ChildProcess $DaemonPidFile "Daemon"
    Write-Log "== Cleanup complete =="
}

function Get-LiveManagedPid($pidFile, $processName) {
    if (-not (Test-Path $pidFile)) {
        return $null
    }

    $existingPid = Get-Content $pidFile -ErrorAction SilentlyContinue
    if (-not $existingPid) {
        return $null
    }

    $proc = Get-Process -Id $existingPid -ErrorAction SilentlyContinue
    if ($proc -and $proc.ProcessName -match $processName) {
        return $existingPid
    }

    Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
    return $null
}

function Test-ProcessCommandLine($processId, $pattern) {
    try {
        $proc = Get-CimInstance Win32_Process -Filter "ProcessId=$processId" -ErrorAction SilentlyContinue
        return ($proc -and $proc.CommandLine -and $proc.CommandLine -like "*$pattern*")
    }
    catch {
        return $false
    }
}

function Get-HealthyManagedPid($pidFile, $processName, $argumentPattern, $healthUrl = "") {
    $livePid = Get-LiveManagedPid $pidFile $processName
    if (-not $livePid) {
        return $null
    }

    if (-not (Test-ProcessCommandLine $livePid $argumentPattern)) {
        Remove-Item $pidFile -Force -ErrorAction SilentlyContinue
        return $null
    }

    if ($healthUrl) {
        try {
            $response = Invoke-WebRequest -UseBasicParsing $healthUrl -TimeoutSec 5
            if ($response.StatusCode -lt 200 -or $response.StatusCode -ge 500) {
                return $null
            }
        }
        catch {
            return $null
        }
    }

    return $livePid
}

function Ensure-BrainWorker($pythonExe) {
    $livePid = Get-LiveManagedPid $BrainPidFile "python"
    if ($livePid) {
        Write-Log "[4/5] Brain Worker already running (PID: $livePid)"
        return $true
    }

    $liveMatches = Get-MatchingPythonProcessIds "src.core.brain.worker"
    if ($liveMatches.Count -gt 0) {
        $liveMatches[0] | Out-File $BrainPidFile -Encoding ASCII -NoNewline
        Write-Log "[4/5] Brain Worker already running via scan (PID: $($liveMatches[0]))"
        return $true
    }

    try {
        Write-Log "[4/5] Brain Worker starting"
        $workerLog = Join-Path $LogDir "brain_worker.log"
        $workerProc = Start-Process $pythonExe `
            -ArgumentList "-m src.core.brain.worker" `
            -WorkingDirectory $ProjectRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $workerLog `
            -RedirectStandardError (Join-Path $LogDir "brain_worker_err.log") `
            -PassThru
        $workerProc.Id | Out-File $BrainPidFile -Encoding ASCII -NoNewline
        Write-Log "[4/5] Brain Worker started (PID: $($workerProc.Id))"
        return $true
    }
    catch {
        Write-Log "[4/5] Brain Worker start FAILED: $_"
        return $false
    }
}

if (-not (Test-Path $MaintenanceFlag)) {
    $otherWrappers = @(Get-OtherDaemonWrappers)
    if ($otherWrappers.Count -gt 0) {
        $wrapperPids = ($otherWrappers | Select-Object -ExpandProperty ProcessId) -join ", "
        Write-Log "Another daemon wrapper is already running (PID: $wrapperPids). Exiting current wrapper."
        exit 0
    }
}

$script:RuntimeOwned = $true
$null = Register-EngineEvent PowerShell.Exiting -Action {
    if (Get-Command Stop-AllChildren -ErrorAction SilentlyContinue) {
        Stop-AllChildren
    }
} -ErrorAction SilentlyContinue
trap {
    if (Get-Command Stop-AllChildren -ErrorAction SilentlyContinue) {
        Stop-AllChildren
    }
    break
}

if (Test-Path $MaintenanceFlag) {
    Write-Log "Maintenance flag detected - forcing cleanup before restart"
    Write-Log "Maintenance step 1: stop stale wrapper descendants"
    Stop-StaleDaemonWrappers
    Write-Log "Maintenance step 2: stop processes via PID files"
    Stop-ChildProcess $DashPidFile "Dashboard (maintenance)"
    Stop-ChildProcess $TunnelPidFile "Tunnel (maintenance)"
    Stop-ChildProcess $CredentialWatcherPidFile "CredentialWatcher (maintenance)"
    Stop-ChildProcess $BrainPidFile "BrainWorker (maintenance)"
    Stop-ChildProcess $DaemonPidFile "Daemon (maintenance)"
    Write-Log "Maintenance step 3: stop known process patterns"
    Stop-PythonProcessesRobust "neo_genesis_daemon.py" "Daemon (maintenance scan)"
    Stop-PythonProcessesRobust "src.core.sora_dashboard:app" "Dashboard (maintenance scan)"
    Stop-PythonProcessesRobust "src.core.neo_scheduler" "Neo Scheduler (maintenance scan)"
    Stop-PythonProcessesRobust "src.core.brain.worker" "Brain Worker (maintenance scan)"
    Stop-PythonProcessesRobust "credential_watch.py" "CredentialWatcher (maintenance scan)"
    Stop-MatchingNamedProcesses "cloudflared*" "tunnel run neo-genesis" "Tunnel (maintenance scan)"
    Write-Log "Maintenance step 4: stop listener on port 7700"
    Stop-ListeningPortProcess 7700 "Dashboard (maintenance port owner)"
    Remove-Item $MaintenanceFlag -Force -ErrorAction SilentlyContinue
    Write-Log "Maintenance cleanup complete"
    Start-Sleep -Seconds 3
}

$healthyDaemonPid = Get-HealthyManagedPid $DaemonPidFile "python" "neo_genesis_daemon.py"
if ($healthyDaemonPid) {
    Write-Log "Daemon already running (PID: $healthyDaemonPid)"
    exit 0
}

$liveDaemonPids = @(Get-MatchingPythonProcessIds "neo_genesis_daemon.py")
if ($liveDaemonPids.Count -gt 0) {
    Write-Log "Cleaning unmanaged daemon processes before startup (PID: $($liveDaemonPids -join ', '))"
    Stop-PythonProcessesRobust "neo_genesis_daemon.py" "Daemon (unmanaged pre-start)"
    Start-Sleep -Seconds 2
}

Stop-ChildProcess $DashPidFile "Dashboard (stale)"
Stop-ChildProcess $TunnelPidFile "Tunnel (stale)"
Stop-ChildProcess $CredentialWatcherPidFile "CredentialWatcher (stale)"
Stop-ChildProcess $BrainPidFile "BrainWorker (stale)"
Stop-MatchingPythonProcesses "src.core.neo_scheduler" "Neo Scheduler (stale)"
Stop-MatchingPythonProcesses "src.core.brain.worker" "Brain Worker (stale)"
Stop-MatchingPythonProcesses "credential_watch.py" "CredentialWatcher (stale)"

$PythonExe = (Get-Command python.exe -ErrorAction SilentlyContinue).Source
if (-not $PythonExe) { $PythonExe = "python.exe" }

$VenvPython = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (Test-Path $VenvPython) {
    & $VenvPython -c "import fastapi" 2>$null
    if ($LASTEXITCODE -eq 0) {
        $PythonExe = $VenvPython
        Write-Log "Using .venv Python: $VenvPython"
    }
    else {
        Write-Log "WARN: .venv missing fastapi, using system Python: $PythonExe"
    }
}

Write-Log "== NEO GENESIS Full System Starting (Python: $PythonExe) =="

$script:RedisAvailable = Ensure-RedisAvailable
if (-not $script:RedisAvailable) {
    Write-Log "[0/5] Redis unavailable - continuing without Brain Worker"
}

try {
    Write-Log "[1/5] Sora Dashboard starting on :7700"
    $dashLog = Join-Path $LogDir "sora_dashboard.log"
    $dashProc = Start-Process $PythonExe `
        -ArgumentList "-m uvicorn src.core.sora_dashboard:app --host 0.0.0.0 --port 7700 --log-level warning" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $dashLog `
        -RedirectStandardError (Join-Path $LogDir "sora_dashboard_err.log") `
        -PassThru
    $dashProc.Id | Out-File $DashPidFile -Encoding ASCII -NoNewline
    Write-Log "[1/5] Dashboard started (PID: $($dashProc.Id))"
}
catch {
    Write-Log "[1/5] Dashboard start FAILED: $_"
}

try {
    $cfExe = Get-Command cloudflared -ErrorAction SilentlyContinue
    if ($cfExe) {
        Write-Log "[2/5] Cloudflare Tunnel starting (neo.heoyesol.kr)"
        $cfLog = Join-Path $LogDir "cloudflare_tunnel.log"
        $cfProc = Start-Process cloudflared `
            -ArgumentList "tunnel run neo-genesis" `
            -WindowStyle Hidden `
            -RedirectStandardOutput $cfLog `
            -RedirectStandardError (Join-Path $LogDir "cloudflare_tunnel_err.log") `
            -PassThru
        $cfProc.Id | Out-File $TunnelPidFile -Encoding ASCII -NoNewline
        Write-Log "[2/5] Tunnel started (PID: $($cfProc.Id))"
    }
    else {
        Write-Log "[2/5] cloudflared not found - tunnel skipped"
    }
}
catch {
    Write-Log "[2/5] Tunnel start FAILED: $_"
}

try {
    Write-Log "[3/5] Credential watcher starting"
    $credLog = Join-Path $LogDir "credential_watcher.log"
    $credProc = Start-Process $PythonExe `
        -ArgumentList "scripts\credential_watch.py --poll-sec 15 --updated-by daemon" `
        -WorkingDirectory $ProjectRoot `
        -WindowStyle Hidden `
        -RedirectStandardOutput $credLog `
        -RedirectStandardError (Join-Path $LogDir "credential_watcher_err.log") `
        -PassThru
    $credProc.Id | Out-File $CredentialWatcherPidFile -Encoding ASCII -NoNewline
    Write-Log "[3/5] Credential watcher started (PID: $($credProc.Id))"
}
catch {
    Write-Log "[3/5] Credential watcher start FAILED: $_"
}

if ($script:RedisAvailable) {
    if (-not (Ensure-BrainWorker $PythonExe)) {
        Write-Log "[4/5] Brain Worker failed to start - aborting startup"
        Stop-AllChildren
        exit 1
    }
}
else {
    Write-Log "[4/5] Brain Worker skipped: Redis unavailable"
}

while ($FailCount -lt $MaxRetries) {
    if (-not $script:RedisAvailable) {
        $script:RedisAvailable = Ensure-RedisAvailable
        if ($script:RedisAvailable) {
            Write-Log "[4/5] Redis recovered - Brain Worker can start"
        }
    }

    if ($script:RedisAvailable) {
        if (-not (Ensure-BrainWorker $PythonExe)) {
            Write-Log "[4/5] Brain Worker restart failed"
            Stop-AllChildren
            exit 1
        }
    }
    else {
        Write-Log "[4/5] Brain Worker skipped: Redis unavailable"
    }

    Write-Log "[5/5] Starting daemon (attempt $($FailCount + 1)/$MaxRetries)"

    try {
        $daemonLog = Join-Path $LogDir "daemon_stdout.log"
        $daemonProc = Start-Process $PythonExe `
            -ArgumentList "neo_genesis_daemon.py" `
            -WorkingDirectory $ProjectRoot `
            -WindowStyle Hidden `
            -RedirectStandardOutput $daemonLog `
            -RedirectStandardError (Join-Path $LogDir "daemon_stderr.log") `
            -PassThru
        $daemonProc.Id | Out-File $DaemonPidFile -Encoding ASCII -NoNewline
        Write-Log "[5/5] Daemon started (PID: $($daemonProc.Id))"
        $daemonProc.WaitForExit()
        $liveDaemonPids = @(Get-MatchingPythonProcessIds "neo_genesis_daemon.py" |
            Where-Object { $_ -ne $daemonProc.Id })
        if ($daemonProc.ExitCode -eq 0 -and $liveDaemonPids.Count -gt 0) {
            Write-Log (
                "Daemon handoff detected after duplicate-start guard " +
                "(active PID: $($liveDaemonPids -join ', ')). Exiting wrapper without retry."
            )
            exit 0
        }
        if ($daemonProc.ExitCode -eq 0) {
            Write-Log "Daemon exited with code 0. Exiting wrapper without retry."
            exit 0
        }
    }
    catch {
        Write-Log "Daemon process error: $_"
    }

    $FailCount++
    Write-Log "Daemon exited! (fail count: $FailCount)"

    if ($FailCount -ge $MaxRetries) {
        Write-Log "Max retries reached. Stopping all services."
        Stop-AllChildren
        exit 1
    }

    Write-Log "Restarting daemon in $RetryDelay seconds..."
    Start-Sleep -Seconds $RetryDelay
}
