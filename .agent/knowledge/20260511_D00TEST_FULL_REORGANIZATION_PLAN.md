# D00.test Full Reorganization Plan v1

> Created: 2026-05-11 KST
> Scope: `D:\`, `D:\00.test`, and `D:\00.test` project-level subdirectories.
> Mode: analysis and design only. Do not execute broad moves from this document without the phase gates below.
> Exclusions: do not read, move, index, or summarize `D:\00.test\personal`, `_secrets`, `.env*` contents, or Google Drive temp roots.

## Conclusion

The directory problem is real: `D:\` is mostly categorized now, but `D:\00.test` is still a flat workspace with active repos, mirrors, similar split projects, build caches, generated outputs, and historical backups mixed together. The correct target is a numbered root taxonomy, but active roots cannot be renamed in one step because agents, RAG bootstrap, credential loaders, MCP filesystem servers, project docs, scripts, and deployment workflows still reference the current flat paths.

Recommended strategy:

1. Keep canonical paths unchanged during analysis.
2. Clean or rehome low-risk generated artifacts first.
3. Rehome active SSOTs that currently live in backup-looking paths.
4. Update config/docs/RAG paths to numbered canonical paths.
5. Move active roots in batches, using temporary hidden junctions only where external tooling cannot be updated immediately.
6. Remove compatibility junctions after access and job logs prove the new paths are stable.

Execution update on 2026-05-12:

- The visible root and first visible child levels have been migrated to `001~010` numbered buckets.
- `portfolio` moved to `D:\00.test\003.portfolio-career\006.portfolio`; the old `D:\00.test\portfolio` path is now a hidden junction alias.
- `neo-genesis`, `project_yesol`, and `PAPER` remain hidden real roots because open handles still exist. The deferred cleanup automation retries them instead of forcing a copy-delete fallback.
- Current navigation index: `D:\00.test\DIRECTORY_INDEX.md`.

## Current Root State

### D:\ Root

`D:\` is acceptable after the first cleanup, with one unresolved item.

| Path | Status | Action |
|---|---|---|
| `D:\00.test` | main project workspace | redesign internally |
| `D:\models`, `D:\ComfyUI_models` | model stores | keep |
| `D:\agent-cache`, `D:\agent-runtime`, `D:\agent-state` | relocated agent/runtime state | keep |
| `D:\docker`, `D:\wsl` | relocated platform disks | keep; move only through supported migration |
| `D:\tmp`, `D:\output`, `D:\local-dev`, `D:\automations` | standard utility roots | keep |
| `D:\KakaoTalk`, `D:\Telegram Desktop`, `D:\Creative App`, `D:\Launcher`, `D:\steam`, `D:\mods` | app-managed roots | do not move without app-specific migration |
| `D:\.claude` | Claude local settings | do not move unless Claude config is updated |
| `D:\agenttest` | canonical copy moved to `D:\00.test\006.games-labs\game-pipeline`; empty source root remains locked | HKCU RunOnce removes source root only if empty at next login |

### D:\00.test Root

After batch 1, root files are clean: only `AGENTS.md`, `CLAUDE.md`, `CREDENTIAL_BIBLE.md`, and `FOLDER_BIBLE.md` remain. The remaining issue is root directory sprawl: 36 root directories remain, many of which should become numbered bucket children.

## Numbered Target Taxonomy

| Prefix | Target bucket | Owns |
|---:|---|---|
| `001` | `001.ssot-agent-runtime` | `neo-genesis`, agent SSOT, shared-brain, runtime adapters, local agent state that must live with this workspace |
| `002` | `002.products-sbu` | SBU/product repos, SaaS sites, product prototypes, HIVE-MIND operated apps |
| `003` | `003.portfolio-career` | portfolio, resume, jobsearch, applications, career assets, master-data |
| `004` | `004.research-paper` | `PAPER`, EthicaAI, WhyLab, arXiv/NeurIPS/TMLR artifacts |
| `005` | `005.client-work` | CTS and client/company deliverables, presentations, work projects |
| `006` | `006.games-labs` | game repos and creative labs |
| `007` | `007.infra-tools` | WebPilot, security, cron, IR tools, helper engines |
| `008` | `008.mirrors-external` | cloned GitHub mirrors and external repos not used as primary working roots |
| `009` | `009.archive` | reviewed backups, rollback bundles, duplicates, old migration artifacts |
| `010` | `010.tmp-output` | temp output, screenshots, QA runs, generated one-off artifacts |

Root should eventually contain only:

- four SSOT docs: `AGENTS.md`, `CLAUDE.md`, `CREDENTIAL_BIBLE.md`, `FOLDER_BIBLE.md`
- the numbered bucket directories above
- temporary hidden compatibility junctions during migration windows only
- Google Drive temp roots only while Drive owns them

## Full Root Mapping

| Current path | Target bucket | Risk | Planned action |
|---|---|---:|---|
| `.claude` | `001.ssot-agent-runtime/.claude` | High | move only after Claude config/session impact check |
| `009.archive/legacy-root-archive` | `009.archive/root-cleanups-and-legacy` | Medium | normalize archive structure; keep audit evidence |
| `003.portfolio-career/extracted-assets` | `003.portfolio-career/extracted-assets` or `009.archive/extracted-review` | Medium | review contents without touching `personal`; classify |
| `_secrets` | no-touch | Critical | leave; do not inspect for cleanup |
| `_tmp` | `010.tmp-output/2026-05` | Medium | classify generated QA/deploy/audio artifacts first |
| `tmp` | `010.tmp-output/2026-05` | Medium | review Supercent/interview outputs, then move |
| `.tmp.drivedownload`, `.tmp.driveupload` | app-managed | Critical | do not move manually |
| `neo-genesis` | `001.ssot-agent-runtime/neo-genesis` | Critical | final phase only; many agents/configs reference it |
| `neo-genesis__sbu_autogrowth` | `009.archive/reviewed-clones` or merge into `neo-genesis` | High | duplicate clone analysis, then archive or delete caches |
| `neo-genesis_untracked_backup_20260505_083608` | split: active `auto-trading` to `002.products-sbu/quant-bot`, rest to `009.archive` | Critical | rehome active SSOT before moving backup wrapper |
| `portfolio` | `003.portfolio-career/006.portfolio` | High | moved on 2026-05-12; old path is hidden junction alias |
| `project_yesol` | `003.portfolio-career/project_yesol` | Critical | credential source and master-data references must be updated |
| `jobsearch` | `003.portfolio-career/jobsearch` | High | credential inventory references `jobsearch/.env`; update loader metadata |
| `PAPER` | `004.research-paper/PAPER` | Critical | many absolute paper and monitor paths; move last |
| `work` | `005.client-work/work` | Medium | active Osaka app and CTS work; update docs |
| `cts` | `005.client-work/cts` | Medium | primary CTS repo; can absorb presentation after check |
| `cts-presentation` | `005.client-work/cts/presentation` or `005.client-work/cts-presentation` | Low-Medium | standalone package, no git; merge candidate |
| `supercent_assignment` | `003.portfolio-career/applications/supercent` | Medium | career/application artifact; verify no private docs before move |
| `2dlivegame` | `006.games-labs/2dlivegame` | Medium | git repo; update local references only |
| `multiverse-creature-lab` | `006.games-labs/multiverse-creature-lab` | High | same origin as `github_repos/game`; choose canonical |
| `clash_of_myths` | `006.games-labs/clash_of_myths` | Medium | git repo with large assets |
| `ably-ai-closet` | `002.products-sbu/ably-ai-closet` | Medium | no origin; dirty; classify as product/prototype |
| `agentic-cro-analysis` | `007.infra-tools/agentic-cro-analysis` or `002.products-sbu` | Medium | has Temporal binary/zip; decide product vs infra |
| `analytics-cron-daemon` | `007.infra-tools/analytics-cron-daemon` | Low | small, no git |
| `internal-ir-report-generator` | `007.infra-tools/internal-ir-report-generator` | Medium | includes Google Cloud SDK copy; cache cleanup candidate |
| `nextjs-ai-chatbot` | `002.products-sbu/nextjs-ai-chatbot` | Low-Medium | git repo; small |
| `secur-pilot-engine` | `007.infra-tools/secur-pilot-engine` | Low-Medium | git repo; small |
| `WebPilot_Engine` | `007.infra-tools/WebPilot_Engine` | High | large `.next`, `.git`, `node_modules`, public assets |
| `why-engine` | `002.products-sbu/why-engine` | Medium | API project; pair with proxy |
| `why-engine-proxy` | `002.products-sbu/why-engine/proxy` | Medium | documented Cloudflare Worker; merge candidate |
| `sora-app` | `002.products-sbu/sora-app` or `001.ssot-agent-runtime/sora-app` | High | product/app; active Sora ecosystem |
| `sora-android` | `002.products-sbu/sora-app/android` | Medium | build output heavy; merge candidate |
| `github_repos` | `008.mirrors-external/github_repos` | High | contains mirrors and duplicate origins; not primary by default |
| `landing_page` | `002.products-sbu/landing_page` or `003.portfolio-career/landing_page` | Low-Medium | git repo; absolute refs low |
| `profile_repo` | `003.portfolio-career/profile_repo` | Low-Medium | git repo; small |

## Key Measurements

### Top-Level Size Summary

| Root | Physical MB | Logical MB excluding common rebuild dirs | Notes |
|---|---:|---:|---|
| `neo-genesis` | 19139.8 | 3763.4 | huge SBU/build state under `src`; active SSOT |
| `project_yesol` | 8694.2 | 8050.0 | real data dominates, not cache |
| `github_repos` | 6851.6 | 3249.2 | mirror/duplicate repo container |
| `WebPilot_Engine` | 5876.9 | 648.9 | mostly `.next`, `.git`, `node_modules` |
| `neo-genesis__sbu_autogrowth` | 4925.8 | 46.2 | mostly duplicated SBU caches/builds |
| `PAPER` | 3642.2 | 1534.3 | paper artifacts plus rebuildable envs |
| `multiverse-creature-lab` | 3570.5 | 1742.4 | images/assets and duplicate game repo issue |
| `clash_of_myths` | 2990.5 | 1561.4 | large assets |
| `portfolio` | 2876.4 | 963.7 | `node_modules`, `.vercel`, `dist`, public output |
| `neo-genesis_untracked_backup_20260505_083608` | 2605.8 | 2248.4 | active `auto-trading` SSOT currently inside backup wrapper |
| `jobsearch` | 918.8 | 251.0 | `.venv` dominates |
| `ably-ai-closet` | 827.0 | 0.3 | nearly all `.next` + `node_modules` |
| `sora-app` | 721.0 | 0.4 | nearly all `.next` + `node_modules` |
| `agentic-cro-analysis` | 693.5 | 253.6 | Temporal binary/zip and deps |
| `internal-ir-report-generator` | 579.9 | 442.5 | bundled Google Cloud SDK copy |
| `2dlivegame` | 364.4 | 188.0 | docs/assets/zips plus deps |
| `sora-android` | 351.9 | 5.8 | Android build output dominates |
| `work` | 287.3 | 15.5 | Osaka app deps dominate |
| `tmp` | 266.5 | 266.5 | recent Supercent/interview output |
| `_tmp` | 211.6 | 211.6 | generated QA/audio/deploy output |
| `009.archive/legacy-root-archive` | 94.3 | 74.8 | prior cleanup and legacy bundles |

### Largest Subdirectory Hotspots

| Area | Hotspot | Size | Plan |
|---|---|---:|---|
| `neo-genesis` | `src` | 16484.9 MB | split active SBU state vs generated deps; do not move root yet |
| `neo-genesis` | `.git` | 1582.5 MB | git history/LFS; keep |
| `neo-genesis` | `data`, `output`, `logs` | 872.1 MB combined | classify output/log retention |
| `project_yesol` | `data` | 7849.2 MB | likely real assets; move only under career bucket with refs updated |
| `github_repos` | `game`, `WebPilot-Engine`, `WhyLab` | 5869.7 MB combined | mirror dedupe candidates |
| `WebPilot_Engine` | `.next`, `.git`, `node_modules`, `public` | 5866.3 MB combined | cache cleanup plus asset review |
| `PAPER` | `WhyLab`, `EthicaAI`, anon variants | 3633.1 MB combined | paper freeze rules apply |
| `portfolio` | `node_modules`, `.vercel`, `public`, `dist` | 2691.1 MB combined | build/deploy cache cleanup after build check |
| `neo-genesis_untracked_backup_20260505_083608` | `auto-trading` | 2327.9 MB | extract active quant SSOT first |
| `_tmp` | `supercent_audio`, `ffmpeg`, deploy QA dirs | 210+ MB | route to `010.tmp-output` or `D:\output` |
| `tmp` | `interview_supergent_20260430` | 260.1 MB | route to application/career output or archive |

### Largest Rebuildable / Cache Candidates

| Path | Kind | Size | Action |
|---|---|---:|---|
| `neo-genesis\src\sbu\ethicaai\.venv` | `.venv` | 4982.4 MB | keep until EthicaAI env reproduced; then recreate policy |
| `WebPilot_Engine\.next` | build cache | 2721.5 MB | delete/rebuild candidate after app smoke plan |
| `neo-genesis\src\sbu\toolpick\.next` | build cache | 1220.8 MB | delete/rebuild candidate after ToolPick build verified |
| `portfolio\node_modules` | deps | 1216.0 MB | delete/reinstall candidate after package lock verified |
| `WebPilot_Engine\node_modules` | deps | 913.9 MB | delete/reinstall candidate |
| duplicated SBU `node_modules` under `neo-genesis` and `neo-genesis__sbu_autogrowth` | deps | multiple 500-730 MB copies | remove duplicate clone first, then cache policy |
| `jobsearch\.venv` | `.venv` | 665.9 MB | keep until `requirements` install verified |
| `sora-android\app\build` | build output | 346.0 MB | safe build-output cleanup after Gradle state check |
| `work\osaka-food-trip\node_modules` | deps | 259.1 MB | keep while app active; prune later |

## Duplicate and Split-Project Findings

| Cluster | Evidence | Risk | Design decision |
|---|---|---:|---|
| `neo-genesis` vs `neo-genesis__sbu_autogrowth` | duplicate SBU repo origins for `aiforge`, `craftdesk`, `deploystack`, `finstack`, `sellkit`, `toolpick`; mostly rebuildable size | High | keep `neo-genesis` canonical; archive/delete duplicate clone only after diff and branch check |
| `neo-genesis_untracked_backup_20260505_083608` | master data calls `auto-trading` active SSOT | Critical | extract `auto-trading` to first-class `002.products-sbu/quant-bot` before archiving wrapper |
| `github_repos/game` vs `multiverse-creature-lab` | same origin `https://github.com/Yesol-Pilot/game`; one dirty | High | choose canonical by latest content, then mirror to `008.mirrors-external` |
| `github_repos/WebPilot-Engine` vs `WebPilot_Engine` | same product family, different root names | High | choose active canonical and move mirror under `70` |
| `PAPER/WhyLab`, `PAPER/WhyLab_anon`, `anon_repo_tmp_v2`, `github_repos/WhyLab` | anon/freeze/mirror variants | Critical | keep freeze anchors; document canonical and archive only generated temp |
| `PAPER/EthicaAI`, `EthicaAI_anon`, `EthicaAI_anon2`, `github_repos/EthicaAI` | paper/freeze/mirror variants | Critical | keep freeze anchors; do not dedupe by name alone |
| `cts`, `work/cts-*`, `cts-presentation` | related CTS deliverables split across root/work | Medium | `005.client-work` bucket; merge presentation only after paths checked |
| `why-engine` + `why-engine-proxy` | API + Cloudflare worker split | Medium | keep as one product with `proxy/` subdir or sibling under `002.products-sbu/why-engine` |
| `sora-app` + `sora-android` | app + mobile artifact split | Medium-High | make `sora-app/android` or `sora-suite/{web,android}` after Sora runtime check |

