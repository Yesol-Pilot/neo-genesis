# -*- coding: utf-8 -*-
from pathlib import Path
import sys

import pytest
from fastapi import HTTPException
from starlette.requests import Request

PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from src.core.dashboard.auth import auth_router


def _make_request(*, host: str, scheme: str = "http", forwarded_host: str = "") -> Request:
    headers = [(b"host", host.encode("utf-8"))]
    if forwarded_host:
        headers.append((b"x-forwarded-host", forwarded_host.encode("utf-8")))
    scope = {
        "type": "http",
        "http_version": "1.1",
        "method": "GET",
        "scheme": scheme,
        "path": "/auth/google",
        "raw_path": b"/auth/google",
        "query_string": b"",
        "headers": headers,
        "client": ("127.0.0.1", 50000),
        "server": ("localhost", 7700),
    }
    return Request(scope)


def test_resolve_redirect_uri_blocks_unlisted_host(monkeypatch):
    monkeypatch.setattr(auth_router, "PUBLIC_BASE_URL", "")

    request = _make_request(host="evil.example")

    with pytest.raises(HTTPException) as exc:
        auth_router._resolve_redirect_uri(request)

    assert exc.value.status_code == 500
    assert "SORA_PUBLIC_BASE_URL" in str(exc.value.detail)


def test_resolve_redirect_uri_allows_fixed_local_dev_host(monkeypatch):
    monkeypatch.setattr(auth_router, "PUBLIC_BASE_URL", "")

    request = _make_request(host="localhost:7700")

    assert auth_router._resolve_redirect_uri(request) == "http://localhost:7700/auth/google/callback"


def test_resolve_redirect_uri_ignores_forwarded_public_host_without_public_base(monkeypatch):
    monkeypatch.setattr(auth_router, "PUBLIC_BASE_URL", "")

    request = _make_request(host="localhost:7700", forwarded_host="neo.example.com")

    assert auth_router._resolve_redirect_uri(request) == "http://localhost:7700/auth/google/callback"


def test_resolve_redirect_uri_prefers_explicit_public_base(monkeypatch):
    monkeypatch.setattr(auth_router, "PUBLIC_BASE_URL", "https://neo.example.com")

    request = _make_request(host="evil.example", forwarded_host="also-evil.example")

    assert auth_router._resolve_redirect_uri(request) == "https://neo.example.com/auth/google/callback"


def test_get_allowed_dashboard_origins_includes_public_and_custom(monkeypatch):
    monkeypatch.setattr(auth_router, "PUBLIC_BASE_URL", "https://neo.example.com")
    monkeypatch.setenv("SORA_ALLOWED_ORIGINS", "https://app.example.com,http://localhost:3000")

    origins = auth_router.get_allowed_dashboard_origins()

    assert "https://neo.example.com" in origins
    assert "https://app.example.com" in origins
    assert "http://localhost:3000" in origins
    assert "http://localhost:7700" in origins
