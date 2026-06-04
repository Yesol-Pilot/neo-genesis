"""Apply cypher_schema.cql to Neo4j via Python driver.

Replaces cypher-shell dependency (AuraDB has no shell access; only Bolt protocol).
Splits the .cql file on semicolons + line-end and runs each statement separately.

Usage:
    export NEO4J_BOLT_URI=neo4j+s://...
    export NEO4J_USER=neo4j
    export NEO4J_PASSWORD=...
    python scripts/ontology/apply_neo4j_schema.py
"""
from __future__ import annotations

import os
import re
import sys
from pathlib import Path

try:
    from neo4j import GraphDatabase
except ImportError:
    print("[ERROR] pip install neo4j")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_PATH = REPO_ROOT / ".agent" / "ontology" / "neo4j" / "cypher_schema.cql"


def split_statements(cql_text: str) -> list[str]:
    """Split .cql by semicolons; strip comments + blank lines."""
    # Strip // comments
    lines = []
    for line in cql_text.splitlines():
        stripped = line.split("//", 1)[0].rstrip()
        if stripped:
            lines.append(stripped)
    joined = "\n".join(lines)
    # Split on semicolons (terminator)
    parts = re.split(r";\s*\n", joined)
    statements = [p.strip().rstrip(";").strip() for p in parts]
    return [s for s in statements if s]


def main() -> int:
    bolt = os.environ.get("NEO4J_BOLT_URI") or os.environ.get("NEO4J_URI")
    user = os.environ.get("NEO4J_USER") or os.environ.get("NEO4J_USERNAME") or "neo4j"
    password = os.environ.get("NEO4J_PASSWORD")
    if not bolt or not password:
        print("[ERROR] NEO4J_BOLT_URI + NEO4J_PASSWORD required")
        return 2

    if not SCHEMA_PATH.exists():
        print(f"[ERROR] schema not found: {SCHEMA_PATH}")
        return 2

    cql = SCHEMA_PATH.read_text(encoding="utf-8")
    statements = split_statements(cql)
    print(f"Loaded {len(statements)} statements from {SCHEMA_PATH.name}")

    driver = GraphDatabase.driver(bolt, auth=(user, password))
    try:
        driver.verify_connectivity()
        print(f"[OK] connected to {bolt}")
        applied = 0
        skipped = 0
        with driver.session() as session:
            for i, stmt in enumerate(statements, 1):
                # n10s/apoc procedure calls — skip in AuraDB Free (no plugins)
                if "n10s." in stmt or "apoc." in stmt:
                    print(f"  [{i}] SKIP (plugin proc): {stmt[:60]}...")
                    skipped += 1
                    continue
                # Existence constraint — Enterprise only
                if "IS NOT NULL" in stmt.upper() and "REQUIRE" in stmt.upper():
                    print(f"  [{i}] SKIP (Enterprise only): {stmt[:60]}...")
                    skipped += 1
                    continue
                try:
                    session.run(stmt).consume()
                    applied += 1
                    print(f"  [{i}] OK: {stmt[:80]}...")
                except Exception as e:
                    err = str(e).split("\n")[0]
                    print(f"  [{i}] FAIL: {err[:120]}")

        # Verify constraints
        with driver.session() as session:
            constraints = list(session.run("SHOW CONSTRAINTS"))
            indexes = list(session.run("SHOW INDEXES"))
        print(f"\n[VERIFY] {len(constraints)} constraints, {len(indexes)} indexes")
        print(f"Applied: {applied} / Skipped: {skipped} / Total: {len(statements)}")
        return 0
    finally:
        driver.close()


if __name__ == "__main__":
    sys.exit(main())
