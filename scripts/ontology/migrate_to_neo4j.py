"""Neo Genesis Ontology v0.4 -- DuckDB/JSONL -> Neo4j migrator.

Imports nodes.jsonl + edges.jsonl into Neo4j Community Edition via Bolt
protocol. Per G1-8 (Store paradigm) + DESIGN §14 (v0.4 Neo4j 이전).

This is the *one-shot* migration — after this, write path bifurcates:
- Authoritative: nodes.jsonl + edges.jsonl (dual-write, file primary)
- Query: Neo4j (Cypher) for RAG + multi-hop + Foundry-style queries

Usage:
    # 1. docker compose up -d (in .agent/ontology/neo4j/)
    # 2. apply schema: docker exec -i neo-genesis-neo4j cypher-shell -u neo4j -p $PW < cypher_schema.cql
    # 3. import:
    python scripts/ontology/migrate_to_neo4j.py --import-nodes --import-edges
    # 4. verify:
    python scripts/ontology/migrate_to_neo4j.py --verify
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_DIR = REPO_ROOT / ".agent" / "ontology"
NODES_PATH = ONTOLOGY_DIR / "nodes.jsonl"
EDGES_PATH = ONTOLOGY_DIR / "edges.jsonl"

DEFAULT_BOLT_URI = "bolt://localhost:7687"
DEFAULT_USER = "neo4j"


def get_driver():
    """Lazy import — neo4j driver only loaded when actually needed."""
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("[ERROR] neo4j driver not installed. Run: pip install neo4j")
        sys.exit(2)
    bolt = os.environ.get("NEO4J_BOLT_URI", DEFAULT_BOLT_URI)
    user = os.environ.get("NEO4J_USER", DEFAULT_USER)
    password = os.environ.get("NEO4J_PASSWORD")
    if not password:
        print("[ERROR] NEO4J_PASSWORD env var required.")
        sys.exit(2)
    return GraphDatabase.driver(bolt, auth=(user, password))


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def flatten_for_neo4j(item: dict) -> dict:
    """Neo4j only accepts primitive properties or arrays of primitives.
    Convert nested dicts and arrays-of-dicts to JSON strings.
    Preserves arrays of strings/numbers as-is.
    """
    out = {}
    for k, v in item.items():
        if v is None:
            continue
        if isinstance(v, dict):
            out[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, list):
            # Array of primitives = OK; array of dicts = JSON string
            if v and isinstance(v[0], (dict, list)):
                out[k] = json.dumps(v, ensure_ascii=False)
            else:
                out[k] = v
        else:
            out[k] = v
    return out


def import_nodes(driver, batch_size: int = 500) -> dict[str, int]:
    """Import all nodes from nodes.jsonl into Neo4j.

    Each node becomes a Cypher node with primary label = rdf_type and id property.
    Other properties become Cypher node properties.
    """
    nodes = load_jsonl(NODES_PATH)
    by_type: dict[str, list[dict]] = {}
    for n in nodes:
        by_type.setdefault(n.get("rdf_type", "Unknown"), []).append(n)

    stats: dict[str, int] = {}
    with driver.session() as session:
        for rdf_type, items in by_type.items():
            count = 0
            for i in range(0, len(items), batch_size):
                batch = [flatten_for_neo4j(n) for n in items[i:i+batch_size]]
                # UNWIND batch + MERGE on id; SET all other props
                cypher = (
                    f"UNWIND $batch AS row "
                    f"MERGE (n:{rdf_type} {{id: row.id}}) "
                    f"SET n += row"
                )
                result = session.run(cypher, batch=batch)
                count += result.consume().counters.nodes_created
            stats[rdf_type] = count
    return stats


def import_edges(driver, batch_size: int = 500) -> dict[str, int]:
    """Import all edges from edges.jsonl into Neo4j.

    Each edge becomes a Cypher relationship. Relationship type = sanitized edge.type
    (Neo4j relationship type must be uppercase + underscore, no colons).
    Original type stored as `original_type` property for round-trip.
    """
    edges = load_jsonl(EDGES_PATH)
    by_type: dict[str, list[dict]] = {}
    for e in edges:
        by_type.setdefault(e["type"], []).append(e)

    stats: dict[str, int] = {}
    with driver.session() as session:
        for original_type, items in by_type.items():
            # Sanitize for Cypher: prov:wasGeneratedBy -> PROV_WAS_GENERATED_BY
            cypher_type = original_type.replace(":", "_").replace("-", "_").upper()
            count = 0
            for i in range(0, len(items), batch_size):
                # Flatten linkProperties from dict to JSON string
                batch = []
                for e in items[i:i+batch_size]:
                    flat = {
                        "id": e["id"],
                        "type": e["type"],
                        "from": e["from"],
                        "to": e["to"],
                        "observed_at": e.get("observed_at"),
                    }
                    lp = e.get("linkProperties")
                    if lp is not None:
                        flat["linkProperties"] = json.dumps(lp, ensure_ascii=False) if isinstance(lp, (dict, list)) else lp
                    batch.append(flat)
                cypher = (
                    f"UNWIND $batch AS row "
                    f"MATCH (a {{id: row.`from`}}), (b {{id: row.to}}) "
                    f"MERGE (a)-[r:{cypher_type} {{id: row.id}}]->(b) "
                    f"SET r.original_type = row.type, "
                    f"    r.observed_at = row.observed_at, "
                    f"    r.linkProperties = row.linkProperties"
                )
                result = session.run(cypher, batch=batch)
                count += result.consume().counters.relationships_created
            stats[original_type] = count
    return stats


def verify(driver) -> dict[str, Any]:
    """Compare DuckDB/JSONL counts vs Neo4j counts (parity check)."""
    jsonl_nodes = len(load_jsonl(NODES_PATH))
    jsonl_edges = len(load_jsonl(EDGES_PATH))

    with driver.session() as session:
        node_count = session.run("MATCH (n) RETURN count(n) AS c").single()["c"]
        edge_count = session.run("MATCH ()-[r]->() RETURN count(r) AS c").single()["c"]
        # Per-class breakdown
        class_breakdown = {}
        for row in session.run("MATCH (n) RETURN labels(n) AS labels, count(n) AS cnt ORDER BY cnt DESC"):
            label_list = row["labels"]
            primary = label_list[0] if label_list else "?"
            class_breakdown[primary] = row["cnt"]

    return {
        "jsonl_nodes": jsonl_nodes,
        "neo4j_nodes": node_count,
        "node_parity": jsonl_nodes == node_count,
        "jsonl_edges": jsonl_edges,
        "neo4j_edges": edge_count,
        "edge_parity": jsonl_edges == edge_count,
        "neo4j_class_breakdown": class_breakdown,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--import-nodes", action="store_true")
    parser.add_argument("--import-edges", action="store_true")
    parser.add_argument("--verify", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="Don't connect to Neo4j; just count JSONL")
    args = parser.parse_args()

    if args.dry_run:
        nodes = load_jsonl(NODES_PATH)
        edges = load_jsonl(EDGES_PATH)
        print(json.dumps({
            "dry_run": True,
            "would_import_nodes": len(nodes),
            "would_import_edges": len(edges),
            "node_classes": list({n.get("rdf_type") for n in nodes}),
            "edge_types": list({e.get("type") for e in edges}),
        }, indent=2, ensure_ascii=False))
        return 0

    driver = get_driver()
    try:
        result = {}
        if args.import_nodes:
            result["nodes_imported"] = import_nodes(driver)
        if args.import_edges:
            result["edges_imported"] = import_edges(driver)
        if args.verify:
            result["verification"] = verify(driver)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
