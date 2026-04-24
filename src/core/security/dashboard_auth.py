# -*- coding: utf-8 -*-
"""Dashboard authentication helpers shared across Sora control surfaces."""
from __future__ import annotations

import base64
import hashlib
import hmac
import ipaddress
import json
import logging
import os
import secrets
import time
from typing import Any

from fastapi import Request

logger = logging.getLogger("neo.dashboard.auth")

_TRUTHY = {"1", "true", "yes", "on"}
ALLOWED_EMAIL = os.getenv("ALLOWED_EMAIL", "dpthf1537@gmail.com").strip()
ALLOW_LEGACY_DASHBOARD_TOKEN = os.getenv("NEO_ALLOW_LEGACY_DASHBOARD_TOKEN", "").strip().lower() in _TRUTHY
ALLOW_PRIVATE_BYPASS = os.getenv("NEO_ALLOW_PRIVATE_BYPASS", "").strip().lower() in _TRUTHY


def _read_env_secret(name: str) -> str:
    return os.getenv(name, "").strip()


def get_dashboard_secret() -> str:
    secret = _read_env_secret("SORA_DASHBOARD_SECRET")
    if secret:
        return secret

    legacy = _read_env_secret("DASHBOARD_TOKEN")
    if legacy and ALLOW_LEGACY_DASHBOARD_TOKEN:
        logger.warning("[Auth] 레거시 DASHBOARD_TOKEN 폴백이 활성화되어 있습니다.")
        return legacy

    return ""


def get_pc_agent_token() -> str:
    return _read_env_secret("PC_AGENT_TOKEN") or get_dashboard_secret()


def _b64url_encode(raw: bytes) -> str:
    return base64.urlsafe_b64encode(raw).rstrip(b"=").decode("ascii")


def _b64url_decode(raw: str) -> bytes:
    padding = "=" * (-len(raw) % 4)
    return base64.urlsafe_b64decode((raw + padding).encode("ascii"))


def is_private_client(host: str) -> bool:
    host = (host or "").strip()
    if host in {"127.0.0.1", "::1", "localhost"}:
        return True
    try:
        ip = ipaddress.ip_address(host)
    except ValueError:
        return False
    return ip.is_private or ip.is_loopback


def private_bypass_allowed(host: str) -> bool:
    return ALLOW_PRIVATE_BYPASS and is_private_client(host)


def _session_user(request: Request) -> dict[str, Any] | None:
    try:
        user = request.session.get("user")
    except Exception:
        return None
    if not isinstance(user, dict):
        return None
    email = str(user.get("email", "")).strip()
    if ALLOWED_EMAIL and email and email != ALLOWED_EMAIL:
        return None
    return user


