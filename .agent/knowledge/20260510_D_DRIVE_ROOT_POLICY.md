# D Drive Root Directory Policy v1

> Created: 2026-05-10 KST
> Scope: `desktop-home` and Windows fleet devices using `D:` as the Neo Genesis work/data drive
> Related: `.agent/knowledge/20260510_C_DRIVE_MANAGEMENT_POLICY.md`, `.agent/knowledge/20260510_C_DRIVE_MIGRATION_RECORD.md`

## Conclusion

`D:\` is not a scratchpad. Agents must keep the D drive root readable and place new files under the standard category roots below. Do not create ad hoc project, log, export, installer, or one-off analysis folders directly under `D:\`.

Owner preference as of 2026-05-11: visible organizer directories should use three-digit prefixes starting at `001`. Do not rename app-managed roots or compatibility-critical roots in one sweep; converge by policy first, then migrate with manifests.

## D Root Target Taxonomy

Future D root organization should converge to these human-readable buckets:

| Prefix | Target | Owns |
|---:|---|---|
| `001` | `D:\001.workspace` | primary workspaces, including the eventual successor of `D:\00.test` |
| `002` | `D:\002.models-ai` | Ollama, HuggingFace, ComfyUI, and other model stores |
| `003` | `D:\003.agent-runtime` | agent caches, runtimes, state, automation roots |
| `004` | `D:\004.local-dev` | local tools, experiments, scratch repos |
| `005` | `D:\005.output` | generated exports, reports, screenshots, downloads archive |
| `006` | `D:\006.virtualization` | WSL, Docker, VM-like disk state |
| `007` | `D:\007.apps-managed` | app-managed paths that can only move through the owning app settings |
| `009` | `D:\009.archive` | reviewed drive-level archive and root cleanup evidence |

Compatibility note: `D:\models`, `D:\ComfyUI_models`, `D:\agent-cache`, `D:\automations`, `D:\local-dev`, `D:\output`, `D:\tmp`, `D:\mods`, `D:\steam`, `D:\agent-runtime`, and `D:\agent-state` are hidden junction aliases to numbered canonical roots. `D:\00.test`, `D:\wsl`, and `D:\docker` remain live non-junction roots. Do not remove old aliases until every config/env var is planned and verified.

## Allowed D Root Directories

These directories are allowed to remain directly under `D:\`:

| Root | Purpose |
|---|---|
| `D:\00.test` | Neo Genesis SSOT, projects, workspace, repo-level archives |
| `D:\models` | compatibility hidden junction to `D:\002.models-ai\models` |
| `D:\ComfyUI_models` | compatibility hidden junction to `D:\002.models-ai\ComfyUI_models` |
| `D:\agent-cache` | compatibility hidden junction to `D:\003.agent-runtime\cache` |
| `D:\agent-runtime` | compatibility hidden junction to `D:\003.agent-runtime\runtime` |
| `D:\agent-state` | compatibility hidden junction to `D:\003.agent-runtime\state` |
| `D:\automations` | compatibility hidden junction to `D:\003.agent-runtime\automations` |
| `D:\local-dev` | compatibility hidden junction to `D:\004.local-dev` |
| `D:\output` | compatibility hidden junction to `D:\005.output` |
| `D:\tmp` | compatibility hidden junction to `D:\005.output\tmp` |
| `D:\wsl` | WSL distributions |
| `D:\docker` | Docker Desktop disk data |
| `D:\steam`, `D:\mods`, `D:\Launcher` | game/app-managed paths; move only with app settings |
| `D:\KakaoTalk`, `D:\Telegram Desktop` | messenger app paths; move only after app config change |
| `D:\Creative App` | Creative service path; do not move while `Creative.VADMonitorService` exists |
| `D:\.claude` | hidden Claude root-local settings; do not move unless Claude config is updated |

Windows system roots such as `D:\$RECYCLE.BIN` and `D:\System Volume Information` are outside agent control.

## Default Placement Rules

| New artifact | Required location |
|---|---|
| New repo/worktree/project | `D:\00.test\<project>` or `D:\004.local-dev\<project>` |
| One-off local tool or unpacked binary | `D:\004.local-dev\tools\<tool>` |
| Temporary experiment | `D:\004.local-dev\experiments\<name>` |
| Script scratchpad | `D:\004.local-dev\scratch\<name>` |
| Generated report/export | `D:\005.output\<domain>\<date-or-run>` |
| Browser test artifacts | `D:\005.output\playwright\<project-or-run>` |
| Loose root files found during cleanup | `D:\00.test\009.archive\root-cleanup-YYYYMMDD\loose-root-files` |
| Old root experiment/project | `D:\00.test\009.archive\root-cleanup-YYYYMMDD\legacy-projects` |
| Old logs or diagnostics | `D:\00.test\009.archive\root-cleanup-YYYYMMDD\tool-logs` |

## 2026-05-10 Root Cleanup Applied

Moved from `D:\`:

| Original root path | New path |
|---|---|
| `D:\.playwright-cli` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\tool-logs\.playwright-cli` |
| `D:\app` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\misc\app` |
| `D:\google_calendar_tool` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\misc\google_calendar_tool` |
| `D:\AntiGravity` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\drive-shortcuts\AntiGravity` |
| root loose Korean `.txt` file | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\loose-root-files\` |
| `D:\llama.cpp` | `D:\local-dev\tools\llama.cpp` |

Moved or partially cleared:

| Path | Reason | Next action |
|---|---|---|
| `D:\agenttest` | Canonical git repo copied to `D:\00.test\006.games-labs\game-pipeline`; source root is now empty but Windows still holds its directory handle | HKCU RunOnce `RemoveEmptyAgenttest20260511` removes `D:\agenttest` only if it is still empty at next login |

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
4. Do not move `D:\wsl` or `D:\docker` without a supported WSL/Docker migration. Do not remove compatibility junctions without updating env/config references first.
5. Prefer moving old root clutter to `D:\00.test\009.archive\root-cleanup-YYYYMMDD\...` instead of deleting.

## D00.test Subdirectory Policy

`D:\00.test` has its own cleanup policy because project roots, generated artifacts, and backups have accumulated under the same flat directory:

- `.agent/knowledge/20260510_D00TEST_DIRECTORY_REORGANIZATION_POLICY.md`

Do not rename active `D:\00.test` project roots until that policy's compatibility and side-effect checks are complete.

## 2026-05-11 D Root Status

Conclusion: `D:\00.test` has been normalized to `001~010` buckets, and many `D:\` root categories now point to numbered canonical roots through hidden junctions. Remaining live non-junction roots need a dedicated compatibility pass before movement.

Current high-volume roots:

| Root | Approx size | Classification | Decision |
|---|---:|---|---|
| `D:\wsl` | 110.6 GB | platform disk | Keep; move only through WSL export/import |
| `D:\mods` | 104.3 GB | game/app managed | Keep; move only through app/library settings |
| `D:\models` | 98.8 GB | AI model store | Keep live path until Ollama/HF/Comfy consumers are audited |
| `D:\00.test` | 84.5 GB | active workspace SSOT | Keep root name until agent/RAG/process compatibility pass |
| `D:\steam` | 50.2 GB | app managed | Keep; move only through Steam library migration |
| `D:\agent-cache` | 26.5 GB | agent cache alias | Moved to `D:\003.agent-runtime\cache`; old path is a hidden junction |
| `D:\output` | 26.1 GB | generated exports/download archive | Candidate for future `005.output` migration |
| `D:\agent-runtime` | 17.9 GB | relocated runtime | Keep until env/junction audit |
| `D:\ComfyUI_models` | 17.3 GB | model store | Candidate to merge under future `002.models-ai` only after ComfyUI config audit |
| `D:\agent-state` | 15.0 GB | active agent state | Keep until Gemini/agent state audit |
| `D:\docker` | 12.1 GB | Docker Desktop disk | Keep; move only through Docker/WSL-supported migration |
| `D:\local-dev` | 4.9 GB | tools/experiments | Candidate for future `004.local-dev` migration |
| `D:\tmp` | 1.2 GB | disposable temp | Candidate for future `005.output\tmp` or cleanup pass |

Current live process blockers:

- `D:\KakaoTalk\KakaoTalk.exe` is running.
- `D:\Telegram Desktop\Telegram.exe` is running.
- Codex kernels are running with working directory `D:\00.test`.

Applied D root cleanup on 2026-05-11:

- `D:\agenttest` was classified as `Yesol-Pilot/game-pipeline`, copied and verified to `D:\00.test\006.games-labs\game-pipeline`.
- Old `D:\agenttest` is empty but locked by Windows; HKCU RunOnce `RemoveEmptyAgenttest20260511` removes it only if it is still empty at next login.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-phase5-d-root-agenttest-game-pipeline-move.json`.

