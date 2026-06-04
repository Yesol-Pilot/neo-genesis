"""Neo Genesis Ontology v0.3 -- deploy event -> ActionRun hook.

Called by Vercel / PM2 / GitHub Actions / manual deploy scripts when a deploy
completes (or fails). Records ActionRun{kind:deploy, prov:Activity} +
references the affected Service.

Wiring options:
1. Vercel webhook → API endpoint → this script
2. GitHub Actions: `python scripts/ontology/hooks/deploy_hook.py --target ...` after deploy step
3. PM2 `ecosystem.config.js`: `on_start` hook
4. Manual CLI invocation post-deploy

Usage:
    python scripts/ontology/hooks/deploy_hook.py \
        --service neo://service/vercel-edge/kott-frontend \
        --commit 634a90e \
        --version v1.2.3 \
        --result success \
        --duration-sec 47
"""
from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from auto_record import record_action  # type: ignore


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--service", required=True,
                        help="Service URI being deployed (neo://service/...)")
    parser.add_argument("--commit", required=True,
                        help="git commit SHA")
    parser.add_argument("--version", default=None,
                        help="Semver / tag (optional)")
    parser.add_argument("--result", default="success",
                        choices=["success", "failure", "partial", "blocked"])
    parser.add_argument("--duration-sec", type=int, default=None)
    parser.add_argument("--platform", default="vercel",
                        choices=["vercel", "pm2", "github_actions", "manual", "cloudflare"])
    parser.add_argument("--agent-id", default="neo://agent/claude-opus-4-7",
                        help="Agent or human URI triggering the deploy")
    parser.add_argument("--rollback-of", default=None,
                        help="If this is a rollback, URI of previous deploy ActionRun")
    args = parser.parse_args()

    meta = {
        "commit": args.commit,
        "version": args.version,
        "platform": args.platform,
        "duration_sec": args.duration_sec,
    }
    if args.rollback_of:
        meta["rollback_of"] = args.rollback_of

    result = record_action(
        kind="deploy",
        agent_id=args.agent_id,
        affected=[args.service],
        meta=meta,
        result=args.result,
        confidence=1.0,
        label=f"deploy {args.service.split('/')[-1]} {args.commit[:7]} ({args.platform})",
    )

    if result is None:
        print(json.dumps({"status": "duplicate", "skipped": True}))
    else:
        print(json.dumps({"status": "recorded", "action_run_id": result["id"]}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
