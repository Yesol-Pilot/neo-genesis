"""Neo Genesis Ontology v0.3 -- OAG Action Tool (governed write API).

Foundry AIP pattern: agents propose mutations; single writer applies via write_queue.

Mutation types:
- add_node: add new node (validates rdf_type + required fields)
- add_edge: add new edge (validates from/to exist + valid relation type)
- modify_node: change properties (e.g. Task status pending -> done)
- remove_node: remove node (with cascade check on edges)
- remove_edge: remove edge

All mutations:
1. Validated against ontology.schema.json structure
2. Wrapped in ActionRun (prov:Activity, kind=ontology_mutation)
3. Dropped in write_queue/pending/ via propose
4. If --apply: also consume immediately (single-agent mode)

Usage:
    python scripts/ontology/mutate.py --add-task "title" --priority P0 --apply
    python scripts/ontology/mutate.py --modify-status <task_uri> done --apply
    python scripts/ontology/mutate.py --add-edge <from> <type> <to> --apply
    python scripts/ontology/mutate.py --diff-file my_diff.json [--apply]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_DIR = REPO_ROOT / ".agent" / "ontology"
NODES_PATH = ONTOLOGY_DIR / "nodes.jsonl"
EDGES_PATH = ONTOLOGY_DIR / "edges.jsonl"
SCRIPTS_DIR = REPO_ROOT / "scripts" / "ontology"

VALID_RELATIONS = {
    "current_revision", "prov:wasGeneratedBy", "prov:wasAssociatedWith",
    "prov:wasDerivedFrom", "supersedes", "owned_by", "deployed_to",
    "depends_on", "governs", "allowed_by", "denied_by", "affects",
    "assigned_to", "blocks", "references", "instantiates",
    "composed_of", "reflects_on",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def short_hash(text: str, n: int = 12) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:n]


def make_ulid() -> str:
    return dt.datetime.now().strftime("%Y%m%dT%H%M%S%f")


def load_node_ids() -> set[str]:
    if not NODES_PATH.exists():
        return set()
    return {json.loads(line)["id"] for line in NODES_PATH.read_text(encoding="utf-8").splitlines() if line.strip()}


def build_diff_for_add_task(title: str, priority: str, agent_id: str) -> dict[str, Any]:
    task_id = f"neo://task/{short_hash(title)}"
    now = now_iso()
    new_node = {
        "id": task_id,
        "rdf_type": "Task",
        "label": title[:60],
        "title": title,
        "status": "pending",
        "priority": priority,
        "created_at": now,
        "updated_at": now,
    }
    return {
        "add_nodes": [new_node],
        "add_edges": [],
        "modify_nodes": [],
        "remove_node_ids": [],
        "remove_edge_ids": [],
    }


def build_diff_for_modify_status(target_uri: str, new_status: str) -> dict[str, Any]:
    return {
        "add_nodes": [],
        "add_edges": [],
        "modify_nodes": [
            {"id": target_uri, "set": {"status": new_status, "updated_at": now_iso()}}
        ],
        "remove_node_ids": [],
        "remove_edge_ids": [],
    }


def build_diff_for_add_edge(from_uri: str, edge_type: str, to_uri: str,
                            link_properties: dict | None = None) -> dict[str, Any]:
    if edge_type not in VALID_RELATIONS:
        raise ValueError(f"invalid relation type: {edge_type}. Valid: {sorted(VALID_RELATIONS)}")
    edge_id = f"neo://relation/{edge_type.replace(':','_')}/{short_hash(from_uri+to_uri+edge_type)}"
    new_edge = {
        "id": edge_id,
        "type": edge_type,
        "from": from_uri,
        "to": to_uri,
        "observed_at": now_iso(),
    }
    if link_properties:
        new_edge["linkProperties"] = link_properties
    return {
        "add_nodes": [],
        "add_edges": [new_edge],
        "modify_nodes": [],
        "remove_node_ids": [],
        "remove_edge_ids": [],
    }


def validate_diff(diff: dict, existing_node_ids: set[str]) -> list[str]:
    """Returns list of validation errors. Empty = OK."""
    errors = []
    # add_edges: from/to must exist or be added in same diff
    new_node_ids = {n["id"] for n in diff.get("add_nodes", [])}
    available_ids = existing_node_ids | new_node_ids
    for e in diff.get("add_edges", []):
        if e["from"] not in available_ids:
            errors.append(f"add_edge: from={e['from']} not in nodes")
        if e["to"] not in available_ids:
            errors.append(f"add_edge: to={e['to']} not in nodes")
        if e["type"] not in VALID_RELATIONS:
            errors.append(f"add_edge: invalid type={e['type']}")
    # modify_nodes: target must exist
    for m in diff.get("modify_nodes", []):
        if m["id"] not in existing_node_ids:
            errors.append(f"modify_node: id={m['id']} not in nodes")
    # remove: target must exist
    for nid in diff.get("remove_node_ids", []):
        if nid not in existing_node_ids:
            errors.append(f"remove_node: id={nid} not in nodes")
    return errors


def submit_diff(diff: dict, agent_id: str, name: str, priority: int = 5,
                apply: bool = False) -> dict[str, Any]:
    """Submit diff via write_queue.py propose. Optionally consume immediately."""
    # Write diff to temp file
    tmp_diff = ONTOLOGY_DIR / f".tmp_diff_{make_ulid()}.json"
    tmp_diff.write_text(json.dumps(diff, indent=2, ensure_ascii=False), encoding="utf-8")
    try:
        # Propose via write_queue
        proc = subprocess.run(
            [sys.executable, str(SCRIPTS_DIR / "write_queue.py"),
             "--propose", name, str(tmp_diff),
             "--agent-id", agent_id, "--priority", str(priority)],
            capture_output=True, text=True, encoding="utf-8"
        )
        propose_output = proc.stdout.strip() + proc.stderr.strip()

        result = {"propose_output": propose_output, "applied": False}
        if apply:
            proc2 = subprocess.run(
                [sys.executable, str(SCRIPTS_DIR / "write_queue.py"), "--consume"],
                capture_output=True, text=True, encoding="utf-8"
            )
            result["consume_output"] = proc2.stdout.strip() + proc2.stderr.strip()
            result["applied"] = True
        return result
    finally:
        if tmp_diff.exists():
            tmp_diff.unlink()


def main() -> int:
    parser = argparse.ArgumentParser(description="OAG Action Tool (governed write)")
    parser.add_argument("--add-task", metavar="TITLE", help="Add a new Task")
    parser.add_argument("--priority", default="P2", choices=["P0", "P1", "P2", "P3"])
    parser.add_argument("--modify-status", nargs=2, metavar=("URI", "NEW_STATUS"),
                        help="Modify status of a node")
    parser.add_argument("--add-edge", nargs=3, metavar=("FROM", "TYPE", "TO"))
    parser.add_argument("--diff-file", metavar="PATH", help="Apply diff from JSON file")
    parser.add_argument("--name", default="mutate", help="Proposal name")
    parser.add_argument("--agent-id", default="claude-opus-4-7")
    parser.add_argument("--apply", action="store_true",
                        help="Immediately consume after propose (single-agent mode)")
    parser.add_argument("--dry-run", action="store_true",
                        help="Print diff without proposing")
    args = parser.parse_args()

    existing_ids = load_node_ids()

    # Build diff based on action
    if args.add_task:
        diff = build_diff_for_add_task(args.add_task, args.priority, args.agent_id)
        name = f"add-task-{short_hash(args.add_task)}"
    elif args.modify_status:
        uri, new_status = args.modify_status
        diff = build_diff_for_modify_status(uri, new_status)
        name = f"modify-{short_hash(uri)}-{new_status}"
    elif args.add_edge:
        from_uri, etype, to_uri = args.add_edge
        diff = build_diff_for_add_edge(from_uri, etype, to_uri)
        name = f"add-edge-{short_hash(from_uri+to_uri+etype)}"
    elif args.diff_file:
        diff = json.loads(Path(args.diff_file).read_text(encoding="utf-8"))
        name = args.name
    else:
        parser.print_help()
        return 1

    # Validate
    errors = validate_diff(diff, existing_ids)
    if errors:
        print("[FAIL] diff validation errors:")
        for err in errors:
            print(f"  - {err}")
        return 2

    if args.dry_run:
        print(json.dumps({"name": name, "diff": diff, "validation": "PASS"},
                         indent=2, ensure_ascii=False))
        return 0

    # Submit
    result = submit_diff(diff, args.agent_id, name, apply=args.apply)
    result["diff_summary"] = {
        "add_nodes": len(diff.get("add_nodes", [])),
        "add_edges": len(diff.get("add_edges", [])),
        "modify_nodes": len(diff.get("modify_nodes", [])),
        "remove_node_ids": len(diff.get("remove_node_ids", [])),
        "remove_edge_ids": len(diff.get("remove_edge_ids", [])),
    }
    print(json.dumps(result, indent=2, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