Applied D root 001-category migration on 2026-05-11:

| Old compatibility path | New canonical path | Compatibility |
|---|---|---|
| `D:\models` | `D:\002.models-ai\models` | old path is a hidden junction |
| `D:\ComfyUI_models` | `D:\002.models-ai\ComfyUI_models` | old path is a hidden junction |
| `D:\automations` | `D:\003.agent-runtime\automations` | old path is a hidden junction |
| `D:\local-dev` | `D:\004.local-dev` | old path is a hidden junction |
| `D:\output` | `D:\005.output` | old path is a hidden junction |
| `D:\tmp` | `D:\005.output\tmp` | old path is a hidden junction |

Recovery note:

- `D:\tmp` hit a read-only `.git` descendant during `Move-Item`. It was recovered by `robocopy` copy-then-verify into `D:\005.output\tmp`; the old path was then replaced with a hidden junction.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-phase6-d-root-001-category-migration.json`.

Applied D root apps/runtime migration on 2026-05-11:

| Old compatibility path | New canonical path | Compatibility |
|---|---|---|
| `D:\mods` | `D:\007.apps-managed\mods` | old path is a hidden junction |
| `D:\steam` | `D:\007.apps-managed\steam` | old path is a hidden junction |
| `D:\agent-runtime` | `D:\003.agent-runtime\runtime` | old path is a hidden junction |
| `D:\agent-state` | `D:\003.agent-runtime\state` | old path is a hidden junction |

Verification:

- `python --version` and `conda --version` still pass after moving `D:\agent-runtime`.
- `D:\mods`, `D:\steam`, `D:\agent-runtime`, and `D:\agent-state` are hidden junction compatibility paths.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-phase7-d-root-app-runtime-migration.json`.

