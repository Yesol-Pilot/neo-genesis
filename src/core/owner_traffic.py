# -*- coding: utf-8 -*-
"""Owner-only traffic dashboard helpers for Sora mobile access."""

from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
OWNER_TRAFFIC_DIR = PROJECT_ROOT / "data" / "owner-analytics"
OWNER_TRAFFIC_HTML = OWNER_TRAFFIC_DIR / "owner-traffic-command.html"
OWNER_TRAFFIC_LATEST = OWNER_TRAFFIC_DIR / "owner-traffic-latest.json"
OWNER_TRAFFIC_ROUTE = "/owner/traffic"

_QUERY_KEYWORDS = (
    "통계",
    "트래픽",
    "방문",
    "방문자",
    "ga4",
    "posthog",
    "analytics",
    "traffic",
    "dashboard",
)
_INTENT_HINTS = (
    "대시보드",
    "링크",
    "열어",
    "보여",
    "줘",
    "상태",
    "모니터",
    "모바일",
    "dashboard",
    "link",
    "open",
    "show",
    "status",
    "monitor",
    "mobile",
)


def owner_traffic_public_base() -> str:
    """Return the mobile-reachable Sora base URL."""
    for key in ("SORA_PUBLIC_BASE_URL", "SORA_DASHBOARD_URL"):
        value = os.getenv(key, "").strip().rstrip("/")
        if value:
            return value
    return "https://dash.neogenesis.app"


def _issue_read_token(ttl_seconds: int) -> str:
    try:
        from src.core.security.dashboard_auth import issue_action_token

        return issue_action_token(
            subject="owner-traffic-mobile",
            scopes=["dashboard:read"],
            ttl_seconds=ttl_seconds,
            actor={
                "email": os.getenv("ALLOWED_EMAIL", "dpthf1537@gmail.com"),
                "name": "Owner Traffic Mobile",
                "auth_type": "owner_traffic_link",
            },
        )
    except Exception:
        return ""


def owner_traffic_url(
    base_url: str | None = None,
    *,
    include_token: bool = False,
    ttl_seconds: int = 12 * 60 * 60,
) -> str:
    base = (base_url or owner_traffic_public_base()).strip().rstrip("/")
    url = f"{base}{OWNER_TRAFFIC_ROUTE}"
    if include_token:
        token = _issue_read_token(ttl_seconds)
        if token:
            url = f"{url}?token={token}"
    return url


def is_owner_traffic_query(text: str) -> bool:
    normalized = (text or "").strip().lower()
    if not normalized:
        return False
    has_keyword = any(keyword in normalized for keyword in _QUERY_KEYWORDS)
    has_intent = any(hint in normalized for hint in _INTENT_HINTS)
    return has_keyword and (has_intent or len(normalized) <= 16)


def load_owner_traffic_snapshot() -> dict[str, Any]:
    if not OWNER_TRAFFIC_LATEST.exists():
        return {}
    try:
        return json.loads(OWNER_TRAFFIC_LATEST.read_text(encoding="utf-8"))
    except Exception:
        return {}


def build_owner_traffic_reply(base_url: str | None = None, *, include_token: bool = True) -> str:
    snapshot = load_owner_traffic_snapshot()
    summary = snapshot.get("summary") if isinstance(snapshot, dict) else {}
    findings = summary.get("findings_by_severity", {}) if isinstance(summary, dict) else {}

    lines = [
        "모바일용 라이브사이트 통계 대시보드입니다.",
        owner_traffic_url(base_url, include_token=include_token),
    ]
    if snapshot:
        lines.extend(
            [
                "",
                f"snapshot: {snapshot.get('snapshot_id', '-')}",
                f"trust: {snapshot.get('data_trust_state', '-')}",
                f"active: {summary.get('active_sites', '-')}",
                f"blocked: {summary.get('blocked_by_measurement', '-')}",
                f"P0/P1/P2: {findings.get('P0', 0)}/{findings.get('P1', 0)}/{findings.get('P2', 0)}",
            ]
        )
    else:
        lines.extend(["", "아직 owner-traffic-latest.json 스냅샷이 없습니다."])
    return "\n".join(lines)
