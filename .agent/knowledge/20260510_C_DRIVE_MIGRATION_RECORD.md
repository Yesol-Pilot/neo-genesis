# C Drive Migration Record - desktop-home

> Date: 2026-05-10 KST
> Device: desktop-home
> Operator: Codex
> Canonical policy: `.agent/knowledge/20260510_C_DRIVE_MANAGEMENT_POLICY.md`

## Conclusion

C drive cleanup was completed with a move-first policy. Do not move these assets back to C, do not remove the junctions casually, and do not create new large agent state on C.

Final measured free space:

| Drive | Free space after cleanup |
|---|---:|
| `C:` | about `450.4 GiB` |
| `D:` | about `1287.3 GiB` |

Baseline before migration was about `112.1 GiB` free on `C:`. Net C recovery was about `338 GiB`.

## Current Junction And Relocation Map

| Original C path | Current D path | Mechanism | Verification |
|---|---|---|---|
| `C:\Users\yesol\.ollama\models` | `D:\models\ollama` | junction + `OLLAMA_MODELS` user env | `ollama list` passed |
| `C:\Users\yesol\.cache\huggingface` | `D:\models\huggingface` | junction + HF user env | path resolves to D |
| `C:\Users\yesol\.cache\puppeteer` | `D:\agent-cache\puppeteer` | junction + `PUPPETEER_CACHE_DIR` | path resolves to D |
| `C:\Users\yesol\.cache\whisper` | `D:\agent-cache\whisper` | junction | path resolves to D |
| `C:\Users\yesol\.cache\codex-runtimes` | `D:\agent-cache\codex-runtimes` | junction | path resolves to D |
| `C:\Users\yesol\AppData\Local\npm-cache` | `D:\agent-cache\npm-cache` | junction + npm config + user env | `npm config get cache` passed |
| `C:\Users\yesol\AppData\Local\ms-playwright` | `D:\agent-cache\ms-playwright` | junction + `PLAYWRIGHT_BROWSERS_PATH` | path resolves to D |
| `C:\Users\yesol\AppData\Local\ms-playwright-go` | `D:\agent-cache\ms-playwright-go` | junction | path resolves to D |
| `C:\Users\yesol\AppData\Local\Docker\wsl` | `D:\docker\wsl` | junction | Docker VHDX files present on D |
| `C:\Users\yesol\.gemini` | `D:\agent-state\gemini` | junction | path resolves to D |
| `C:\Users\yesol\miniconda3` | `D:\agent-runtime\miniconda3` | junction | `conda 25.9.1` and Python import check passed |

WSL was migrated by export/import, not by raw VHDX move:

| Distribution | Current path | Verification |
|---|---|---|
| `Ubuntu-24.04` | `D:\wsl\Ubuntu-24.04\ext4.vhdx` | `wsl -d Ubuntu-24.04` passed |

Downloads were moved, not deleted:

| Source | Archive |
|---|---|
| `C:\Users\yesol\Downloads\*` | `D:\output\downloads-archive\20260510` |

## User Environment Defaults Set

These are user-level environment variables. New terminals and agents should inherit them.

```powershell
TMP=D:\tmp
TEMP=D:\tmp
npm_config_cache=D:\agent-cache\npm-cache
PIP_CACHE_DIR=D:\agent-cache\pip
UV_CACHE_DIR=D:\agent-cache\uv
PLAYWRIGHT_BROWSERS_PATH=D:\agent-cache\ms-playwright
PUPPETEER_CACHE_DIR=D:\agent-cache\puppeteer
HF_HOME=D:\models\huggingface
HUGGINGFACE_HUB_CACHE=D:\models\huggingface\hub
TRANSFORMERS_CACHE=D:\models\huggingface\transformers
OLLAMA_MODELS=D:\models\ollama
```

Pip was also configured with:

```powershell
python -m pip config set global.cache-dir D:\agent-cache\pip
```

Npm was also configured with:

```powershell
npm config set cache D:\agent-cache\npm-cache --global
```

## Deleted Or Cleared Items

Only regenerable or explicitly disposable locations were cleared:

| Path | Action |
|---|---|
| `C:\Users\yesol\AppData\Local\NVIDIA\DXCache` | cleared |
| `C:\Users\yesol\AppData\Local\Temp` | cleared, locked files skipped |
| `C:\Users\yesol\AppData\Local\CrashDumps` | cleared |
| `C:\temp` | cleared |
| `C:\tmp` | cleared |

Google DriveFS internals, Chrome profile data, Claude app state, Codex app state, Windows folders, `Program Files`, and private `personal/` data were not manually moved or deleted.

## Known Residuals

| Residual | Status | Required next action |
|---|---|---|
| `C:\pagefile.sys` | still custom configured at `98304 MB` initial and `196608 MB` max | elevated Windows settings plus reboot; do not change from non-admin sessions |
| `C:\Users\yesol\miniconda3._old_20260510` | about `3.75 GiB` locked old DLL/PYD residue | HKCU RunOnce `DeleteOldMiniconda20260510` registered; retry after next login/reboot |
| Google DriveFS cache | about 40+ GiB class before cleanup; left untouched | change cache/location only through Google Drive app settings |
| Chrome/Claude/Codex live app state | left untouched while running | move only in stopped-agent maintenance window with app-specific rollback |

## Agent Rules After This Migration

1. Treat the C-path junctions above as compatibility shims. Do not replace them with real directories.
2. Before installing models, browsers, package caches, or temporary artifacts, check the D defaults first.
3. If a tool ignores user env vars and writes large data to C, stop and update this record plus the policy before continuing.
4. Do not run cleanup commands against `C:\Users\yesol\Downloads`; use the D archive path for older downloads.
5. Do not attempt pagefile or hibernation changes unless the session is elevated and a reboot/rollback plan is explicit.

## Quick Verification Commands

```powershell
Get-Item C:\Users\yesol\.ollama\models
Get-Item C:\Users\yesol\.cache\huggingface
Get-Item C:\Users\yesol\AppData\Local\npm-cache
Get-Item C:\Users\yesol\AppData\Local\Docker\wsl
Get-Item C:\Users\yesol\.gemini
Get-Item C:\Users\yesol\miniconda3
ollama list
wsl -d Ubuntu-24.04 -e sh -lc "whoami; df -h /"
C:\Users\yesol\miniconda3\Scripts\conda.exe --version
Get-CimInstance Win32_PageFileUsage
```
