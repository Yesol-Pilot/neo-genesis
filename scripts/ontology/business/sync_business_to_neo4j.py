"""Sync Neo Genesis Business Ontology v0.1 → AuraDB.

Sister to scripts/ontology/migrate_to_neo4j.py but reads from
.agent/ontology/business/ (separate dir for biz layer).

Labels are prefixed with `Biz` to distinguish from meta (e.g. `biz:Founder` →
Neo4j label `BizFounder`). Cross-links to meta (e.g. biz:Product → meta Project)
become Cypher relationships between Biz<Class> and meta <Class>.

Usage:
    export NEO4J_BOLT_URI=...
    export NEO4J_USER=neo4j
    export NEO4J_PASSWORD=...
    python scripts/ontology/business/sync_business_to_neo4j.py --import-nodes --import-edges --verify
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BIZ_DIR = REPO_ROOT / ".agent" / "ontology" / "business"
NODES_PATH = BIZ_DIR / "nodes.jsonl"
EDGES_PATH = BIZ_DIR / "edges.jsonl"

DEFAULT_BOLT_URI = "bolt://localhost:7687"
DEFAULT_USER = "neo4j"


def sanitize_label(rdf_type: str) -> str:
    """biz:Founder → BizFounder (Cypher 호환)"""
    return re.sub(r"[^A-Za-z0-9]", "", rdf_type.replace("biz:", "Biz_").replace("_", ""))


def sanitize_rel(rel_type: str) -> str:
    """biz:owns → BIZ_OWNS"""
    return re.sub(r"[^A-Z0-9_]", "", rel_type.replace(":", "_").upper())


def get_driver():
    try:
        from neo4j import GraphDatabase
    except ImportError:
        print("[ERROR] pip install neo4j")
        sys.exit(2)
    bolt = os.environ.get("NEO4J_BOLT_URI") or os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER") or "neo4j"
    pw = os.environ.get("NEO4J_PASSWORD")
    if not bolt or not pw:
        print("[ERROR] NEO4J_BOLT_URI + NEO4J_PASSWORD required")
        sys.exit(2)
    return GraphDatabase.driver(bolt, auth=(user, pw))


def load_jsonl(p: Path) -> list[dict]:
    if not p.exists():
        return []
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def flatten(item: dict) -> dict:
    """Neo4j primitive 한계 회피."""
    out = {}
    for k, v in item.items():
        if v is None:
            continue
        if isinstance(v, dict):
            out[k] = json.dumps(v, ensure_ascii=False)
        elif isinstance(v, list):
            if v and isinstance(v[0], (dict, list)):
                out[k] = json.dumps(v, ensure_ascii=False)
            else:
                out[k] = v
        else:
            out[k] = v
    return out


def import_nodes(driver) -> dict:
    nodes = load_jsonl(NODES_PATH)
    by_type: dict[str, list[dict]] = {}
    for n in nodes:
        by_type.setdefault(n["rdf_type"], []).append(n)
    stats = {}
    with driver.session() as s:
        for rdf_type, items in by_type.items():
            label = sanitize_label(rdf_type)
            batch = [flatten(n) for n in items]
            cypher = (
                f"UNWIND $batch AS row "
                f"MERGE (n:{label} {{id: row.id}}) "
                f"SET n += row, n.rdf_type = row.rdf_type"
            )
            r = s.run(cypher, batch=batch)
            stats[rdf_type] = r.consume().counters.nodes_created
    return stats


def import_edges(driver) -> dict:
    edges = load_jsonl(EDGES_PATH)
    by_type: dict[str, list[dict]] = {}
    for e in edges:
        by_type.setdefault(e["type"], []).append(e)
    stats = {}
    with driver.session() as s:
        for original_type, items in by_type.items():
            cypher_type = sanitize_rel(original_type)
            batch = []
            for e in items:
                flat = {
                    "id": e["id"],
                    "original_type": e["type"],
                    "from_id": e["from"],
                    "to_id": e["to"],
                    "observed_at": e.get("observed_at"),
                }
                lp = e.get("linkProperties")
                if lp is not None:
                    flat["linkProperties"] = json.dumps(lp, ensure_ascii=False) if isinstance(lp, (dict, list)) else lp
                batch.append(flat)
            cypher = (
                f"UNWIND $batch AS row "
                f"MATCH (a {{id: row.from_id}}), (b {{id: row.to_id}}) "
                f"MERGE (a)-[r:{cypher_type} {{id: row.id}}]->(b) "
                f"SET r += {{original_type: row.original_type, observed_at: row.observed_at, linkProperties: row.linkProperties}}"
            )
            r = s.run(cypher, batch=batch)
            stats[original_type] = r.consume().counters.relationships_created
    return stats


def verify(driver) -> dict:
    nodes = load_jsonl(NODES_PATH)
    edges = load_jsonl(EDGES_PATH)
    with driver.session() as s:
        biz_nodes = s.run("MATCH (n) WHERE n.rdf_type STARTS WITH 'biz:' RETURN count(n) AS c").single()["c"]
        biz_edges = s.run("MATCH ()-[r]->() WHERE r.original_type STARTS WITH 'biz:' RETURN count(r) AS c").single()["c"]
        by_label = {}
        for row in s.run("MATCH (n) WHERE n.rdf_type STARTS WITH 'biz:' RETURN n.rdf_type AS t, count(n) AS c ORDER BY c DESC"):
            by_label[row["t"]] = row["c"]
        cross_links = s.run(
            "MATCH (b)-[r {original_type: 'biz:cross_ref_meta'}]->(m) RETURN count(r) AS c"
        ).single()["c"]
    return {
        "jsonl_biz_nodes": len(nodes),
        "neo4j_biz_nodes": biz_nodes,
        "node_parity": len(nodes) == biz_nodes,
        "jsonl_biz_edges": len(edges),
        "neo4j_biz_edges": biz_edges,
        "edge_parity": len(edges) == biz_edges,
        "biz_node_breakdown": by_label,
        "cross_links_to_meta": cross_links,
    }


def main() -> int:
    p = argparse.ArgumentParser()
    p.add_argument("--import-nodes", action="store_true")
    p.add_argument("--import-edges", action="store_true")
    p.add_argument("--verify", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    args = p.parse_args()

    if args.dry_run:
        nodes = load_jsonl(NODES_PATH)
        edges = load_jsonl(EDGES_PATH)
        print(json.dumps({
            "dry_run": True,
            "biz_nodes": len(nodes),
            "biz_edges": len(edges),
            "node_classes": sorted({n["rdf_type"] for n in nodes}),
            "edge_types": sorted({e["type"] for e in edges}),
        }, indent=2, ensure_ascii=False))
        return 0

    driver = get_driver()
    try:
        result = {}
        if args.import_nodes:
            result["nodes"] = import_nodes(driver)
        if args.import_edges:
            result["edges"] = import_edges(driver)
        if args.verify:
            result["verification"] = verify(driver)
        print(json.dumps(result, indent=2, ensure_ascii=False))
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
