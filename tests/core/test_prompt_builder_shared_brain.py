# -*- coding: utf-8 -*-
from pathlib import Path
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.prompt_builder import PromptBuilder


def test_shared_brain_summary_includes_ai_ops_inbox(tmp_path):
    shared = tmp_path / "shared-brain"
    shared.mkdir()
    (shared / "ai-ops-brief-inbox.md").write_text(
        """# Inbox
- [ ] Internalize GPT-5.5 automation signal
- [ ] Review model routing cost impact
""",
        encoding="utf-8",
    )

    summary = PromptBuilder._load_shared_brain_summary(
        {"knowledge_sources": {"shared_brain_dir": str(shared)}}
    )

    assert "### ai ops brief inbox" in summary
    assert "Internalize GPT-5.5 automation signal" in summary
