# -*- coding: utf-8 -*-
"""
인증 라우터 — Google OAuth 2.0 + 세션 + 단기 액션 토큰

sora_dashboard.py에서 분리된 인증 전용 모듈입니다.
"""
import logging
import os
import secrets
from datetime import datetime
from urllib.parse import urlparse

from fastapi import APIRouter, HTTPException, Request
from fastapi.responses import RedirectResponse

from src.core.security.dashboard_auth import (
    ALLOWED_EMAIL,
    authenticate_request,
    clear_dashboard_session,
    issue_action_token,
    set_dashboard_session,
    verify_manual_login_secret,
)

logger = logging.getLogger(__name__)

GOOGLE_CLIENT_ID = os.environ.get("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.environ.get("GOOGLE_CLIENT_SECRET", "")

# ── 라우터 ──
router = APIRouter(prefix="/auth", tags=["auth"])

PUBLIC_BASE_URL = os.environ.get("SORA_PUBLIC_BASE_URL", "").strip().rstrip("/")
LOCAL_OAUTH_BASES = {
    "localhost:7700": "http://localhost:7700",
    "127.0.0.1:7700": "http://127.0.0.1:7700",
}


def get_allowed_dashboard_origins() -> list[str]:
    origins: set[str] = {
        "http://localhost:7700",
        "http://127.0.0.1:7700",
    }
    if PUBLIC_BASE_URL:
        parsed = urlparse(PUBLIC_BASE_URL)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(500, "Invalid SORA_PUBLIC_BASE_URL")
        origins.add(PUBLIC_BASE_URL)

    for raw_origin in os.environ.get("SORA_ALLOWED_ORIGINS", "").split(","):
        origin = raw_origin.strip().rstrip("/")
        if not origin:
            continue
        parsed = urlparse(origin)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(500, f"Invalid dashboard origin: {origin}")
        origins.add(origin)
    return sorted(origins)


def _resolve_redirect_uri(request: Request) -> str:
    if PUBLIC_BASE_URL:
        parsed = urlparse(PUBLIC_BASE_URL)
        if not parsed.scheme or not parsed.netloc:
            raise HTTPException(500, "Invalid SORA_PUBLIC_BASE_URL")
        return f"{PUBLIC_BASE_URL}/auth/google/callback"

    # Public OAuth redirect URIs must come from explicit config, not request headers.
    # Without SORA_PUBLIC_BASE_URL we only allow fixed local development origins.
    host = request.headers.get("host", "").strip().lower()
    local_base = LOCAL_OAUTH_BASES.get(host)
    if local_base:
        return f"{local_base}/auth/google/callback"

    raise HTTPException(
        500,
        "SORA_PUBLIC_BASE_URL is required for non-local OAuth redirect handling",
    )


def check_auth(request: Request, required_scope: str = "dashboard:read") -> bool:
    """세션 / 내부 서비스 시크릿 / 단기 액션 토큰 검증."""
    context = authenticate_request(request, required_scope=required_scope)
    request.state.dashboard_auth = context
    return context["authenticated"]


@router.get("/google")
async def auth_google(request: Request):
    """구글 로그인 시작 → 구글 인증 페이지로 리다이렉트"""
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(500, "Google OAuth 미설정 (GOOGLE_CLIENT_ID)")

    redirect_uri = _resolve_redirect_uri(request)
    request.session["redirect_uri"] = redirect_uri
    logger.info(f"[Auth] redirect_uri = {redirect_uri}")

    # CSRF state
    state = secrets.token_hex(16)
    request.session["oauth_state"] = state

    from urllib.parse import quote
    google_auth_url = (
        f"https://accounts.google.com/o/oauth2/v2/auth?"
        f"client_id={GOOGLE_CLIENT_ID}"
        f"&redirect_uri={quote(redirect_uri, safe='')}"
        f"&response_type=code"
        f"&scope=openid%20email%20profile"
        f"&state={state}"
        f"&access_type=offline"
    )
    return RedirectResponse(google_auth_url)


@router.get("/google/callback")
async def auth_google_callback(request: Request):
    """구글 OAuth 콜백 → 이메일 화이트리스트 확인 → 세션 생성"""
    import httpx

    code = request.query_params.get("code")
    state = request.query_params.get("state")

    # CSRF 검증
    if state != request.session.get("oauth_state"):
        raise HTTPException(403, "잘못된 요청 (state mismatch)")

    redirect_uri = request.session.get("redirect_uri", "")

    # 코드 → 토큰 교환
    async with httpx.AsyncClient() as client:
        token_resp = await client.post(
            "https://oauth2.googleapis.com/token",
            data={
                "code": code,
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "redirect_uri": redirect_uri,
                "grant_type": "authorization_code",
            },
        )
        if token_resp.status_code != 200:
            raise HTTPException(401, f"토큰 교환 실패: {token_resp.text[:200]}")

        tokens = token_resp.json()

        # 사용자 정보 조회
        userinfo_resp = await client.get(
            "https://www.googleapis.com/oauth2/v2/userinfo",
            headers={"Authorization": f"Bearer {tokens['access_token']}"},
        )
        if userinfo_resp.status_code != 200:
            raise HTTPException(401, "사용자 정보 조회 실패")

        user_info = userinfo_resp.json()

    email = user_info.get("email", "")
    logger.info(f"[Auth] Google 로그인 시도: {email}")

    # 이메일 화이트리스트 확인
    if email != ALLOWED_EMAIL:
        logger.warning(f"[Auth] 차단된 로그인: {email}")
        raise HTTPException(403, f"접근 권한이 없습니다: {email}")

    # 세션 생성
    set_dashboard_session(
        request,
        email=email,
        name=user_info.get("name", ""),
        picture=user_info.get("picture", ""),
        auth_type="oauth",
    )
    request.session.pop("oauth_state", None)
    request.session.pop("redirect_uri", None)

    logger.info(f"[Auth] CEO 로그인 성공: {email}")
    return RedirectResponse("/app")


@router.post("/logout")
async def auth_logout(request: Request):
    """로그아웃"""
    clear_dashboard_session(request)
    return {"ok": True}


@router.get("/logout")
async def auth_logout_redirect(request: Request):
    """브라우저 리다이렉트용 로그아웃."""
    clear_dashboard_session(request)
    return RedirectResponse("/app")


@router.get("/check")
async def auth_check(request: Request):
    """세션 유효성 확인 + 사용자 정보"""
    context = authenticate_request(request, required_scope="dashboard:read")
    user = context.get("user", {}) if context["authenticated"] else {}
    return {
        "authenticated": context["authenticated"],
        "auth_type": context.get("auth_type", "none"),
        "user": user,
    }


@router.post("/login")
async def auth_login(request: Request):
    """수동 시크릿 검증 → 세션 생성."""
    body = await request.json()
    secret = (body.get("password") or body.get("token") or "").strip()

    if not verify_manual_login_secret(secret):
        raise HTTPException(status_code=401, detail="Invalid secret")

    user = set_dashboard_session(
        request,
        email=ALLOWED_EMAIL or "ceo@local",
        name="CEO",
        auth_type="manual_secret",
    )
    return {"ok": True, "user": user}


@router.post("/action-token")
async def auth_action_token(request: Request):
    """세션/서비스 인증 후 짧은 수명의 액션 토큰 발급."""
    context = authenticate_request(request, required_scope="dashboard:read")
    if not context["authenticated"]:
        raise HTTPException(status_code=401, detail="Authentication required")

    body = await request.json() if request.headers.get("content-type", "").startswith("application/json") else {}
    scope = (body.get("scope") or "dashboard:read").strip()
    ttl_seconds = int(body.get("ttl_seconds", 300))
    ttl_seconds = max(30, min(ttl_seconds, 900))
    user = context.get("user", {})
    subject = user.get("email") or user.get("name") or "dashboard-user"

    token = issue_action_token(
        subject=subject,
        scopes=[scope],
        ttl_seconds=ttl_seconds,
        actor={
            "email": user.get("email", ""),
            "name": user.get("name", "CEO"),
            "auth_type": context.get("auth_type", "session"),
        },
    )
    return {
        "ok": True,
        "token": token,
        "scope": scope,
        "expires_in": ttl_seconds,
        "issued_at": datetime.now().isoformat(),
    }
