#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import html
import json
import sys
from datetime import datetime, timezone, timedelta
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TEMPLATE = PROJECT_ROOT / "src" / "core" / "governance" / "templates" / "judgment_report.html"
DEFAULT_SCHEMA = PROJECT_ROOT / ".agent" / "schemas" / "decision_artifact.schema.json"
SCHEMA_VERSION = "ng.judgment.v1"

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")


def _kst_now() -> str:
    return datetime.now(timezone(timedelta(hours=9))).isoformat(timespec="seconds")


def _load_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _rel(path: Path) -> str:
    try:
        return str(path.resolve().relative_to(PROJECT_ROOT)).replace("/", "\\")
    except ValueError:
        return str(path)


def _escape(value: Any) -> str:
    return html.escape("" if value is None else str(value), quote=True)


def _script_json(value: dict[str, Any]) -> str:
    return (
        json.dumps(value, ensure_ascii=False, indent=2)
        .replace("&", "\\u0026")
        .replace("<", "\\u003c")
        .replace(">", "\\u003e")
        .replace("\u2028", "\\u2028")
        .replace("\u2029", "\\u2029")
    )


def _status(value: str | None) -> str:
    value = (value or "neutral").lower()
    if value in {"green", "yellow", "red", "neutral"}:
        return value
    return "neutral"


