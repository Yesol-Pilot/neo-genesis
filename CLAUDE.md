<!-- generated: scripts/sync_agent_context.py -->
# Neo Genesis Claude Adapter (v2 slim, 2026-05-12)

> Root SSOT lives in `.agent/`
> This file is an adapter for Claude Code memory loading.
> v2 (2026-05-12): Tier 1 만 @import. Tier 2 (COLLABORATION_CONTRACT / AGENT_SHARED_MEMORY / AGENT_RUNTIME_OPTIMIZATION / CLAUDE_COLLABORATION / cross-agent-review) 는 lazy load (필요 시 Read).

@./AGENTS.md
@./infra/agent-runtime/LIVE_STATUS.md
@./.agent/shared-brain/active-tasks.md
@./.agent/shared-brain/handoff.md

<!-- Tier 2 lazy load (필요 시 Read):
- .agent/contracts/COLLABORATION_CONTRACT.md
- .agent/knowledge/AGENT_SHARED_MEMORY.md
- .agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md
- .agent/knowledge/CLAUDE_COLLABORATION.md
- .agent/knowledge/CALLABLE_TOOLS_REGISTRY_POLICY.md
- .agent/registries/callable_tools.json
- .agent/registries/external_tool_capabilities.json
- .agent/shared-brain/cross-agent-review.md
- infra/agent-runtime/FLEET_STATUS.md
-->
