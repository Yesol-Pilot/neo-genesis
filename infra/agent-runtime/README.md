<!-- generated: scripts/sync_agent_context.py -->
# Neo Genesis Runtime Bundle

This directory is the generated runtime bundle for shared agent context.

Files:
- `AGENTS.md` for Codex-compatible instructions
- `CLAUDE.md` for Claude Code imports
- `GEMINI.md` for Gemini CLI imports
- `LIVE_STATUS.md` for shared-brain status summary
- `FLEET_STATUS.md` for per-device rollout and heartbeat summary
- `SSOT_REVISION.txt` for canonical runtime revision checks
- `claude_checkpoint.py` for selective Claude checkpoint logging when collaboration is requested or needed
- `claude_collab.py` for Claude model routing and infinite-loop guard
- `ollama/Modelfile` for Ollama
- `runtime_heartbeat.py` for per-device self-report generation

Claude project assets expected at the repo root:
- `.claude/agents/neo-reviewer.md`
- `.claude/agents/neo-architect.md`
- `.claude/agents/neo-implementer.md`
- `.claude/agents/neo-conflict-resolver.md`

Current canonical revision: `92613c3d6066233f`

Refresh:
```powershell
python scripts/sync_agent_context.py
```

Heartbeat example:
```powershell
python infra/agent-runtime/runtime_heartbeat.py --device-id desktop-sol01 --print-json
```
