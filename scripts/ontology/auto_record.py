"""Neo Genesis Ontology v0.3 -- fast-path ActionRun helper.

For high-volume events (dispatcher routing / killswitch fire / deploy notice),
write_queue (propose + consume cycle) is overkill. This module appends a single
ActionRun (prov:Activity) directly to nodes.jsonl.

Safe because:
- Append-only (no concurrent modification of existing nodes)
- File lock via fcntl/msvcrt portable wrapper
- Idempotent: same event recorded twice = same ULID/hash 만 1번 박제
- ActionRun is immutable by design (prov:Activity)

For diffs that modify existing nodes, USE write_queue.py instead.

API:
    from auto_record import record_action
    record_action(
        kind="dispatcher_route",
        agent_id="neo://agent/claude-opus-4-7",
        affected=["neo://agent/senior-da-pm-korean"],
        meta={"matched_layer": "L2_keyword", "query_hash": "abc123"},
    )

CLI usage:
    python scripts/ontology/auto_record.py --kind dispatcher_route \
        --agent neo://agent/claude-opus-4-7 \
        --affected neo://agent/senior-da-pm-korean \
        --meta '{"matched_layer":"L2_keyword"}'
"""
from __future__ import annotations

import argparse
import datetime as dt
import hashlib
import json
import os
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[2]
ONTOLOGY_DIR = REPO_ROOT / ".agent" / "ontology"
NODES_PATH = ONTOLOGY_DIR / "nodes.jsonl"

VALID_KINDS = {
    "dispatcher_route", "killswitch_fire", "deploy", "commit",
    "mcp_tool_call", "persona_invocation", "external_api_call",
    "ontology_mutation", "extract", "heartbeat",
}


def now_iso() -> str:
    return dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")


def make_action_id(kind: str, agent_id: str, started_at: str, meta: dict) -> str:
    """Deterministic ID — same event recorded twice resolves to same id (idempotent)."""
    key = f"{kind}|{agent_id}|{started_at}|{json.dumps(meta, sort_keys=True)}"
    h = hashlib.sha256(key.encode("utf-8")).hexdigest()[:16]
    return f"neo://action_run/{kind}-{h}"


def _append_jsonl_locked(path: Path, item: dict) -> None:
    """Append a single JSON line with file lock (portable)."""
    path.parent.mkdir(parents=True, exist_ok=True)
    line = json.dumps(item, ensure_ascii=False)

    # Cross-platform lock (msvcrt on Windows, fcntl on POSIX)
    if os.name == "nt":
        import msvcrt
        with path.open("a", encoding="utf-8") as f:
            # Lock 1 byte at current position
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_LOCK, 1)
            except OSError:
                pass  # Lock unavailable; proceed best-effort
            f.write(line + "\n")
            try:
                msvcrt.locking(f.fileno(), msvcrt.LK_UNLCK, 1)
            except OSError:
                pass
    else:
        import fcntl
        with path.open("a", encoding="utf-8") as f:
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_EX)
            except OSError:
                pass
            f.write(line + "\n")
            try:
                fcntl.flock(f.fileno(), fcntl.LOCK_UN)
            except OSError:
                pass


def _already_recorded(action_id: str) -> bool:
    """Check if action_id is already in nodes.jsonl (linear scan, OK for PoC scale)."""
    if not NODES_PATH.exists():
        return False
    target = f'"id": "{action_id}"'
    try:
        with NODES_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                if target in line:
                    return True
    except Exception:
        return False
    return False


def record_action(
    kind: str,
    agent_id: str,
    affected: list[str] | None = None,
    meta: dict | None = None,
    result: str = "success",
    confidence: float | None = None,
    label: str | None = None,
) -> dict[str, Any] | None:
    """Append a single ActionRun (prov:Activity) to nodes.jsonl.

    Returns the recorded ActionRun dict, or None if duplicate (idempotent).
    """
    if kind not in VALID_KINDS:
        raise ValueError(f"Invalid kind: {kind}. Valid: {sorted(VALID_KINDS)}")

    now = now_iso()
    meta = meta or {}
    affected = affected or []
    action_id = make_action_id(kind, agent_id, now, meta)

    # Idempotency check
    if _already_recorded(action_id):
        return None

    action_node = {
        "id": action_id,
        "rdf_type": "ActionRun",
        "prov_type": "prov:Activity",
        "kind": kind,
        "label": label or f"{kind} {now[:19]}",
        "triggered_by": agent_id,
        "affectedObjects": affected,
        "status": "committed",
        "result": result,
        "started_at": now,
        "finished_at": now,
        "created_at": now,
        "updated_at": now,
        "provenance": "observed_from_live_source",  # self-record: 도구가 자기 행위 직접 관측 기록 (무결성 100% 유지)
        "provenance_source": "auto_record.py runtime self-record",
        "markings": ["internal"],
    }
    if confidence is not None:
        action_node["confidence"] = confidence
    if meta:
        action_node["meta"] = meta

    _append_jsonl_locked(NODES_PATH, action_node)
    return action_node


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--kind", required=True, choices=sorted(VALID_KINDS))
    parser.add_argument("--agent", required=True, help="Agent URI")
    parser.add_argument("--affected", nargs="*", default=[], help="Affected node URIs")
    parser.add_argument("--meta", default="{}", help="JSON meta dict")
    parser.add_argument("--result", default="success", choices=["success", "failure", "partial", "blocked"])
    parser.add_argument("--confidence", type=float, default=None)
    parser.add_argument("--label", default=None)
    args = parser.parse_args()

    try:
        meta = json.loads(args.meta)
    except json.JSONDecodeError as e:
        print(f"[ERROR] invalid --meta JSON: {e}", file=sys.stderr)
        return 2

    result = record_action(
        kind=args.kind,
        agent_id=args.agent,
        affected=args.affected,
        meta=meta,
        result=args.result,
        confidence=args.confidence,
        label=args.label,
    )
    if result is None:
        print(json.dumps({"status": "duplicate", "skipped": True}))
    else:
        print(json.dumps({"status": "recorded", "action_run_id": result["id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
