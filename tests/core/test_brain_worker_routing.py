# -*- coding: utf-8 -*-
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.brain.worker import _should_skip_task_planner


def test_daily_ai_brief_automation_skips_task_planner():
    assert _should_skip_task_planner(
        {
            "session_id": "automation:daily-ai-brief",
            "metadata": {
                "automation": "daily-ai-brief",
                "kind": "daily_ai_ops_brief",
            },
        }
    )


def test_general_requests_can_use_task_planner():
    assert not _should_skip_task_planner(
        {
            "session_id": "telegram",
            "metadata": {"kind": "general"},
        }
    )
