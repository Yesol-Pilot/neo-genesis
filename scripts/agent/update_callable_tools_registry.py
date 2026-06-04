#!/usr/bin/env python3
"""Generate the Neo Genesis callable tools registry.

The registry is intentionally derived from live Python modules instead of a
hand-maintained list. Agents can refresh it after tool changes and consult the
same JSON/Markdown artifacts before assuming a tool exists.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib
import inspect
import json
import logging
import sys
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable


PROJECT_ROOT = Path(__file__).resolve().parents[2]
AGENT_ROOT = PROJECT_ROOT / ".agent"
REGISTRY_ROOT = AGENT_ROOT / "registries"
REGISTRY_JSON = REGISTRY_ROOT / "callable_tools.json"
REGISTRY_MD = REGISTRY_ROOT / "callable_tools.md"
TOOL_MODULES_DIR = PROJECT_ROOT / "src" / "core" / "tools"
AGENT_ROUTER_PATH = PROJECT_ROOT / "src" / "core" / "brain" / "agent_router.py"
EXECUTION_GATE_PATH = PROJECT_ROOT / "src" / "core" / "governance" / "execution_gate.py"
TOOL_MODULE_PACKAGE = "src.core.tools"


def _ensure_project_path() -> None:
    root = str(PROJECT_ROOT)
    if root not in sys.path:
        sys.path.insert(0, root)
    logging.getLogger("neo.tools").setLevel(logging.ERROR)
    logging.getLogger("neo.brain.router").setLevel(logging.ERROR)


def _now_iso() -> str:
    return datetime.now().astimezone().replace(microsecond=0).isoformat()


def _short_doc(func: Callable[..., Any]) -> str:
    doc = inspect.getdoc(func) or ""
    for line in doc.splitlines():
        cleaned = line.strip()
        if cleaned:
            return cleaned[:220]
    return ""


def _safe_signature(func: Callable[..., Any]) -> str:
    try:
        return str(inspect.signature(func))
    except Exception:
        return "(...)"


def _safe_source(func: Callable[..., Any]) -> dict[str, Any]:
    try:
        source_file = inspect.getsourcefile(func) or ""
        _, line_no = inspect.getsourcelines(func)
    except Exception:
        source_file = ""
        line_no = None

    if source_file:
        try:
            path = Path(source_file).resolve()
            display = str(path)
        except Exception:
            display = source_file
    else:
        display = ""

    return {"path": display, "line": line_no}


def _policy_metadata(tool_name: str) -> dict[str, Any]:
    try:
        from src.core.governance.execution_gate import (
            AUTHORITY_ORDER,
            READONLY_TOOL_PREFIXES,
            get_tool_policy,
        )

        policy = get_tool_policy(tool_name)
        authority_tier = policy.authority_tier
        requires_approval = (
            policy.external_side_effect
            or AUTHORITY_ORDER.get(authority_tier, 0) >= AUTHORITY_ORDER["G4"]
        )
        readonly_by_prefix = any(tool_name.startswith(prefix) for prefix in READONLY_TOOL_PREFIXES)
        return {
            "authority_tier": authority_tier,
            "action": policy.action,
            "controls": list(policy.controls),
            "external_side_effect": policy.external_side_effect,
            "requires_approval": requires_approval,
            "readonly_by_prefix": readonly_by_prefix,
        }
    except Exception as exc:
        return {
            "authority_tier": "unknown",
            "action": "policy lookup failed",
            "controls": [],
            "external_side_effect": False,
            "requires_approval": True,
            "readonly_by_prefix": False,
            "policy_error": str(exc),
        }


def _describe_callable(
    func: Callable[..., Any],
    *,
    origin: str,
    registered_in_tools_list: bool,
) -> dict[str, Any]:
    name = getattr(func, "__name__", repr(func))
    module = getattr(func, "__module__", "")
    source = _safe_source(func)
    status = "available"
    doc = _short_doc(func)
    source_text = ""
    try:
        source_text = inspect.getsource(func).lower()
    except Exception:
        source_text = ""
    if (
        "unavailable" in doc.lower()
        or "not installed" in doc.lower()
        or '"unavailable"' in source_text
        or "not installed" in source_text
    ):
        status = "unavailable_stub"
    if not registered_in_tools_list:
        status = "route_only" if status == "available" else status

    return {
        "name": name,
        "module": module,
        "qualname": getattr(func, "__qualname__", name),
        "signature": _safe_signature(func),
        "doc_summary": doc,
        "source": source,
        "origin": origin,
        "registered_in_tools_list": registered_in_tools_list,
        "status": status,
        "policy": _policy_metadata(name),
    }


def _tool_module_names() -> list[str]:
    if not TOOL_MODULES_DIR.exists():
        return []
    names = []
    for path in TOOL_MODULES_DIR.glob("*.py"):
        if path.name == "__init__.py" or path.name.startswith("_"):
            continue
        names.append(path.stem)
    return sorted(set(names))


def _collect_tool_modules() -> tuple[dict[str, dict[str, Any]], list[dict[str, Any]]]:
    tools_by_name: dict[str, dict[str, Any]] = {}
    module_reports: list[dict[str, Any]] = []

    for module_name in _tool_module_names():
        import_name = f"{TOOL_MODULE_PACKAGE}.{module_name}"
        report: dict[str, Any] = {
            "module": import_name,
            "source": str(TOOL_MODULES_DIR / f"{module_name}.py"),
            "status": "unknown",
            "tool_count": 0,
            "tool_names": [],
        }
        try:
            module = importlib.import_module(import_name)
            raw_tools = getattr(module, "TOOLS", [])
            if raw_tools is None:
                raw_tools = []
            for item in raw_tools:
                if not callable(item):
                    continue
                tool = _describe_callable(
                    item,
                    origin="module_tools",
                    registered_in_tools_list=True,
                )
                name = tool["name"]
                if name in tools_by_name:
                    tools_by_name[name].setdefault("duplicates", []).append(tool)
                else:
                    tools_by_name[name] = tool
                report["tool_names"].append(name)
            report["tool_count"] = len(report["tool_names"])
            report["status"] = "ok"
        except Exception as exc:
            report["status"] = "import_failed"
            report["error"] = str(exc)
            report["traceback_tail"] = traceback.format_exc(limit=3).splitlines()[-6:]
        module_reports.append(report)

    return tools_by_name, module_reports


def _collect_agent_routes(tools_by_name: dict[str, dict[str, Any]]) -> tuple[dict[str, Any], list[dict[str, Any]]]:
    routes: dict[str, Any] = {}
    route_errors: list[dict[str, Any]] = []

    try:
        router = importlib.import_module("src.core.brain.agent_router")
        agents = getattr(router, "AGENTS", {})
        get_agent_tools = getattr(router, "_get_agent_tools")
    except Exception as exc:
        route_errors.append({
            "agent_id": "*",
            "status": "router_import_failed",
            "error": str(exc),
            "traceback_tail": traceback.format_exc(limit=3).splitlines()[-6:],
        })
        return routes, route_errors

    for agent_id in sorted(agents):
        config = agents.get(agent_id, {}) or {}
        try:
            route_tools = list(get_agent_tools(agent_id))
            tool_names: list[str] = []
            for func in route_tools:
                if not callable(func):
                    continue
                name = getattr(func, "__name__", repr(func))
                tool_names.append(name)
                if name not in tools_by_name:
                    tools_by_name[name] = _describe_callable(
                        func,
                        origin=f"agent_route:{agent_id}",
                        registered_in_tools_list=False,
                    )
            routes[agent_id] = {
                "name": config.get("name", agent_id),
                "description": config.get("description", ""),
                "tools_module": config.get("tools_module"),
                "tool_count": len(tool_names),
                "tool_names": tool_names,
            }
        except Exception as exc:
            route_errors.append({
                "agent_id": agent_id,
                "status": "route_failed",
                "error": str(exc),
                "traceback_tail": traceback.format_exc(limit=3).splitlines()[-6:],
            })

    return routes, route_errors


def _index_tools(tools: list[dict[str, Any]]) -> dict[str, Any]:
    by_module: dict[str, Any] = {}
    by_authority_tier: dict[str, list[str]] = {}
    by_status: dict[str, list[str]] = {}

    for tool in tools:
        module = tool.get("module") or "unknown"
        by_module.setdefault(module, {"tool_count": 0, "tool_names": []})
        by_module[module]["tool_count"] += 1
        by_module[module]["tool_names"].append(tool["name"])

        tier = tool.get("policy", {}).get("authority_tier", "unknown")
        by_authority_tier.setdefault(tier, []).append(tool["name"])

        status = tool.get("status", "unknown")
        by_status.setdefault(status, []).append(tool["name"])

    for bucket in (by_module, by_authority_tier, by_status):
        for value in bucket.values():
            if isinstance(value, dict):
                value["tool_names"] = sorted(value["tool_names"])
            elif isinstance(value, list):
                value.sort()

    return {
        "by_module": dict(sorted(by_module.items())),
        "by_authority_tier": dict(sorted(by_authority_tier.items())),
        "by_status": dict(sorted(by_status.items())),
    }


def _registry_hash(payload: dict[str, Any]) -> str:
    stable = dict(payload)
    for volatile_key in ("generated_at", "updated_by", "registry_revision"):
        stable.pop(volatile_key, None)
    material = json.dumps(stable, ensure_ascii=False, sort_keys=True, default=str)
    return hashlib.sha256(material.encode("utf-8")).hexdigest()[:16]


def build_registry(updated_by: str = "agent") -> dict[str, Any]:
    _ensure_project_path()
    tools_by_name, module_reports = _collect_tool_modules()
    agent_routes, route_errors = _collect_agent_routes(tools_by_name)
    tools = sorted(tools_by_name.values(), key=lambda item: (item["name"], item.get("module", "")))
    indexes = _index_tools(tools)

    failed_modules = [item for item in module_reports if item.get("status") != "ok"]
    payload: dict[str, Any] = {
        "schema_version": "1.0",
        "scope": "neo_genesis_local_python_tools",
        "generated_at": _now_iso(),
        "updated_by": updated_by,
        "project_root": str(PROJECT_ROOT),
        "registry_paths": {
            "json": str(REGISTRY_JSON),
            "markdown": str(REGISTRY_MD),
        },
        "source_paths": {
            "tool_modules_dir": str(TOOL_MODULES_DIR),
            "agent_router": str(AGENT_ROUTER_PATH),
            "execution_gate": str(EXECUTION_GATE_PATH),
        },
        "tool_count": len(tools),
        "agent_count": len(agent_routes),
        "tools": tools,
        "indexes": indexes,
        "agent_routes": agent_routes,
        "module_imports": module_reports,
        "diagnostics": {
            "failed_module_count": len(failed_modules),
            "failed_modules": failed_modules,
            "route_error_count": len(route_errors),
            "route_errors": route_errors,
        },
        "refresh_command": "python scripts/agent/update_callable_tools_registry.py --updated-by <agent>",
        "policy_document": str(AGENT_ROOT / "knowledge" / "CALLABLE_TOOLS_REGISTRY_POLICY.md"),
    }
    payload["registry_revision"] = _registry_hash(payload)
    return payload


def render_markdown(payload: dict[str, Any]) -> str:
    lines = [
        "<!-- generated: scripts/agent/update_callable_tools_registry.py -->",
        "# Callable Tools Registry",
        "",
        f"- Generated at: `{payload.get('generated_at')}`",
        f"- Updated by: `{payload.get('updated_by')}`",
        f"- Registry revision: `{payload.get('registry_revision')}`",
        f"- Tool count: `{payload.get('tool_count')}`",
        f"- Agent route count: `{payload.get('agent_count')}`",
        f"- JSON SSOT: `.agent/registries/callable_tools.json`",
        f"- Refresh: `python scripts/agent/update_callable_tools_registry.py --updated-by <agent>`",
        "",
        "## Tools By Module",
    ]

    for module, item in payload.get("indexes", {}).get("by_module", {}).items():
        names = ", ".join(f"`{name}`" for name in item.get("tool_names", []))
        lines.append(f"- `{module}` ({item.get('tool_count', 0)}): {names}")

    lines.extend(["", "## Tools By Authority Tier"])
    for tier, names in payload.get("indexes", {}).get("by_authority_tier", {}).items():
        lines.append(f"- `{tier}` ({len(names)}): " + ", ".join(f"`{name}`" for name in names))

    lines.extend(["", "## Agent Routes"])
    for agent_id, route in payload.get("agent_routes", {}).items():
        names = ", ".join(f"`{name}`" for name in route.get("tool_names", []))
        lines.append(f"- `{agent_id}` ({route.get('tool_count', 0)}): {names}")

    diagnostics = payload.get("diagnostics", {})
    if diagnostics.get("failed_module_count") or diagnostics.get("route_error_count"):
        lines.extend(["", "## Diagnostics"])
        for item in diagnostics.get("failed_modules", []):
            lines.append(f"- module `{item.get('module')}`: {item.get('error')}")
        for item in diagnostics.get("route_errors", []):
            lines.append(f"- route `{item.get('agent_id')}`: {item.get('error')}")

    return "\n".join(lines) + "\n"


def write_registry(payload: dict[str, Any]) -> None:
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
        "status": "ok",
        "check_only": args.check,
        "tool_count": payload["tool_count"],
        "agent_count": payload["agent_count"],
        "registry_revision": payload["registry_revision"],
        "json": str(REGISTRY_JSON),
        "markdown": str(REGISTRY_MD),
        "failed_module_count": payload["diagnostics"]["failed_module_count"],
        "route_error_count": payload["diagnostics"]["route_error_count"],
    }
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
