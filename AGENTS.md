<!-- generated: scripts/sync_agent_context.py -->
# Neo Genesis Agent Runtime Guide

> Canonical source: `.agent/NEO_MASTER_RULES.md`
> Supporting sources: `.agent/BIBLE.md`, `.agent/knowledge/AGENT_SHARED_MEMORY.md`, `.agent/shared-brain/*`
> Regenerate with `python scripts/sync_agent_context.py`
> Live snapshot source: `.agent/shared-brain/status.json` (`2026-04-28T15:29:09+09:00`)

## SSOT Order
1. `.agent/NEO_MASTER_RULES.md`
2. `.agent/BIBLE.md`
3. `.agent/knowledge/AGENT_SHARED_MEMORY.md`
4. `.agent/shared-brain/`

## Mandatory Rules
- Respond to the owner in Korean by default.
- Put the conclusion first, then supporting details.
- Read SSOT before coding, refactoring, or changing operational behavior.
- Check scope and side effects before tests, deploys, notifications, credential changes, or any external action.
- Do not hardcode paths, URLs, model names, or environment-specific values when SSOT or config already defines them.
- Verify unstable or time-sensitive facts with official documentation before using them.
- Treat `.agent/` as the source of truth. Treat root `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and `infra/agent-runtime/` as generated adapters.

## Shared Knowledge
- Collaboration contract: `.agent/contracts/COLLABORATION_CONTRACT.md`
- Long-term memory: `.agent/knowledge/AGENT_SHARED_MEMORY.md`
- Role optimization: `.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md`
- Claude collaboration: `.agent/knowledge/CLAUDE_COLLABORATION.md`
- Owner profile: `.agent/knowledge/OWNER_PROFILE.md`
- Live state: `.agent/shared-brain/status.json`, `.agent/shared-brain/active-tasks.md`, `.agent/shared-brain/handoff.md`, `.agent/shared-brain/cross-agent-review.md`
- Fleet state: `.agent/shared-brain/device_inventory.json`, `.agent/shared-brain/device_heartbeats.json`, `infra/agent-runtime/FLEET_STATUS.md`
- After changing `.agent/`, regenerate runtime adapters with `python scripts/sync_agent_context.py`.

## Runtime Mapping
- Codex reads `AGENTS.md` directly from its discovery chain.
- Claude Code loads `CLAUDE.md` and supports `@path` imports.
- Gemini CLI loads `GEMINI.md` and supports `@file.md` imports.
- Ollama uses `infra/agent-runtime/ollama/Modelfile` only after the model is rebuilt with `ollama create`.
- Sora reads `src/core/data/sora_context.json` for shared-brain and runtime paths.

## Runtime Revision
- ssotRevision: `703c1f6780eedf07`

## Live Snapshot
- `claude-code`: status=active, version=2.1.88, model=claude-opus-4-7, plan=claude-max
- `antigravity`: status=active, model=claude-opus-4.6-thinking
- `codex`: status=active, model=gpt-5-codex
- `sora`: status=active, version=v5.19, server=YSH-Server (100.67.221.25), container=sora-live (sora:v5.2)

## Connected Devices
- checkedAt: `2026-04-28T13:29:53+09:00`
- online: `desktop-sol01`, `desktop-yesol`, `ysh-server`
- offline: `mx-macbuild-mac-studio`, `s26-ultra`, `tab-s10-ultra`

## Device Rollout
- `desktop-sol01`: verified_installed
- `desktop-yesol`: verified_installed
- `ysh-server`: verified_installed
- `mx-macbuild-mac-studio`: offline
- `s26-ultra`: mobile_operator_mode_offline
- `tab-s10-ultra`: mobile_operator_mode_offline