## Absolute Path and Runtime Side Effects

| Side effect | Evidence | Mitigation |
|---|---|---|
| Hardcoded absolute paths | active scan found refs concentrated in `project_yesol` 287, `PAPER` 262, `portfolio` 98, `neo-genesis` 58, `jobsearch` 30 | replace/configure before moving those roots |
| RAG bootstrap stale paths | `sora_context.json` has `D:/00.test/neo-genesis`, `portfolio`, `work`, `project_yesol`, `WebPilot_Engine`, `multiverse-creature-lab`, `2dlivegame`, `PAPER` | update bootstrap paths and reindex after migration |
| RAG sensitive path | `sora_context.json` lists `D:/00.test/personal` under sensitive | keep excluded from cleanup/index unless explicit privacy design changes |
| Credential loader paths | `credential_loader.py` hardcodes `D:/00.test/neo-genesis`; credential inventory references `jobsearch/.env`, `project_yesol/.env.n8n` | update loader/config and regenerate credential inventory |
| Active processes | MCP filesystem servers run on `D:/00.test`; PC agent and http-server use `neo-genesis` paths | stop/restart or leave compatibility junctions during move |
| Git dirty trees | `neo-genesis` dirty 68, `PAPER/WhyLab` dirty 95, `PAPER/EthicaAI` dirty 69, `project_yesol/toss-portfolio` dirty 12, etc. | do not move dirty repos until status is recorded and owner-approved changes are preserved |
| Deployment paths | Vercel/Cloudflare/local scripts often assume cwd path | run build/deploy smoke after each moved project |
| Package and venv paths | `.venv`, `.next`, `node_modules`, Gradle build outputs may contain absolute paths | prefer deletion/rebuild over moving caches |
| Google Drive temp dirs | `.tmp.driveupload` is 12.4 GB and app-managed | do not manually move/delete; use Drive app controls |
| Archive audit evidence | `.agent/shared-brain/claude-checkpoints`, prior root cleanup archives, paper freeze dirs | preserve or compress, do not delete blind |
| Windows junctions | C-drive compatibility junctions already exist for caches/runtime | do not replace junctions with real dirs; document any new junctions |