Applied D root agent-cache migration on 2026-05-11:

| Old compatibility path | New canonical path | Compatibility |
|---|---|---|
| `D:\agent-cache` | `D:\003.agent-runtime\cache` | old path is a hidden junction |

Verification:

- Stopped 18 Node processes whose command lines ran from `D:\agent-cache` (`http-server`, `serve`, and MCP servers) before moving.
- Remaining `D:\agent-cache` Node process count was 0 before the move.
- `D:\agent-cache\npm-cache` still resolves through the hidden junction after the move.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-phase8-d-root-agent-cache-migration.json`.

Applied D root visual hygiene on 2026-05-11:

| Path | Action | Compatibility |
|---|---|---|
| `D:\.claude` | set `Hidden` attribute only | path unchanged; Claude config remains valid |
| `D:\agenttest` | set `Hidden` attribute only | still empty and scheduled for RunOnce cleanup |

Verification:

- `D:\agenttest` remained empty but immediate removal still failed because another process holds the directory handle.
- HKCU RunOnce `RemoveEmptyAgenttest20260511` remains registered and removes `D:\agenttest` only if it is still empty at next login.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-phase9-d-root-visual-hide-residuals.json`.

Still deferred after phase 9:

- `D:\00.test` because it is the active workspace and Codex/MCP cwd target.
- `D:\wsl` and `D:\docker` because they require supported WSL/Docker migration.
- `D:\Creative App` because it is app/service-managed.
- `D:\KakaoTalk` and `D:\Telegram Desktop` because the apps are running.
- `D:\Launcher` because `Directory.Move` was denied even though Rockstar Service is stopped/manual.
- `D:\agenttest` because it is an empty locked residual folder scheduled for RunOnce cleanup.

Next safe D root migration strategy:

1. Stop app/agent processes in a maintenance window.
2. Move one category at a time into the `001~` target root.
3. Update environment variables, service settings, WSL/Docker config, and app library paths before removing old names.
4. Use junctions only as short transition aids; do not leave permanent duplicate-looking root aliases unless an app requires it.
5. Write a manifest under `D:\00.test\009.archive\reorg-manifests` for every D root move.
