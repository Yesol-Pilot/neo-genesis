# -*- coding: utf-8 -*-
from datetime import datetime, timezone
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import push_ai_ops_brief_to_sora


def test_build_sora_request_wraps_brief_and_operational_gates():
    brief = "## Today\n- model release"

    prompt = push_ai_ops_brief_to_sora._build_sora_request(brief)

    assert "AI Ops Brief" in prompt
    assert brief in prompt
    assert "Operational gates" in prompt
    assert "authority_tier" in prompt


def test_render_html_report_bolds_numbered_sections():
    html_report = push_ai_ops_brief_to_sora._render_html_report(
        "1. Today decision\nApply local prompt change"
    )

    assert "<b>Sora AI Ops Brief</b>" in html_report
    assert "<b>1. Today decision</b>" in html_report
    assert "Apply local prompt change" in html_report


def test_render_fallback_report_hides_raw_debug_context_and_keeps_gates():
    brief = """# AI Ops Brief
## Items
### 1. Introducing GPT-5.5
- source: OpenAI
- url: https://openai.com/index/introducing-gpt-5-5
- authority_tier: G2
- eval_method: local golden task A/B
- why_it_matters: agent workflow impact
- score: 9

### 2. Automations
- source: OpenAI
- url: https://openai.com/academy/codex-automations
- why_it_matters: automation workflow impact
- score: 6
"""

    html_report = push_ai_ops_brief_to_sora._render_fallback_report(brief)

    assert "<b>Sora AI Ops Brief</b>" in html_report
    assert "Introducing GPT-5.5" in html_report
    assert "authority_tier: G2" in html_report
    assert "fallback_reason" not in html_report
    assert "localhost:6379" not in html_report
    assert "<pre># AI Ops Brief" not in html_report


def test_record_pending_internalization_writes_shared_brain_inbox(tmp_path, monkeypatch):
    inbox_md = tmp_path / "ai-ops-brief-inbox.md"
    inbox_jsonl = tmp_path / "ai-ops-brief-inbox.jsonl"
    source_path = tmp_path / "brief.md"
    source_path.write_text("# AI Ops Brief\n", encoding="utf-8")
    monkeypatch.setattr(push_ai_ops_brief_to_sora, "SHARED_BRAIN_DIR", tmp_path)
    monkeypatch.setattr(push_ai_ops_brief_to_sora, "AI_OPS_INBOX_MD", inbox_md)
    monkeypatch.setattr(push_ai_ops_brief_to_sora, "AI_OPS_INBOX_JSONL", inbox_jsonl)

    brief = """# AI Ops Brief
## Items
### 1. Introducing GPT-5.5
- source: OpenAI
- url: https://openai.com/index/introducing-gpt-5-5
- authority_tier: G2
- action_gate: dry-run first
- eval_method: local golden task A/B
- why_it_matters: agent workflow impact
"""

    result = push_ai_ops_brief_to_sora._record_pending_internalization(
        brief,
        reason="redis unavailable",
        source_path=source_path,
        now=datetime(2026, 4, 24, 9, 0, tzinfo=timezone.utc),
    )

    md_text = inbox_md.read_text(encoding="utf-8")
    jsonl_text = inbox_jsonl.read_text(encoding="utf-8")
    assert result["inbox_markdown"] == str(inbox_md)
    assert "AI Ops Brief Pending Internalization" in md_text
    assert "Introducing GPT-5.5" in md_text
    assert "authority_tier: G2" in md_text
    assert "eval_method: local golden task A/B" in md_text
    assert "redis unavailable" in md_text
    assert '"status": "pending"' in jsonl_text
