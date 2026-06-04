# D00.test Directory Reorganization Policy v1

> Created: 2026-05-11 KST under the existing `root-cleanup-20260510` maintenance window.
> Scope: `D:\00.test` and project-level subdirectories.
> Related: `D:\00.test\FOLDER_BIBLE.md`, `.agent/knowledge/20260510_D_DRIVE_ROOT_POLICY.md`, `.agent/knowledge/20260424_Directory_Cleanup_Audit_v1.md`

## Conclusion

`D:\00.test` has been converted to a numbered-bucket workspace, but a few high-risk active roots remain hidden in place until their locks clear. Do not solve the remaining cleanup with blind deletion or ad hoc archiving. Use the numbered taxonomy, verify references first, then move or merge in small batches.

`portfolio` has moved to `D:\00.test\003.portfolio-career\006.portfolio` with `D:\00.test\portfolio` preserved as a hidden junction. Renaming the remaining active project roots `D:\00.test\neo-genesis`, `D:\00.test\PAPER`, and `D:\00.test\project_yesol` is intentionally parked as of 2026-05-14 because long-running agent sessions keep holding those roots. Use the deferred cleanup script only during a manual maintenance window.

Google Drive must not mirror `D:\00.test` or active numbered buckets. `D:\00.test` contains live repositories, generated builds, `.git` state, agent runtime state, temp output, and compatibility junctions; Drive should receive only curated export snapshots or final deliverables.

## Target Numbered Taxonomy

Future normalized layout should converge toward these numbered buckets:

| Prefix | Bucket | Purpose |
|---:|---|---|
| `001` | `001.ssot-agent-runtime` | `neo-genesis`, `.agent`, generated adapters, shared-brain, runtime policies |
| `002` | `002.products-sbu` | SBU/product code, public sites, SaaS/product experiments |
| `003` | `003.portfolio-career` | `portfolio`, `project_yesol`, `jobsearch`, resume and application assets |
| `004` | `004.research-paper` | `PAPER`, EthicaAI, WhyLab, NeurIPS/arXiv assets |
| `005` | `005.client-work` | CTS/work/client deliverables and presentations |
| `006` | `006.games-labs` | `2dlivegame`, `multiverse-creature-lab`, game/lab experiments |
| `007` | `007.infra-tools` | WebPilot, security, cron daemons, local infra and helper engines |
| `008` | `008.mirrors-external` | `github_repos` and external mirrors not directly owned as primary working trees |
| `009` | `009.archive` | Reviewed historical backups, duplicates, old runs, and rollback bundles |
| `010` | `010.tmp-output` | Short-lived temp, test output, screenshots, generated exports |

Do not create these buckets and move active roots in one step. First update SSOT references and decide whether old paths remain as junctions or are migrated fully.

## Current High-Signal Findings

| Finding | Evidence | Decision |
|---|---|---|
| Root contains loose generated files | `acl_*.txt/json/hujson`, `devices*.json` had 0 reference samples in active scan | Moved to numbered cleanup archive |
| `cts_slides` duplicates `cts-presentation\slides` | 17 files, SHA256 identical, 0 reference samples | Moved duplicate copy to numbered cleanup archive |
| `source` is a stale WSL venv | `pyvenv.cfg` points to `/mnt/d/00.test/source`; no active process or exact path refs | Moved to legacy runtime archive |
| `scripts` root was empty | 0 files, 0 dirs | Moved to empty-root archive |
| `test-results` root was only `.last-run.json` | 0 reference samples | Moved to tool-results archive |
| `neo-genesis_untracked_backup_20260505_083608` was not safe to archive as a whole | It contained the active `quant-bot` git repo with `.env` and dirty work | Resolved on 2026-05-11 by extracting `auto-trading` to `002.products-sbu\quant-bot`, then archiving the reviewed wrapper |
| `why-engine-proxy` is documented | `FOLDER_BIBLE.md` references it as Cloudflare Worker | Leave until it is either registered under infra or merged |
| `sora-android` is referenced as an asset | Master asset data mentions it with `sora-app` | Leave until Sora mobile scope is clarified |
| `.tmp.drivedownload` and `.tmp.driveupload` are app-managed | Google Drive temporary roots | Do not move manually |
| Google Drive mirrored the live workspace | 2026-05-14 DriveFS state showed `D:\00.test` root, 1,710,975 mirrored items, and 31,967 queued uploads dominated by `neo-genesis\src\sbu\*.next` | Remove live repo/build roots from Drive scope through Drive settings; export curated snapshots instead |
| `_tmp` and `tmp` hold recent work output | Supercent/interview/deploy QA artifacts | Review before consolidating into `010.tmp-output` |

