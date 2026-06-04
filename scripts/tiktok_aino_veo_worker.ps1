param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [string[]]$ArgsForWorker
)

$ErrorActionPreference = 'Stop'
$Repo = Split-Path -Parent $PSScriptRoot
Set-Location $Repo
python -m src.core.tiktok_aino.veo_automation @ArgsForWorker
exit $LASTEXITCODE
