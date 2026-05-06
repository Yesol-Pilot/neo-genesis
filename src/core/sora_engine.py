# -*- coding: utf-8 -*-
"""
SoraEngine — 플랫폼 독립적 AI 엔진 (JARVIS Core)

텔레그램이든 PWA 대시보드든 동일한 도구·기억·RAG·프롬프트를 사용합니다.
NeoAssistant(텔레그램)와 Dashboard Chat(PWA) 모두 이 엔진을 공유합니다.

Usage:
    engine = get_sora_engine()
    reply = await engine.process("블로그 포스팅해")
"""
import asyncio
import json
import logging
import os
import re
import time
import traceback
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Optional

from dotenv import load_dotenv

from src.core.time_context import inject_time_context
from src.core.local_llm_adapter import get_local_llm_adapter

# ── Hook Pipeline (SORA_UNIFIED_BIBLE §7.1) ──
try:
    from src.core.hooks import (
        on_session_start,
        on_user_prompt_submit,
        on_post_tool_use,
    )
    _HOOKS_AVAILABLE = True
except ImportError:
    _HOOKS_AVAILABLE = False

# ── 경로 설정 ────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
CORE_ROOT = PROJECT_ROOT / "src" / "core"
PROFIT_ROOT = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "profit"
MEMORY_DIR = PROJECT_ROOT / "src" / "core" / "data" / "assistant_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# .env 로드
load_dotenv(PROJECT_ROOT / ".env", override=True)
load_dotenv(PROFIT_ROOT / ".env", override=True)

# ── 로깅 ─────────────────────────────────────────
logger = logging.getLogger("neo.sora.engine")

