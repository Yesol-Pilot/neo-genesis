"""Neo Genesis -- Decision Outcome Timeline.

Outcome 은 snapshot 이 아니라 시계열. 매일 측정 → biz:OutcomeSnapshot 박제 →
시간 흐름 따라 status change 추적.

가설:
- 어떤 G1 박제가 며칠간 validated 였다가 failed 가 됐는가
- 어떤 결정이 안정적인가 / 불안정한가
- 새 결정이 outcome 도달까지 며칠 걸리는가

Schema:
biz:OutcomeSnapshot {
    id: neo://biz/outcome_snapshot/<g_id>/<date>
    decision_id, g_id, snapshot_date, status,
    checks_pass, checks_total, evidence
}

Usage:
    python scripts/ontology/business/outcome_timeline.py [--dry-run]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import sys
from pathlib import Path
from collections import defaultdict, Counter

REPO_ROOT = Path(__file__).resolve().parents[3]
BIZ_DIR = REPO_ROOT / ".agent" / "ontology" / "business"
NODES_PATH = BIZ_DIR / "nodes.jsonl"
TIMELINE_LOG_PATH = BIZ_DIR / "outcome_timeline.json"


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


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    nodes = load_jsonl(NODES_PATH)
    decisions = [n for n in nodes if n.get("rdf_type") == "biz:Decision"]
    today_iso = dt.date.today().isoformat()

    # Build new snapshots for today
    new_snapshots = []
    for d in decisions:
        g_id = d.get("g_id")
        status = d.get("outcome_status")
        if not g_id or not status:
            continue
        snap_id = f"neo://biz/outcome_snapshot/{g_id}/{today_iso}"
        new_snapshots.append({
            "id": snap_id,
            "rdf_type": "biz:OutcomeSnapshot",
            "label": f"{g_id} snapshot {today_iso}",
            "decision_id": d["id"],
            "g_id": g_id,
            "snapshot_date": today_iso,
            "status": status,
            "checks_pass": d.get("outcome_checks_pass"),
            "checks_total": d.get("outcome_checks_total"),
            "evidence": d.get("outcome_evidence", "")[:200],
            "markings": ["internal"],
            "provenance": "observed_from_live_source",
            "provenance_source": "decision_outcome_tracker daily snapshot",
            "created_at": now_iso(),
            "updated_at": now_iso(),
        })

    # Load existing snapshots
    existing_snapshots = [n for n in nodes if n.get("rdf_type") == "biz:OutcomeSnapshot"]
    today_existing_ids = {n["id"] for n in existing_snapshots if n.get("snapshot_date") == today_iso}

    # Append only new (idempotent: today's snapshot 이미 있으면 갱신)
    by_id = {n["id"]: n for n in nodes}
    added = 0
    updated = 0
    for snap in new_snapshots:
        if snap["id"] in by_id:
            # update only if status differs
            old = by_id[snap["id"]]
            if old.get("status") != snap.get("status"):
                by_id[snap["id"]] = snap
                updated += 1
        else:
            by_id[snap["id"]] = snap
            added += 1

    # Build timeline analysis (status change detection)
    all_snapshots = [n for n in by_id.values() if n.get("rdf_type") == "biz:OutcomeSnapshot"]
    by_decision: dict[str, list[dict]] = defaultdict(list)
    for s in all_snapshots:
        by_decision[s["g_id"]].append(s)

    status_changes = []
    for g_id, snaps in by_decision.items():
        snaps.sort(key=lambda s: s["snapshot_date"])
        for i in range(1, len(snaps)):
            if snaps[i]["status"] != snaps[i-1]["status"]:
                status_changes.append({
                    "g_id": g_id,
                    "from_date": snaps[i-1]["snapshot_date"],
                    "to_date": snaps[i]["snapshot_date"],
                    "from_status": snaps[i-1]["status"],
                    "to_status": snaps[i]["status"],
                })

    # Stability score per decision = (days_with_same_status) / (total_days)
    stability = {}
    today_d = dt.date.today()
    for g_id, snaps in by_decision.items():
        if not snaps:
            continue
        snaps.sort(key=lambda s: s["snapshot_date"])
        first = dt.date.fromisoformat(snaps[0]["snapshot_date"])
        span_days = (today_d - first).days + 1
        latest_status = snaps[-1]["status"]
        same_status_days = sum(1 for s in snaps if s["status"] == latest_status)
        stability[g_id] = {
            "current_status": latest_status,
            "snapshots": len(snaps),
            "span_days": span_days,
            "same_status_count": same_status_days,
            "is_stable": same_status_days == len(snaps),
        }

    summary = {
        "audited_at": now_iso(),
        "snapshot_date": today_iso,
        "decisions_snapshot": len(new_snapshots),
        "added_today": added,
        "updated_today": updated,
        "total_snapshots_in_ontology": len(all_snapshots),
        "decisions_tracked": len(by_decision),
        "status_changes_detected": len(status_changes),
        "recent_status_changes": status_changes[-5:] if status_changes else [],
        "stability_overview": dict(Counter(
            "stable" if v["is_stable"] else "unstable"
            for v in stability.values()
        )),
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

    # Persist
    TIMELINE_LOG_PATH.write_text(
        json.dumps({"summary": summary, "stability": stability,
                    "status_changes": status_changes}, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )

    if not args.dry_run:
        final = list(by_id.values())
        write_jsonl(NODES_PATH, final)
        print(f"[OK] outcome timeline persisted: {len(all_snapshots)} total snapshots → {NODES_PATH}", file=sys.stderr)

    return 0


if __name__ == "__main__":
    sys.exit(main())
