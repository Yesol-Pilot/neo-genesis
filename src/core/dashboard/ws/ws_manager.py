# -*- coding: utf-8 -*-
"""
WebSocket 매니저 — 실시간 채팅 + 브로드캐스트

sora_dashboard.py에서 분리된 WebSocket 전용 모듈입니다.
"""
import asyncio
import json
import logging
import os
from datetime import datetime
from pathlib import Path

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent

# ── SoraEngine 연결 (지연 초기화) ──
_sora_engine = None

_SORA_SYSTEM = (
    "당신은 NEO GENESIS의 AI 비서 '소라'입니다. "
    "CEO 전용 모바일 앱에서 대화 중입니다. "
    "한국어로 간결하고 친절하게 답변하세요. "
    "시스템 상태, 업무 현황, 일정 등을 안내할 수 있습니다."
)


def _get_sora_engine():
    """SoraEngine 싱글턴 — 클라우드 모드에서는 비활성화."""
    import os
    if os.environ.get("SORA_CLOUD_MODE"):
        return None
    global _sora_engine
    if _sora_engine is None:
        try:
            from src.core.sora_engine import get_sora_engine
            _sora_engine = get_sora_engine()
            logger.info("[WS] SoraEngine 연결 성공")
        except Exception as e:
            logger.error(f"[WS] SoraEngine 초기화 실패: {e}")
            return None
    return _sora_engine


async def _fallback_gemini(prompt: str) -> str:
    """SoraEngine 사용 불가 시 레거시 폴백."""
    api_key = os.environ.get("GEMINI_API_KEY", "")
    if api_key:
        try:
            from google import genai
            client = genai.Client(api_key=api_key)
            response = await asyncio.to_thread(
                client.models.generate_content,
                model="gemini-2.0-flash",
                contents=prompt,
            )
            return response.text or ""
        except Exception as e:
            logger.warning(f"[WS] 레거시 폴백 실패: {e}")
    return "⛔ AI 서비스가 일시적으로 불안정합니다."


# ── 채팅 로거 ──
def _log_chat(sender: str, message: str):
    """채팅 내용을 JSONL로 기록."""
    try:
        log_path = PROJECT_ROOT / "data" / "chat_history.jsonl"
        log_path.parent.mkdir(parents=True, exist_ok=True)
        entry = {
            "timestamp": datetime.now().isoformat(),
            "sender": sender,
            "message": message,
        }
        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.error(f"채팅 로깅 실패: {e}")


# ── WebSocket 클라이언트 관리 ──
_ws_clients: set = set()


async def ws_broadcast(data: dict):
    """모든 WebSocket 클라이언트에 메시지 브로드캐스트."""
    dead = set()
    for ws in _ws_clients:
        try:
            await ws.send_json(data)
        except Exception:
            dead.add(ws)
    _ws_clients -= dead


def get_ws_client_count() -> int:
    """현재 연결된 WebSocket 클라이언트 수."""
    return len(_ws_clients)


# ── 라우터 ──
router = APIRouter(tags=["websocket"])


@router.websocket("/ws/chat")
async def ws_chat(ws: WebSocket):
    """WebSocket 실시간 채팅 — SoraEngine 경유.

    프로토콜:
    - Client → Server: {"type":"message", "text":"..."}
    - Server → Client: {"type":"status", "text":"..."} (진행 상태)
    - Server → Client: {"type":"reply", "text":"..."}  (최종 응답)
    - Server → Client: {"type":"error", "text":"..."}  (오류)
    """
    # 로컬 네트워크 인증 확인
    client_ip = ws.client.host if ws.client else ""
    is_local = client_ip in ("127.0.0.1", "::1", "localhost") or client_ip.startswith(("192.168.", "10."))
    if not is_local:
        await ws.close(code=4001, reason="Authentication required")
        return

    await ws.accept()
    _ws_clients.add(ws)
    logger.info(f"[WS] 클라이언트 연결: {client_ip} (총 {len(_ws_clients)}명)")

    try:
        while True:
            data = await ws.receive_json()
            msg_type = data.get("type", "message")
            text = data.get("text", "").strip()

            if msg_type == "ping":
                await ws.send_json({"type": "pong"})
                continue

            if not text:
                await ws.send_json({"type": "error", "text": "빈 메시지입니다"})
                continue

            # 사용자 메시지 로깅
            _log_chat("user", text)

            # 진행 상태 알림
            await ws.send_json({"type": "status", "text": "🧠 소라가 생각하고 있어요..."})

            try:
                engine = _get_sora_engine()
                if engine:
                    await ws.send_json({"type": "status", "text": "⚙️ 도구 실행 중..."})
                    reply = await engine.process(text)
                else:
                    prompt = f"{_SORA_SYSTEM}\n\n사용자: {text}"
                    reply = await _fallback_gemini(prompt)

                _log_chat("sora", reply)
                await ws.send_json({"type": "reply", "text": reply})

            except Exception as e:
                logger.error(f"[WS] 처리 오류: {e}", exc_info=True)
                err_msg = f"처리 중 오류: {str(e)[:300]}"
                _log_chat("system", f"ERROR: {err_msg}")
                await ws.send_json({"type": "error", "text": err_msg})

    except WebSocketDisconnect:
        logger.info(f"[WS] 클라이언트 해제: {client_ip}")
    except Exception as e:
        logger.warning(f"[WS] 예외: {e}")
    finally:
        _ws_clients.discard(ws)


@router.get("/api/v2/chat/history")
async def api_chat_history(limit: int = 50):
    """채팅 기록 조회 (최신순)"""
    log_path = PROJECT_ROOT / "data" / "chat_history.jsonl"
    if not log_path.exists():
        return {"history": []}

    try:
        lines = log_path.read_text(encoding="utf-8").splitlines()
        recent = [json.loads(line) for line in lines[-limit:]]
        return {"history": recent}
    except Exception as e:
        return {"history": [], "error": str(e)}
