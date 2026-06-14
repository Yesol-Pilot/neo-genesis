<!-- generated: scripts/sync_agent_context.py -->
# Neo Genesis Agent Runtime Guide

> Canonical source: `.agent/NEO_MASTER_RULES.md`
> Supporting sources: `.agent/BIBLE.md`, `.agent/knowledge/AGENT_SHARED_MEMORY.md`, `.agent/shared-brain/*`
> Regenerate with `python scripts/sync_agent_context.py`
> Live snapshot source: `.agent/shared-brain/status.json` (`2026-06-14T17:02:04+09:00`)

## SSOT Order
1. `.agent/NEO_MASTER_RULES.md`
2. `.agent/BIBLE.md`
3. `.agent/knowledge/AGENT_SHARED_MEMORY.md`
4. `.agent/shared-brain/`

## Mandatory Rules
- Respond to the owner in Korean by default.
- Put the conclusion first, then supporting details.
- Read SSOT before coding, refactoring, or changing operational behavior.
- Session start (PCP v1): run `python scripts/agent_session_sync.py <path>` for Safe-Sync before work. Never blind `git pull`; the tool does fetch then pull--rebase on a clean tree or report-only on a dirty tree. Classify any unregistered project in `.agent/policies/project_continuity_registry.json` first. Canonical rule: `.agent/knowledge/20260614_PROJECT_CONTINUITY_PROTOCOL_v1.md`.
- Check scope and side effects before tests, deploys, notifications, credential changes, or any external action.
- Do not hardcode paths, URLs, model names, or environment-specific values when SSOT or config already defines them.
- Public/customer-facing contact email is `help@neogenesis.app` (forwards to `neogenesis.research@gmail.com` via Cloudflare Email Routing) — use it for business inquiries, customer leads, sales, quotes, invoices, payment guidance, partnerships, product CTAs, and `mailto:` links. Keep `neogenesis.research@gmail.com` for internal account identity only (logins, payment-processor/OAuth accounts, forwarding destination); keep `dpthf1537@gmail.com` only for GitHub/git/Vercel/Cloudflare personal account, authentication, and admin uses, never as a public contact.
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
- ssotRevision: `9d59954e99dae8cf`

## Live Snapshot
- `codex`: status=active
