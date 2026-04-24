# -*- coding: utf-8 -*-
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.governance import report_gate


def test_daily_ai_ops_brief_uses_full_body_passthrough(tmp_path, monkeypatch):
    monkeypatch.setattr(report_gate, "GEMINI_API_KEY", "")
    monkeypatch.setattr(report_gate, "_THROTTLE_STATE_PATH", tmp_path / "report_gate_throttle.json")
    monkeypatch.setattr(report_gate, "_THROTTLE_LOCK_PATH", tmp_path / "report_gate_throttle.lock")
    report_gate._RECENT_FINGERPRINTS.clear()

    html_body = "<b>Sora AI Ops Brief</b>\n핵심만 전달"
    result = report_gate.review_report(
        report_type="daily_ai_ops_brief",
        title="Sora AI Ops Brief",
        summary="오늘의 한 줄 결론",
        details="상세 원문",
        severity="medium",
        source="automation",
        metadata={"html_body": html_body},
        cooldown_sec=1800,
    )

    assert result["notify"] is True
    assert result["report"] == html_body
