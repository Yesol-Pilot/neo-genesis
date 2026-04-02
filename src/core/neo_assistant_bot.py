# -*- coding: utf-8 -*-
"""
NEO GENESIS 소라(Sora) — 텔레그램 어댑터 v4.0

SoraEngine(JARVIS Core)의 텔레그램 채널 어댑터입니다.
AI 엔진 로직은 sora_engine.py에 통합되어 있으며,
이 파일은 텔레그램 I/O만 담당합니다.

아키텍처: PTB v20 + asyncio.Queue 기반 Producer-Consumer 패턴
- Producer: 텔레그램 메시지 수신 → 즉시 큐 적재
- Consumer: 백그라운드 워커가 큐에서 작업을 꺼내 SoraEngine 처리

Usage:
    python neo_assistant_bot.py          # 독립 실행
    (데몬에서 자동 기동)
"""
import asyncio
import logging
import os
import re
import time
from pathlib import Path

from dotenv import load_dotenv

# ── 경로 설정 ────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROFIT_ROOT = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "profit"
MEMORY_DIR = PROJECT_ROOT / "src" / "core" / "data" / "assistant_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# .env 로드
load_dotenv(PROJECT_ROOT / ".env", override=True)
load_dotenv(PROFIT_ROOT / ".env", override=True)

# ── 로깅 ─────────────────────────────────────────
logger = logging.getLogger("neo.jarvis")

# ── 설정 ─────────────────────────────────────────
BOT_TOKEN = os.getenv("NEO_ALERT_BOT_TOKEN", "")
CHAT_ID = os.getenv("NEO_ALERT_CHAT_ID", "")


# ══════════════════════════════════════════════════
# 역호환: 도구 모듈에서 ALL_TOOLS를 neo_assistant_bot에서 임포트하는 코드 대응
# ══════════════════════════════════════════════════
from src.core.tools import ALL_TOOLS  # noqa: F401 — 외부 참조용 유지

# 역호환: 기억 시스템도 sora_engine에서 재수출
from src.core.sora_engine import get_memory as _get_memory
_memory = _get_memory()


# ══════════════════════════════════════════════════
# 텔레그램 어댑터 (NeoAssistant)
# ══════════════════════════════════════════════════