## Recommended Migration Architecture

### Path Strategy

Use a three-layer transition:

1. **Current canonical layer**: old root paths remain during analysis and config updates.
2. **Numbered canonical layer**: target directories under numbered buckets become the real project locations.
3. **Compatibility shim layer**: temporary root junctions from old path to new target only for high-risk paths that external tools may still call.

Rules:

- Low-risk roots with no active absolute refs can move without junctions.
- High-risk roots need reference updates first, then move, then a 14-30 day hidden junction window.
- Rebuildable caches should not be moved; delete/recreate them in the new location after project verification.
- Every junction must have an owner, expiry date, and rollback note.

### Migration Gate Template

Before each move:

1. `git status --short` for repo roots.
2. absolute path scan for current path.
3. active process scan for current path.
4. RAG/credential/deploy config scan.
5. classify action: `MOVE`, `MERGE`, `CACHE-REBUILD`, `KEEP`, `ARCHIVE`, `DELETE`.
6. write move manifest with source, target, risk, rollback.

After each move:

1. verify source absent or junctioned intentionally.
2. verify target exists and file counts match.
3. run project-specific smoke:
   - web: install/build or existing dev smoke
   - Python: import/syntax or test subset
   - paper: compile or file presence check
   - runtime: agent config load
4. update SSOT docs and RAG bootstrap.
5. append daily-log entry.

