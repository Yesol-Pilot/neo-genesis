# -*- coding: utf-8 -*-
"""
Operational Telegram alerts for long-running experiments and approval flows.

This module is intentionally standalone so Codex, Claude, Sora, and helper
scripts can all emit the same alert format without depending on the full
Telegram bot runtime.
"""
from __future__ import annotations

import html
import logging
import os
import re
from pathlib import Path
from typing import Any

import requests
from src.core.governance.report_gate import send_reviewed_telegram_report

logger = logging.getLogger("neo.ops.telegram")

BOT_TOKEN = os.getenv("NEO_ALERT_BOT_TOKEN") or os.getenv("TELEGRAM_BOT_TOKEN", "")
CHAT_ID = os.getenv("NEO_ALERT_CHAT_ID") or os.getenv("TELEGRAM_CHAT_ID", "")
MAX_MESSAGE_LEN = 4096


def _clean_text(value: Any, limit: int = 600) -> str:
    text = str(value or "").strip()
    if not text:
        return ""
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"\n{3,}", "\n\n", text)
    if len(text) > limit:
        return text[: limit - 3].rstrip() + "..."
    return text


def _format_duration(seconds: float | None) -> str:
    if seconds is None:
        return ""
    total = max(0, int(round(seconds)))
    hours, remainder = divmod(total, 3600)
    minutes, secs = divmod(remainder, 60)
    parts: list[str] = []
    if hours:
        parts.append(f"{hours}h")
    if minutes:
        parts.append(f"{minutes}m")
    if secs or not parts:
        parts.append(f"{secs}s")
    return " ".join(parts)


def _append_line(lines: list[str], label: str, value: Any, *, code: bool = False, limit: int = 240) -> None:
    text = _clean_text(value, limit=limit)
    if not text:
        return
    safe_label = html.escape(label)
    safe_text = html.escape(text)
    if code:
        lines.append(f"<b>{safe_label}:</b> <code>{safe_text}</code>")
    else:
        lines.append(f"<b>{safe_label}:</b> {safe_text}")


def _append_block(lines: list[str], label: str, value: Any, *, limit: int = 1200) -> None:
    text = _clean_text(value, limit=limit)
    if not text:
        return
    lines.append(f"<b>{html.escape(label)}:</b>")
    lines.append(f"<pre>{html.escape(text)}</pre>")


def _append_metadata(lines: list[str], metadata: dict[str, Any] | None) -> None:
    if not metadata:
        return
    for key, value in metadata.items():
        _append_line(lines, key, value, limit=180)


def _truncate_message(message: str) -> str:
    if len(message) <= MAX_MESSAGE_LEN:
        return message
    return message[: MAX_MESSAGE_LEN - 4].rstrip() + " ..."


def _send_html_message(message: str) -> bool:
    if not BOT_TOKEN or not CHAT_ID:
        logger.warning("[OpsTelegram] Bot token or chat id is missing")
        return False

    try:
        response = requests.post(
            f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
            json={
                "chat_id": CHAT_ID,
                "text": _truncate_message(message),
                "parse_mode": "HTML",
                "disable_web_page_preview": True,
            },
            timeout=10,
        )
        if response.status_code != 200:
            logger.warning("[OpsTelegram] Telegram send failed: %s %s", response.status_code, response.text[:200])
            return False
        return True
    except Exception as exc:
        logger.warning("[OpsTelegram] Telegram send error: %s", exc)
        return False


