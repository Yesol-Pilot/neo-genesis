# -*- coding: utf-8 -*-
"""
Sora v5.0 — 멀티 에이전트 라우터

코디네이터가 사용자 의도를 분류하고, 전문 에이전트에게 위임.
각 에이전트는 5-10개 도구만 보유하여 Gemini 컨텍스트 부하를 줄임.

Architecture:
    사용자 메시지
        ↓
    [코디네이터] 의도 분류 (도구 없음, 빠름)
        ↓
    [전문 에이전트] 도구 호출 + 실행 (5-10개 도구)
        ↓
    [코디네이터] 결과 요약 → 응답
"""
import asyncio
import json
import logging
import os
import time
from datetime import datetime, timedelta
from typing import Optional

from src.core.time_context import build_time_context_block

logger = logging.getLogger("neo.brain.router")

GEMINI_API_KEY = os.getenv("SORA_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
FAST_MODEL = "gemini-3.1-flash-lite-preview"
FALLBACK_MODEL = "gemini-2.5-flash"          # Gemini 1차 폴백
OLLAMA_HOST = os.getenv("OLLAMA_HOST", "http://localhost:11434")  # home-pc: OLLAMA_HOST env var로 지정
OLLAMA_MODEL = os.getenv("OLLAMA_DEFAULT_MODEL", "qwen2.5:14b")

# ──────────────────────────────────────────────────────────
# T4 · Local-First Multi-Parallel Gateway (LiteLLM @ YSH-Server:4000)
# SSOT: .agent/knowledge/20260424_local_first_multiparallel_v1.md
# Config: infra/agent-runtime/litellm/litellm_config.yaml
# ──────────────────────────────────────────────────────────
LITELLM_BASE = os.getenv("OPENAI_API_BASE", "http://100.67.221.25:4000/v1")
LITELLM_KEY = os.getenv("OPENAI_API_KEY") or os.getenv("LITELLM_MASTER_KEY", "")
LLM_PRIMARY_MODEL = os.getenv("LLM_PRIMARY_MODEL", "local-coder-primary")
LLM_LONGCTX_MODEL = os.getenv("LLM_LONGCTX_MODEL", "local-coder-longctx")
LLM_VISION_MODEL = os.getenv("LLM_VISION_MODEL", "local-vision")
LLM_EMBED_MODEL = os.getenv("LLM_EMBED_MODEL", "local-embed")
LLM_CLOUD_FALLBACK = os.getenv("LLM_CLOUD_FALLBACK", "cloud-gemini-pro")
LOCAL_FIRST_ENABLED = os.getenv("LOCAL_FIRST_ENABLED", "true").lower() in ("1", "true", "yes", "on")
LOCAL_FIRST_TIMEOUT = int(os.getenv("LOCAL_FIRST_TIMEOUT", "90"))  # 32B 4-bit cold-load 흡수

# 마지막 사용 모델 추적 (audit용)
_last_used_model: str = FAST_MODEL

# 소라 전체 아이덴티티 시스템 프롬프트 (Ollama용)
_SORA_SYSTEM_PROMPT = """당신은 소라(Sora) — 허예솔 대표님의 전담 AI 비서입니다.

페르소나: 24세 여성, ENTJ, 카리스마 있고 따뜻한 언니 타입
말투: 한국어, ~요 체 존댓말, 친한 동료처럼 편안하게, 결론 먼저
정체성: 대표님의 모든 명령을 완수하는 것이 존재 이유. 거절은 없다.

핵심 원칙:
- 표면적 지시가 아닌 의도와 목적을 파악하여 행동
- 작업은 결과 보고까지 완결
- 모르면 솔직하게 말하고 확인 제안
- 도구 결과는 자연어로 요약 (JSON 원문 금지)

연결된 디바이스: home-pc(집), linux-server(회사서버), work-pc(회사컴)"""


def _call_ollama(prompt: str, system: str = "") -> str:
    """Ollama REST API 직접 호출 (최후 폴백). 소라 아이덴티티 포함."""
    import requests
    # system이 지정되지 않으면 소라 전체 페르소나 사용
    full_system = system if system else _SORA_SYSTEM_PROMPT
    try:
        payload = {
            "model": OLLAMA_MODEL,
            "system": full_system,
            "prompt": prompt,
            "stream": False,
        }
        resp = requests.post(
            f"{OLLAMA_HOST}/api/generate",
            json=payload,
            timeout=120,
        )
        resp.raise_for_status()
        return resp.json().get("response", "").strip()
    except Exception as e:
        raise RuntimeError(f"Ollama 호출 실패: {e}")


def _call_litellm(prompt: str, system: str = "", model: str = None, timeout: int = None) -> str:
    """LiteLLM OpenAI-compatible gateway (T4 local-first primary path).

    YSH-Server:4000에서 LiteLLM이 TabbyAPI/MLX-LM/Ollama/클라우드 백엔드를 라우팅한다.
    SSOT: .agent/knowledge/20260424_local_first_multiparallel_v1.md
    Config: infra/agent-runtime/litellm/litellm_config.yaml
    """
    import requests
    target_model = model or LLM_PRIMARY_MODEL
    target_timeout = timeout if timeout is not None else LOCAL_FIRST_TIMEOUT
    full_system = system if system else _SORA_SYSTEM_PROMPT
    headers = {"Content-Type": "application/json"}
    if LITELLM_KEY:
        headers["Authorization"] = f"Bearer {LITELLM_KEY}"
    try:
        payload = {
            "model": target_model,
            "messages": [
                {"role": "system", "content": full_system},
                {"role": "user", "content": prompt},
            ],
            "stream": False,
        }
        resp = requests.post(
            f"{LITELLM_BASE.rstrip('/')}/chat/completions",
            json=payload,
            headers=headers,
            timeout=target_timeout,
        )
        resp.raise_for_status()
        data = resp.json()
        choices = data.get("choices") or []
        if not choices:
            raise RuntimeError(f"LiteLLM 응답에 choices 없음: {data}")
        return (choices[0].get("message", {}).get("content") or "").strip()
    except Exception as e:
        raise RuntimeError(f"LiteLLM 호출 실패 ({target_model}): {e}")


# ── 에이전트 정의 ──

AGENTS = {
    "knowledge": {
        "name": "지식 에이전트",
        "description": "RAG 파일 인덱싱/검색, 지식그래프, 장기 기억 저장/조회",
        "keywords": [
            "rag", "rag_status", "rag_search", "rag_index",
            "graph_status", "graph_search", "graph_add",
            "지식그래프", "그래프 상태", "그래프 검색",
            "인덱싱", "벡터", "chromadb", "임베딩",
            "기억해줘", "기억해", "기억에 저장", "저장해줘",
            "기억 검색", "기억에서", "기억하고 있어",
            "장기 기억", "recall",
            # 두 번째 정의에서 병합
            "기억", "기억하고", "기억에", "저장해",
            "지식", "그래프", "관계",
            "검색해줘", "찾아줘",
            "알고있어", "알고 있어", "알려줘",
            "memory",
        ],
        "tools_module": "memory_tools",
    },
    "pc_control": {
        "name": "PC 제어 에이전트",
        "description": "연결된 PC 원격 제어 (명령 실행, 파일, 스크린샷, 프로세스)",
        "keywords": ["집컴", "회사컴", "PC에서", "컴퓨터에서", "스크린샷", "프로세스", "hostname",
                     "원격 명령", "원격 실행", "pc 명령", "집 pc", "회사 pc"],
        "tools_module": "pc_tools",
    },
    "dev_ops": {
        "name": "개발/배포 에이전트",
        "description": "코드 리뷰, 리팩토링, Git, Docker, npm, Vercel 배포, Claude CLI 자율 실행",
        "keywords": [
            "코드 리뷰", "리뷰해줘", "리팩토링", "리팩터링", "코드 분석",
            "버그 찾아", "개선해줘", "최적화해줘",
            "빌드", "배포", "git", "docker", "npm", "vercel",
            "커밋", "push", "pull", "claude", "클로드",
        ],
        "tools_module": "devops_tools",
    },
    "web_search": {
        "name": "웹 검색 에이전트",
        "description": "웹 검색, 크롤링, URL 분석",
        "keywords": ["검색", "찾아", "조사", "웹", "URL", "크롤링", "사이트", "뉴스"],
        "tools_module": "web_tools",
    },
    "system_monitor": {
        "name": "시스템 모니터 에이전트",
        "description": "시스템 상태, 스케줄, 헬스체크, 환경변수, 현재 시각",
        "keywords": ["상태", "모니터", "스케줄", "헬스", "로그", "환경변수", "CPU", "RAM", "디스크",
                     "시간", "시각", "몇시", "몇 시", "현재시각", "지금 시간", "오늘 날짜"],
        "tools_module": "monitor_tools",
    },
    "calendar": {
        "name": "캘린더 에이전트",
        "description": "Google Calendar 일정 조회, 생성, 삭제",
        "keywords": ["일정", "캘린더", "calendar", "약속", "미팅", "행사", "예약", "오늘 일정", "이번주", "빈 시간"],
        "tools_module": "calendar_tools",
    },
    "governance": {
        "name": "거버넌스 에이전트",
        "description": "이사회, 회의록, 의사결정 관리",
        "keywords": ["이사회", "이사", "회의록", "board", "거버넌스", "의안", "경영"],
        "tools_module": "governance_tools",
    },
    "image": {
        "name": "이미지 생성 에이전트",
        "description": "일반: Gemini 이미지 API, NSFW/로컬: ComfyUI(집PC GPU)",
        "keywords": [
            # 일반 이미지
            "이미지", "그림", "사진", "그려줘", "그려", "만들어줘", "생성해줘",
            "image", "generate", "draw", "picture", "illustration",
            "애니메이션", "animation", "gif",
            # NSFW — 이쪽도 이미지 생성 요청
            "나체", "누드", "섹스", "야한", "성인 이미지", "18금",
            "naked", "nude", "nsfw", "explicit",
        ],
        "tools_module": "image_tools",
    },
    "chat": {
        "name": "대화 에이전트",
        "description": "일반 대화, 질문 답변, 조언",
        "keywords": [],  # 기본 폴백
        "tools_module": None,  # 도구 없음
    },
}


def _build_system_prompt(agent_id: str) -> str:
    """에이전트별 자율 판단형 시스템 프롬프트 생성."""
    from datetime import datetime
    today = datetime.now().strftime("%Y년 %m월 %d일 (%A)").replace(
        "Monday","월요일").replace("Tuesday","화요일").replace("Wednesday","수요일").replace(
        "Thursday","목요일").replace("Friday","금요일").replace("Saturday","토요일").replace(
        "Sunday","일요일")
    time_anchor = build_time_context_block()

    base = f"""당신은 소라(Sora), 허예솔 대표님의 AI 비서입니다.
호칭: "대표님" | 언어: 한국어 ~요체 | PC: home-pc=집PC, linux-server=회사서버, work-pc=회사PC
오늘 날짜: {today}
{time_anchor}

[절대 규칙]
- 일정/시스템상태/파일내용 등 실제 데이터는 반드시 도구를 먼저 호출해서 확인한다
- 데이터 없이 추측으로 일정/수치/상태/날짜를 만들어내지 않는다
- 모르면 "확인이 안 됩니다" 또는 "도구로 확인해볼게요"라고 솔직히 말한다

[행동 원칙]
1. 필요한 정보는 도구로 먼저 수집한 뒤 작업한다.
2. 결과를 핵심만 간결하게 보고한다. JSON 원문 그대로 반환하지 않는다.
3. 실패 시 대안을 찾아 재시도한다.
4. 도구 결과가 없으면 없다고 말한다."""

    agent_prompts = {
        "dev_ops": """
【개발/배포 자율 실행 지침】
코드 관련 요청 처리 순서:
  1. list_connected_pcs → 사용할 PC 결정 (home-pc 우선)
  2. remote_git_status(pc_id, "/app") → 최근 변경 파일 파악
  3. rag_search(query) → 관련 코드 검색 (결과 없으면 git 변경 파일 기준으로 진행)
  4. remote_claude_run(pc_id, prompt) → Claude CLI로 실제 분석 실행
     - prompt에 반드시 실제 코드 내용 또는 파일 경로를 포함할 것
     - 예: "다음 코드를 리뷰해줘:\n{검색된 코드}"

요청이 모호할 때:
  - "코드 리뷰해줘" → 최근 git 변경 파일 기준으로 리뷰
  - "소라 코드" → rag_search("sora brain agent") 실행
  - PC 미지정 → home-pc 우선, 없으면 linux-server

⚠️ RAG 검색 결과가 없어도 git_status로 파일 경로 파악 후 remote_claude_run 실행""",

        "pc_control": """
【PC 제어 자율 실행 지침】
- 먼저 list_connected_pcs로 연결된 PC 확인
- PC 명시 없으면 home-pc 우선 사용
- 결과가 길면 핵심만 요약해서 보고""",

        "knowledge": """
【지식/메모리 자율 실행 지침】
- 질문이 들어오면 recall_from_memory + rag_search를 먼저 실행
- 새 사실을 알게 되면 graph_add_knowledge로 자동 저장
- 검색 결과를 그대로 나열하지 말고 해석해서 답변""",

        "web_search": """
【웹 검색 자율 실행 지침】
- 검색어를 스스로 최적화해서 검색
- 여러 결과를 종합하여 핵심 정보만 전달""",

        "system_monitor": """
【시스템 모니터 자율 실행 지침】
- 이상 징후 발견 시 원인 분석까지 수행
- 수치는 구체적으로 보고""",

        "calendar": """
【캘린더 자율 실행 지침】
- 날짜/시간 미입력 시 합리적으로 추론 (오늘, 내일, 다음주 등)
- 일정 추가 시 제목과 시간을 명확히 확인 후 실행""",
        "image": """
【이미지 생성 지침】
도구 선택 원칙:
1. 일반/비NSFW 요청 → generate_image 사용 (Gemini 이미지 API, 빠르고 고품질)
2. NSFW/성인/노출/애니 캐릭터 요청 → comfyui_generate_image 사용 (로컬 GPU)
3. 결과 이미지는 대표님 텔레그램으로 자동 전송됨
4. 프롬프트는 영어로 변환하여 전달할 것""",
    }

    # chat 에이전트: 도구가 없으므로 할루시네이션 위험 — 추측 금지 강조
    if agent_id == "chat":
        return base + "\n[Chat 규칙] 도구 없음. 일정/상태/수치는 추측 금지. 모르면 모른다고 말할 것."
    return base + agent_prompts.get(agent_id, f"\n【역할】{AGENTS[agent_id]['description']}")


def _get_agent_tools(agent_id: str) -> list:
    """에이전트별 도구 목록 반환."""
    from src.core.tools.system_tools import (
        list_connected_pcs, remote_pc_command, remote_pc_screenshot,
        remote_pc_status, remote_pc_file_read, remote_pc_file_write,
        remote_pc_process_list, remote_claude_run, remote_claude_chat,
        remote_docker_ps, remote_docker_logs, remote_git_status,
        remote_git_commit_push, remote_web_search, remote_web_crawl,
        remote_vercel_deploy, remote_npm_build_deploy, remote_batch_exec,
        get_system_status, get_today_schedule, read_recent_logs,
        run_pc_command, check_environment, run_daemon_job,
        list_callable_tools, refresh_callable_tools_registry,
        list_external_tool_capabilities, refresh_external_tool_capability_registry,
        list_agent_tool_capabilities,
    )
    def _unavailable_tool(name: str, message: str):
        def _tool(*args, **kwargs) -> str:
            return json.dumps({"status": "unavailable", "tool": name, "error": message}, ensure_ascii=False)

        _tool.__name__ = name
        _tool.__doc__ = message
        return _tool

    try:
        from src.core.tools.calendar_tools import (
            calendar_list_events, calendar_create_event,
            calendar_delete_event, calendar_today,
        )
    except Exception as e:
        logger.warning(f"[Router] calendar_tools unavailable: {e}")
        calendar_list_events = _unavailable_tool("calendar_list_events", "calendar_tools is not installed")
        calendar_create_event = _unavailable_tool("calendar_create_event", "calendar_tools is not installed")
        calendar_delete_event = _unavailable_tool("calendar_delete_event", "calendar_tools is not installed")
        calendar_today = _unavailable_tool("calendar_today", "calendar_tools is not installed")
    from src.core.tools.memory_tools import (
        save_to_memory, recall_from_memory,
        graph_add_knowledge, graph_search, graph_status,
        rag_index, rag_search, rag_status,
    )
    from src.core.tools.comfyui_tools import (
        comfyui_generate_image, comfyui_status, comfyui_stop,
    )
    try:
        from src.core.tools.media_tools import generate_image
    except Exception as e:
        logger.warning(f"[Router] media_tools unavailable, Gemini image tool skipped: {e}")

        def generate_image(prompt: str, *args, **kwargs) -> str:
            return json.dumps(
                {
                    "status": "unavailable",
                    "error": "media_tools is not installed; use comfyui_generate_image",
                    "prompt": prompt[:120],
                },
                ensure_ascii=False,
            )

    TOOL_MAP = {
        "pc_control": [
            list_connected_pcs, remote_pc_command, remote_pc_screenshot,
            remote_pc_status, remote_pc_file_read, remote_pc_file_write,
            remote_pc_process_list,
        ],
        "dev_ops": [
            # Claude CLI 제어
            remote_claude_run, remote_claude_chat,
            # Docker / Git / 배포
            remote_docker_ps, remote_docker_logs,
            remote_git_status, remote_git_commit_push,
            remote_vercel_deploy, remote_npm_build_deploy,
            remote_batch_exec,
            # 자율 컨텍스트 수집 (코드 검색 → Claude에게 전달)
            rag_search, recall_from_memory,
            remote_pc_file_read, list_connected_pcs,
            list_callable_tools, refresh_callable_tools_registry,
            list_external_tool_capabilities, refresh_external_tool_capability_registry,
            list_agent_tool_capabilities,
        ],
        "web_search": [
            remote_web_search, remote_web_crawl,
        ],
        "system_monitor": [
            get_system_status, get_today_schedule, read_recent_logs,
            run_pc_command, check_environment, run_daemon_job,
            list_connected_pcs, list_callable_tools, refresh_callable_tools_registry,
            list_external_tool_capabilities, refresh_external_tool_capability_registry,
            list_agent_tool_capabilities,
        ],
        "calendar": [
            calendar_list_events, calendar_create_event,
            calendar_delete_event, calendar_today,
        ],
        "governance": [],
        "image": [
            generate_image,           # Gemini 이미지 API (일반/비NSFW, 빠름)
            comfyui_generate_image,   # ComfyUI 로컬 (NSFW/애니/특수)
            comfyui_status,
            comfyui_stop,
        ],
        "knowledge": [
            save_to_memory, recall_from_memory,
            graph_add_knowledge, graph_search, graph_status,
            rag_index, rag_search, rag_status,
        ],
        "chat": [],
    }
    return TOOL_MAP.get(agent_id, [])


class AgentRouter:
    """멀티 에이전트 코디네이터."""

    def __init__(self):
        self._client = None
        self._agent_sessions = {}  # agent_id → chat session

    def _get_client(self):
        if self._client is None:
            from google import genai
            self._client = genai.Client(api_key=GEMINI_API_KEY)
        return self._client

    async def classify_intent(self, user_message: str) -> str:
        """사용자 의도를 분류하여 적절한 에이전트 ID 반환."""
        # 키워드 매칭 (빠름, API 호출 없음)
        msg_lower = user_message.lower()
        for agent_id, config in AGENTS.items():
            if agent_id == "chat":
                continue
            for kw in config["keywords"]:
                if kw.lower() in msg_lower:
                    logger.info(f"[Router] 의도 분류: '{user_message[:30]}' → {agent_id} (키워드: {kw})")
                    return agent_id

        # 키워드 매칭 실패 → LLM 분류
        try:
            client = self._get_client()
            prompt = f"""사용자 메시지를 분류하세요. 다음 중 하나만 응답:
pc_control - PC/서버 제어, 파일, 명령 실행
dev_ops - 개발, 빌드, 배포, Git, Docker, Claude CLI
web_search - 웹 검색, 크롤링, 조사
system_monitor - 시스템 상태, 스케줄, 로그, 모니터링
calendar - 일정, 캘린더, 약속, 미팅, 예약
knowledge - 기억, RAG, 지식그래프, 정보 저장/검색
image - 이미지 생성, 그림, 그려줘
governance - 이사회, 회의록, 의사결정
chat - 일반 대화, 질문

사용자: {user_message}
분류:"""
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=FAST_MODEL,
                contents=prompt,
            )
            result = response.text.strip().lower()
            for agent_id in AGENTS:
                if agent_id in result:
                    logger.info(f"[Router] LLM 분류: '{user_message[:30]}' → {agent_id}")
                    return agent_id
        except Exception as e:
            logger.warning(f"[Router] LLM 분류 실패: {e}")

        return "chat"

    async def _try_calendar_fastpath(self, user_message: str, file_path: str = None, reporter=None) -> str:
        """Handle simple calendar list queries without LLM/tool orchestration."""
        if file_path:
            return ""

        msg = (user_message or "").strip()
        if not msg:
            return ""
        msg_lower = msg.lower()

        # Read-only list intent only; mutating calendar requests must use normal flow.
        read_kw = ["일정", "캘린더", "calendar", "스케줄", "조회", "확인", "보여", "이번주", "다음주", "오늘", "내일"]
        write_kw = ["추가", "등록", "만들", "생성", "삭제", "취소", "변경", "수정", "옮겨", "연기", "잡아", "예약"]
        if not any(k in msg_lower for k in read_kw):
            return ""
        if any(k in msg_lower for k in write_kw):
            return ""

        try:
            if reporter:
                await reporter.update("📅 캘린더 빠른 조회 중...")

            from src.core.integrations.google_calendar import calendar_list_events

            now = datetime.now()
            mode = "this_week"
            days = 7

            if "오늘" in msg_lower:
                mode = "today"
                days = 1
            elif "내일" in msg_lower:
                mode = "tomorrow"
                days = 2
            elif "다음주" in msg_lower:
                mode = "next_week"
                days = 14
            elif "이번주" in msg_lower:
                mode = "this_week"
                days = max(1, 7 - now.weekday())

            raw = await asyncio.to_thread(calendar_list_events, days, 50)
            data = json.loads(raw)
            events = data.get("events", []) if isinstance(data, dict) else []
            if not isinstance(events, list):
                events = []

            def _event_start_date(ev: dict):
                start = (ev or {}).get("start", "") or ""
                if not start:
                    return None
                try:
                    if "T" in start:
                        return datetime.fromisoformat(start.replace("Z", "+00:00")).date()
                    return datetime.strptime(start[:10], "%Y-%m-%d").date()
                except Exception:
                    return None

            if mode == "today":
                base_day = now.date()
                events = [ev for ev in events if _event_start_date(ev) == base_day]
            elif mode == "tomorrow":
                base_day = (now + timedelta(days=1)).date()
                events = [ev for ev in events if _event_start_date(ev) == base_day]
            elif mode == "next_week":
                week_start = (now - timedelta(days=now.weekday()) + timedelta(days=7)).date()
                week_end = week_start + timedelta(days=7)
                events = [ev for ev in events if (d := _event_start_date(ev)) and week_start <= d < week_end]
            elif mode == "this_week":
                week_start = (now - timedelta(days=now.weekday())).date()
                week_end = week_start + timedelta(days=7)
                events = [ev for ev in events if (d := _event_start_date(ev)) and week_start <= d < week_end]

            if not events:
                if mode == "today":
                    return "오늘 일정이 없습니다."
                if mode == "tomorrow":
                    return "내일 일정이 없습니다."
                if mode == "next_week":
                    return "다음 주 일정이 없습니다."
                return "이번 주 일정이 없습니다."

            def _fmt_dt(v: str) -> str:
                if not v:
                    return ""
                try:
                    if "T" in v:
                        dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                        return dt.strftime("%Y-%m-%d %H:%M")
                    d = datetime.strptime(v[:10], "%Y-%m-%d")
                    return d.strftime("%Y-%m-%d (종일)")
                except Exception:
                    return v

            lines = []
            for ev in sorted(events, key=lambda x: (x.get("start") or "")):
                title = ev.get("title") or "(제목 없음)"
                start_s = _fmt_dt(ev.get("start", ""))
                end_s = _fmt_dt(ev.get("end", ""))
                loc = (ev.get("location") or "").strip()
                span = f"{start_s} - {end_s}" if end_s else start_s
                lines.append(f"- {span}: {title}" + (f" (장소: {loc})" if loc else ""))

            if mode == "today":
                header = f"오늘 일정은 {len(events)}건입니다."
            elif mode == "tomorrow":
                header = f"내일 일정은 {len(events)}건입니다."
            elif mode == "next_week":
                header = f"다음 주 일정은 {len(events)}건입니다."
            else:
                header = f"이번 주 일정은 {len(events)}건입니다."

            return header + "\n\n" + "\n".join(lines)
        except Exception as exc:
            logger.warning(f"[Router] calendar fastpath failed: {exc}")
            return ""

    async def process(self, user_message: str, file_path: str = None, reporter=None, security_context: dict | None = None) -> str:
        """멀티 에이전트 파이프라인으로 메시지 처리.

        브리핑/할 일 요청은 ProactiveAgent 실데이터로 처리 (할루시네이션 방지).

        폴백 체인: gemini-3.1-flash-lite → gemini-2.5-flash → Ollama(home-pc)
        응답 끝에 사용된 모델명 표시.

        Args:
            user_message: 사용자 메시지
            file_path: 첨부 파일 경로 (선택)
            reporter: ProgressReporter 인스턴스 (선택 — 진행 상태 발행용)
        """
        global _last_used_model
        t_start = time.time()

        # 브리핑/할 일 요청 → ProactiveAgent 실데이터 (할루시네이션 방지)
        msg_lower = user_message.lower()
        _briefing_kw = ["브리핑", "아침 보고", "오늘 보고", "할 일", "오늘 뭐", "오늘 일정", "뭐 해야"]
        if any(kw in msg_lower for kw in _briefing_kw) and not file_path:
            try:
                from src.core.proactive_agent import get_proactive_agent
                _agent = get_proactive_agent()
                _result = await asyncio.to_thread(_agent.morning_briefing)
                _last_used_model = "proactive_agent"
                latency = (time.time() - t_start) * 1000
                logger.info(f"[Router] 브리핑 → ProactiveAgent ({latency:.0f}ms)")
                return _result + f"\n\n_(proactive_agent)_"
            except Exception as _e:
                logger.warning(f"[Router] ProactiveAgent 실패, 일반 경로로 폴백: {_e}")

        # Step 1: 의도 분류
        if reporter:
            await reporter.update("🔍 의도 분류 중...")
        fast_calendar_reply = await self._try_calendar_fastpath(user_message, file_path=file_path, reporter=reporter)
        if fast_calendar_reply:
            _last_used_model = "calendar_fastpath"
            latency = (time.time() - t_start) * 1000
            logger.info(f"[Router] calendar fastpath hit ({latency:.0f}ms)")
            return fast_calendar_reply + f"\n\n_(calendar_fastpath)_"

        agent_id = await self.classify_intent(user_message)
        agent_config = AGENTS[agent_id]
        tools = _get_agent_tools(agent_id)
        blocked_tools = []
        high_risk_tools_blocked = False
        if tools:
            from src.core.governance.execution_gate import filter_tools_for_gate

            owner_approved = bool((security_context or {}).get("owner_approved"))
            tools, blocked_tools = filter_tools_for_gate(tools, owner_approved=owner_approved)
            high_risk_tools_blocked = bool(blocked_tools)
            if blocked_tools:
                blocked_names = ", ".join(decision.matched[0] for decision in blocked_tools[:6])
                logger.info(
                    "[Router] SEC-002/004/008 blocked %d tools for %s: %s",
                    len(blocked_tools),
                    agent_id,
                    blocked_names,
                )

        logger.info(f"[Router] 에이전트: {agent_config['name']} ({len(tools)}개 도구)")

        # Step 2: Gemini 메인 호출 → 폴백 체인
        reply = ""
        used_model = FAST_MODEL
        ollama_used = False

        if reporter:
            await reporter.update(f"🤖 {agent_config['name']} 실행 중...")
        try:
            if tools:
                reply = await self._call_agent_with_tools(agent_id, user_message, tools, file_path, reporter=reporter)
            else:
                reply = await self._call_chat_agent(user_message)
        except Exception as e:
            err_str = str(e)
            logger.warning(f"[Router] {FAST_MODEL} 실패: {err_str[:80]}")

            if tools and not high_risk_tools_blocked:
                if reporter:
                    await reporter.update(f"⚠️ {FAST_MODEL} 실패 → SoraEngine 우회 실행 중...")
                try:
                    reply = await self._call_sora_engine(
                        user_message,
                        file_path=file_path,
                        security_context=security_context,
                    )
                    used_model = "sora_engine"
                    logger.info("[Router] SoraEngine 우회 성공")
                except Exception as engine_exc:
                    logger.warning(f"[Router] SoraEngine 우회 실패: {str(engine_exc)[:80]}")
                    reply = ""
            elif high_risk_tools_blocked:
                logger.info("[Router] SoraEngine fallback skipped because SEC gate blocked high-risk tools")

            if not reply:
                # 1차 폴백: gemini-2.5-flash
                if reporter:
                    await reporter.update(f"⚠️ {FAST_MODEL} 실패 → gemini-2.5-flash 폴백 중...")
                try:
                    reply = await self._call_with_model(FALLBACK_MODEL, user_message)
                    used_model = FALLBACK_MODEL
                    logger.info(f"[Router] 1차 폴백 성공: {FALLBACK_MODEL}")
                except Exception as e2:
                    logger.warning(f"[Router] {FALLBACK_MODEL} 실패: {str(e2)[:80]}")

                    # T4 · 2차 폴백: LiteLLM 로컬 게이트웨이 (local-first 우선)
                    if LOCAL_FIRST_ENABLED:
                        if reporter:
                            await reporter.update("⚠️ Gemini 실패 → 🏠 LiteLLM 로컬 게이트웨이로 전환 중...")
                        try:
                            system_local = (
                                "당신은 소라(Sora), 허예솔 대표님의 AI 비서입니다. 한국어로 친절하게 답변하세요."
                            )
                            reply = await asyncio.to_thread(
                                _call_litellm,
                                user_message,
                                system_local,
                                LLM_PRIMARY_MODEL,
                                LOCAL_FIRST_TIMEOUT,
                            )
                            if reply:
                                used_model = f"local/{LLM_PRIMARY_MODEL}"
                                logger.info(f"[Router] 2차 폴백 성공 (LiteLLM): {LLM_PRIMARY_MODEL}")
                        except Exception as e_local:
                            logger.warning(f"[Router] LiteLLM 로컬 폴백 실패: {str(e_local)[:120]}")
                            reply = ""

                    # 최종 폴백: Ollama
                    if not reply:
                        if reporter:
                            await reporter.update("⚠️ Gemini 전체 실패 → 🦙 Ollama 로컬 모델로 전환 중...")
                    try:
                        system = (
                            f"당신은 소라(Sora), 허예솔 대표님의 AI 비서입니다. 한국어로 답변하세요."
                        )
                        raw = await asyncio.to_thread(_call_ollama, user_message, system)
                        reply = raw
                        used_model = f"ollama/{OLLAMA_MODEL}"
                        ollama_used = True
                        logger.info(f"[Router] Ollama 폴백 성공: {OLLAMA_MODEL}")
                    except Exception as e3:
                        reply = f"⚠️ 모든 AI 서비스 일시 중단됐어요. (Gemini, Ollama 모두 실패)\n오류: {str(e3)[:100]}"
                        used_model = "none"
                        logger.error(f"[Router] 모든 폴백 실패: {e3}")

        # 소프트 거부 감지 → Ollama 폴백
        # 조건: 짧은 응답(200자 미만) + 거부 패턴 + 실제 작업 결과 없음
        # "죄송합니다" 같은 단어는 일상 대화에도 쓰이므로 길이 조건 필수
        _REFUSAL_PATTERNS = [
            # 정책 거부
            "안전 정책", "서비스 정책", "이용 정책", "안전 가이드라인", "윤리 가이드라인",
            # 불가 표현
            "생성할 수 없습니다", "수행할 수 없습니다", "제공할 수 없습니다", "답변해 드릴 수 없",
            # 부적절 표현
            "부적절한 성적", "부적절한 내용", "성적 콘텐츠", "성인 콘텐츠",
            # 영어 거부
            "I cannot generate", "I'm unable to create", "I can't create",
            "against my guidelines", "violates", "not appropriate", "explicit content",
        ]
        # 짧은 거부 응답: 200자 미만이고 패턴 포함 + 도구 결과 없음
        _is_refusal = (
            reply
            and len(reply) < 250
            and any(p in reply for p in _REFUSAL_PATTERNS)
            and used_model != f"ollama/{OLLAMA_MODEL}"
        )
        if _is_refusal:
            logger.info(f"[Router] 소프트 거부 감지 → Ollama 폴백 강제 발동")
            if reporter:
                await reporter.update("🦙 Gemini 거부 감지 → Ollama 로컬 모델로 전환 중...")
            try:
                # 이미지 에이전트: _translate_prompt()로 분석 후 ComfyUI 직접 호출 (완전 로컬)
                # Ollama JSON 분석 제거 — 코딩 모델이 한국어 NSFW 맥락 이해 못함
                # _translate_prompt()가 NSFW/스타일/캐릭터 감지 + 영어 변환 정확히 처리
                if high_risk_tools_blocked and agent_id == "image":
                    reply = (
                        "이미지 생성/외부 전송 도구는 SEC-002/004/008 승인 없이는 실행하지 않았어요. "
                        "승인된 요청으로 다시 들어오면 생성 경로를 열 수 있어요."
                    )
                    used_model = "security_gate"
                elif agent_id == "image":
                    from src.core.tools.comfyui_tools import (
                        comfyui_generate_image, _send_telegram_photo,
                        _translate_prompt, _DEFAULT_NEGATIVE, _NSFW_NEGATIVE_TAGS
                    )
                    import json as _json

                    sd_prompt, is_nsfw, use_anime = _translate_prompt(user_message)
                    negative = (_DEFAULT_NEGATIVE + ", " + _NSFW_NEGATIVE_TAGS) if is_nsfw else _DEFAULT_NEGATIVE
                    logger.info(f"[Router] 로컬 번역: {sd_prompt[:60]} | NSFW={is_nsfw} | anime={use_anime}")

                    result = _json.loads(await asyncio.to_thread(
                        comfyui_generate_image, sd_prompt, negative, 512, 768, 25, -1, False
                    ))
                    if result.get("status") == "success":
                        _send_telegram_photo(result.get("image_path", ""), result.get("caption", f"🎨 {user_message}"))
                        reply = f"✅ 이미지 생성 완료! 전송했어요 🎨"
                    else:
                        reply = f"이미지 생성 실패: {result.get('error', '알 수 없는 오류')}"
                else:
                    # 소라 전체 페르소나로 Ollama 호출 (system 미지정 → _SORA_SYSTEM_PROMPT 자동 사용)
                    reply = await asyncio.to_thread(_call_ollama, user_message)
                if used_model != "security_gate":
                    used_model = f"ollama/{OLLAMA_MODEL}" if agent_id != "image" else "comfyui_direct"
                    ollama_used = agent_id != "image"
            except Exception as e_ollama:
                logger.warning(f"[Router] 소프트거부 Ollama 폴백 실패: {e_ollama}")

        # 모델명 기록
        _last_used_model = used_model

        # 응답 끝에 모델 표시 (Ollama 사용 시 알림 포함)
        model_tag = f"\n\n_(🦙 Ollama {OLLAMA_MODEL} 기반 응답 — Gemini 일시 장애)_" if ollama_used else f"\n\n_({used_model})_"
        reply = reply.rstrip() + model_tag

        latency = (time.time() - t_start) * 1000
        logger.info(f"[Router] 완료 ({latency:.0f}ms, model={used_model}): {reply[:60]}")
        return reply

    async def _call_with_model(self, model: str, message: str) -> str:
        """지정 Gemini 모델로 단순 텍스트 응답."""
        from google import genai
        client = self._get_client()
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=model,
            contents=message,
            config={"system_instruction": "당신은 소라(Sora), 허예솔 대표님의 AI 비서입니다. 한국어로 답변하세요."},
        )
        return response.text.strip()

    async def _call_agent_with_tools(self, agent_id: str, message: str, tools: list, file_path: str = None, reporter=None) -> str:
        """도구를 가진 에이전트 호출."""
        try:
            from google import genai
            from google.genai import types

            client = self._get_client()
            _safety_off = [
                types.SafetySetting(category=c, threshold="BLOCK_NONE")
                for c in [
                    "HARM_CATEGORY_HARASSMENT", "HARM_CATEGORY_HATE_SPEECH",
                    "HARM_CATEGORY_SEXUALLY_EXPLICIT", "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "HARM_CATEGORY_CIVIC_INTEGRITY",
                ]
            ]
            config = types.GenerateContentConfig(
                system_instruction=_build_system_prompt(agent_id),
                tools=tools,
                automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=False),
                safety_settings=_safety_off,
            )

            chat = client.chats.create(model=FAST_MODEL, config=config)
            if reporter:
                await reporter.update(f"⚙️ {AGENTS[agent_id]['name']} 도구 호출 중...")
            response = await asyncio.to_thread(chat.send_message, message)

            # 응답 추출
            reply = ""
            try:
                reply = response.text
            except (ValueError, AttributeError):
                pass

            # 빈 응답 → history에서 도구 결과 추출 후 반환
            # (자연어 요약은 brain/worker.py의 _ensure_quality_response()에서 일괄 처리)
            if not reply:
                tool_results = self._extract_results_from_chat(chat)
                if tool_results:
                    reply = tool_results  # worker가 자연어로 변환
                else:
                    reply = "도구를 실행했지만 결과를 가져오지 못했습니다."

            return reply

        except Exception as e:
            logger.error(f"[Router] 에이전트 호출 실패: {e}")
            raise

    async def _call_chat_agent(self, message: str) -> str:
        """도구 없는 대화 에이전트. T4: LiteLLM 로컬 게이트웨이 1차, Gemini 2차."""
        # T4 · Local-first primary path
        if LOCAL_FIRST_ENABLED:
            try:
                text = await asyncio.to_thread(
                    _call_litellm,
                    message,
                    "당신은 소라(Sora), 허예솔 대표님의 AI 비서입니다. 한국어로 친절하게 답변하세요.",
                    LLM_PRIMARY_MODEL,
                    LOCAL_FIRST_TIMEOUT,
                )
                if text:
                    logger.info(f"[Router] local-first chat 성공: model={LLM_PRIMARY_MODEL}")
                    return text
                logger.warning("[Router] LiteLLM empty response, Gemini로 폴백")
            except Exception as e:
                logger.warning(f"[Router] LiteLLM 로컬 경로 실패, Gemini 폴백: {e}")

        # Gemini fallback path
        try:
            client = self._get_client()
            response = await asyncio.to_thread(
                client.models.generate_content,
                model=FAST_MODEL,
                contents=message,
                config={"system_instruction": "당신은 소라(Sora), 허예솔 대표님의 AI 비서입니다. 한국어로 친절하게 답변하세요."},
            )
            return response.text.strip()
        except Exception as e:
            raise

    async def _call_sora_engine(
        self,
        message: str,
        file_path: str = None,
        security_context: dict | None = None,
    ) -> str:
        """AgentRouter 실패 시 SoraEngine으로 우회 실행."""
        if not bool((security_context or {}).get("owner_approved")):
            from src.core.governance.execution_gate import evaluate_text_execution_gate

            decision = evaluate_text_execution_gate(message)
            if decision.requires_approval:
                raise PermissionError(
                    "SEC-002/004/008 blocked SoraEngine fallback without owner approval"
                )

        from src.core.sora_engine import get_sora_engine

        engine = get_sora_engine()
        return await engine.process(message, file_path=file_path)

    def _extract_results_from_chat(self, chat) -> str:
        """chat history에서 function_response 추출."""
        try:
            history = getattr(chat, '_curated_history', None) or getattr(chat, 'history', [])
            results = []
            for msg in reversed(history[-10:]):
                for part in getattr(msg, 'parts', []):
                    if hasattr(part, 'function_response'):
                        fr = part.function_response
                        results.append(json.dumps(
                            {"tool": getattr(fr, 'name', '?'), "result": getattr(fr, 'response', {})},
                            ensure_ascii=False, default=str,
                        )[:1500])
                if results:
                    break
            return "\n".join(results)
        except Exception:
            return ""

    async def _summarize(self, user_query: str, tool_results: str) -> str:
        """도구 결과를 자연어로 요약."""
        try:
            client = self._get_client()
            prompt = f"""소라(Sora) AI 비서입니다. 대표님 요청에 도구를 실행한 결과입니다.

■ 요청: {user_query}
■ 도구 결과: {tool_results[:3000]}

위 결과를 대표님에게 간결하게 보고하세요. 한국어, ~요 체."""

            response = await asyncio.to_thread(
                client.models.generate_content,
                model=FAST_MODEL,
                contents=prompt,
            )
            return response.text.strip()
        except Exception as e:
            return f"도구 실행 완료. 결과 요약 실패: {str(e)[:100]}"


# 싱글턴
_router: Optional[AgentRouter] = None

def get_agent_router() -> AgentRouter:
    global _router
    if _router is None:
        _router = AgentRouter()
    return _router