## Phase Plan

### Phase 0 - Freeze and Inventory

Status: this document completes the first analysis pass.

Tasks:

- preserve current root state snapshot.
- export top-level inventory and duplicate-origin map.
- mark no-touch dirs: `personal`, `_secrets`, Google Drive temp roots, app-managed D roots.

Exit criteria:

- inventory doc exists.
- no broad move performed.
- owner can review risk map.

### Phase 1 - Generated Artifact and Cache Hygiene

Goal: reduce noise and storage without changing canonical project paths.

Actions:

- prune or rebuild selected `.next`, `node_modules`, `.venv`, Gradle `build`, `.wrangler`, `.vercel` only after project-specific install/build check.
- move `tmp` and `_tmp` into `010.tmp-output` or `D:\output` by owner-facing domain:
  - Supercent/interview -> `003.portfolio-career/applications/supercent/_output`
  - deploy QA -> `010.tmp-output/deploy-qa/202605`
  - `ffmpeg` binary -> `D:\local-dev\tools\ffmpeg` if useful, otherwise archive.

Risks:

- deleting deps breaks immediate dev until reinstall.
- venv deletion loses local package state if requirements are incomplete.

Exit criteria:

- no active project loses reproducible build path.
- reclaimed size and rebuild command recorded.

### Phase 2 - Active SSOT Rehoming