## Google Drive Boundary

Treat Google Drive as an external delivery/backup target, not as a live workspace location.

- Forbidden sync roots: `D:\00.test`, active numbered buckets, active repositories, `.git`, `.next`, `node_modules`, `.venv`, caches, logs, temp outputs, generated media, and agent runtime state.
- Allowed sync artifacts: curated docs, final reports, signed or approved deliverables, release ZIPs, manifest files, and explicit reviewed export snapshots.
- If a team needs a Drive copy of a project, generate a clean export package first and copy that package to Drive. Do not configure Drive to watch the working tree.
- Do not manually move or delete `.tmp.drivedownload`, `.tmp.driveupload`, or DriveFS internal state. Change scope in Google Drive app settings or during a stopped-app maintenance window.

## Applied Batch 1

Moved, not deleted:

| Original | New path |
|---|---|
| `D:\00.test\acl_current.hujson` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\00-loose-root-files\acl-device-snapshots\acl_current.hujson` |
| `D:\00.test\acl_headers.txt` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\00-loose-root-files\acl-device-snapshots\acl_headers.txt` |
| `D:\00.test\acl_new.json` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\00-loose-root-files\acl-device-snapshots\acl_new.json` |
| `D:\00.test\acl_post_headers.txt` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\00-loose-root-files\acl-device-snapshots\acl_post_headers.txt` |
| `D:\00.test\acl_response.txt` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\00-loose-root-files\acl-device-snapshots\acl_response.txt` |
| `D:\00.test\devices.json` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\00-loose-root-files\acl-device-snapshots\devices.json` |
| `D:\00.test\devices2.json` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\00-loose-root-files\acl-device-snapshots\devices2.json` |
| `D:\00.test\cts_slides` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\01-duplicate-folders\cts_slides__duplicate_of_cts-presentation_slides` |
| `D:\00.test\source` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\02-legacy-runtime\source__wsl-venv` |
| `D:\00.test\scripts` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\03-empty-root-dirs\scripts` |
| `D:\00.test\test-results` | `D:\00.test\009.archive\legacy-root-archive\root-cleanup-20260510\04-tool-results\test-results` |

Verification:

| Check | Result |
|---|---|
| Removed root paths absent | PASS for `cts_slides`, `source`, `scripts`, `test-results` |
| Archive targets present | PASS |
| `cts-presentation\slides` still complete | PASS, 17 files, 8.8 MB, `slide_01.jpg` through `slide_17.jpg` |

## Side Effect Map

| Change | Side effect | Mitigation |
|---|---|---|
| Move root loose files | Old ad hoc commands expecting those exact root files will not find them | Active reference scan found 0 samples; files preserved in archive |
| Move `cts_slides` duplicate | Someone browsing root no longer sees standalone slide copy | Hash-identical canonical copy remains in `cts-presentation\slides` |
| Move `source` venv | Any stale script using `/mnt/d/00.test/source` would fail | No active process; exact active path refs absent; venv is reproducible |
| Move empty `scripts` | Root-level `scripts` folder no longer exists | Folder was empty; project scripts stay under their owning projects |
| Move `test-results` | Playwright root state no longer at old root path | Only `.last-run.json`; preserved in tool-results archive |

## Next Batches

