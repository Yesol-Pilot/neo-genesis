# -*- coding: utf-8 -*-
"""
Neo Genesis: Sora Dashboard (FastAPI) — v3.1 통합 대시보드

- 포트: 7700
- 기존 API (v1): System, Memory, Security, Tools
- 신규 API (v2): Overview, SBU, Traffic, Finance, Governance
- Google OAuth 인증 (CEO 전용)
- GA4 프록시 (Node.js 브릿지)
"""
import asyncio
from contextlib import asynccontextmanager
import hashlib
import inspect
import json
import logging
import os
import platform
import secrets
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from fastapi import FastAPI, Query, Request, Response, Cookie, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from starlette.middleware.sessions import SessionMiddleware

from dotenv import load_dotenv
load_dotenv(Path(__file__).resolve().parent.parent.parent / ".env")

logger = logging.getLogger(__name__)

# ── 경로 설정 ────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
STATIC_DIR = Path(__file__).resolve().parent / "static"
DASHBOARD_DIR = Path(__file__).resolve().parent / "dashboard"
DATA_DIR = PROJECT_ROOT / "data"
STATIC_DIR.mkdir(parents=True, exist_ok=True)
DASHBOARD_DIR.mkdir(parents=True, exist_ok=True)

sys.path.insert(0, str(PROJECT_ROOT))

SERVER_START_TIME = time.time()

# ── SoraEngine 싱글턴 헬퍼 ─────────────────────
_sora_engine_instance = None
_SORA_SYSTEM = "당신은 소라(Sora) — NEO GENESIS의 AI 비서입니다. 한국어로 답변하세요."


def _get_sora_engine():
    """SoraEngine 싱글턴 인스턴스 반환 (대시보드에서는 로드하지 않음).

    대시보드는 PC Agent Hub + REST API만 서빙.
    SoraEngine은 데몬 프로세스(텔레그램 봇)에서만 초기화.
    """
    global _sora_engine_instance
    # 클라우드 모드에서는 대시보드에서 SoraEngine을 로드하지 않음
    # (이벤트 루프 블로킹 방지)
    if os.environ.get("SORA_CLOUD_MODE"):
        return _sora_engine_instance  # None 반환 — 데몬이 별도로 로드
    if _sora_engine_instance is None:
        try:
            from src.core.sora_engine import get_sora_engine
            _sora_engine_instance = get_sora_engine()
        except Exception as e:
            logger.warning(f"[Dashboard] SoraEngine 로드 실패: {e}")
    return _sora_engine_instance


async def _fallback_gemini(prompt: str) -> str:
    """SoraEngine 사용 불가 시 Gemini 직접 호출 폴백."""
    try:
        from google import genai
        api_key = os.environ.get("GEMINI_API_KEY", "")
        if not api_key:
            return "⚠️ GEMINI_API_KEY 미설정"
        client = genai.Client(api_key=api_key)
        response = await asyncio.to_thread(
            client.models.generate_content,
            model=os.environ.get("GEMINI_MODEL", "gemini-2.0-flash"),
            contents=prompt,
        )
        return response.text
    except Exception as e:
        return f"⚠️ AI 응답 오류: {str(e)[:200]}"

# -- 인증 설정 (auth_router에서 관리) --
from src.core.dashboard.auth.auth_router import check_auth as _check_auth, DASHBOARD_TOKEN, TOKEN_HASH
SESSION_SECRET = os.environ.get("SESSION_SECRET", secrets.token_hex(32))

# -- GA4 캐시 --
_ga4_cache: dict[str, dict] = {}
GA4_CACHE_TTL = 300

# -- FastAPI lifespan (v2.0: Redis 연결) --
@asynccontextmanager
async def lifespan(app: FastAPI):
    """서버 시작/종료 — Redis 리스너 시작. SoraEngine은 Brain Worker에서만 로드."""
    # Redis Bus 연결 + PubSub 리스너 시작
    try:
        from src.core.queue.redis_bus import get_redis_bus
        bus = get_redis_bus()
        await bus.connect()
        await bus.start_listener()
        logger.info("[Lifespan] Redis Bus 연결 + 리스너 시작 ✓")
    except Exception as e:
        logger.warning(f"[Lifespan] Redis 연결 실패 (폴백 모드): {e}")

    logger.info("[Lifespan] Gateway 시작 (SoraEngine은 Brain Worker에서 실행)")
    yield
    # 종료
    try:
        bus = get_redis_bus()
        await bus.close()
    except Exception:
        pass
    logger.info("[Lifespan] Gateway 종료")

# -- FastAPI 앱 --
app = FastAPI(
    title="NEO GENESIS Command Center",
    description="1인 CEO 통합 관제 대시보드",
    version="3.1",
    lifespan=lifespan,
)