Goal: remove active work from backup-looking folders.

Actions:

- move or promote `neo-genesis_untracked_backup_20260505_083608\auto-trading` to a first-class canonical path, likely `002.products-sbu/quant-bot` or `001.ssot-agent-runtime/quant-bot` depending on operating role.
- update `project_yesol/master-data/master-asset-verified.json` evidence path.
- verify VM/deploy scripts do not depend on old local path.
- archive remaining wrapper subdirs only after active SSOT extraction.

Risks:

- quant docs/portfolio evidence path breaks.
- VM deploy commands may refer to old local path.

Exit criteria:

- active quant evidence path updated.
- old backup wrapper no longer contains the only active SSOT.

### Phase 3 - Merge Similar Split Projects

Order:

1. `cts` + `cts-presentation` + `work/cts-*`
2. `why-engine` + `why-engine-proxy`
3. `sora-app` + `sora-android`
4. `multiverse-creature-lab` + `github_repos/game`
5. `WebPilot_Engine` + `github_repos/WebPilot-Engine`

Risks:

- merging into a git repo may stage huge build artifacts or node_modules.
- preserving history may require subtree or separate archive, not raw move.

Exit criteria:

- one canonical owner path per product family.
- mirror paths classified under `008.mirrors-external` or `009.archive`.

