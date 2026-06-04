"""Neo Genesis Ontology v0.3 -- killswitch event -> ActionRun hook.

Called by quant-bot 9-Layer Kill Switch or any safety mechanism that halts
operations. Records ActionRun{kind:killswitch_fire, prov:Activity} with full
context for audit.

Wiring options:
1. PM2 process hook: ecosystem.config.js `on_exit` script
2. Killswitch dispatcher (HaltOrchestrator) direct invocation
3. CLI for manual triggers

Usage:
    python scripts/ontology/hooks/killswitch_hook.py \
        --layer L7 \
        --trigger "drawdown_exceeded" \
        --affected "neo://service/ysh-server/quant-bot-live" \
        --details '{"drawdown_pct": 12.5, "threshold_pct": 10.0}'
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

# Add parent to path for auto_record import
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_record import record_action  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--layer", required=True,
                        help="Killswitch layer (L1~L9)")
    parser.add_argument("--trigger", required=True,
                        help="Trigger reason: drawdown_exceeded / api_error / latency_spike / etc.")
    parser.add_argument("--affected", nargs="*", default=[],
                        help="Affected Service / Artifact URIs")
    parser.add_argument("--details", default="{}",
                        help="JSON dict of extra context")
    parser.add_argument("--agent-id", default="neo://agent/quant-bot-live")
    parser.add_argument("--result", default="success", choices=["success", "failure", "partial", "blocked"])
    args = parser.parse_args()

    try:
        details = json.loads(args.details)
    except json.JSONDecodeError as e:
        print(f"[ERROR] invalid --details JSON: {e}", file=sys.stderr)
        return 2

    meta = {
        "layer": args.layer,
        "trigger": args.trigger,
        "details": details,
    }

    result = record_action(
        kind="killswitch_fire",
        agent_id=args.agent_id,
        affected=args.affected,
        meta=meta,
        result=args.result,
        confidence=1.0,
        label=f"killswitch {args.layer}: {args.trigger}",
    )

    if result is None:
        print(json.dumps({"status": "duplicate", "skipped": True}))
    else:
        print(json.dumps({"status": "recorded", "action_run_id": result["id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
