# -*- coding: utf-8 -*-
"""SEC-002/004/008 execution gate for Sora/Codex automation.

This module is intentionally local and deterministic. It does not ask an LLM
whether a tool is safe; it maps requests and tool names to the existing G0-G5
authority model before execution.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Callable, Iterable


AUTHORITY_ORDER = {"G0": 0, "G1": 1, "G2": 2, "G3": 3, "G4": 4, "G5": 5}
CONTROL_AUTHORITY = "SEC-002"
CONTROL_TOOL_POLICY = "SEC-004"
CONTROL_EXTERNAL_APPROVAL = "SEC-008"


@dataclass(frozen=True)
class GateDecision:
    """A deterministic pre-execution decision."""

    authority_tier: str
    risk_score: int
    action: str
    requires_approval: bool
    allowed: bool
    controls: list[str] = field(default_factory=list)
    reasons: list[str] = field(default_factory=list)
    matched: list[str] = field(default_factory=list)

    def to_metadata(self, *, owner_approved: bool = False) -> dict[str, object]:
        return {
            "authority_tier": self.authority_tier,
            "risk_score": self.risk_score,
            "action": self.action,
            "requires_approval": self.requires_approval,
            "owner_approved": owner_approved,
            "controls": list(self.controls),
            "reasons": list(self.reasons),
            "matched": list(self.matched),
            "allowed": self.allowed or owner_approved,
        }


@dataclass(frozen=True)
class ToolPolicy:
    authority_tier: str
    action: str
    controls: tuple[str, ...]
    external_side_effect: bool = False


READONLY_TOOL_POLICY = ToolPolicy(
    authority_tier="G1",
    action="read-only inspection",
    controls=(CONTROL_AUTHORITY, CONTROL_TOOL_POLICY),
)

TOOL_POLICIES: dict[str, ToolPolicy] = {
    # External writes / notifications / deploys.
    "deploy_project": ToolPolicy("G5", "production deploy", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "remote_vercel_deploy": ToolPolicy("G5", "remote production deploy", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "remote_npm_build_deploy": ToolPolicy("G5", "remote build and deploy", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "remote_git_commit_push": ToolPolicy("G4", "remote git commit and push", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "gmail_draft": ToolPolicy("G4", "external email draft mutation", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "gmail_send": ToolPolicy("G4", "external email send", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "gmail_send_confirmed": ToolPolicy("G4", "external email send", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "calendar_create_event": ToolPolicy("G4", "calendar external mutation", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "calendar_update_event": ToolPolicy("G4", "calendar external mutation", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "calendar_mark_done": ToolPolicy("G4", "calendar external mutation", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "calendar_delete_event": ToolPolicy("G4", "calendar external mutation", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "notion_create_page": ToolPolicy("G4", "Notion external write", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "notion_append_block": ToolPolicy("G4", "Notion external write", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "generate_image": ToolPolicy("G4", "external image generation/notification path", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    "comfyui_generate_image": ToolPolicy("G4", "image generation/notification path", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY, CONTROL_EXTERNAL_APPROVAL), True),
    # Local or cross-device execution.
    "remote_pc_command": ToolPolicy("G3", "remote command execution", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "remote_batch_exec": ToolPolicy("G3", "remote batch execution", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "remote_claude_run": ToolPolicy("G3", "remote agent execution", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "remote_claude_chat": ToolPolicy("G3", "remote agent execution", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "run_pc_command": ToolPolicy("G3", "local PC command execution", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "execute_code": ToolPolicy("G3", "local code execution", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "exec_git_commit": ToolPolicy("G3", "local git commit", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "run_daemon_job": ToolPolicy("G3", "daemon job execution", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "scheduler_run_once": ToolPolicy("G3", "scheduler job execution", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "scheduler_start": ToolPolicy("G3", "scheduler execution", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "remote_pc_file_write": ToolPolicy("G3", "remote file write", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "comfyui_start": ToolPolicy("G3", "local GPU service start", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "local_generate_image": ToolPolicy("G3", "local image generation", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "save_to_memory": ToolPolicy("G2", "memory write", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "graph_add_knowledge": ToolPolicy("G2", "knowledge graph write", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
    "rag_index": ToolPolicy("G2", "local RAG index write", (CONTROL_AUTHORITY, CONTROL_TOOL_POLICY)),
}

READONLY_TOOL_PREFIXES = (
    "read_",
    "get_",
    "list_",
    "check_",
    "calendar_list_",
    "calendar_today",
    "gmail_list_",
    "gmail_read",
    "notion_search",
    "remote_web_search",
    "remote_web_crawl",
    "remote_git_status",
    "remote_docker_ps",
    "remote_docker_logs",
    "remote_pc_status",
    "remote_pc_screenshot",
    "remote_pc_file_read",
    "remote_pc_process_list",
    "list_connected_pcs",
    "image_engine_status",
    "comfyui_status",
    "comfyui_list_models",
    "rag_search",
    "rag_status",
    "recall_",
    "graph_search",
    "graph_status",
)

TEXT_RULES: tuple[tuple[str, str, str, str], ...] = (
    ("G5", "production deploy", CONTROL_EXTERNAL_APPROVAL, "prod"),
    ("G5", "production deploy", CONTROL_EXTERNAL_APPROVAL, "production"),
    ("G5", "production deploy", CONTROL_EXTERNAL_APPROVAL, "vercel --prod"),
    ("G5", "credential or secret change", CONTROL_EXTERNAL_APPROVAL, "credential"),
    ("G5", "credential or secret change", CONTROL_EXTERNAL_APPROVAL, "secret"),
    ("G5", "credential or secret change", CONTROL_EXTERNAL_APPROVAL, "api key"),
    ("G5", "credential or secret change", CONTROL_EXTERNAL_APPROVAL, "환경변수"),
    ("G5", "credential or secret change", CONTROL_EXTERNAL_APPROVAL, "자격증명"),
    ("G5", "financial or irreversible action", CONTROL_EXTERNAL_APPROVAL, "결제"),
    ("G5", "financial or irreversible action", CONTROL_EXTERNAL_APPROVAL, "자금"),
    ("G5", "financial or irreversible action", CONTROL_EXTERNAL_APPROVAL, "trade"),
    ("G5", "financial or irreversible action", CONTROL_EXTERNAL_APPROVAL, "매수"),
    ("G5", "financial or irreversible action", CONTROL_EXTERNAL_APPROVAL, "매도"),
    ("G4", "external notification", CONTROL_EXTERNAL_APPROVAL, "telegram"),
    ("G4", "external notification", CONTROL_EXTERNAL_APPROVAL, "텔레그램"),
    ("G4", "external notification", CONTROL_EXTERNAL_APPROVAL, "메일 발송"),
    ("G4", "external notification", CONTROL_EXTERNAL_APPROVAL, "메일 보내"),
    ("G4", "external notification", CONTROL_EXTERNAL_APPROVAL, "gmail_send"),
    ("G4", "external API mutation", CONTROL_EXTERNAL_APPROVAL, "external api"),
    ("G4", "external API mutation", CONTROL_EXTERNAL_APPROVAL, "외부 api"),
    ("G4", "git push", CONTROL_EXTERNAL_APPROVAL, "git push"),
    ("G4", "git push", CONTROL_EXTERNAL_APPROVAL, "force push"),
    ("G4", "deploy", CONTROL_EXTERNAL_APPROVAL, "deploy"),
    ("G4", "deploy", CONTROL_EXTERNAL_APPROVAL, "배포해"),
    ("G4", "deploy", CONTROL_EXTERNAL_APPROVAL, "배포 실행"),
    ("G4", "calendar mutation", CONTROL_EXTERNAL_APPROVAL, "일정 추가"),
    ("G4", "calendar mutation", CONTROL_EXTERNAL_APPROVAL, "일정 삭제"),
    ("G4", "calendar mutation", CONTROL_EXTERNAL_APPROVAL, "calendar_create_event"),
    ("G4", "calendar mutation", CONTROL_EXTERNAL_APPROVAL, "calendar_delete_event"),
    ("G4", "image generation/external notification", CONTROL_EXTERNAL_APPROVAL, "generate image"),
    ("G4", "image generation/external notification", CONTROL_EXTERNAL_APPROVAL, "이미지 생성"),
    ("G4", "image generation/external notification", CONTROL_EXTERNAL_APPROVAL, "그림 그려"),
    ("G4", "image generation/external notification", CONTROL_EXTERNAL_APPROVAL, "그려줘"),
    ("G3", "local or remote execution", CONTROL_TOOL_POLICY, "명령 실행"),
    ("G3", "local or remote execution", CONTROL_TOOL_POLICY, "원격 실행"),
    ("G3", "local or remote execution", CONTROL_TOOL_POLICY, "execute"),
    ("G2", "local edit", CONTROL_AUTHORITY, "수정"),
    ("G2", "local edit", CONTROL_AUTHORITY, "파일 쓰기"),
)

REPORT_ONLY_MARKERS = {
    "daily-ai-brief",
    "daily_ai_ops_brief",
    "report_only_until_gate_allows_side_effects",
    "report_only_until_owner_or_policy_gate_allows_external_side_effects",
}


def authority_value(tier: str) -> int:
    return AUTHORITY_ORDER.get(tier, 0)


def _highest_tier(tiers: Iterable[str]) -> str:
    return max(tiers, key=authority_value, default="G0")


def _risk_for_tier(tier: str) -> int:
    return {"G0": 5, "G1": 10, "G2": 35, "G3": 55, "G4": 80, "G5": 95}.get(tier, 20)


def _metadata_is_report_only(metadata: dict | None) -> bool:
    if not metadata:
        return False
    values = {str(v).strip().lower() for v in metadata.values() if isinstance(v, str)}
    return bool(values & REPORT_ONLY_MARKERS)


def _matches_text_rule(lowered_text: str, pattern: str) -> bool:
    lowered_pattern = pattern.lower()
    if lowered_pattern in {
        "prod",
        "production",
        "deploy",
        "credential",
        "secret",
        "trade",
        "execute",
    }:
        return re.search(rf"\b{re.escape(lowered_pattern)}\b", lowered_text) is not None
    return lowered_pattern in lowered_text


def evaluate_text_execution_gate(text: str, metadata: dict | None = None) -> GateDecision:
    """Map a natural-language request to a G0-G5 execution gate."""
    if _metadata_is_report_only(metadata):
        return GateDecision(
            authority_tier="G0",
            risk_score=5,
            action="report-only automation",
            requires_approval=False,
            allowed=True,
            controls=[CONTROL_AUTHORITY],
            reasons=["report_only_metadata"],
        )

    lowered = (text or "").lower()
    matched: list[str] = []
    tiers: list[str] = []
    controls = {CONTROL_AUTHORITY}
    actions: list[str] = []

    for tier, action, control, pattern in TEXT_RULES:
        if _matches_text_rule(lowered, pattern):
            matched.append(pattern)
            tiers.append(tier)
            controls.add(control)
            if action not in actions:
                actions.append(action)

    if not tiers:
        return GateDecision(
            authority_tier="G1",
            risk_score=10,
            action="safe inspection or conversation",
            requires_approval=False,
            allowed=True,
            controls=[CONTROL_AUTHORITY],
            reasons=["no_high_risk_pattern"],
        )

    tier = _highest_tier(tiers)
    requires_approval = authority_value(tier) >= AUTHORITY_ORDER["G4"]
    if requires_approval:
        controls.add(CONTROL_EXTERNAL_APPROVAL)
    return GateDecision(
        authority_tier=tier,
        risk_score=_risk_for_tier(tier),
        action=", ".join(actions[:3]),
        requires_approval=requires_approval,
        allowed=not requires_approval,
        controls=sorted(controls),
        reasons=["matched_text_rule"],
        matched=matched,
    )


def get_tool_policy(tool_name: str) -> ToolPolicy:
    if tool_name in TOOL_POLICIES:
        return TOOL_POLICIES[tool_name]
    if any(tool_name.startswith(prefix) for prefix in READONLY_TOOL_PREFIXES):
        return READONLY_TOOL_POLICY
    return ToolPolicy(
        authority_tier="G2",
        action="registered local tool",
        controls=(CONTROL_AUTHORITY, CONTROL_TOOL_POLICY),
    )


def evaluate_tool_execution_gate(tool_name: str, *, owner_approved: bool = False) -> GateDecision:
    """Map a tool invocation to a G0-G5 execution gate."""
    policy = get_tool_policy(tool_name)
    requires_approval = (
        policy.external_side_effect
        or authority_value(policy.authority_tier) >= AUTHORITY_ORDER["G4"]
    )
    allowed = not requires_approval or owner_approved
    controls = set(policy.controls)
    controls.add(CONTROL_AUTHORITY)
    controls.add(CONTROL_TOOL_POLICY)
    if requires_approval:
        controls.add(CONTROL_EXTERNAL_APPROVAL)
    return GateDecision(
        authority_tier=policy.authority_tier,
        risk_score=_risk_for_tier(policy.authority_tier),
        action=policy.action,
        requires_approval=requires_approval,
        allowed=allowed,
        controls=sorted(controls),
        reasons=["tool_policy", "owner_approved" if owner_approved else "owner_not_approved"],
        matched=[tool_name],
    )


def filter_tools_for_gate(
    tools: list[Callable],
    *,
    owner_approved: bool = False,
    max_unapproved_tier: str = "G3",
) -> tuple[list[Callable], list[GateDecision]]:
    """Return tools allowed for the current request and decisions for removed tools."""
    allowed: list[Callable] = []
    blocked: list[GateDecision] = []
    ceiling = authority_value(max_unapproved_tier)
    for tool in tools:
        name = getattr(tool, "__name__", str(tool))
        decision = evaluate_tool_execution_gate(name, owner_approved=owner_approved)
        if owner_approved or (decision.allowed and authority_value(decision.authority_tier) <= ceiling):
            allowed.append(tool)
        else:
            blocked.append(decision)
    return allowed, blocked
