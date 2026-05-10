# C Drive Management Policy v1

> Created: 2026-05-10 KST
> Scope: desktop-home and any Windows fleet device used by Neo Genesis agents
> Goal: keep `C:` stable for Windows/runtime essentials, move large agent-created state to `D:` when safe.

## 1. Conclusion

`C:` cleanup must prefer relocation over deletion. Large model files, caches, temporary outputs, WSL/Docker disks, generated datasets, and exported archives created by agents should be moved or re-homed to `D:` whenever the tool supports it. Deletion is reserved for disposable caches, crash dumps, duplicate installers, or owner-approved personal/download artifacts.

## 2. C: Role

Allowed on `C:` by default:

- Windows, drivers, security tools, firmware/vendor utilities.
- Unavoidable app binaries under `Program Files` or Windows app package folders.
- Small user profile config, browser profile identity, credential stores.
- Active OS runtime files such as pagefile and hibernation files.

Do not create these on `C:`:

- New repositories, worktrees, generated datasets, crawl dumps, export archives.
- AI model weights, HuggingFace/Ollama/ComfyUI model caches.
- npm/pnpm/pip/uv/playwright/puppeteer bulk caches.
- WSL or Docker large virtual disks when a D-drive location is practical.
- Long-running agent temp output, screenshots, videos, logs, or one-off analysis artifacts.

## 3. D: Standard Paths

| Purpose | Default path |
|---|---|
| Project SSOT and repos | `D:\00.test\` |
| Large AI models | `D:\models\` |
| ComfyUI models | `D:\ComfyUI_models\` |
| Local isolated development | `D:\local-dev\` |
| Long-running automations | `D:\automations\` |
| Temporary files | `D:\tmp\` |
| Generated exports | `D:\output\` |
| Agent/package caches | `D:\agent-cache\` |
| WSL distribution VHDX | `D:\wsl\<distro>\` |
| Docker disk data | `D:\docker\` or Docker Desktop's D-drive disk image setting |

`D:\tmp\` is the single temporary root. Do not create a parallel `D:\temp\`.

## 4. Agent Environment Defaults

For commands or automations likely to create large caches, set these per process before running. Do not change global system environment variables unless the owner asks for that rollout or a rollback plan exists.

```powershell
$env:TMP = "D:\tmp"
$env:TEMP = "D:\tmp"
$env:npm_config_cache = "D:\agent-cache\npm-cache"
$env:PIP_CACHE_DIR = "D:\agent-cache\pip"
$env:UV_CACHE_DIR = "D:\agent-cache\uv"
$env:PLAYWRIGHT_BROWSERS_PATH = "D:\agent-cache\ms-playwright"
$env:PUPPETEER_CACHE_DIR = "D:\agent-cache\puppeteer"
$env:HF_HOME = "D:\models\huggingface"
$env:HUGGINGFACE_HUB_CACHE = "D:\models\huggingface\hub"
$env:TRANSFORMERS_CACHE = "D:\models\huggingface\transformers"
$env:OLLAMA_MODELS = "D:\models\ollama"
```

## 5. Cleanup Classification

| Class | Meaning | Action |
|---|---|---|
| `MOVE` | Valuable state that can run from `D:` | Move, update config, verify, then clean old source |
| `CACHE-REBUILD` | Re-downloadable or regenerable cache | Change cache path or delete after apps stop |
| `KEEP` | OS/app/account state directly required | Keep |
| `DELETE` | Duplicate, obsolete installer, crash dump, clear temp file | Delete only when low-risk or owner-approved |

Default sequence:

1. Measure size and owner impact.
2. Check whether D-drive relocation or config change is supported.
3. Stop the app/service if files are active.
4. Move or re-home, then run the tool.
5. Do not delete the old source before verification.

## 6. Current desktop-home Priorities

Measured on 2026-05-10:

| Item | Current path | Size | Policy |
|---|---|---:|---|
| WSL Ubuntu VHDX | `C:\Users\yesol\AppData\Local\wsl\...\ext4.vhdx` | 111.9GiB | Export/import to `D:\wsl\Ubuntu-24.04\`, verify, then remove old import |
| pagefile | `C:\pagefile.sys` | 96GiB reserved | Consider 32-64GiB admin change with reboot/rollback; do not change casually |
| Ollama models | `C:\Users\yesol\.ollama\models` | 53.1GiB | Move to `D:\models\ollama` with `OLLAMA_MODELS` |
| Recycle Bin | `C:\$Recycle.Bin` | 47.7GiB | Empty only after owner approval |
| Google DriveFS | `C:\Users\yesol\AppData\Local\Google\DriveFS` | 40.1GiB | Use Google Drive app settings; do not manually delete internals |
| HuggingFace cache | `C:\Users\yesol\.cache\huggingface` | 16.7GiB | Move to `D:\models\huggingface` or rebuild there |
| NVIDIA DXCache | `C:\Users\yesol\AppData\Local\NVIDIA\DXCache` | 15.4GiB | Regenerable cache; delete only after GPU apps close |
| Docker VHDX | `C:\Users\yesol\AppData\Local\Docker\wsl\disk` | 11.7GiB | Move through Docker Desktop settings |
| npm/pip caches | AppData Local caches | 19.2GiB | Point to `D:\agent-cache`, then prune |
| Downloads exports | `C:\Users\yesol\Downloads` | 18.2GiB | Separate duplicates from business/personal files before action |

## 7. Capacity Targets

| State | Criteria | Action |
|---|---|---|
| Target | `C:` free >= 200GiB | Normal |
| Warning | free < 150GiB or used > 80% | No new large C-drive work; inspect relocation candidates |
| Critical | free < 100GiB or used > 90% | Prepare immediate cache/Recycle Bin/WSL/Docker/Ollama plan |

## 8. Hard Prohibitions

- Do not read, move, or delete `personal/` or legal/financial/private documents for disk cleanup.
- Do not manually move/delete Google DriveFS `.tmp.driveupload`, `.tmp.drivedownload`, or internal DriveFS cache.
- Do not move WSL/Docker VHDX files by drag/drop or raw file move. Use export/import or official app settings.
- Do not manually delete `C:\Windows`, `Program Files`, or `ProgramData` contents.
- Do not change pagefile or hibernation without administrator context, reboot awareness, and rollback plan.

## 9. Verification

```powershell
Get-Volume -DriveLetter C,D
wsl.exe -l -v
ollama list
docker system df
Get-CimInstance Win32_PageFileUsage
```

After any migration, verify both the tool behavior and `C:` free space.
