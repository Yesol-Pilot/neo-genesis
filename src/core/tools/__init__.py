# -*- coding: utf-8 -*-
"""
소라(Sora) 도구 자동 등록 — Phase 1-1 + Phase 2A + God Mode

각 서브모듈의 TOOLS 리스트를 자동 수집 → ToolRegistry 건강 검사 → ALL_TOOLS 구성.
파손된 도구(환경변수 미설정, docstring 없음 등)는 자동 제외됩니다.
"""
import logging
from importlib import import_module

logger = logging.getLogger("neo.tools")

def _load_tools(module_name: str) -> list:
    try:
        module = import_module(f"{__name__}.{module_name}")
        return list(getattr(module, "TOOLS", []))
    except Exception as e:
        logger.warning(f"[Tools] {module_name} load failed: {e}")
        return []


_system = _load_tools("system_tools")
_memory = _load_tools("memory_tools")
_deploy = _load_tools("deploy_tools")
_media = _load_tools("media_tools")
_skill = _load_tools("skill_tools")
_web = _load_tools("web_tools")
_security = _load_tools("security_tools")
_governance = _load_tools("governance_tools")
_planner = _load_tools("planner_tools")
# 2026-05-29: 분석 도구 (GA4 SBU 트래픽 + PostHog DAU) — owner daily 사용
try:
    from .analytics_tools import ANALYTICS_TOOLS as _analytics
except Exception as e:
    logger.warning(f"[Tools] analytics_tools 로드 실패: {e}")
    _analytics = []

# Phase 3: 외부 서비스 연동 도구 (안전한 import)
try:
    from .calendar_tools import TOOLS as _calendar
except Exception as e:
    logger.warning(f"[Tools] calendar_tools 로드 실패: {e}")
    _calendar = []
try:
    from .comfyui_tools import TOOLS as _comfyui
except Exception as e:
    logger.warning(f"[Tools] comfyui_tools 로드 실패: {e}")
    _comfyui = []
try:
    from .gmail_tools import TOOLS as _gmail
except Exception as e:
    logger.warning(f"[Tools] gmail_tools 로드 실패: {e}")
    _gmail = []
try:
    from .notion_tools import TOOLS as _notion
except Exception as e:
    logger.warning(f"[Tools] notion_tools 로드 실패: {e}")
    _notion = []

# God Mode 도구 (안전한 import — 미구현 시 빈 리스트)
try:
    from .healer_tools import TOOLS as _healer
except ImportError:
    _healer = []
try:
    from .executor_tools import TOOLS as _executor
except ImportError:
    _executor = []
try:
    from .agent_tools import TOOLS as _agent
except ImportError:
    _agent = []

# 2026-05-12 P0 fix: ALL_TOOLS 순서 owner-relevant 우선으로 reorder.
# 원인: 직전 순서 (_system 첫번째) 가 get_today_schedule(#3, SBU 데몬 스케줄) 을 attention 우선에 배치.
# owner 가 "오늘 일정" 물으면 Gemini 가 #3 데몬 스케줄 도구 보고 calendar_today(#40) 못 찾음.
# 결과: tool 호출 없이 "오늘 일정 없어요" hallucination. owner 가 직접 본 bug.
# 새 순서: owner-relevant (calendar/gmail/memory) → owner-domain (media/skill) → system → ops.
_raw_tools = (
    _calendar     # 일정 (owner 직접 쓰는 #1)
    + _gmail      # 메일 (owner 직접 쓰는 #2)
    + _memory     # RAG/회상 (owner 직접 쓰는 #3)
    + _analytics  # GA4 트래픽 + PostHog DAU (owner daily 방문자 조회)
    + _media      # 이미지 생성/처리
    + _skill      # skill 호출
    + _system     # PC ops (run_pc_command 등, owner 보다는 시스템)
    + _deploy     # 배포
    + _web        # 웹 크롤
    + _security   # 보안 분석
    + _governance # 거버넌스
    + _planner    # 작업 계획
    + _healer     # 자가 치유
    + _executor   # 폴리글랏 실행
    + _agent      # 멀티 에이전트
    + _notion     # Notion (대부분 미설정)
    + _comfyui    # ComfyUI 이미지
)

# ToolRegistry 건강 검사 — 파손 도구 자동 제외
try:
    from .registry import ToolRegistry
    _registry = ToolRegistry()
    ALL_TOOLS, BROKEN_TOOLS = _registry.check_all(_raw_tools)
except Exception as e:
    logger.warning(f"[Tools] ToolRegistry 초기화 실패, 전체 도구 사용: {e}")
    ALL_TOOLS = _raw_tools
    BROKEN_TOOLS = []

__all__ = ["ALL_TOOLS", "BROKEN_TOOLS"]
