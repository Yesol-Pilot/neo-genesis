# -*- coding: utf-8 -*-
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.governance.report_gate import review_report
from src.core.governance import report_gate


def _reset_report_gate_state(tmp_path, monkeypatch):
    monkeypatch.setattr(report_gate, "GEMINI_API_KEY", "")
    monkeypatch.setattr(report_gate, "_THROTTLE_STATE_PATH", tmp_path / "report_gate_throttle.json")
    monkeypatch.setattr(report_gate, "_THROTTLE_LOCK_PATH", tmp_path / "report_gate_throttle.lock")
    report_gate._RECENT_FINGERPRINTS.clear()


def test_report_gate_skips_low_signal_duplicate(tmp_path, monkeypatch):
    _reset_report_gate_state(tmp_path, monkeypatch)
    first = review_report(
        report_type="heartbeat",
        title="상태 확인",
        summary="ok",
        details="",
        severity="info",
        source="test",
        cooldown_sec=3600,
    )
    second = review_report(
        report_type="heartbeat",
        title="상태 확인",
        summary="ok",
        details="",
        severity="info",
        source="test",
        cooldown_sec=3600,
    )
    assert first["notify"] is False
    assert second["notify"] is False


def test_report_gate_sends_high_severity(tmp_path, monkeypatch):
    _reset_report_gate_state(tmp_path, monkeypatch)
    result = review_report(
        report_type="self_heal_failed",
        title="자가치유 실패",
        summary="자동 복구 실패",
        details="redis 연결 복구 실패, 수동 확인 필요",
        severity="high",
        source="self_healer",
        cooldown_sec=3600,
    )
    assert result["notify"] is True
    assert "자가치유 실패" in result["report"]
