# -*- coding: utf-8 -*-
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.governance import report_gate
from src.core.governance.report_gate import review_report


def _reset_report_gate_state(tmp_path, monkeypatch):
    monkeypatch.setattr(report_gate, "GEMINI_API_KEY", "")
    monkeypatch.setattr(report_gate, "_THROTTLE_STATE_PATH", tmp_path / "report_gate_throttle.json")
    monkeypatch.setattr(report_gate, "_THROTTLE_LOCK_PATH", tmp_path / "report_gate_throttle.lock")
    report_gate._RECENT_FINGERPRINTS.clear()


def test_ops_alert_bypasses_ai_review(tmp_path, monkeypatch):
    _reset_report_gate_state(tmp_path, monkeypatch)
    called = {"count": 0}

    def _boom(*args, **kwargs):
        called["count"] += 1
        raise AssertionError("AI review should not be called for ops_alert")

    monkeypatch.setattr(report_gate, "_ai_review", _boom)

    result = review_report(
        report_type="ops_alert",
        title="Sora AI Ops Brief delivery failed",
        summary="Sora delivery pipeline could not complete.",
        details="error: timeout",
        severity="high",
        source="ai_ops_brief_automation",
        cooldown_sec=1800,
    )

    assert called["count"] == 0
    assert result["notify"] is True
    assert "Sora AI Ops Brief delivery failed" in result["report"]
