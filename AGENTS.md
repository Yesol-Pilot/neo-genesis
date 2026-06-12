<!-- generated: scripts/sync_agent_context.py -->
# Neo Genesis Agent Runtime Guide

> Canonical source: `.agent/NEO_MASTER_RULES.md`
> Supporting sources: `.agent/BIBLE.md`, `.agent/knowledge/AGENT_SHARED_MEMORY.md`, `.agent/shared-brain/*`
> Regenerate with `python scripts/sync_agent_context.py`
> Live snapshot source: `.agent/shared-brain/status.json` (`2026-06-12T14:36:29+09:00`)

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
- For C drive storage/cleanup, follow `.agent/knowledge/20260510_C_DRIVE_MANAGEMENT_POLICY.md`: move or re-home large agent-created state to `D:` before deleting.
- For D drive root hygiene, follow `.agent/knowledge/20260510_D_DRIVE_ROOT_POLICY.md`: do not create ad hoc top-level folders under `D:\`.
- For Google Drive, do not sync active repos, `D:\00.test`, build outputs, caches, logs, temp outputs, generated media, or agent runtime state; export curated deliverables only.
- For owner-authorized personal legal/finance context, follow `.agent/knowledge/PERSONAL_CONTEXT_ROUTING.md` and do not copy sensitive contents into shared prompts.
- Verify unstable or time-sensitive facts with official documentation before using them.
- Treat `.agent/` as the source of truth. Treat root `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and `infra/agent-runtime/` as generated adapters.
- For Neo Genesis business/runtime state (SBU, product, KPI, revenue path, decision, risk, agent, device), consult the ontology before acting and record material changes after: query `python scripts/ontology/business/query.py --object-set <name>` (business) or `scripts/ontology/query.py` (runtime); record via `scripts/ontology/mutate.py` / `auto_record.py`. The ontology auto-refreshes daily (Task Scheduler `NeoGenesisOntologyDailyMaintain`); every node/edge carries `provenance` and integrity is gated by `scripts/ontology/validate.py`.
- For Vercel and Supabase, use only the `neogenesis` organization, never the legacy `etribe` org (Vercel team `etribe-cts's projects` / Supabase `etirbe-cts's Org`) — 2026-06-09 account migration. Before creating projects, deploying, running DB migrations, or changing env vars, confirm the target org is `neogenesis`; if only `etribe` is selectable, stop and tell the owner.

## Shared Knowledge
- Ontology (Neo Genesis operating graph): `.agent/ontology/` (runtime/meta) + `.agent/ontology/business/` (business). Tools: `query.py` / `mutate.py` / `validate.py` / MCP `neo-genesis-ontology`. Design: `.agent/ontology/DESIGN_v0.1.md`.
- Collaboration contract: `.agent/contracts/COLLABORATION_CONTRACT.md`
- Long-term memory: `.agent/knowledge/AGENT_SHARED_MEMORY.md`
- Personal context routing: `.agent/knowledge/PERSONAL_CONTEXT_ROUTING.md`
- Role optimization: `.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md`
- Claude collaboration: `.agent/knowledge/CLAUDE_COLLABORATION.md`
- Tool registries: local `.agent/registries/callable_tools.json`, external `.agent/registries/external_tool_capabilities.json`, policy `.agent/knowledge/CALLABLE_TOOLS_REGISTRY_POLICY.md`
- C drive management: `.agent/knowledge/20260510_C_DRIVE_MANAGEMENT_POLICY.md`
- D drive root policy: `.agent/knowledge/20260510_D_DRIVE_ROOT_POLICY.md`
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
- ssotRevision: `c51879e75eaa2f8c`