1. Merge or classify similar pairs:
   - `cts` + `cts-presentation` now live under `005.client-work`.
   - `why-engine` + `why-engine-proxy` now live under `002.products-sbu`.
   - `sora-app` + `sora-android` remain at root until Sora runtime impact is checked.
   - `neo-genesis` + `neo-genesis__sbu_autogrowth` remain at root until duplicate clone review is complete.
2. Review retained archive/output buckets with lifecycle rules: keep active rollback evidence, compress old reviewed backups, move generated outputs to `D:\output` or `D:\tmp`.
3. Do not read, move, or index `personal/` for cleanup.

## Applied Numbered Migration - 2026-05-11

Created numbered buckets:

- `001.ssot-agent-runtime`
- `002.products-sbu`
- `003.portfolio-career`
- `004.research-paper`
- `005.client-work`
- `006.games-labs`
- `007.infra-tools`
- `008.mirrors-external`
- `009.archive`
- `010.tmp-output`

Move manifests:

- `D:\00.test\009.archive\reorg-manifests\20260511-phase1-generated-output-and-low-risk-root.json`
- `D:\00.test\009.archive\reorg-manifests\20260511-phase1-low-risk-project-root-moves.json`
- `D:\00.test\009.archive\reorg-manifests\20260511-phase1-rag-path-updated-low-risk-moves.json`
- `D:\00.test\009.archive\reorg-manifests\20260511-phase1-reference-updated-infra-root-moves.json`
- `D:\00.test\009.archive\reorg-manifests\20260511-phase1-no-ref-client-mirror-proxy-moves.json`
- `D:\00.test\009.archive\reorg-manifests\20260511-phase1-reference-updated-game-infra-work-moves.json`
- `D:\00.test\009.archive\reorg-manifests\20260511-phase1-reference-updated-why-engine-move.json`
- `D:\00.test\009.archive\reorg-manifests\20260511-master-data-json-repair.json`
- `D:\00.test\009.archive\reorg-manifests\20260511-phase2-quant-bot-ssot-extraction.json`
- `D:\00.test\009.archive\reorg-manifests\20260511-phase3-three-digit-bucket-renames.json`
- `D:\00.test\009.archive\reorg-manifests\20260511-phase10-d00test-root-visible-numbered-migration.json`
- `D:\00.test\009.archive\reorg-manifests\20260511-phase11-d00test-bucket-child-numbering.json`
- `D:\00.test\009.archive\reorg-manifests\20260512-phase12-locked-root-recheck-and-directory-index.json`
- `D:\00.test\009.archive\reorg-manifests\20260512-phase13-neo-genesis-handle-blockers.json`
- `D:\00.test\009.archive\reorg-manifests\20260512-phase14-deferred-cleanup-handoff.json`
- `D:\00.test\009.archive\reorg-manifests\20260512-phase15-deferred-cleanup-first-run.json`
- `D:\00.test\009.archive\reorg-manifests\20260512-phase16-root-docs-cleanup.json`
- `D:\00.test\009.archive\reorg-manifests\20260512-phase17-remaining-root-handle-pinpoint.json`
- `D:\00.test\009.archive\reorg-manifests\20260512-phase18-deferred-cleanup-script-hardening.json`
- `D:\00.test\009.archive\reorg-manifests\20260512-phase19-deferred-cleanup-live-rerun.json`
- `D:\00.test\009.archive\reorg-manifests\20260514-phase20-deferred-cleanup-automation-paused.json`
- `D:\00.test\009.archive\reorg-manifests\20260514-phase21-visible-root-residual-cleanup.json`

Reference updates applied before moves:

- `neo-genesis/src/core/data/sora_context.json`
- `neo-genesis__sbu_autogrowth/src/core/data/sora_context.json`
- `CREDENTIAL_BIBLE.md`
- `portfolio/scripts/generate-brand-thumbs.mjs`
- `portfolio/data/projects-database.json`
- `portfolio/public/data/projects-database.json`
- `portfolio/public/data/master-portfolio.json`
- `project_yesol/master-data/scripts/_patch_projects_phase_b_20260424.py`
- `project_yesol/master-data/projects.json`
- `project_yesol/master-data/project-ref-triage.json`
- `project_yesol/master-data/master-asset-verified.json`