class NeoAssistant:
    """SoraEngine의 텔레그램 채널 어댑터.

    AI 엔진 로직(도구, 기억, RAG, 프롬프트)은 SoraEngine이 담당하며,
    이 클래스는 텔레그램 메시지 수신/발신만 처리합니다.
    """

    def __init__(self):
        from src.core.sora_engine import get_sora_engine
        self.engine = get_sora_engine()
        self.memory = self.engine.memory
        self.task_queue: asyncio.Queue = asyncio.Queue()
        logger.info("[Sora] 텔레그램 어댑터 초기화 완료 (v4.0 — SoraEngine 통합)")

    # ── 텔레그램 핸들러 (Producer) ──

    async def _on_message(self, update, context):
        """텔레그램 텍스트 메시지 수신 → 큐에 적재"""
        message = update.message
        if not message or not message.text:
            return

        if CHAT_ID and str(message.chat_id) != CHAT_ID:
            await message.reply_text("🔒 접근 권한이 없습니다.")
            return

        text = message.text.strip()
        if not text:
            return

        logger.info(f"[Sora] 수신: {text[:50]}")
        await self.task_queue.put((update, text))

    async def _on_photo(self, update, context):
        """텔레그램 사진 수신 → Gemini Vision 분석"""
        message = update.message
        if not message:
            return
        if CHAT_ID and str(message.chat_id) != CHAT_ID:
            return

        try:
            photo = message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            local_path = MEMORY_DIR / f"photo_{int(time.time())}.jpg"
            await file.download_to_drive(str(local_path))

            caption = message.caption or "이 이미지를 분석해주세요."
            await self.task_queue.put((update, caption, str(local_path)))
        except Exception as e:
            logger.error(f"[Sora] 사진 처리 실패: {e}")

    async def _on_document(self, update, context):
        """텔레그램 문서 수신 → 내용 추출 + AI 분석"""
        message = update.message
        if not message or not message.document:
            return
        if CHAT_ID and str(message.chat_id) != CHAT_ID:
            return

        try:
            doc = message.document
            file = await context.bot.get_file(doc.file_id)
            local_path = MEMORY_DIR / doc.file_name
            await file.download_to_drive(str(local_path))

            caption = message.caption or f"이 파일({doc.file_name})을 분석해주세요."
            await self.task_queue.put((update, caption, str(local_path)))
        except Exception as e:
            logger.error(f"[Sora] 문서 처리 실패: {e}")

    # ── 백그라운드 워커 (Consumer) ──

    async def _worker(self):
        """큐에서 작업을 꺼내 처리 — v2.0: Redis 큐 경유 또는 직접 처리"""
        while True:
            item = await self.task_queue.get()
            if len(item) == 3:
                update, text, file_path = item
            else:
                update, text = item
                file_path = None

            message = update.message

            try:
                # 타이핑 표시
                action = (
                    "upload_photo"
                    if file_path
                    and Path(file_path).suffix.lower()
                    in ('.jpg', '.jpeg', '.png', '.webp', '.gif')
                    else "typing"
                )
                await message.chat.send_action(action)

                # v2.0: Redis 큐 경유 시도 → 실패 시 직접 처리 폴백
                reply = await self._process_via_redis_or_direct(
                    text, str(message.chat_id), file_path
                )

                # 텍스트 응답 전송 (4000자 제한)
                truncated = reply[:4000]
                try:
                    await message.reply_text(truncated, parse_mode="Markdown")
                except Exception:
                    await message.reply_text(truncated)

                logger.info(f"[Sora] 응답 완료: {reply[:60]}")

            except Exception as e:
                error_msg = f"⚠️ 처리 중 오류: {str(e)[:300]}"
                logger.error(f"[Sora] {error_msg}", exc_info=True)
                try:
                    await message.reply_text(error_msg)
                except Exception:
                    pass

            finally:
                self.task_queue.task_done()

    async def _process_via_redis_or_direct(self, text: str, chat_id: str, file_path: str = None) -> str:
        """v2.0: Redis Brain Worker 경유 처리. 실패 시 직접 SoraEngine 폴백."""
        # Redis 경유 시도
        try:
            from src.core.queue.redis_bus import get_redis_bus
            bus = get_redis_bus()
            await bus.connect()

            request_id = await bus.enqueue_request(
                text=text,
                channel="telegram",
                device_id="phone",
                chat_id=chat_id,
                file_path=file_path or "",
            )
            logger.info(f"[Sora] Redis 큐 적재: {request_id}")

            # Brain Worker의 응답 대기 (최대 90초)
            result = await bus.wait_for_result(request_id, timeout=90)
            reply = result.get("reply", "")
            if reply and not result.get("error"):
                return reply
            logger.warning(f"[Sora] Redis 응답 에러: {result.get('error', 'empty')}")

        except Exception as e:
            logger.warning(f"[Sora] Redis 경유 실패, 직접 처리 폴백: {e}")

        # 폴백: 직접 SoraEngine 호출
        return await self.engine.process(text, file_path=file_path)

    # ── 메인 실행 ──────────────────────────────────

    def run(self):
        """PTB v20 Application 기동 (동기 엔트리포인트)"""
        from telegram.ext import ApplicationBuilder, MessageHandler, filters

        if not BOT_TOKEN:
            logger.error("[Sora] NEO_ALERT_BOT_TOKEN 미설정")
            return

        # PID 락 — 중복 실행 방지
        pid_file = MEMORY_DIR / "jarvis.pid"
        if pid_file.exists():
            try:
                old_pid = int(pid_file.read_text().strip())
                import psutil
                if psutil.pid_exists(old_pid):
                    logger.warning(f"[Sora] 이미 실행 중 (PID {old_pid}). 종료.")
                    return
            except Exception:
                pass
        pid_file.write_text(str(os.getpid()))

        logger.info("[Sora] 소라 온라인 (v4.0 — SoraEngine 통합)")

        async def _post_init(application) -> None:
            """시작 알림 + 백그라운드 워커 기동"""
            asyncio.create_task(self._worker())
            await application.bot.send_message(
                chat_id=CHAT_ID,
                text=(
                    "안녕하세요 대표님! 소라예요 ✨\n"
                    "v4.0 — JARVIS 통합 완료!\n"
                    "폰에서도 모든 도구를 사용할 수 있어요 📱"
                ),
            )
            logger.info("[Sora] 시작 알림 전송 완료")

        app = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .post_init(_post_init)
            .build()
        )

        app.add_handler(
            MessageHandler(
                filters.TEXT & ~filters.COMMAND,
                self._on_message,
            )
        )
        app.add_handler(
            MessageHandler(filters.PHOTO, self._on_photo)
        )
        app.add_handler(
            MessageHandler(filters.Document.ALL, self._on_document)
        )

        app.run_polling(drop_pending_updates=True)

    async def _run_async(self):
        """비동기 실행 — 별도 스레드에서 안전하게 polling 시작 (Linux 호환)."""
        from telegram.ext import ApplicationBuilder, MessageHandler, filters

        if not BOT_TOKEN:
            logger.error("[Sora] NEO_ALERT_BOT_TOKEN 미설정")
            return

        logger.info("[Sora] 소라 온라인 (v4.0 — async 모드)")

        app = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .build()
        )

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message))
        app.add_handler(MessageHandler(filters.PHOTO, self._on_photo))
        app.add_handler(MessageHandler(filters.Document.ALL, self._on_document))

        # 워커 시작
        asyncio.get_event_loop().create_task(self._worker())

        # 시작 알림
        async with app:
            await app.bot.send_message(
                chat_id=CHAT_ID,
                text="안녕하세요 대표님! 소라예요 ✨\nGCP 클라우드에서 24/7 가동 중이에요!",
            )
            logger.info("[Sora] 시작 알림 전송 완료")

            await app.updater.start_polling(drop_pending_updates=True)
            await app.start()
            logger.info("[Sora] polling 시작 완료")

            # 무한 대기 (polling 유지)
            while True:
                await asyncio.sleep(3600)

    def run_in_thread(self):
        """백그라운드 스레드 실행 (데몬 호환용, Linux 안전)"""
        import threading

        def _thread_target():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._run_async())
            except Exception as e:
                logger.error(f"[Sora] 텔레그램 봇 스레드 에러: {e}", exc_info=True)
            finally:
                loop.close()

        t = threading.Thread(target=_thread_target, daemon=True, name="sora")
        t.start()
        return t


# ══════════════════════════════════════════════════
# 엔트리포인트
# ══════════════════════════════════════════════════

if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s — %(message)s",
    )
    bot = NeoAssistant()
    bot.run()
