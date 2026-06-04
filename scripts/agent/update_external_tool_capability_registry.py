#!/usr/bin/env python3
"""Generate the external tool capability registry.

External tools are session/app capabilities such as Codex developer tools,
hosted web/image tools, and deferred connector plugin families. They cannot be
imported from the Neo Genesis Python runtime, so this generator validates and
indexes the declarative source file instead.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from datetime import datetime
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENT_ROOT = PROJECT_ROOT / ".agent"
REGISTRY_ROOT = AGENT_ROOT / "registries"
SOURCE_JSON = REGISTRY_ROOT / "external_tool_capabilities.source.json"
REGISTRY_JSON = REGISTRY_ROOT / "external_tool_capabilities.json"
REGISTRY_MD = REGISTRY_ROOT / "external_tool_capabilities.md"

REQUIRED_FIELDS = {
    "id",
    "namespace",
    "tool",
    "display_name",
    "capability_type",
    "status",
    "callable_by",
    "authority_tier",
    "external_side_effect",
    "description",
}


def _now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _load_source() -> dict[str, Any]:
    if not SOURCE_JSON.exists():
        raise FileNotFoundError(f"external capability source not found: {SOURCE_JSON}")
    return json.loads(SOURCE_JSON.read_text(encoding="utf-8"))


def _validate_capabilities(capabilities: list[dict[str, Any]]) -> list[dict[str, Any]]:
    diagnostics: list[dict[str, Any]] = []
    seen: set[str] = set()

    for idx, item in enumerate(capabilities):
        capability_id = item.get("id", f"<missing:{idx}>")
        missing = sorted(REQUIRED_FIELDS - set(item.keys()))
        if missing:
            diagnostics.append({
                "id": capability_id,
                "severity": "error",
                "message": "missing required fields",
                "fields": missing,
            })
        if capability_id in seen:
            diagnostics.append({
                "id": capability_id,
                "severity": "error",
                "message": "duplicate capability id",
            })
        seen.add(capability_id)

        callable_by = item.get("callable_by")
        if not isinstance(callable_by, list) or not callable_by:
            diagnostics.append({
                "id": capability_id,
                "severity": "error",
                "message": "callable_by must be a non-empty list",
            })

        handoff = item.get("handoff_required_for", [])
        if handoff and not isinstance(handoff, list):
            diagnostics.append({
                "id": capability_id,
                "severity": "error",
                "message": "handoff_required_for must be a list when present",
            })

        tier = item.get("authority_tier", "")
        if tier not in {"G0", "G1", "G2", "G3", "G4", "G5"}:
            diagnostics.append({
                "id": capability_id,
                "severity": "error",
                "message": "authority_tier must be G0-G5",
                "authority_tier": tier,
            })

    return diagnostics


def _index(capabilities: list[dict[str, Any]]) -> dict[str, Any]:
    indexes: dict[str, dict[str, list[str]]] = {
        "by_namespace": {},
        "by_status": {},
        "by_capability_type": {},
        "by_authority_tier": {},
        "by_callable_by": {},
    }

    for item in capabilities:
        capability_id = item["id"]
        for key, index_name in (
            ("namespace", "by_namespace"),
            ("status", "by_status"),
            ("capability_type", "by_capability_type"),
            ("authority_tier", "by_authority_tier"),
        ):
            value = str(item.get(key, "unknown"))
            indexes[index_name].setdefault(value, []).append(capability_id)

        for caller in item.get("callable_by", []):
            indexes["by_callable_by"].setdefault(str(caller), []).append(capability_id)

    for bucket in indexes.values():
        for values in bucket.values():
            values.sort()
    return {name: dict(sorted(bucket.items())) for name, bucket in indexes.items()}


def _registry_hash(payload: dict[str, Any]) -> str:
    stable = dict(payload)
    for volatile_key in ("generated_at", "updated_by", "registry_revision"):
        stable.pop(volatile_key, None)
    material = json.dumps(stable, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def build_registry(updated_by: str = "agent") -> dict[str, Any]:
    source = _load_source()
    capabilities = sorted(source.get("capabilities", []), key=lambda item: item.get("id", ""))
    diagnostics = _validate_capabilities(capabilities)
    indexes = _index(capabilities)

    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "scope": "external_tool_capabilities",
        "generated_at": _now_iso(),
        "updated_by": updated_by,
        "project_root": str(PROJECT_ROOT),
        "source_path": str(SOURCE_JSON),
        "registry_paths": {
            "json": str(REGISTRY_JSON),
            "markdown": str(REGISTRY_MD),
        },
        "capability_count": len(capabilities),
        "capabilities": capabilities,
        "indexes": indexes,
        "diagnostics": {
            "error_count": len([item for item in diagnostics if item.get("severity") == "error"]),
            "items": diagnostics,
        },
        "refresh_command": "python scripts/agent/update_external_tool_capability_registry.py --updated-by <agent>",
        "policy_document": str(AGENT_ROOT / "knowledge" / "CALLABLE_TOOLS_REGISTRY_POLICY.md"),
        "local_callable_registry": str(REGISTRY_ROOT / "callable_tools.json"),
    }
    payload["registry_revision"] = _registry_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "<!-- generated: scripts/agent/update_external_tool_capability_registry.py -->",
        "# External Tool Capabilities",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Updated by: `{payload.get('updated_by')}`",
        f"- Registry revision: `{payload.get('registry_revision')}`",
        f"- Capability count: `{payload.get('capability_count')}`",
        "- JSON SSOT: `.agent/registries/external_tool_capabilities.json`",
        "- Source: `.agent/registries/external_tool_capabilities.source.json`",
        "- Refresh: `python scripts/agent/update_external_tool_capability_registry.py --updated-by <agent>`",
        "",
        "## By Namespace",
    ]

    for namespace, names in payload.get("indexes", {}).get("by_namespace", {}).items():
        lines.append(f"- `{namespace}` ({len(names)}): " + ", ".join(f"`{name}`" for name in names))

    lines.extend(["", "## By Capability Type"])
    for capability_type, names in payload.get("indexes", {}).get("by_capability_type", {}).items():
        lines.append(f"- `{capability_type}` ({len(names)}): " + ", ".join(f"`{name}`" for name in names))

    lines.extend(["", "## By Authority Tier"])
    for tier, names in payload.get("indexes", {}).get("by_authority_tier", {}).items():
        lines.append(f"- `{tier}` ({len(names)}): " + ", ".join(f"`{name}`" for name in names))

    diagnostics = payload.get("diagnostics", {})
    if diagnostics.get("error_count"):
        lines.extend(["", "## Diagnostics"])
        for item in diagnostics.get("items", []):
            lines.append(f"- `{item.get('id')}`: {item.get('message')}")

    return "\n".join(lines) + "\n"


def write_registry(payload: dict[str, Any]) -> None:
    if payload.get("diagnostics", {}).get("error_count"):
        raise RuntimeError("external capability source has validation errors")
    REGISTRY_ROOT.mkdir(parents=True, exist_ok=True)
    REGISTRY_JSON.write_text(
        json.dumps(payload, ensure_ascii=False, indent=2, default=str) + "\n",
        encoding="utf-8",
    )
    REGISTRY_MD.write_text(render_markdown(payload), encoding="utf-8")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--updated-by", default="agent", help="agent name recorded in the registry")
    parser.add_argument("--check", action="store_true", help="do not write files; print JSON summary")
    args = parser.parse_args()

    payload = build_registry(updated_by=args.updated_by)
    if not args.check:
        write_registry(payload)

    summary = {
        "status": "ok" if payload["diagnostics"]["error_count"] == 0 else "invalid",
        "check_only": args.check,
        "capability_count": payload["capability_count"],
        "registry_revision": payload["registry_revision"],
        "json": str(REGISTRY_JSON),
        "markdown": str(REGISTRY_MD),
        "error_count": payload["diagnostics"]["error_count"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0 if summary["status"] == "ok" else 1


if __name__ == "__main__":
    raise SystemExit(main())
