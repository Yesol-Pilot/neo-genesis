# -*- coding: utf-8 -*-
"""
소라(Sora) 프롬프트 빌더 — Phase 1-3

시스템 프롬프트를 정적(static) + 동적(dynamic) 2단계로 구성합니다.
정적 부분은 부팅 시 1회 캐싱, 동적 부분은 매 메시지마다 갱신합니다.
"""
import json
import logging
import re
from pathlib import Path
from typing import Optional

from src.core.time_context import build_time_context_block

logger = logging.getLogger("neo.jarvis")

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent


class PromptBuilder:
    """시스템 프롬프트 2단계 구성"""

    def __init__(self, bible_loader=None, retriever=None, memory=None):
        self.bible = bible_loader
        self.retriever = retriever
        self.memory = memory
        self._static_cache: Optional[str] = None

    def build_static(self) -> str:
        """부팅 시 1회 구성 (변하지 않는 부분)"""
        if self._static_cache:
            return self._static_cache

        parts = []

        # 0) BIBLE 헌법
        if self.bible:
            try:
                constitution = self.bible.get_constitution()
                if constitution:
                    parts.append(constitution)
            except Exception as e:
                logger.warning(f"[PromptBuilder] BIBLE 헌법 로드 실패: {e}")

        # 1) Persona + 원칙 + 도구 가이드 (sora_context.json)
        ctx = self._load_sora_context()
        persona = ctx.get("persona", {})
        principles = ctx.get("principles", [])
        tool_guides = ctx.get("tool_guides", {})
        pc_info = ctx.get("pc_info", {})

        parts.append(f"""당신은 {persona.get('name', '소라')}({persona.get('name_en', 'Sora')}) — NEO GENESIS의 AI 비서입니다.

## 정체성
- 이름: {persona.get('name', '소라')} ({persona.get('name_en', 'Sora')})
- 나이: {persona.get('age', 24)}세 {persona.get('gender', '여성')}
- MBTI: {persona.get('mbti', 'ENTJ')} — {persona.get('personality', '')}
- 주인: {persona.get('owner_name', '')} ({persona.get('owner_name_en', '')}) — NEO GENESIS 대표. "{persona.get('owner_title', '대표님')}"이라고 부름
- 통신: {persona.get('channel', '')}""")

        tone_lines = persona.get("tone", [])
        if tone_lines:
            parts.append("## 성격과 말투\n" + "\n".join(f"- {t}" for t in tone_lines))

        if principles:
            numbered = "\n".join(f"{i+1}. {p}" for i, p in enumerate(principles))
            parts.append(f"## 핵심 원칙\n{numbered}")

        if tool_guides:
            guide_lines = "\n".join(f"- **{k}**: {v}" for k, v in tool_guides.items())
            parts.append(f"## 도구 사용 가이드\n{guide_lines}")

        # 2) PC 정보
        parts.append(f"## PC 정보\nOS: {pc_info.get('os', 'Windows 11')} | 루트: {PROJECT_ROOT} | 셸: {pc_info.get('shell', 'PowerShell')}")

        # 3) 환경변수 상태
        env_lines = []
        env_file = PROJECT_ROOT / ".env"
        if env_file.exists():
            for line in env_file.read_text(encoding="utf-8").splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    key, val = line.split("=", 1)
                    status = "✅" if val.strip() else "❌"
                    env_lines.append(f"  {key}: {status}")
        if env_lines:
            parts.append(f"## 환경변수\n{chr(10).join(env_lines)}")

        self._static_cache = "\n\n".join(parts)
        return self._static_cache

    def build_dynamic(self, user_query: str = "") -> str:
        """매 메시지마다 구성 (변하는 부분)"""
        parts = [f"## 현재 시간 기준\n{build_time_context_block()}"]

        # 동적 BIBLE 섹션
        if self.bible and user_query:
            try:
                relevant = self.bible.get_relevant_sections(user_query)
                if relevant:
                    parts.append(f"## 관련 정책/스킬\n{relevant}")
            except Exception as e:
                logger.warning(f"[PromptBuilder] 동적 BIBLE 실패: {e}")

        # KI 요약
        ctx = self._load_sora_context()
        ki_summary = self._load_ki_summaries(ctx)
        if ki_summary:
            parts.append(f"## 학습된 지식 (KI)\n{ki_summary}")

        # 그래프 메모리 (사용자 프로필)
        shared_brain_summary = self._load_shared_brain_summary(ctx)
        if shared_brain_summary:
            parts.append(f"## Shared Brain Live Context\n{shared_brain_summary}")

        if self.retriever:
            try:
                profile = self.retriever.get_user_profile()
                if profile:
                    parts.append(f"## 대표님에 대해 아는 것\n{profile}")
            except Exception:
                pass

        # 기억한 사실
        if self.memory:
            try:
                facts = self.memory.get_facts_text()
                if facts and facts.strip():
                    parts.append(f"## 기억한 사실\n{facts}")
            except Exception:
                pass

        # 헬스 상태
        hf = PROJECT_ROOT / "src" / "core" / "data" / "health_state.json"
        if hf.exists():
            try:
                health = json.loads(hf.read_text(encoding="utf-8"))
                parts.append(f"## 시스템 상태\n{json.dumps(health, ensure_ascii=False, indent=2)[:800]}")
            except Exception:
                pass

        return "\n\n".join(parts)

    def build_full(self, user_query: str = "") -> str:
        """static + dynamic 합성"""
        static = self.build_static()
        dynamic = self.build_dynamic(user_query)
        if dynamic:
            return f"{static}\n\n{dynamic}"
        return static

    def invalidate_cache(self):
        """정적 캐시 무효화 (설정 변경 시)"""
        self._static_cache = None

    # ── 내부 유틸 ──

    @staticmethod
    def _load_sora_context() -> dict:
        """sora_context.json 로드"""
        ctx_file = PROJECT_ROOT / "src" / "core" / "data" / "sora_context.json"
        if ctx_file.exists():
            try:
                return json.loads(ctx_file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {}

    @staticmethod
    def _resolve_ks_path(raw: str) -> Path:
        """knowledge_sources 경로를 PROJECT_ROOT 기준으로 resolve.

        절대경로이면 그대로, 상대경로이면 PROJECT_ROOT 기준으로 변환합니다.
        """
        p = Path(raw)
        if p.is_absolute():
            return p
        return PROJECT_ROOT / p

    @staticmethod
    def _load_ki_summaries(ctx: dict) -> str:
        """KI 폴더 순회 → overview.md 요약 수집"""
        ki_dir_str = ctx.get("knowledge_sources", {}).get("ki_dir", "")
        if not ki_dir_str:
            return ""

        ki_dir = PromptBuilder._resolve_ks_path(ki_dir_str)
        if not ki_dir.exists():
            return ""

        summaries = []
        try:
            for overview in sorted(ki_dir.glob("*/overview.md"))[:20]:
                text = overview.read_text(encoding="utf-8", errors="ignore")
                # 첫 5줄만
                first_lines = "\n".join(text.splitlines()[:5])
                folder_name = overview.parent.name
                summaries.append(f"### {folder_name}\n{first_lines}")
        except Exception:
            pass

        return "\n\n".join(summaries)

    @staticmethod
    def _load_shared_brain_summary(ctx: dict) -> str:
        knowledge_sources = ctx.get("knowledge_sources", {})
        _raw = knowledge_sources.get("shared_brain_dir") or ".agent/shared-brain"
        shared_root = PromptBuilder._resolve_ks_path(_raw)
        if not shared_root.exists():
            return ""

        sections = []
        status_path = shared_root / "status.json"
        if status_path.exists():
            try:
                payload = json.loads(status_path.read_text(encoding="utf-8"))
                shared = payload.get("sharedContext", {})
                agents = payload.get("agents", {})
                tailscale = payload.get("infrastructure", {}).get("tailscale", {})
                lines = []
                if shared.get("status"):
                    lines.append(f"- shared status: {shared['status']}")
                if shared.get("ssotRevision"):
                    lines.append(f"- ssot revision: {shared['ssotRevision']}")
                if agents:
                    states = []
                    for name in ("codex", "claude-code", "antigravity", "sora"):
                        if name in agents:
                            states.append(f"{name}={agents[name].get('status', 'unknown')}")
                    if states:
                        lines.append("- agents: " + ", ".join(states))
                if tailscale.get("online"):
                    lines.append("- online devices: " + ", ".join(tailscale.get("online", [])[:6]))
                if lines:
                    sections.append("### live status\n" + "\n".join(lines))
            except Exception:
                pass

        for filename, title in (
            ("ai-ops-brief-inbox.md", "ai ops brief inbox"),
            ("active-tasks.md", "active tasks"),
            ("handoff.md", "handoff"),
            ("cross-agent-review.md", "cross-agent review"),
        ):
            summary = PromptBuilder._summarize_markdown_items(shared_root / filename)
            if summary:
                sections.append(f"### {title}\n{summary}")

        return "\n\n".join(sections[:5])

    @staticmethod
    def _summarize_markdown_items(path: Path, max_items: int = 6) -> str:
        if not path.exists():
            return ""

        try:
            lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
        except Exception:
            return ""

        items = []
        in_code_block = False
        for raw_line in lines:
            stripped = raw_line.strip()
            if stripped.startswith("```"):
                in_code_block = not in_code_block
                continue
            if in_code_block or not stripped:
                continue
            if stripped.startswith((">", "#", "Template:", "Rules:")):
                continue
            if stripped.lower() in {"- [ ] none", "- [x] none"}:
                continue
            if stripped.startswith(("- [ ]", "- [x]", "- ")) or re.match(r"^\d+\.\s", stripped):
                items.append(re.sub(r"\s+", " ", stripped))
            if len(items) >= max_items:
                break

        return "\n".join(items)