def notify_long_running_experiment(
    *,
    name: str,
    status: str,
    agent: str = "codex",
    duration_sec: float | None = None,
    summary: str | None = None,
    command: str | None = None,
    log_path: str | os.PathLike[str] | None = None,
    exit_code: int | None = None,
    error: str | None = None,
    output_tail: str | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    normalized_status = (status or "").strip().lower()
    title_map = {
        "started": ("장기 실험 시작", "ℹ️"),
        "completed": ("장기 실험 완료", "✅"),
        "failed": ("장기 실험 실패", "❌"),
        "cancelled": ("장기 실험 취소", "⚠️"),
    }
    title, icon = title_map.get(normalized_status, ("장기 실험 알림", "ℹ️"))

    lines: list[str] = [f"{icon} <b>{html.escape(title)}</b>"]
    _append_line(lines, "agent", agent, code=True)
    _append_line(lines, "experiment", name, limit=160)
    _append_line(lines, "status", normalized_status or status, code=True)
    _append_line(lines, "duration", _format_duration(duration_sec), code=True)
    if exit_code is not None:
        _append_line(lines, "exit_code", exit_code, code=True)
    if command:
        _append_block(lines, "command", command, limit=800)
    if log_path:
        _append_line(lines, "log_path", Path(log_path), code=True, limit=260)
    _append_metadata(lines, metadata)
    _append_block(lines, "summary", summary, limit=1000)
    if error:
        _append_block(lines, "error", error, limit=1000)
    elif output_tail:
        _append_block(lines, "tail", output_tail, limit=1000)

    severity_map = {
        "started": "info",
        "completed": "info",
        "failed": "high",
        "cancelled": "medium",
    }
    return send_reviewed_telegram_report(
        report_type="long_running_experiment",
        title=f"{title}: {name}",
        summary=summary or f"{name} 상태가 {normalized_status or status}로 변경되었습니다.",
        details="\n".join(lines),
        severity=severity_map.get(normalized_status, "info"),
        source=agent,
        metadata=metadata,
        cooldown_sec=60 if normalized_status == "started" else 300,
    )


def notify_agent_approval_requested(
    *,
    agent: str,
    request_id: str,
    action: str,
    summary: str | None = None,
    timeout_sec: float = 30.0,
    metadata: dict[str, Any] | None = None,
) -> bool:
    lines: list[str] = ["⚠️ <b>권한 확인 필요</b>"]
    _append_line(lines, "agent", agent, code=True)
    _append_line(lines, "request_id", request_id, code=True)
    _append_line(lines, "action", action, limit=160)
    _append_line(lines, "timeout", f"{int(timeout_sec)}s", code=True)
    _append_metadata(lines, metadata)
    _append_block(lines, "summary", summary, limit=1000)
    return send_reviewed_telegram_report(
        report_type="approval_requested",
        title=f"권한 확인 필요: {action}",
        summary=summary or f"{agent}가 권한 확인을 요청했습니다.",
        details="\n".join(lines),
        severity="medium",
        source=agent,
        metadata=metadata,
        cooldown_sec=30,
    )


def notify_agent_approval_result(
    *,
    agent: str,
    request_id: str,
    action: str,
    decision: str,
    summary: str | None = None,
    elapsed_sec: float | None = None,
    metadata: dict[str, Any] | None = None,
) -> bool:
    normalized_decision = (decision or "").strip().lower()
    title_map = {
        "approved": ("✅ <b>권한 승인 완료</b>", "approved"),
        "rejected": ("⚠️ <b>권한 거부됨</b>", "rejected"),
        "timeout": ("⏱️ <b>권한 확인 시간 초과</b>", "timeout"),
        "error": ("❌ <b>권한 확인 오류</b>", "error"),
    }
    title, status_value = title_map.get(normalized_decision, ("ℹ️ <b>권한 확인 결과</b>", normalized_decision or decision))

    lines: list[str] = [title]
    _append_line(lines, "agent", agent, code=True)
    _append_line(lines, "request_id", request_id, code=True)
    _append_line(lines, "action", action, limit=160)
    _append_line(lines, "decision", status_value, code=True)
    _append_line(lines, "elapsed", _format_duration(elapsed_sec), code=True)
    _append_metadata(lines, metadata)
    _append_block(lines, "summary", summary, limit=1000)
    severity_map = {
        "approved": "info",
        "rejected": "medium",
        "timeout": "high",
        "error": "high",
    }
    return send_reviewed_telegram_report(
        report_type="approval_result",
        title=f"권한 확인 결과: {action}",
        summary=summary or f"{agent} 권한 확인 결과는 {status_value} 입니다.",
        details="\n".join(lines),
        severity=severity_map.get(normalized_decision, "info"),
        source=agent,
        metadata=metadata,
        cooldown_sec=30,
    )