Verification:

- All move manifests parse as JSON.
- `sora_context.json` in both `neo-genesis` and `neo-genesis__sbu_autogrowth` parses as JSON after path updates.
- Exact old-path scans for moved roots return zero matches, excluding no-touch and rebuild/cache folders.
- Dirty git working trees were moved as-is; no user edits were reverted.

Additional 2026-05-11 repairs:

- Repaired parser-invalid `project_yesol/master-data/projects.json`, `project-ref-triage.json`, and `master-asset-verified.json`; corrupt originals are preserved under `D:\00.test\009.archive\master-data-json-repair-20260511`.
- Promoted active quant SSOT from `D:\00.test\neo-genesis_untracked_backup_20260505_083608\auto-trading` to `D:\00.test\002.products-sbu\quant-bot`.
- Archived the duplicate clean mirror from `008.mirrors-external\github_repos\quant-bot` to `009.archive\reviewed-clones\github_repos_quant-bot_clean_mirror_20260511`.
- Archived the remaining reviewed backup wrapper to `009.archive\reviewed-clones\neo-genesis_untracked_backup_20260505_083608__reviewed_after_quant_extract`.
- `quant-bot` still has a dirty working tree by design; do not revert or delete it during directory cleanup.

Three-digit numbering update:

- Owner requested `001~` numbering for intuitive drive/workspace management.
- Renamed prior `00/10/20/...` buckets to `001/002/003/.../010`.
- During the `006.games-labs` rename, PowerShell `Move-Item` partially copied `2dlivegame` and stopped on a read-only `.agent\bible\specs` directory. The partial destination was recovered by verified copy-then-remove of the old source; no source was deleted until every source file existed at the new destination with matching length.

Legacy root folder consolidation:

