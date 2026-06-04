# -*- coding: utf-8 -*-
from pathlib import Path
import json
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import render_judgment_report


def _minimal_control_tower():
    return {
        "generatedAt": "2026-05-12T13:00:00+09:00",
        "sites": [
            {
                "id": "toolpick",
                "name": "ToolPick <script>",
                "domain": "https://toolpick.dev",
                "score": 88,
                "status": "green",
                "local": {
                    "git": {"dirty": False},
                    "posts": {"modeledMau": 149100},
                },
                "live": {
                    "blog": {"ok": True},
                    "detail": {"ok": True},
                    "sitemap": {"ok": True},
                },
                "actions": [],
            }
        ],
    }


def test_validate_decision_artifact_rejects_missing_fields():
    errors = render_judgment_report.validate_decision_artifact({"schemaVersion": "ng.judgment.v1"})

    assert "missing top-level key: run" in errors
    assert "verdict.status must be green, yellow, or red" in errors


def test_sbu_control_tower_conversion_is_green(tmp_path):
    control_path = tmp_path / "control.json"
    control_path.write_text(json.dumps(_minimal_control_tower()), encoding="utf-8")

    artifact = render_judgment_report.from_sbu_control_tower(
        json.loads(control_path.read_text(encoding="utf-8")),
        control_path=control_path,
    )

    assert artifact["schemaVersion"] == "ng.judgment.v1"
    assert artifact["verdict"]["status"] == "green"
    assert artifact["verdict"]["decision"] == "proceed"
    assert artifact["metrics"][1]["value"] == "1/1"
    assert not render_judgment_report.validate_decision_artifact(artifact)


def test_json_schema_validation_rejects_invalid_evidence_type(tmp_path):
    control_path = tmp_path / "control.json"
    artifact = render_judgment_report.from_sbu_control_tower(
        _minimal_control_tower(),
        control_path=control_path,
    )
    artifact["evidence"][0]["type"] = "unsafe-html"

    errors = render_judgment_report.validate_decision_artifact(artifact)

    assert any("schema:" in error and "unsafe-html" in error for error in errors)


def test_sbu_regression_warnings_require_review(tmp_path):
    control_path = tmp_path / "control.json"
    control_path.write_text(json.dumps(_minimal_control_tower()), encoding="utf-8")
    regression = {
        "criticalIssueCount": 0,
        "warningCount": 1,
        "issues": [],
        "warnings": [
            {
                "site": "toolpick",
                "code": "dirty_worktree",
                "message": "Review dirty tree.",
            }
        ],
    }

    artifact = render_judgment_report.from_sbu_control_tower(
        _minimal_control_tower(),
        control_path=control_path,
        regression=regression,
        regression_path=tmp_path / "regression.json",
    )

    assert artifact["verdict"]["status"] == "yellow"
    assert artifact["verdict"]["decision"] == "review"
    assert artifact["approvals"][0]["state"] == "pending"


def test_sbu_regression_can_be_read_from_growth_loop_stdout(tmp_path):
    control_path = tmp_path / "control.json"
    growth_loop = {
        "steps": [
            {
                "name": "regression-gate",
                "stdoutTail": json.dumps(
                    {
                        "generatedAt": "2026-05-12T13:00:00+09:00",
                        "criticalIssueCount": 1,
                        "warningCount": 0,
                        "issues": [
                            {
                                "site": "toolpick",
                                "code": "live_detail_failed",
                                "message": "Live detail page failed.",
                            }
                        ],
                        "warnings": [],
                    }
                ),
            }
        ]
    }

    artifact = render_judgment_report.from_sbu_control_tower(
        _minimal_control_tower(),
        control_path=control_path,
        growth_loop=growth_loop,
        growth_loop_path=tmp_path / "growth-loop.json",
    )

    assert artifact["verdict"]["status"] == "red"
    assert artifact["verdict"]["decision"] == "block"
    assert artifact["risks"][0]["label"] == "toolpick / live_detail_failed"


def test_stale_growth_loop_regression_is_ignored(tmp_path):
    control_path = tmp_path / "control.json"
    growth_loop = {
        "steps": [
            {
                "name": "regression-gate",
                "stdoutTail": json.dumps(
                    {
                        "generatedAt": "2026-05-12T12:59:00+09:00",
                        "criticalIssueCount": 0,
                        "warningCount": 1,
                        "issues": [],
                        "warnings": [
                            {
                                "site": "toolpick",
                                "code": "dirty_worktree",
                                "message": "Old warning.",
                            }
                        ],
                    }
                ),
            }
        ]
    }

    artifact = render_judgment_report.from_sbu_control_tower(
        _minimal_control_tower(),
        control_path=control_path,
        growth_loop=growth_loop,
        growth_loop_path=tmp_path / "growth-loop.json",
    )

    assert artifact["verdict"]["status"] == "green"
    assert artifact["metrics"][4]["value"] == 0
    assert artifact["risks"][0]["label"] == "stale regression output ignored"
    assert artifact["risks"][0]["status"] == "mitigated"


def test_render_html_escapes_untrusted_values(tmp_path):
    control_path = tmp_path / "control.json"
    artifact = render_judgment_report.from_sbu_control_tower(
        _minimal_control_tower(),
        control_path=control_path,
    )

    rendered = render_judgment_report.render_html(artifact)

    assert "ToolPick &lt;script&gt;" in rendered
    assert "ToolPick <script>" not in rendered
    assert '<script id="decision-artifact" type="application/json">' in rendered
    assert '"schemaVersion": "ng.judgment.v1"' in rendered
    assert "ToolPick \\u003cscript\\u003e" in rendered
