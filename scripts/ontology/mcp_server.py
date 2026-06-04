"""Neo Genesis Ontology v0.3 -- MCP Server (FastMCP).

Wraps query.py / mutate.py / auto_record.py as MCP tools so Claude / Codex /
Sora can invoke ontology operations natively (instead of Bash + Python).

Tools exposed:
- ontology_list_object_sets   : list named queries
- ontology_query_object_set   : run a named query
- ontology_query_sql          : ad-hoc SELECT (read-only, markings enforced)
- ontology_impact             : transitive impact analysis
- ontology_staleness          : find stale Service / Device
- ontology_add_task           : add new Task via write_queue
- ontology_modify_status      : modify a node's status
- ontology_add_edge           : add new edge
- ontology_record_action      : append ActionRun (fast-path)
- ontology_graphrag_query     : query communities by substring

Registration (Claude Desktop / Code config snippet):
    {
      "mcpServers": {
        "neo-genesis-ontology": {
          "command": "python",
          "args": ["D:/00.test/neo-genesis/scripts/ontology/mcp_server.py"],
          "env": {}
        }
      }
    }

Run standalone (stdio transport, default):
    python scripts/ontology/mcp_server.py
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path
from typing import Any

try:
    from mcp.server.fastmcp import FastMCP
except ImportError:
    print("[ERROR] mcp package not installed. Run: pip install mcp")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "ontology"

mcp = FastMCP("neo-genesis-ontology")


def _run(args: list[str]) -> str:
    """Run a Python subscript and return stdout (or stderr on failure)."""
    proc = subprocess.run(
        [sys.executable] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        cwd=str(REPO_ROOT),
    )
    if proc.returncode != 0:
        return json.dumps({
            "error": f"exit_code={proc.returncode}",
            "stderr": proc.stderr[:1000],
            "stdout": proc.stdout[:1000],
        })
    return proc.stdout


# ============================================================
# Read Tools
# ============================================================

@mcp.tool()
def ontology_list_object_sets() -> str:
    """List all named Object Set queries available."""
    return _run([str(SCRIPTS_DIR / "query.py"), "--list-object-sets"])


@mcp.tool()
def ontology_query_object_set(object_set_id: str, agent: str | None = None) -> str:
    """Run a named Object Set query.

    Args:
        object_set_id: URI like 'neo://object-set/active-agents'.
        agent: Calling agent URI for markings enforcement.
    """
    args = [str(SCRIPTS_DIR / "query.py"), "--object-set", object_set_id]
    if agent:
        args.extend(["--agent", agent])
    return _run(args)


@mcp.tool()
def ontology_query_sql(sql: str, agent: str | None = None) -> str:
    """Run ad-hoc SELECT/WITH SQL query (read-only enforced).

    Args:
        sql: SELECT or WITH query (DDL/DML forbidden).
        agent: Calling agent URI for markings enforcement.
    """
    args = [str(SCRIPTS_DIR / "query.py"), "--sql", sql]
    if agent:
        args.extend(["--agent", agent])
    return _run(args)


@mcp.tool()
def ontology_impact(target_uri: str) -> str:
    """Transitive impact analysis: what is affected if `target_uri` changes?

    Walks reverse depends_on / references / affects / composed_of edges up to depth 5.

    Args:
        target_uri: Node URI like 'neo://service/ysh-server/supabase-api'.
    """
    return _run([str(SCRIPTS_DIR / "query.py"), "--impact", target_uri])


@mcp.tool()
def ontology_staleness(threshold_hours: int = 24) -> str:
    """Find Service / Device with last observation older than threshold_hours.

    Args:
        threshold_hours: Staleness threshold in hours (default 24).
    """
    return _run([str(SCRIPTS_DIR / "query.py"), "--staleness",
                 "--threshold-hours", str(threshold_hours)])


@mcp.tool()
def ontology_graphrag_query(query: str, top_k: int = 3) -> str:
    """Query communities (clusters) by substring match.

    Args:
        query: Substring to match against community member labels.
        top_k: Number of top communities to return.
    """
    return _run([str(SCRIPTS_DIR / "graphrag.py"), "--query", query,
                 "--top-k", str(top_k)])


# ============================================================
# Write Tools (governed via write_queue)
# ============================================================

@mcp.tool()
def ontology_add_task(title: str, priority: str = "P2",
                      agent_id: str = "claude-opus-4-7") -> str:
    """Add a new Task via write_queue (governed mutation).

    Args:
        title: Task title.
        priority: P0 / P1 / P2 / P3.
        agent_id: Agent slug for ActionRun attribution.
    """
    args = [str(SCRIPTS_DIR / "mutate.py"), "--add-task", title,
            "--priority", priority, "--agent-id", agent_id, "--apply"]
    return _run(args)


@mcp.tool()
def ontology_modify_status(uri: str, new_status: str,
                           agent_id: str = "claude-opus-4-7") -> str:
    """Modify the `status` field of an existing node via write_queue.

    Args:
        uri: Target node URI.
        new_status: New status value (e.g. 'done', 'in_progress', 'blocked').
        agent_id: Agent slug for ActionRun attribution.
    """
    args = [str(SCRIPTS_DIR / "mutate.py"), "--modify-status", uri, new_status,
            "--agent-id", agent_id, "--apply"]
    return _run(args)


@mcp.tool()
def ontology_add_edge(from_uri: str, edge_type: str, to_uri: str,
                      agent_id: str = "claude-opus-4-7") -> str:
    """Add a new edge between two existing nodes via write_queue.

    Args:
        from_uri: Source node URI.
        edge_type: One of the 17 valid relations (e.g. 'depends_on', 'references').
        to_uri: Target node URI.
        agent_id: Agent slug for ActionRun attribution.
    """
    args = [str(SCRIPTS_DIR / "mutate.py"), "--add-edge", from_uri, edge_type, to_uri,
            "--agent-id", agent_id, "--apply"]
    return _run(args)


@mcp.tool()
def ontology_record_action(kind: str, agent: str, affected: list[str] | None = None,
                           meta: dict | None = None, result: str = "success",
                           label: str | None = None) -> str:
    """Append a single ActionRun (fast-path, file-locked, idempotent).

    For high-volume events (dispatcher_route / killswitch_fire / deploy / mcp_tool_call).
    Use ontology_add_task / modify_status / add_edge for actual node mutations.

    Args:
        kind: One of: dispatcher_route / killswitch_fire / deploy / commit /
              mcp_tool_call / persona_invocation / external_api_call /
              ontology_mutation / extract / heartbeat.
        agent: Agent URI triggering the action.
        affected: List of affected node URIs.
        meta: Extra context dict.
        result: 'success' / 'failure' / 'partial' / 'blocked'.
        label: Optional short label.
    """
    args = [str(SCRIPTS_DIR / "auto_record.py"),
            "--kind", kind, "--agent", agent, "--result", result]
    if affected:
        args.extend(["--affected"] + affected)
    if meta:
        args.extend(["--meta", json.dumps(meta)])
    if label:
        args.extend(["--label", label])
    return _run(args)


# ============================================================
# Health / Stats
# ============================================================

@mcp.tool()
def ontology_stats() -> str:
    """Return ontology size + class breakdown (smoke check)."""
    sql = """
    SELECT rdf_type, COUNT(*) AS count
    FROM nodes
    GROUP BY rdf_type
    ORDER BY count DESC
    """
    return _run([str(SCRIPTS_DIR / "query.py"), "--sql", sql])


@mcp.tool()
def ontology_validate() -> str:
    """Run all 6 P0 quality gates (URI uniq / format / fields / edge integrity / markings / secrets)."""
    return _run([str(SCRIPTS_DIR / "validate.py")])


@mcp.tool()
def ontology_validate_competency() -> str:
    """Run 20 competency questions via DuckDB SQL."""
    return _run([str(SCRIPTS_DIR / "validate_competency.py")])


# ============================================================
# Main (stdio transport default)
# ============================================================

if __name__ == "__main__":
    mcp.run()
