# start_litellm.ps1 — LiteLLM proxy on :4000
# 실행 전 조건:
#   1) llama-server (:8080, :8081) 가 먼저 떠 있어야 함
#   2) ops/local-llm/.env.local-llm 에 GEMINI_API_KEY, LITELLM_MASTER_KEY 존재

$ErrorActionPreference = "Stop"

$ProjectRoot = "D:/00.test/neo-genesis"
$ConfigPath  = "$ProjectRoot/ops/local-llm/litellm_config.yaml"
$EnvFile     = "$ProjectRoot/ops/local-llm/.env.local-llm"

if (-not (Test-Path $ConfigPath)) { throw "config not found: $ConfigPath" }

# .env.local-llm 를 프로세스 env 에 주입
if (Test-Path $EnvFile) {
    Get-Content $EnvFile | ForEach-Object {
        if ($_ -match "^\s*#")  { return }
        if ($_ -match "^\s*$")  { return }
        if ($_ -match "^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.*?)\s*$") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
    Write-Host "[litellm] env loaded from $EnvFile" -ForegroundColor DarkGray
} else {
    Write-Warning "[litellm] $EnvFile not found — proxy will start without local env overrides"
}

# 기존 .env 의 Gemini key 도 상속 (fallback 용)
$RootEnv = "$ProjectRoot/.env"
if (Test-Path $RootEnv) {
    Get-Content $RootEnv | ForEach-Object {
        if ($_ -match "^(SORA_GEMINI_API_KEY|GEMINI_API_KEY)\s*=\s*(.*?)\s*$") {
            [Environment]::SetEnvironmentVariable($matches[1], $matches[2], "Process")
        }
    }
}

if (-not $env:LITELLM_MASTER_KEY) {
    $env:LITELLM_MASTER_KEY = "sk-local-litellm-master"
    Write-Warning "LITELLM_MASTER_KEY not set - using default 'sk-local-litellm-master'"
}

# Force UTF-8 for YAML loading (Windows default cp949 breaks non-ASCII configs)
$env:PYTHONUTF8 = "1"
$env:PYTHONIOENCODING = "utf-8"

Write-Host "[litellm] starting on 127.0.0.1:4000 - config=$ConfigPath" -ForegroundColor Cyan

# 2026-05-04: sora-live 가 호출하는 port = 4400 / host = 0.0.0.0
# (Tailscale userspace networking 으로 docker bridge gateway → host 4400 routing)
$LitellmExe = "$env:LOCALAPPDATA\Packages\PythonSoftwareFoundation.Python.3.13_qbz5n2kfra8p0\LocalCache\local-packages\Python313\Scripts\litellm.exe"
if (Test-Path $LitellmExe) {
    & $LitellmExe --config $ConfigPath --port 4400 --host 0.0.0.0
} else {
    python -m litellm.proxy.proxy_cli --config $ConfigPath --port 4400 --host 0.0.0.0
}