### Phase 4 - Numbered Root Migration

Move low-risk roots first:

- `analytics-cron-daemon` -> `007.infra-tools`
- `nextjs-ai-chatbot` -> `002.products-sbu`
- `secur-pilot-engine` -> `007.infra-tools`
- `landing_page`, `profile_repo` -> target bucket after docs update
- `cts-presentation` after merge decision

Move high-risk roots last:

- `neo-genesis`
- `project_yesol`
- `PAPER`
- `portfolio`
- `jobsearch`
- `work`

Risks:

- RAG/credential/deploy/agent paths break.
- old MCP filesystem process stays rooted at `D:\00.test`, which is OK, but agents may use old exact paths.

Exit criteria:

- root is numbered except temporary hidden junctions.
- all SSOT docs point to numbered canonical paths.
- RAG bootstrap updated and reindex plan exists.

### Phase 5 - RAG and Agent Runtime Reindex

Actions:

- update `sora_context.json` `rag_dirs` and `rag_bootstrap`.
- remove nonexistent `D:/00.test/pay-for-me` if confirmed obsolete.
- ensure `personal` remains excluded from automatic cleanup/indexing unless explicitly designed.
- reindex Qdrant/Chroma/LanceDB collections after file moves.
- update generated runtime adapters with `python scripts/sync_agent_context.py`.

Risks:

- old vector metadata points to stale paths.
- RAG claims may overstate coverage.

Exit criteria:

- RAG search returns new paths.
- path alias map exists for historical docs.

## Proposed Final Shape

```text
D:\00.test
  AGENTS.md
  CLAUDE.md
  CREDENTIAL_BIBLE.md
  FOLDER_BIBLE.md
  001.ssot-agent-runtime\
    neo-genesis\
    agent-state-local\
  002.products-sbu\
    aiforge\
    craftdesk\
    deploystack\
    finstack\
    sellkit\
    toolpick\
    reviewlab\
    k-ott\
    ur-wrong\
    why-engine\
    sora-app\
    quant-bot\
    prototypes\
  003.portfolio-career\
    portfolio\
    project_yesol\
    jobsearch\
    applications\
  004.research-paper\
    PAPER\
  005.client-work\
    cts\
    work\
  006.games-labs\
    2dlivegame\
    multiverse-creature-lab\
    clash_of_myths\
  007.infra-tools\
    WebPilot_Engine\
    secur-pilot-engine\
    analytics-cron-daemon\
    internal-ir-report-generator\
    agentic-cro-analysis\
  008.mirrors-external\
    github_repos\
  009.archive\
    root-cleanups\
    reviewed-clones\
    rollback-bundles\
  010.tmp-output\
    2026-05\
```

## Do Not Do

- Do not rename `neo-genesis`, `project_yesol`, `PAPER`, `portfolio`, or `jobsearch` immediately.
- Do not move `personal`, `_secrets`, `.env*`, or Google Drive temp roots.
- Do not delete dirty git working trees.
- Do not move build caches as valuable state; rebuild them or leave them.
- Do not rely on folder name similarity to dedupe paper freeze/anonymous submission directories.
- Do not create untracked backup folders without a retention label, owner, and expiry date.

