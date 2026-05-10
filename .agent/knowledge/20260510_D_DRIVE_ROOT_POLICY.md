# D Drive Root Directory Policy v1

> Created: 2026-05-10 KST
> Scope: `desktop-home` and Windows fleet devices using `D:` as the Neo Genesis work/data drive
> Related: `.agent/knowledge/20260510_C_DRIVE_MANAGEMENT_POLICY.md`, `.agent/knowledge/20260510_C_DRIVE_MIGRATION_RECORD.md`

## Conclusion

`D:\` is not a scratchpad. Agents must keep the D drive root readable and place new files under the standard category roots below. Do not create ad hoc project, log, export, installer, or one-off analysis folders directly under `D:\`.

## Allowed D Root Directories

These directories are allowed to remain directly under `D:\`:

| Root | Purpose |
|---|---|
| `D:\00.test` | Neo Genesis SSOT, projects, workspace, repo-level archives |
| `D:\models` | AI model stores such as Ollama and HuggingFace |
| `D:\ComfyUI_models` | ComfyUI model store |
| `D:\agent-cache` | npm/pip/uv/browser/runtime caches |
| `D:\agent-runtime` | relocated runtimes such as Miniconda |
| `D:\agent-state` | relocated agent state such as Gemini |
| `D:\automations` | long-running automation roots |
| `D:\local-dev` | local tools, experiments, unpacked binaries, temporary dev repos |
| `D:\output` | generated exports, reports, screenshots, downloads archive |
| `D:\tmp` | disposable temporary files |
| `D:\wsl` | WSL distributions |
| `D:\docker` | Docker Desktop disk data |
| `D:\steam`, `D:\mods`, `D:\Launcher` | game/app-managed paths; move only with app settings |
| `D:\KakaoTalk`, `D:\Telegram Desktop` | messenger app paths; move only after app config change |
| `D:\Creative App` | Creative service path; do not move while `Creative.VADMonitorService` exists |
| `D:\.claude` | Claude root-local settings; do not move unless Claude config is updated |

Windows system roots such as `D:\$RECYCLE.BIN` and `D:\System Volume Information` are outside agent control.

## Default Placement Rules

| New artifact | Required location |
|---|---|
| New repo/worktree/project | `D:\00.test\<project>` or `D:\local-dev\<project>` |
| One-off local tool or unpacked binary | `D:\local-dev\tools\<tool>` |
| Temporary experiment | `D:\local-dev\experiments\<name>` |
| Script scratchpad | `D:\local-dev\scratch\<name>` |
| Generated report/export | `D:\output\<domain>\<date-or-run>` |
| Browser test artifacts | `D:\output\playwright\<project-or-run>` |
| Loose root files found during cleanup | `D:\00.test\_archive\root-cleanup-YYYYMMDD\loose-root-files` |
| Old root experiment/project | `D:\00.test\_archive\root-cleanup-YYYYMMDD\legacy-projects` |
| Old logs or diagnostics | `D:\00.test\_archive\root-cleanup-YYYYMMDD\tool-logs` |

## 2026-05-10 Root Cleanup Applied

Moved from `D:\`:

| Original root path | New path |
|---|---|
| `D:\.playwright-cli` | `D:\00.test\_archive\root-cleanup-20260510\tool-logs\.playwright-cli` |
| `D:\app` | `D:\00.test\_archive\root-cleanup-20260510\misc\app` |
| `D:\google_calendar_tool` | `D:\00.test\_archive\root-cleanup-20260510\misc\google_calendar_tool` |
| `D:\AntiGravity` | `D:\00.test\_archive\root-cleanup-20260510\drive-shortcuts\AntiGravity` |
| root loose Korean `.txt` file | `D:\00.test\_archive\root-cleanup-20260510\loose-root-files\` |
| `D:\llama.cpp` | `D:\local-dev\tools\llama.cpp` |

Attempted but not moved:

| Path | Reason | Next action |
|---|---|---|
| `D:\agenttest` | Windows reported a file handle in use | Retry after reboot or during stopped-agent maintenance; intended target is `D:\00.test\_archive\root-cleanup-20260510\legacy-projects\agenttest` |

Intentionally left at root:

| Path | Reason |
|---|---|
| `D:\KakaoTalk` | running `KakaoTalk.exe` from this path |
| `D:\Telegram Desktop` | running `Telegram.exe` from this path |
| `D:\Creative App` | Windows service `Creative.VADMonitorService` runs from this path |
| `D:\Launcher` | Rockstar service path points here |
| `D:\steam`, `D:\mods` | game-managed paths; do not move without app/library migration |
| `D:\.claude` | local Claude settings |

## Hard Rules

1. Do not create new top-level folders under `D:\` without updating this policy.
2. Do not move app-managed folders just to make the root prettier. Update the owning app setting first.
3. Do not manually delete `.tmp.driveupload` or DriveFS-looking temporary directories. Treat them as app-managed.
4. Do not move `D:\wsl`, `D:\docker`, `D:\agent-runtime`, or `D:\agent-state` without updating the C migration record and verifying all linked tools.
5. Prefer moving old root clutter to `D:\00.test\_archive\root-cleanup-YYYYMMDD\...` instead of deleting.