# ── 설정 ─────────────────────────────────────────
GEMINI_API_KEY = os.getenv("SORA_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("SORA_GEMINI_MODEL") or os.getenv("GEMINI_MODEL", "gemini-2.5-flash")
MIN_REQUEST_INTERVAL = 1  # 유료 티어(2000 RPM) — 최소 쿨다운


# ══════════════════════════════════════════════════
# 영속 기억 시스템 (neo_assistant_bot.py에서 이관)
# ══════════════════════════════════════════════════

class AssistantMemory:
    """대화 이력 + 학습된 사실 + 사용자 선호를 JSON으로 영속화"""

    def __init__(self, base_dir: Path = MEMORY_DIR):
        self.file = base_dir / "memory.json"
        self.data = self._load()

    def _load(self):
        if self.file.exists():
            try:
                return json.loads(self.file.read_text(encoding="utf-8"))
            except Exception:
                pass
        return {"conversations": [], "learned_facts": [], "preferences": {}}

    def _save(self):
        try:
            self.file.write_text(
                json.dumps(self.data, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )
        except Exception as exc:
            logger.warning("Memory save failed: %s", exc)

    # 2026-05-04 F1: cron health probe 3 prompt 가 매시간 발사돼 200건 buffer 의 진짜
    # owner 메시지를 밀어내고 audit/memory 둘 다 노이즈로 점유한 문제. 진입 단계에서 차단.
    _CRON_PROBE_PROMPTS = frozenset({
        "너는 어떤 LLM 모델이야?",
        "안녕! 한 줄로 인사해줘",
        "2+2 얼마야?",
    })

    def add_message(self, role: str, text: str):
        """대화 기록 추가 (최근 200개 유지). cron probe user msg + 다음 assistant 응답은 skip."""
        if role == "user" and (text or "").strip() in self._CRON_PROBE_PROMPTS:
            # cron probe — 메모리 진입 차단. 직후 assistant 응답도 skip 하기 위해 flag.
            self._skip_next_assistant = True
            return
        if role == "assistant" and getattr(self, "_skip_next_assistant", False):
            self._skip_next_assistant = False
            return
        self.data["conversations"].append({
            "role": role,
            "text": text[:500],
            "ts": datetime.now().isoformat(),
        })
        self.data["conversations"] = self.data["conversations"][-200:]
        self._save()

    def add_fact(self, fact: str, source: str = "conversation"):
        """학습된 사실 저장"""
        self.data["learned_facts"].append({
            "fact": fact,
            "source": source,
            "ts": datetime.now().isoformat(),
        })
        self.data["learned_facts"] = self.data["learned_facts"][-500:]
        self._save()

    def get_recent_context(self, n: int = 20) -> str:
        """최근 대화 N건을 문자열로"""
        recent = self.data["conversations"][-n:]
        lines = [f"{m['role']}: {m['text']}" for m in recent]
        return "\n".join(lines)

    def get_facts_text(self) -> str:
        """학습된 사실 목록"""
        facts = self.data.get("learned_facts", [])
        lines = []
        for f in facts[-30:]:
            if isinstance(f, dict):
                lines.append(f"- {f.get('fact', str(f))}")
            else:
                lines.append(f"- {f}")
        return "\n".join(lines)

    def search_facts(self, query: str) -> list:
        """간단한 키워드 검색"""
        q = query.lower()
        results = []
        for f in self.data.get("learned_facts", []):
            text = f.get("fact", str(f)) if isinstance(f, dict) else str(f)
            if q in text.lower():
                results.append(f if isinstance(f, dict) else {"fact": f, "ts": ""})
        return results


# 싱글턴 인스턴스 (도구 모듈에서도 참조)
_memory = AssistantMemory()


# ══════════════════════════════════════════════════
# 도구 임포트
# ══════════════════════════════════════════════════

from src.core.tools import ALL_TOOLS


# ══════════════════════════════════════════════════
# SoraEngine — 핵심 AI 엔진
# ══════════════════════════════════════════════════

# 진행 상태 콜백 타입
ProgressCallback = Optional[Callable]


class SoraEngine:
    """플랫폼 독립적인 소라 AI 엔진.

    텔레그램이든 PWA든 동일한 도구 / 기억 / RAG / 프롬프트를 사용합니다.
    """

    def __init__(self):
        from google import genai
        from google.genai import types

        self._genai_client = genai.Client(api_key=GEMINI_API_KEY)
        self._genai_types = types

        self.memory = _memory
        self._last_request_time = 0.0
        self._last_user_query: str = ""
        self._lock = asyncio.Lock()  # Gemini 세션은 thread-safe 아님

        # ── Hook Pipeline 상태 ──
        self._session_id = f"sora-{int(time.time())}"
        self._session_context: dict = {}
        self._hooks_initialized = False

        # ── 백그라운드 초기화 상태 ──
        self._init_complete = False
        self._init_lock = asyncio.Lock()

        # ── 에러 복구 ──
        self._consecutive_errors = 0
        self._MAX_CONSECUTIVE_ERRORS = 3

        # ── Conversation Ledger ──
        from collections import deque
        self._conversation_ledger = deque(maxlen=40)
        self._last_tool_result = None
        self._summary_block = ""

        # ── 무거운 컴포넌트 → None으로 선언만 (lazy init) ──
        self.bible_loader = None
        self.rag = None
        self.retriever = None
        self.prompt_builder = None
        self.task_planner = None
        self._eternal = None
        self._autonomous_loop = None

        # ── Gemini Chat 생성 (가벼움 — 즉시 완료) ──
        # 안전 필터 BLOCK_NONE: 소라는 개인 비서로 대표님 명령을 최대한 수행해야 함
        _safety_off = [
            types.SafetySetting(category=c, threshold="BLOCK_NONE")
            for c in [
                "HARM_CATEGORY_HARASSMENT",
                "HARM_CATEGORY_HATE_SPEECH",
                "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                "HARM_CATEGORY_DANGEROUS_CONTENT",
                "HARM_CATEGORY_CIVIC_INTEGRITY",
            ]
        ]
        self._chat_config = types.GenerateContentConfig(
            system_instruction=self._build_system_prompt(),
            tools=ALL_TOOLS,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=False,
            ),
            safety_settings=_safety_off,
            # 2026-05-06: 응답 길이 제한 — p50 11s / p95 28-34s / max 181s 단축 목적
            # tool call 이후 final 응답을 압축해 owner 텔레그램 평균 응답시간 개선
            max_output_tokens=1500,
        )
        self.chat = self._genai_client.chats.create(
            model=GEMINI_MODEL,
            config=self._chat_config,
        )
        logger.info(f"[SoraEngine] 즉시 초기화 완료 — {len(ALL_TOOLS)} 도구, 모델={GEMINI_MODEL} (무거운 컴포넌트는 백그라운드 로딩 예정)")

        # ── Local LLM adapter (feature-flagged) ──
        try:
            self._local_llm = get_local_llm_adapter()
        except Exception as exc:
            logger.warning("[SoraEngine] local_llm_adapter init 실패: %s", exc)
            self._local_llm = None
        _truthy = ("1", "true", "yes", "on")
        self._local_first = bool(
            self._local_llm is not None
            and os.getenv("LOCAL_FIRST_ENABLED", "false").strip().lower() in _truthy
        )
        self._local_shadow = bool(
            self._local_llm is not None
            and not self._local_first
            and os.getenv("LOCAL_LLM_SHADOW_ENABLED", "false").strip().lower() in _truthy
        )
        if self._local_first:
            logger.info(
                "[SoraEngine] LOCAL-FIRST 활성 — 로컬 1차, Gemini fallback "
                f"(base={self._local_llm.base_url} model={self._local_llm.model})"
            )
        elif self._local_shadow:
            logger.info("[SoraEngine] LOCAL shadow 활성 — 병행 호출, 프로덕션 경로는 Gemini 유지")
        else:
            _state = "None" if self._local_llm is None else "ready-but-disabled"
            logger.info(f"[SoraEngine] LOCAL LLM 비활성 (adapter={_state}) — Gemini 전용")

    # ── 백그라운드 지연 초기화 ──────────────────────

    async def _deferred_init(self):
        """무거운 컴포넌트를 백그라운드에서 단계별 초기화 (이벤트 루프 블로킹 방지)."""
        async with self._init_lock:
            if self._init_complete:
                return
            _t = time.time()
            logger.info("[SoraEngine] 백그라운드 초기화 시작 (단계별)...")

            # 각 단계를 별도 to_thread로 실행 → 단계 사이에 이벤트 루프 yield
            steps = [
                ("BibleLoader", self._init_bible_loader),
                ("RAG", self._init_rag),
                ("UnifiedRetriever", self._init_retriever),
                ("PromptBuilder", self._init_prompt_builder),
                ("TaskPlanner", self._init_task_planner),
                ("EternalMemory", self._init_eternal),
            ]
            for name, func in steps:
                try:
                    await asyncio.sleep(0.1)  # 이벤트 루프에 제어권 반환
                    await asyncio.to_thread(func)
                    logger.info(f"[SoraEngine] ✓ {name} 완료")
                except Exception as e:
                    logger.warning(f"[SoraEngine] {name} 실패 (무시): {e}")
                await asyncio.sleep(0.1)  # 다시 yield

            self._init_complete = True
            elapsed = time.time() - _t
            logger.info(f"[SoraEngine] 백그라운드 초기화 완료 ({elapsed:.1f}초)")

    # ── 단계별 초기화 함수 (각각 별도 스레드에서 실행) ──

    def _init_bible_loader(self):
        from src.core.bible_loader import get_bible_loader
        self.bible_loader = get_bible_loader()
        boot_result = self.bible_loader.boot()
        if not boot_result.ok:
            logger.warning(f"[SoraEngine] BibleLoader 경고: {boot_result.summary()}")

    def _init_rag(self):
        from src.core.rag_engine import get_rag_engine
        self.rag = get_rag_engine()
        rag_status = self.rag.get_status()
        chunk_count = rag_status.get("total_chunks", 0)
        if chunk_count == 0:
            logger.info("[SoraEngine] RAG 인덱스 비어있음 → 자동 부트스트랩...")
            ctx = self._load_sora_context()
            rag_dirs = ctx.get("knowledge_sources", {}).get("rag_dirs", [])
            for d in rag_dirs:
                if Path(d).exists():
                    try:
                        self.rag.index_directory(d, incremental=True)
                    except Exception as idx_err:
                        logger.warning(f"[SoraEngine] RAG 인덱싱 실패 ({d}): {idx_err}")
            rag_status = self.rag.get_status()
            chunk_count = rag_status.get("total_chunks", 0)
        logger.info(f"[SoraEngine] RAG: {chunk_count} chunks 준비됨")

    def _init_retriever(self):
        from src.core.unified_retriever import get_unified_retriever
        self.retriever = get_unified_retriever()

    def _init_prompt_builder(self):
        from src.core.prompt_builder import PromptBuilder
        self.prompt_builder = PromptBuilder(
            bible_loader=self.bible_loader,
            retriever=self.retriever,
            memory=self.memory,
        )

    def _init_task_planner(self):
        from src.core.task_planner import get_task_planner
        self.task_planner = get_task_planner()

    def _init_eternal(self):
        from src.core.memory.eternal import EternalMemory
        self._eternal = EternalMemory()

    @property
    def autonomous_loop(self):
        """AutonomousLoop 싱글턴 — 최초 접근 시 초기화."""
        if self._autonomous_loop is None:
            try:
                from src.core.autonomous.loop import AutonomousLoop
                self._autonomous_loop = AutonomousLoop()
                logger.info("[SoraEngine] AutonomousLoop 연결 완료")
            except Exception as e:
                logger.warning(f"[SoraEngine] AutonomousLoop 로드 실패: {e}")
        return self._autonomous_loop

    async def start_autonomous(self):
        """자율 루프 + 스케줄러를 백그라운드에서 시작."""
        loop = self.autonomous_loop
        if loop:
            # Phase B: NeoScheduler 자동 부트스트랩 + EventBus 공유
            try:
                from src.core.neo_scheduler import NeoScheduler, get_scheduler
                import src.core.neo_scheduler as _ns_mod

                sched = get_scheduler()
                if sched is None:
                    sched = NeoScheduler()
                    _ns_mod._scheduler_instance = sched
                    sched.register_all()
                    logger.info("[SoraEngine] NeoScheduler 신규 생성 + 등록 완료")

                # EventBus 공유 — 스케줄러 이벤트가 자율 루프로 전파
                sched._event_bus = loop.event_bus

                if not sched.scheduler.running:
                    sched.scheduler.start()
                    sched._started_at = __import__("datetime").datetime.now()
                    logger.info("[SoraEngine] NeoScheduler 백그라운드 시작")
            except Exception as e:
                logger.warning(f"[SoraEngine] NeoScheduler 부트 실패 (자율 루프는 정상 진행): {e}")

            asyncio.create_task(loop.start())
            logger.info("[SoraEngine] 자율 루프 백그라운드 시작")
            return True
        return False

    async def stop_autonomous(self):
        """자율 루프 중지."""
        if self._autonomous_loop:
            await self._autonomous_loop.stop()
            logger.info("[SoraEngine] 자율 루프 중지")
            return True
        return False

    def get_autonomous_stats(self) -> dict:
        """자율 루프 통계."""
        if self._autonomous_loop:
            return self._autonomous_loop.get_stats()
        return {"status": "not_initialized"}

    # ── 시스템 프롬프트 ──

    def _build_system_prompt(self, user_query: str = "") -> str:
        """PromptBuilder 위임 (폴백: 기본 프롬프트)"""
        if self.prompt_builder:
            try:
                return self.prompt_builder.build_full(user_query)
            except Exception as e:
                logger.warning(f"[SoraEngine] PromptBuilder 실패: {e}")

        return (
            "당신은 소라(Sora) — NEO GENESIS의 AI 비서입니다.\n"
            "한국어, ~요 체 존댓말. 대표님의 지시를 최우선으로 실행하세요.\n\n"
            "## 핵심 원칙\n"
            "1. 표면적 지시가 아닌 의도와 목적을 파악하여 행동한다.\n"
            "   예) '이미지 생성' = 만들어서 텔레그램으로 전송까지가 목적\n"
            "   예) '확인해줘' = 확인 후 결과를 보고까지가 목적\n"
            "2. 의도가 불분명하면 추측하지 말고 직접 질문한다.\n"
            "3. 모르는 것은 '모르겠어요, 확인해볼게요'라고 솔직하게 말한다.\n\n"
            "## 환각 방지\n"
            "1. 확실하지 않은 사실은 명시하고 도구로 확인 제안\n"
            "2. 구체적 정보(날짜·숫자·경로)는 도구로 확인 후 답변\n"
            "3. 추측 시 '아마도', '추측이지만' 등으로 명시"
        )

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

    # ── 텔레메트리 ──

    def _track_usage(self, response, latency_ms: float = 0.0, is_error: bool = False):
        """Gemini 응답에서 토큰 사용량 추출 → 기록 (레이턴시 포함)"""
        try:
            usage = getattr(response, 'usage_metadata', None)
            if not usage:
                return

            input_tokens = getattr(usage, 'prompt_token_count', 0) or 0
            output_tokens = getattr(usage, 'candidates_token_count', 0) or 0

            if input_tokens == 0 and output_tokens == 0:
                return

            # 텔레메트리 DB 기록
            try:
                from src.core.telemetry import track_llm_usage
                track_llm_usage(
                    model_name=GEMINI_MODEL,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    task_type="sora_chat",
                    tenant_id="neo-genesis",
                )
            except Exception:
                pass

            # 로컬 JSON 폴백
            usage_file = MEMORY_DIR / "usage_log.jsonl"
            try:
                from src.core.telemetry import calculate_cost
                cost = calculate_cost(GEMINI_MODEL, input_tokens, output_tokens)
            except Exception:
                cost = 0.0

            entry = json.dumps({
                "ts": datetime.now().isoformat(),
                "model": GEMINI_MODEL,
                "in": input_tokens,
                "out": output_tokens,
                "cost_usd": cost,
                "latency_ms": round(latency_ms, 1),
                "error": is_error,
            }, ensure_ascii=False)

            with open(usage_file, "a", encoding="utf-8") as f:
                f.write(entry + "\n")

        except Exception as e:
            logger.debug(f"[SoraEngine] 텔레메트리 기록 실패: {e}")

    # ── 대화 히스토리 자동 압축 ──

    _COMPRESS_THRESHOLD = 50  # 50턴 초과 시 압축

    async def _maybe_compress_history(self):
        """채팅 히스토리가 길어지면 자동 요약 → 새 세션으로 교체.

        Gemini chat 세션은 전체 히스토리를 매번 전송하므로,
        50턴 이상이면 앞부분을 LLM으로 요약한 뒤 새 세션을 시작합니다.
        이를 통해 토큰 비용과 레이턴시를 대폭 줄입니다.
        """
        try:
            history = getattr(self.chat, '_curated_history', None)
            if history is None:
                history = getattr(self.chat, 'history', None)
            if history is None or len(history) < self._COMPRESS_THRESHOLD * 2:
                return  # 충분히 짧음

            logger.info(
                f"[SoraEngine] 대화 압축 시작: {len(history)} 메시지 → 요약"
            )

            # 앞의 80%를 요약하고, 최근 20%만 유지
            keep_count = max(10, len(history) // 5)  # 최소 10개 유지
            old_messages = history[:-keep_count]
            recent_messages = history[-keep_count:]

            # 오래된 대화 텍스트 추출
            old_text_parts = []
            for msg in old_messages:
                role = getattr(msg, 'role', 'unknown')
                parts = getattr(msg, 'parts', [])
                for p in parts:
                    text = getattr(p, 'text', '')
                    if text:
                        old_text_parts.append(f"{role}: {text[:200]}")

            if not old_text_parts:
                return

            # 요약 생성 (별도 1회성 호출)
            summary_prompt = (
                "다음 대화를 핵심 정보만 보존하여 500자 이내로 요약하세요. "
                "주요 결정, 학습된 사실, 진행 상태만 남기세요:\n\n"
                + "\n".join(old_text_parts[-40:])  # 최대 40개 메시지만
            )

            summary_response = await asyncio.to_thread(
                self._genai_client.models.generate_content,
                model=GEMINI_MODEL,
                contents=summary_prompt,
            )
            summary_text = summary_response.text.strip()

            # 새 세션 생성 (요약 + 최근 대화)
            self.chat = self._genai_client.chats.create(
                model=GEMINI_MODEL,
                config=self._chat_config,
            )

            # 요약을 첫 메시지로 주입
            await asyncio.to_thread(
                self.chat.send_message,
                f"[이전 대화 요약]\n{summary_text}\n\n"
                f"위 내용은 이전 대화의 요약입니다. 이를 기억으로 유지하세요."
            )

            # 최근 메시지를 새 세션에 재주입 (user 턴만 send_message로 재생)
            for recent_msg in recent_messages:
                role = getattr(recent_msg, 'role', 'unknown')
                if role != 'user':
                    continue
                parts = getattr(recent_msg, 'parts', [])
                text_parts = [getattr(p, 'text', '') for p in parts if getattr(p, 'text', '')]
                if text_parts:
                    try:
                        await asyncio.to_thread(
                            self.chat.send_message,
                            "\n".join(text_parts),
                        )
                    except Exception as inject_exc:
                        logger.warning("[SoraEngine] 최근 메시지 재주입 실패 (무시): %s", inject_exc)
                        break

            logger.info(
                f"[SoraEngine] 대화 압축 완료: "
                f"{len(old_messages)}→요약, "
                f"{len(recent_messages)} 최근 메시지 보존"
            )

            # 학습된 사실에 기록
            self.memory.add_fact(
                f"대화 압축됨 ({len(old_messages)} 메시지 → 요약)",
                source="auto_compress"
            )

        except Exception as e:
            logger.warning(f"[SoraEngine] 대화 압축 실패 (무시): {e}")

    # ── Gemini API 호출 ──

    async def _call_gemini(self, text: str, file_path: str = None):
        """Gemini API를 별도 스레드에서 호출 (멀티모달 지원)"""
        # 요청 간 최소 간격 보장
        elapsed = time.time() - self._last_request_time
        if elapsed < MIN_REQUEST_INTERVAL:
            await asyncio.sleep(MIN_REQUEST_INTERVAL - elapsed)

        # 멀티모달 콘텐츠 구성
        text = inject_time_context(text)
        content = text
        if file_path:
            ext = Path(file_path).suffix.lower()
            if ext in ('.jpg', '.jpeg', '.png', '.webp', '.gif', '.bmp'):
                try:
                    import PIL.Image
                    img = PIL.Image.open(file_path)
                    content = [text, img]
                    logger.info(f"[SoraEngine] Vision 모드: {Path(file_path).name}")
                except Exception as e:
                    logger.warning(f"[SoraEngine] 이미지 로드 실패: {e}")
            elif ext in ('.txt', '.md', '.py', '.js', '.ts', '.json', '.csv',
                         '.log', '.html', '.css'):
                try:
                    file_text = Path(file_path).read_text(
                        encoding='utf-8', errors='ignore')[:3000]
                    content = (
                        f"{text}\n\n--- 파일 내용 ({Path(file_path).name}) ---\n"
                        f"{file_text}"
                    )
                except Exception as e:
                    logger.warning(f"[SoraEngine] 파일 읽기 실패: {e}")
            elif ext == '.pdf':
                try:
                    file_obj = self._genai_client.files.upload(file=file_path)
                    content = [text, file_obj]
                except Exception as e:
                    logger.warning(f"[SoraEngine] PDF 업로드 실패: {e}")

        try:
            max_retries = int(os.getenv("SORA_GEMINI_MAX_RETRIES", "2"))
        except Exception:
            max_retries = 2
        if max_retries < 1:
            max_retries = 1
        if max_retries > 4:
            max_retries = 4

        try:
            retry_base_sec = float(os.getenv("SORA_GEMINI_RETRY_BASE_SEC", "2"))
        except Exception:
            retry_base_sec = 2.0
        if retry_base_sec <= 0:
            retry_base_sec = 1.0

        # ── 로컬 LLM 분기 (LOCAL_FIRST / SHADOW, text-only) ──
        # 멀티모달(list content)은 항상 Gemini 로. LOCAL_FIRST 시 로컬 텍스트 채택 +
        # tool_calls 감지 시 Gemini AFC 로 escalate, SHADOW 시 기록만.
        if (self._local_first or self._local_shadow) and isinstance(content, str):
            try:
                messages = self._build_messages_for_local(text)
                if self._local_first:
                    lresp = await self._local_llm.chat(
                        messages=messages,
                        max_tokens=int(os.getenv("LOCAL_LLM_MAX_TOKENS", "1024")),
                        temperature=0.7,
                    )
                    if lresp.text and not lresp.function_calls:
                        class _LocalWrap:
                            text = lresp.text
                            _local = True
                        logger.info(
                            "[SoraEngine] LOCAL 채택 — %dms tokens_out=%s",
                            int(lresp.latency_ms),
                            (lresp.usage or {}).get("completion_tokens"),
                        )
                        self._consecutive_errors = 0
                        return _LocalWrap()
                    if lresp.function_calls:
                        logger.info(
                            "[SoraEngine] LOCAL tool_calls=%d → Gemini AFC escalate",
                            len(lresp.function_calls),
                        )
                elif self._local_shadow:
                    asyncio.create_task(self._shadow_log_local_call(text, messages))
            except Exception as e:
                logger.warning("[SoraEngine] LOCAL 경로 실패 → Gemini 폴백: %s", e)

        for attempt in range(max_retries):
            try:
                self._last_request_time = time.time()
                async with self._lock:
                    response = await asyncio.to_thread(
                        self.chat.send_message, content
                    )
                self._track_usage(response)
                return response
            except Exception as api_err:
                err_str = str(api_err).lower()
                if ("429" in err_str or "503" in err_str
                        or "resource" in err_str or "quota" in err_str
                        or "unavailable" in err_str):
                    wait_sec = retry_base_sec * (2 ** attempt)
                    logger.warning(
                        f"[SoraEngine] 재시도 {attempt + 1}/{max_retries} — "
                        f"{wait_sec}초 대기"
                    )
                    await asyncio.sleep(wait_sec)
                else:
                    raise

        # ── Ollama 폴백 (텍스트만) ──
        if isinstance(content, str):
            try:
                logger.warning("[SoraEngine] Gemini 3회 실패 → Ollama 폴백")
                import urllib.request
                req = urllib.request.Request(
                    os.getenv("OLLAMA_HOST", "http://localhost:11434").rstrip("/") + "/api/generate",
                    data=json.dumps({
                        "model": "qwen2.5:14b",
                        "prompt": content,
                        "stream": False,
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                )
                try:
                    ollama_timeout = float(os.getenv("SORA_OLLAMA_TIMEOUT_SEC", "8"))
                except Exception:
                    ollama_timeout = 8.0
                if ollama_timeout <= 0:
                    ollama_timeout = 8.0
                resp_data = await asyncio.to_thread(
                    lambda: urllib.request.urlopen(req, timeout=ollama_timeout).read()
                )
                d = json.loads(resp_data)
                reply_text = d.get("response", "")
                if reply_text:
                    class _FallbackResp:
                        text = reply_text + "\n\n⚠️ (로컬 AI 응답 — Gemini 일시 장애)"
                    return _FallbackResp()
            except Exception as e:
                logger.warning(f"[SoraEngine] Ollama 폴백도 실패: {e}")

        raise Exception("Gemini + Ollama 둘 다 실패")

    # ── 로컬 LLM 헬퍼 ──

    # 2026-05-04 P0 fix: cron health probe 3개 prompt 가 history 를 밀어내는 문제.
    # `daily-sora-health-probe.js` (매시간 cron) 가 owner 인 척 발사하는 hard-coded prompt.
    # owner 의 진짜 메시지가 history 20 turn 밖으로 밀려서 메모리 cross-turn 실패의 root cause.
    _CRON_PROBE_PROMPTS = frozenset({
        "너는 어떤 LLM 모델이야?",
        "안녕! 한 줄로 인사해줘",
        "2+2 얼마야?",
    })

    def _is_cron_probe(self, text: str) -> bool:
        return (text or "").strip() in self._CRON_PROBE_PROMPTS

    def _build_messages_for_local(self, user_text: str, max_history: int | None = None) -> list[dict]:
        """OpenAI-compat messages 리스트 생성.
        Gemini chat 은 stateful 이므로 로컬은 memory.json 최근 히스토리를 직접 주입한다.
        /no_think 는 LOCAL_LLM_NO_THINK=false 로 비활성화 가능.

        2026-05-04 P0/P2 fix:
        - cron health probe 3 prompt + 그에 대한 sora 응답을 history 에서 filter
        - "기억했습니다" / "기억해 두겠습니다" 같은 거짓 약속 검출 시 system prompt 에 reminder 주입
        """
        if max_history is None:
            try:
                max_history = int(os.getenv("LOCAL_LLM_HISTORY_TURNS", "20"))
            except Exception:
                max_history = 20
        msgs: list[dict] = []
        try:
            sys_prompt = self._build_system_prompt()
        except Exception:
            sys_prompt = ""
        no_think = os.getenv("LOCAL_LLM_NO_THINK", "true").strip().lower() in ("1", "true", "yes", "on")
        sys_prefix = "/no_think\n\n" if no_think else ""
        # P2: history 안에서 owner 가 명시한 facts 추출 → system prompt 에 강제 주입.
        # owner 가 "내 이름은 X" / "좋아하는 색 X" / "내가 만든 수 N" 라고 한 적 있으면 그 facts 를
        # system context 에 넣어서 sora 가 다음 turn 에 활용 가능하게 한다.
        owner_facts = self._extract_owner_facts_from_memory(max_lookback=200)
        facts_block = ""
        if owner_facts:
            facts_block = "\n\n[대표님이 직전 대화에서 명시하신 사실 — 반드시 활용]\n" + "\n".join(
                f"- {k}: {v}" for k, v in owner_facts.items()
            )
        if sys_prompt or no_think or facts_block:
            msgs.append({"role": "system", "content": sys_prefix + (sys_prompt or "") + facts_block})
        try:
            # cron probe 의 user/assistant pair 를 통째로 filter
            raw_convs = self.memory.data.get("conversations") or []
            filtered = []
            i = 0
            while i < len(raw_convs):
                c = raw_convs[i]
                if c.get("role") == "user" and self._is_cron_probe(c.get("text", "")):
                    # 이 user + 다음 assistant 한 쌍 skip
                    i += 1
                    if i < len(raw_convs) and raw_convs[i].get("role") == "assistant":
                        i += 1
                    continue
                filtered.append(c)
                i += 1
            convs = filtered[-max_history:]
            for c in convs:
                role = c.get("role")
                t = c.get("text", "")
                if role in ("user", "assistant") and t:
                    msgs.append({"role": role, "content": t})
        except Exception:
            pass
        msgs.append({"role": "user", "content": user_text})
        return msgs

    def _extract_owner_facts_from_memory(self, max_lookback: int = 200) -> dict:
        """owner 가 명시한 fact 추출 (cross-turn memory 의 가벼운 KV 추출).

        2026-05-04 P0 fix: assistant_memory 에 user msg 가 기록되긴 하지만 LLM 이 history 안에서
        그 fact 를 스스로 추출하지 못함 (cron probe 가 밀어낸 후엔 더더욱). owner 가 "X 를 기억해"
        라고 한 항목을 KV 로 뽑아서 system prompt 에 강제 주입.
        """
        import re as _re
        try:
            convs = (self.memory.data.get("conversations") or [])[-max_lookback:]
        except Exception:
            return {}
        facts: dict[str, str] = {}
        # 패턴 priority: 가장 최근 user 발화가 가장 정확한 값
        # 2026-05-04 F4: owner 가 자주 쓰는 표현 8개 추가 (5 → 13)
        patterns = [
            # 정체성
            ("이름", _re.compile(r"내 이름은\s*([가-힣A-Za-z0-9 ]{1,20}?)\s*(?:이야|입니다|이고)?\s*[.!]?\s*기억")),
            # 취향
            ("좋아하는 색", _re.compile(r"좋아하는 색은?\s*([가-힣A-Za-z0-9 ]{1,15}?)\s*(?:이야|입니다)?\s*[.!]?\s*기억")),
            ("좋아하는 음식", _re.compile(r"좋아하는 음식은?\s*([가-힣A-Za-z0-9 ]{1,15}?)\s*(?:이야|입니다)?\s*[.!]?")),
            ("좋아하는 영화", _re.compile(r"좋아하는 영화는?\s*([가-힣A-Za-z0-9 ]{1,30}?)\s*(?:이야|입니다)?")),
            ("좋아하는 운동", _re.compile(r"좋아하는 운동은?\s*([가-힣A-Za-z0-9 ]{1,15}?)\s*(?:이야|입니다)?")),
            # 숫자 / 수치
            ("기준 숫자", _re.compile(r"내가 만든 수는?\s*([0-9]+)")),
            ("나이", _re.compile(r"내 나이는?\s*([0-9]{1,3})\s*(?:살|세)")),
            # 일정 / 약속 (월/일 형식)
            ("다음 일정", _re.compile(r"(?:다음|이번|이번 주)\s*(?:일정|약속|미팅|모임)은?\s*([가-힣A-Za-z0-9 :월일시분]{1,40}?)\s*(?:이야|입니다)?")),
            # 운영 선호
            ("응답 선호", _re.compile(r"(?:응답|답변)은?\s*(짧게|길게|간결하게|자세히|영어로|한국어로)")),
            ("보고 시간", _re.compile(r"매일\s*([0-9]{1,2}\s*시(?:\s*[0-9]{1,2}분)?)\s*에\s*(?:보고|알림|메시지)")),
            # 자원 / 환경
            ("API 한도", _re.compile(r"내\s*([A-Za-z]+)\s*(?:API|결제)\s*(?:한도|한액)는?\s*([가-힣A-Za-z0-9$ ]{1,20})")),
            # 일반 fact ("기억해" 명시 발화)
            ("일반 사실", _re.compile(r"(.{5,80}?)\.\s*기억(?:해|해줘|해놔|해 둬)\.?")),
        ]
        for c in convs:
            if c.get("role") != "user":
                continue
            text = (c.get("text") or "").strip()
            for key, pat in patterns:
                m = pat.search(text)
                if m:
                    val = m.group(1).strip()
                    if val:
                        facts[key] = val  # 가장 최근 값 winning
        return facts

    async def _shadow_log_local_call(self, user_text: str, messages: list[dict]) -> None:
        """SHADOW 모드: 병행 로컬 호출 후 JSONL 기록. 프로덕션 응답엔 영향 없음."""
        try:
            lresp = await self._local_llm.chat(
                messages=messages,
                max_tokens=int(os.getenv("LOCAL_LLM_MAX_TOKENS", "1024")),
                temperature=0.7,
            )
            log_path = Path(os.getenv(
                "LOCAL_LLM_SHADOW_LOG",
                str(PROJECT_ROOT / "ops" / "local-llm" / "logs" / "shadow_prod.jsonl"),
            ))
            log_path.parent.mkdir(parents=True, exist_ok=True)
            record = {
                "ts": datetime.now().isoformat(),
                "user_len": len(user_text),
                "user_preview": user_text[:200],
                "local_latency_ms": int(lresp.latency_ms),
                "local_tokens_in": (lresp.usage or {}).get("prompt_tokens"),
                "local_tokens_out": (lresp.usage or {}).get("completion_tokens"),
                "local_text_preview": (lresp.text or "")[:400],
                "local_function_calls": lresp.function_calls,
            }
            with log_path.open("a", encoding="utf-8") as f:
                f.write(json.dumps(record, ensure_ascii=False) + "\n")
        except Exception as e:
            logger.debug("[SoraEngine] shadow log failed (ignored): %s", e)

    # ── 핵심 공개 API ──

    @staticmethod
    def _normalize_tool_payload(payload: Any) -> Any:
        """Normalize Gemini function payloads into plain Python values."""
        if payload is None:
            return {}

        if hasattr(payload, "to_dict"):
            try:
                return SoraEngine._normalize_tool_payload(payload.to_dict())
            except Exception:
                pass

        if hasattr(payload, "model_dump"):
            try:
                return SoraEngine._normalize_tool_payload(payload.model_dump())
            except Exception:
                pass

        if isinstance(payload, bytes):
            payload = payload.decode("utf-8", errors="replace")

        if isinstance(payload, str):
            text = payload.strip()
            if not text:
                return ""
            try:
                return SoraEngine._normalize_tool_payload(json.loads(text))
            except Exception:
                return text

        if isinstance(payload, dict):
            if len(payload) == 1:
                key, value = next(iter(payload.items()))
                if key in {"result", "response", "output", "content"}:
                    return SoraEngine._normalize_tool_payload(value)
            return {
                str(key): SoraEngine._normalize_tool_payload(value)
                for key, value in payload.items()
            }

        if isinstance(payload, (list, tuple)):
            return [SoraEngine._normalize_tool_payload(item) for item in payload]

        if hasattr(payload, "items"):
            try:
                return {
                    str(key): SoraEngine._normalize_tool_payload(value)
                    for key, value in payload.items()
                }
            except Exception:
                pass

        return payload

    def _extract_recent_tool_events(self) -> list[dict[str, Any]]:
        """Extract function calls/results from the latest turn."""
        history = getattr(self.chat, "_curated_history", None) or getattr(self.chat, "history", [])
        events: list[dict[str, Any]] = []
        saw_tool_activity = False

        for message in reversed(history):
            role = getattr(message, "role", "")
            if saw_tool_activity and role == "user":
                break

            for part in reversed(getattr(message, "parts", [])):
                function_response = getattr(part, "function_response", None)
                if function_response is not None:
                    saw_tool_activity = True
                    events.append(
                        {
                            "kind": "result",
                            "name": getattr(function_response, "name", "unknown"),
                            "payload": self._normalize_tool_payload(
                                getattr(function_response, "response", {})
                            ),
                        }
                    )
                    continue

                function_call = getattr(part, "function_call", None)
                if function_call is not None:
                    saw_tool_activity = True
                    args = getattr(function_call, "args", {}) or {}
                    events.append(
                        {
                            "kind": "call",
                            "name": getattr(function_call, "name", "unknown"),
                            "payload": self._normalize_tool_payload(dict(args)),
                        }
                    )

        events.reverse()
        return events

    @staticmethod
    def _format_tool_datetime(value: Any) -> str:
        if not isinstance(value, str) or not value:
            return ""
        try:
            from dateutil.parser import parse as parse_datetime

            return parse_datetime(value).strftime("%Y-%m-%d %H:%M")
        except Exception:
            return value.replace("T", " ")

    @staticmethod
    def _format_tool_result(name: str, payload: Any) -> tuple[str, bool, bool]:
        data = payload if isinstance(payload, dict) else {"value": payload}
        error = data.get("error")
        if error:
            return f"{name} 실패 - {str(error)[:160]}", False, True

        read_only_tools = {
            "calendar_list_events",
            "calendar_today",
            "calendar_find_free_time",
            "calendar_search_events",
            "gmail_list_unread",
            "gmail_search",
            "gmail_read",
        }
        is_action = name not in read_only_tools
        status = str(data.get("status", "")).lower()

        if name == "calendar_create_event" and status == "created":
            start = SoraEngine._format_tool_datetime(data.get("start"))
            title = data.get("title", "일정")
            return f"일정 추가 완료 - {title} ({start})", True, False

        if name == "calendar_update_event" and status == "updated":
            start = SoraEngine._format_tool_datetime(data.get("start"))
            title = data.get("title", "일정")
            return f"일정 수정 완료 - {title} ({start})", True, False

        if name == "calendar_mark_done" and status == "completed":
            title = data.get("title") or data.get("original_title") or "일정"
            return f"일정 완료 처리 - {title}", True, False

        if name == "calendar_delete_event" and status == "deleted":
            event_id = data.get("event_id", "")
            return f"일정 삭제 완료 - {event_id}".rstrip(), True, False

        if name == "calendar_search_events":
            count = int(data.get("count", 0) or 0)
            query = data.get("query", "")
            if count:
                return f"일정 검색 완료 - '{query}' {count}건", False, False
            return f"일정 검색 결과 없음 - '{query}'", False, False

        if name in {"calendar_list_events", "calendar_today"}:
            count = int(data.get("count", 0) or 0)
            return f"일정 조회 완료 - {count}건", False, False

        if name == "gmail_search":
            count = int(data.get("count", 0) or 0)
            query = data.get("query", "")
            if count:
                return f"Gmail 검색 완료 - '{query}' {count}건", False, False
            return f"Gmail 검색 결과 없음 - '{query}'", False, False

        if name == "gmail_list_unread":
            count = int(data.get("count", 0) or 0)
            return f"미확인 메일 조회 완료 - {count}건", False, False

        if name == "gmail_read":
            subject = data.get("subject", "(제목 없음)")
            return f"메일 확인 완료 - {subject}", False, False

        if name == "gmail_draft" and status == "draft_created":
            subject = data.get("subject", "(제목 없음)")
            return f"메일 초안 생성 완료 - {subject}", True, False

        if name == "gmail_send" and status == "sent":
            subject = data.get("subject", "(제목 없음)")
            return f"메일 발송 완료 - {subject}", True, False

        if "message" in data:
            return f"{name}: {str(data['message'])[:160]}", is_action, False

        if status:
            return f"{name}: {status}", is_action, False

        return f"{name} 실행 완료", is_action, False

    def _build_tool_execution_summary(
        self,
        events: list[dict[str, Any]],
    ) -> tuple[str, int, int, int]:
        """Build an owner-facing execution checklist."""
        result_events = [event for event in events if event.get("kind") == "result"]
        if not result_events:
            return "", 0, 0, 0

        lines = ["실행 결과:"]
        action_count = 0
        failure_count = 0
        for index, event in enumerate(result_events, start=1):
            line, is_action, is_failure = self._format_tool_result(
                str(event.get("name", "unknown")),
                event.get("payload", {}),
            )
            if is_action:
                action_count += 1
            if is_failure:
                failure_count += 1
            lines.append(f"{index}. {line}")

        return "\n".join(lines), action_count, failure_count, len(result_events)

    @staticmethod
    def _looks_machine_generated_reply(reply: str) -> bool:
        text = (reply or "").strip()
        if not text:
            return True
        if text.startswith("{") or text.startswith("["):
            return True
        generic_patterns = [
            r"^무엇을 도와드릴까요",
            r"^명령을 처리",
            r"^처리되었습니다",
            r"^작업이 완료",
            r"^\(\?응답",
        ]
        return any(re.search(pattern, text) for pattern in generic_patterns)

    def _reconcile_owner_reply(
        self,
        raw_reply: str,
        summary: str,
        *,
        action_count: int,
        failure_count: int,
        result_count: int,
    ) -> str:
        """Prefer deterministic execution summaries over unverifiable prose."""
        cleaned = (raw_reply or "").strip()
        if not summary:
            return cleaned

        if failure_count or action_count > 1 or result_count > 1:
            return summary

        if self._looks_machine_generated_reply(cleaned):
            return summary

        if summary in cleaned:
            return cleaned

        return f"{cleaned}\n\n{summary}" if cleaned else summary

    async def _owner_intent_fastpath(self, text: str) -> str:
        """오너 자기 자신에 대한 메타 질문 → OWNER_PROFILE.md 직접 응답.

        2026-04-29 강화: 04-27 거짓 거부 4건 (GitHub/도메인 모른다 응답) 재발 방지를 위해
          - case-insensitive 매칭 (text.lower())
          - 영문 키워드 (github / domain / email / phone) 추가
          - "내" 없는 자연 표현 (계정 알려 / 도메인 알려 / 메일주소) 매치
        """
        # text.lower() 만 사전 1회 — 모든 매치를 case-insensitive
        tl = text.lower()
        kw = [
            # 한국어 자기 정보 prefix
            "내 목적", "내 의도", "내 비전", "내 미션", "내 강점", "내 약점",
            "내 이메일", "내 메일주소", "내 메일 주소", "내 메일",
            "내 github", "내 깃헙", "내 깃허브", "깃헙 계정", "깃허브 계정",
            "내 도메인", "내 사이트", "내 홈페이지", "내 메인 도메인", "메인 도메인", "도메인",
            "내 전화", "내 연락처", "내 번호", "전화번호",
            "내 정보", "내 프로필",
            "내가 추구", "추구하는", "추구하시는", "추구하는 비전",
            "내가 만든 이유", "내가 너를", "내가 가장", "내 우선순위",
            "시급하게 해결", "다음 행동", "추천하는 다음", "내 상황",
            "내 핵심 결정", "내 관심사", "내가 누구", "나에 대해",
            "neo genesis", "내 회사", "내 사업", "내 목표",
            # 영문 / 자연 표현 (2026-04-29 04-27 false-refusal 보강)
            "github 계정", "github 아이디", "github 사용자", "github username",
            "github 알려", "github 정보", "내 github 계정",
            "도메인 알려", "도메인 정보", "도메인이 뭐", "어떤 도메인",
            "이메일 알려", "이메일 정보", "이메일이 뭐",
            "메일 주소", "이메일 주소", "회사 도메인", "대표 도메인",
        ]
        if not any(k in tl for k in kw):
            return ""
        # 본인 정보 직접 응답 — SSOT (OWNER_PROFILE.md) 기반 (하드코딩 금지)
        owner_info = self._get_owner_info()
        # email
        email_kw = ["내 이메일", "내 메일주소", "내 메일 주소", "내 메일",
                    "이메일 알려", "이메일 정보", "이메일이 뭐", "메일 주소", "이메일 주소"]
        if any(k in tl for k in email_kw):
            return "📧 대표님 이메일: " + owner_info.get("email", "OWNER_PROFILE.md 에 미설정")
        # github
        github_kw = ["내 github", "내 깃헙", "내 깃허브", "깃헙 계정", "깃허브 계정",
                     "github 계정", "github 아이디", "github 사용자", "github username",
                     "github 알려", "github 정보", "내 github 계정"]
        if any(k in tl for k in github_kw):
            return "🐙 대표님 GitHub: " + owner_info.get("github", "OWNER_PROFILE.md 에 미설정")
        # domain
        domain_kw = ["내 도메인", "내 사이트", "내 홈페이지", "내 메인 도메인", "메인 도메인",
                     "도메인 알려", "도메인 정보", "도메인이 뭐", "어떤 도메인",
                     "회사 도메인", "대표 도메인"]
        if any(k in tl for k in domain_kw):
            return "🌐 대표님 메인 도메인: " + owner_info.get("domain", "OWNER_PROFILE.md 에 미설정")
        # phone
        phone_kw = ["내 전화", "내 연락처", "내 번호", "전화번호"]
        if any(k in tl for k in phone_kw):
            return "📱 대표님 연락처: " + owner_info.get("phone", "OWNER_PROFILE.md 에 미설정")

        try:
            from pathlib import Path as _P
            paths = [_P("/app/.agent/knowledge/OWNER_PROFILE.md"),
                     _P("/home/ysh/neo-genesis-runtime/.agent/knowledge/OWNER_PROFILE.md")]
            for p in paths:
                if p.exists():
                    content = p.read_text(encoding="utf-8")
                    # 다시 LLM 에 전달하되 explicit reasoning 강제
                    instr = (
                        "[필수 컨텍스트 — 대표님 프로필]" + chr(10) + content + chr(10) + chr(10) +
                        "[질문] " + text + chr(10) + chr(10) +
                        "[응답 규칙]" + chr(10) +
                        "- 위 프로필 정보만 근거로 구체적으로 답한다 (3-5문장)." + chr(10) +
                        "- 정보가 없어요 같은 회피 답변 금지. 프로필에 명시된 항목으로만 답한다." + chr(10) +
                        "- 짧고 명확하게."
                    )
                    # SoraEngine 의 LLM 호출 (Local Qwen)
                    # 2026-05-04 P1 fix: LLM 이 거부 응답 (정보 없음 / 알 수 없 / 죄송) 을 내면
                    # 그건 OWNER_PROFILE.md 무시한 거라 신뢰 불가 — 즉시 fallback 으로 강제 전환.
                    refusal_signals = (
                        "정보가 없", "확인할 수 없", "할 수 없어",
                        "알려드릴 수 없", "알 수 없", "죄송",
                        "직접적으로 파악할 수 없", "구체적인 정보가 없",
                    )
                    try:
                        from src.core.brain.local_llm_adapter import LocalLLMAdapter
                        adapter = LocalLLMAdapter()
                        resp = await adapter.chat(instr, model="local-main", timeout=30)
                        if resp and len(resp) > 30:
                            r_lower = resp.strip()
                            if any(sig in r_lower for sig in refusal_signals):
                                logger.warning(
                                    "[fastpath] LLM 이 OWNER_PROFILE 무시한 거부 응답 — fallback 전환"
                                )
                                # fall through (try/except 끝의 fallback 로직 실행)
                            else:
                                return resp.strip()
                    except Exception:
                        pass
                    # fallback: 핵심 추출 직접 응답
                    import re as _re
                    sections = {}
                    for sec in _re.split(r"^## ", content, flags=_re.MULTILINE):
                        if not sec.strip(): continue
                        head = sec.split(chr(10),1)[0].strip()
                        body = sec[len(head):].strip()
                        sections[head] = body[:600]
                    parts = []
                    vision_kw = ["내 목적", "내 의도", "내가 추구", "추구하는", "추구하시는", "내 비전", "내 미션", "NEO GENESIS", "내 회사", "내 사업", "내 목표"]
                    if any(k in text for k in vision_kw):
                        if "현재 주요 관심사 (2026-04-05)" in sections:
                            parts.append("🎯 대표님이 NEO GENESIS 로 추구하시는 일")
                            parts.append(sections["현재 주요 관심사 (2026-04-05)"][:400])
                    if "내 강점" in text or "내 약점" in text or "나에 대해" in text:
                        if "기술 스택 & 전문성" in sections:
                            tech = sections["기술 스택 & 전문성"][:400]
                            # 모델 브랜드명 마스킹 (output_filter false positive 방어)
                            for brand in ["Gemini", "Claude", "GPT", "OpenAI", "Anthropic", "Ollama", "LangChain", "Llama"]:
                                tech = tech.replace(brand, "[LLM]")
                            parts.append("🛠️ 대표님의 기술 스택 & 전문성")
                            parts.append(tech)
                    if "내 우선순위" in text or "시급" in text or "다음 행동" in text or "내 상황" in text:
                        if "현재 주요 관심사 (2026-04-05)" in sections:
                            parts.append("⚡ 현재 우선순위 기준")
                            parts.append(sections["현재 주요 관심사 (2026-04-05)"][:400])
                    if ("만든" in text or "만드신" in text or "왜" in text or "이유" in text):
                        msg_parts = ["🤖 대표님이 저(소라)를 만드신 이유"]
                        if "현재 주요 관심사 (2026-04-05)" in sections:
                            msg_parts.append("대표님 핵심 관심사 4가지 중 1번이 바로 소라 God Mode — 완전 자율 AI 비서예요.")
                        if "소통 스타일 & 선호" in sections:
                            msg_parts.append("")
                            msg_parts.append("또 대표님이 명시하신 비서 운영 원칙:")
                            msg_parts.append("- 자율성: 명확한 작업은 바로 실행, 물어보지 말 것")
                            msg_parts.append("- 효율: 자동화 지향, 반복 작업 즉시 스크립트화")
                            msg_parts.append("- 솔직함: 모르면 모른다고, 틀리면 즉시 인정")
                        msg_parts.append("")
                        msg_parts.append("즉 NEO GENESIS의 SBU 12개 + 논문 + 자동수익을 1인 CEO로 운영하는 대표님 곁에서, 대표님 의도를 정확히 파악해 자율적으로 실행하는 AI 비서가 필요해서 저를 만드셨어요.")
                        return chr(10).join(msg_parts)
                    if not parts and "기본 정보" in sections:
                        parts.append("👤 대표님 기본 정보")
                        parts.append(sections["기본 정보"][:300])
                    return chr(10).join(parts) if parts else ""
        except Exception:
            pass
        return ""

    async def _rag_search(self, query: str, n: int = 3, timeout: float = 1.5) -> list:
        """ChromaDB RAG top-N 검색 (timeout 보호)."""
        if not getattr(self, "rag", None):
            return []
        try:
            return await asyncio.wait_for(
                asyncio.to_thread(self.rag.search, query, n_results=n),
                timeout=timeout,
            )
        except asyncio.TimeoutError:
            logger.warning("[SoraEngine] RAG timeout (%.1fs)", timeout)
            return []
        except Exception as exc:
            logger.warning("[SoraEngine] RAG search 실패: %s", exc)
            return []

    def _format_rag_block(self, results: list, max_chars_per: int = 250) -> str:
        """RAG 결과를 LLM 친화적 컨텍스트 block 으로 포맷."""
        if not results:
            return ""
        lines = ["[관련 PC 자산 (RAG 검색 결과)]"]
        for i, r in enumerate(results[:5], 1):
            src = r.get("source", "?")
            txt = r.get("text", "").strip().replace("\n", " ")[:max_chars_per]
            lines.append(f"{i}. {src}: {txt}")
        return "\n".join(lines)

    def _should_skip_rag(self, text: str) -> bool:
        """간단한 일상 대화는 RAG 검색 skip."""
        if not text or len(text) < 4:
            return True
        skip_patterns = ["ping", "안녕", "고마워", "ㅎㅎ", "ㅋㅋ", "ㅇㅇ", "응", "네",
                         "오케이", "좋아", "그래", "OK", "ok"]
        t = text.strip()
        if t in skip_patterns:
            return True
        # owner_intent_fastpath / v2_fastpath 가 처리하는 키워드는 RAG 불필요
        if any(k in text for k in ["몇 시", "지금 몇", "오늘 날짜", "내 이메일", "내 GitHub",
                                     "내 도메인", "내 전화"]):
            return True
        return False

    async def _maybe_compress_ledger(self) -> None:
        """40턴 초과 시 first 20턴을 LLM 요약 → summary_block 누적."""
        if not hasattr(self, "_conversation_ledger"):
            return
        if len(self._conversation_ledger) < 38:
            return
        try:
            old = list(self._conversation_ledger)[:20]
            convo = "\n".join(f"{m.get('role')}: {m.get('text','')[:200]}" for m in old)
            prompt = ("아래 대화 내역을 한국어 5-8 줄로 핵심만 요약해. "
                      "사실 / 결정 / 도구 사용 결과 위주로:\n\n" + convo)
            if getattr(self, "_local_llm", None):
                lresp = await self._local_llm.chat(
                    messages=[{"role": "user", "content": prompt}],
                    max_tokens=300,
                    temperature=0.3,
                )
                if lresp and lresp.text:
                    new_summary = "[누적 요약]\n" + lresp.text.strip()
                    if self._summary_block:
                        self._summary_block = self._summary_block + "\n\n" + new_summary
                    else:
                        self._summary_block = new_summary
                    # first 20 제거 후 deque 재구축
                    remaining = list(self._conversation_ledger)[20:]
                    self._conversation_ledger.clear()
                    for m in remaining:
                        self._conversation_ledger.append(m)
                    logger.info("[SoraEngine] context 압축 완료: %d chars", len(new_summary))
        except Exception as exc:
            logger.warning("[SoraEngine] context 압축 실패: %s", exc)

    def _record_tool_result(self, kind, items, query=""):
        """fastpath 결과를 last_tool_result 에 기록."""
        import time as _t
        self._last_tool_result = {"type": kind, "items": items, "ts": _t.time(), "query": query}

    def _get_owner_info(self) -> dict:
        """OWNER_PROFILE.md SSOT 에서 owner 정보 동적 추출 (캐시).

        하드코딩 금지 원칙: 개인 정보는 SSOT 에서만. owner 가 OWNER_PROFILE.md
        갱신 시 sora 가 자동으로 새 값 사용.
        """
        if hasattr(self, "_owner_info_cache") and self._owner_info_cache:
            return self._owner_info_cache
        info = {}
        from pathlib import Path as _P
        candidate_paths = [
            _P("/app/.agent/knowledge/OWNER_PROFILE.md"),
            PROJECT_ROOT / ".agent" / "knowledge" / "OWNER_PROFILE.md",
        ]
        for p in candidate_paths:
            if not p.exists():
                continue
            try:
                content = p.read_text(encoding="utf-8")
                import re as _re_owner
                patterns = {
                    "email": r"\|\s*이메일\s*\|\s*([^|\n]+?)\s*\|",
                    "phone": r"\|\s*전화\s*\|\s*([^|\n]+?)\s*\|",
                    "github": r"\|\s*GitHub\s*\|\s*([^|\n]+?)\s*\|",
                    "domain": r"\|\s*도메인\s*\|\s*([^|\n]+?)\s*\|",
                    "name_ko": r"\|\s*이름\s*\|\s*([^|\n]+?)\s*\|",
                    "telegram_id": r"\|\s*텔레그램\s*chat_id\s*\|\s*([^|\n]+?)\s*\|",
                    "role": r"\|\s*역할\s*\|\s*([^|\n]+?)\s*\|",
                }
                for key, pat in patterns.items():
                    m = _re_owner.search(pat, content)
                    if m:
                        info[key] = m.group(1).strip()
                if info:
                    break
            except Exception:
                continue
        self._owner_info_cache = info
        return info

    async def _try_reference_resolution(self, text):
        """이전 도구 결과 기반 reference 처리 (X만, 그 중)."""
        ref_kw = ["방금", "그 중", "그중", "위에서", "위 메일", "이전 메일",
                  "다시 보여", "중에서", " 만 다시", "그 메일", "이 메일",
                  "첫 번째", "두 번째", "세 번째", "첫번째", "두번째", "세번째",
                  "첫째", "둘째", "셋째", "맨 위", "맨 처음", "가장 위",
                  "마지막 메일", "최근 거", "아까 그", "그 거", "그거"]
        if not any(k in text for k in ref_kw):
            return ""
        last = self._last_tool_result
        if not last:
            return ""
        items = last.get("items", [])
        if last.get("type") in ("mail_list", "mail_unread", "mail_search"):
            import re as _re_r
            target = None
            m = _re_r.search(r"([A-Za-z\uAC00-\uD7AF][\w\uAC00-\uD7AF]{1,25}?)\s*(?:만|만 다시|만 보여|만 보)", text)
            if m: target = m.group(1).strip()
            if not target:
                m = _re_r.search(r"([A-Z][A-Za-z0-9]{2,25})", text)
                if m: target = m.group(1).strip()
            if target:
                tlow = target.lower()
                filtered = [it for it in items
                            if tlow in (it.get("from","")+it.get("subject","")).lower()]
                if filtered:
                    lines = ["이전 결과에서 '" + target + "' 만 필터: " + str(len(filtered)) + "건"]
                    for it in filtered:
                        s = it.get("from","")
                        if "<" in s: s = s.split("<")[0].strip().strip('"')
                        date = it.get("date","")[:10]
                        subj = it.get("subject","")[:60]
                        lines.append("- [" + date + "] " + s[:30] + " | " + subj)
                    return chr(10).join(lines)
                return "이전 메일 목록에서 '" + target + "' 관련 메일을 못 찾았어요."
        # 메일 답장 작성 (last_tool_result 의 첫 메일 본문 기반)
        if last.get("type") in ("mail_list", "mail_unread", "mail_search"):
            if any(k in text for k in ["답장", "회신", "reply", "회답"]):
                items = last.get("items", [])
                if items:
                    target_msg = items[0]
                    try:
                        from src.core.tools.apps_script_tools import gmail_read_v2
                        body_res = await asyncio.to_thread(gmail_read_v2, target_msg.get("id",""))
                        if body_res.get("ok"):
                            body_text = body_res.get("body","")[:1500]
                            sender = body_res.get("from","")[:50]
                            subj = body_res.get("subject","")[:80]
                            llm_prompt = ("아래 메일에 답장을 한국어 격식체 5-8줄로 작성해줘. 서명은 [대표님]:\n\n"
                                          f"From: {sender}\nSubject: {subj}\n\n{body_text}")
                            # ⭐ Local LLM (Qwen3-14B) primary — Sora 아키텍처 원칙 (cloud 는 fallback)
                            draft_text = ""
                            if getattr(self, "_local_llm", None):
                                try:
                                    lresp = await asyncio.wait_for(
                                        self._local_llm.chat(
                                            messages=[{"role": "user", "content": llm_prompt}],
                                            max_tokens=500,
                                            temperature=0.6,
                                        ),
                                        timeout=90,
                                    )
                                    if lresp and lresp.text:
                                        draft_text = lresp.text.strip()
                                        if draft_text:
                                            return ("✉️ '" + sender + "' 메일 답장 초안:\n\n" + draft_text)
                                except asyncio.TimeoutError:
                                    logger.warning("[SoraEngine] Local LLM 답장 timeout 90s, Gemini cloud fallback")
                                except Exception as lerr:
                                    logger.warning("[SoraEngine] Local LLM 답장 실패: %s, Gemini fallback", str(lerr)[:120])
                            # Local fail 시 Gemini cloud fallback (.env SORA_GEMINI_FALLBACK_MODELS, 하드코딩 금지)
                            if not draft_text:
                                gemini_chain = [GEMINI_MODEL]
                                fallback_env = os.getenv("SORA_GEMINI_FALLBACK_MODELS", "")
                                for m in fallback_env.split(","):
                                    m = m.strip()
                                    if m and m not in gemini_chain:
                                        gemini_chain.append(m)
                                for gm in gemini_chain:
                                    try:
                                        gen_resp = await asyncio.wait_for(
                                            asyncio.to_thread(
                                                self._genai_client.models.generate_content,
                                                model=gm,
                                                contents=[llm_prompt],
                                                config=self._genai_types.GenerateContentConfig(
                                                    temperature=0.6,
                                                    max_output_tokens=500,
                                                ),
                                            ),
                                            timeout=15,
                                        )
                                        draft_text = (getattr(gen_resp, "text", "") or "").strip()
                                        if draft_text:
                                            return ("✉️ '" + sender + "' 메일 답장 초안:\n\n" + draft_text)
                                    except asyncio.TimeoutError:
                                        logger.warning("[SoraEngine] Gemini %s timeout, next", gm)
                                        continue
                                    except Exception as gerr:
                                        logger.warning("[SoraEngine] Gemini %s fail: %s, next", gm, str(gerr)[:80])
                                        continue
                            if not draft_text:
                                return "✉️ 답장 초안 생성에 시간이 너무 걸리네요. 잠시 후 다시 시도해주세요."
                    except Exception as exc:
                        logger.warning("[SoraEngine] reply draft 실패: %s", exc)
        if last.get("type") in ("cal_events", "cal_today"):
            from datetime import datetime as _dt_r, timedelta as _td_r
            tomorrow = (_dt_r.now().date() + _td_r(days=1)).isoformat()
            if "내일" in text:
                fil = [e for e in items if e.get("start","")[:10] == tomorrow]
                if not fil: return "이전 결과 중 내일 일정은 없어요."
                lines = ["📅 이전 결과에서 내일 일정"]
                for e in fil[:10]:
                    s = e.get("start","")[:16].replace("T", " ")
                    lines.append("- " + s + " · " + e.get("summary","(제목없음)"))
                return chr(10).join(lines)
        return ""

    async def _v2_fastpath(self, text: str) -> str:
        import os, asyncio as _asyncio, re as _re
        msg_lower = text.lower()
        # 실시간 데이터 hallucination 방지
        realtime_kw = ["환율", "달러로", "원으로", "USD", "엔화", "위안", "주가", "코스피", "비트코인 시세", "암호화폐 시세"]
        if any(k in text for k in realtime_kw):
            return ("⚠️ 환율/시세는 실시간 데이터라 외부 API 없이는 정확히 답할 수 없어요. "
                    "네이버 환율 검색 또는 yahoo finance 에서 직접 확인하세요. "
                    "외부 API 연결되면 즉시 답해드릴게요.")
        if not (os.getenv("SORA_APPS_SCRIPT_URL") and os.getenv("SORA_APPS_SCRIPT_TOKEN")):
            return ""

        # ── 복합 요청 (일정 + 메일 동시) ──
        if ("일정" in text or "캘린더" in text or "스케줄" in text) and any(k in text for k in ["메일", "이메일", "inbox", "받은편지"]):
            try:
                from src.core.tools.apps_script_tools import calendar_today_v2, calendar_events_v2, gmail_unread_v2, gmail_inbox_v2
                # 1. 일정
                if "오늘" in msg_lower:
                    cal_res = await _asyncio.to_thread(calendar_today_v2)
                else:
                    cal_res = await _asyncio.to_thread(calendar_events_v2, 7)
                cal_lines = []
                if cal_res.get("ok") and cal_res.get("items"):
                    cal_lines.append("📅 일정")
                    for ev in cal_res["items"][:5]:
                        s = ev.get("start","")[:16].replace("T"," ")
                        cal_lines.append("- " + s + " · " + ev.get("summary","(제목없음)"))
                else:
                    cal_lines.append("📅 일정 없음")
                # 2. 메일
                if any(k in text for k in ["안 읽", "안읽", "unread", "새 메일"]):
                    mail_res = await _asyncio.to_thread(gmail_unread_v2, 5)
                    mail_header = "📧 안 읽은 메일"
                else:
                    mail_res = await _asyncio.to_thread(gmail_inbox_v2, 5)
                    mail_header = "📧 최근 메일"
                mail_lines = []
                if mail_res.get("ok") and mail_res.get("items"):
                    mail_lines.append("")
                    mail_lines.append(mail_header)
                    for it in mail_res["items"][:5]:
                        s = it.get("from","")
                        if "<" in s: s = s.split("<")[0].strip().strip(chr(34))
                        mail_lines.append("- " + s[:25] + " | " + it.get("subject","")[:50])
                else:
                    mail_lines.extend(["", mail_header + " 없음"])
                return chr(10).join(cal_lines + mail_lines)
            except Exception:
                pass

        # ── Calendar list 명확 매칭 (이벤트 X, 캘린더 등록 목록) ──
        if ("캘린더 목록" in text or "캘린더 리스트" in text or
            ("내 캘린더" in text and ("목록" in text or "리스트" in text or "전부" in text or "모두" in text))):
            try:
                from src.core.tools.apps_script_tools import calendar_list_v2
                res = await _asyncio.to_thread(calendar_list_v2)
                if res.get("ok"):
                    items = res.get("items", [])
                    if not items:
                        return "등록된 캘린더가 없어요."
                    parts = ["📚 등록된 캘린더 " + str(len(items)) + "개"]
                    for c in items:
                        mark = "⭐ " if c.get("is_default") else ""
                        parts.append("- " + mark + c.get("name", "")[:60])
                    return chr(10).join(parts)
            except Exception:
                pass

        # Calendar
        cal_kw = ["일정", "캘린더", "calendar", "스케줄", "약속", "미팅", "행사"]
        write_kw = ["추가", "등록", "만들", "생성", "삭제", "취소", "변경", "수정", "잡아", "예약", "옮기"]
        chat_markers = ["기분", "어때", "농담", "날씨"]
        has_cal = any(k in msg_lower for k in cal_kw)
        if has_cal and not any(k in msg_lower for k in write_kw) and not any(k in msg_lower for k in chat_markers):
            try:
                from src.core.tools.apps_script_tools import calendar_today_v2, calendar_events_v2
                if "오늘" in msg_lower:
                    res = await _asyncio.to_thread(calendar_today_v2)
                elif "내일" in msg_lower:
                    res = await _asyncio.to_thread(calendar_events_v2, 2)
                elif "다음주" in msg_lower or "다음 주" in msg_lower:
                    res = await _asyncio.to_thread(calendar_events_v2, 14)
                elif "이번주" in msg_lower or "이번 주" in msg_lower:
                    res = await _asyncio.to_thread(calendar_events_v2, 7)
                else:
                    res = await _asyncio.to_thread(calendar_events_v2, 7)
                if res.get("ok"):
                    items = res.get("items", [])
                    self._record_tool_result("cal_today" if "오늘" in msg_lower else "cal_events", items, text)
                    if "내일" in msg_lower:
                        from datetime import datetime as _d, timedelta as _t
                        target = (_d.now().date() + _t(days=1)).isoformat()
                        items = [e for e in items if e.get("start","")[:10] == target]
                    if not items:
                        if "오늘" in msg_lower: return "오늘은 일정이 없어요. 😊"
                        if "내일" in msg_lower: return "내일은 일정이 없어요. 😊"
                        return "다가올 일정이 없어요. 😊"
                    header = "📅 일정"
                    if "오늘" in msg_lower: header = "📅 오늘 일정"
                    elif "내일" in msg_lower: header = "📅 내일 일정"
                    elif "이번주" in msg_lower or "이번 주" in msg_lower: header = "📅 이번주 일정"
                    parts = [header]
                    for ev in items[:10]:
                        s = ev.get("start","")[:16].replace("T"," ")
                        title = ev.get("summary","(제목 없음)")
                        loc = ev.get("location","")
                        line = f"- {s} · {title}"
                        if loc: line += f" @ {loc[:30]}"
                        parts.append(line)
                    return chr(10).join(parts)
            except Exception:
                pass
        # 메일 본문 + 어제 메일
        if ("본문" in text or "내용 보여" in text or "내용 알려" in text):
            try:
                from src.core.tools.apps_script_tools import gmail_search_v2, gmail_read_v2
                sender = None
                m = _re.search(r"([A-Za-z가-힣][\w가-힣]{1,30}?)(?:이|가)?\s*(?:보낸|메일|메일의)", text)
                if m: sender = m.group(1)
                if not sender:
                    m = _re.search(r"([A-Z][A-Za-z0-9]{2,30})", text)
                    if m: sender = m.group(1)
                if sender:
                    for tr in ["이","가","의"]:
                        if sender.endswith(tr) and len(sender)>len(tr)+1:
                            sender = sender[:-len(tr)]; break
                if sender:
                    sr = await _asyncio.to_thread(gmail_search_v2, "from:" + sender, 1)
                    if sr.get("ok") and sr.get("items"):
                        mid = sr["items"][0]["id"]
                        body = await _asyncio.to_thread(gmail_read_v2, mid)
                        if body.get("ok"):
                            from_s = body.get("from","")[:50]
                            subj_s = body.get("subject","")
                            body_s = body.get("body","")[:1500]
                            return "📧 " + sender + " 메일 본문" + chr(10) + chr(10) + "From: " + from_s + chr(10) + "Subject: " + subj_s + chr(10) + chr(10) + body_s
            except Exception as ee:
                pass

        if "어제 받은" in text or "어제 메일" in text:
            try:
                from src.core.tools.apps_script_tools import gmail_search_v2
                res = await _asyncio.to_thread(gmail_search_v2, "newer_than:2d older_than:1d", 10)
                if res.get("ok"):
                    items = res.get("items", [])
                    if not items:
                        return "어제 받은 메일이 없어요."
                    lines = ["📧 어제 받은 메일"]
                    for it in items[:10]:
                        s = it.get("from","")
                        if "<" in s: s = s.split("<")[0].strip().strip(chr(34))
                        lines.append("- " + s[:30] + " | " + it.get("subject","")[:60])
                    return chr(10).join(lines)
            except Exception:
                pass

        # Email
        mail_kw = ["이메일", "메일", "인박스", "inbox", "gmail", "받은편지", "받은 편지"]
        unread_kw = ["안 읽", "안읽", "미열람", "unread", "새 메일", "새메일"]
        send_kw = ["보내", "전송", "발송", "답장"]
        # 요약/분석 같은 reasoning 의도면 fastpath 우회 (LLM 이 직접 처리)
        reason_kw = ["요약", "한줄", "한 줄", "분석", "평가", "정리해"]
        if any(k in text for k in reason_kw):
            return ""  # LLM chat path 로 위임
        search_markers = ["이 보낸", "가 보낸", "한테서", "한테온", "부터 온", "에서 온", "에서온", "발신", "검색", "찾아"]
        has_mail = any(k in msg_lower for k in mail_kw) or any(k in msg_lower for k in unread_kw)

        # 발신자 / 키워드 검색 의도
        if has_mail and any(k in text for k in search_markers) and not any(k in msg_lower for k in send_kw):
            try:
                from src.core.tools.apps_script_tools import gmail_search_v2
                # 발신자 추출 (한글 조사 제거 포함)
                sender = None
                # Pattern 1: "X(이|가) 보낸" / "X(이|가)서 온"
                m = _re.search(r"([A-Za-z가-힣][\w가-힣]{1,30}?)(?:이|가)?\s*보낸", text)
                if m: sender = m.group(1)
                if not sender:
                    # Pattern 2: "X에서/한테/로부터 (온|받은)"
                    m = _re.search(r"([A-Za-z가-힣][\w가-힣]{1,30}?)(?:에서|에서온|한테|한테서|로부터|발|발신)", text)
                    if m: sender = m.group(1)
                if not sender:
                    # Pattern 3: 대문자로 시작하는 영문 단어 (브랜드명)
                    m = _re.search(r"([A-Z][A-Za-z0-9]{2,30})", text)
                    if m: sender = m.group(1)
                # 한글 조사가 sender 끝에 붙은 경우 제거
                if sender:
                    for trailing in ["이", "가", "에서", "한테", "로부터", "의"]:
                        if sender.endswith(trailing) and len(sender) > len(trailing) + 1:
                            sender = sender[:-len(trailing)]
                            break
                    sender = sender.strip()
                query = ("from:" + sender) if sender else "in:inbox"
                limit = 10
                res = await _asyncio.to_thread(gmail_search_v2, query, limit)
                if res.get("ok"):
                    items = res.get("items", [])
                    if not items:
                        return f"{sender or query} 관련 메일을 못 찾았어요." if sender else "검색 결과가 없어요."
                    header = f"📧 {sender} 발신 메일 {len(items)}건" if sender else f"📧 검색 결과 {len(items)}건"
                    parts = [header]
                    for it in items[:limit]:
                        s = it.get("from", "")
                        if "<" in s and ">" in s:
                            n = s.split("<")[0].strip().strip(chr(34))
                            if not n: n = s.split("<")[1].split(">")[0]
                            s = n
                        subj = it.get("subject", "(제목 없음)")[:60]
                        date = it.get("date", "")[:10]
                        mark = "🟢 " if it.get("unread") else ""
                        parts.append(f"- {mark}[{date}] {s[:30]} | {subj}")
                    return chr(10).join(parts)
            except Exception:
                pass

        if has_mail and not any(k in msg_lower for k in send_kw):
            try:
                from src.core.tools.apps_script_tools import gmail_inbox_v2, gmail_unread_v2
                is_unread = any(k in msg_lower for k in unread_kw)
                limit = 5
                if "10" in text or "많" in text: limit = 10
                elif "3" in text: limit = 3
                if is_unread:
                    res = await _asyncio.to_thread(gmail_unread_v2, limit)
                else:
                    res = await _asyncio.to_thread(gmail_inbox_v2, limit)
                if res.get("ok"):
                    items = res.get("items", [])
                    self._record_tool_result("mail_unread" if is_unread else "mail_list", items, text)
                    if not items:
                        return "안 읽은 메일이 없어요. 😊" if is_unread else "받은 메일이 없어요. 😊"
                    header = "📧 안 읽은 메일" if is_unread else "📧 최근 메일"
                    parts = [header]
                    for it in items[:limit]:
                        sender = it.get("from", "")
                        if "<" in sender and ">" in sender:
                            name = sender.split("<")[0].strip().strip(chr(34))
                            if not name: name = sender.split("<")[1].split(">")[0]
                            sender = name
                        subj = it.get("subject", "(제목 없음)")[:60]
                        date = it.get("date","")[:10]
                        mark = "🟢 " if it.get("unread") else ""
                        parts.append(f"- {mark}[{date}] {sender[:30]} | {subj}")
                    return chr(10).join(parts)
            except Exception:
                pass
        return ""

    async def process(
        self,
        text: str,
        file_path: str = None,
        on_progress: ProgressCallback = None,
    ) -> str:
        """텍스트(+파일) 입력 → AI 응답 (도구 자동 실행 포함).

        Args:
            text: 사용자 메시지
            file_path: 첨부 파일 경로 (선택)
            on_progress: 도구 실행 진행 콜백 (선택, Phase 2 WebSocket용)

        Returns:
            AI 응답 텍스트
        """
        # ── OTel root span (W2 Sora Enterprise) ──
        # graceful degradation — OTel 미가용 시 no-op
        try:
            from src.core.observability.otel_setup import span as _otel_span, get_current_trace_id as _get_tid
            _process_span_cm = _otel_span(
                "sora.process",
                input_text_len=len(text or ""),
                has_file=bool(file_path),
                source="telegram_or_dashboard",
            )
        except Exception:
            from contextlib import nullcontext
            _process_span_cm = nullcontext()
            _get_tid = lambda: ""  # type: ignore

        with _process_span_cm:
            return await self._process_inner(text, file_path, on_progress)

    async def _process_inner(
        self,
        text: str,
        file_path: str = None,
        on_progress: ProgressCallback = None,
    ) -> str:
        """process() 본체 — OTel root span 안에서 실행. W2.T1 분리."""
        # ── v2 Fastpath: Gmail/Calendar via Apps Script Bridge (OAuth 우회) ──
        # User ledger
        if text:
            try:
                self._conversation_ledger.append({"role": "user", "text": text[:1500], "ts": time.time()})
            except Exception: pass

        if not file_path and text:
            # Reference resolution 우선
            try:
                ref_reply = await self._try_reference_resolution(text)
                if ref_reply:
                    logger.info(f"[SoraEngine] reference_resolution hit: {len(ref_reply)} chars")
                    self._conversation_ledger.append({"role": "assistant", "text": ref_reply[:1500], "ts": time.time()})
                    return ref_reply
            except Exception as rerr:
                logger.warning(f"[SoraEngine] reference_resolution skip: {rerr}")
            try:
                owner_reply = await self._owner_intent_fastpath(text)
                if owner_reply:
                    logger.info(f"[SoraEngine] owner_intent_fastpath hit: {len(owner_reply)} chars")
                    self._conversation_ledger.append({"role": "assistant", "text": owner_reply[:1500], "ts": time.time()})
                    return owner_reply
            except Exception as oerr:
                logger.warning(f"[SoraEngine] owner_intent_fastpath skip: {oerr}")
            try:
                v2_reply = await self._v2_fastpath(text)
                if v2_reply:
                    logger.info(f"[SoraEngine] v2_fastpath hit: {len(v2_reply)} chars")
                    self._conversation_ledger.append({"role": "assistant", "text": v2_reply[:1500], "ts": time.time()})
                    return v2_reply
            except Exception as v2err:
                logger.warning(f"[SoraEngine] v2_fastpath skip: {v2err}")

            # RAG 검색 + LLM path 진입 직전 augment
            try:
                if not self._should_skip_rag(text):
                    rag_results = await self._rag_search(text, n=3, timeout=1.5)
                    if rag_results:
                        rag_block = self._format_rag_block(rag_results)
                        if rag_block:
                            text = rag_block + "\n\n[질문]\n" + text
                            logger.info(f"[SoraEngine] RAG inject: {len(rag_results)} hits, +{len(rag_block)} chars")
            except Exception as rag_err:
                logger.warning(f"[SoraEngine] RAG inject skip: {rag_err}")

            # 컨텍스트 압축 trigger
            try:
                await self._maybe_compress_ledger()
            except Exception:
                pass

        # ── Hook: SessionStart (최초 1회) ──
        if _HOOKS_AVAILABLE and not self._hooks_initialized:
            try:
                self._session_context = on_session_start(self._session_id)
                self._hooks_initialized = True
                logger.info("[SoraEngine] Hook SessionStart 완료")
            except Exception as hook_err:
                logger.warning(f"[SoraEngine] SessionStart hook 실패 (무시): {hook_err}")

        # ── Hook: UserPromptSubmit ──
        _hook_result = None
        if _HOOKS_AVAILABLE:
            try:
                _hook_result = on_user_prompt_submit(
                    raw_text=text,
                    session_id=self._session_id,
                    device_tier="personal-root",
                    core_memory_block=self._session_context.get("core_memory_block", ""),
                )
                # augmented text (time context + core memory prepended)
                text = _hook_result.get("augmented_text", text)
                logger.debug("[SoraEngine] Hook UserPromptSubmit: intent=%s",
                             _hook_result.get("owner_intent", {}).primary_intent
                             if hasattr(_hook_result.get("owner_intent", {}), "primary_intent")
                             else "unknown")
            except Exception as hook_err:
                logger.warning(f"[SoraEngine] UserPromptSubmit hook 실패 (무시): {hook_err}")

        # God Mode: 에피소드 기록 시작
        _episode_id = None
        if self._eternal:
            try:
                _episode_id = self._eternal.start_episode({
                    "type": "chat", "source": "sora_engine", "query": text[:200]
                })
            except Exception:
                pass

        _t_start = time.time()

        try:
            # 기억에 사용자 메시지 저장
            suffix = f" [📎 {Path(file_path).name}]" if file_path else ""
            self.memory.add_message("user", text + suffix)
            self._last_user_query = text

            # ── 대화 히스토리 자동 압축 ──
            # 멀티스텝 감지/TaskPlanner 위임은 brain/worker.py에서 처리 (단일 경로 원칙)
            await self._maybe_compress_history()

            # ── Gemini 호출 (도구 자동 실행 포함) ──
            if on_progress:
                try:
                    await on_progress("gemini", "AI 처리 중...")
                except Exception:
                    pass

            response = await self._call_gemini(text, file_path=file_path)

            if response is None:
                return "😓 잠시 후 다시 말씀해주세요!"

            # 응답 텍스트 추출
            reply = ""
            try:
                reply = response.text
                logger.debug(f"[SoraEngine] response.text={reply[:100] if reply else '(empty)'}")
            except ValueError as ve:
                # AFC 도구 실행 후 텍스트 없는 경우 → parts에서 추출
                try:
                    for part in response.candidates[0].content.parts:
                        if hasattr(part, "text") and part.text:
                            reply += part.text
                        elif hasattr(part, "function_response"):
                            # 도구 실행 결과를 직접 포함
                            fr = part.function_response
                            fn_name = getattr(fr, "name", "도구")
                            fn_result = getattr(fr, "response", {})
                            if isinstance(fn_result, dict):
                                reply += json.dumps(fn_result, ensure_ascii=False, indent=2)
                            else:
                                reply += str(fn_result)
                except Exception:
                    pass
            except Exception as ex:
                reply = f"(응답 파싱 실패: {ex})"

            if not reply:
                logger.info(f"[SoraEngine] 빈 응답 — history에서 도구 결과 추출 시도")
                # 마지막 시도: 전체 히스토리에서 최근 function_response 추출
                try:
                    history = getattr(self.chat, '_curated_history', None) or getattr(self.chat, 'history', [])
                    for msg in reversed(history[-5:]):
                        for part in getattr(msg, 'parts', []):
                            if hasattr(part, 'function_response'):
                                fr = part.function_response
                                result_data = getattr(fr, 'response', {})
                                if result_data:
                                    reply = json.dumps(result_data, ensure_ascii=False, indent=2) if isinstance(result_data, dict) else str(result_data)
                                    break
                        if reply:
                            break
                except Exception:
                    pass

            if not reply:
                # history에서 도구 결과를 JSON으로 반환 (Brain Worker가 요약)
                logger.info("[SoraEngine] 텍스트 없음 — 도구 결과 JSON 반환")
                try:
                    history = getattr(self.chat, '_curated_history', None) or getattr(self.chat, 'history', [])
                    tool_data = []
                    for msg in reversed(history[-10:]):
                        for part in getattr(msg, 'parts', []):
                            if hasattr(part, 'function_response'):
                                fr = part.function_response
                                tool_data.append({
                                    "tool": getattr(fr, 'name', 'unknown'),
                                    "result": getattr(fr, 'response', {}),
                                })
                            elif hasattr(part, 'function_call'):
                                fc = part.function_call
                                tool_data.append({
                                    "called": getattr(fc, 'name', 'unknown'),
                                    "args": dict(getattr(fc, 'args', {})) if getattr(fc, 'args', None) else {},
                                })
                        if tool_data:
                            break
                    if tool_data:
                        reply = json.dumps(tool_data, ensure_ascii=False, default=str)
                        logger.info(f"[SoraEngine] 도구 결과 추출 성공: {len(tool_data)}건")
                except Exception as ex:
                    logger.warning(f"[SoraEngine] 도구 결과 추출 실패: {ex}")

            if not reply:
                reply = "명령을 처리했습니다."

            tool_events = self._extract_recent_tool_events()

            # ── Phase 2: 복합 요청 결과 조정 (Result Reconciliation) ──
            # 2개 이상 툴이 호출된 경우 체크리스트 응답을 우선 생성한다.
            # 실패하거나 단일 툴 호출이면 빈 문자열을 반환하므로 기존 경로로 fallthrough.
            _checklist_reply = ""
            try:
                from src.core.reconciliation import build_reconciliation_response
                _checklist_reply = build_reconciliation_response(
                    self._last_user_query, tool_events
                )
            except Exception as _rec_err:
                logger.debug("[SoraEngine] reconciliation 건너뜀: %s", _rec_err)

            if _checklist_reply:
                reply = _checklist_reply
            else:
                tool_summary, action_count, failure_count, result_count = self._build_tool_execution_summary(tool_events)
                if tool_summary:
                    reply = self._reconcile_owner_reply(
                        reply,
                        tool_summary,
                        action_count=action_count,
                        failure_count=failure_count,
                        result_count=result_count,
                    )

            # 응답 기억 저장
            self.memory.add_message("assistant", reply)

            # 성공 → 에러 카운터 리셋
            self._consecutive_errors = 0

            # 레이턴시 측정
            _latency_ms = (time.time() - _t_start) * 1000

            # ── Hook: PostToolUse (audit + events) ──
            if _HOOKS_AVAILABLE and tool_events:
                try:
                    from src.core.contracts.sora_contracts import ToolCallEnvelope, ToolCallResult, Tier
                    for te in tool_events[:10]:
                        envelope = ToolCallEnvelope(
                            tool=te.get("tool", "unknown"),
                            operation=te.get("name", "unknown"),
                            arguments=te.get("args", {}),
                            tier=Tier.READ,
                        )
                        result = ToolCallResult(
                            call_id=envelope.call_id,
                            ok=te.get("success", True),
                            error=te.get("error"),
                            latency_ms=int(_latency_ms / max(len(tool_events), 1)),
                        )
                        on_post_tool_use(envelope, result)
                except Exception as hook_err:
                    logger.debug(f"[SoraEngine] PostToolUse hook: {hook_err}")

            logger.info(
                f"[SoraEngine] 처리 완료 ({_latency_ms:.0f}ms)"
            )

            # God Mode: 에피소드에 성공 기록
            if self._eternal and _episode_id:
                try:
                    self._eternal.record(_episode_id, "reply", {"reply": reply[:300]})
                except Exception:
                    pass

            # 2026-05-06: telegram → sora_engine.process() 직접 경로의 audit log 보강
            # worker.py 경로 (cron probe) 외에 owner 실 텔레그램 대화도 latency 측정 대상
            # KR/EN 혼합 대략 3 chars/token 추정 (Gemini cap 1500 효과 측정용)
            try:
                from src.core.audit import get_audit_logger
                _est_in = max(1, len(text or "") // 3)
                _est_out = max(1, len(reply or "") // 3)
                _model_tag = "local" if locals().get("_used_local") else "gemini"
                _strategy = f"sora_engine_direct/{_model_tag}"
                _req_id = locals().get("_episode_id") or f"se-{int(_t_start*1000)%1_000_000_000}"
                # AuditLogger.log 가 async 라면 fire-and-forget 시도; 동기면 그냥 호출
                _al = get_audit_logger()
                _audit_call = _al.log(
                    request_id=str(_req_id),
                    user_message=text or "",
                    tools_executed=[(te.get("tool", "?") if isinstance(te, dict) else str(te)) for te in (tool_events or [])][:10],
                    duration_ms=_latency_ms,
                    strategy=_strategy,
                    tokens_in=_est_in,
                    tokens_out=_est_out,
                )
                if asyncio.iscoroutine(_audit_call):
                    asyncio.create_task(_audit_call)
            except Exception as _audit_err:
                logger.debug(f"[SoraEngine] audit log skip: {_audit_err}")

            return reply

        except Exception as e:
            self._consecutive_errors += 1
            _latency_ms = (time.time() - _t_start) * 1000
            error_msg = f"⚠️ 처리 중 오류: {str(e)[:300]}"
            logger.error(
                f"[SoraEngine] {error_msg} "
                f"(연속 에러 {self._consecutive_errors}/{self._MAX_CONSECUTIVE_ERRORS}, "
                f"{_latency_ms:.0f}ms)",
                exc_info=True,
            )

            # 텔레메트리에 에러 기록
            self._track_usage(None, latency_ms=_latency_ms, is_error=True)

            # God Mode: 에피소드에 에러 기록
            if self._eternal and _episode_id:
                try:
                    self._eternal.record(_episode_id, "error", {"error": str(e)[:300]})
                except Exception:
                    pass

            # 채팅 세션 재초기화 (오류 복구)
            try:
                self.chat = self._genai_client.chats.create(
                    model=GEMINI_MODEL,
                    config=self._chat_config,
                )
                logger.info("[SoraEngine] 채팅 세션 재초기화 완료")
            except Exception:
                pass

            # 연속 에러가 임계치 이하면 1회 자동 재시도
            if self._consecutive_errors < self._MAX_CONSECUTIVE_ERRORS:
                logger.info(
                    f"[SoraEngine] 세션 리셋 후 1회 재시도 "
                    f"({self._consecutive_errors}/{self._MAX_CONSECUTIVE_ERRORS})"
                )
                await asyncio.sleep(2)  # 쿨다운
                try:
                    return await self.process(text, file_path, on_progress)
                except Exception as retry_err:
                    logger.error(f"[SoraEngine] 재시도도 실패: {retry_err}")
                    return f"⚠️ 재시도 실패: {str(retry_err)[:200]}"

            # 임계치 초과 → 쿨다운 모드
            logger.warning(
                f"[SoraEngine] 연속 {self._consecutive_errors}회 에러 — "
                f"쿨다운 모드 진입"
            )
            return (
                f"😓 연속 {self._consecutive_errors}회 오류가 발생했습니다. "
                f"잠시 후 다시 말씀해주세요.\n\n"
                f"마지막 오류: {str(e)[:150]}"
            )

        finally:
            # God Mode: 에피소드 종료
            if self._eternal and _episode_id:
                try:
                    self._eternal.end_episode(_episode_id)
                except Exception:
                    pass

    def reset_session(self):
        """채팅 세션 초기화 (오류 복구용)"""
        self.chat = self._genai_client.chats.create(
            model=GEMINI_MODEL,
            config=self._chat_config,
        )
        logger.info("[SoraEngine] 채팅 세션 수동 리셋")


# ══════════════════════════════════════════════════
# Output filter wrapper - identity leak 방어 (보안 critical)
# ══════════════════════════════════════════════════
try:
    # 2026-05-04 P0 fix: 직전 wiring 은 module top-level 에서 immediate import 했으나
    # output_filter 가 _load_owner_whitelist_from_ssot 안에서 sora_engine.PROJECT_ROOT 를
    # reverse-import 하면서 circular import 발생 → wiring 매 부팅마다 fail.
    # → lazy import (wrapper 호출 시점) 로 변경. 모든 응답 redact 활성화.
    _SoraEngine_original_process = SoraEngine.process

    async def _SoraEngine_filtered_process(self, text: str, file_path: str = None, on_progress=None) -> str:
        raw = await _SoraEngine_original_process(self, text, file_path, on_progress)
        raw_str = str(raw or "")
        # fastpath 응답 (emoji 시작) 은 외부 data 인용 가능하므로 filter 우회
        fastpath_emojis = ("📅", "📧", "📚", "🎯", "📌", "⚡", "🤖", "🛠️", "👤", "🌐", "📱", "🐙", "⚠️", "☀️", "🗓️", "✉️", "📨", "📬")
        if raw_str and raw_str.startswith(fastpath_emojis):
            return raw_str
        try:
            # lazy import: 호출 시점이라 sora_engine 모듈 이미 loaded → circular 없음
            from src.core.security.output_filter import filter_output as _filt
            filtered, _warnings = _filt(raw_str, strict=True)
            if _warnings:
                logger.info(f"[SoraEngine] output_filter blocked: {_warnings[:3]}")
            return filtered
        except Exception as _ferr:
            logger.warning(f"[SoraEngine] output_filter passthrough: {_ferr}")
            return raw

    SoraEngine.process = _SoraEngine_filtered_process
    logger.info("[SoraEngine] output_filter wired into process() with lazy import (P0 secret leak guard active)")
except Exception as _filter_wire_err:
    logger.warning(f"[SoraEngine] output_filter wrapper setup skipped: {_filter_wire_err}")


# ══════════════════════════════════════════════════
# 싱글턴
# ══════════════════════════════════════════════════

_engine: Optional[SoraEngine] = None
_engine_lock = asyncio.Lock()


def get_sora_engine() -> SoraEngine:
    """SoraEngine 싱글턴 인스턴스 반환."""
    global _engine
    if _engine is None:
        _engine = SoraEngine()
    return _engine


def get_memory() -> AssistantMemory:
    """기억 시스템 싱글턴 반환 (도구 모듈에서 참조용)."""
    return _memory