## Execution Status - 2026-05-11

Phase 1 and a low/medium-risk subset of Phase 4 have been executed with move manifests. No broad delete was performed.

Created numbered bucket roots:

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

Moved to numbered buckets:

| Old root | New path |
|---|---|
| `analytics-cron-daemon` | `007.infra-tools\analytics-cron-daemon` |
| `agentic-cro-analysis` | `007.infra-tools\agentic-cro-analysis` |
| `internal-ir-report-generator` | `007.infra-tools\internal-ir-report-generator` |
| `secur-pilot-engine` | `007.infra-tools\secur-pilot-engine` |
| `WebPilot_Engine` | `007.infra-tools\WebPilot_Engine` |
| `nextjs-ai-chatbot` | `002.products-sbu\nextjs-ai-chatbot` |
| `ably-ai-closet` | `002.products-sbu\ably-ai-closet` |
| `landing_page` | `002.products-sbu\landing_page` |
| `why-engine` | `002.products-sbu\why-engine` |
| `why-engine-proxy` | `002.products-sbu\why-engine-proxy` |
| `profile_repo` | `003.portfolio-career\profile_repo` |
| `supercent_assignment` | `003.portfolio-career\applications\supercent\assignment` |
| `cts` | `005.client-work\cts` |
| `cts-presentation` | `005.client-work\cts-presentation` |
| `work` | `005.client-work\work` |
| `2dlivegame` | `006.games-labs\2dlivegame` |
| `clash_of_myths` | `006.games-labs\clash_of_myths` |
| `multiverse-creature-lab` | `006.games-labs\multiverse-creature-lab` |
| `github_repos` | `008.mirrors-external\github_repos` |
| `_tmp` generated outputs | `010.tmp-output`, `003.portfolio-career\applications\...`, and `D:\local-dev\tools\ffmpeg` |

Updated reference surfaces:

- Sora RAG bootstrap in both `neo-genesis` and `neo-genesis__sbu_autogrowth`.
- Credential inventory paths for moved credential-bearing roots.
- Portfolio data and script references for moved roots.
- Project Yesol master-data localPath/sourceDocument references for moved roots.

Verification:

- All move manifests parse as JSON.
- Sora context JSON validates after UTF-8 repair and path updates.
- Exact old-path scans for moved roots now return zero matches.
- Dirty git working trees were preserved in their moved locations.

Important caveat:

- A PowerShell text-rewrite attempt exposed encoding/JSON-control-character issues. Sora and portfolio tracked files were repaired from git HEAD plus path replacements. `project_yesol/master-data/*.json` has no root git and already contains parser-invalid control characters, so those files need a separate master-data encoding repair pass before relying on JSON parser validation.

## Execution Status - 2026-05-11 Phase 2

Master-data JSON repair is complete.