def set_dashboard_session(
    request: Request,
    *,
    email: str,
    name: str,
    picture: str = "",
    auth_type: str = "session",
) -> dict[str, Any]:
    user = {
        "email": email,
        "name": name,
        "picture": picture,
        "auth_type": auth_type,
        "logged_in_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    request.session["user"] = user
    return user


def clear_dashboard_session(request: Request) -> None:
    try:
        request.session.clear()
    except Exception:
        pass


def extract_bearer_token(request: Request) -> str:
    auth_header = request.headers.get("authorization", "")
    if auth_header.startswith("Bearer "):
        return auth_header[7:].strip()
    return ""


def verify_service_secret(token: str) -> bool:
    secret = get_dashboard_secret()
    return bool(secret and token and secrets.compare_digest(token, secret))


def verify_manual_login_secret(secret: str) -> bool:
    if verify_service_secret(secret):
        return True

    legacy = _read_env_secret("DASHBOARD_TOKEN")
    if legacy and ALLOW_LEGACY_DASHBOARD_TOKEN:
        return secrets.compare_digest(secret, legacy)

    return False


def issue_action_token(
    *,
    subject: str,
    scopes: str | list[str],
    ttl_seconds: int = 300,
    actor: dict[str, Any] | None = None,
) -> str:
    secret = get_dashboard_secret()
    if not secret:
        raise RuntimeError("SORA_DASHBOARD_SECRET not configured")

    scope_list = [scopes] if isinstance(scopes, str) else list(scopes)
    now = int(time.time())
    payload = {
        "sub": subject,
        "scp": scope_list,
        "iat": now,
        "exp": now + ttl_seconds,
        "nonce": secrets.token_urlsafe(8),
        "actor": actor or {},
    }
    payload_bytes = json.dumps(payload, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
    signature = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    return f"{_b64url_encode(payload_bytes)}.{_b64url_encode(signature)}"


def _scope_allows(token_scopes: list[str], required_scope: str | None) -> bool:
    if not required_scope:
        return True

    available = set(token_scopes)
    if "*" in available:
        return True

    if required_scope == "dashboard:read":
        acceptable = {"dashboard:read", "dashboard:execute", "dashboard:*"}
    elif required_scope == "dashboard:execute":
        acceptable = {"dashboard:execute", "dashboard:*"}
    elif required_scope == "ws:sora":
        acceptable = {"ws:sora", "dashboard:execute", "dashboard:*"}
    else:
        prefix = required_scope.split(":", 1)[0]
        acceptable = {required_scope, f"{prefix}:*"}

    return bool(available & acceptable)


def verify_action_token(token: str, required_scope: str | None = None) -> dict[str, Any] | None:
    secret = get_dashboard_secret()
    if not secret or not token:
        return None

    try:
        payload_b64, sig_b64 = token.split(".", 1)
        payload_bytes = _b64url_decode(payload_b64)
        provided_sig = _b64url_decode(sig_b64)
    except Exception:
        return None

    expected_sig = hmac.new(secret.encode("utf-8"), payload_bytes, hashlib.sha256).digest()
    if not hmac.compare_digest(provided_sig, expected_sig):
        return None

    try:
        payload = json.loads(payload_bytes.decode("utf-8"))
    except Exception:
        return None

    now = int(time.time())
    if int(payload.get("exp", 0)) <= now:
        return None

    scopes = payload.get("scp", [])
    if not isinstance(scopes, list) or not _scope_allows(scopes, required_scope):
        return None

    return payload


def authenticate_request(request: Request, required_scope: str | None = None) -> dict[str, Any]:
    user = _session_user(request)
    if user:
        return {
            "authenticated": True,
            "auth_type": user.get("auth_type", "session"),
            "user": user,
            "scopes": ["dashboard:*"],
        }

    token = extract_bearer_token(request)
    if token:
        if verify_service_secret(token):
            return {
                "authenticated": True,
                "auth_type": "internal_secret",
                "user": {"name": "Sora Internal", "email": "service@local"},
                "scopes": ["dashboard:*"],
            }

        payload = verify_action_token(token, required_scope=required_scope)
        if payload:
            actor = payload.get("actor", {}) if isinstance(payload.get("actor"), dict) else {}
            return {
                "authenticated": True,
                "auth_type": "action_token",
                "user": actor or {"name": payload.get("sub", "action-token"), "email": actor.get("email", "")},
                "scopes": payload.get("scp", []),
                "token_payload": payload,
            }

    client_ip = request.client.host if request.client else ""
    if private_bypass_allowed(client_ip):
        return {
            "authenticated": True,
            "auth_type": "private_bypass",
            "user": {"name": "Private Network", "email": "private@local"},
            "scopes": ["dashboard:*"],
        }

    return {"authenticated": False, "auth_type": "none", "user": {}, "scopes": []}


def authenticate_websocket_token(token: str, required_scope: str | None = None) -> dict[str, Any]:
    if token and verify_service_secret(token):
        return {
            "authenticated": True,
            "auth_type": "internal_secret",
            "user": {"name": "Sora Internal", "email": "service@local"},
            "scopes": ["dashboard:*"],
        }

    payload = verify_action_token(token, required_scope=required_scope)
    if payload:
        actor = payload.get("actor", {}) if isinstance(payload.get("actor"), dict) else {}
        return {
            "authenticated": True,
            "auth_type": "action_token",
            "user": actor or {"name": payload.get("sub", "action-token"), "email": actor.get("email", "")},
            "scopes": payload.get("scp", []),
            "token_payload": payload,
        }

    return {"authenticated": False, "auth_type": "none", "user": {}, "scopes": []}
