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
from typing import Callable, Optional

from dotenv import load_dotenv

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
        except Exception:
            pass

    def add_message(self, role: str, text: str):
        """대화 기록 추가 (최근 200개 유지)"""
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

        # ── 백그라운드 초기화 상태 ──
        self._init_complete = False
        self._init_lock = asyncio.Lock()

        # ── 에러 복구 ──
        self._consecutive_errors = 0
        self._MAX_CONSECUTIVE_ERRORS = 3

        # ── 무거운 컴포넌트 → None으로 선언만 (lazy init) ──
        self.bible_loader = None
        self.rag = None
        self.retriever = None
        self.prompt_builder = None
        self.task_planner = None
        self._eternal = None
        self._autonomous_loop = None

        # ── Gemini Chat 생성 (가벼움 — 즉시 완료) ──
        self._chat_config = types.GenerateContentConfig(
            system_instruction=self._build_system_prompt(),
            tools=ALL_TOOLS,
            automatic_function_calling=types.AutomaticFunctionCallingConfig(
                disable=False,
            ),
        )
        self.chat = self._genai_client.chats.create(
            model=GEMINI_MODEL,
            config=self._chat_config,
        )
        logger.info(f"[SoraEngine] 즉시 초기화 완료 — {len(ALL_TOOLS)} 도구, 모델={GEMINI_MODEL} (무거운 컴포넌트는 백그라운드 로딩 예정)")

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
            "한국어로 답변하세요. 대표님의 지시를 최우선으로 실행하세요."
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

        max_retries = 3
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
                    wait_sec = 10 * (2 ** attempt)
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
                    "http://localhost:11434/api/generate",
                    data=json.dumps({
                        "model": "qwen2.5:14b",
                        "prompt": content,
                        "stream": False,
                    }).encode(),
                    headers={"Content-Type": "application/json"},
                )
                resp_data = await asyncio.to_thread(
                    lambda: urllib.request.urlopen(req, timeout=30).read()
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

    # ── 핵심 공개 API ──

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

            # ── 멀티스텝 감지 → TaskPlanner 위임 ──
            if (self.task_planner
                    and not file_path
                    and self.task_planner.is_multi_step(text)):
                logger.info("[SoraEngine] 멀티스텝 감지 → TaskPlanner 위임")
                if on_progress:
                    try:
                        await on_progress("task_planner", "멀티스텝 계획 수립 중...")
                    except Exception:
                        pass
                plan = await self.task_planner.plan_and_execute(text)
                reply = plan.summary()
                self.memory.add_message("assistant", reply)
                return reply

            # ── 대화 히스토리 자동 압축 ──
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
            except ValueError:
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
                reply = "명령을 처리했습니다."

            # 응답 기억 저장
            self.memory.add_message("assistant", reply)

            # 성공 → 에러 카운터 리셋
            self._consecutive_errors = 0

            # 레이턴시 측정
            _latency_ms = (time.time() - _t_start) * 1000
            logger.info(
                f"[SoraEngine] 처리 완료 ({_latency_ms:.0f}ms)"
            )

            # God Mode: 에피소드에 성공 기록
            if self._eternal and _episode_id:
                try:
                    self._eternal.record(_episode_id, "reply", {"reply": reply[:300]})
                except Exception:
                    pass

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
