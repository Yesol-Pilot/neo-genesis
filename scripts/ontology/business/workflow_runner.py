"""Neo Genesis -- Workflow executor (actuation loop closure).

Reads `biz:Workflow` nodes with `executable_command` field → executes →
records ActionRun{kind:workflow_run} for audit.

This closes the loop: ontology no longer just describes operating procedures
but actually drives them.

Safety:
- Only commands explicitly박제된 in Workflow.executable_command are executable.
- Timeout 5 min per workflow.
- ActionRun audit trail per execution.
- --dry-run shows what would run.
- Precondition evaluation (when specified) gate execution.

Usage:
    # List executable workflows
    python scripts/ontology/business/workflow_runner.py --list

    # Run specific workflow
    python scripts/ontology/business/workflow_runner.py --run neo://biz/workflow/kpi-auto-fetch

    # Run all workflows whose precondition match
    python scripts/ontology/business/workflow_runner.py --run-all-ready

    # Dry-run
    python scripts/ontology/business/workflow_runner.py --run-all-ready --dry-run
"""
from __future__ import annotations

import argparse
import ast
import datetime as dt
import json
import operator as op
import os
import re
import shlex
import subprocess
import sys
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[3]
BIZ_DIR = REPO_ROOT / ".agent" / "ontology" / "business"
NODES_PATH = BIZ_DIR / "nodes.jsonl"


def load_workflows() -> list[dict]:
    """Load biz:Workflow nodes."""
    if not NODES_PATH.exists():
        return []
    workflows = []
    for line in NODES_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        n = json.loads(line)
        if n.get("rdf_type") == "biz:Workflow":
            workflows.append(n)
    return workflows


_SAFE_OPS = {
    ast.Eq: op.eq, ast.NotEq: op.ne,
    ast.Lt: op.lt, ast.LtE: op.le,
    ast.Gt: op.gt, ast.GtE: op.ge,
    ast.And: lambda a, b: a and b,
    ast.Or: lambda a, b: a or b,
    ast.Not: op.not_,
    ast.Add: op.add, ast.Sub: op.sub,
    ast.Mult: op.mul, ast.Div: op.truediv,
    ast.Mod: op.mod,
    ast.In: lambda a, b: a in b,
    ast.NotIn: lambda a, b: a not in b,
}


def _safe_eval(node, ctx):
    """Pure AST walker — eval() 회피. Only comparison + arithmetic + names + literals.

    No function calls, attribute access, subscript with arbitrary expr.
    """
    if isinstance(node, ast.Expression):
        return _safe_eval(node.body, ctx)
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name):
        if node.id in ctx:
            return ctx[node.id]
        raise ValueError(f"Unknown name: {node.id}")
    if isinstance(node, ast.BoolOp):
        vals = [_safe_eval(v, ctx) for v in node.values]
        if isinstance(node.op, ast.And):
            return all(vals)
        if isinstance(node.op, ast.Or):
            return any(vals)
        raise ValueError(f"Unsupported BoolOp: {type(node.op).__name__}")
    if isinstance(node, ast.UnaryOp):
        if isinstance(node.op, ast.Not):
            return not _safe_eval(node.operand, ctx)
        if isinstance(node.op, ast.USub):
            return -_safe_eval(node.operand, ctx)
        raise ValueError(f"Unsupported UnaryOp: {type(node.op).__name__}")
    if isinstance(node, ast.Compare):
        left = _safe_eval(node.left, ctx)
        for o, c in zip(node.ops, node.comparators):
            right = _safe_eval(c, ctx)
            if type(o) not in _SAFE_OPS:
                raise ValueError(f"Unsupported Compare op: {type(o).__name__}")
            if not _SAFE_OPS[type(o)](left, right):
                return False
            left = right
        return True
    if isinstance(node, ast.BinOp):
        if type(node.op) not in _SAFE_OPS:
            raise ValueError(f"Unsupported BinOp: {type(node.op).__name__}")
        return _SAFE_OPS[type(node.op)](
            _safe_eval(node.left, ctx), _safe_eval(node.right, ctx)
        )
    if isinstance(node, ast.Attribute):
        # Allow ONLY .weekday() on date — common precondition idiom
        obj = _safe_eval(node.value, ctx)
        if isinstance(obj, dt.date) and node.attr in ("weekday", "day", "month", "year"):
            val = getattr(obj, node.attr)
            return val() if callable(val) else val
        raise ValueError(f"Disallowed attribute: {node.attr}")
    if isinstance(node, ast.Call):
        # Allow ONLY zero-arg method calls (e.g. today.weekday())
        if isinstance(node.func, ast.Attribute) and not node.args and not node.keywords:
            return _safe_eval(node.func, ctx)
        raise ValueError("Function calls not allowed in precondition")
    raise ValueError(f"Unsupported node: {type(node).__name__}")


def eval_precondition(precondition: str, context: dict) -> bool:
    """AST-based safe evaluator (no eval / no exec).

    Supports: ==, !=, <, <=, >, >=, and, or, not, +, -, *, /, %, in, not in.
    + literals + names from context + zero-arg method calls on date objects.
    """
    if not precondition:
        return True
    ctx = {
        "today": dt.date.today(),
        "now": dt.datetime.now(),
        **context,
    }
    try:
        tree = ast.parse(precondition, mode="eval")
        result = _safe_eval(tree, ctx)
        return bool(result)
    except Exception as e:
        print(f"[WARN] precondition eval failed ({precondition}): {e}", file=sys.stderr)
        return False


