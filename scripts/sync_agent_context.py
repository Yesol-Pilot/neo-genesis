#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import shutil
from datetime import datetime
from pathlib import Path
from typing import Any

# Optional credential-bible sync. The script was historically split out into
# `scripts/sync_credential_bible.py` (per `.agent/shared-brain/daily-log.md`
# entry around 2026-04-x), but the file is no longer present on disk and there
# is no remaining git history for it. Treat its absence as a no-op so SSOT
# regeneration is never blocked by a missing optional helper.
try:
    from sync_credential_bible import sync_credential_bible  # type: ignore
    _HAS_CREDENTIAL_BIBLE = True
except ImportError:
    _HAS_CREDENTIAL_BIBLE = False

    def sync_credential_bible(*_args: Any, **_kwargs: Any) -> list[Path]:
        """No-op stub when sync_credential_bible.py is not present."""
        return []


PROJECT_ROOT = Path(__file__).resolve().parent.parent
AGENT_ROOT = PROJECT_ROOT / ".agent"
SHARED_BRAIN = AGENT_ROOT / "shared-brain"
RUNTIME_ROOT = PROJECT_ROOT / "infra" / "agent-runtime"
OLLAMA_ROOT = RUNTIME_ROOT / "ollama"
STATUS_PATH = SHARED_BRAIN / "status.json"
DEVICE_INVENTORY_PATH = SHARED_BRAIN / "device_inventory.json"
DEVICE_HEARTBEATS_PATH = SHARED_BRAIN / "device_heartbeats.json"
RUNTIME_REVISION_PATH = RUNTIME_ROOT / "SSOT_REVISION.txt"
MARKER = "<!-- generated: scripts/sync_agent_context.py -->"


def _timestamp_now() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _read_json(path: Path) -> dict[str, Any]:
    if not path.exists():
        return {}
    return json.loads(path.read_text(encoding="utf-8"))


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def _write_guarded(path: Path, content: str, force: bool) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not force and path.exists() and MARKER not in path.read_text(encoding="utf-8", errors="ignore"):
        raise RuntimeError(f"Refusing to overwrite non-generated file: {path}")
    path.write_text(content if content.endswith("\n") else content + "\n", encoding="utf-8")


def _runtime_revision() -> str:
    tracked_files = [
        AGENT_ROOT / "NEO_MASTER_RULES.md",
        AGENT_ROOT / "BIBLE.md",
        AGENT_ROOT / "contracts" / "COLLABORATION_CONTRACT.md",
        AGENT_ROOT / "knowledge" / "AGENT_SHARED_MEMORY.md",
        AGENT_ROOT / "knowledge" / "AGENT_RUNTIME_OPTIMIZATION.md",
        AGENT_ROOT / "knowledge" / "CLAUDE_COLLABORATION.md",
        AGENT_ROOT / "knowledge" / "20260510_C_DRIVE_MANAGEMENT_POLICY.md",
        AGENT_ROOT / "knowledge" / "OWNER_PROFILE.md",
        SHARED_BRAIN / "active-tasks.md",
        SHARED_BRAIN / "cross-agent-review.md",
        SHARED_BRAIN / "handoff.md",
        DEVICE_INVENTORY_PATH,
        PROJECT_ROOT / ".claude" / "agents" / "neo-reviewer.md",
        PROJECT_ROOT / ".claude" / "agents" / "neo-architect.md",
        PROJECT_ROOT / ".claude" / "agents" / "neo-implementer.md",
        PROJECT_ROOT / ".claude" / "agents" / "neo-conflict-resolver.md",
        RUNTIME_ROOT / "claude_checkpoint.py",
        RUNTIME_ROOT / "claude_collab.py",
    ]
    digest = hashlib.sha256()
    for path in tracked_files:
        digest.update(path.as_posix().encode("utf-8"))
        if path.exists():
            digest.update(path.read_bytes())
        digest.update(b"\0")
    return digest.hexdigest()[:16]


def _ensure_shared_context(status_payload: dict[str, Any], updated_by: str, runtime_revision: str) -> dict[str, Any]:
    payload = dict(status_payload)
    payload.setdefault("version", "1.0")
    payload.setdefault("agents", {})
    payload.setdefault("infrastructure", {})
    payload["sharedContext"] = {
        "status": "active",
        "sourceOfTruth": str(AGENT_ROOT),
        "syncCommand": f"python {PROJECT_ROOT / 'scripts' / 'sync_agent_context.py'}",
        "runtimeAdapters": [
            str(PROJECT_ROOT / "AGENTS.md"),
            str(PROJECT_ROOT / "CLAUDE.md"),
            str(PROJECT_ROOT / "GEMINI.md"),
            str(OLLAMA_ROOT / "Modelfile"),
        ],
        "ssotRevision": runtime_revision,
        "lastSyncedAt": _timestamp_now(),
        "lastSyncedBy": updated_by,
    }
    return payload


