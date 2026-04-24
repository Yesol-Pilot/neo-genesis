# -*- coding: utf-8 -*-
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.governance import report_gate


class _Resp:
    status_code = 200


def test_send_reviewed_report_preserves_reply_markup(monkeypatch):
    sent = {}

    def fake_post(url, json=None, timeout=0):
        sent["url"] = url
        sent["json"] = json
        return _Resp()

    monkeypatch.setattr(report_gate, "BOT_TOKEN", "bot")
    monkeypatch.setattr(report_gate, "CHAT_ID", "chat")
    monkeypatch.setattr(report_gate.requests, "post", fake_post)

    ok = report_gate.send_reviewed_telegram_report(
        report_type="approval_requested",
        title="Approval Needed",
        summary="Need approval",
        details="Sensitive action is waiting for approval.",
        severity="high",
        source="test",
        reply_markup={"inline_keyboard": [[{"text": "승인", "callback_data": "ok"}]]},
    )

    assert ok is True
    assert "reply_markup" in sent["json"]
