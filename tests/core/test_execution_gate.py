# -*- coding: utf-8 -*-
from pathlib import Path
import sys

import pytest

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.governance.execution_gate import (
    CONTROL_EXTERNAL_APPROVAL,
    evaluate_text_execution_gate,
    evaluate_tool_execution_gate,
    filter_tools_for_gate,
)


def test_text_gate_requires_approval_for_external_side_effect():
    decision = evaluate_text_execution_gate("git push the current branch")

    assert decision.authority_tier == "G4"
    assert decision.requires_approval is True
    assert decision.allowed is False
    assert CONTROL_EXTERNAL_APPROVAL in decision.controls


def test_report_only_metadata_bypasses_execution_patterns():
    decision = evaluate_text_execution_gate(
        "send telegram and deploy production",
        {"automation": "daily-ai-brief"},
    )

    assert decision.authority_tier == "G0"
    assert decision.requires_approval is False
    assert decision.allowed is True


def test_prod_rule_does_not_match_product_words():
    decision = evaluate_text_execution_gate("summarize the product roadmap")

    assert decision.authority_tier == "G1"
    assert decision.requires_approval is False
    assert decision.allowed is True


def test_text_gate_treats_image_generation_as_external_side_effect():
    decision = evaluate_text_execution_gate("이미지 생성해줘")

    assert decision.authority_tier == "G4"
    assert decision.requires_approval is True
    assert CONTROL_EXTERNAL_APPROVAL in decision.controls


def test_tool_gate_blocks_external_mutation_without_owner_approval():
    blocked = evaluate_tool_execution_gate("gmail_send")
    approved = evaluate_tool_execution_gate("gmail_send", owner_approved=True)

    assert blocked.authority_tier == "G4"
    assert blocked.requires_approval is True
    assert blocked.allowed is False
    assert approved.allowed is True


def test_filter_tools_removes_high_risk_tools_until_approved():
    def read_status():
        return "ok"

    def gmail_send():
        return "sent"

    allowed, blocked = filter_tools_for_gate([read_status, gmail_send])

    assert [tool.__name__ for tool in allowed] == ["read_status"]
    assert [decision.matched[0] for decision in blocked] == ["gmail_send"]


@pytest.mark.asyncio
async def test_agent_router_sora_engine_fallback_requires_approval():
    from src.core.brain.agent_router import AgentRouter

    router = AgentRouter()

    with pytest.raises(PermissionError):
        await router._call_sora_engine("git push the current branch")


@pytest.mark.asyncio
async def test_task_planner_blocks_high_risk_tool_without_approval():
    from src.core.task_planner import SubTask, TaskPlan, TaskPlanner

    planner = TaskPlanner()
    plan = TaskPlan(
        command="send email",
        tasks=[
            SubTask(
                step=1,
                description="send external email",
                tool_name="gmail_send",
                tool_args={"to": "owner@example.com", "subject": "x", "body": "y"},
            )
        ],
    )

    await planner._execute_steps(plan, owner_approved=False)

    assert plan.status == "failed"
    assert plan.tasks[0].success is False
    assert "SEC-002/004/008" in plan.tasks[0].error