# 세션 미들웨어 (Google OAuth 필수)
# NOTE: 로컬 서버는 HTTP이므로 https_only=False 유지. Cloudflare Tunnel이 HTTPS를 처리.
app.add_middleware(
    SessionMiddleware,
    secret_key=SESSION_SECRET,
    same_site="lax",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# Sora 인증 미들웨어 (Tier 4)
try:
    from src.core.auth_middleware import register_auth_middleware
    register_auth_middleware(app)
    logger.info("[Init] SoraAuthMiddleware 등록 완료")
except Exception as e:
    logger.warning(f"[Init] SoraAuthMiddleware 로드 실패: {e}")

# Bridge Server 라우터 통합 (포트 8000 별도 프로세스 불필요)
try:
    from src.api.bridge_server import bridge_router
    app.include_router(bridge_router, tags=["bridge"])
    logger.info("[Init] Bridge Server 라우터 통합 완료 (20+ 엔드포인트)")
except ImportError as e:
    logger.warning(f"[Init] Bridge Server 라우터 로드 실패 (무시): {e}")

# Autonomous Loop API 라우터 통합
try:
    from src.api.autonomous_router import autonomous_router
    app.include_router(autonomous_router, tags=["autonomous"])
    logger.info("[Init] Autonomous Loop 라우터 통합 완료 (4 엔드포인트)")
except ImportError as e:
    logger.warning(f"[Init] Autonomous 라우터 로드 실패 (무시): {e}")

# Auth 라우터 통합 (dashboard/auth/auth_router.py에서 분리)
try:
    from src.core.dashboard.auth.auth_router import router as auth_router
    app.include_router(auth_router, tags=["auth"])
    logger.info("[Init] Auth 라우터 통합 완료")
except ImportError as e:
    logger.warning(f"[Init] Auth 라우터 로드 실패 (무시): {e}")

# WebSocket 라우터 통합 (dashboard/ws/ws_manager.py에서 분리)
try:
    from src.core.dashboard.ws.ws_manager import router as ws_router, get_ws_client_count
    app.include_router(ws_router, tags=["websocket"])
    logger.info("[Init] WebSocket 라우터 통합 완료")
except ImportError as e:
    logger.warning(f"[Init] WebSocket 라우터 로드 실패 (무시): {e}")

# PC Agent Hub 라우터 통합 (원격 PC 제어)
try:
    from src.core.pc_agent.hub import router as pc_agent_router
    app.include_router(pc_agent_router, tags=["pc-agent"])
    logger.info("[Init] PC Agent Hub 라우터 통합 완료 (WS + REST)")
except ImportError as e:
    logger.warning(f"[Init] PC Agent Hub 로드 실패 (무시): {e}")

# Telegram Webhook 라우터 (v2.0 — polling 대체)
try:
    from src.core.gateway.telegram_webhook import router as tg_webhook_router
    app.include_router(tg_webhook_router, tags=["telegram"])
    logger.info("[Init] Telegram Webhook 라우터 통합 완료")
except ImportError as e:
    logger.warning(f"[Init] Telegram Webhook 로드 실패 (무시): {e}")

# Chat REST API (v2.0 — sora-app, 대시보드, CLI용)
try:
    from src.core.gateway.chat_api import router as chat_router
    app.include_router(chat_router, tags=["chat"])
    logger.info("[Init] Chat API 라우터 통합 완료")
except ImportError as e:
    logger.warning(f"[Init] Chat API 로드 실패 (무시): {e}")

# v1 System API 라우터 (dashboard/routes/api_status.py에서 분리)
try:
    from src.core.dashboard.routes.api_status import router as status_router, set_start_time
    set_start_time(SERVER_START_TIME)
    app.include_router(status_router, prefix="/api", tags=["v1-system"])
    logger.info("[Init] v1 System API 라우터 통합 완료")
except ImportError as e:
    logger.warning(f"[Init] v1 System API 라우터 로드 실패 (무시): {e}")

# v2 Dashboard API 라우터 (dashboard/routes/api_v2.py에서 분리)
try:
    from src.core.dashboard.routes.api_v2 import router as v2_router
    app.include_router(v2_router, prefix="/api", tags=["v2-dashboard"])
    logger.info("[Init] v2 Dashboard API 라우터 통합 완료")
except ImportError as e:
    logger.warning(f"[Init] v2 Dashboard API 라우터 로드 실패 (무시): {e}")

# Board/Governance API 라우터 (dashboard/routes/api_board.py에서 분리)
try:
    from src.core.dashboard.routes.api_board import router as board_router
    app.include_router(board_router, prefix="/api", tags=["v2-board"])
    logger.info("[Init] Board/Governance API 라우터 통합 완료")
except ImportError as e:
    logger.warning(f"[Init] Board/Governance API 라우터 로드 실패 (무시): {e}")

# ── Sora Chat & WebSocket → dashboard/ws/ws_manager.py로 이관 완료 ──
# get_ws_client_count()는 위에서 import됨


# ======================================================
# 인증 함수 → dashboard/auth/auth_router.py로 이관 완료
# _check_auth는 auth_router.check_auth로 import됨
# ======================================================


# ======================================================
# 전역 인증 미들웨어 -- 모든 /api/* 경로 보호
# ======================================================

_PUBLIC_PATHS = ["/auth/", "/api/status", "/api/health", "/static/", "/app/sw.js", "/favicon"]

# 로컬 네트워크 채팅 허용 경로 (OAuth 완성 전까지)
_LOCAL_CHAT_PATHS = [
    "/api/v2/chat", "/api/v2/sora/", "/api/v2/system", "/api/v2/overview",
    "/api/v2/events", "/api/v2/push",
    # Bridge Server 통합 경로
    "/api/tenants", "/api/tenant/", "/api/keyword", "/api/generate",
    "/api/reviewlab", "/api/toolpick", "/api/deploy", "/api/mission",
    "/api/dev", "/api/task", "/api/tasks", "/api/skills", "/api/sandbox",
    "/api/a2a/", "/api/godel", "/api/watermark",
]

@app.middleware("http")
async def auth_middleware(request: Request, call_next):
    """인증되지 않은 요청 차단. /auth/*, /api/status 허용."""
    path = request.url.path

    # 공개 경로 허용
    if any(path.startswith(p) for p in _PUBLIC_PATHS):
        return await call_next(request)

    # 대시보드 HTML -- 로그인 UI 포함이므로 허용
    if path in ("/app", "/app/"):
        return await call_next(request)

    # 로컬 네트워크 → 모든 API 허용 (개발 편의 + OAuth 미설정 상태 대응)
    client_ip = request.client.host if request.client else ""
    if client_ip in ("127.0.0.1", "::1", "localhost") or client_ip.startswith(("192.168.", "10.")):
        return await call_next(request)

    # 외부 접속 -- API 경로 인증 필수
    if path.startswith("/api/"):
        authed = _check_auth(request)
        if not authed:
            return JSONResponse({"error": "Unauthorized"}, status_code=401)

    return await call_next(request)





# ══════════════════════════════════════════════════
# v1 API → dashboard/routes/api_status.py 로 이관 완료
# (status, tools, graph, security, skills, llm)
# ══════════════════════════════════════════════════


# ══════════════════════════════════════════════════
# v2 API — 통합 대시보드
# ══════════════════════════════════════════════════

# -- 인증 (Google OAuth) → dashboard/auth/auth_router.py로 이관 완료 --
# /auth/google, /auth/google/callback, /auth/logout, /auth/check, /auth/login
# 모두 auth_router에서 처리됨



# ══════════════════════════════════════════════════
# v2 API → dashboard/routes/api_v2.py + api_board.py 로 이관 완료
# (overview, coupang, sbu, activity, traffic, telemetry, finance,
#  governance, meeting, convene, ceo-action, whylab, sora/status,
#  healer, episodes, loyalty)
# ══════════════════════════════════════════════════


# 내부 유틸리티
# ══════════════════════════════════════════════════

def _format_uptime(seconds: int) -> str:
    h, r = divmod(seconds, 3600)
    m, s = divmod(r, 60)
    if h > 0:
        return f"{h}h {m}m"
    return f"{m}m {s}s"


def _load_finance() -> dict:
    """finance.json 로드"""
    fp = DATA_DIR / "finance.json"
    if fp.exists():
        return json.loads(fp.read_text(encoding="utf-8"))
    return {"revenue": {}, "cost": {}}


def _get_sbu_status() -> list[dict]:
    """전체 SBU 상태 목록 — 실시간 운영 메트릭 포함"""
    sbu_base = [
        {"id": "toolpick", "name": "ToolPick", "type": "profit", "description": "영문 SaaS 리뷰 블로그",
         "url": "https://www.toolpick.dev", "ga4_id": "G-8YRD4KPHZN", "revenue_source": "AdSense",
         "github": "https-www.toolpick.dev-"},
        {"id": "ur_wrong", "name": "UR WRONG", "type": "profit", "description": "AI 토론 플랫폼",
         "url": "https://ur-wrong.com", "ga4_id": "G-MHJ96JLHT2", "revenue_source": "AdSense + Viral",
         "github": "https-ur-wrong.com-"},
        {"id": "reviewlab", "name": "ReviewLab", "type": "profit", "description": "한국어 가전 리뷰 블로그",
         "url": "https://reviewlab.vercel.app", "ga4_id": "G-0NYTJ1DZRC", "revenue_source": "쿠팡 파트너스",
         "github": "reviewlab"},
        {"id": "whylab", "name": "WhyLab", "type": "lab", "description": "인과 의사결정 엔진",
         "url": "", "ga4_id": "", "revenue_source": "B2B SaaS",
         "github": "WhyLab"},
        {"id": "ethicaai", "name": "EthicaAI", "type": "lab", "description": "윤리 AI 연구소",
         "url": "https://ethicaai.vercel.app", "ga4_id": "G-ME6PDCNP8B", "revenue_source": "학술/논문",
         "github": "EthicaAI"},
        {"id": "game", "name": "Game (MCL)", "type": "lab", "description": "게임 + 크리처 랩",
         "url": "", "ga4_id": "G-2814PKJTGH", "revenue_source": "인앱 구매",
         "github": "game"},
        {"id": "crypto", "name": "Crypto", "type": "profit", "description": "파밍 / 리워드 하베스터",
         "url": "", "ga4_id": "", "revenue_source": "에어드랍",
         "github": ""},
        {"id": "portfolio", "name": "Portfolio", "type": "portfolio", "description": "heoyesol.kr",
         "url": "https://heoyesol.kr", "ga4_id": "G-SPPMR6QS9B", "revenue_source": "",
         "github": "portfolio"},
    ]

    # 실시간 운영 메트릭 수집
    for sbu in sbu_base:
        metrics = _collect_sbu_metrics(sbu["id"])
        sbu["status"] = metrics.get("status", "active")
        sbu["metrics"] = metrics

    return sbu_base


def _collect_sbu_metrics(sbu_id: str) -> dict:
    """SBU별 실시간 운영 메트릭 수집 (모든 값 null 방어)"""
    def _safe_metrics(d: dict) -> dict:
        """dict 내 None/undefined 값을 'N/A'로 교체"""
        return {k: (v if v is not None and v != '' else 'N/A') for k, v in d.items()}
    try:
        if sbu_id == "toolpick":
            return _safe_metrics(_metrics_blog(
                PROJECT_ROOT / "src" / "sbu" / "profit_center" / "blog" / "content",
                [".mdx", ".md"]
            ))
        elif sbu_id == "ur_wrong":
            return _safe_metrics(_metrics_battlefield())
        elif sbu_id == "reviewlab":
            return _safe_metrics(_metrics_blog(
                PROJECT_ROOT / "src" / "sbu" / "profit_center" / "profit" / "blog",
                [".md", ".mdx"]
            ))
        elif sbu_id == "whylab":
            return _safe_metrics(_metrics_whylab())
        elif sbu_id == "ethicaai":
            return _safe_metrics(_metrics_ethicaai())
        elif sbu_id == "game":
            return _safe_metrics(_metrics_game())
        elif sbu_id == "crypto":
            return _safe_metrics(_metrics_crypto())
        elif sbu_id == "portfolio":
            return _safe_metrics({"status": "active", "content_count": 0, "last_activity": None, "label": "포트폴리오 사이트"})
    except Exception as e:
        logger.warning(f"Metrics error [{sbu_id}]: {e}")
    return {"status": "active", "content_count": 0, "last_activity": 'N/A'}


def _metrics_blog(content_dir: Path, extensions: list[str]) -> dict:
    """블로그 SBU 메트릭 — 글 수, 마지막 발행일"""
    if not content_dir.exists():
        return {"status": "idle", "content_count": 0, "last_activity": None, "label": "콘텐츠 폴더 없음"}
    posts = []
    for ext in extensions:
        posts.extend(content_dir.rglob(f"*{ext}"))
    if not posts:
        return {"status": "idle", "content_count": 0, "last_activity": None, "label": "글 0개"}
    latest = max(posts, key=lambda f: f.stat().st_mtime)
    last_time = datetime.fromtimestamp(latest.stat().st_mtime)
    age_hours = (datetime.now() - last_time).total_seconds() / 3600
    status = "active" if age_hours < 48 else "idle"
    return {
        "status": status,
        "content_count": len(posts),
        "last_activity": last_time.isoformat(),
        "last_activity_ago": f"{int(age_hours)}h ago" if age_hours < 48 else f"{int(age_hours / 24)}d ago",
        "latest_file": latest.name,
        "label": f"{len(posts)}개 글",
    }


def _metrics_battlefield() -> dict:
    """UR WRONG 메트릭 — git 커밋, 배포 상태"""
    bf_dir = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "battlefield"
    git_dir = bf_dir / ".git"
    if not git_dir.exists():
        return {"status": "active", "content_count": 0, "last_activity": None, "label": "배포 운영 중"}
    try:
        result = subprocess.run(
            ["git", "-C", str(bf_dir), "log", "-1", "--format=%H|%s|%ai"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            parts = result.stdout.strip().split("|")
            commit_msg = parts[1] if len(parts) > 1 else ""
            commit_date = parts[2][:19] if len(parts) > 2 else ""
            return {
                "status": "active",
                "content_count": 0,
                "last_activity": commit_date,
                "last_commit": commit_msg[:50],
                "label": f"최근 커밋: {commit_msg[:30]}",
            }
    except Exception:
        pass
    return {"status": "active", "content_count": 0, "last_activity": None, "label": "배포 운영 중"}


def _metrics_whylab() -> dict:
    """WhyLab 메트릭 — 실험 리포트 수, 최신 실험"""
    reports_dir = PROJECT_ROOT / "src" / "core" / "decision_engine" / "paper" / "reports"
    if not reports_dir.exists():
        return {"status": "idle", "content_count": 0, "last_activity": None, "label": "실험 0건"}
    reports = list(reports_dir.glob("*.md"))
    if not reports:
        return {"status": "idle", "content_count": 0, "last_activity": None, "label": "실험 0건"}
    latest = max(reports, key=lambda f: f.stat().st_mtime)
    last_time = datetime.fromtimestamp(latest.stat().st_mtime)
    return {
        "status": "active",
        "content_count": len(reports),
        "last_activity": last_time.isoformat(),
        "latest_file": latest.name,
        "label": f"{len(reports)}개 실험 리포트",
    }


def _metrics_ethicaai() -> dict:
    """EthicaAI 메트릭 — 실험 데이터"""
    ea_dir = PROJECT_ROOT / "src" / "sbu" / "lab_creative" / "ethicaai"
    if not ea_dir.exists():
        return {"status": "idle", "content_count": 0, "last_activity": None, "label": "프로젝트 없음"}
    data_files = list(ea_dir.rglob("*.csv")) + list(ea_dir.rglob("*.pt")) + list(ea_dir.rglob("*.json"))
    py_files = list(ea_dir.rglob("*.py"))
    latest_all = data_files + py_files
    if not latest_all:
        return {"status": "idle", "content_count": 0, "last_activity": None, "label": "데이터 없음"}
    latest = max(latest_all, key=lambda f: f.stat().st_mtime)
    last_time = datetime.fromtimestamp(latest.stat().st_mtime)
    return {
        "status": "active",
        "content_count": len(data_files),
        "last_activity": last_time.isoformat(),
        "label": f"{len(py_files)}개 모듈, {len(data_files)}개 데이터",
    }


def _metrics_game() -> dict:
    """Game (MCL) 메트릭 — 크리처 이미지 수"""
    mcl_dir = Path("d:/00.test/multiverse-creature-lab/images")
    if not mcl_dir.exists():
        return {"status": "idle", "content_count": 0, "last_activity": None, "label": "이미지 없음"}
    images = list(mcl_dir.rglob("*.png")) + list(mcl_dir.rglob("*.webp"))
    if not images:
        return {"status": "idle", "content_count": 0, "last_activity": None, "label": "이미지 없음"}
    latest = max(images, key=lambda f: f.stat().st_mtime)
    last_time = datetime.fromtimestamp(latest.stat().st_mtime)
    return {
        "status": "active",
        "content_count": len(images),
        "last_activity": last_time.isoformat(),
        "label": f"{len(images)}개 크리처 이미지",
    }


def _metrics_crypto() -> dict:
    """Crypto 메트릭 — 크롤링/파밍 상태"""
    crypto_dir = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "profit" / "crypto"
    if not crypto_dir.exists():
        crypto_dir = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "profit"
    log_files = list(crypto_dir.rglob("*.log")) + list(crypto_dir.rglob("*.json"))
    if log_files:
        latest = max(log_files, key=lambda f: f.stat().st_mtime)
        last_time = datetime.fromtimestamp(latest.stat().st_mtime)
        return {"status": "active", "content_count": len(log_files), "last_activity": last_time.isoformat(), "label": "파밍 시스템 가동"}
    return {"status": "active", "content_count": 0, "last_activity": None, "label": "파밍 시스템 대기"}


def _collect_activity_log() -> list[dict]:
    """전체 SBU 최근 활동 로그 수집 — 파일 시스템 기반"""
    activities = []

    # ToolPick 최근 글
    tp_dir = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "blog" / "content"
    if tp_dir.exists():
        for f in sorted(tp_dir.rglob("*.mdx"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
            activities.append({
                "sbu": "ToolPick", "action": "글 발행",
                "detail": f.stem[:40],
                "time": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })

    # ReviewLab 최근 글
    rl_dir = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "profit" / "blog"
    if rl_dir.exists():
        for f in sorted(rl_dir.rglob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
            activities.append({
                "sbu": "ReviewLab", "action": "글 발행",
                "detail": f.stem[:40],
                "time": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })

    # WhyLab 최근 실험
    wl_dir = PROJECT_ROOT / "src" / "core" / "decision_engine" / "paper" / "reports"
    if wl_dir.exists():
        for f in sorted(wl_dir.glob("*.md"), key=lambda x: x.stat().st_mtime, reverse=True)[:3]:
            activities.append({
                "sbu": "WhyLab", "action": "실험 완료",
                "detail": f.stem[:40],
                "time": datetime.fromtimestamp(f.stat().st_mtime).isoformat(),
            })

    # UR WRONG git 커밋
    bf_dir = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "battlefield"
    try:
        result = subprocess.run(
            ["git", "-C", str(bf_dir), "log", "-3", "--format=%s|%ai"],
            capture_output=True, text=True, timeout=5
        )
        if result.returncode == 0:
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    msg, dt = line.rsplit("|", 1)
                    activities.append({"sbu": "UR WRONG", "action": "코드 배포", "detail": msg.strip()[:40], "time": dt.strip()[:19]})
    except Exception:
        pass

    # 시간순 정렬 (최신 먼저)
    activities.sort(key=lambda x: x.get("time", ""), reverse=True)
    return activities[:15]


def _load_governance_log() -> list[dict]:
    """HIVE MIND 거버넌스 로그 로드"""
    log_dir = DATA_DIR / "governance"
    if not log_dir.exists():
        # 샘플 데이터 반환
        return [
            {"date": "2026-02-17", "title": "GA4 통합 수집 시스템 구축", "status": "approved", "department": "CTO"},
            {"date": "2026-02-16", "title": "UR WRONG 에이전트 배틀 버그 수정", "status": "approved", "department": "CTO"},
            {"date": "2026-02-15", "title": "블로그 SEO 콘텐츠 파이프라인 개선", "status": "approved", "department": "CMO"},
            {"date": "2026-02-14", "title": "EthicaAI Phase 1 실험 실행", "status": "approved", "department": "CTO"},
            {"date": "2026-02-13", "title": "HIVE MIND 거버넌스 v3.0 재설계", "status": "approved", "department": "CEO"},
        ]

    logs = []
    for f in sorted(log_dir.glob("*.json"), reverse=True):
        try:
            logs.append(json.loads(f.read_text(encoding="utf-8")))
        except Exception:
            pass
    return logs


async def _call_ga4_proxy() -> dict:
    """GA4 Data API 프록시 — Node.js 프로세스 호출"""
    script_path = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "blog" / "scripts" / "test-ga4-all.ts"
    if not script_path.exists():
        return {"sites": [], "total": {"sessions": 0, "pageViews": 0}}

    report_path = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "blog" / "scripts" / "ga4-traffic-report.json"

    # 캐시된 리포트 파일 사용 (5분 이내면)
    if report_path.exists():
        age = time.time() - report_path.stat().st_mtime
        if age < GA4_CACHE_TTL:
            try:
                return json.loads(report_path.read_text(encoding="utf-8"))
            except Exception:
                pass

    # Node.js로 GA4 데이터 수집 실행
    try:
        proc = await asyncio.create_subprocess_exec(
            "npx", "tsx", str(script_path),
            cwd=str(script_path.parent.parent),
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await asyncio.wait_for(proc.wait(), timeout=30)

        if report_path.exists():
            return json.loads(report_path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.warning(f"GA4 proxy error: {e}")

    return {"sites": [], "total": {"sessions": 0, "pageViews": 0}}


# ── Favicon 404 방지 ───────────────────────────

@app.get("/favicon.ico")
async def favicon():
    """빈 favicon — 404 방지"""
    return Response(content=b"", media_type="image/x-icon")


# ── 정적 파일 (아이콘 등) ──────────────────────
from starlette.staticfiles import StaticFiles

_static_dir = DASHBOARD_DIR / "static"
if _static_dir.exists():
    app.mount("/static", StaticFiles(directory=str(_static_dir)), name="static")

# ── 정적 파일 + SPA 라우팅 ──────────────────────

@app.get("/old")
async def serve_old_dashboard():
    """기존 대시보드 HTML 서빙"""
    html_path = STATIC_DIR / "dashboard.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>dashboard.html not found</h1>", status_code=404)


@app.get("/")
async def serve_command_center():
    """통합 대시보드 서빙"""
    html_path = DASHBOARD_DIR / "index.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    # 폴백: 기존 대시보드
    old_path = STATIC_DIR / "dashboard.html"
    if old_path.exists():
        return HTMLResponse(old_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>Command Center not found</h1>", status_code=404)


@app.get("/login")
async def serve_login():
    """로그인 페이지"""
    html_path = DASHBOARD_DIR / "auth.html"
    if html_path.exists():
        return HTMLResponse(html_path.read_text(encoding="utf-8"))
    return HTMLResponse("<h1>auth.html not found</h1>", status_code=404)


# ── 모바일 앱 (PWA) ─────────────────────────────

@app.get("/app")
async def serve_app():
    """CEO 전용 모바일 앱 서빙"""
    html_path = DASHBOARD_DIR / "app.html"
    if html_path.exists():
        return HTMLResponse(
            html_path.read_text(encoding="utf-8"),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return HTMLResponse("<h1>app.html not found</h1>", status_code=404)


@app.get("/sora")
async def serve_sora():
    """Sora God Mode 전용 페이지"""
    html_path = DASHBOARD_DIR / "sora.html"
    if html_path.exists():
        return HTMLResponse(
            html_path.read_text(encoding="utf-8"),
            headers={
                "Cache-Control": "no-cache, no-store, must-revalidate",
                "Pragma": "no-cache",
                "Expires": "0",
            },
        )
    return HTMLResponse("<h1>sora.html not found</h1>", status_code=404)

@app.get("/app/manifest.json")
async def serve_manifest():
    """PWA 매니페스트"""
    path = DASHBOARD_DIR / "manifest.json"
    if path.exists():
        return JSONResponse(json.loads(path.read_text(encoding="utf-8")))
    return JSONResponse({"error": "manifest not found"}, status_code=404)


@app.get("/app/sw.js")
async def serve_sw():
    """Service Worker"""
    path = DASHBOARD_DIR / "sw.js"
    if path.exists():
        return Response(
            content=path.read_text(encoding="utf-8"),
            media_type="application/javascript",
            headers={"Service-Worker-Allowed": "/"},
        )
    return Response("// sw not found", media_type="application/javascript")


# ── 채팅 API — SoraEngine 통합 (JARVIS Core) ────
#
# 이전: 단순 Gemini API 직접 호출 (도구 0개, 기억 없음)
# 이후: SoraEngine 경유 (45개 도구 + 기억 + RAG + 프롬프트빌더)
#

# SoraEngine 인스턴스 (지연 초기화)
_sora_engine = None


def _get_sora_engine():
    """SoraEngine 싱글턴 — 클라우드 모드에서는 비활성화 (Gateway 블로킹 방지)."""
    if os.environ.get("SORA_CLOUD_MODE"):
        return None
    global _sora_engine
    if _sora_engine is None:
        try:
            from src.core.sora_engine import get_sora_engine
            _sora_engine = get_sora_engine()
            logger.info("[Dashboard] SoraEngine 연결 성공")
        except Exception as e:
            logger.error(f"[Dashboard] SoraEngine 초기화 실패: {e}")
            return None
    return _sora_engine


# 레거시 폴백용 (SoraEngine 로드 실패 시)
_SORA_SYSTEM = (
    "당신은 NEO GENESIS의 AI 비서 '소라'입니다. "
    "CEO 전용 모바일 앱에서 대화 중입니다. "
    "한국어로 간결하고 친절하게 답변하세요. "
    "시스템 상태, 업무 현황, 일정 등을 안내할 수 있습니다."
)


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
            logger.warning(f"[Chat] 레거시 폴백 실패: {e}")
    return "⛔ AI 서비스가 일시적으로 불안정합니다. 잠시 후 다시 시도해주세요."


@app.post("/api/v2/chat")
async def api_chat(request: Request):
    """웹 채팅 — SoraEngine 경유 (45개 도구 + 기억 + RAG)

    SoraEngine 활성화 시: 도구 자동 실행, 기억 영속, RAG 검색 지원.
    SoraEngine 비활성화 시: 레거시 Gemini 직접 호출 (도구 없음).
    """
    try:
        body = await request.json()
        text = body.get("message", "").strip()
        if not text:
            return JSONResponse({"reply": "메시지를 입력해주세요"})

        # SoraEngine으로 처리 (도구 + 기억 + RAG)
        engine = _get_sora_engine()
        if engine:
            reply = await engine.process(text)
        else:
            # 폴백: 레거시 Gemini 직접 호출
            prompt = f"{_SORA_SYSTEM}\n\n사용자: {text}"
            reply = await _fallback_gemini(prompt)

        return JSONResponse({"reply": reply})

    except Exception as e:
        logger.error(f"Chat API error: {e}")
        return JSONResponse({"reply": f"오류 발생: {str(e)[:200]}"})


@app.post("/api/v2/chat/upload")
async def api_chat_upload(request: Request):
    """파일 업로드 + AI 분석 — SoraEngine 경유"""
    try:
        form = await request.form()
        file = form.get("file")
        message = form.get("message", "이 파일을 분석해주세요")

        if not file:
            return JSONResponse({"reply": "파일이 없습니다"})

        file_content = await file.read()
        filename = file.filename or "unknown"

        engine = _get_sora_engine()
        if engine:
            # 파일을 임시 저장 후 SoraEngine에 전달
            import tempfile
            suffix = Path(filename).suffix
            with tempfile.NamedTemporaryFile(
                delete=False, suffix=suffix, dir=str(STATIC_DIR)
            ) as tmp:
                tmp.write(file_content)
                tmp_path = tmp.name

            try:
                reply = await engine.process(message, file_path=tmp_path)
            finally:
                try:
                    os.unlink(tmp_path)
                except Exception:
                    pass
        else:
            # 폴백: 레거시 처리
            if filename.lower().endswith(('.png', '.jpg', '.jpeg', '.gif', '.webp')):
                from PIL import Image
                import io
                img = Image.open(io.BytesIO(file_content))
                from google import genai
                api_key = os.environ.get("GEMINI_API_KEY", "")
                client = genai.Client(api_key=api_key)
                response = await asyncio.to_thread(
                    client.models.generate_content,
                    model="gemini-2.0-flash",
                    contents=[message, img],
                )
                reply = response.text or "분석 실패"
            else:
                text_content = file_content.decode('utf-8', errors='replace')[:5000]
                prompt = (
                    f"{_SORA_SYSTEM}\n\n"
                    f"파일명: {filename}\n내용:\n{text_content}\n\n{message}"
                )
                reply = await _fallback_gemini(prompt)

        return JSONResponse({"reply": reply})

    except Exception as e:
        logger.error(f"Chat upload error: {e}")
        return JSONResponse({"reply": f"파일 분석 오류: {str(e)[:200]}"})


# ══════════════════════════════════════════════════
# WebSocket 실시간 채팅 → dashboard/ws/ws_manager.py로 이관 완료
# /ws/chat, /api/v2/chat/history 모두 ws_router에서 처리됨
# ══════════════════════════════════════════════════




# ══════════════════════════════════════════════════
# SSE 대시보드 이벤트 스트림 (/api/v2/events)
# ══════════════════════════════════════════════════

async def _sse_generator():
    """30초 간격으로 대시보드 데이터를 SSE로 스트리밍"""
    while True:
        try:
            data = {}

            # 시스템 상태
            try:
                import psutil
                data["system"] = {
                    "cpu": psutil.cpu_percent(),
                    "ram": psutil.virtual_memory().percent,
                    "disk": psutil.disk_usage('/').percent if platform.system() != 'Windows' else psutil.disk_usage('D:\\').percent,
                }
            except Exception:
                data["system"] = {"cpu": 0, "ram": 0, "disk": 0}

            # 각 SBU 상태
            try:
                from src.core.dashboard.data_bridge import get_data_bridge
                bridge = get_data_bridge()
                data["overview"] = bridge.get_kpi_overview()
            except Exception:
                pass

            # 서버 업타임
            data["uptime"] = _format_uptime(int(time.time() - SERVER_START_TIME))
            try:
                data["ws_clients"] = get_ws_client_count()
            except NameError:
                data["ws_clients"] = 0
            data["timestamp"] = datetime.now().isoformat()

            yield f"data: {json.dumps(data, ensure_ascii=False, default=str)}\n\n"

        except Exception as e:
            yield f"data: {{\"error\": \"{str(e)[:100]}\"}}\n\n"

        await asyncio.sleep(30)


@app.get("/api/v2/events")
async def sse_events():
    """SSE 엔드포인트 — 대시보드 실시간 갱신"""
    return StreamingResponse(
        _sse_generator(),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",
            "Connection": "keep-alive",
            "X-Accel-Buffering": "no",  # nginx 프록시 대응
        },
    )


# ══════════════════════════════════════════════════
# Push 알림 API
# ══════════════════════════════════════════════════

_PUSH_SUBS_FILE = PROJECT_ROOT / "src" / "core" / "data" / "push_subscriptions.json"
_VAPID_FILE = PROJECT_ROOT / "src" / "core" / "data" / "vapid_keys.json"


def _get_vapid_keys() -> dict:
    """VAPID 키 로드"""
    if _VAPID_FILE.exists():
        try:
            return json.loads(_VAPID_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def _load_push_subs() -> list:
    if _PUSH_SUBS_FILE.exists():
        try:
            return json.loads(_PUSH_SUBS_FILE.read_text(encoding="utf-8"))
        except Exception:
            pass
    return []


def _save_push_subs(subs: list):
    _PUSH_SUBS_FILE.parent.mkdir(parents=True, exist_ok=True)
    _PUSH_SUBS_FILE.write_text(json.dumps(subs, ensure_ascii=False), encoding="utf-8")


@app.get("/api/v2/push/vapid-key")
async def get_vapid_key():
    """VAPID 공개키 반환"""
    keys = _get_vapid_keys()
    public_key = keys.get("public_key", "")
    if not public_key:
        return JSONResponse({"publicKey": "", "note": "VAPID 키 미설정"})
    return JSONResponse({"publicKey": public_key})


@app.post("/api/v2/push/subscribe")
async def push_subscribe(request: Request):
    """Push 구독 등록"""
    try:
        sub_data = await request.json()
        subs = _load_push_subs()
        endpoints = {s.get("endpoint") for s in subs}
        if sub_data.get("endpoint") not in endpoints:
            subs.append(sub_data)
            _save_push_subs(subs)
            logger.info(f"[Push] 새 구독 등록 (총 {len(subs)}건)")
        return JSONResponse({"ok": True, "total": len(subs)})
    except Exception as e:
        return JSONResponse({"error": str(e)[:200]}, status_code=400)


# ══════════════════════════════════════════════════
# Billing — SBU별 Gemini API 비용 추적
# ══════════════════════════════════════════════════

# SBU별 API 키 매핑
_SBU_API_KEYS = {
    "Sora": os.environ.get("SORA_GEMINI_API_KEY", ""),
    "ToolPick": os.environ.get("TOOLPICK_GEMINI_API_KEY", ""),
    "UR WRONG": os.environ.get("BATTLEFIELD_GEMINI_API_KEY", ""),
    "ReviewLab": os.environ.get("REVIEWLAB_GEMINI_API_KEY", ""),
    "WhyLab": os.environ.get("WHYLAB_GEMINI_API_KEY", ""),
    "EthicaAI": os.environ.get("ETHICAAI_GEMINI_API_KEY", ""),
    "Game/MCL": os.environ.get("MCL_GEMINI_API_KEY", ""),
    "Crypto": os.environ.get("CRYPTO_GEMINI_API_KEY", ""),
}

# Gemini 2.0 Flash 가격 (USD / 1M tokens) — 2026-02 기준
_GEMINI_PRICING = {
    "input_per_1m": 0.10,   # $0.10 / 1M input tokens
    "output_per_1m": 0.40,  # $0.40 / 1M output tokens
}
_KRW_PER_USD = float(os.environ.get("KRW_PER_USD", "1450"))
_CREDIT_TOTAL_KRW = float(os.environ.get("GEMINI_CREDIT_KRW", "429024"))
_CREDIT_EXPIRY = os.environ.get("GEMINI_CREDIT_EXPIRY", "2026-05-18")

# 사용량 로그 (JSON 파일)
_USAGE_LOG_PATH = PROJECT_ROOT / "data" / "gemini_usage_log.json"


def _load_usage_log() -> dict:
    if _USAGE_LOG_PATH.exists():
        try:
            return json.loads(_USAGE_LOG_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {"sbu_usage": {}, "last_updated": ""}


def _save_usage_log(data: dict):
    _USAGE_LOG_PATH.parent.mkdir(parents=True, exist_ok=True)
    _USAGE_LOG_PATH.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


@app.get("/api/v2/billing")
async def api_billing():
    """SBU별 Gemini API 비용 현황"""
    usage = _load_usage_log()
    sbu_data = usage.get("sbu_usage", {})

    total_cost_krw = 0.0
    sbu_costs = []
    for sbu_name, key_val in _SBU_API_KEYS.items():
        sbu_info = sbu_data.get(sbu_name, {})
        input_tokens = sbu_info.get("input_tokens", 0)
        output_tokens = sbu_info.get("output_tokens", 0)
        requests = sbu_info.get("requests", 0)

        cost_usd = (
            (input_tokens / 1_000_000) * _GEMINI_PRICING["input_per_1m"]
            + (output_tokens / 1_000_000) * _GEMINI_PRICING["output_per_1m"]
        )
        cost_krw = cost_usd * _KRW_PER_USD
        total_cost_krw += cost_krw

        sbu_costs.append({
            "sbu": sbu_name,
            "has_key": bool(key_val),
            "requests": requests,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "cost_usd": round(cost_usd, 4),
            "cost_krw": round(cost_krw, 1),
        })

    credit_remaining = _CREDIT_TOTAL_KRW - total_cost_krw

    return {
        "project_id": "gen-lang-client-0899707972",
        "project_number": 404017831005,
        "model": "gemini-2.0-flash",
        "pricing": _GEMINI_PRICING,
        "krw_per_usd": _KRW_PER_USD,
        "credit": {
            "total_krw": _CREDIT_TOTAL_KRW,
            "used_krw": round(total_cost_krw, 1),
            "remaining_krw": round(credit_remaining, 1),
            "expiry": _CREDIT_EXPIRY,
            "usage_pct": round(total_cost_krw / _CREDIT_TOTAL_KRW * 100, 2),
        },
        "sbu_costs": sbu_costs,
        "last_updated": usage.get("last_updated", ""),
        "note": "자체 추적 기반. /api/v2/billing/record POST로 사용량 기록.",
    }


@app.post("/api/v2/billing/record")
async def api_billing_record(request: Request):
    """SBU별 사용량 기록 — 각 SBU가 API 호출 후 콜백"""
    body = await request.json()
    sbu_name = body.get("sbu", "")
    input_tokens = body.get("input_tokens", 0)
    output_tokens = body.get("output_tokens", 0)

    if not sbu_name:
        raise HTTPException(400, "sbu 필수")

    usage = _load_usage_log()
    sbu_data = usage.setdefault("sbu_usage", {})
    sbu = sbu_data.setdefault(sbu_name, {"requests": 0, "input_tokens": 0, "output_tokens": 0})
    sbu["requests"] += 1
    sbu["input_tokens"] += input_tokens
    sbu["output_tokens"] += output_tokens
    usage["last_updated"] = datetime.now().isoformat()
    _save_usage_log(usage)

    return {"ok": True, "sbu": sbu_name, "accumulated": sbu}


# ══════════════════════════════════════════════════
# Image Engine — 로컬 이미지 생성 API
# ══════════════════════════════════════════════════

@app.post("/api/v2/image/generate")
async def api_image_generate(request: Request):
    """SDXL Turbo 로컬 이미지 생성 — 각 SBU에서 HTTP로 호출"""
    body = await request.json()
    prompt = body.get("prompt", "")
    if not prompt:
        raise HTTPException(400, "prompt 필수")

    sbu = body.get("sbu", "unknown")
    steps = body.get("steps", 4)
    width = body.get("width", 512)
    height = body.get("height", 512)
    seed = body.get("seed", -1)

    try:
        from src.core.image_engine import get_image_engine
        engine = get_image_engine()

        # 비동기로 실행 (블로킹 방지)
        import functools
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            None,
            functools.partial(
                engine.generate,
                prompt=prompt,
                steps=steps,
                width=width,
                height=height,
                seed=seed,
            )
        )

        # 활동 로그에 기록
        logger.info(f"[ImageEngine] {sbu} 이미지 생성 완료: {result.get('duration_ms', 0)}ms")

        return {
            "ok": not result.get("error"),
            "sbu": sbu,
            **result,
        }

    except ImportError:
        raise HTTPException(503, "ImageEngine 미설치 (diffusers/torch 필요)")
    except Exception as e:
        raise HTTPException(500, f"이미지 생성 실패: {str(e)[:200]}")


@app.get("/api/v2/image/status")
async def api_image_status():
    """이미지 엔진 상태 조회"""
    try:
        from src.core.image_engine import get_image_engine
        engine = get_image_engine()
        return engine.get_status()
    except ImportError:
        return {
            "available": False,
            "reason": "diffusers/torch 미설치",
            "install_cmd": "pip install diffusers transformers accelerate torch",
        }
    except Exception as e:
        return {"available": False, "error": str(e)[:200]}


@app.get("/api/v2/scheduler")
async def api_scheduler():
    """하이브리드 스케줄러 상태 조회 (로컬 워치독 + 서버 파이프라인)."""
    result = {"mode": "hybrid", "local_watchdog": None, "server_pipeline": None}

    # 1. 로컬 워치독
    try:
        from src.core.neo_scheduler import get_scheduler
        sched = get_scheduler()
        result["local_watchdog"] = sched.status() if sched else {"running": False, "message": "워치독 미시작"}
    except ImportError:
        result["local_watchdog"] = {"running": False, "message": "모듈 미발견"}

    # 2. 서버 파이프라인 (Supabase job_queue)
    try:
        import urllib.request
        sb_url = os.environ.get("SUPABASE_URL", "")
        sb_key = os.environ.get("SUPABASE_SERVICE_KEY", "")
        if sb_url and sb_key:
            url = f"{sb_url}/rest/v1/job_queue?select=sbu,status,created_at&order=created_at.desc&limit=10"
            req = urllib.request.Request(url, headers={"apikey": sb_key, "Authorization": f"Bearer {sb_key}"})
            with urllib.request.urlopen(req, timeout=5) as r:
                jobs = json.loads(r.read())
                status_counts = {}
                for j in jobs:
                    s = j.get("status", "unknown")
                    status_counts[s] = status_counts.get(s, 0) + 1
                result["server_pipeline"] = {
                    "connected": True,
                    "recent_jobs": len(jobs),
                    "status_counts": status_counts,
                    "latest": jobs[:3] if jobs else [],
                }
        else:
            result["server_pipeline"] = {"connected": False, "error": "SUPABASE_URL/KEY 미설정"}
    except Exception as e:
        result["server_pipeline"] = {"connected": False, "error": str(e)[:100]}

    return result


@app.get("/api/v2/system")
async def api_system():
    """시스템 자원 현황 (CPU/RAM/GPU/디스크)."""
    import psutil
    metrics = {
        "cpu_pct": psutil.cpu_percent(interval=0.5),
        "cpu_count": psutil.cpu_count(),
        "ram_pct": psutil.virtual_memory().percent,
        "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
        "ram_total_gb": round(psutil.virtual_memory().total / (1024**3), 1),
        "disk_pct": psutil.disk_usage("D:\\").percent if Path("D:\\").exists() else psutil.disk_usage("C:\\").percent,
    }
    # GPU
    try:
        import subprocess as sp
        r = sp.run(
            ["nvidia-smi", "--query-gpu=name,utilization.gpu,temperature.gpu,memory.used,memory.total",
             "--format=csv,noheader,nounits"],
            capture_output=True, text=True, timeout=5,
        )
        if r.returncode == 0 and r.stdout.strip():
            p = r.stdout.strip().split(",")
            if len(p) >= 5:
                metrics["gpu_name"] = p[0].strip()
                metrics["gpu_util_pct"] = float(p[1].strip())
                metrics["gpu_temp_c"] = float(p[2].strip())
                mem_used = float(p[3].strip())
                mem_total = float(p[4].strip())
                metrics["gpu_vram_pct"] = round(mem_used / mem_total * 100, 1) if mem_total > 0 else 0
                metrics["gpu_vram_used_gb"] = round(mem_used / 1024, 1)
                metrics["gpu_vram_total_gb"] = round(mem_total / 1024, 1)
    except Exception:
        metrics["gpu_name"] = "N/A"

    # 부하 수준 판정
    cpu, ram = metrics.get("cpu_pct", 0), metrics.get("ram_pct", 0)
    gpu_v = metrics.get("gpu_vram_pct", 0)
    if cpu > 85 or ram > 88 or gpu_v > 90:
        metrics["load_level"] = "CRITICAL"
    elif cpu > 70 or ram > 75 or gpu_v > 80:
        metrics["load_level"] = "CAUTION"
    else:
        metrics["load_level"] = "NORMAL"

    return metrics



# ══════════════════════════════════════════════════
# Board/Sora Log API → dashboard/routes/api_board.py 로 이관 완료
# ══════════════════════════════════════════════════

async def root_redirect():
    """루트(/) 접속 시 /app으로 리다이렉트"""
    return RedirectResponse(url="/app")


def start_dashboard(port: int = 7700):
    """대시보드 서버 시작"""
    import uvicorn
    logger.info(f"[Dashboard] http://localhost:{port} 에서 시작")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


# ══════════════════════════════════════════════════
# Sora God Mode API
# ══════════════════════════════════════════════════

@app.get("/api/v2/sora/goals")
async def sora_goals_list():
    """Sora 활성 목표 목록."""
    try:
        from src.core.agents.goal_manager import GoalManager
        gm = GoalManager()
        goals = gm.list_goals()
        due = gm.get_due_goals()
        return {
            "goals": goals,
            "due_count": len(due),
            "total": len(goals),
        }
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/goals")
async def sora_goals_add(request: Request):
    """새 목표 추가."""
    try:
        from src.core.agents.goal_manager import GoalManager
        body = await request.json()
        gm = GoalManager()
        goal = gm.add_goal(
            goal_type=body.get("type", "directive"),
            description=body.get("description", ""),
            **{k: v for k, v in body.items() if k not in ("type", "description")},
        )
        return {"success": True, "goal": goal}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.put("/api/v2/sora/goals/{goal_id}")
async def sora_goals_update(goal_id: str, request: Request):
    """목표 수정."""
    try:
        from src.core.agents.goal_manager import GoalManager
        body = await request.json()
        gm = GoalManager()
        updated = gm.update_goal(goal_id, **body)
        if updated:
            return {"success": True, "goal": updated}
        return {"error": f"Goal not found: {goal_id}"}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.delete("/api/v2/sora/goals/{goal_id}")
async def sora_goals_delete(goal_id: str):
    """목표 삭제."""
    try:
        from src.core.agents.goal_manager import GoalManager
        gm = GoalManager()
        removed = gm.remove_goal(goal_id)
        return {"success": removed}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/system")
async def sora_system_status():
    """Sora 시스템 상태 (PC 모니터링 + 목표 + 모델 라우터)."""
    try:
        from src.core.agents.system_monitor import SystemMonitor
        from src.core.agents.goal_manager import GoalManager
        from src.core.utils.llm_client import ModelRouter

        sm = SystemMonitor()
        gm = GoalManager()
        router = ModelRouter()

        return {
            "system": sm.collect(),
            "goals": {
                "active": len(gm.list_goals(status="active")),
                "due": len(gm.get_due_goals()),
            },
            "models": {tier: info[1] for tier, info in router.MODELS.items()},
            "god_mode": True,
        }
    except Exception as e:
        return {"error": str(e)[:200]}


# ── Sora PC 제어 API ───────────────────────

@app.get("/api/v2/sora/screen")
async def sora_screen_capture():
    """현재 화면을 캡처하여 JPEG로 반환."""
    from fastapi.responses import Response
    try:
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        img_bytes = vc.capture_bytes(quality=75)
        if img_bytes:
            return Response(content=img_bytes, media_type="image/jpeg")
        return {"error": "Capture failed"}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/screen/live")
async def sora_screen_live():
    """CCTV 모드 live_view.jpg 반환 (실시간 스트리밍용)."""
    from fastapi.responses import FileResponse
    live_path = Path(__file__).resolve().parent.parent.parent / "data" / "live_view.jpg"
    if live_path.exists():
        return FileResponse(str(live_path), media_type="image/jpeg",
                           headers={"Cache-Control": "no-cache, no-store"})
    # live_view가 없으면 즉시 캡처
    from fastapi.responses import Response
    try:
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        img_bytes = vc.capture_bytes(quality=50)
        if img_bytes:
            return Response(content=img_bytes, media_type="image/jpeg")
    except Exception:
        pass
    return {"error": "No live view available"}


@app.post("/api/v2/sora/chat")
async def sora_chat(request: Request):
    """Sora에게 자연어 명령 → 실행 결과 반환 (세션 기반 히스토리)."""
    try:
        body = await request.json()
        message = body.get("message", "")
        session_id = body.get("session_id", f"default-{int(time.time())}")
        if not message:
            return {"error": "message is required"}

        # 세션 히스토리 관리
        if session_id not in _chat_sessions:
            _chat_sessions[session_id] = {
                "history": [],
                "created_at": time.time(),
            }
        session = _chat_sessions[session_id]
        session["history"].append({"role": "user", "content": message})

        # 히스토리가 20턴 초과 시 앞 15턴 요약 압축
        if len(session["history"]) > 40:  # 20턴 = 40 메시지 (user+assistant)
            old = session["history"][:30]
            summary_text = " / ".join([m["content"][:50] for m in old])
            session["history"] = [
                {"role": "system", "content": f"[이전 대화 요약] {summary_text[:500]}"},
                *session["history"][30:],
            ]

        # SoraEngine 경유 — Agent 도구 포함 (Phase A 통합)
        engine = _get_sora_engine()
        if engine:
            # 히스토리 컨텍스트를 포함한 메시지 구성
            context_lines = []
            for m in session["history"][-10:]:
                role = "사용자" if m["role"] == "user" else "Sora"
                context_lines.append(f"{role}: {m['content'][:200]}")
            history_context = "\n".join(context_lines)
            full_message = f"[대화 히스토리]\n{history_context}\n\n[현재 요청]\n{message}"
            response_text = await engine.process(full_message)
        else:
            # 폴백: 레거시 Gemini 직접 호출
            response_text = await _fallback_gemini(f"{_SORA_SYSTEM}\n\n사용자: {message}")

        session["history"].append({"role": "assistant", "content": response_text})

        # WebSocket 알림 브로드캐스트
        try:
            from src.core.dashboard.ws.ws_manager import ws_broadcast
            await ws_broadcast({"type": "chat_response", "session_id": session_id,
                                "message": response_text[:200]})
        except Exception:
            pass

        return {
            "response": response_text,
            "status": "completed",
            "session_id": session_id,
            "history_length": len(session["history"]),
        }
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/chat/history")
async def sora_chat_history(session_id: str = Query(default="default")):
    """채팅 세션 히스토리 조회."""
    if session_id not in _chat_sessions:
        return {"history": [], "session_id": session_id}
    session = _chat_sessions[session_id]
    return {
        "history": session["history"][-50:],
        "session_id": session_id,
        "total": len(session["history"]),
    }


@app.delete("/api/v2/sora/chat/history")
async def sora_chat_clear(session_id: str = Query(default="default")):
    """채팅 세션 히스토리 초기화."""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
    return {"success": True}


# ── Sora 인증 API ──────────────────────────

@app.post("/api/v2/sora/auth/login")
async def sora_auth_login(request: Request):
    """대시보드 로그인 — 시크릿 검증 후 토큰 반환."""
    try:
        body = await request.json()
        password = body.get("password", "")
        from src.core.auth_middleware import verify_token, DASHBOARD_SECRET
        if verify_token(password):
            return {"success": True, "token": DASHBOARD_SECRET}
        return JSONResponse(status_code=401, content={"error": "Invalid password"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


# ── WebSocket 실시간 알림 ──────────────────

@app.websocket("/ws/sora")
async def sora_websocket(websocket: WebSocket):
    """Sora 실시간 알림 채널 (토큰 인증)."""
    # WebSocket 토큰 검증
    try:
        from src.core.auth_middleware import verify_token
        token = websocket.query_params.get("token", "")
        if not token or not verify_token(token):
            await websocket.close(code=4001, reason="Unauthorized")
            logger.warning(f"🔒 WS auth failed (IP: {websocket.client.host})")
            return
    except ImportError:
        pass  # 미들웨어 없으면 통과 (하위 호환)

    await websocket.accept()
    _ws_clients.add(websocket)
    logger.info(f"🔌 WebSocket connected (total: {len(_ws_clients)})")
    try:
        # 연결 즉시 시스템 상태 전송
        try:
            from src.core.agents.system_monitor import SystemMonitor
            sm = SystemMonitor()
            await websocket.send_json({"type": "system_status", "data": sm.collect()})
        except Exception:
            pass

        while True:
            # 클라이언트 ping 대기 (연결 유지)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong", "ts": int(time.time())})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _ws_clients.discard(websocket)
        logger.info(f"🔌 WebSocket disconnected (total: {len(_ws_clients)})")


# ── 클립보드 API ──────────────────────────

@app.get("/api/v2/sora/clipboard")
async def sora_clipboard_read():
    """클립보드 내용 읽기."""
    try:
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        content = vc.clipboard_read()
        return {"content": content}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/clipboard")
async def sora_clipboard_write(request: Request):
    """클립보드에 텍스트 쓰기."""
    try:
        body = await request.json()
        text = body.get("text", "")
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        result = vc.clipboard_write(text)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


# ── 영역 캡처 API ──────────────────────────

@app.get("/api/v2/sora/screen/region")
async def sora_screen_region(
    x: int = Query(default=0), y: int = Query(default=0),
    w: int = Query(default=800), h: int = Query(default=600),
):
    """화면 특정 영역만 캡처."""
    from fastapi.responses import Response
    try:
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        img_bytes = vc.capture_region(x, y, w, h)
        if img_bytes:
            return Response(content=img_bytes, media_type="image/jpeg")
        return {"error": "Region capture failed"}
    except Exception as e:
        return {"error": str(e)[:200]}




@app.post("/api/v2/sora/click")
async def sora_click(request: Request):
    """화면 좌표 클릭."""
    try:
        body = await request.json()
        x, y = int(body.get("x", 0)), int(body.get("y", 0))
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        result = vc.click(x, y)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/type")
async def sora_type(request: Request):
    """텍스트 입력."""
    try:
        body = await request.json()
        text = body.get("text", "")
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        result = vc.type_text(text)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/app/launch")
async def sora_app_launch(request: Request):
    """앱 실행."""
    try:
        body = await request.json()
        cmd = body.get("command", "")
        from src.core.agents.local_controller import LocalController
        lc = LocalController()
        result = lc.launch_app(cmd)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/app/control")
async def sora_app_control(request: Request):
    """GUI 컨트롤 클릭."""
    try:
        body = await request.json()
        window = body.get("window", "")
        control = body.get("control", "")
        control_type = body.get("control_type", "Button")
        from src.core.agents.local_controller import LocalController
        lc = LocalController()
        result = lc.find_and_click(window, control, control_type)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/files/{file_path:path}")
async def sora_file_serve(file_path: str):
    """로컬 파일 서빙 (이미지/텍스트)."""
    from fastapi.responses import FileResponse, JSONResponse
    import mimetypes

    target = Path(file_path)
    # 상대 경로면 프로젝트 루트 기준
    if not target.is_absolute():
        target = Path(__file__).resolve().parent.parent.parent / file_path

    if not target.exists():
        return JSONResponse({"error": f"Not found: {file_path}"}, status_code=404)

    # 텍스트 파일은 JSON으로
    mime, _ = mimetypes.guess_type(str(target))
    if mime and mime.startswith("text"):
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            return {"filename": target.name, "content": content[:10000]}
        except Exception as e:
            return {"error": str(e)[:200]}

    # 바이너리 파일은 직접 반환
    return FileResponse(str(target), media_type=mime or "application/octet-stream")


# ── 예약 실행 API ──────────────────────────

@app.get("/api/v2/sora/schedules")
async def sora_schedules_list():
    """예약 목록 조회."""
    try:
        from src.core.agents.scheduled_engine import ScheduledTaskEngine
        engine = ScheduledTaskEngine()
        return {"schedules": engine.list_schedules(active_only=False)}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/schedules")
async def sora_schedules_create(request: Request):
    """예약 추가."""
    try:
        body = await request.json()
        from src.core.agents.scheduled_engine import ScheduledTaskEngine
        engine = ScheduledTaskEngine()
        entry = engine.add(
            task_proposal=body.get("proposal", ""),
            schedule_type=body.get("type", "once"),
            schedule_value=body.get("value", ""),
            priority=body.get("priority", "medium"),
        )
        return {"success": True, "schedule": entry}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.delete("/api/v2/sora/schedules/{schedule_id}")
async def sora_schedules_delete(schedule_id: str):
    """예약 삭제."""
    try:
        from src.core.agents.scheduled_engine import ScheduledTaskEngine
        engine = ScheduledTaskEngine()
        removed = engine.remove(schedule_id)
        return {"success": removed}
    except Exception as e:
        return {"error": str(e)[:200]}


# ── 교훈 API ──────────────────────────────

@app.get("/api/v2/sora/lessons")
async def sora_lessons_list(limit: int = Query(default=20)):
    """축적된 교훈 목록."""
    try:
        from src.core.agents.lesson_extractor import LessonExtractor
        le = LessonExtractor()
        return {"lessons": le.get_lessons(limit=limit)}
    except Exception as e:
        return {"error": str(e)[:200]}


# ── 브라우저 자동화 API ──────────────────────

@app.post("/api/v2/sora/browser/navigate")
async def sora_browser_navigate(request: Request):
    """URL로 브라우저 이동."""
    try:
        body = await request.json()
        url = body.get("url", "")
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        result = bc.navigate(url)
        return result
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/browser/click")
async def sora_browser_click(request: Request):
    """CSS 셀렉터로 요소 클릭."""
    try:
        body = await request.json()
        selector = body.get("selector", "")
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        result = bc.click(selector)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/browser/type")
async def sora_browser_type(request: Request):
    """입력 필드에 텍스트 입력."""
    try:
        body = await request.json()
        selector = body.get("selector", "")
        text = body.get("text", "")
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        result = bc.type_text(selector, text)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/browser/screenshot")
async def sora_browser_screenshot():
    """현재 페이지 스크린샷."""
    try:
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        img = bc.screenshot()
        if img:
            return Response(content=img, media_type="image/jpeg")
        return {"error": "Screenshot failed"}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/browser/text")
async def sora_browser_text():
    """현재 페이지 텍스트 추출."""
    try:
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        text = bc.extract_text()
        return {"text": text}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/browser/eval")
async def sora_browser_eval(request: Request):
    """JavaScript 실행."""
    try:
        body = await request.json()
        js = body.get("code", "")
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        result = bc.evaluate(js)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/browser/info")
async def sora_browser_info():
    """현재 브라우저 상태."""
    try:
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        if bc.is_running:
            return bc.get_page_info()
        return {"status": "not_running"}
    except Exception as e:
        return {"error": str(e)[:200]}


# ── 파일 탐색 API ──────────────────────────

@app.get("/api/v2/sora/files/list")
async def sora_files_list(path: str = Query(default=".")):
    """디렉토리 내용 목록."""
    try:
        import os
        target = Path(path).resolve()
        # 보안: 프로젝트 루트 내부만 허용
        if not str(target).startswith(str(PROJECT_ROOT)):
            return {"error": "Access denied: path outside project"}
        if not target.exists():
            return {"error": "Path not found"}
        if target.is_file():
            return {"type": "file", "name": target.name, "size": target.stat().st_size}

        items = []
        for entry in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": stat.st_size if entry.is_file() else None,
                    "modified": int(stat.st_mtime),
                })
            except (PermissionError, OSError):
                continue
        return {"path": str(target), "items": items[:200]}  # 최대 200개
    except Exception as e:
        return {"error": str(e)[:200]}


_task_dispatcher = None

@app.on_event("startup")
async def startup_sora_system():
    """Sora OS 핵심 모듈 가동 (Phase 4 & 8 + Phase B)"""
    global _task_dispatcher
    logger.info("🚀 Sora System Booting...")
    
    try:
        # 1. SoraEngine 초기화 (Agent 도구 포함)
        engine = _get_sora_engine()
        if engine:
            logger.info("🧠 SoraEngine 초기화 완료 — Agent 도구 포함")
        else:
            logger.warning("⚠️ SoraEngine 초기화 실패")

        # 2. Task Dispatcher (SoraEngine 경유)
        from src.core.hive_mind.task_dispatcher import TaskDispatcher
        logger.info("🤖 Starting TaskDispatcher...")
        _task_dispatcher = TaskDispatcher()
        _task_dispatcher.start()

        # 3. Phase B: 자율 루프 + NeoScheduler 자동 시작
        if engine and hasattr(engine, 'start_autonomous'):
            started = await engine.start_autonomous()
            if started:
                logger.info("🔱 자율 루프 + NeoScheduler 백그라운드 시작")
            else:
                logger.warning("⚠️ 자율 루프 시작 실패")
        
        logger.info("✅ Sora System Ready: [Engine: ON] [Auto-Pilot: ON] [Scheduler: ON]")

    except Exception as e:
        logger.error(f"❌ System Startup Failed: {e}", exc_info=True)


@app.on_event("shutdown")
async def shutdown_sora_system():
    """시스템 종료 처리"""
    global _task_dispatcher
    logger.info("💤 Sora System Shutting Down...")
    
    if _task_dispatcher:
        _task_dispatcher.stop()

    # 자율 루프 종료
    try:
        engine = _get_sora_engine()
        if engine and hasattr(engine, 'autonomous_loop'):
            loop = engine.autonomous_loop
            if loop:
                await loop.stop()
                logger.info("🔱 자율 루프 정상 종료")
    except Exception:
        pass

    # NeoScheduler 종료
    try:
        from src.core.neo_scheduler import get_scheduler
        sched = get_scheduler()
        if sched and sched.scheduler.running:
            sched.scheduler.shutdown(wait=False)
            logger.info("📅 NeoScheduler 정상 종료")
    except Exception:
        pass
    
    # 브라우저 종료
    try:
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        if bc.is_running:
            bc.close()
    except Exception:
        pass


# ══════════════════════════════════════════════════
# Phase C/D: 관제 대시보드 API
# ══════════════════════════════════════════════════

@app.get("/api/v2/autonomous")
async def api_autonomous_status():
    """자율 루프 + EventBus + 스케줄러 통합 상태."""
    result = {
        "autonomous_loop": None,
        "event_bus": None,
        "scheduler": None,
    }

    # 1. 자율 루프
    try:
        engine = _get_sora_engine()
        if engine and hasattr(engine, 'autonomous_loop'):
            loop = engine.autonomous_loop
            if loop:
                result["autonomous_loop"] = loop.get_stats()
    except Exception as e:
        result["autonomous_loop"] = {"error": str(e)[:100]}

    # 2. EventBus
    try:
        engine = _get_sora_engine()
        if engine and hasattr(engine, 'autonomous_loop'):
            loop = engine.autonomous_loop
            if loop and hasattr(loop, 'event_bus'):
                result["event_bus"] = loop.event_bus.get_stats()
    except Exception as e:
        result["event_bus"] = {"error": str(e)[:100]}

    # 3. 스케줄러
    try:
        from src.core.neo_scheduler import get_scheduler
        sched = get_scheduler()
        if sched:
            result["scheduler"] = sched.status()
        else:
            result["scheduler"] = {"running": False, "message": "미시작"}
    except Exception as e:
        result["scheduler"] = {"error": str(e)[:100]}

    return result


@app.get("/api/v2/autonomous/events")
async def api_autonomous_events():
    """EventBus 최근 이벤트 통계."""
    try:
        engine = _get_sora_engine()
        if engine and hasattr(engine, 'autonomous_loop'):
            loop = engine.autonomous_loop
            if loop and hasattr(loop, 'event_bus'):
                stats = loop.event_bus.get_stats()
                return {
                    "total_events": stats.get("total_events", 0),
                    "events_by_type": dict(stats.get("events_by_type", {})),
                    "queue_size": stats.get("queue_size", 0),
                    "handlers": stats.get("handlers", {}),
                    "running": stats.get("running", False),
                }
        return {"error": "자율 루프 미시작"}
    except Exception as e:
        return {"error": str(e)[:100]}


@app.get("/api/v2/control-panel")
async def api_control_panel():
    """통합 관제 패널 — 전체 시스템 상태 한 눈에."""
    import psutil
    result = {
        "system": {
            "cpu_pct": psutil.cpu_percent(interval=0),
            "ram_pct": psutil.virtual_memory().percent,
            "ram_used_gb": round(psutil.virtual_memory().used / (1024**3), 1),
        },
        "engine": None,
        "autonomous": None,
        "scheduler": None,
        "sbu_summary": [],
    }

    # Engine
    try:
        engine = _get_sora_engine()
        if engine:
            result["engine"] = {
                "tools": len(getattr(engine, '_tools', [])),
                "model": getattr(engine, 'model_name', 'unknown'),
            }
    except Exception:
        pass

    # Autonomous
    try:
        engine = _get_sora_engine()
        if engine and hasattr(engine, 'autonomous_loop'):
            loop = engine.autonomous_loop
            if loop:
                stats = loop.get_stats()
                result["autonomous"] = {
                    "running": bool(stats.get("started_at")),
                    "total_processed": stats.get("total_processed", 0),
                    "approved": stats.get("approved", 0),
                    "blocked": stats.get("blocked", 0),
                    "healed": stats.get("healed", 0),
                    "anomalies": stats.get("anomalies_detected", 0),
                }
    except Exception:
        pass

    # Scheduler SBU Summary
    try:
        from src.core.neo_scheduler import get_scheduler
        sched = get_scheduler()
        if sched:
            result["scheduler"] = {
                "running": sched.scheduler.running if hasattr(sched.scheduler, 'running') else False,
                "total_runs": sched._total_runs,
                "total_skips": sched._total_skips,
            }
            for sbu_id, job in sched._jobs.items():
                result["sbu_summary"].append({
                    "sbu": sbu_id,
                    "name": job.name,
                    "runs": job.run_count,
                    "fails": job.fail_count,
                    "last_run": job.last_run.isoformat() if job.last_run else None,
                    "status": "OK" if job.consecutive_fails == 0 else f"FAIL x{job.consecutive_fails}",
                })
    except Exception:
        pass

    return result


@app.get("/api/v2/evolution")
async def api_evolution_status():
    """Phase E: 자기 진화 시스템 상태 — GodelAgent + A2A."""
    result = {
        "godel_agent": None,
        "a2a_agents": [],
        "evolution_events": [],
    }

    # 1. GodelAgent 상태
    try:
        from src.core.godel_agent import GodelAgent
        agent = GodelAgent()
        result["godel_agent"] = {
            "max_issues_per_cycle": agent.MAX_ISSUES_PER_CYCLE,
            "available": True,
        }
    except Exception as e:
        result["godel_agent"] = {"available": False, "error": str(e)[:100]}

    # 2. A2A Protocol 에이전트 목록
    try:
        from src.core.a2a_protocol import A2AProtocol
        a2a = A2AProtocol()
        agents = a2a.discover()
        result["a2a_agents"] = [
            {
                "id": a.agent_id,
                "name": a.name,
                "skills": a.skills,
                "endpoint": a.endpoint,
            }
            for a in agents
        ]
    except Exception as e:
        result["a2a_agents"] = [{"error": str(e)[:100]}]

    # 3. EventBus에서 evolution_event 통계
    try:
        engine = _get_sora_engine()
        if engine and hasattr(engine, 'autonomous_loop'):
            loop = engine.autonomous_loop
            if loop and hasattr(loop, 'event_bus'):
                stats = loop.event_bus.get_stats()
                by_type = stats.get("events_by_type", {})
                result["evolution_events"] = {
                    "total": by_type.get("evolution_event", 0),
                    "schedule_events": by_type.get("schedule_event", 0),
                    "anomaly_events": by_type.get("anomaly_event", 0),
                }
    except Exception:
        pass

    return result


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    start_dashboard()



# ══════════════════════════════════════════════════
# Board/Sora Log API → dashboard/routes/api_board.py 로 이관 완료
# ══════════════════════════════════════════════════


async def root_redirect():
    """루트(/) 접속 시 /app으로 리다이렉트"""
    return RedirectResponse(url="/app")


def start_dashboard(port: int = 7700):
    """대시보드 서버 시작"""
    import uvicorn
    logger.info(f"[Dashboard] http://localhost:{port} 에서 시작")
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")


# ══════════════════════════════════════════════════
# Sora God Mode API
# ══════════════════════════════════════════════════

@app.get("/api/v2/sora/goals")
async def sora_goals_list():
    """Sora 활성 목표 목록."""
    try:
        from src.core.agents.goal_manager import GoalManager
        gm = GoalManager()
        goals = gm.list_goals()
        due = gm.get_due_goals()
        return {
            "goals": goals,
            "due_count": len(due),
            "total": len(goals),
        }
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/goals")
async def sora_goals_add(request: Request):
    """새 목표 추가."""
    try:
        from src.core.agents.goal_manager import GoalManager
        body = await request.json()
        gm = GoalManager()
        goal = gm.add_goal(
            goal_type=body.get("type", "directive"),
            description=body.get("description", ""),
            **{k: v for k, v in body.items() if k not in ("type", "description")},
        )
        return {"success": True, "goal": goal}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.put("/api/v2/sora/goals/{goal_id}")
async def sora_goals_update(goal_id: str, request: Request):
    """목표 수정."""
    try:
        from src.core.agents.goal_manager import GoalManager
        body = await request.json()
        gm = GoalManager()
        updated = gm.update_goal(goal_id, **body)
        if updated:
            return {"success": True, "goal": updated}
        return {"error": f"Goal not found: {goal_id}"}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.delete("/api/v2/sora/goals/{goal_id}")
async def sora_goals_delete(goal_id: str):
    """목표 삭제."""
    try:
        from src.core.agents.goal_manager import GoalManager
        gm = GoalManager()
        removed = gm.remove_goal(goal_id)
        return {"success": removed}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/system")
async def sora_system_status():
    """Sora 시스템 상태 (PC 모니터링 + 목표 + 모델 라우터)."""
    try:
        from src.core.agents.system_monitor import SystemMonitor
        from src.core.agents.goal_manager import GoalManager
        from src.core.utils.llm_client import ModelRouter

        sm = SystemMonitor()
        gm = GoalManager()
        router = ModelRouter()

        return {
            "system": sm.collect(),
            "goals": {
                "active": len(gm.list_goals(status="active")),
                "due": len(gm.get_due_goals()),
            },
            "models": {tier: info[1] for tier, info in router.MODELS.items()},
            "god_mode": True,
        }
    except Exception as e:
        return {"error": str(e)[:200]}


# ── Sora PC 제어 API ───────────────────────

@app.get("/api/v2/sora/screen")
async def sora_screen_capture():
    """현재 화면을 캡처하여 JPEG로 반환."""
    from fastapi.responses import Response
    try:
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        img_bytes = vc.capture_bytes(quality=75)
        if img_bytes:
            return Response(content=img_bytes, media_type="image/jpeg")
        return {"error": "Capture failed"}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/screen/live")
async def sora_screen_live():
    """CCTV 모드 live_view.jpg 반환 (실시간 스트리밍용)."""
    from fastapi.responses import FileResponse
    live_path = Path(__file__).resolve().parent.parent.parent / "data" / "live_view.jpg"
    if live_path.exists():
        return FileResponse(str(live_path), media_type="image/jpeg",
                           headers={"Cache-Control": "no-cache, no-store"})
    # live_view가 없으면 즉시 캡처
    from fastapi.responses import Response
    try:
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        img_bytes = vc.capture_bytes(quality=50)
        if img_bytes:
            return Response(content=img_bytes, media_type="image/jpeg")
    except Exception:
        pass
    return {"error": "No live view available"}


@app.post("/api/v2/sora/chat")
async def sora_chat(request: Request):
    """Sora에게 자연어 명령 → 실행 결과 반환 (세션 기반 히스토리)."""
    try:
        body = await request.json()
        message = body.get("message", "")
        session_id = body.get("session_id", f"default-{int(time.time())}")
        if not message:
            return {"error": "message is required"}

        # 세션 히스토리 관리
        if session_id not in _chat_sessions:
            _chat_sessions[session_id] = {
                "history": [],
                "created_at": time.time(),
            }
        session = _chat_sessions[session_id]
        session["history"].append({"role": "user", "content": message})

        # 히스토리가 20턴 초과 시 앞 15턴 요약 압축
        if len(session["history"]) > 40:  # 20턴 = 40 메시지 (user+assistant)
            old = session["history"][:30]
            summary_text = " / ".join([m["content"][:50] for m in old])
            session["history"] = [
                {"role": "system", "content": f"[이전 대화 요약] {summary_text[:500]}"},
                *session["history"][30:],
            ]

        # SoraEngine 경유 — Agent 도구 포함 (Phase A 통합)
        engine = _get_sora_engine()
        if engine:
            context_lines = []
            for m in session["history"][-10:]:
                role = "사용자" if m["role"] == "user" else "Sora"
                context_lines.append(f"{role}: {m['content'][:200]}")
            history_context = "\n".join(context_lines)
            full_message = f"[대화 히스토리]\n{history_context}\n\n[현재 요청]\n{message}"
            response_text = await engine.process(full_message)
        else:
            response_text = await _fallback_gemini(f"{_SORA_SYSTEM}\n\n사용자: {message}")

        session["history"].append({"role": "assistant", "content": response_text})

        try:
            from src.core.dashboard.ws.ws_manager import ws_broadcast
            await ws_broadcast({"type": "chat_response", "session_id": session_id,
                                "message": response_text[:200]})
        except Exception:
            pass

        return {
            "response": response_text,
            "status": "completed",
            "session_id": session_id,
            "history_length": len(session["history"]),
        }
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/chat/history")
async def sora_chat_history(session_id: str = Query(default="default")):
    """채팅 세션 히스토리 조회."""
    if session_id not in _chat_sessions:
        return {"history": [], "session_id": session_id}
    session = _chat_sessions[session_id]
    return {
        "history": session["history"][-50:],
        "session_id": session_id,
        "total": len(session["history"]),
    }


@app.delete("/api/v2/sora/chat/history")
async def sora_chat_clear(session_id: str = Query(default="default")):
    """채팅 세션 히스토리 초기화."""
    if session_id in _chat_sessions:
        del _chat_sessions[session_id]
    return {"success": True}


# ── Sora 인증 API ──────────────────────────

@app.post("/api/v2/sora/auth/login")
async def sora_auth_login(request: Request):
    """대시보드 로그인 — 시크릿 검증 후 토큰 반환."""
    try:
        body = await request.json()
        password = body.get("password", "")
        from src.core.auth_middleware import verify_token, DASHBOARD_SECRET
        if verify_token(password):
            return {"success": True, "token": DASHBOARD_SECRET}
        return JSONResponse(status_code=401, content={"error": "Invalid password"})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)[:200]})


# ── WebSocket 실시간 알림 ──────────────────

@app.websocket("/ws/sora")
async def sora_websocket(websocket: WebSocket):
    """Sora 실시간 알림 채널 (토큰 인증)."""
    # WebSocket 토큰 검증
    try:
        from src.core.auth_middleware import verify_token
        token = websocket.query_params.get("token", "")
        if not token or not verify_token(token):
            await websocket.close(code=4001, reason="Unauthorized")
            logger.warning(f"🔒 WS auth failed (IP: {websocket.client.host})")
            return
    except ImportError:
        pass  # 미들웨어 없으면 통과 (하위 호환)

    await websocket.accept()
    _ws_clients.add(websocket)
    logger.info(f"🔌 WebSocket connected (total: {len(_ws_clients)})")
    try:
        # 연결 즉시 시스템 상태 전송
        try:
            from src.core.agents.system_monitor import SystemMonitor
            sm = SystemMonitor()
            await websocket.send_json({"type": "system_status", "data": sm.collect()})
        except Exception:
            pass

        while True:
            # 클라이언트 ping 대기 (연결 유지)
            data = await websocket.receive_text()
            if data == "ping":
                await websocket.send_json({"type": "pong", "ts": int(time.time())})
    except WebSocketDisconnect:
        pass
    except Exception:
        pass
    finally:
        _ws_clients.discard(websocket)
        logger.info(f"🔌 WebSocket disconnected (total: {len(_ws_clients)})")


# ── 클립보드 API ──────────────────────────

@app.get("/api/v2/sora/clipboard")
async def sora_clipboard_read():
    """클립보드 내용 읽기."""
    try:
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        content = vc.clipboard_read()
        return {"content": content}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/clipboard")
async def sora_clipboard_write(request: Request):
    """클립보드에 텍스트 쓰기."""
    try:
        body = await request.json()
        text = body.get("text", "")
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        result = vc.clipboard_write(text)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


# ── 영역 캡처 API ──────────────────────────

@app.get("/api/v2/sora/screen/region")
async def sora_screen_region(
    x: int = Query(default=0), y: int = Query(default=0),
    w: int = Query(default=800), h: int = Query(default=600),
):
    """화면 특정 영역만 캡처."""
    from fastapi.responses import Response
    try:
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        img_bytes = vc.capture_region(x, y, w, h)
        if img_bytes:
            return Response(content=img_bytes, media_type="image/jpeg")
        return {"error": "Region capture failed"}
    except Exception as e:
        return {"error": str(e)[:200]}




@app.post("/api/v2/sora/click")
async def sora_click(request: Request):
    """화면 좌표 클릭."""
    try:
        body = await request.json()
        x, y = int(body.get("x", 0)), int(body.get("y", 0))
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        result = vc.click(x, y)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/type")
async def sora_type(request: Request):
    """텍스트 입력."""
    try:
        body = await request.json()
        text = body.get("text", "")
        from src.core.agents.vision_controller import VisionController
        vc = VisionController()
        result = vc.type_text(text)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/app/launch")
async def sora_app_launch(request: Request):
    """앱 실행."""
    try:
        body = await request.json()
        cmd = body.get("command", "")
        from src.core.agents.local_controller import LocalController
        lc = LocalController()
        result = lc.launch_app(cmd)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/app/control")
async def sora_app_control(request: Request):
    """GUI 컨트롤 클릭."""
    try:
        body = await request.json()
        window = body.get("window", "")
        control = body.get("control", "")
        control_type = body.get("control_type", "Button")
        from src.core.agents.local_controller import LocalController
        lc = LocalController()
        result = lc.find_and_click(window, control, control_type)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/files/{file_path:path}")
async def sora_file_serve(file_path: str):
    """로컬 파일 서빙 (이미지/텍스트)."""
    from fastapi.responses import FileResponse, JSONResponse
    import mimetypes

    target = Path(file_path)
    # 상대 경로면 프로젝트 루트 기준
    if not target.is_absolute():
        target = Path(__file__).resolve().parent.parent.parent / file_path

    if not target.exists():
        return JSONResponse({"error": f"Not found: {file_path}"}, status_code=404)

    # 텍스트 파일은 JSON으로
    mime, _ = mimetypes.guess_type(str(target))
    if mime and mime.startswith("text"):
        try:
            content = target.read_text(encoding="utf-8", errors="replace")
            return {"filename": target.name, "content": content[:10000]}
        except Exception as e:
            return {"error": str(e)[:200]}

    # 바이너리 파일은 직접 반환
    return FileResponse(str(target), media_type=mime or "application/octet-stream")


# ── 예약 실행 API ──────────────────────────

@app.get("/api/v2/sora/schedules")
async def sora_schedules_list():
    """예약 목록 조회."""
    try:
        from src.core.agents.scheduled_engine import ScheduledTaskEngine
        engine = ScheduledTaskEngine()
        return {"schedules": engine.list_schedules(active_only=False)}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/schedules")
async def sora_schedules_create(request: Request):
    """예약 추가."""
    try:
        body = await request.json()
        from src.core.agents.scheduled_engine import ScheduledTaskEngine
        engine = ScheduledTaskEngine()
        entry = engine.add(
            task_proposal=body.get("proposal", ""),
            schedule_type=body.get("type", "once"),
            schedule_value=body.get("value", ""),
            priority=body.get("priority", "medium"),
        )
        return {"success": True, "schedule": entry}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.delete("/api/v2/sora/schedules/{schedule_id}")
async def sora_schedules_delete(schedule_id: str):
    """예약 삭제."""
    try:
        from src.core.agents.scheduled_engine import ScheduledTaskEngine
        engine = ScheduledTaskEngine()
        removed = engine.remove(schedule_id)
        return {"success": removed}
    except Exception as e:
        return {"error": str(e)[:200]}


# ── 교훈 API ──────────────────────────────

@app.get("/api/v2/sora/lessons")
async def sora_lessons_list(limit: int = Query(default=20)):
    """축적된 교훈 목록."""
    try:
        from src.core.agents.lesson_extractor import LessonExtractor
        le = LessonExtractor()
        return {"lessons": le.get_lessons(limit=limit)}
    except Exception as e:
        return {"error": str(e)[:200]}


# ── 브라우저 자동화 API ──────────────────────

@app.post("/api/v2/sora/browser/navigate")
async def sora_browser_navigate(request: Request):
    """URL로 브라우저 이동."""
    try:
        body = await request.json()
        url = body.get("url", "")
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        result = bc.navigate(url)
        return result
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/browser/click")
async def sora_browser_click(request: Request):
    """CSS 셀렉터로 요소 클릭."""
    try:
        body = await request.json()
        selector = body.get("selector", "")
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        result = bc.click(selector)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/browser/type")
async def sora_browser_type(request: Request):
    """입력 필드에 텍스트 입력."""
    try:
        body = await request.json()
        selector = body.get("selector", "")
        text = body.get("text", "")
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        result = bc.type_text(selector, text)
        return {"success": True, "result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/browser/screenshot")
async def sora_browser_screenshot():
    """현재 페이지 스크린샷."""
    try:
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        img = bc.screenshot()
        if img:
            return Response(content=img, media_type="image/jpeg")
        return {"error": "Screenshot failed"}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/browser/text")
async def sora_browser_text():
    """현재 페이지 텍스트 추출."""
    try:
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        text = bc.extract_text()
        return {"text": text}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.post("/api/v2/sora/browser/eval")
async def sora_browser_eval(request: Request):
    """JavaScript 실행."""
    try:
        body = await request.json()
        js = body.get("code", "")
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        result = bc.evaluate(js)
        return {"result": result}
    except Exception as e:
        return {"error": str(e)[:200]}


@app.get("/api/v2/sora/browser/info")
async def sora_browser_info():
    """현재 브라우저 상태."""
    try:
        from src.core.agents.browser_controller import BrowserController
        bc = BrowserController()
        if bc.is_running:
            return bc.get_page_info()
        return {"status": "not_running"}
    except Exception as e:
        return {"error": str(e)[:200]}


# ── 파일 탐색 API ──────────────────────────

@app.get("/api/v2/sora/files/list")
async def sora_files_list(path: str = Query(default=".")):
    """디렉토리 내용 목록."""
    try:
        import os
        target = Path(path).resolve()
        # 보안: 프로젝트 루트 내부만 허용
        if not str(target).startswith(str(PROJECT_ROOT)):
            return {"error": "Access denied: path outside project"}
        if not target.exists():
            return {"error": "Path not found"}
        if target.is_file():
            return {"type": "file", "name": target.name, "size": target.stat().st_size}

        items = []
        for entry in sorted(target.iterdir(), key=lambda x: (not x.is_dir(), x.name.lower())):
            try:
                stat = entry.stat()
                items.append({
                    "name": entry.name,
                    "type": "dir" if entry.is_dir() else "file",
                    "size": stat.st_size if entry.is_file() else None,
                    "modified": int(stat.st_mtime),
                })
            except (PermissionError, OSError):
                continue
        return {"path": str(target), "items": items[:200]}  # 최대 200개
    except Exception as e:
        return {"error": str(e)[:200]}




if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(message)s")
    start_dashboard()


