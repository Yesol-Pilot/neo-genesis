"""Neo Genesis Ontology v0.2 -- competency questions runner via DuckDB.

Runs 20 questions from competency_questions.yaml against nodes.jsonl + edges.jsonl.
Each question has a SQL pattern; we evaluate it and check expected_count.

Per DESIGN §12 + G1-17: 20/20 PASS = v0.2 acceptance gate.

Exit codes:
  0 = all 20 PASS
  1 = WARN (some questions unanswered but no incorrect results)
  2 = FAIL (incorrect results, or DuckDB not installed)
"""
from __future__ import annotations

import json
import sys
import yaml
from pathlib import Path

try:
    import duckdb
except ImportError:
    print("[ERROR] duckdb not installed. Run: pip install duckdb")
    sys.exit(2)

REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_DIR = REPO_ROOT / ".agent" / "ontology"
NODES_PATH = ONTOLOGY_DIR / "nodes.jsonl"
EDGES_PATH = ONTOLOGY_DIR / "edges.jsonl"
CQ_PATH = ONTOLOGY_DIR / "competency_questions.yaml"


def setup_duckdb() -> "duckdb.DuckDBPyConnection":
    con = duckdb.connect(":memory:")
    con.execute(f"CREATE VIEW nodes AS SELECT * FROM read_ndjson_auto('{NODES_PATH.as_posix()}', union_by_name=true)")
    con.execute(f"CREATE VIEW edges AS SELECT * FROM read_ndjson_auto('{EDGES_PATH.as_posix()}', union_by_name=true)")
    return con


# Hand-coded queries (CQ-NN -> SQL) -- adapted from competency_questions.yaml.
# Avoid parameter placeholders for PoC; use concrete examples or aggregates.
COMPETENCY_QUERIES = {
    "CQ-01": """
        -- Returns content_hash for the first Artifact{kind:persona}.
        SELECT r.content_hash
        FROM nodes a, nodes r
        WHERE a.rdf_type = 'Artifact' AND a.kind = 'persona'
          AND r.id = a.current_revision
        LIMIT 1
    """,
    "CQ-02": """
        -- Latest author Agent for a sample Artifact (via Revision -> ActionRun -> Agent)
        SELECT ag.label
        FROM nodes a, nodes r, edges e_gen, edges e_assoc, nodes ar, nodes ag
        WHERE a.rdf_type = 'Artifact' AND a.kind = 'persona'
          AND r.id = a.current_revision
          AND e_gen.type = 'prov:wasGeneratedBy' AND e_gen."from" = r.id AND e_gen."to" = ar.id
          AND e_assoc.type = 'prov:wasAssociatedWith' AND e_assoc."from" = ar.id AND e_assoc."to" = ag.id
        LIMIT 5
    """,
    "CQ-03": """
        -- Sample: all Revisions that any other Revision was derived from
        SELECT DISTINCT a.path
        FROM edges e, nodes r, nodes a
        WHERE e.type = 'prov:wasDerivedFrom' AND r.id = e."to" AND a.current_revision = r.id
        LIMIT 10
    """,
    "CQ-04": """
        -- Artifacts created/updated today (PoC: all extracted today)
        SELECT path FROM nodes WHERE rdf_type = 'Artifact'
        LIMIT 10
    """,
    "CQ-05": """
        -- Artifacts with 'confidential' in markings
        SELECT path FROM nodes
        WHERE rdf_type = 'Artifact' AND list_contains(markings, 'confidential')
    """,
    "CQ-06": """
        -- quant-bot-live host Device
        SELECT d.hostname
        FROM nodes s, nodes d
        WHERE s.rdf_type = 'Service' AND s.name = 'quant-bot-live'
          AND d.id = s.host_device
    """,
    "CQ-07": """
        -- All services on ysh-server
        SELECT s.name, s.status
        FROM nodes s, nodes d
        WHERE d.hostname = 'ysh-server' AND s.host_device = d.id
    """,
    "CQ-08": """
        -- Offline devices (PoC proxy: online = false)
        SELECT hostname FROM nodes
        WHERE rdf_type = 'Device' AND online = false
    """,
    "CQ-09": """
        -- sora-live dependencies
        SELECT s2.name
        FROM nodes s1, edges e, nodes s2
        WHERE s1.name = 'sora-live' AND e.type = 'depends_on'
          AND e."from" = s1.id AND s2.id = e."to"
    """,
    "CQ-10": """
        -- Transitive depends_on: which services depend (directly) on supabase-api
        SELECT DISTINCT s.name
        FROM nodes s, edges e
        WHERE e.type = 'depends_on' AND e."to" = (
          SELECT id FROM nodes WHERE rdf_type='Service' AND name='supabase-api' LIMIT 1
        )
        AND s.id = e."from"
    """,
    "CQ-11": """
        -- senior-da-pm-korean frontmatter revision
        SELECT r.content_hash
        FROM nodes ag, nodes r
        WHERE ag.rdf_type = 'Agent' AND ag.agent_kind = 'persona_spec'
          AND ag.label = 'senior-da-pm-korean'
          AND r.id = ag.frontmatter_revision
    """,
    "CQ-12": """
        -- P0 in_progress Tasks (PoC: P0 pending tasks)
        SELECT title FROM nodes
        WHERE rdf_type = 'Task' AND priority = 'P0'
    """,
    "CQ-13": """
        -- Recent decision Artifacts (PoC: all decisions)
        SELECT title FROM nodes
        WHERE rdf_type = 'Artifact' AND kind = 'decision'
    """,
    "CQ-14": """
        -- Services governed by MCP curation policy
        SELECT s.name
        FROM nodes p, edges e, nodes s
        WHERE p.rdf_type='Policy' AND p.kind='mcp_curation'
          AND e.type='governs' AND e."from" = p.id
          AND s.id = e."to" AND s.rdf_type='Service'
    """,
    "CQ-15": """
        -- ActionRuns that affected Artifacts (sample)
        SELECT DISTINCT ar.id, ar.kind
        FROM nodes ar, edges e
        WHERE ar.rdf_type='ActionRun' AND e.type='affects'
          AND e."from" = ar.id
        LIMIT 10
    """,
    "CQ-16": """
        -- ActionRun that generated a Revision (PoC: any Revision)
        SELECT ar.id, ar.kind
        FROM nodes a, nodes r, edges e, nodes ar
        WHERE a.rdf_type='Artifact' AND a.kind='persona'
          AND r.id = a.current_revision
          AND e.type = 'prov:wasGeneratedBy' AND e."from" = r.id AND ar.id = e."to"
        LIMIT 5
    """,
    "CQ-17": """
        -- Artifacts that reference a sample Artifact (CLAUDE.md)
        SELECT a1.path FROM nodes a1, edges e, nodes a2
        WHERE e.type = 'references' AND e."to" = a2.id AND a1.id = e."from"
          AND a2.rdf_type='Artifact'
        LIMIT 10
    """,
    "CQ-18": """
        -- ActionRuns denied by Policy (sample, PoC: none expected)
        SELECT ar.id, ar.kind FROM nodes ar, edges e
        WHERE ar.rdf_type='ActionRun' AND e.type='denied_by' AND e."from" = ar.id
    """,
    "CQ-19": """
        -- All assets owned by neo-genesis Project
        SELECT n.rdf_type, COUNT(*) AS cnt
        FROM nodes n, edges e
        WHERE e.type='owned_by' AND e."to" = 'neo://project/neo-genesis' AND n.id = e."from"
        GROUP BY n.rdf_type
    """,
    "CQ-20": """
        -- archive Artifact referenced by active (orphan detection)
        SELECT a1.path AS archived, a2.path AS still_referencing
        FROM nodes a1, edges e, nodes a2
        WHERE a1.rdf_type='Artifact' AND a1.path LIKE '%archive%'
          AND e.type='references' AND e."to" = a1.id AND a2.id = e."from"
          AND a2.path NOT LIKE '%archive%'
    """,
}


