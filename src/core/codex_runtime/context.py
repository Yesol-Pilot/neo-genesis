# -*- coding: utf-8 -*-
"""Build a stable Codex prompt bundle for Sora requests."""

from __future__ import annotations

import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
CONTEXT_PATH = PROJECT_ROOT / "src" / "core" / "data" / "sora_context.json"
OWNER_PROFILE_PATH = PROJECT_ROOT / ".agent" / "knowledge" / "OWNER_PROFILE.md"
SHARED_MEMORY_PATH = PROJECT_ROOT / ".agent" / "knowledge" / "AGENT_SHARED_MEMORY.md"


def _read_text(path: Path, limit: int) -> str:
    if not path.exists():
        return ""
    text = path.read_text(encoding="utf-8", errors="ignore").strip()
    return text[:limit]


def _load_sora_context() -> dict:
    if not CONTEXT_PATH.exists():
        return {}
    return json.loads(CONTEXT_PATH.read_text(encoding="utf-8"))


def _format_identity_block(context: dict) -> str:
    persona = context.get("persona", {})
    principles = context.get("principles", [])

    lines = [
        f"- 이름: {persona.get('name_en') or persona.get('name') or 'Sora'}",
        f"- 역할: {persona.get('identity', '')[:400]}",
        f"- 오너: {persona.get('owner_name_en') or persona.get('owner_name') or ''}",
        f"- 채널: {persona.get('channel', '')}",
    ]
    if principles:
        lines.append("- 원칙:")
        for item in principles[:8]:
            lines.append(f"  - {str(item)[:180]}")
    return "\n".join(line for line in lines if line.strip())


def _format_recent_context(session_id: str) -> str:
    try:
        from src.core.storage.supabase_store import get_supabase_store

        rows = get_supabase_store().get_recent_conversations(n=8, session_id=session_id)
    except Exception:
        rows = []

    if not rows:
        return ""

    lines = []
    for row in rows[-8:]:
        role = row.get("role", "unknown")
        content = str(row.get("content", "")).replace("\n", " ").strip()
        if content:
            lines.append(f"- {role}: {content[:220]}")
    return "\n".join(lines)


def _format_rag_hits(query: str) -> str:
    try:
        from src.core.rag_engine import get_rag_engine

        hits = get_rag_engine().search(query, n_results=5)
    except Exception:
        hits = []

    if not hits:
        return ""

    lines = []
    for hit in hits[:5]:
        source = hit.get("source", "")
        section = hit.get("section", "")
        text = str(hit.get("text", "")).replace("\n", " ").strip()
        lines.append(f"- source: {source}")
        if section:
            lines.append(f"  section: {section}")
        lines.append(f"  excerpt: {text[:320]}")
    return "\n".join(lines)


def build_codex_prompt_bundle(
    *,
    user_text: str,
    session_id: str,
    file_path: str = "",
    metadata: dict | None = None,
) -> str:
    context = _load_sora_context()
    identity = _format_identity_block(context)
    owner_profile = _read_text(OWNER_PROFILE_PATH, limit=4000)
    shared_memory = _read_text(SHARED_MEMORY_PATH, limit=4000)
    recent_context = _format_recent_context(session_id)
    rag_hits = _format_rag_hits(user_text)

    parts = [
        "당신은 소라(Sora)로 동작하는 Codex 실행 엔진이다.",
        "반드시 한국어로 답하고, 결론 먼저, 직접적이고 사실 중심으로 보고한다.",
        "사용자 요청을 우선 수행하되, 위험한 작업은 이미 상위 ConfirmGate에서 승인되었을 때만 진행한다고 가정한다.",
        "내부 JSON, 원시 도구 결과, 스택트레이스를 사용자에게 그대로 노출하지 않는다.",
        "",
        "[소라 아이덴티티]",
        identity,
        "",
        "[오너 프로필]",
        owner_profile,
        "",
        "[공유 장기기억]",
        shared_memory,
    ]

    if recent_context:
        parts.extend(["", "[최근 세션 맥락]", recent_context])

    if rag_hits:
        parts.extend(["", "[관련 RAG 검색 결과]", rag_hits])

    if file_path:
        parts.extend(["", "[첨부 파일 경로]", file_path])

    if metadata:
        safe_metadata = json.dumps(metadata, ensure_ascii=False, default=str)[:1000]
        parts.extend(["", "[요청 메타데이터]", safe_metadata])

    parts.extend(
        [
            "",
            "[사용자 요청]",
            user_text.strip(),
            "",
            "[응답 규칙]",
            "- 결과가 있으면 결과부터 보고한다.",
            "- 불확실하면 무엇이 불확실한지 짧게 밝힌다.",
            "- 실행한 작업이 있으면 핵심만 1~3줄로 정리한다.",
            "- 다음 액션이 필요할 때만 짧게 제안한다.",
        ]
    )

    return "\n".join(part for part in parts if part is not None)
