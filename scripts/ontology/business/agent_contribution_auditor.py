"""Neo Genesis -- Real Agent Contribution Auditor.

cold evaluation 정정: biz:AgentContribution 13건이 모두 hardcoded estimate.
본 스크립트는 meta layer 의 ActionRun audit log 를 분석해서 실 측정된
contribution 노드 (provenance=observed_from_live_source) 박제.

Source:
- meta ActionRun nodes (kind: dispatcher_route, ontology_mutation, extract, deploy, etc.)
- triggered_by → Agent
- affectedObjects → biz Product (via cross-link or path heuristics)

각 (agent, product) pair 마다:
- audit_action_count: ActionRun 발생 횟수
- last_active_at: 최근 ActionRun timestamp
- audit_action_ids: 참조한 ActionRun URI 리스트 (최근 5)
- evidence: 자동 생성 narrative

Replaces (not augments) 직전 hardcoded contributions.

Usage:
    python scripts/ontology/business/agent_contribution_auditor.py [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import sys
from collections import defaultdict, Counter
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
BIZ_DIR = REPO_ROOT / ".agent" / "ontology" / "business"
META_DIR = REPO_ROOT / ".agent" / "ontology"
NODES_PATH = BIZ_DIR / "nodes.jsonl"
META_NODES_PATH = META_DIR / "nodes.jsonl"


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def load_jsonl(path: Path) -> list[dict]:
    if not path.exists():
        return []
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


def write_jsonl(path: Path, items: list[dict]) -> None:
    seen: dict[str, dict] = {}
    for item in items:
        nid = item.get("id")
        if nid:
            seen[nid] = item
    with path.open("w", encoding="utf-8") as f:
        for item in seen.values():
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


def map_affected_to_product(uri: str, biz_products: dict[str, dict]) -> str | None:
    """Heuristic: affectedObject URI → biz:Product slug.

    Mapping rules:
    - neo://project/<slug> → biz:Product slug match
    - neo://service/<host>/<name> → product if name in product slug
    - neo://artifact/<sha> → check path for SBU directory
    """
    if not uri:
        return None
    # Direct project match
    if uri.startswith("neo://project/"):
        slug = uri.split("/")[-1]
        if slug in biz_products:
            return f"neo://biz/product/{slug}"
    # Service URI: check name segment
    if uri.startswith("neo://service/"):
        parts = uri.split("/")
        if len(parts) >= 5:
            svc_name = parts[-1].lower()
            for slug in biz_products:
                if slug in svc_name:
                    return f"neo://biz/product/{slug}"
    return None


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--lookback-days", type=int, default=30)
    args = parser.parse_args()

    meta_nodes = load_jsonl(META_NODES_PATH)
    biz_nodes = load_jsonl(NODES_PATH)

    # Build biz product index
    biz_products = {
        n.get("slug"): n for n in biz_nodes
        if n.get("rdf_type") == "biz:Product" and n.get("slug")
    }

    # Extract ActionRun events
    cutoff = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(days=args.lookback_days)).isoformat()
    action_runs = [n for n in meta_nodes if n.get("rdf_type") == "ActionRun"]
    recent_actions = [a for a in action_runs if a.get("started_at", "1900") >= cutoff]

    # Aggregate by (agent, product)
    by_pair: dict[tuple[str, str], dict] = defaultdict(lambda: {
        "action_count": 0,
        "kinds": Counter(),
        "last_active_at": "",
        "action_ids": [],
    })
    agent_total_actions: Counter[str] = Counter()

    for a in recent_actions:
        agent_uri = a.get("triggered_by")
        if not agent_uri:
            continue
        agent_total_actions[agent_uri] += 1
        affected = a.get("affectedObjects", []) or []
        for tgt in affected:
            product_uri = map_affected_to_product(tgt, biz_products)
            if not product_uri:
                continue
            key = (agent_uri, product_uri)
            agg = by_pair[key]
            agg["action_count"] += 1
            agg["kinds"][a.get("kind", "?")] += 1
            t = a.get("started_at", "")
            if t > agg["last_active_at"]:
                agg["last_active_at"] = t
            if a["id"] not in agg["action_ids"] and len(agg["action_ids"]) < 5:
                agg["action_ids"].append(a["id"])

    # Build new contribution nodes
    new_contribs: list[dict] = []
    for (agent_uri, product_uri), agg in by_pair.items():
        agent_slug = agent_uri.split("/")[-1]
        product_slug = product_uri.split("/")[-1]
        # Intensity = action_count percentile
        if agg["action_count"] >= 10:
            intensity = "high"
        elif agg["action_count"] >= 3:
            intensity = "medium"
        else:
            intensity = "low"
        # Role inference
        kinds_top = agg["kinds"].most_common(2)
        role_hint = kinds_top[0][0] if kinds_top else "unknown"
        role_map = {
            "dispatcher_route": "agent_orchestration",
            "ontology_mutation": "ontology_keeper",
            "extract": "data_extractor",
            "deploy": "deployer",
            "killswitch_fire": "safety_responder",
            "heartbeat": "audit_recorder",
        }
        role = role_map.get(role_hint, role_hint)

        new_contribs.append({
            "id": f"neo://biz/contribution/{agent_slug}-{product_slug}",
            "rdf_type": "biz:AgentContribution",
            "label": f"{agent_slug} → {product_slug} (audited)",
            "agent": agent_uri,
            "product": product_uri,
            "role": role,
            "intensity": intensity,
            "audit_action_count": agg["action_count"],
            "audit_action_kinds": dict(agg["kinds"]),
            "audit_action_ids": agg["action_ids"],
            "last_active_at": agg["last_active_at"],
            "lookback_days": args.lookback_days,
            "evidence_note": f"{agg['action_count']} ActionRun events in last {args.lookback_days}d (kinds: {dict(agg['kinds'])})",
            "markings": ["internal"],
            "provenance": "observed_from_live_source",
            "provenance_source": f"meta ActionRun audit (lookback={args.lookback_days}d)",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })

    # Agent-only summary (when no product mapping)
    for agent_uri, total in agent_total_actions.most_common():
        agent_slug = agent_uri.split("/")[-1]
        new_contribs.append({
            "id": f"neo://biz/contribution/_summary-{agent_slug}",
            "rdf_type": "biz:AgentContribution",
            "label": f"{agent_slug} TOTAL audit ({total} actions)",
            "agent": agent_uri,
            "product": None,
            "role": "aggregate_total",
            "intensity": "high" if total >= 10 else ("medium" if total >= 3 else "low"),
            "audit_action_count": total,
            "evidence_note": f"All ActionRun audit: {total} actions in last {args.lookback_days}d",
            "markings": ["internal"],
            "provenance": "observed_from_live_source",
            "provenance_source": "meta ActionRun audit (agent-aggregate, all products)",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })

    # Drop existing biz:AgentContribution + replace with observed ones
    kept = [n for n in biz_nodes if n.get("rdf_type") != "biz:AgentContribution"]
    final = kept + new_contribs

    summary = {
        "audited_at": now_iso(),
        "lookback_days": args.lookback_days,
        "action_runs_total": len(action_runs),
        "action_runs_in_window": len(recent_actions),
        "agent_total_actions": dict(agent_total_actions),
        "pair_count": len(by_pair),
        "contribution_nodes_after": len([n for n in final if n.get("rdf_type") == "biz:AgentContribution"]),
        "biz_nodes_total_before": len(biz_nodes),
        "biz_nodes_total_after": len(final),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

    if args.dry_run:
        print("[dry-run] not writing")
        return 0

    write_jsonl(NODES_PATH, final)
    print(f"[OK] {len(new_contribs)} AgentContribution nodes (observed) → {NODES_PATH}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    sys.exit(main())