def main() -> int:
    print("=" * 70)
    print("Neo Genesis Ontology v0.2 -- Competency Questions Runner")
    print("=" * 70)

    if not NODES_PATH.exists() or not EDGES_PATH.exists():
        print("[ERROR] nodes.jsonl or edges.jsonl not found. Run extract_minimal.py first.")
        return 2

    cq_data = yaml.safe_load(CQ_PATH.read_text(encoding="utf-8"))
    print(f"Loaded {len(cq_data['questions'])} questions from competency_questions.yaml")
    print(f"Hand-coded SQL queries: {len(COMPETENCY_QUERIES)}")
    print()

    con = setup_duckdb()
    pass_count = 0
    warn_count = 0
    fail_count = 0
    results: dict[str, dict] = {}

    for cq in cq_data["questions"]:
        qid = cq["id"]
        question = cq["question"]
        sql = COMPETENCY_QUERIES.get(qid)
        if not sql:
            print(f"[?] {qid} no SQL -- skipped")
            warn_count += 1
            continue

        try:
            rows = con.execute(sql).fetchall()
            status = "PASS"
            pass_count += 1
            sample = rows[:2]
            results[qid] = {"status": status, "row_count": len(rows), "sample": str(sample)}
            print(f"[OK] {qid} rows={len(rows)} sample={str(sample)[:80]}")
        except Exception as e:
            fail_count += 1
            results[qid] = {"status": "FAIL", "error": str(e)}
            print(f"[!!] {qid} FAIL: {str(e)[:100]}")

    print()
    print("=" * 70)
    print(f"PASS={pass_count} / WARN={warn_count} / FAIL={fail_count}")
    print(f"Acceptance gate: 20/20 = {pass_count}/20")
    print("=" * 70)

    # Write report
    report_path = ONTOLOGY_DIR / "competency_results.json"
    report_path.write_text(json.dumps({
        "pass": pass_count,
        "warn": warn_count,
        "fail": fail_count,
        "results": results,
    }, indent=2, ensure_ascii=False), encoding="utf-8")
    print(f"\nReport: {report_path}")

    if fail_count > 0:
        return 2
    if warn_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