def _status_summary(status_payload: dict[str, Any]) -> str:
    agents = status_payload.get("agents", {})
    infra = status_payload.get("infrastructure", {})
    shared_context = status_payload.get("sharedContext", {})
    lines: list[str] = []

    runtime_revision = shared_context.get("ssotRevision")
    if runtime_revision:
        lines.append("## Runtime Revision")
        lines.append(f"- ssotRevision: `{runtime_revision}`")

    if agents:
        if lines:
            lines.append("")
        lines.append("## Live Snapshot")
        for name, payload in agents.items():
            meta: list[str] = []
            for key in ("status", "version", "model", "plan", "server", "container"):
                value = payload.get(key)
                if value:
                    meta.append(f"{key}={value}")
            if meta:
                lines.append(f"- `{name}`: " + ", ".join(meta))

    tailscale = infra.get("tailscale", {})
    online = tailscale.get("online", [])
    offline = tailscale.get("offline", [])
    checked_at = tailscale.get("checkedAt")
    if online or offline:
        lines.append("")
        lines.append("## Connected Devices")
        if checked_at:
            lines.append(f"- checkedAt: `{checked_at}`")
        if online:
            lines.append("- online: " + ", ".join(f"`{device}`" for device in online))
        if offline:
            lines.append("- offline: " + ", ".join(f"`{device}`" for device in offline))

    rollout = status_payload.get("deviceRollout", {})
    if rollout:
        lines.append("")
        lines.append("## Device Rollout")
        for device, state in rollout.items():
            lines.append(f"- `{device}`: {state}")

    return "\n".join(lines).strip()


def _render_repo_agents(status_payload: dict[str, Any]) -> str:
    snapshot = _status_summary(status_payload)
    shared_context = status_payload.get("sharedContext", {})
    last_updated = shared_context.get("lastSyncedAt") or status_payload.get("lastUpdated", "unknown")
    return f"""{MARKER}
# Neo Genesis Agent Runtime Guide

> Canonical source: `.agent/NEO_MASTER_RULES.md`
> Supporting sources: `.agent/BIBLE.md`, `.agent/knowledge/AGENT_SHARED_MEMORY.md`, `.agent/shared-brain/*`
> Regenerate with `python scripts/sync_agent_context.py`
> Live snapshot source: `.agent/shared-brain/status.json` (`{last_updated}`)

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
- Verify unstable or time-sensitive facts with official documentation before using them.
- Treat `.agent/` as the source of truth. Treat root `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`, and `infra/agent-runtime/` as generated adapters.

## Shared Knowledge
- Collaboration contract: `.agent/contracts/COLLABORATION_CONTRACT.md`
- Long-term memory: `.agent/knowledge/AGENT_SHARED_MEMORY.md`
- Role optimization: `.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md`
- Claude collaboration: `.agent/knowledge/CLAUDE_COLLABORATION.md`
- C drive management: `.agent/knowledge/20260510_C_DRIVE_MANAGEMENT_POLICY.md`
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

{snapshot}
"""


def _render_live_status(status_payload: dict[str, Any]) -> str:
    snapshot = _status_summary(status_payload)
    if not snapshot:
        snapshot = "## Live Snapshot\n- shared-brain status is not available."
    return f"""{MARKER}
# Neo Genesis Live Status

> Generated from `.agent/shared-brain/status.json`
> Regenerate with `python scripts/sync_agent_context.py`

{snapshot}
"""


