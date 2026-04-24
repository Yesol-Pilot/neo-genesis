# -*- coding: utf-8 -*-
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.governance import report_gate


def _reset_report_gate_state(tmp_path, monkeypatch):
    monkeypatch.setattr(report_gate, "GEMINI_API_KEY", "")
    monkeypatch.setattr(report_gate, "_THROTTLE_STATE_PATH", tmp_path / "report_gate_throttle.json")
    monkeypatch.setattr(report_gate, "_THROTTLE_LOCK_PATH", tmp_path / "report_gate_throttle.lock")
    report_gate._RECENT_FINGERPRINTS.clear()


def test_context_required_reports_use_owner_context_template(tmp_path, monkeypatch):
    _reset_report_gate_state(tmp_path, monkeypatch)

    result = report_gate.review_report(
        report_type="scheduler_alert",
        title="Dashboard Alert",
        summary="대시보드 응답이 지연되고 있습니다.",
        details="Dashboard timed out after 10 seconds.",
        severity="high",
        source="neo_scheduler",
        metadata={},
        cooldown_sec=60,
    )

    assert result["notify"] is True
    assert "<b>문제:</b>" in result["report"]
    assert "<b>영향:</b>" in result["report"]
    assert "<b>다음 조치:</b>" in result["report"]


def test_context_required_reports_without_owner_context_are_blocked(tmp_path, monkeypatch):
    _reset_report_gate_state(tmp_path, monkeypatch)
    monkeypatch.setattr(
        report_gate,
        "_ai_review",
        lambda **kwargs: {"notify": True, "reason": "ai_review", "report": "<b>Dashboard Alert</b>"},
    )

    result = report_gate.review_report(
        report_type="scheduler_alert",
        title="Dashboard Alert",
        summary="대시보드 응답이 지연되고 있습니다.",
        details="Dashboard timed out after 10 seconds.",
        severity="high",
        source="neo_scheduler",
        metadata={},
        cooldown_sec=60,
    )

    assert result["notify"] is False
    assert result["reason"] == "needs_sora_review_context"
