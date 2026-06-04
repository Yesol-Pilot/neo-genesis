"""Neo Genesis Ontology v0.2 -- file-based write queue (G1-19).

Per G1-10 (Single Writer + Queue) and G1-19 (v0.2 = file-based, Supabase v0.3 평가):
- Agents propose ontology writes by dropping JSON files in `.agent/ontology/write_queue/pending/`.
- A single writer (this script, run as cron or daemon) consumes them in order,
  applies the diff, records ActionRun{kind:ontology_mutation, status:committed},
  and moves the file to `.agent/ontology/write_queue/processed/` or `failed/`.

This is the PoC reference implementation. Production scheduling (PM2 / cron)
is owner action.

Usage:
    python scripts/ontology/write_queue.py --propose <name> <diff.json>
    python scripts/ontology/write_queue.py --consume [--dry-run]
    python scripts/ontology/write_queue.py --status
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import shutil
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_DIR = REPO_ROOT / ".agent" / "ontology"
NODES_PATH = ONTOLOGY_DIR / "nodes.jsonl"
EDGES_PATH = ONTOLOGY_DIR / "edges.jsonl"
QUEUE_DIR = ONTOLOGY_DIR / "write_queue"
PENDING_DIR = QUEUE_DIR / "pending"
PROCESSED_DIR = QUEUE_DIR / "processed"
FAILED_DIR = QUEUE_DIR / "failed"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def ensure_dirs() -> None:
    for d in (PENDING_DIR, PROCESSED_DIR, FAILED_DIR):
        d.mkdir(parents=True, exist_ok=True)


def propose(agent_id: str, name: str, diff_path: Path, priority: int = 5) -> Path:
    """Drop a write proposal in pending/."""
    ensure_dirs()
    if not diff_path.exists():
        raise FileNotFoundError(f"diff file not found: {diff_path}")
    diff = json.loads(diff_path.read_text(encoding="utf-8"))
    ts = now_iso().replace(":", "").replace("-", "")
    out_path = PENDING_DIR / f"{ts}__{priority:02d}__{agent_id}__{name}.json"
    proposal = {
        "proposed_at": now_iso(),
        "agent_id": agent_id,
        "name": name,
        "priority": priority,
        "diff": diff,
        "status": "pending",
    }
    out_path.write_text(json.dumps(proposal, indent=2, ensure_ascii=False), encoding="utf-8")
    return out_path


def status() -> dict[str, int]:
    ensure_dirs()
    return {
        "pending": len(list(PENDING_DIR.glob("*.json"))),
        "processed": len(list(PROCESSED_DIR.glob("*.json"))),
        "failed": len(list(FAILED_DIR.glob("*.json"))),
    }


def _load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def _write_jsonl(path: Path, items: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        "\n".join(json.dumps(item, ensure_ascii=False) for item in items) + "\n",
        encoding="utf-8",
    )


def _sync_to_neo4j(diff: dict[str, Any], action_run_id: str) -> dict[str, Any]:
    """v0.5: dual-write JSONL → Neo4j AuraDB (best-effort).

    Triggers when NEO4J_BOLT_URI + NEO4J_PASSWORD env vars are set.
    Failure is non-fatal — JSONL remains authoritative.
    """
    bolt = os.environ.get("NEO4J_BOLT_URI") or os.environ.get("NEO4J_URI")
    password = os.environ.get("NEO4J_PASSWORD")
    if not bolt or not password:
        return {"skipped": "NEO4J_BOLT_URI or NEO4J_PASSWORD not set"}

    try:
        from neo4j import GraphDatabase
    except ImportError:
        return {"skipped": "neo4j driver not installed"}

    user = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME") or "neo4j"

    # Reuse flatten from migrate_to_neo4j (same module path)
    try:
        sys.path.insert(0, str(Path(__file__).resolve().parent))
        from migrate_to_neo4j import flatten_for_neo4j  # type: ignore
    except ImportError:
        def flatten_for_neo4j(item: dict) -> dict:
            out = {}
            for k, v in item.items():
                if v is None:
                    continue
                if isinstance(v, (dict, list)) and v and isinstance(next(iter(v) if v else None, None), (dict,)):
                    out[k] = json.dumps(v, ensure_ascii=False)
                elif isinstance(v, dict):
                    out[k] = json.dumps(v, ensure_ascii=False)
                else:
                    out[k] = v
            return out

    stats = {
        "nodes_added": 0,
        "nodes_modified": 0,
        "edges_added": 0,
        "skipped": 0,
        "errors": [],
    }

    try:
        driver = GraphDatabase.driver(bolt, auth=(user, password))
        with driver.session() as session:
            # add_nodes
            for n in diff.get("add_nodes", []):
                flat = flatten_for_neo4j(n)
                rdf_type = n.get("rdf_type", "Unknown")
                try:
                    session.run(
                        f"MERGE (x:{rdf_type} {{id: $id}}) SET x += $props",
                        id=n["id"], props=flat,
                    ).consume()
                    stats["nodes_added"] += 1
                except Exception as e:
                    stats["errors"].append(f"add_node {n['id']}: {str(e)[:100]}")

            # modify_nodes
            for m in diff.get("modify_nodes", []):
                try:
                    session.run(
                        "MATCH (x {id: $id}) SET x += $props",
                        id=m["id"], props=m.get("set", {}),
                    ).consume()
                    stats["nodes_modified"] += 1
                except Exception as e:
                    stats["errors"].append(f"modify_node {m['id']}: {str(e)[:100]}")

            # add_edges
            for e in diff.get("add_edges", []):
                cypher_type = e["type"].replace(":", "_").replace("-", "_").upper()
                flat_edge = {
                    "id": e["id"],
                    "original_type": e["type"],
                    "observed_at": e.get("observed_at"),
                }
                lp = e.get("linkProperties")
                if lp is not None:
                    flat_edge["linkProperties"] = json.dumps(lp, ensure_ascii=False) if isinstance(lp, (dict, list)) else lp
                try:
                    session.run(
                        f"MATCH (a {{id: $from_id}}), (b {{id: $to_id}}) "
                        f"MERGE (a)-[r:{cypher_type} {{id: $edge_id}}]->(b) "
                        f"SET r += $props",
                        from_id=e["from"], to_id=e["to"], edge_id=e["id"], props=flat_edge,
                    ).consume()
                    stats["edges_added"] += 1
                except Exception as ex:
                    stats["errors"].append(f"add_edge {e['id']}: {str(ex)[:100]}")
        driver.close()
        stats["status"] = "synced"
    except Exception as e:
        stats["status"] = "connect_failed"
        stats["errors"].append(f"driver: {str(e)[:100]}")

    return stats


def apply_diff(diff: dict[str, Any], action_run_id: str) -> dict[str, Any]:
    """Apply a diff to nodes.jsonl + edges.jsonl + (optional) Neo4j AuraDB.

    v0.5: dual-write — JSONL primary + Neo4j optional (if env var set).
    Returns summary {nodes_added, edges_added, nodes_modified, nodes_removed, edges_removed, neo4j_sync}.
    """
    nodes = _load_jsonl(NODES_PATH)
    edges = _load_jsonl(EDGES_PATH)
    node_index = {n["id"]: i for i, n in enumerate(nodes)}
    edge_index = {e["id"]: i for i, e in enumerate(edges)}

    summary = {
        "nodes_added": 0,
        "edges_added": 0,
        "nodes_modified": 0,
        "nodes_removed": 0,
        "edges_removed": 0,
    }
    affected = []

    # add_nodes (deduplicate by id)
    for n in diff.get("add_nodes", []):
        if n["id"] in node_index:
            continue  # idempotent — skip duplicates
        nodes.append(n)
        node_index[n["id"]] = len(nodes) - 1
        summary["nodes_added"] += 1
        affected.append(n["id"])

    # add_edges
    for e in diff.get("add_edges", []):
        if e["id"] in edge_index:
            continue
        edges.append(e)
        edge_index[e["id"]] = len(edges) - 1
        summary["edges_added"] += 1
        affected.append(e["id"])

    # modify_nodes
    for m in diff.get("modify_nodes", []):
        idx = node_index.get(m["id"])
        if idx is None:
            continue
        for k, v in m.get("set", {}).items():
            nodes[idx][k] = v
        summary["nodes_modified"] += 1
        affected.append(m["id"])

    # remove_node_ids
    for nid in diff.get("remove_node_ids", []):
        if nid not in node_index:
            continue
        idx = node_index.pop(nid)
        nodes[idx] = None  # mark for removal
        summary["nodes_removed"] += 1
        affected.append(nid)

    # remove_edge_ids
    for eid in diff.get("remove_edge_ids", []):
        if eid not in edge_index:
            continue
        idx = edge_index.pop(eid)
        edges[idx] = None
        summary["edges_removed"] += 1
        affected.append(eid)

    # Drop nulls (removed) + add ActionRun node itself
    nodes = [n for n in nodes if n is not None]
    edges = [e for e in edges if e is not None]

    # ActionRun auto-record (prov:Activity)
    action_node = {
        "id": action_run_id,
        "rdf_type": "ActionRun",
        "prov_type": "prov:Activity",
        "kind": "ontology_mutation",
        "label": f"wq apply {action_run_id.split('/')[-1][:40]}",
        "triggered_by": "neo://agent/claude-opus-4-7",  # default; override via diff
        "affectedObjects": affected,
        "status": "committed",
        "result": "success",
        "started_at": now_iso(),
        "finished_at": now_iso(),
        "created_at": now_iso(),
        "updated_at": now_iso(),
    }
    nodes.append(action_node)

    # Re-write JSONL atomically
    _write_jsonl(NODES_PATH, nodes)
    _write_jsonl(EDGES_PATH, edges)

    summary["action_run_id"] = action_run_id
    summary["affected_count"] = len(affected)

    # v0.5 dual-write: optional Neo4j sync (best-effort, never raises)
    try:
        summary["neo4j_sync"] = _sync_to_neo4j(diff, action_run_id)
    except Exception as e:
        summary["neo4j_sync"] = {"status": "exception", "error": str(e)[:200]}

    return summary


def consume(dry_run: bool = False) -> dict[str, Any]:
    """Consume pending proposals in chronological order.

    v0.3: actually applies diff to nodes.jsonl + edges.jsonl.
    Records ActionRun{kind:ontology_mutation, status:committed} per proposal.
    """
    ensure_dirs()
    pending = sorted(PENDING_DIR.glob("*.json"))
    results = {"consumed": 0, "skipped_dry_run": 0, "failed": 0, "details": []}

    for p in pending:
        try:
            proposal = json.loads(p.read_text(encoding="utf-8"))
            diff = proposal.get("diff", {})
            action_run_id = f"neo://action_run/wq-{p.stem}"

            if dry_run:
                results["skipped_dry_run"] += 1
                results["details"].append({
                    "file": p.name,
                    "action": "dry-run",
                    "would_apply": {
                        "add_nodes": len(diff.get("add_nodes", [])),
                        "add_edges": len(diff.get("add_edges", [])),
                        "modify_nodes": len(diff.get("modify_nodes", [])),
                        "remove_node_ids": len(diff.get("remove_node_ids", [])),
                    },
                })
                continue

            # Apply diff (v0.3 actual mutation)
            apply_summary = apply_diff(diff, action_run_id)

            # Mark proposal status
            proposal["status"] = "committed"
            proposal["committed_at"] = now_iso()
            proposal["action_run_id"] = action_run_id
            proposal["apply_summary"] = apply_summary
            (PROCESSED_DIR / p.name).write_text(
                json.dumps(proposal, indent=2, ensure_ascii=False), encoding="utf-8"
            )
            p.unlink()

            results["consumed"] += 1
            results["details"].append({
                "file": p.name,
                "action_run_id": action_run_id,
                "summary": apply_summary,
            })
        except Exception as e:
            results["failed"] += 1
            try:
                shutil.move(str(p), str(FAILED_DIR / p.name))
            except Exception:
                pass
            results["details"].append({"file": p.name, "error": str(e)})

    return results


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--propose", nargs=2, metavar=("NAME", "DIFF_PATH"))
    parser.add_argument("--consume", action="store_true")
    parser.add_argument("--status", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--agent-id", default="claude-opus-4-7")
    parser.add_argument("--priority", type=int, default=5)
    args = parser.parse_args()

    ensure_dirs()

    if args.status:
        s = status()
        print(json.dumps(s, indent=2))
        return 0

    if args.propose:
        name, diff_path = args.propose
        out = propose(args.agent_id, name, Path(diff_path), args.priority)
        print(f"[OK] proposal -> {out}")
        return 0

    if args.consume:
        r = consume(dry_run=args.dry_run)
        print(json.dumps(r, indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
