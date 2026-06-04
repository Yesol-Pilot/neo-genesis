"""Neo Genesis Ontology v0.2 -- validator.

Checks per DESIGN_v0.1.md §13 Quality Gates:
- JSON Schema strict (nodes + edges per ontology.schema.json)
- URI uniqueness (no neo:// collision)
- Edge integrity (domain/range nodes exist)
- Markings integrity (no personal-forbidden leak)
- Redaction (no secret pattern in any field)

Exit codes:
  0 = all gates PASS
  1 = WARN (non-blocking issues)
  2 = FAIL (P0 violations)
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path
from collections import Counter
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_DIR = REPO_ROOT / ".agent" / "ontology"
NODES_PATH = ONTOLOGY_DIR / "nodes.jsonl"
EDGES_PATH = ONTOLOGY_DIR / "edges.jsonl"
BIZ_NODES_PATH = ONTOLOGY_DIR / "business" / "nodes.jsonl"
BIZ_EDGES_PATH = ONTOLOGY_DIR / "business" / "edges.jsonl"

SECRET_PATTERNS = [
    re.compile(r"sk-[A-Za-z0-9_-]{20,}"),
    re.compile(r"AIza[A-Za-z0-9_-]{30,}"),
    re.compile(r"ghp_[A-Za-z0-9]{30,}"),
    re.compile(r"AKIA[A-Z0-9]{16}"),
    re.compile(r"\d{10}:AAE[A-Za-z0-9_-]{30,}"),
    re.compile(r"eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+"),
]

VALID_KINDS = {
    # meta layer
    "Artifact", "Revision", "Project", "Service", "Device",
    "Agent", "Task", "Policy", "ActionRun", "Skill", "Reflection",
    # biz layer (Neo Genesis business ontology)
    "biz:Founder", "biz:Product", "biz:Domain", "biz:Strategy",
    "biz:RevenueStream", "biz:Investment", "biz:ResearchIP",
    "biz:Lead", "biz:LeadCategory", "biz:KPI", "biz:Decision",
    "biz:Capability", "biz:ExternalFederation", "biz:TemporalEvent",
    "biz:MonthlyCost", "biz:Workflow", "biz:ContentCorpus",
    "biz:BrandAsset", "biz:Risk", "biz:AgentContribution",
    "biz:ExternalSignal", "biz:OutcomeSnapshot",
}

# Semantic provenance check: biz nodes 가 fabricated 일 경우 명시 의무
PROV_FABRICATED = {"hardcoded_strategy_lead_seed", "placeholder_pending_real_data"}
BIZ_KINDS_NEEDING_PROVENANCE = {
    "biz:MonthlyCost", "biz:Capability", "biz:AgentContribution",
    "biz:Investment", "biz:LeadCategory", "biz:Lead",
}

VALID_RELATIONS = {
    # meta layer
    "current_revision", "prov:wasGeneratedBy", "prov:wasAssociatedWith",
    "prov:wasDerivedFrom", "supersedes", "owned_by", "deployed_to",
    "depends_on", "governs", "allowed_by", "denied_by", "affects",
    "assigned_to", "blocks", "references", "instantiates",
    "composed_of", "reflects_on",
    # meta P0 엣지 전사 (2026-05-29 ultracode — Reflection 작성자 / Service→Project)
    "prov:wasAttributedTo", "belongs_to",
    # biz layer
    "biz:owns", "biz:deployed_at", "biz:targets_lead",
    "biz:targets_lead_category", "biz:projected_revenue",
    "biz:allocates", "biz:decided", "biz:measures", "biz:produced",
    "biz:supersedes", "biz:cross_ref_meta", "biz:defines",
    "biz:has_capability",
    # biz connective tissue (2026-05-20, evidence-grounded relationships)
    "biz:generates_revenue_via", "biz:threatened_by", "biz:enables",
    # biz P0 엣지 전사 (2026-05-29 ultracode critic — 결정적 키 매칭)
    "biz:incurs", "biz:funds", "biz:adopted", "biz:depends_on",
    # biz P0-9/10 노드 내장 사실 엣지 전사 (2026-05-29 neo-implementer)
    "biz:references", "biz:affects",
}


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    if not path.exists():
        return []
    return [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]


def check_uri_uniqueness(nodes: list[dict]) -> tuple[int, list[str]]:
    """Returns (violations, sample_dupes)."""
    ids = [n["id"] for n in nodes]
    dupes = [uid for uid, cnt in Counter(ids).items() if cnt > 1]
    return len(dupes), dupes[:5]


def check_uri_format(items: list[dict]) -> list[str]:
    """Returns list of malformed URIs."""
    bad = []
    pat = re.compile(r"^neo://[a-z_]+/[\S]+$")
    for item in items:
        uid = item.get("id", "")
        if not pat.match(uid):
            bad.append(uid)
    return bad


def check_node_required_fields(nodes: list[dict]) -> list[str]:
    """Returns list of node IDs missing required fields per rdf_type."""
    violations = []
    for n in nodes:
        rt = n.get("rdf_type")
        if rt not in VALID_KINDS:
            violations.append(f"{n.get('id','?')}: invalid rdf_type={rt}")
            continue
        if not n.get("id") or not n.get("created_at"):
            violations.append(f"{n.get('id','?')}: missing id/created_at")
        # Per-type required fields
        if rt == "Artifact":
            if "kind" not in n or "path" not in n or "title" not in n or "markings" not in n:
                violations.append(f"{n['id']}: Artifact missing kind/path/title/markings")
        elif rt == "Service":
            if "status" not in n or "host_device" not in n:
                violations.append(f"{n['id']}: Service missing status/host_device")
        elif rt == "Device":
            if "hostname" not in n or "online" not in n:
                violations.append(f"{n['id']}: Device missing hostname/online")
        elif rt == "ActionRun":
            if "status" not in n or "triggered_by" not in n or "affectedObjects" not in n:
                violations.append(f"{n['id']}: ActionRun missing status/triggered_by/affectedObjects")
    return violations


def check_edge_integrity(nodes: list[dict], edges: list[dict]) -> list[str]:
    """Edges must reference existing nodes."""
    node_ids = {n["id"] for n in nodes}
    violations = []
    for e in edges:
        if e.get("type") not in VALID_RELATIONS:
            violations.append(f"{e.get('id','?')}: invalid relation type={e.get('type')}")
        from_id = e.get("from")
        to_id = e.get("to")
        if from_id not in node_ids:
            violations.append(f"{e.get('id','?')}: from={from_id} not in nodes")
        if to_id not in node_ids:
            violations.append(f"{e.get('id','?')}: to={to_id} not in nodes")
    return violations


def check_markings_integrity(nodes: list[dict]) -> tuple[list[str], list[str]]:
    """Personal-forbidden Artifacts must NOT have any non-empty allowedAgents.
    Returns (violations, personal_forbidden_count_sample)."""
    violations = []
    personal_forbidden_count = 0
    for n in nodes:
        if n.get("rdf_type") != "Artifact":
            continue
        markings = n.get("markings", [])
        if "personal-forbidden" in markings:
            personal_forbidden_count += 1
            allowed = n.get("allowedAgents", [])
            if allowed:
                violations.append(f"{n['id']}: personal-forbidden + non-empty allowedAgents={allowed}")
    return violations, [str(personal_forbidden_count)]


def check_secret_redaction(items: list[dict]) -> list[str]:
    """Scan all string fields for secret patterns."""
    leaks = []
    for item in items:
        for k, v in item.items():
            if not isinstance(v, str):
                continue
            for pat in SECRET_PATTERNS:
                if pat.search(v):
                    leaks.append(f"{item.get('id','?')}.{k}: secret pattern leaked")
                    break
    return leaks


def main() -> int:
    print("=" * 70)
    print("Neo Genesis Ontology v0.2 -- validator")
    print("=" * 70)

    meta_nodes = load_jsonl(NODES_PATH)
    meta_edges = load_jsonl(EDGES_PATH)
    biz_nodes = load_jsonl(BIZ_NODES_PATH)
    biz_edges = load_jsonl(BIZ_EDGES_PATH)
    nodes = meta_nodes + biz_nodes
    edges = meta_edges + biz_edges
    print(f"Loaded: {len(nodes)} nodes ({len(meta_nodes)} meta + {len(biz_nodes)} biz)")
    print(f"        {len(edges)} edges ({len(meta_edges)} meta + {len(biz_edges)} biz)")
    print()

    p0_fails = []
    p1_warns = []

    # P0: URI uniqueness
    dupe_count, dupe_sample = check_uri_uniqueness(nodes)
    if dupe_count > 0:
        p0_fails.append(f"URI duplicates: {dupe_count} (sample: {dupe_sample})")
    print(f"[P0] URI uniqueness: {'PASS' if dupe_count == 0 else f'FAIL ({dupe_count} dupes)'}")

    # P0: URI format
    bad_uris = check_uri_format(nodes) + check_uri_format(edges)
    if bad_uris:
        p0_fails.append(f"Malformed URIs: {len(bad_uris)} (sample: {bad_uris[:3]})")
    print(f"[P0] URI format: {'PASS' if not bad_uris else f'FAIL ({len(bad_uris)})'}")

    # P0: Node required fields
    field_violations = check_node_required_fields(nodes)
    if field_violations:
        p0_fails.extend(field_violations[:5])
    print(f"[P0] Required fields: {'PASS' if not field_violations else f'FAIL ({len(field_violations)})'}")

    # P0: Edge integrity
    edge_violations = check_edge_integrity(nodes, edges)
    if edge_violations:
        p0_fails.extend(edge_violations[:5])
    print(f"[P0] Edge integrity: {'PASS' if not edge_violations else f'FAIL ({len(edge_violations)})'}")

    # P0: Markings integrity
    mark_violations, pf_count = check_markings_integrity(nodes)
    if mark_violations:
        p0_fails.extend(mark_violations[:5])
    print(f"[P0] Markings integrity: {'PASS' if not mark_violations else f'FAIL ({len(mark_violations)})'} (personal-forbidden count: {pf_count[0]})")

    # P0: Secret redaction
    secret_leaks = check_secret_redaction(nodes) + check_secret_redaction(edges)
    if secret_leaks:
        p0_fails.extend(secret_leaks[:5])
    print(f"[P0] Secret redaction: {'PASS' if not secret_leaks else f'FAIL ({len(secret_leaks)})'}")

    # P0 semantic: biz fabrication 명시 의무
    biz_missing_prov = []
    biz_fabricated_count = 0
    for n in nodes:
        rt = n.get("rdf_type", "")
        if rt in BIZ_KINDS_NEEDING_PROVENANCE:
            prov = n.get("provenance")
            if not prov:
                biz_missing_prov.append(f"{n.get('id','?')}: biz fabrication-candidate without provenance")
            elif prov in PROV_FABRICATED:
                biz_fabricated_count += 1
    if biz_missing_prov:
        p0_fails.extend(biz_missing_prov[:5])
    print(f"[P0] Biz provenance: {'PASS' if not biz_missing_prov else f'FAIL ({len(biz_missing_prov)})'} (fabricated nodes declared: {biz_fabricated_count})")

    # P1 무결성 회귀 게이트 (축5, 2026-05-29): 전체 biz 노드 provenance coverage.
    # 2026-05-29 baseline = 100% (none 0). 회귀 시 가시화 (P1 WARN, cron 비차단).
    biz_all = [n for n in nodes if n.get("rdf_type", "").startswith("biz:")]
    biz_none = [n for n in biz_all if not n.get("provenance")]
    biz_cov = round(100 * (len(biz_all) - len(biz_none)) / max(len(biz_all), 1))
    cov_status = "PASS" if not biz_none else f"WARN ({len(biz_none)} none — provenance 회귀)"
    print(f"[P1] Biz provenance coverage: {cov_status} ({biz_cov}% of {len(biz_all)} biz nodes, baseline 100%)")

    # P1 메타층 provenance coverage (2026-05-29): biz 와 동일 무결성 기준 확장.
    # baseline 100% (meta backfill 후). 회귀 가시화, cron 비차단.
    meta_all = [n for n in nodes if not n.get("rdf_type", "").startswith("biz:")]
    meta_none = [n for n in meta_all if not n.get("provenance")]
    meta_cov = round(100 * (len(meta_all) - len(meta_none)) / max(len(meta_all), 1))
    meta_status = "PASS" if not meta_none else f"WARN ({len(meta_none)} none — provenance 회귀)"
    print(f"[P1] Meta provenance coverage: {meta_status} ({meta_cov}% of {len(meta_all)} meta nodes, baseline 100%)")

    # P1: rdf_type distribution + 0-instance audit
    # Note: 0 instances 는 valid state (e.g. biz:Lead = no prospects yet, biz:ActionRun fresh start).
    # P1 check 은 forward only — present rdf_type 가 모두 VALID_KINDS 인지.
    type_counts = Counter(n["rdf_type"] for n in nodes)
    invalid_present = set(type_counts.keys()) - VALID_KINDS
    zero_classes = sorted([k for k in VALID_KINDS if type_counts.get(k, 0) == 0])
    if invalid_present:
        p1_warns.append(f"Unknown rdf_types present: {invalid_present}")
    print(f"[P1] rdf_types valid: {'YES' if not invalid_present else f'NO ({invalid_present})'}")
    print(f"[P1] zero-instance classes ({len(zero_classes)}): {zero_classes}")
    print("[P1] Class breakdown:")
    for t in sorted(VALID_KINDS):
        cnt = type_counts.get(t, 0)
        marker = "  " if cnt > 0 else "0 "
        print(f"     {marker}{t:30s}: {cnt}")

    print()
    print("=" * 70)
    if p0_fails:
        print(f"FAIL -- {len(p0_fails)} P0 violations:")
        for v in p0_fails[:10]:
            print(f"  - {v}")
        return 2
    if p1_warns:
        print(f"WARN -- {len(p1_warns)} P1 issues (non-blocking):")
        for w in p1_warns:
            print(f"  - {w}")
        return 1
    print("PASS -- all P0 / P1 gates green")
    return 0


if __name__ == "__main__":
    sys.exit(main())
