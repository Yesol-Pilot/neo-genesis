# -*- coding: utf-8 -*-
import json
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import build_ai_ops_brief


def test_relevance_hint_prefers_automation_signals():
    hint = build_ai_ops_brief._relevance_hint("New agent tools", "automation workflow")
    assert isinstance(hint, str)
    assert hint


def test_format_brief_includes_operating_metadata():
    item = build_ai_ops_brief.BriefItem(
        source="OpenAI",
        title="Tooling update",
        url="https://example.com",
        summary="new api for workflows",
    )
    build_ai_ops_brief._finalize_item(item)

    brief = build_ai_ops_brief._format_brief([item])

    assert "## Sora briefing instructions" in brief
    assert "Tooling update" in brief
    assert "authority_reference" in brief
    assert "authority_tier" in brief
    assert "action_gate" in brief
    assert "eval_method" in brief
    assert "effective_score" in brief


def test_history_dedupe_penalizes_repeated_urls(tmp_path):
    history_file = tmp_path / "20260424_090000_brief.md"
    history_file.write_text(
        "# AI Ops Brief\n"
        "### 1. Old item\n"
        "- url: https://example.com/repeated\n"
        "### 2. Old item again\n"
        "- url: https://example.com/repeated/\n",
        encoding="utf-8",
    )

    item = build_ai_ops_brief.BriefItem(
        source="OpenAI",
        title="Repeated agent workflow",
        url="https://example.com/repeated/",
        summary="agent workflow automation",
    )
    build_ai_ops_brief._finalize_item(item)

    history = build_ai_ops_brief._load_recent_history(tmp_path, lookback_days=14)
    build_ai_ops_brief._apply_history([item], history)

    assert item.history_seen_count == 2
    assert item.novelty == "repeat_2"
    assert item.effective_score < item.score


def test_archive_items_accumulates_observations_and_url_index(tmp_path):
    item = build_ai_ops_brief.BriefItem(
        source="OpenAI",
        title="Agent workflow reliability",
        url="https://example.com/agent-workflow",
        summary="agent workflow automation reliability",
    )
    build_ai_ops_brief._finalize_item(item)

    stats_first = build_ai_ops_brief._archive_items([item], tmp_path, "20260424_090000", [item])
    stats_second = build_ai_ops_brief._archive_items([item], tmp_path, "20260425_090000", [item])

    observations = (tmp_path / "observations.jsonl").read_text(encoding="utf-8").splitlines()
    index = json.loads((tmp_path / "url_index.json").read_text(encoding="utf-8"))
    daily = json.loads((tmp_path / "daily" / "20260425.json").read_text(encoding="utf-8"))

    assert stats_first["new_urls"] == 1
    assert stats_second["updated_urls"] == 1
    assert len(observations) == 2
    assert index["total_urls"] == 1
    assert index["urls"]["https://example.com/agent-workflow"]["seen_count"] == 2
    assert daily["stats"]["observed"] == 1
    assert daily["items"][0]["selected_for_brief"] is True