def _table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return '<p class="empty">none</p>'
    head = "".join(f"<th>{_escape(label)}</th>" for key, label in columns)
    body_rows = []
    for row in rows:
        cells = "".join(f"<td>{_escape(row.get(key, ''))}</td>" for key, label in columns)
        body_rows.append(f"<tr>{cells}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _status_table(rows: list[dict[str, Any]], columns: list[tuple[str, str]]) -> str:
    if not rows:
        return '<p class="empty">none</p>'
    head = "".join(f"<th>{_escape(label)}</th>" for key, label in columns)
    body_rows = []
    for row in rows:
        cells = []
        for key, label in columns:
            value = row.get(key, "")
            if key in {"status", "severity", "state", "decision"}:
                cls = _status(str(value).lower())
                if str(value).lower() in {"low", "mitigated", "approved", "not_required", "done", "proceed"}:
                    cls = "green"
                elif str(value).lower() in {"medium", "open", "pending", "review", "next"}:
                    cls = "yellow"
                elif str(value).lower() in {"high", "critical", "blocked", "rejected", "block"}:
                    cls = "red"
                cells.append(f'<td><span class="badge {cls}">{_escape(value)}</span></td>')
            else:
                cells.append(f"<td>{_escape(value)}</td>")
        body_rows.append(f"<tr>{''.join(cells)}</tr>")
    return f"<table><thead><tr>{head}</tr></thead><tbody>{''.join(body_rows)}</tbody></table>"


def _json_schema_errors(artifact: dict[str, Any], schema_path: Path = DEFAULT_SCHEMA) -> list[str]:
    if not schema_path.exists():
        return [f"schema file not found: {schema_path}"]
    try:
        from jsonschema import Draft202012Validator
    except ModuleNotFoundError:
        return []

    schema = json.loads(schema_path.read_text(encoding="utf-8"))
    validator = Draft202012Validator(schema)
    errors = []
    for error in sorted(validator.iter_errors(artifact), key=lambda item: list(item.path)):
        path = "/".join(str(part) for part in error.path) or "$"
        errors.append(f"schema: {path}: {error.message}")
    return errors


def validate_decision_artifact(
    artifact: dict[str, Any],
    *,
    schema_path: Path = DEFAULT_SCHEMA,
    use_json_schema: bool = True,
) -> list[str]:
    errors: list[str] = []
    if artifact.get("schemaVersion") != SCHEMA_VERSION:
        errors.append(f"schemaVersion must be {SCHEMA_VERSION}")

    for key in ("generatedAt", "run", "mission", "verdict", "summary", "evidence", "risks", "approvals", "nextActions"):
        if key not in artifact:
            errors.append(f"missing top-level key: {key}")

    run = artifact.get("run") if isinstance(artifact.get("run"), dict) else {}
    if not run.get("id"):
        errors.append("run.id is required")
    if not run.get("kind"):
        errors.append("run.kind is required")

    mission = artifact.get("mission") if isinstance(artifact.get("mission"), dict) else {}
    if not mission.get("goal"):
        errors.append("mission.goal is required")

    verdict = artifact.get("verdict") if isinstance(artifact.get("verdict"), dict) else {}
    if verdict.get("status") not in {"green", "yellow", "red"}:
        errors.append("verdict.status must be green, yellow, or red")
    if verdict.get("decision") not in {"proceed", "review", "block"}:
        errors.append("verdict.decision must be proceed, review, or block")
    for key in ("label", "reason"):
        if not verdict.get(key):
            errors.append(f"verdict.{key} is required")

    summary = artifact.get("summary") if isinstance(artifact.get("summary"), dict) else {}
    for key in ("conclusion", "topAction", "residualRisk"):
        if not summary.get(key):
            errors.append(f"summary.{key} is required")

    for key in ("evidence", "risks", "approvals", "nextActions"):
        if not isinstance(artifact.get(key), list):
            errors.append(f"{key} must be a list")

    if use_json_schema:
        errors.extend(_json_schema_errors(artifact, schema_path))

    return errors


def _count_regression_issues(regression: dict[str, Any] | None) -> tuple[int, int]:
    if not regression:
        return 0, 0
    return int(regression.get("criticalIssueCount") or 0), int(regression.get("warningCount") or 0)


def _parse_json_object(text: str) -> dict[str, Any] | None:
    text = (text or "").strip()
    if not text:
        return None
    start = text.find("{")
    end = text.rfind("}")
    if start < 0 or end < start:
        return None
    try:
        parsed = json.loads(text[start : end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _regression_from_growth_loop(growth_loop: dict[str, Any] | None) -> dict[str, Any] | None:
    for step in (growth_loop or {}).get("steps") or []:
        if step.get("name") != "regression-gate":
            continue
        return _parse_json_object(step.get("stdoutTail", ""))
    return None


def from_sbu_control_tower(
    control_tower: dict[str, Any],
    *,
    control_path: Path,
    regression: dict[str, Any] | None = None,
    regression_path: Path | None = None,
    growth_loop: dict[str, Any] | None = None,
    growth_loop_path: Path | None = None,
) -> dict[str, Any]:
    stale_regression: dict[str, Any] | None = None
    if regression is None:
        regression = _regression_from_growth_loop(growth_loop)
        if regression and regression.get("generatedAt") != control_tower.get("generatedAt"):
            stale_regression = regression
            regression = None

    sites = control_tower.get("sites") or []
    regression_reference = ""
    if regression_path:
        regression_reference = _rel(regression_path)
    elif regression is not None and growth_loop_path:
        regression_reference = f"{_rel(growth_loop_path)}#regression-gate"
    red_sites = [site for site in sites if site.get("status") == "red"]
    yellow_sites = [site for site in sites if site.get("status") == "yellow"]
    action_sites = [site for site in sites if site.get("actions")]
    critical_count, warning_count = _count_regression_issues(regression)

    if critical_count or red_sites:
        status = "red"
        decision = "block"
        label = "Block"
        reason = "Critical SBU gate failed."
    elif warning_count or yellow_sites or action_sites:
        status = "yellow"
        decision = "review"
        label = "Review"
        reason = "No critical blocker, but warnings or review actions remain."
    else:
        status = "green"
        decision = "proceed"
        label = "Proceed"
        reason = "SBU control tower and live checks are green."

    source_artifacts = [_rel(control_path)]
    if regression_path:
        source_artifacts.append(_rel(regression_path))
    if growth_loop_path:
        source_artifacts.append(_rel(growth_loop_path))

    site_count = len(sites)
    live_ok_count = 0
    dirty_count = 0
    modeled_mau_total = 0
    for site in sites:
        live = site.get("live") or {}
        if all((live.get(key) or {}).get("ok") for key in ("blog", "detail", "sitemap")):
            live_ok_count += 1
        if ((site.get("local") or {}).get("git") or {}).get("dirty"):
            dirty_count += 1
        modeled_mau_total += int((((site.get("local") or {}).get("posts") or {}).get("modeledMau")) or 0)

    issues = list((regression or {}).get("issues") or [])
    warnings = list((regression or {}).get("warnings") or [])
    risks = []
    if stale_regression:
        risks.append({
            "severity": "low",
            "label": "stale regression output ignored",
            "mitigation": (
                "The regression stdout came from a different control tower timestamp "
                f"({stale_regression.get('generatedAt', 'unknown')}) and was not used for the current verdict."
            ),
            "status": "mitigated",
        })
    for item in issues:
        risks.append({
            "severity": "high",
            "label": f"{item.get('site', 'sbu')} / {item.get('code', 'issue')}",
            "mitigation": item.get("message", "Resolve critical SBU gate failure."),
            "status": "open",
        })
    for item in warnings:
        risks.append({
            "severity": "medium",
            "label": f"{item.get('site', 'sbu')} / {item.get('code', 'warning')}",
            "mitigation": item.get("message", "Review warning before automated external action."),
            "status": "open",
        })
    for site in action_sites:
        for action in site.get("actions") or []:
            risks.append({
                "severity": "medium",
                "label": f"{site.get('id', 'sbu')} action",
                "mitigation": action,
                "status": "open",
            })

    approvals = []
    if dirty_count or status != "green":
        approvals.append({
            "authorityTier": "G3",
            "action": "SBU deploy or push continuation",
            "scope": "SBU growth automation after review warnings are resolved",
            "rollbackPath": "Use latest git commit plus Vercel deployment rollback for affected SBU only.",
            "state": "pending" if status == "yellow" else "blocked",
        })
    else:
        approvals.append({
            "authorityTier": "G3",
            "action": "SBU routine continuation",
            "scope": "Existing standing approval for SBU growth operations",
            "rollbackPath": "Per-SBU git revert or Vercel rollback if a later external action fails.",
            "state": "not_required",
        })

    growth_steps = []
    for step in (growth_loop or {}).get("steps") or []:
        growth_steps.append({
            "label": step.get("name", "step"),
            "value": "passed" if step.get("ok") else "failed",
            "status": "green" if step.get("ok") else "red",
            "detail": step.get("cmd", ""),
        })

    next_action = "Continue normal SBU loop."
    if status == "red":
        next_action = "Fix critical SBU gate failure before deploy, push, or indexing work."
    elif status == "yellow":
        next_action = "Review warnings and dirty worktrees before external side effects."

    return {
        "schemaVersion": SCHEMA_VERSION,
        "generatedAt": control_tower.get("generatedAt") or _kst_now(),
        "run": {
            "id": "sbu-growth-control-tower",
            "kind": "sbu_growth",
            "sourceArtifacts": source_artifacts,
        },
        "mission": {
            "goal": "Judge whether the SBU growth loop is ready to proceed.",
            "successCriteria": [
                "Control tower generated.",
                "Regression gate has zero critical issues.",
                "Live blog, detail, and sitemap checks pass for each SBU.",
                "Residual warnings are visible before external side effects.",
            ],
            "constraints": [
                "Do not print secrets.",
                "Do not treat DB-only publish as success for file-based SBU blogs.",
                "Keep live verification separate from local publish success.",
            ],
        },
        "verdict": {
            "status": status,
            "decision": decision,
            "label": label,
            "reason": reason,
        },
        "summary": {
            "conclusion": f"{label}: {reason}",
            "topAction": next_action,
            "residualRisk": "Warnings are review points; critical issues block external continuation.",
        },
        "metrics": [
            {"label": "SBU sites", "value": site_count, "status": "neutral"},
            {"label": "Live OK", "value": f"{live_ok_count}/{site_count}", "status": "green" if live_ok_count == site_count else "red"},
            {"label": "Modeled MAU", "value": modeled_mau_total, "status": "neutral"},
            {"label": "Critical issues", "value": critical_count, "status": "green" if critical_count == 0 else "red"},
            {"label": "Warnings", "value": warning_count, "status": "green" if warning_count == 0 else "yellow"},
            {"label": "Dirty SBU worktrees", "value": dirty_count, "status": "green" if dirty_count == 0 else "yellow"},
        ],
        "lanes": [
            {
                "label": "SBU Control Tower",
                "value": "generated",
                "status": "green" if site_count else "red",
                "detail": _rel(control_path),
            },
            {
                "label": "Regression Gate",
                "value": "passed" if critical_count == 0 else "failed",
                "status": "green" if critical_count == 0 else "red",
                "detail": regression_reference or "not attached",
            },
            *growth_steps[:8],
        ],
        "evidence": [
            {
                "type": "file",
                "label": "Control tower JSON",
                "status": "green",
                "reference": _rel(control_path),
                "summary": "SBU status, local checks, and live checks.",
            },
            {
                "type": "file",
                "label": "Regression gate output",
                "status": "green" if critical_count == 0 else "red",
                "reference": regression_reference,
                "summary": f"{critical_count} critical issues, {warning_count} warnings."
                + (" Stale growth-loop regression output was ignored." if stale_regression else ""),
            },
            *[
                {
                    "type": "url",
                    "label": f"{site.get('name', site.get('id', 'SBU'))} domain",
                    "status": "green" if site.get("status") == "green" else "yellow",
                    "reference": site.get("domain", ""),
                    "summary": f"score={site.get('score')} status={site.get('status')}",
                }
                for site in sites[:12]
            ],
        ],
        "risks": risks,
        "approvals": approvals,
        "memory": [],
        "nextActions": [
            {
                "label": next_action,
                "owner": "Codex/SBU automation",
                "status": "next" if status != "red" else "blocked",
            }
        ],
    }


def render_html(artifact: dict[str, Any], template_path: Path = DEFAULT_TEMPLATE) -> str:
    errors = validate_decision_artifact(artifact)
    if errors:
        raise ValueError("; ".join(errors))

    run = artifact["run"]
    verdict = artifact["verdict"]
    summary = artifact["summary"]
    mission = artifact["mission"]
    body = []
    body.append('<section class="grid">')
    body.append('<div class="panel span-12"><div class="summary">')
    for label, key in (("Conclusion", "conclusion"), ("Top Action", "topAction"), ("Residual Risk", "residualRisk")):
        body.append(
            f'<div class="summary-item"><div class="label">{_escape(label)}</div>'
            f'<div class="value">{_escape(summary.get(key))}</div></div>'
        )
    body.append("</div></div>")

    criteria = "".join(f"<li>{_escape(item)}</li>" for item in mission.get("successCriteria", []))
    constraints = "".join(f"<li>{_escape(item)}</li>" for item in mission.get("constraints", []))
    body.append(
        '<div class="panel span-8"><h2>Mission</h2>'
        f'<p class="value">{_escape(mission.get("goal"))}</p>'
        '<div style="height:10px"></div>'
        '<h3>Success Criteria</h3>'
        f'<ul>{criteria or "<li>none</li>"}</ul>'
        '</div>'
    )
    body.append(
        '<div class="panel span-4"><h2>Verdict</h2>'
        f'<p><span class="badge {_status(verdict.get("status"))}">{_escape(verdict.get("decision"))}</span></p>'
        f'<p class="meta">{_escape(verdict.get("reason"))}</p>'
        '<div style="height:10px"></div>'
        '<h3>Constraints</h3>'
        f'<ul>{constraints or "<li>none</li>"}</ul>'
        '</div>'
    )

    body.append('<div class="panel span-6"><h2>Metrics</h2>')
    body.append(_status_table(artifact.get("metrics", []), [("label", "Metric"), ("value", "Value"), ("status", "Status"), ("detail", "Detail")]))
    body.append("</div>")

    body.append('<div class="panel span-6"><h2>Agent Lanes</h2>')
    body.append(_status_table(artifact.get("lanes", []), [("label", "Lane"), ("value", "Result"), ("status", "Status"), ("detail", "Detail")]))
    body.append("</div>")

    body.append('<div class="panel span-12"><h2>Evidence Board</h2>')
    body.append(_status_table(artifact.get("evidence", []), [("type", "Type"), ("label", "Label"), ("status", "Status"), ("reference", "Reference"), ("summary", "Summary")]))
    body.append("</div>")

    body.append('<div class="panel span-6"><h2>Risk Board</h2>')
    body.append(_status_table(artifact.get("risks", []), [("severity", "Severity"), ("label", "Risk"), ("status", "State"), ("mitigation", "Mitigation")]))
    body.append("</div>")

    body.append('<div class="panel span-6"><h2>Approval Queue</h2>')
    body.append(_status_table(artifact.get("approvals", []), [("authorityTier", "Tier"), ("action", "Action"), ("state", "State"), ("scope", "Scope"), ("rollbackPath", "Rollback")]))
    body.append("</div>")

    body.append('<div class="panel span-6"><h2>Memory Board</h2>')
    body.append(_table(artifact.get("memory", []), [("label", "Memory"), ("value", "Value"), ("status", "Status"), ("detail", "Detail")]))
    body.append("</div>")

    body.append('<div class="panel span-6"><h2>Next Actions</h2>')
    body.append(_status_table(artifact.get("nextActions", []), [("label", "Action"), ("owner", "Owner"), ("status", "Status"), ("due", "Due")]))
    body.append("</div>")
    body.append("</section>")

    title = f"Judgment Control Tower - {run.get('kind')}"
    replacements = {
        "{{title}}": _escape(title),
        "{{generated_at}}": _escape(artifact.get("generatedAt")),
        "{{run_kind}}": _escape(run.get("kind")),
        "{{run_id}}": _escape(run.get("id")),
        "{{status_class}}": _status(verdict.get("status")),
        "{{verdict_label}}": _escape(verdict.get("label")),
        "{{body}}": "\n".join(body),
        "{{artifact_json}}": _script_json(artifact),
    }
    template = template_path.read_text(encoding="utf-8")
    for needle, value in replacements.items():
        template = template.replace(needle, value)
    return template


def parse_args(argv: list[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Render a Neo Genesis judgment report HTML file.")
    source = parser.add_mutually_exclusive_group(required=True)
    source.add_argument("--input", type=Path, help="Existing decision artifact JSON.")
    source.add_argument("--from-sbu-control-tower", type=Path, help="SBU control tower JSON to convert.")
    parser.add_argument("--regression", type=Path, help="Optional SBU regression gate JSON.")
    parser.add_argument("--growth-loop", type=Path, help="Optional SBU growth loop JSON.")
    parser.add_argument("--output", type=Path, help="HTML output path.")
    parser.add_argument("--decision-output", type=Path, help="Optional normalized decision JSON output path.")
    parser.add_argument("--template", type=Path, default=DEFAULT_TEMPLATE)
    parser.add_argument("--validate-only", action="store_true")
    parser.add_argument("--print-json", action="store_true")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv or sys.argv[1:])
    if args.input:
        artifact = _load_json(args.input)
    else:
        regression = _load_json(args.regression) if args.regression else None
        growth_loop = _load_json(args.growth_loop) if args.growth_loop else None
        artifact = from_sbu_control_tower(
            _load_json(args.from_sbu_control_tower),
            control_path=args.from_sbu_control_tower,
            regression=regression,
            regression_path=args.regression,
            growth_loop=growth_loop,
            growth_loop_path=args.growth_loop,
        )

    errors = validate_decision_artifact(artifact)
    if errors:
        for error in errors:
            print(f"error: {error}", file=sys.stderr)
        return 2

    if args.print_json:
        print(json.dumps(artifact, ensure_ascii=False, indent=2))

    if args.decision_output:
        args.decision_output.parent.mkdir(parents=True, exist_ok=True)
        args.decision_output.write_text(json.dumps(artifact, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    if args.validate_only:
        return 0

    if not args.output:
        print("error: --output is required unless --validate-only is used", file=sys.stderr)
        return 2

    html_text = render_html(artifact, args.template)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(html_text, encoding="utf-8")
    print(str(args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