# Allowlist for executable_command — only python scripts under scripts/ontology/
_CMD_ALLOWLIST_PREFIXES = (
    "python scripts/ontology/",
)


def is_command_allowed(cmd: str) -> bool:
    """Whitelist check — only Python scripts under scripts/ontology/."""
    return cmd.strip().startswith(_CMD_ALLOWLIST_PREFIXES)


def build_context() -> dict:
    """Build context dict for precondition evaluation."""
    # TODO: extend with real signals (blog_published_this_month, last_review_age_days, etc.)
    return {
        "blog_published_this_month": 0,  # HIVE MIND 발행 0 박제
        "last_review_age_days": 7,  # 일주일 가정 (precise tracking 별도)
    }


def list_workflows() -> dict:
    workflows = load_workflows()
    rows = []
    for w in workflows:
        rows.append({
            "id": w["id"],
            "label": w.get("label"),
            "kind": w.get("kind"),
            "status": w.get("status"),
            "executable": bool(w.get("executable_command")),
            "has_precondition": bool(w.get("precondition")),
            "command_preview": (w.get("executable_command") or "")[:60],
        })
    return {"total": len(workflows), "executable_count": sum(1 for r in rows if r["executable"]), "workflows": rows}


def run_one(workflow: dict, dry_run: bool = False) -> dict:
    cmd = workflow.get("executable_command")
    if not cmd:
        return {"workflow": workflow["id"], "status": "SKIP", "reason": "no executable_command"}

    started_at = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")
    result = {
        "workflow": workflow["id"],
        "label": workflow.get("label"),
        "command": cmd,
        "started_at": started_at,
    }

    if dry_run:
        result["status"] = "DRY_RUN"
        result["would_execute"] = cmd
        return result

    # Security: allowlist check
    if not is_command_allowed(cmd):
        result["status"] = "BLOCKED"
        result["reason"] = f"command not allowlisted (must start with one of {_CMD_ALLOWLIST_PREFIXES})"
        return result

    try:
        env = os.environ.copy()
        env["PYTHONIOENCODING"] = "utf-8"
        env["PYTHONUTF8"] = "1"
        # shell=False + shlex argv (injection 회피)
        argv = shlex.split(cmd)
        proc = subprocess.run(
            argv, shell=False, capture_output=True, text=True,
            encoding="utf-8", cwd=str(REPO_ROOT), timeout=300, env=env,
        )
        result["exit_code"] = proc.returncode
        result["status"] = "OK" if proc.returncode == 0 else "FAIL"
        result["stdout_tail"] = (proc.stdout or "")[-500:].strip()
        result["stderr_tail"] = (proc.stderr or "")[-300:].strip()
    except subprocess.TimeoutExpired:
        result["status"] = "TIMEOUT"
    except Exception as e:
        result["status"] = "EXCEPTION"
        result["error"] = str(e)[:200]

    result["finished_at"] = dt.datetime.now(dt.timezone.utc).isoformat(timespec="seconds")

    # Record ActionRun for audit (best-effort)
    try:
        sys.path.insert(0, str(REPO_ROOT / "scripts" / "ontology"))
        from auto_record import record_action  # type: ignore
        record_action(
            kind="workflow_run" if "workflow_run" in {"workflow_run"} else "external_api_call",  # closest valid kind
            agent_id="neo://agent/workflow-runner",
            affected=[workflow["id"]],
            meta={
                "workflow_id": workflow["id"],
                "command": cmd,
                "exit_code": result.get("exit_code"),
                "status": result.get("status"),
            },
            result="success" if result.get("status") == "OK" else "failure",
            label=f"workflow_run {workflow.get('label')}",
        )
    except Exception as e:
        result["audit_record_warn"] = str(e)[:100]

    return result


def run_all_ready(dry_run: bool = False) -> dict:
    workflows = load_workflows()
    ctx = build_context()
    results = []
    for w in workflows:
        if not w.get("executable_command"):
            continue
        precond = w.get("precondition")
        if precond and not eval_precondition(precond, ctx):
            results.append({"workflow": w["id"], "status": "PRECOND_NOT_MET", "precondition": precond})
            continue
        r = run_one(w, dry_run=dry_run)
        results.append(r)
    return {
        "dry_run": dry_run,
        "total_evaluated": len(workflows),
        "executed_or_evaluated": len(results),
        "ok_count": sum(1 for r in results if r.get("status") == "OK"),
        "fail_count": sum(1 for r in results if r.get("status") == "FAIL"),
        "results": results,
    }


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--list", action="store_true")
    parser.add_argument("--run", help="Workflow URI to run (single)")
    parser.add_argument("--run-all-ready", action="store_true",
                        help="Run all workflows whose precondition matches")
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    if args.list:
        print(json.dumps(list_workflows(), indent=2, ensure_ascii=False))
        return 0

    if args.run:
        workflows = load_workflows()
        w = next((x for x in workflows if x["id"] == args.run), None)
        if not w:
            print(f"[ERROR] workflow not found: {args.run}")
            return 2
        print(json.dumps(run_one(w, dry_run=args.dry_run), indent=2, ensure_ascii=False))
        return 0

    if args.run_all_ready:
        print(json.dumps(run_all_ready(dry_run=args.dry_run), indent=2, ensure_ascii=False))
        return 0

    parser.print_help()
    return 1


if __name__ == "__main__":
    sys.exit(main())
