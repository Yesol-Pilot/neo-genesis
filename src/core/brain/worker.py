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

from dotenv import load_dotenv
load_dotenv(PROJECT_ROOT / ".env", override=True)

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
            # SoraEngine으로 처리 (도구 자동 실행 포함)
            self._init_engine()
            reply = await self._engine.process(text, file_path=file_path or None)

            # 빈 응답 또는 기본 폴백 감지 → 2단계 요약 처리
            if reply in ("명령을 처리했습니다.", "") or reply.startswith("{") or reply.startswith("["):
                reply = await self._summarize_tool_result(text, reply)

            latency_ms = (time.time() - t_start) * 1000
            logger.info(f"[Brain] 처리 완료: {request_id} ({latency_ms:.0f}ms) {reply[:60]}")
            self._stats["requests_processed"] += 1

            return {
                "reply": reply,
                "error": None,
                "metadata": {
                    "latency_ms": round(latency_ms, 1),
                    "model": GEMINI_MODEL,
                    "request_id": request_id,
                },
            }

        except Exception as e:
            self._stats["errors"] += 1
            error_msg = str(e)[:500]
            logger.error(f"[Brain] 처리 실패: {request_id} — {error_msg}")
            return {
                "reply": f"⚠️ 처리 중 오류: {error_msg[:200]}",
                "error": error_msg,
                "metadata": {"request_id": request_id},
            }

    async def _summarize_tool_result(self, user_query: str, raw_result: str) -> str:
        """도구 실행 결과를 자연어로 요약 (2단계 처리).

        Gemini AFC가 도구 결과를 텍스트로 변환하지 못할 때 호출.
        별도 Gemini Flash 호출로 빠르게 요약.
        """
        try:
            from google import genai
            client = genai.Client(api_key=GEMINI_API_KEY)

            prompt = f"""사용자 질문: {user_query}

도구 실행 결과 (JSON):
{raw_result[:3000]}

위 도구 실행 결과를 사용자에게 친절하게 한국어로 요약해주세요.
- 핵심 정보만 간결하게
- 마크다운 포맷 사용 가능
- "대표님"이라고 호칭
- 소라(Sora) AI 비서 톤으로"""

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
        logger.info(f"[Brain] 모델: {GEMINI_MODEL}")
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
    worker = BrainWorker()

    def _signal_handler(sig, frame):
        logger.info(f"[Brain] 시그널 수신 ({sig}), 종료 중...")
        worker.stop()

    signal.signal(signal.SIGTERM, _signal_handler)
    signal.signal(signal.SIGINT, _signal_handler)

    asyncio.run(worker.run())


if __name__ == "__main__":
    main()