- Moved former root `_archive` contents into `D:\00.test\009.archive\legacy-root-archive`.
- Moved former root `_extracted` into `D:\00.test\003.portfolio-career\extracted-assets`.
- Updated hardcoded `D:\00.test\tmp\interview_supergent_20260430` script paths and moved the folder to `D:\00.test\010.tmp-output\interview_supergent_20260430`.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-phase4-legacy-root-folder-consolidation.json`.

Applied visible-root numbered migration on 2026-05-11:

Moved with hidden junction compatibility:

- `.claude` -> `001.ssot-agent-runtime\.claude`
- `.codex_tmp` -> `010.tmp-output\codex_tmp`
- `jobsearch` -> `003.portfolio-career\jobsearch`
- `sora-app` -> `002.products-sbu\sora-app`
- `sora-android` -> `002.products-sbu\sora-android`
- `neo-genesis__sbu_autogrowth` -> `001.ssot-agent-runtime\neo-genesis__sbu_autogrowth`

Hidden in place, not moved:

- `neo-genesis`: active agent SSOT/runtime root with running process references.
- `project_yesol`: move failed because a process holds the path.
- `portfolio`: moved on 2026-05-12 by the deferred cleanup script; old path is a hidden junction.
- `PAPER`: move failed because a process holds the path.
- `_secrets` and `personal`: protected no-touch roots; contents must not be read, indexed, moved, or summarized during cleanup.
- `.tmp.drivedownload` and `.tmp.driveupload`: Google Drive temp roots; app-managed and left untouched.

Default `Get-ChildItem D:\00.test -Directory` should now show only `001~010` buckets. Use `-Force` to see hidden compatibility paths.

Applied bucket-child numbering on 2026-05-11:

- Every default-visible first-level child under `001.ssot-agent-runtime`, `002.products-sbu`, `003.portfolio-career`, `005.client-work`, `006.games-labs`, `007.infra-tools`, `008.mirrors-external`, `009.archive`, and `010.tmp-output` now uses `001.*`, `002.*`, etc.
- Previous child names remain as hidden junction aliases, so old paths such as `003.portfolio-career\jobsearch`, `009.archive\reorg-manifests`, and `010.tmp-output\codex_tmp` still resolve.
- `004.research-paper` currently has no default-visible children because `PAPER` remains a hidden locked compatibility root at `D:\00.test\PAPER`.

Locked-root recheck on 2026-05-12:

- Created `D:\00.test\DIRECTORY_INDEX.md` as the quick navigation index for humans and agents.
- `neo-genesis` still has running process references (`start_pc_agent.bat`, Next on port 4041); keep it hidden in place.
- `project_yesol` and `PAPER` still fail root move with path-in-use even though command-line scan and Restart Manager report no direct lockers.
- `portfolio` was still blocked at this point; it was moved later by the first deferred cleanup run.
- Do not use copy-delete fallback for the remaining locked roots. Retry only in a maintenance window or after handle-level inspection.

Neo Genesis handle-level recheck on 2026-05-12:

- Stopped safe direct blockers first: `start_pc_agent.bat`, local `next start`, ToolPick Next build workers, and some D:/00.test MCP filesystem processes.
- Sysinternals `handle64.exe` still found open handles from `explorer.exe`, `python3.13.exe`, several `claude.exe` worktree sessions, `cmd.exe`, `node.exe`, and `node_repl.exe`.
- `neo-genesis` remains hidden in place. Do not force copy-delete this root.
- Next retry requires a maintenance window that closes Explorer windows under `neo-genesis`, Claude worktrees, and remaining node/node_repl processes under that root.

Deferred cleanup setup on 2026-05-12:

- Script: `D:\00.test\007.infra-tools\006.directory-maintenance\Invoke-D00TestDeferredCleanup.ps1`.
- Agents should run this after completing work under `D:\00.test`, after closing their own dev servers, MCP/filesystem sessions, worktrees, shells, browser previews, and output generators.
- The script checks process references and Sysinternals `handle64.exe`; if either shows a lock, it defers. It never copy-deletes these high-risk roots.
- Successful moves preserve old paths as hidden junctions and write a run manifest under `D:\00.test\009.archive\001.reorg-manifests\deferred-cleanup-runs`.
- Automation `d00test-deferred-cleanup` is paused as of 2026-05-14. Agents should not rely on background retries; close their own handles when done, and leave still-locked roots parked until a manual maintenance window.

First deferred cleanup run on 2026-05-12:

- Run manifest: `D:\00.test\009.archive\001.reorg-manifests\deferred-cleanup-runs\20260512-114952-d00test-deferred-cleanup.json`.
- The first run manifest was sanitized after PowerShell handle objects bloated the raw JSON. Raw evidence is compressed at `D:\00.test\009.archive\001.reorg-manifests\deferred-cleanup-runs\20260512-114952-d00test-deferred-cleanup.raw-large.zip`.
- Summary manifest: `D:\00.test\009.archive\001.reorg-manifests\20260512-phase15-deferred-cleanup-first-run.json`.
- `portfolio` moved to `D:\00.test\003.portfolio-career\006.portfolio`; `D:\00.test\portfolio` is now a hidden junction alias.
- `neo-genesis`, `project_yesol`, and `PAPER` were deferred because open handles remain.
- The cleanup script was tightened so future run manifests store handle owners as plain strings, not large PowerShell objects.

Second deferred cleanup run on 2026-05-12:

- Run manifest: `D:\00.test\009.archive\001.reorg-manifests\deferred-cleanup-runs\20260512-122052-d00test-deferred-cleanup.json`.
- `portfolio` was already a hidden junction alias.
- `neo-genesis` still had open handles from Explorer, Python, Claude worktrees, and other runtime processes.
- `project_yesol` and `PAPER` were deferred because handle scan timed out; no copy-delete fallback was used.

Root `docs` cleanup on 2026-05-12:

- Moved stray root report folder `D:\00.test\docs` to `D:\00.test\010.tmp-output\006.root-docs-reports`.
- Preserved `D:\00.test\docs` as a hidden junction alias for compatibility.
- Manifest: `D:\00.test\009.archive\001.reorg-manifests\20260512-phase16-root-docs-cleanup.json`.
- New reports should be created under the owning project or a numbered output bucket, not as a default-visible root folder.

Remaining hidden-root handle pinpoint on 2026-05-12:

- `neo-genesis`: still held by Explorer, Claude worktrees, Python, Node/node_repl/cmd-class runtime processes from the phase13/phase17 evidence.
- `project_yesol`: move preflight found Explorer handles on the root and Claude handles on both the root and `.claude`.
- `PAPER`: 600s handle scan found Claude handles on the root and `.claude`.
- Manifest: `D:\00.test\009.archive\001.reorg-manifests\20260512-phase17-remaining-root-handle-pinpoint.json`.
- Do not force stop unrelated sessions. The owning agents should close their worktrees or change cwd, then rerun deferred cleanup.

Deferred cleanup script hardening on 2026-05-12:

- Added per-root handle timeouts and slower defaults for `project_yesol` and `PAPER`.
- Added compact manifest fields: `processRefCount`, `handleOwnerCount`, per-root `handleTimeoutSeconds`, and grouped `handleOwnerSummary`.
- Truncated long process command lines in manifests.
- Excluded `handle64.exe` itself from process reference matching.
- Enforced timeout floors: `HandleTimeoutSeconds >= 60`, `SlowHandleTimeoutSeconds >= 180`.
- A 5-second dry-run produced a false `dry_run_would_move` for `neo-genesis`; do not lower timeout values to speed up cleanup.
- Manifest: `D:\00.test\009.archive\001.reorg-manifests\20260512-phase18-deferred-cleanup-script-hardening.json`.

Hardened deferred cleanup live rerun on 2026-05-12:

- Run manifest: `D:\00.test\009.archive\001.reorg-manifests\deferred-cleanup-runs\20260512-134714-d00test-deferred-cleanup.json`.
- Summary manifest: `D:\00.test\009.archive\001.reorg-manifests\20260512-phase19-deferred-cleanup-live-rerun.json`.
- No moves were performed.
- `neo-genesis` was blocked at process-ref stage by ToolPick Next build / jest-worker Node processes under `src\sbu\toolpick`.
- `project_yesol` was blocked by Explorer and Claude handles.
- `PAPER` was blocked by Claude handles.
- Do not stop these as part of directory cleanup unless the owning work is confirmed complete.

Deferred cleanup automation pause on 2026-05-14:

- Automation `d00test-deferred-cleanup` was changed from `ACTIVE` to `PAUSED`.
- No filesystem moves were attempted in this step.
- Remaining hidden real roots are parked intentionally: `D:\00.test\neo-genesis`, `D:\00.test\project_yesol`, and `D:\00.test\PAPER`.
- Manual retry is allowed only after the owning agents, shells, previews, and cwd references are closed or moved outside those roots.
- Manifest: `D:\00.test\009.archive\001.reorg-manifests\20260514-phase20-deferred-cleanup-automation-paused.json`.

Visible root residual cleanup on 2026-05-14:

- Moved root `.playwright-cli` browser/test artifacts to `D:\00.test\010.tmp-output\009.playwright-cli-root-artifacts-20260512`.
- Moved recreated root `neo-genesis_untracked_backup_20260505_083608` wrappers to `D:\00.test\009.archive\003.reviewed-clones\003.neo-genesis-untracked-backup-residual-20260514` and `D:\00.test\009.archive\003.reviewed-clones\004.neo-genesis-untracked-backup-residual-20260514-1403`.
- No deletes were performed.
- Manifest: `D:\00.test\009.archive\001.reorg-manifests\20260514-phase21-visible-root-residual-cleanup.json`.
