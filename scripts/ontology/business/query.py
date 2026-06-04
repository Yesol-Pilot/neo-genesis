"""Neo Genesis Business Ontology -- OAG Data Tool (read-only query interface).

The agent-facing READ surface for the BUSINESS layer (neo://biz/*). Agents do
NOT touch biz/nodes.jsonl directly -- they ask questions here.

Mirrors scripts/ontology/query.py (meta layer) but over the business graph:
- Named Object Set queries (.agent/ontology/business/object_sets.yaml)
- Ad-hoc read-only SQL (SELECT/WITH only)
- Impact analysis (biz edge traversal)
- markings enforcement (personal-forbidden never leaks)

AuraDB-independent: queries the local JSONL via DuckDB. The cloud mirror is
optional; this is the resilient operating read layer.

Usage:
    python scripts/ontology/business/query.py --list-object-sets
    python scripts/ontology/business/query.py --object-set kpi-live-values
    python scripts/ontology/business/query.py --sql "SELECT rdf_type, count(*) FROM nodes GROUP BY 1"
    python scripts/ontology/business/query.py --impact neo://biz/product/kott
    python scripts/ontology/business/query.py --stats
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
BIZ_DIR = REPO_ROOT / ".agent" / "ontology" / "business"
NODES_PATH = BIZ_DIR / "nodes.jsonl"
EDGES_PATH = BIZ_DIR / "edges.jsonl"
OBJECT_SETS_PATH = BIZ_DIR / "object_sets.yaml"

RESTRICTED_MARKINGS = {"personal-forbidden", "restricted", "confidential"}

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass


def setup_duckdb():
    import duckdb
    con = duckdb.connect(":memory:")
    con.execute(
        f"CREATE VIEW nodes AS SELECT * FROM read_ndjson_auto('{NODES_PATH.as_posix()}', union_by_name=true)"
    )
    con.execute(
        f"CREATE VIEW edges AS SELECT * FROM read_ndjson_auto('{EDGES_PATH.as_posix()}', union_by_name=true)"
    )
    return con


def _markings_of(row: dict) -> set[str]:
    m = row.get("markings") or []
    if isinstance(m, str):
        m = [m]
    return set(m)


def apply_markings_filter(rows: list[dict], agent_id: str | None) -> list[dict]:
    """Drop rows referencing restricted markings unless agent is allowlisted."""
    out = []
    for r in rows:
        restricted = _markings_of(r) & RESTRICTED_MARKINGS
        if not restricted:
            out.append(r)
        elif agent_id and agent_id in (r.get("allowedAgents") or []):
            out.append(r)
    return out


def _rows_as_dicts(cursor) -> tuple[list[str], list[dict]]:
    cols = [d[0] for d in cursor.description]
    return cols, [dict(zip(cols, r)) for r in cursor.fetchall()]


def load_object_sets() -> list[dict]:
    import yaml
    return yaml.safe_load(OBJECT_SETS_PATH.read_text(encoding="utf-8"))["sets"]


def run_object_set(con, set_id: str, agent_id: str | None) -> dict[str, Any]:
    sets = load_object_sets()
    spec = next((s for s in sets if s["id"] == set_id), None)
    if not spec:
        return {"error": f"object_set not found: {set_id}",
                "available": [s["id"] for s in sets]}
    try:
        cols, rows = _rows_as_dicts(con.execute(spec["sql"]))
    except Exception as e:
        return {"object_set": set_id, "error": f"query failed: {type(e).__name__}: {str(e)[:200]}"}
    rows = apply_markings_filter(rows, agent_id)
    return {
        "object_set": set_id,
        "description": spec["description"],
        "cache_ttl_minutes": spec.get("cache_ttl_minutes", 30),
        "agent_id": agent_id,
        "row_count": len(rows),
        "columns": cols,
        "rows": rows,
    }


def list_object_sets() -> dict[str, Any]:
    sets = load_object_sets()
    return {"count": len(sets),
            "sets": [{"id": s["id"], "description": s["description"]} for s in sets]}


def run_sql(con, sql: str, agent_id: str | None) -> dict[str, Any]:
    s = sql.strip().lower()
    if not (s.startswith("select") or s.startswith("with")):
        return {"error": "only SELECT / WITH queries allowed (read-only)"}
    if any(kw in s for kw in ["insert", "update", "delete", "drop", "create", "alter", "attach", "copy"]):
        return {"error": "DDL/DML keywords forbidden in --sql mode"}
    try:
        cols, rows = _rows_as_dicts(con.execute(sql))
    except Exception as e:
        return {"error": f"query failed: {type(e).__name__}: {str(e)[:200]}"}
    rows = apply_markings_filter(rows, agent_id)
    return {"row_count": len(rows), "columns": cols, "rows": rows[:100]}


def impact_query(con, target_uri: str) -> dict[str, Any]:
    """What is affected if target_uri changes? Reverse traversal over biz edges."""
    sql = """
    WITH RECURSIVE impact AS (
      SELECT ? AS id, 0 AS depth, '' AS via
      UNION ALL
      SELECT e."from", i.depth + 1, e.type
      FROM edges e, impact i
      WHERE e."to" = i.id AND i.depth < 5
    )
    SELECT DISTINCT n.id, n.rdf_type, n.label, MIN(i.depth) AS min_depth,
           ANY_VALUE(i.via) AS via_relation
    FROM impact i, nodes n
    WHERE n.id = i.id AND i.depth > 0
    GROUP BY n.id, n.rdf_type, n.label
    ORDER BY min_depth, n.rdf_type
    """
    cols, rows = _rows_as_dicts(con.execute(sql, [target_uri]))
    return {"target": target_uri, "impact_count": len(rows),
            "max_depth": max([r["min_depth"] for r in rows], default=0),
            "items": rows[:50]}


COMPETENCY_PATH = BIZ_DIR / "competency_questions.yaml"


def run_competency(con) -> dict[str, Any]:
    """Run business competency questions -- the acceptance gate for whether the
    ontology actually models the company (mirrors meta validate_competency)."""
    import yaml
    qs = yaml.safe_load(COMPETENCY_PATH.read_text(encoding="utf-8"))["questions"]
    results = []
    p0_fail = 0
    for q in qs:
        try:
            row = con.execute(q["sql"]).fetchone()
            val = row[0] if row else 0
            ok = True
            if "expect_min_value" in q and (val is None or val < q["expect_min_value"]):
                ok = False
            if "expect_exact_value" in q and val != q["expect_exact_value"]:
                ok = False
            if "expect_min_rows" in q and (val is None or val < 1):
                ok = False
            status = "PASS" if ok else "FAIL"
        except Exception as e:
            status, val = "ERROR", str(e)[:120]
            ok = False
        if not ok and q.get("severity") == "P0":
            p0_fail += 1
        results.append({"id": q["id"], "severity": q.get("severity"),
                        "question": q["question"], "value": val, "status": status})
    passed = sum(1 for r in results if r["status"] == "PASS")
    return {"total": len(qs), "passed": passed, "failed": len(qs) - passed,
            "p0_failures": p0_fail,
            "gate": "PASS" if p0_fail == 0 else "FAIL",
            "results": results}


def stats(con) -> dict[str, Any]:
    _, by_type = _rows_as_dicts(con.execute(
        "SELECT rdf_type, count(*) AS n FROM nodes GROUP BY 1 ORDER BY 2 DESC"))
    _, by_edge = _rows_as_dicts(con.execute(
        "SELECT type, count(*) AS n FROM edges GROUP BY 1 ORDER BY 2 DESC"))
    _, prov = _rows_as_dicts(con.execute(
        "SELECT COALESCE(provenance,'(none)') AS provenance, count(*) AS n "
        "FROM nodes GROUP BY 1 ORDER BY 2 DESC"))
    total_nodes = con.execute("SELECT count(*) FROM nodes").fetchone()[0]
    total_edges = con.execute("SELECT count(*) FROM edges").fetchone()[0]
    return {"total_nodes": total_nodes, "total_edges": total_edges,
            "nodes_by_type": {r["rdf_type"]: r["n"] for r in by_type},
            "edges_by_type": {r["type"]: r["n"] for r in by_edge},
            "provenance_breakdown": {r["provenance"]: r["n"] for r in prov}}


def main() -> int:
    parser = argparse.ArgumentParser(description="Business OAG Data Tool (read-only)")
    parser.add_argument("--object-set", help="Run a named Object Set query")
    parser.add_argument("--list-object-sets", action="store_true")
    parser.add_argument("--sql", help="Ad-hoc SELECT/WITH SQL query")
    parser.add_argument("--impact", help="Impact analysis for a biz node URI")
    parser.add_argument("--stats", action="store_true")
    parser.add_argument("--competency", action="store_true",
                        help="Run business competency questions (acceptance gate)")
    parser.add_argument("--agent", default=None, help="Calling agent URI (markings)")
    parser.add_argument("--output", choices=["json", "text"], default="json")
    args = parser.parse_args()

    if not NODES_PATH.exists():
        print("[ERROR] biz/nodes.jsonl not found. Run extract_business.py first.")
        return 2

    if args.list_object_sets:
        print(json.dumps(list_object_sets(), indent=2, ensure_ascii=False))
        return 0

    try:
        con = setup_duckdb()
    except ImportError:
        print("[ERROR] duckdb not installed. pip install duckdb", file=sys.stderr)
        return 2

    if args.stats:
        result = stats(con)
    elif args.competency:
        result = run_competency(con)
    elif args.object_set:
        result = run_object_set(con, args.object_set, args.agent)
    elif args.sql:
        result = run_sql(con, args.sql, args.agent)
    elif args.impact:
        result = impact_query(con, args.impact)
    else:
        parser.print_help()
        return 0

    print(json.dumps(result, indent=2, ensure_ascii=False, default=str))
    return 0 if "error" not in result else 1


if __name__ == "__main__":
    sys.exit(main())
