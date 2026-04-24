# -*- coding: utf-8 -*-
"""
Sora v2.0 — Brain Worker

별도 프로세스에서 실행. Redis 큐에서 요청을 꺼내 LLM을 호출하고 결과를 publish.
Gateway(FastAPI)의 이벤트 루프를 절대 블로킹하지 않음.

Architecture:
    [Redis Queue] --dequeue--> [Brain Worker] --LLM call--> [publish result]
                                     |
                                     ├── Gemini (도구 호출, 멀티모달)
                                     ├── Claude (복잡한 추론) [Phase 3]
                                     └── Ollama (로컬 폴백)

Usage:
    python -m src.core.brain.worker
"""
import asyncio
import json
import logging
import os
import signal
import sys
import time
from pathlib import Path

# 경로 설정
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
WORKER_PID_PATH = PROJECT_ROOT / "brain_worker.pid"
WORKER_MATCHERS = ("src.core.brain.worker", "brain\\worker.py")

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

from src.core.ops_telegram_alerts import (
    notify_agent_approval_requested,
    notify_agent_approval_result,
)
from src.core.governance.execution_gate import evaluate_text_execution_gate
from src.core.runtime.single_instance import claim_single_instance
from src.core.time_context import build_time_context_block, needs_explicit_time_context

# 로깅
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [Brain] %(levelname)s — %(message)s",
)
logger = logging.getLogger("neo.brain.worker")

# ── 설정 ──
GEMINI_API_KEY = os.getenv("SORA_GEMINI_API_KEY") or os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("SORA_GEMINI_MODEL", "gemini-2.5-flash")
TELEGRAM_BOT_TOKEN = os.getenv("NEO_ALERT_BOT_TOKEN", "")
EXECUTION_BACKEND = os.getenv("SORA_EXECUTION_BACKEND", "gemini").strip().lower()


# ── 에러 메시지 한국어 변환 테이블 ──
_ERROR_MESSAGES = {
    "VERCEL_TOKEN": "Vercel 배포 권한이 없어요. VERCEL_TOKEN을 확인해주세요.",
    "Connection refused": "서버 연결이 끊어졌어요. 잠시 후 다시 시도해주세요.",
    "TimeoutExpired": "작업 시간이 초과됐어요(5분). 더 작은 단위로 나눠서 요청해보세요.",
    "429": "AI API 사용량 한도에 도달했어요. 약 1분 후 다시 시도해주세요.",
    "Resource exhausted": "AI API 사용량 한도에 도달했어요. 약 1분 후 다시 시도해주세요.",
    "home-pc": "집 PC와 연결이 끊어졌어요. PC Agent가 실행 중인지 확인해주세요.",
    "work-pc": "회사 PC와 연결이 끊어졌어요. PC Agent가 실행 중인지 확인해주세요.",
    "linux-server": "리눅스 서버 연결이 끊어졌어요. 서버 상태를 확인해주세요.",
    "GEMINI_API_KEY": "Gemini API 키가 없어요. SORA_GEMINI_API_KEY를 확인해주세요.",
    "Permission denied": "권한이 없어요. 실행 권한을 확인해주세요.",
    "No such file": "파일을 찾을 수 없어요. 경로를 다시 확인해주세요.",
    "ModuleNotFoundError": "필요한 라이브러리가 설치되지 않았어요.",
}

def _format_error(error_msg: str) -> str:
    """기술 에러 메시지 → 사용자 친화적 한국어 변환."""
    for key, friendly in _ERROR_MESSAGES.items():
        if key.lower() in error_msg.lower():
            return f"⚠️ {friendly}\n\n기술 정보: `{error_msg[:100]}`"
    return f"⚠️ 처리 중 오류가 발생했어요.\n\n기술 정보: `{error_msg[:150]}`"


def _assess_risk(text: str) -> tuple[int, str]:
    """명령어 위험도 평가.

    Returns:
        (risk_level, action_description) — risk_level 0-100
    """
    decision = evaluate_text_execution_gate(text)
    return decision.risk_score, decision.action if decision.requires_approval else ""


def _should_skip_task_planner(request: dict) -> bool:
    """Report-generation automations should be answered, not decomposed as executable plans."""
    metadata = request.get("metadata") or {}
    if metadata.get("automation") == "daily-ai-brief":
        return True
    if metadata.get("kind") == "daily_ai_ops_brief":
        return True
    if request.get("session_id") == "automation:daily-ai-brief":
        return True
    return False