- Repaired `project_yesol/master-data/projects.json` from valid `portfolio\data\projects-database.json`, with moved-root path mappings reapplied.
- Rebuilt `project_yesol/master-data/project-ref-triage.json` from extractable structural fields; long free-text notes from the malformed file were not reliable and were not preserved.
- Restored `project_yesol/master-data/master-asset-verified.json` from valid `master-asset-verified-v3.json`, with moved-root path mappings reapplied.
- Corrupt originals are preserved under `D:\00.test\009.archive\master-data-json-repair-20260511`.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-master-data-json-repair.json`.

Active quant SSOT extraction is complete.

- Promoted `D:\00.test\neo-genesis_untracked_backup_20260505_083608\auto-trading` to `D:\00.test\002.products-sbu\quant-bot`.
- Preserved git origin `https://github.com/Yesol-Pilot/quant-bot.git`, branch `master`, head `1ca0a57`, and dirty working tree state.
- `.env` existence was checked but secret values were not opened or printed.
- Updated active path references from `neo-genesis/auto-trading` to `002.products-sbu/quant-bot`.
- Archived duplicate clean mirror `008.mirrors-external\github_repos\quant-bot` to `009.archive\reviewed-clones\github_repos_quant-bot_clean_mirror_20260511`.
- Archived the remaining reviewed backup wrapper to `009.archive\reviewed-clones\neo-genesis_untracked_backup_20260505_083608__reviewed_after_quant_extract`.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-phase2-quant-bot-ssot-extraction.json`.

Verification:

- All 23 root JSON files under `project_yesol/master-data` parse successfully.
- The new master-data and quant extraction manifests parse as JSON after UTF-8 no-BOM normalization.
- Exact active scans for old `neo-genesis/auto-trading` and `neo-genesis\auto-trading` paths return zero matches outside `009.archive`.

## Execution Status - 2026-05-11 Phase 3

Owner requested a `001~` numbering convention instead of the earlier `00/10/20/...` bucket names. The numbered buckets were renamed accordingly:

| Previous | Current |
|---|---|
| `00.ssot-agent-runtime` | `001.ssot-agent-runtime` |
| `10.products-sbu` | `002.products-sbu` |
| `20.portfolio-career` | `003.portfolio-career` |
| `30.research-paper` | `004.research-paper` |
| `40.client-work` | `005.client-work` |
| `50.games-labs` | `006.games-labs` |
| `60.infra-tools` | `007.infra-tools` |
| `70.mirrors-external` | `008.mirrors-external` |
| `90.archive` | `009.archive` |
| `99.tmp-output` | `010.tmp-output` |

Recovery note:

- `Move-Item` partially copied `2dlivegame` before stopping on a read-only `.agent\bible\specs` directory.
- The partial `006.games-labs` destination was completed by verified copy-then-remove from the old `50.games-labs` source. The old source was removed only after every source file existed at the new destination with the same length.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-phase3-three-digit-bucket-renames.json`.

## Execution Status - 2026-05-11 Phase 4

Legacy root clutter was moved into the `001~` buckets:

| Previous root | Current path |
|---|---|
| `_archive` | `009.archive\legacy-root-archive` |
| `_extracted` | `003.portfolio-career\extracted-assets` |
| `tmp\interview_supergent_20260430` | `010.tmp-output\interview_supergent_20260430` |

Notes:

- `tmp\interview_supergent_20260430` contained hardcoded self paths. Those literals were updated to `D:\00.test\010.tmp-output\interview_supergent_20260430` before moving.
- `_archive` had read-only descendants, so it was consolidated with verified copy-then-remove rather than blind deletion.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-phase4-legacy-root-folder-consolidation.json`.

## Execution Status - 2026-05-11 Phase 5

D root cleanup continued with `D:\agenttest`:

- Classified `D:\agenttest` as the `Yesol-Pilot/game-pipeline` git repo, not a throwaway folder.
- Copied and verified it to `D:\00.test\006.games-labs\game-pipeline`, preserving git origin, branch, and dirty working tree.
- The source `D:\agenttest` folder is now empty, but Windows still holds the directory handle and blocks immediate removal.
- Registered HKCU RunOnce `RemoveEmptyAgenttest20260511`, which removes `D:\agenttest` only if it is still empty at next login.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-phase5-d-root-agenttest-game-pipeline-move.json`.

## Execution Status - 2026-05-11 Phase 10

`D:\00.test` default-visible directories are now numbered-only.

Moved with hidden junction compatibility:

| Previous root | Current path |
|---|---|
| `.claude` | `001.ssot-agent-runtime\.claude` |
| `.codex_tmp` | `010.tmp-output\codex_tmp` |
| `jobsearch` | `003.portfolio-career\jobsearch` |
| `sora-app` | `002.products-sbu\sora-app` |
| `sora-android` | `002.products-sbu\sora-android` |
| `neo-genesis__sbu_autogrowth` | `001.ssot-agent-runtime\neo-genesis__sbu_autogrowth` |

Hidden in place, not moved:

- `neo-genesis`: active agent SSOT/runtime root.
- `project_yesol`: path locked during move attempt.
- `portfolio`: initially failed here, then moved on 2026-05-12 to `003.portfolio-career\006.portfolio` by deferred cleanup.
- `PAPER`: path locked during move attempt.
- `_secrets` and `personal`: protected no-touch roots.

Verification:

- `Get-ChildItem D:\00.test -Directory` shows only `001~010` buckets.
- Old moved paths remain accessible through hidden junctions.
- No copy-delete fallback was used for locked high-risk roots.
- Manifest: `D:\00.test\009.archive\reorg-manifests\20260511-phase10-d00test-root-visible-numbered-migration.json`.
