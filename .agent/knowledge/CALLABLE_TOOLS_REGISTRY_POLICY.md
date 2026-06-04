# Callable Tools Registry Policy

> Local callable tools: `.agent/registries/callable_tools.json`  
> External capabilities: `.agent/registries/external_tool_capabilities.json`  
> Human summaries: `.agent/registries/callable_tools.md`, `.agent/registries/external_tool_capabilities.md`  
> Generators: `scripts/agent/update_callable_tools_registry.py`, `scripts/agent/update_external_tool_capability_registry.py`

## Purpose

All Neo Genesis agents should share one current list of locally callable Python tools and one current list of external Codex/session capabilities.

The local registry is generated from actual `src/core/tools/*_tools.py` `TOOLS` lists plus `src/core/brain/agent_router.py` route mappings, then annotated with execution-gate policy metadata from `src/core/governance/execution_gate.py`.

The external capability registry is generated from `.agent/registries/external_tool_capabilities.source.json`. These entries describe Codex desktop tools, hosted tools, and deferred connector/plugin capability groups. They are not automatically callable by Sora/Claude/Gemini local runtimes unless `callable_by` explicitly includes that runtime.

## Required Behavior

- Before assuming a local tool exists, consult `.agent/registries/callable_tools.json` or call `list_callable_tools`.
- Before assuming a Codex connector/plugin/hosted tool exists, consult `.agent/registries/external_tool_capabilities.json` or call `list_external_tool_capabilities`.
- For a combined view, call `list_agent_tool_capabilities`.
- After adding, removing, renaming, or changing a tool signature, refresh the registry:

```powershell
python scripts\agent\update_callable_tools_registry.py --updated-by <agent>
```

- After adding or changing a Codex/connector/plugin capability declaration, refresh the external registry:

```powershell
python scripts\agent\update_external_tool_capability_registry.py --updated-by <agent>
```

- Agents may also refresh from runtime through `refresh_callable_tools_registry` and `refresh_external_tool_capability_registry`.
- Do not hand-edit generated registry outputs: `.agent/registries/callable_tools.json`, `.agent/registries/callable_tools.md`, `.agent/registries/external_tool_capabilities.json`, or `.agent/registries/external_tool_capabilities.md`.
- `.agent/registries/external_tool_capabilities.source.json` is the curated source for external capability declarations.
- If a route contains an unavailable fallback stub, treat it as unavailable until the underlying module is installed or repaired.
- Execution authority is still governed by `src/core/governance/execution_gate.py`; the registry only exposes the policy metadata, it does not bypass approvals.
- External capabilities with `handoff_required_for` require the listed local agents to hand off to Codex instead of pretending they can call the tool directly.

## Shared Update Contract

1. Tool author updates Python code.
2. Tool or capability author runs the relevant registry generator.
3. If `.agent` policy, source registry, or adapter-visible knowledge changed, run:

```powershell
python scripts\sync_agent_context.py
```

4. Report the registry revision and any diagnostics.