class BrainWorker:
    """LLM 호출 워커 — Redis 큐 소비 → 처리 → 결과 발행."""

    def __init__(self):
        self._running = True
        self._engine = None
        self._telegram_bot = None
        self._bus = None
        self._stats = {
            "started_at": time.time(),
            "requests_processed": 0,
            "errors": 0,
        }

    def _init_engine(self):
        """SoraEngine 초기화 (이 프로세스에서만 — Gateway와 분리)."""
        if self._engine is None:
            try:
                from src.core.sora_engine import get_sora_engine
                self._engine = get_sora_engine()
                logger.info(f"[Brain] SoraEngine 초기화 완료 — {GEMINI_MODEL}")
            except Exception as e:
                logger.error(f"[Brain] SoraEngine 초기화 실패: {e}")
                raise

    def _use_codex_backend(self) -> bool:
        return EXECUTION_BACKEND == "codex"

    async def _process_request_with_codex(self, request: dict, reporter, security_context: dict | None = None) -> dict:
        from src.core.codex_runtime import build_codex_prompt_bundle, run_codex_request

        text = request.get("text", "")
        file_path = request.get("file_path", "")
        session_id = request.get("session_id", request.get("channel", "unknown"))

        await reporter.update("🧠 Codex 컨텍스트 조립 중...", force=True)
        metadata = dict(request.get("metadata") or {})
        if security_context:
            metadata["security_gate"] = security_context

        prompt = build_codex_prompt_bundle(
            user_text=text,
            session_id=session_id,
            file_path=file_path,
            metadata=metadata,
        )

        await reporter.update("⚙️ Codex 실행 중...", force=True)
        result = await asyncio.to_thread(
            run_codex_request,
            prompt=prompt,
            user_text=text,
            file_path=file_path,
        )

        return {
            "reply": result.reply,
            "error": None,
            "metadata": {
                "request_id": request.get("request_id", ""),
                "backend": "codex",
                "model": os.getenv("SORA_CODEX_MODEL", "codex-default").strip() or "codex-default",
                "codex_thread_id": result.thread_id,
                "sandbox": result.sandbox,
                "latency_ms": result.duration_ms,
                "stderr_summary": result.stderr_summary,
                "security_gate": security_context or {},
            },
        }

    async def _init_telegram(self):
        """텔레그램 Bot 인스턴스 (응답 전송용)."""
        if self._telegram_bot is None and TELEGRAM_BOT_TOKEN:
            try:
                from telegram import Bot
                self._telegram_bot = Bot(token=TELEGRAM_BOT_TOKEN)
                logger.info("[Brain] Telegram Bot 인스턴스 생성 완료")
            except Exception as e:
                logger.warning(f"[Brain] Telegram Bot 생성 실패: {e}")

    async def _get_bus(self):
        """Redis Bus 연결."""
        if self._bus is None:
            from src.core.queue.redis_bus import get_redis_bus
            self._bus = get_redis_bus()
            await self._bus.connect()
        return self._bus

    async def process_request(self, request: dict) -> dict:
        """단일 요청 처리.

        Args:
            request: {"request_id", "text", "channel", "device_id", "chat_id", "file_path", "metadata"}

        Returns:
            {"reply": str, "error": str|None, "metadata": dict}
        """
        request_id = request.get("request_id", "unknown")
        text = request.get("text", "")
        file_path = request.get("file_path", "")
        channel = request.get("channel", "unknown")

        logger.info(f"[Brain] 처리 시작: {request_id} ({channel}) {text[:60]}")
        t_start = time.time()

        try:
            # ── ProgressReporter 초기화 ──
            from src.core.progress import ProgressReporter
            bus = await self._get_bus()
            reporter = ProgressReporter(bus, request_id, request.get("chat_id", ""))

            # ── SEC-002/004/008 ConfirmGate: 위험 작업 사전 확인 ──
            request_metadata = request.get("metadata") or {}
            gate_decision = evaluate_text_execution_gate(text, request_metadata)
            security_context = gate_decision.to_metadata(owner_approved=False)
            if gate_decision.requires_approval:
                risk_level = gate_decision.risk_score
                risk_description = gate_decision.action
                logger.info(
                    "[Brain] 실행 게이트 승인 필요 (tier=%s risk=%s): %s",
                    gate_decision.authority_tier,
                    risk_level,
                    risk_description,
                )
                await reporter.confirm_required(
                    f"⚠️ *위험 작업 확인 필요*\n\n"
                    f"실행 예정: *{risk_description}*\n"
                    f"권한 등급: *{gate_decision.authority_tier}*\n"
                    f"보안 기준: `{', '.join(gate_decision.controls)}`\n"
                    f"명령: `{text[:80]}`\n\n"
                    f"30초 안에 응답해주세요."
                )
                notify_agent_approval_requested(
                    agent="sora",
                    request_id=request_id,
                    action=risk_description,
                    summary=text[:240],
                    timeout_sec=30.0,
                    metadata={
                        "channel": channel,
                        "risk_level": risk_level,
                        "authority_tier": gate_decision.authority_tier,
                        "controls": gate_decision.controls,
                    },
                )
                approval_started_at = time.time()
                decision = await bus.wait_for_confirm_decision(request_id, timeout=30.0)
                notify_agent_approval_result(
                    agent="sora",
                    request_id=request_id,
                    action=risk_description,
                    decision=decision,
                    summary=text[:240],
                    elapsed_sec=time.time() - approval_started_at,
                    metadata={
                        "channel": channel,
                        "risk_level": risk_level,
                        "authority_tier": gate_decision.authority_tier,
                        "controls": gate_decision.controls,
                    },
                )
                if decision != "approved":
                    cancel_reply = "⏱️ 확인 시간이 초과되어 작업이 취소되었습니다."
                    if decision == "rejected":
                        cancel_reply = "❌ 작업이 취소되었습니다."
                    return {
                        "reply": cancel_reply,
                        "error": None,
                        "metadata": {
                            "request_id": request_id,
                            "cancelled": True,
                            "cancelled_reason": decision,
                            "security_gate": security_context,
                        },
                    }
                await reporter.update("✅ 확인 완료. 실행을 시작합니다...", force=True)
                security_context = gate_decision.to_metadata(owner_approved=True)

            if self._use_codex_backend():
                result = await self._process_request_with_codex(request, reporter, security_context)
                logger.info(
                    "[Brain] Codex 처리 완료: %s (%sms)",
                    request_id,
                    result.get("metadata", {}).get("latency_ms", "?"),
                )
                self._stats["requests_processed"] += 1
                return result

            # ── 멀티스텝 감지 → TaskPlanner 위임 (단일 진입점) ──
            try:
                from src.core.task_planner import get_task_planner
                planner = get_task_planner()
                if planner and not file_path and not _should_skip_task_planner(request) and planner.is_multi_step(text):
                    logger.info(f"[Brain] 멀티스텝 감지 → TaskPlanner 위임: {text[:40]}")
                    await reporter.update("📋 멀티스텝 계획 수립 중...")
                    plan = await planner.plan_and_execute(
                        text,
                        owner_approved=bool(security_context.get("owner_approved")),
                    )
                    reply = plan.summary()
                    reply = await self._ensure_quality_response(text, reply)
                    latency_ms = (time.time() - t_start) * 1000
                    self._stats["requests_processed"] += 1
                    return {
                        "reply": reply,
                        "error": None,
                        "metadata": {
                            "latency_ms": round(latency_ms, 1),
                            "model": GEMINI_MODEL,
                            "request_id": request_id,
                            "path": "task_planner",
                            "security_gate": security_context,
                        },
                    }
            except Exception as e:
                logger.warning(f"[Brain] TaskPlanner 실패, 에이전트 라우터로 폴백: {e}")

            # ── v5.0: 멀티 에이전트 라우터 경유 ──
            from src.core.brain.agent_router import get_agent_router
            router = get_agent_router()
            reply = await router.process(
                text,
                file_path=file_path or None,
                reporter=reporter,
                security_context=security_context,
            )

            # ── 응답 품질 보장: JSON 덤프·빈 응답 → 자연어로 재요약 ──
            reply = await self._ensure_quality_response(text, reply)

            latency_ms = (time.time() - t_start) * 1000
            logger.info(f"[Brain] 처리 완료: {request_id} ({latency_ms:.0f}ms) {reply[:60]}")
            self._stats["requests_processed"] += 1

            # 감사 로그 기록 (사용 모델 포함)
            try:
                from src.core.audit import get_audit_logger
                from src.core.brain.agent_router import _last_used_model
                await get_audit_logger().log(
                    request_id=request_id,
                    user_message=text,
                    tools_executed=[],
                    duration_ms=latency_ms,
                    strategy=f"agent_router/{_last_used_model}",
                )
            except Exception:
                pass

            return {
                "reply": reply,
                "error": None,
                "metadata": {
                    "latency_ms": round(latency_ms, 1),
                    "model": GEMINI_MODEL,
                    "request_id": request_id,
                    "security_gate": security_context,
                },
            }

        except Exception as e:
            self._stats["errors"] += 1
            error_msg = str(e)[:500]
            logger.error(f"[Brain] 처리 실패: {request_id} — {error_msg}")
            return {
                "reply": _format_error(error_msg),
                "error": error_msg,
                "metadata": {"request_id": request_id},
            }

    async def _ensure_quality_response(self, user_query: str, raw_reply: str) -> str:
        """Stage 2: 응답 품질 보장.

        양호한 응답은 그대로 반환.
        부실한 응답(빈 응답, JSON 덤프, 기본 폴백)은 도구 결과를 추출해 재요약.
        """
        # 양호한 응답 기준: 한국어 텍스트, 20자 이상, JSON이 아닌 것
        is_good = (
            raw_reply
            and raw_reply not in ("명령을 처리했습니다.", "")
            and not raw_reply.startswith("{")
            and not raw_reply.startswith("[")
            and len(raw_reply) > 15
        )

        if is_good:
            return raw_reply

        # 부실한 응답 → chat history에서 도구 실행 결과 추출
        logger.info(f"[Brain] 부실 응답 감지, 2단계 후처리 시작: '{raw_reply[:30]}...'")

        tool_results = self._extract_tool_results()
        if tool_results:
            return await self._summarize_tool_result(user_query, tool_results)
        elif raw_reply and raw_reply != "명령을 처리했습니다.":
            return await self._summarize_tool_result(user_query, raw_reply)
        else:
            return "요청을 처리했지만 결과를 가져오지 못했습니다. 다시 시도해주세요."

    def _extract_tool_results(self) -> str:
        """SoraEngine chat history에서 최근 도구 실행 결과를 추출."""
        try:
            if not self._engine or not self._engine.chat:
                return ""
            history = getattr(self._engine.chat, '_curated_history', None) or getattr(self._engine.chat, 'history', [])
            results = []
            for msg in reversed(history[-10:]):
                for part in getattr(msg, 'parts', []):
                    if hasattr(part, 'function_response'):
                        fr = part.function_response
                        name = getattr(fr, 'name', 'tool')
                        response = getattr(fr, 'response', {})
                        results.append(f"[{name}]: {json.dumps(response, ensure_ascii=False, default=str)[:1500]}")
                    elif hasattr(part, 'function_call'):
                        fc = part.function_call
                        name = getattr(fc, 'name', 'tool')
                        args = getattr(fc, 'args', {})
                        results.append(f"[호출: {name}({json.dumps(dict(args) if args else {}, ensure_ascii=False)[:200]})]")
                if results:
                    break
            return "\n".join(results) if results else ""
        except Exception as e:
            logger.warning(f"[Brain] 도구 결과 추출 실패: {e}")
            return ""

    async def _summarize_tool_result(self, user_query: str, raw_result: str) -> str:
        """도구 실행 결과를 자연어로 요약 (2단계 처리).

        Gemini AFC가 도구 결과를 텍스트로 변환하지 못할 때 호출.
        별도 Gemini Flash 호출로 빠르게 요약.
        """
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)
            time_anchor = build_time_context_block() if needs_explicit_time_context(user_query) else ""
            if time_anchor:
                raw_result = f"{time_anchor}\n\n{raw_result}"

            prompt = f"""당신은 소라(Sora), 허예솔 대표님의 AI 비서입니다.
대표님이 다음과 같이 요청했고, 도구를 실행한 결과가 있습니다.

■ 대표님 요청: {user_query}

■ 도구 실행 결과:
{raw_result[:3000]}

위 결과를 대표님에게 보고해주세요.
규칙:
- 한국어, ~요 체 존댓말
- 핵심 정보만 간결하게 (3-5줄)
- JSON 원문 그대로 보내지 말고 읽기 쉽게 정리
- 숫자/상태 정보는 구체적으로 포함
- 추가 제안이 있으면 간단히 덧붙이기"""

            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.5-flash",
                contents=prompt,
            )
            summary = response.text.strip()
            if summary:
                logger.info(f"[Brain] 도구 결과 요약 완료: {len(summary)}자")
                return summary
        except Exception as e:
            logger.warning(f"[Brain] 도구 결과 요약 실패: {e}")

        # 요약 실패 시 원본 그대로 반환
        if raw_result and raw_result != "명령을 처리했습니다.":
            return f"도구 실행 결과:\n```json\n{raw_result[:2000]}\n```"
        return "명령을 처리했습니다. 결과를 확인해주세요."

    def _save_to_supabase(
        self,
        content: str,
        role: str,
        channel: str,
        device_id: str,
        *,
        session_id: str,
        metadata: dict | None = None,
    ):
        """대화를 Supabase에 저장 + 세션 last_message_at 자동 갱신."""
        try:
            from src.core.storage.supabase_store import get_supabase_store
            store = get_supabase_store()
            store.add_conversation(
                role=role, content=content[:2000],
                channel=channel, device_id=device_id,
                session_id=session_id,
                metadata=metadata or {},
            )
            # 세션 last_message_at 갱신 (응답 저장 시 1회)
            if role == "assistant":
                store.touch_session(session_id, channel)
        except Exception as e:
            logger.debug(f"[Brain] Supabase 저장 실패 (무시): {e}")

    async def _send_reply(self, request: dict, result: dict):
        """결과를 Redis pubsub으로 발행.

        텔레그램 응답은 데몬의 _worker가 Redis 결과를 받아서 직접 전송.
        (Brain Worker가 직접 보내면 이중 응답 발생)
        """
        bus = await self._get_bus()
        await bus.publish_result(request["request_id"], result)
        logger.info(f"[Brain] 결과 발행: {request['request_id']} ({request.get('channel', '?')})")

    async def run(self):
        """메인 루프 — Redis 큐에서 요청을 꺼내 처리."""
        logger.info("=" * 60)
        logger.info("[Brain] Sora Brain Worker v3.0 시작")
        if self._use_codex_backend():
            logger.info("[Brain] 실행 백엔드: codex")
        else:
            logger.info(f"[Brain] 실행 백엔드: gemini ({GEMINI_MODEL})")
        logger.info("[Brain] SoraEngine은 첫 요청 시 lazy 초기화")
        logger.info("=" * 60)

        # A: Gateway가 먼저 안정화되도록 30초 대기
        logger.info("[Brain] Gateway 안정화 대기 (30초)...")
        await asyncio.sleep(30)

        # B: SoraEngine 사전 초기화 안 함 — 첫 요청 시 lazy 로드
        await self._init_telegram()

        bus = await self._get_bus()
        logger.info("[Brain] Redis 큐 대기 시작 (SoraEngine은 첫 요청 시 로드)")

        while self._running:
            try:
                # 큐에서 요청 꺼내기 (5초마다 타임아웃으로 상태 체크)
                request = await bus.dequeue_request(timeout=5)
                if request is None:
                    continue

                # 요청 처리
                result = await self.process_request(request)

                # Supabase에 대화 저장 (사용자 메시지 + 소라 응답)
                channel = request.get("channel", "unknown")
                device_id = request.get("device_id", "cloud")
                session_id = request.get("session_id", channel)
                request_metadata = {
                    "request_id": request.get("request_id", ""),
                    "file_path": request.get("file_path", ""),
                    **(request.get("metadata") or {}),
                }
                result_metadata = {
                    **(result.get("metadata") or {}),
                    "request_id": request.get("request_id", ""),
                }
                self._save_to_supabase(
                    request.get("text", ""),
                    "user",
                    channel,
                    device_id,
                    session_id=session_id,
                    metadata=request_metadata,
                )
                self._save_to_supabase(
                    result.get("reply", ""),
                    "assistant",
                    channel,
                    device_id,
                    session_id=session_id,
                    metadata=result_metadata,
                )

                # 응답 전송
                await self._send_reply(request, result)

            except KeyboardInterrupt:
                break
            except Exception as e:
                logger.error(f"[Brain] 루프 에러: {e}", exc_info=True)
                await asyncio.sleep(2)

        logger.info("[Brain] Worker 종료")

    def stop(self):
        """워커 중지."""
        self._running = False

    def get_stats(self) -> dict:
        """워커 통계."""
        return {
            **self._stats,
            "uptime_sec": round(time.time() - self._stats["started_at"], 1),
        }


# ── 엔트리포인트 ──

def main():
    acquired, reason = claim_single_instance(WORKER_PID_PATH, WORKER_MATCHERS)
    if not acquired:
        logger.warning("[Brain] duplicate start blocked: %s", reason)
        print(f"[SKIP] {reason}")
        return

    worker = BrainWorker()

    def _signal_handler(sig, frame):
        logger.info(f"[Brain] 시그널 수신 ({sig}), 종료 중...")
        worker.stop()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    asyncio.run(worker.run())


if __name__ == "__main__":
    main()