def _render_fleet_status(status_payload: dict[str, Any], runtime_revision: str) -> str:
    inventory_payload = _read_json(DEVICE_INVENTORY_PATH)
    heartbeat_payload = _read_json(DEVICE_HEARTBEATS_PATH)
    devices = inventory_payload.get("devices", {})
    heartbeats = heartbeat_payload.get("devices", {})
    collected_at = heartbeat_payload.get("lastCollectedAt") or "unknown"

    lines = [
        MARKER,
        "# Neo Genesis Fleet Status",
        "",
        "> Generated from `.agent/shared-brain/device_inventory.json` and `.agent/shared-brain/device_heartbeats.json`",
        f"> Canonical runtime revision: `{runtime_revision}`",
        f"> Last collected: `{collected_at}`",
        "",
        "## Devices",
    ]

    if not devices:
        lines.append("- No device inventory found.")
        return "\n".join(lines) + "\n"

    for device_id, meta in devices.items():
        heartbeat = heartbeats.get(device_id, {})
        roles = ", ".join(meta.get("roles", [])) or "none"
        connectivity = heartbeat.get("connectivity", "unknown")
        rollout_state = heartbeat.get("rolloutState") or status_payload.get("deviceRollout", {}).get(device_id, "unknown")
        seen_at = heartbeat.get("generatedAt") or "unknown"
        revision = heartbeat.get("runtimeRevision") or "n/a"
        match = heartbeat.get("runtimeRevisionMatch")
        match_text = "match" if match is True else "mismatch" if match is False else "n/a"
        lines.append(
            f"- `{device_id}`: tier={meta.get('ownerTier', 'unknown')}, transport={meta.get('transport', 'unknown')}, "
            f"roles={roles}, connectivity={connectivity}, state={rollout_state}, revision={revision} ({match_text}), "
            f"seenAt={seen_at}"
        )

    return "\n".join(lines) + "\n"


def _render_claude_md() -> str:
    return f"""{MARKER}
# Neo Genesis Claude Adapter

> Root SSOT lives in `.agent/`
> This file is an adapter for Claude Code memory loading.

@./AGENTS.md
@./infra/agent-runtime/LIVE_STATUS.md
@./infra/agent-runtime/FLEET_STATUS.md
@./.agent/contracts/COLLABORATION_CONTRACT.md
@./.agent/knowledge/AGENT_SHARED_MEMORY.md
@./.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md
@./.agent/knowledge/CLAUDE_COLLABORATION.md
@./.agent/shared-brain/active-tasks.md
@./.agent/shared-brain/cross-agent-review.md
@./.agent/shared-brain/handoff.md
"""


def _render_gemini_md() -> str:
    return f"""{MARKER}
# Neo Genesis Gemini Adapter

This file keeps Gemini CLI aligned with the Neo Genesis SSOT.

@./AGENTS.md
@./infra/agent-runtime/LIVE_STATUS.md
@./infra/agent-runtime/FLEET_STATUS.md
@./.agent/contracts/COLLABORATION_CONTRACT.md
@./.agent/knowledge/AGENT_SHARED_MEMORY.md
@./.agent/knowledge/AGENT_RUNTIME_OPTIMIZATION.md
@./.agent/knowledge/CLAUDE_COLLABORATION.md
@./.agent/shared-brain/active-tasks.md
@./.agent/shared-brain/cross-agent-review.md
@./.agent/shared-brain/handoff.md
"""


def _render_ollama_system(status_payload: dict[str, Any]) -> str:
    snapshot = _status_summary(status_payload)
    return f"""{MARKER}
# Neo Genesis Ollama System Prompt

You are an internal Neo Genesis agent runtime.

Core rules:
- Respond to the owner in Korean by default.
- Put the conclusion first, then supporting details.
- Follow `.agent/NEO_MASTER_RULES.md` as the canonical source of truth.
- Treat `.agent/BIBLE.md`, `.agent/knowledge/AGENT_SHARED_MEMORY.md`, and `.agent/shared-brain/*` as supporting context.
- Verify unstable facts with official documentation before relying on them.

Runtime snapshot:

{snapshot}
"""


def _render_ollama_modelfile(base_model: str, system_prompt: str) -> str:
    clean_system_prompt = system_prompt.removeprefix(f"{MARKER}\n")
    escaped = clean_system_prompt.replace('"""', '\\"""')
    # Ollama Modelfile uses '#' for comments. Wrap MARKER in a comment so the
    # marker substring is present (satisfying _write_guarded) without changing
    # Modelfile semantics.
    return f"""# {MARKER}
FROM {base_model}
PARAMETER temperature 0.2
PARAMETER num_ctx 8192
SYSTEM \"\"\"{escaped}\"\"\"
"""


def _render_runtime_readme(runtime_revision: str) -> str:
    return f"""{MARKER}
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

Current canonical revision: `{runtime_revision}`

Refresh:
```powershell
python scripts/sync_agent_context.py
```

Heartbeat example:
```powershell
python infra/agent-runtime/runtime_heartbeat.py --device-id desktop-sol01 --print-json
```
"""


def _backup_if_exists(path: Path) -> None:
    if not path.exists():
        return
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    shutil.copy2(path, path.with_name(f"{path.name}.bak-{stamp}"))


