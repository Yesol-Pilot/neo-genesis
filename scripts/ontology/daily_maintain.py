"""Neo Genesis Ontology -- daily maintenance orchestrator.

매일 09:00 KST 자동 실행 (scheduled-tasks MCP cron 박제).

수행 작업 (순서):
1. extract_minimal.py — .agent/ 변경사항 재추출 (nodes.jsonl + edges.jsonl 갱신)
2. validate.py — 6 P0 gate 통과 확인 (FAIL 시 stderr 알람)
3. validate_competency.py — 20/20 PASS 회귀 확인
4. graphrag.py --rebuild — community detection 재계산
5. vector_index.py --rebuild — KURE 또는 TF-IDF 자동 선택
6. migrate_to_neo4j.py --verify — AuraDB parity 확인 + 3-day auto-pause heartbeat
7. auto_record.py — ActionRun{kind:heartbeat} 박제 (cron 실행 audit trail)

Exit codes:
- 0: 모두 PASS
- 1: WARN (1+ task skipped or partial fail)
- 2: FAIL (any P0 gate failed)

Usage:
    python scripts/ontology/daily_maintain.py [--dry-run] [--skip-neo4j]
"""
from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPTS_DIR = REPO_ROOT / "scripts" / "ontology"


def run_step(name: str, cmd: list[str], allow_fail: bool = False, env_extra: dict | None = None) -> dict:
    """Run a subscript, capture result."""
    started = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    env = os.environ.copy()
    if env_extra:
        env.update(env_extra)
    env["PYTHONIOENCODING"] = "utf-8"

    try:
        proc = subprocess.run(
            [sys.executable] + cmd,
            capture_output=True,
            text=True,
            encoding="utf-8",
            cwd=str(REPO_ROOT),
            timeout=300,
            env=env,
        )
        return {
            "step": name,
            "cmd": " ".join(cmd),
            "started_at": started,
            "exit_code": proc.returncode,
            "status": "OK" if proc.returncode == 0 else ("WARN" if allow_fail else "FAIL"),
            "stdout_tail": proc.stdout[-500:].strip() if proc.stdout else "",
            "stderr_tail": proc.stderr[-300:].strip() if proc.stderr else "",
        }
    except subprocess.TimeoutExpired:
        return {"step": name, "status": "TIMEOUT", "cmd": " ".join(cmd)}
    except Exception as e:
        return {"step": name, "status": "EXCEPTION", "error": str(e)[:200]}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--skip-neo4j", action="store_true",
                        help="Skip AuraDB heartbeat (use when offline)")
    args = parser.parse_args()

    print(f"=== Neo Genesis Ontology Daily Maintenance ===")
    print(f"Started: {dt.datetime.now(dt.timezone.utc).isoformat(timespec='seconds')}")
    print()

    steps = []

    # 1a. Re-extract meta
    steps.append(run_step(
        "extract_minimal",
        [str(SCRIPTS_DIR / "extract_minimal.py")],
    ))

    # 1b. Re-extract business
    steps.append(run_step(
        "extract_business",
        [str(SCRIPTS_DIR / "business" / "extract_business.py")],
        allow_fail=True,
    ))

    # 2. Validate (6 P0 gates)
    steps.append(run_step(
        "validate",
        [str(SCRIPTS_DIR / "validate.py")],
    ))

    # 3. Competency Q regression
    steps.append(run_step(
        "validate_competency",
        [str(SCRIPTS_DIR / "validate_competency.py")],
    ))

    # 4. Community detection refresh
    steps.append(run_step(
        "graphrag_rebuild",
        [str(SCRIPTS_DIR / "graphrag.py"), "--rebuild"],
        allow_fail=True,
    ))

    # 5. Vector index rebuild
    steps.append(run_step(
        "vector_index_rebuild",
        [str(SCRIPTS_DIR / "vector_index.py"), "--rebuild"],
        allow_fail=True,
    ))

    # 5b. KPI auto-fetch (GA4 / GSC / PostHog → biz:KPI.current_value)
    steps.append(run_step(
        "kpi_auto_fetch",
        [str(SCRIPTS_DIR / "business" / "kpi_fetch.py")],
        allow_fail=True,
    ))

    # 5c. External signals (market via yfinance + conference deadlines)
    steps.append(run_step(
        "external_signals",
        [str(SCRIPTS_DIR / "business" / "external_signal_fetcher.py")],
        allow_fail=True,
    ))

    # NOTE: AuraDB sync moved to AFTER decision_outcome_tracker + outcome_timeline +
    # agent_contribution_audit — those overwrite biz/nodes.jsonl. Sync MUST be last
    # to push outcome_status / outcome_snapshots / observed contributions to AuraDB.
    # (Chrome verification 2026-05-14 — drift detected before this reorder.)
    pass

    # 6b. Decision outcome tracker (learning loop)
    steps.append(run_step(
        "decision_outcome_tracker",
        [str(SCRIPTS_DIR / "business" / "decision_outcome_tracker.py")],
        allow_fail=True,
    ))

    # 6c. Outcome timeline (status changes over days)
    steps.append(run_step(
        "outcome_timeline",
        [str(SCRIPTS_DIR / "business" / "outcome_timeline.py")],
        allow_fail=True,
    ))

    # 6d. Agent contribution audit (real measured, replaces hardcoded)
    steps.append(run_step(
        "agent_contribution_audit",
        [str(SCRIPTS_DIR / "business" / "agent_contribution_auditor.py")],
        allow_fail=True,
    ))

    # 6e. AuraDB sync — moved to AFTER all biz/nodes.jsonl mutators (sync ordering fix)
    if not args.skip_neo4j and os.environ.get("NEO4J_BOLT_URI") and os.environ.get("NEO4J_PASSWORD"):
        steps.append(run_step(
            "neo4j_parity_meta",
            [str(SCRIPTS_DIR / "migrate_to_neo4j.py"), "--verify"],
            allow_fail=True,
        ))
        steps.append(run_step(
            "neo4j_sync_business",
            [str(SCRIPTS_DIR / "business" / "sync_business_to_neo4j.py"),
             "--import-nodes", "--import-edges", "--verify"],
            allow_fail=True,
        ))
    else:
        steps.append({"step": "neo4j_parity_meta", "status": "SKIP",
                      "reason": "NEO4J_BOLT_URI / NEO4J_PASSWORD env not set"})
        steps.append({"step": "neo4j_sync_business", "status": "SKIP",
                      "reason": "NEO4J env not set"})

    # 7. Active surfacing — daily attention digest (AI-native operating)
    steps.append(run_step(
        "daily_digest",
        [str(SCRIPTS_DIR / "business" / "daily_digest.py"), "--save-as-decision"],
        allow_fail=True,
    ))

    # 7b. Generate static HTML dashboard (browseable)
    steps.append(run_step(
        "dashboard_generator",
        [str(SCRIPTS_DIR / "business" / "dashboard_generator.py")],
        allow_fail=True,
    ))

    # 8. Self-record heartbeat ActionRun
    steps.append(run_step(
        "auto_record_heartbeat",
        [str(SCRIPTS_DIR / "auto_record.py"),
         "--kind", "heartbeat",
         "--agent", "neo://agent/ontology-daily-cron",
         "--label", f"daily_maintain {dt.datetime.now().strftime('%Y-%m-%d')}",
         "--meta", json.dumps({"orchestrator": "daily_maintain.py"})],
    ))

    # Summary
    pass_count = sum(1 for s in steps if s.get("status") == "OK")
    warn_count = sum(1 for s in steps if s.get("status") in ("WARN", "SKIP"))
    fail_count = sum(1 for s in steps if s.get("status") in ("FAIL", "TIMEOUT", "EXCEPTION"))

    summary = {
        "started_at": steps[0].get("started_at"),
        "finished_at": dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds"),
        "total_steps": len(steps),
        "pass": pass_count,
        "warn": warn_count,
        "fail": fail_count,
        "steps": steps,
    }
    print(json.dumps(summary, indent=2, ensure_ascii=False, default=str))

    # Persist report
    report_path = REPO_ROOT / ".agent" / "ontology" / "daily_maintain_last.json"
    report_path.write_text(json.dumps(summary, indent=2, ensure_ascii=False, default=str), encoding="utf-8")
    print(f"\n[OK] report -> {report_path}")

    if fail_count > 0:
        return 2
    if warn_count > 0:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
