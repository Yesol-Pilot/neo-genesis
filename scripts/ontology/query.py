"""Neo Genesis Ontology v0.3 -- OAG Data Tool (governed read API).

Foundry AIP pattern (RESEARCH §6, DESIGN §9.2):
> "LLMs do not have direct access to tools; LLMs can only ask to use tools,
>  and these tool calls are then executed within the invoking user's permissions."

This script is the agent-facing read interface. Agents do NOT touch nodes.jsonl directly.

Features:
- Named Object Set queries (.agent/ontology/object_sets.yaml)
- Ad-hoc DuckDB SQL queries
- Markings enforcement (refuse personal-forbidden / restricted unless agent in allowedAgents)
- Impact analysis (transitive depends_on / affects)
- Staleness check (last_observed_at / last_heartbeat_at vs threshold)

Usage:
    python scripts/ontology/query.py --object-set neo://object-set/active-agents [--agent <id>]
    python scripts/ontology/query.py --list-object-sets
    python scripts/ontology/query.py --sql "SELECT ..."
    python scripts/ontology/query.py --impact neo://service/ysh-server/sora-live
    python scripts/ontology/query.py --staleness --threshold-hours 24
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from typing import Any

try:
    import duckdb
    import yaml
except ImportError as e:
    print(f"[ERROR] missing dependency: {e}. Run: pip install duckdb pyyaml")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_DIR = REPO_ROOT / ".agent" / "ontology"
NODES_PATH = ONTOLOGY_DIR / "nodes.jsonl"
EDGES_PATH = ONTOLOGY_DIR / "edges.jsonl"
OBJECT_SETS_PATH = ONTOLOGY_DIR / "object_sets.yaml"

RESTRICTED_MARKINGS = {"personal-forbidden", "restricted", "confidential"}


def setup_duckdb() -> "duckdb.DuckDBPyConnection":
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE VIEW nodes AS SELECT * FROM read_ndjson_auto('{NODES_PATH.as_posix()}', union_by_name=true)")
    con.execute(f"CREATE VIEW edges AS SELECT * FROM read_ndjson_auto('{EDGES_PATH.as_posix()}', union_by_name=true)")
    return con


def apply_markings_filter(rows: list[tuple], cols: list[str], agent_id: str | None) -> list[tuple]:
    """Filter rows: if any row references a restricted-markings node, drop it
    unless agent_id is in allowedAgents."""
    # Simplified: only filter if 'markings' column present in result
    if "markings" not in cols:
        return rows
    idx = cols.index("markings")
    filtered = []
    for r in rows:
        markings = r[idx] or []
        if isinstance(markings, str):
            markings = [markings]
        restricted = set(markings) & RESTRICTED_MARKINGS
        if not restricted:
            filtered.append(r)
        elif agent_id and _agent_allowed(r, cols, agent_id):
            filtered.append(r)
        # else: dropped (markings enforced)
    return filtered


def _agent_allowed(row: tuple, cols: list[str], agent_id: str) -> bool:
    if "allowedAgents" not in cols:
        return False
    idx = cols.index("allowedAgents")
    allowed = row[idx] or []
    return agent_id in allowed


def run_object_set(con, set_id: str, agent_id: str | None) -> dict[str, Any]:
    sets = yaml.safe_load(OBJECT_SETS_PATH.read_text(encoding="utf-8"))["sets"]
    spec = next((s for s in sets if s["id"] == set_id), None)
    if not spec:
        return {"error": f"object_set not found: {set_id}", "available": [s["id"] for s in sets]}
    sql = spec["sql"]
    cursor = con.execute(sql)
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    rows = apply_markings_filter(rows, cols, agent_id)
    return {
        "object_set": set_id,
        "description": spec["description"],
        "cache_ttl_minutes": spec.get("cache_ttl_minutes", 30),
        "agent_id": agent_id,
        "row_count": len(rows),
        "columns": cols,
        "rows": [dict(zip(cols, r)) for r in rows],
    }


def list_object_sets() -> dict[str, Any]:
    sets = yaml.safe_load(OBJECT_SETS_PATH.read_text(encoding="utf-8"))["sets"]
    return {"count": len(sets), "sets": [{"id": s["id"], "description": s["description"]} for s in sets]}


def run_sql(con, sql: str, agent_id: str | None) -> dict[str, Any]:
    """Ad-hoc SQL query (read-only enforced via SELECT-only check)."""
    sql_strip = sql.strip().lower()
    if not sql_strip.startswith("select") and not sql_strip.startswith("with"):
        return {"error": "only SELECT / WITH queries allowed (read-only)"}
    if any(kw in sql_strip for kw in ["insert", "update", "delete", "drop", "create", "alter"]):
        return {"error": "DDL/DML keywords forbidden in --sql mode"}
    cursor = con.execute(sql)
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    rows = apply_markings_filter(rows, cols, agent_id)
    return {
        "row_count": len(rows),
        "columns": cols,
        "rows": [dict(zip(cols, r)) for r in rows[:100]],  # cap 100
    }


def impact_query(con, target_uri: str) -> dict[str, Any]:
    """Transitive impact: what is affected if `target_uri` changes?
    Walks reverse depends_on + reverse references."""
    sql = """
    WITH RECURSIVE impact AS (
      SELECT ? AS id, 0 AS depth, '' AS via
      UNION ALL
      SELECT e."from", i.depth + 1, e.type
      FROM edges e, impact i
      WHERE e."to" = i.id
        AND e.type IN ('depends_on', 'references', 'owned_by', 'affects', 'composed_of')
        AND i.depth < 5
    )
    SELECT DISTINCT n.id, n.rdf_type, n.label, MIN(i.depth) AS min_depth, ANY_VALUE(i.via) AS via_relation
    FROM impact i, nodes n
    WHERE n.id = i.id AND i.depth > 0
    GROUP BY n.id, n.rdf_type, n.label
    ORDER BY min_depth, n.rdf_type
    """
    cursor = con.execute(sql, [target_uri])
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()
    return {
        "target": target_uri,
        "impact_count": len(rows),
        "max_depth": max([r[3] for r in rows], default=0),
        "items": [dict(zip(cols, r)) for r in rows[:50]],
    }


TRANSITIVE_RELATIONS = {"depends_on", "blocks", "supersedes", "prov:wasDerivedFrom", "composed_of"}


def transitive_closure(con, relation: str, start_uri: str | None = None,
                       direction: str = "forward", max_depth: int = 10) -> dict[str, Any]:
    """OWL EL profile transitive closure via DuckDB recursive CTE.

    Per DESIGN §7 (v0.5 EL profile) — depends_on / blocks / supersedes /
    prov:wasDerivedFrom / composed_of 의 closure 를 query-time 추론한다.

    Args:
        relation: One of TRANSITIVE_RELATIONS.
        start_uri: Optional anchor node URI; if None, full closure (cartesian-like).
        direction: 'forward' (from -> to chain) or 'reverse' (to -> from chain).
        max_depth: Recursion depth cap.
    """
    if relation not in TRANSITIVE_RELATIONS:
        return {"error": f"Not a declared-transitive relation: {relation}",
                "transitive_relations": sorted(TRANSITIVE_RELATIONS)}

    if direction == "forward":
        # from -> to: 누가 X 로 끝나는 chain 인가
        seed_filter = f"AND e.\"from\" = '{start_uri}'" if start_uri else ""
        cypher_sql = f"""
            WITH RECURSIVE closure(start_id, current_id, depth, path) AS (
              -- Base: direct edges from start
              SELECT e."from", e."to", 1, ARRAY[e."from", e."to"]
              FROM edges e
              WHERE e.type = '{relation}' {seed_filter}
              UNION ALL
              -- Step: extend chain via same relation
              SELECT c.start_id, e."to", c.depth + 1, list_append(c.path, e."to")
              FROM closure c, edges e
              WHERE e.type = '{relation}'
                AND e."from" = c.current_id
                AND c.depth < {max_depth}
                AND NOT list_contains(c.path, e."to")  -- cycle protection
            )
            SELECT start_id, current_id AS end_id, depth, path
            FROM closure
            ORDER BY start_id, depth, end_id
        """
    else:
        # reverse: 누가 X 에 의존하는 chain 인가
        seed_filter = f"AND e.\"to\" = '{start_uri}'" if start_uri else ""
        cypher_sql = f"""
            WITH RECURSIVE closure(start_id, current_id, depth, path) AS (
              SELECT e."to", e."from", 1, ARRAY[e."to", e."from"]
              FROM edges e
              WHERE e.type = '{relation}' {seed_filter}
              UNION ALL
              SELECT c.start_id, e."from", c.depth + 1, list_append(c.path, e."from")
              FROM closure c, edges e
              WHERE e.type = '{relation}'
                AND e."to" = c.current_id
                AND c.depth < {max_depth}
                AND NOT list_contains(c.path, e."from")
            )
            SELECT start_id, current_id AS end_id, depth, path
            FROM closure
            ORDER BY start_id, depth, end_id
        """

    cursor = con.execute(cypher_sql)
    cols = [d[0] for d in cursor.description]
    rows = cursor.fetchall()

    # Enrich with labels
    inferred = []
    for r in rows:
        node_lookup = con.execute(
            f"SELECT id, label FROM nodes WHERE id IN ({','.join([repr(x) for x in (r[0], r[1])])})"
        ).fetchall()
        label_map = {nid: lbl for nid, lbl in node_lookup}
        inferred.append({
            "start_id": r[0],
            "start_label": label_map.get(r[0], "?"),
            "end_id": r[1],
            "end_label": label_map.get(r[1], "?"),
            "depth": r[2],
            "path": r[3],
            "inferred": r[2] > 1,
        })

    return {
        "relation": relation,
        "direction": direction,
        "start_uri": start_uri,
        "max_depth": max_depth,
        "edges_found": len(rows),
        "inferred_count": sum(1 for r in rows if r[2] > 1),
        "results": inferred[:50],
    }


def staleness_check(con, threshold_hours: int) -> dict[str, Any]:
    """Find Service / Device with stale last_observed_at / last_heartbeat_at."""
    now = dt.datetime.now(dt.timezone.utc)
    threshold = now - dt.timedelta(hours=threshold_hours)
    threshold_iso = threshold.isoformat()
    # Devices
    dev_sql = """
    SELECT id, hostname, last_heartbeat_at
    FROM nodes
    WHERE rdf_type = 'Device' AND last_heartbeat_at < ?
    ORDER BY last_heartbeat_at
    """
    dev_rows = con.execute(dev_sql, [threshold_iso]).fetchall()
    # Services
    svc_sql = """
    SELECT id, name, status, last_observed_at
    FROM nodes
    WHERE rdf_type = 'Service' AND last_observed_at < ?
    ORDER BY last_observed_at
    """
    svc_rows = con.execute(svc_sql, [threshold_iso]).fetchall()
    return {
        "threshold_hours": threshold_hours,
        "threshold_iso": threshold_iso,
        "stale_devices": [{"id": r[0], "hostname": r[1], "last": r[2]} for r in dev_rows],
        "stale_services": [{"id": r[0], "name": r[1], "status": r[2], "last": r[3]} for r in svc_rows],
        "total_stale": len(dev_rows) + len(svc_rows),
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="OAG Data Tool (read-only)")
    parser.add_argument("--object-set", help="Run a named Object Set query")
    parser.add_argument("--list-object-sets", action="store_true")
    parser.add_argument("--sql", help="Ad-hoc SELECT/WITH SQL query")
    parser.add_argument("--impact", help="Impact analysis for a node URI")
    parser.add_argument("--staleness", action="store_true")
    parser.add_argument("--threshold-hours", type=int, default=24)
    parser.add_argument("--closure", choices=sorted(TRANSITIVE_RELATIONS),
                        help="OWL EL transitive closure for a declared-transitive relation")
    parser.add_argument("--closure-start", help="Anchor URI for --closure (optional)")
    parser.add_argument("--closure-direction", choices=["forward", "reverse"], default="forward")
    parser.add_argument("--closure-depth", type=int, default=10)
    parser.add_argument("--agent", help="Calling agent URI (for markings enforcement)", default=None)
    parser.add_argument("--output", choices=["json", "text"], default="json")
    args = parser.parse_args()

    if not NODES_PATH.exists():
        print("[ERROR] nodes.jsonl not found. Run extract_minimal.py first.")
        return 2

    if args.list_object_sets:
        print(json.dumps(list_object_sets(), indent=2, ensure_ascii=False))
        return 0

    con = setup_duckdb()

    if args.object_set:
        result = run_object_set(con, args.object_set, args.agent)
    elif args.sql:
        result = run_sql(con, args.sql, args.agent)
    elif args.impact:
        result = impact_query(con, args.impact)
    elif args.staleness:
        result = staleness_check(con, args.threshold_hours)
    elif args.closure:
        result = transitive_closure(
            con, args.closure,
            start_uri=args.closure_start,
            direction=args.closure_direction,
            max_depth=args.closure_depth,
        )
    else:
        parser.print_help()
        return 1

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0


if __name__ == "__main__":
    sys.exit(main())