def _install_home_adapters() -> list[Path]:
    home = Path.home()
    claude_dir = home / ".claude"
    gemini_dir = home / ".gemini"
    codex_dir = home / ".codex"
    claude_agents_dir = claude_dir / "agents"
    claude_dir.mkdir(parents=True, exist_ok=True)
    gemini_dir.mkdir(parents=True, exist_ok=True)
    codex_dir.mkdir(parents=True, exist_ok=True)
    claude_agents_dir.mkdir(parents=True, exist_ok=True)

    claude_file = claude_dir / "CLAUDE.md"
    gemini_file = gemini_dir / "GEMINI.md"
    codex_file = codex_dir / "AGENTS.md"

    for path in (claude_file, gemini_file, codex_file):
        _backup_if_exists(path)

    claude_target = (PROJECT_ROOT / "CLAUDE.md").as_posix()
    gemini_target = (PROJECT_ROOT / "GEMINI.md").as_posix()

    claude_file.write_text(
        f"{MARKER}\n# Neo Genesis Claude Global Adapter\n\n@{claude_target}\n",
        encoding="utf-8",
    )
    gemini_file.write_text(
        f"{MARKER}\n# Neo Genesis Gemini Global Adapter\n\n@{gemini_target}\n",
        encoding="utf-8",
    )
    codex_file.write_text((PROJECT_ROOT / "AGENTS.md").read_text(encoding="utf-8"), encoding="utf-8")

    installed = [claude_file, gemini_file, codex_file]
    for agent_name in (
        "neo-reviewer.md",
        "neo-architect.md",
        "neo-implementer.md",
        "neo-conflict-resolver.md",
    ):
        src = PROJECT_ROOT / ".claude" / "agents" / agent_name
        dst = claude_agents_dir / agent_name
        _backup_if_exists(dst)
        dst.write_text(src.read_text(encoding="utf-8"), encoding="utf-8")
        installed.append(dst)
    return installed


def sync(force: bool, install_home: bool, updated_by: str, base_model: str) -> list[Path]:
    credential_outputs = sync_credential_bible(updated_by=updated_by)
    status_payload = _read_json(STATUS_PATH)
    runtime_revision = _runtime_revision()
    status_payload = _ensure_shared_context(status_payload, updated_by=updated_by, runtime_revision=runtime_revision)
    _write_json(STATUS_PATH, status_payload)

    system_prompt = _render_ollama_system(status_payload)
    outputs = {
        PROJECT_ROOT / "AGENTS.md": _render_repo_agents(status_payload),
        PROJECT_ROOT / "CLAUDE.md": _render_claude_md(),
        PROJECT_ROOT / "GEMINI.md": _render_gemini_md(),
        RUNTIME_ROOT / "README.md": _render_runtime_readme(runtime_revision),
        RUNTIME_ROOT / "LIVE_STATUS.md": _render_live_status(status_payload),
        RUNTIME_ROOT / "FLEET_STATUS.md": _render_fleet_status(status_payload, runtime_revision),
        OLLAMA_ROOT / "SYSTEM.md": system_prompt,
        OLLAMA_ROOT / "Modelfile": _render_ollama_modelfile(base_model, system_prompt),
    }

    written: list[Path] = []
    for path, content in outputs.items():
        _write_guarded(path, content, force=force)
        written.append(path)

    # SSOT_REVISION.txt is a canonical single-line hash file. It is structurally
    # impossible to embed the MARKER sentinel inside it without breaking every
    # consumer that reads it as a plain revision string (runtime_heartbeat.py,
    # claude_collab.py, etc). It is only ever written by this script and never
    # hand-edited, so it bypasses _write_guarded() and writes unconditionally.
    # This eliminates the --force requirement on repeat syncs.
    RUNTIME_REVISION_PATH.parent.mkdir(parents=True, exist_ok=True)
    RUNTIME_REVISION_PATH.write_text(runtime_revision + "\n", encoding="utf-8")
    written.append(RUNTIME_REVISION_PATH)

    if install_home:
        written.extend(_install_home_adapters())
    return credential_outputs + written


def main() -> int:
    parser = argparse.ArgumentParser(description="Generate Neo Genesis runtime adapters from SSOT.")
    parser.add_argument("--force", action="store_true", help="Overwrite previously generated files.")
    parser.add_argument("--install-home", action="store_true", help="Install home-level Claude/Gemini/Codex adapters.")
    parser.add_argument("--updated-by", default="codex")
    parser.add_argument("--base-model", default="llama3.1:8b")
    args = parser.parse_args()

    written = sync(
        force=args.force,
        install_home=args.install_home,
        updated_by=args.updated_by,
        base_model=args.base_model,
    )
    for path in written:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
