# -*- coding: utf-8 -*-
"""Telegram adapter for Sora."""

from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import os
import re
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

from src.core.runtime.single_instance import claim_single_instance
from src.core.tools import ALL_TOOLS  # noqa: F401 - imported for tool registration side effects


PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
PROFIT_ROOT = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "profit"
MEMORY_DIR = PROJECT_ROOT / "src" / "core" / "data" / "assistant_memory"
MEMORY_DIR.mkdir(parents=True, exist_ok=True)

# 2026-05-12 P0: override=False — docker --env-file 우선 (stale /app/.env override 차단)
load_dotenv(PROJECT_ROOT / ".env", override=False)
load_dotenv(PROFIT_ROOT / ".env", override=False)

logger = logging.getLogger("neo.jarvis")

BOT_TOKEN = os.getenv("NEO_ALERT_BOT_TOKEN", "")
CHAT_ID = os.getenv("NEO_ALERT_CHAT_ID", "")
BOT_PID_PATH = MEMORY_DIR / "jarvis.pid"
# 2026-05-03: subprocess 로 polling 띄우는 구조에서 daemon cmdline 매치되면 self-conflict.
# `neo_genesis_daemon.py` 매처 제거 → polling subprocess 만 정확히 매치.
BOT_MATCHERS = ("neo_assistant_bot", "NeoAssistant().run()")
SEND_STARTUP_CHAT_NOTICE = os.getenv("SORA_SEND_STARTUP_CHAT_NOTICE", "").strip().lower() in {
    "1",
    "true",
    "yes",
    "on",
}


def _build_startup_chat_notice() -> str:
    return "?뚮씪 ?곌껐??蹂듦뎄?섏뿀?듬땲??\n?꾩슂?섎㈃ /s 濡??꾩옱 ?곹깭瑜??뺤씤?섏꽭??"


def _allow_direct_engine_fallback() -> bool:
    disable = os.getenv("SORA_DISABLE_DIRECT_ENGINE_FALLBACK", "").strip().lower()
    return disable not in {"1", "true", "yes", "on"}


def _brain_path_unavailable_message() -> str:
    return (
        "?꾩옱 ?묒뾽 ?ㅼ??ㅽ듃?덉씠???곌껐??遺덉븞?뺥빀?덈떎.\n"
        "?좎떆 ???ㅼ떆 ?쒕룄??二쇱꽭?? 臾몄젣媛 怨꾩냽?섎㈃ ?댁쁺 寃쎈줈瑜??먭??섍쿋?듬땲??"
    )


def _try_calendar_fastpath_reply(text: str, file_path: str | None = None) -> str | None:
    """Return direct calendar list reply for simple read-only queries."""
    if file_path:
        return None
    msg = (text or "").strip()
    if not msg:
        return None
    msg_lower = msg.lower()

    read_kw = ["일정", "캘린더", "calendar", "스케줄", "조회", "확인", "이번주", "다음주", "오늘", "내일"]
    write_kw = ["추가", "등록", "만들", "생성", "삭제", "취소", "변경", "수정", "옮겨", "연기", "예약"]
    if not any(k in msg_lower for k in read_kw):
        return None
    if any(k in msg_lower for k in write_kw):
        return None

    try:
        from src.core.integrations.google_calendar import calendar_list_events

        now = datetime.now()
        mode = "this_week"
        days = 7
        if "오늘" in msg_lower:
            mode = "today"
            days = 1
        elif "내일" in msg_lower:
            mode = "tomorrow"
            days = 2
        elif "다음주" in msg_lower:
            mode = "next_week"
            days = 14
        elif "이번주" in msg_lower:
            mode = "this_week"
            days = max(1, 7 - now.weekday())

        data = json.loads(calendar_list_events(days=days, max_results=50))
        events = data.get("events", []) if isinstance(data, dict) else []
        if not isinstance(events, list):
            events = []

        def _event_start_date(ev: dict):
            start = (ev or {}).get("start", "") or ""
            if not start:
                return None
            try:
                if "T" in start:
                    return datetime.fromisoformat(start.replace("Z", "+00:00")).date()
                return datetime.strptime(start[:10], "%Y-%m-%d").date()
            except Exception:
                return None

        if mode == "today":
            target = now.date()
            events = [ev for ev in events if _event_start_date(ev) == target]
        elif mode == "tomorrow":
            target = (now + timedelta(days=1)).date()
            events = [ev for ev in events if _event_start_date(ev) == target]
        elif mode == "next_week":
            week_start = (now - timedelta(days=now.weekday()) + timedelta(days=7)).date()
            week_end = week_start + timedelta(days=7)
            events = [ev for ev in events if (d := _event_start_date(ev)) and week_start <= d < week_end]
        else:
            week_start = (now - timedelta(days=now.weekday())).date()
            week_end = week_start + timedelta(days=7)
            events = [ev for ev in events if (d := _event_start_date(ev)) and week_start <= d < week_end]

        if not events:
            if mode == "today":
                return "오늘 일정이 없습니다."
            if mode == "tomorrow":
                return "내일 일정이 없습니다."
            if mode == "next_week":
                return "다음 주 일정이 없습니다."
            return "이번 주 일정이 없습니다."

        def _fmt_dt(v: str) -> str:
            if not v:
                return ""
            try:
                if "T" in v:
                    dt = datetime.fromisoformat(v.replace("Z", "+00:00"))
                    return dt.strftime("%Y-%m-%d %H:%M")
                d = datetime.strptime(v[:10], "%Y-%m-%d")
                return d.strftime("%Y-%m-%d (종일)")
            except Exception:
                return v

        lines = []
        for ev in sorted(events, key=lambda x: (x.get("start") or "")):
            title = ev.get("title") or "(제목 없음)"
            start_s = _fmt_dt(ev.get("start", ""))
            end_s = _fmt_dt(ev.get("end", ""))
            loc = (ev.get("location") or "").strip()
            span = f"{start_s} - {end_s}" if end_s else start_s
            lines.append(f"- {span}: {title}" + (f" (장소: {loc})" if loc else ""))

        if mode == "today":
            header = f"오늘 일정은 {len(events)}건입니다."
        elif mode == "tomorrow":
            header = f"내일 일정은 {len(events)}건입니다."
        elif mode == "next_week":
            header = f"다음 주 일정은 {len(events)}건입니다."
        else:
            header = f"이번 주 일정은 {len(events)}건입니다."
        return header + "\n\n" + "\n".join(lines)
    except Exception as exc:
        logger.warning("[Sora] calendar fastpath skipped due to error: %s", exc)
        return None


def _safe_document_filename(filename: str | None) -> str:
    candidate = Path(str(filename or "")).name.strip()
    if not candidate:
        return f"document_{int(time.time())}.bin"

    sanitized = re.sub(r"[^A-Za-z0-9._-]", "_", candidate)
    sanitized = sanitized.lstrip(".").strip("._")
    if not sanitized:
        sanitized = f"document_{int(time.time())}"

    suffix = Path(candidate).suffix
    if suffix and not sanitized.endswith(suffix):
        sanitized = f"{sanitized}{suffix}"

    return sanitized


def _extract_meeting_title(text: str) -> str | None:
    patterns = (
        r"^?뚯쓽濡??:\s*紐⑤뱶)?\s*?쒖옉[:竊??\s*(.*)$",
        r"^?뚯쓽\s*(?:湲곕줉\s*)??쒖옉[:竊??\s*(.*)$",
    )
    normalized = (text or "").strip()
    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return (match.group(1) or "").strip()
    return None


def _extract_meeting_finish_note(text: str) -> str | None:
    patterns = (
        r"^?뚯쓽濡?s*(?:?뺣━?댁쨾|?뺣━|留덈Т由?醫낅즺)[:竊??\s*(.*)$",
        r"^?뚯쓽\s*(?:?뺣━|醫낅즺)[:竊??\s*(.*)$",
    )
    normalized = (text or "").strip()
    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return (match.group(1) or "").strip()
    return None


def _is_meeting_status_text(text: str) -> bool:
    normalized = (text or "").strip()
    return normalized in {"?뚯쓽濡??곹깭", "?뚯쓽濡?吏꾪뻾?곹솴", "?뚯쓽濡?紐⑤뱶 ?곹깭", "?뚯쓽 ?곹깭"}


def _is_meeting_cancel_text(text: str) -> bool:
    normalized = (text or "").strip()
    return normalized in {"?뚯쓽濡?痍⑥냼", "?뚯쓽濡?紐⑤뱶 痍⑥냼", "?뚯쓽濡?以묐떒", "?뚯쓽 痍⑥냼"}


def _extract_meeting_title(text: str) -> str | None:
    patterns = (
        r"^?뚯쓽濡??:\s*紐⑤뱶)?\s*?쒖옉[:竊??\s*(.*)$",
        r"^?뚯쓽\s*(?:湲곕줉\s*)??쒖옉[:竊??\s*(.*)$",
    )
    normalized = (text or "").strip()
    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return (match.group(1) or "").strip()
    return None


def _extract_meeting_finish_note(text: str) -> str | None:
    patterns = (
        r"^?뚯쓽濡?s*(?:?뺣━?댁쨾|?뺣━|留덈Т由?醫낅즺)[:竊??\s*(.*)$",
        r"^?뚯쓽\s*(?:?뺣━|醫낅즺)[:竊??\s*(.*)$",
    )
    normalized = (text or "").strip()
    for pattern in patterns:
        match = re.match(pattern, normalized, flags=re.IGNORECASE)
        if match:
            return (match.group(1) or "").strip()
    return None


def _is_meeting_status_text(text: str) -> bool:
    normalized = (text or "").strip()
    return normalized in {"?뚯쓽濡??곹깭", "?뚯쓽濡?吏꾪뻾?곹솴", "?뚯쓽濡?紐⑤뱶 ?곹깭", "?뚯쓽 ?곹깭"}


def _is_meeting_cancel_text(text: str) -> bool:
    normalized = (text or "").strip()
    return normalized in {"?뚯쓽濡?痍⑥냼", "?뚯쓽濡?紐⑤뱶 痍⑥냼", "?뚯쓽濡?以묐떒", "?뚯쓽 痍⑥냼"}


def _normalize_meeting_text(text: str) -> str:
    return re.sub(r"[^0-9a-z\uac00-\ud7a3]+", "", (text or "").lower())


def _contains_meeting_keyword(text: str, keywords: tuple[str, ...]) -> bool:
    return any(keyword in text for keyword in keywords)


def _clean_meeting_title(title: str) -> str:
    cleaned = re.sub(r"\s+", " ", (title or "").strip(" \t:-_")).strip()
    cleaned = re.sub(
        r"(?:\ud68c\uc758\ub85d|\ud68c\uc758|\ubbf8\ud305|\ubaa8\ub4dc|\uc2dc\uc791\ud560\uac8c|\uc2dc\uc791\ud574\uc918|\uc2dc\uc791|\uae30\ub85d\ud574\uc918|\uae30\ub85d|\uc791\uc131\ud574\uc918|\uc791\uc131|\uc815\ub9ac\ud574\uc918|\uc815\ub9ac|\ub0a8\uaca8\uc918|\ud574\uc918|\ud560\uac8c)$",
        "",
        cleaned,
    ).strip(" -_:")
    return cleaned


def _looks_like_meeting_start_text(text: str) -> bool:
    normalized = _normalize_meeting_text(text)
    if not normalized:
        return False

    strong_phrases = (
        "\ud68c\uc758\ub85d\ubaa8\ub4dc\uc2dc\uc791",
        "\ud68c\uc758\ub85d\uc2dc\uc791",
        "\ud68c\uc758\uae30\ub85d\uc2dc\uc791",
        "\ud68c\uc758\ub85d\ub0a8\uaca8\uc918",
        "\ud68c\uc758\ub0b4\uc6a9\uae30\ub85d\ud574\uc918",
        "\ud68c\uc758\ub0b4\uc6a9\ub0a8\uaca8\uc918",
        "\uc774\ub300\ud654\ud68c\uc758\ub85d\uc73c\ub85c",
        "\uc9c0\uae08\ubd80\ud130\ud68c\uc758\ub85d",
        "\uc55e\uc73c\ub85c\ud68c\uc758\ub85d",
        "\ud68c\uc758\ub85d\uc791\uc131\ud574\uc918",
    )
    if any(phrase in normalized for phrase in strong_phrases):
        return True

    has_meeting_noun = _contains_meeting_keyword(
        normalized,
        (
            "\ud68c\uc758\ub85d",
            "\ud68c\uc758\uae30\ub85d",
            "\ud68c\uc758\uba54\ubaa8",
            "\ud68c\uc758\ub0b4\uc6a9",
            "\ubbf8\ud305\ub0b4\uc6a9",
        ),
    )
    has_start_intent = _contains_meeting_keyword(
        normalized,
        (
            "\uc2dc\uc791",
            "\ucf1c\uc918",
            "\uc5f4\uc5b4\uc918",
            "\ub4e4\uc5b4\uac00",
            "\uc804\ud658",
            "\uae30\ub85d\ud574\uc918",
            "\ub0a8\uaca8\uc918",
            "\uc791\uc131\ud574\uc918",
        ),
    )
    has_streaming_context = _contains_meeting_keyword(
        normalized,
        (
            "\uc9c0\uae08\ubd80\ud130",
            "\uc55e\uc73c\ub85c",
            "\uacc4\uc18d\ubcf4\ub0bc",
            "\uacc4\uc18d\ubcf4\ub0b4\ub294",
            "\uc774\ub300\ud654",
            "\uc774\ub0b4\uc6a9",
        ),
    )
    return has_meeting_noun and (has_start_intent or has_streaming_context)


def _extract_meeting_title(text: str) -> str | None:
    stripped = (text or "").strip()
    patterns = (
        r"^(?:/meeting_start\s+)?(?P<title>.+?)\s*(?:\ud68c\uc758|\ubbf8\ud305)\s*(?:\ud68c\uc758\ub85d|\uae30\ub85d)?\s*(?:\uc2dc\uc791(?:\ud560\uac8c|\ud574\uc918)?|\ud560\uac8c|\ud574\uc918|\ub0a8\uaca8\uc918)$",
        r"^(?:\ud68c\uc758\ub85d|\ud68c\uc758)\s*(?:\ubaa8\ub4dc)?\s*(?:\uc2dc\uc791|\uc2dc\uc791\ud560\uac8c|\uc2dc\uc791\ud574\uc918)[:\s-]*(?P<title>.*)$",
        r"^(?:\uc9c0\uae08\ubd80\ud130|\uc55e\uc73c\ub85c)?\s*(?P<title>.+?)\s*(?:\ud68c\uc758|\ubbf8\ud305)\s*(?:\ub0b4\uc6a9)?\s*(?:\ud68c\uc758\ub85d\uc73c\ub85c|\uae30\ub85d\uc73c\ub85c|\uae30\ub85d)\s*(?:\ub0a8\uaca8\uc918|\uc815\ub9ac\ud574\uc918|\uc791\uc131\ud574\uc918).*$",
    )
    for pattern in patterns:
        match = re.match(pattern, stripped, flags=re.IGNORECASE)
        if not match:
            continue
        cleaned = _clean_meeting_title(match.groupdict().get("title", ""))
        return cleaned
    return None


def _looks_like_meeting_finish_text(text: str) -> bool:
    normalized = _normalize_meeting_text(text)
    if not normalized:
        return False
    strong_phrases = (
        "\ud68c\uc758\ub85d\uc815\ub9ac\ud574\uc918",
        "\ud68c\uc758\uc815\ub9ac\ud574\uc918",
        "\ud68c\uc758\ub85d\ub9c8\ubb34\ub9ac\ud574\uc918",
        "\ud68c\uc758\ub85d\uc791\uc131\ud574\uc918",
        "\uc9c0\uae08\uae4c\uc9c0\ub0b4\uc6a9\uc815\ub9ac\ud574\uc918",
        "\uc774\uc81c\uc815\ub9ac\ud574\uc918",
        "\ud68c\uc758\ub05d\ub0ac\uc5b4\uc815\ub9ac\ud574\uc918",
    )
    if any(phrase in normalized for phrase in strong_phrases):
        return True
    has_finish_noun = _contains_meeting_keyword(
        normalized,
        ("\ud68c\uc758\ub85d", "\ud68c\uc758", "\ubbf8\ud305"),
    )
    has_finish_verb = _contains_meeting_keyword(
        normalized,
        (
            "\uc815\ub9ac",
            "\ub9c8\ubb34\ub9ac",
            "\uc885\ub8cc",
            "\ub05d\ub0b4",
            "\uc791\uc131",
            "\uc694\uc57d",
        ),
    )
    return has_finish_noun and has_finish_verb


def _extract_meeting_finish_note(text: str) -> str:
    stripped = (text or "").strip()
    patterns = (
        r"^(?:/meeting_finish)(?:\s+(?P<note>.*))?$",
        r"^(?:\ud68c\uc758\ub85d|\ud68c\uc758)\s*(?:\uc815\ub9ac|\ub9c8\ubb34\ub9ac|\uc885\ub8cc)[:\s-]*(?P<note>.*)$",
        r"^(?:\uc9c0\uae08\uae4c\uc9c0\s*)?(?:\ub0b4\uc6a9|\ud68c\uc758\ub0b4\uc6a9)\s*(?:\uc815\ub9ac|\uc694\uc57d)\s*\ud574\uc918[:\s-]*(?P<note>.*)$",
    )
    for pattern in patterns:
        match = re.match(pattern, stripped, flags=re.IGNORECASE)
        if match:
            return (match.groupdict().get("note", "") or "").strip()
    return ""


def _is_meeting_status_text(text: str) -> bool:
    normalized = _normalize_meeting_text(text)
    if not normalized:
        return False
    return any(
        phrase in normalized
        for phrase in (
            "\ud68c\uc758\ub85d\uc0c1\ud0dc",
            "\ud68c\uc758\uc0c1\ud0dc",
            "\ud68c\uc758\ub85d\uc9c4\ud589\uc0c1\ud669",
            "\uc5b4\ub514\uae4c\uc9c0\uae30\ub85d\ub410\uc5b4",
            "\uc5bc\ub9c8\ub098\uae30\ub85d\ub410\uc5b4",
            "\ud604\uc7ac\ud68c\uc758\ub85d",
        )
    )


def _is_meeting_cancel_text(text: str) -> bool:
    normalized = _normalize_meeting_text(text)
    if not normalized:
        return False
    return any(
        phrase in normalized
        for phrase in (
            "\ud68c\uc758\ub85d\ucde8\uc18c",
            "\ud68c\uc758\ub85d\ubaa8\ub4dc\ucde8\uc18c",
            "\ud68c\uc758\uae30\ub85d\uadf8\ub9cc",
            "\ud68c\uc758\ubaa8\ub4dc\uaebc\uc918",
            "\ud68c\uc758\ub85d\uc911\ub2e8",
        )
    )


class NeoAssistant:
    """Telegram entrypoint that forwards requests to the Sora engine."""

    _pending_oauth_flow: Any = None

    def __init__(self) -> None:
        from src.core.sora_engine import get_sora_engine

        self.engine = get_sora_engine()
        self.memory = self.engine.memory
        self.task_queue: asyncio.Queue = asyncio.Queue()
        self._last_request_id = ""
        self._worker_task: asyncio.Task | None = None
        self._recent_requests: dict[str, float] = {}
        self._recent_replies: dict[str, str] = {}
        self._dedup_window_sec = max(5, int(os.getenv("SORA_DEDUP_WINDOW_SEC", "20")))
        logger.info("[Sora] telegram adapter initialized")

    @staticmethod
    def _claim_polling_slot() -> tuple[bool, str]:
        return claim_single_instance(BOT_PID_PATH, BOT_MATCHERS)

    @staticmethod
    def _meeting_manager():
        from src.core.meeting_minutes import get_meeting_minutes_manager

        return get_meeting_minutes_manager()

    @staticmethod
    def _split_compound_request(text: str) -> list[str]:
        raw = (text or "").strip()
        if not raw or "\n" not in raw or raw.startswith("/"):
            return [raw]

        parts: list[str] = []
        for line in raw.splitlines():
            cleaned = re.sub(r"^\s*(?:[-*•]|\d+[.)])\s*", "", line).strip()
            if cleaned:
                parts.append(cleaned)

        if len(parts) < 2:
            return [raw]
        return parts[:6]

    @staticmethod
    def _make_request_fingerprint(chat_id: str, text: str, file_path: str | None = None) -> str:
        normalized = re.sub(r"\s+", " ", (text or "").strip())
        key = f"{chat_id}|{normalized}|{Path(file_path).name if file_path else ''}"
        return hashlib.sha1(key.encode("utf-8", errors="ignore")).hexdigest()

    def _prune_recent_requests(self) -> None:
        now = time.monotonic()
        expire_before = now - (self._dedup_window_sec * 6)
        stale_keys = [key for key, ts in self._recent_requests.items() if ts < expire_before]
        for key in stale_keys:
            self._recent_requests.pop(key, None)
            self._recent_replies.pop(key, None)

    def _reuse_recent_reply_if_duplicate(self, fingerprint: str) -> str | None:
        ts = self._recent_requests.get(fingerprint)
        if ts is None:
            return None
        if time.monotonic() - ts > self._dedup_window_sec:
            return None
        return self._recent_replies.get(fingerprint)

    async def _start_meeting_mode(self, message, title: str = "") -> None:
        result = self._meeting_manager().start_session(
            str(message.chat_id),
            title=title,
            started_by="telegram",
        )
        if result["status"] == "already_active":
            await message.reply_text(
                f"?대? ?뚯쓽濡?紐⑤뱶媛 吏꾪뻾 以묒엯?덈떎.\n"
                f"- ?쒕ぉ: {result['title']}\n"
                f"- ?꾩쟻 硫붾え: {result['entry_count']}嫄?n"
                f"?뺣━媛 ?앸굹硫?`/meeting_finish` ?먮뒗 `?뚯쓽濡??뺣━?댁쨾`濡?留덈Т由ы븯?몄슂."
            )
            return

        await message.reply_text(
            f"?뚯쓽濡?紐⑤뱶瑜??쒖옉?덉뒿?덈떎.\n"
            f"- ?쒕ぉ: {result['title']}\n"
            f"- ?댁젣 蹂대궡???띿뒪?? ?띿뒪??臾몄꽌, ?뚯꽦 ?뚯씪???뚯쓽 硫붾え濡??꾩쟻?⑸땲??\n"
            f"- 留덈Т由щ뒗 `/meeting_finish` ?먮뒗 `?뚯쓽濡??뺣━?댁쨾`濡??섏꽭??"
        )

    async def _meeting_status(self, message) -> None:
        try:
            status = self._meeting_manager().get_status(str(message.chat_id))
        except Exception:
            await message.reply_text("?꾩옱 ?쒖꽦 ?뚯쓽濡??몄뀡???놁뒿?덈떎.")
            return

        await message.reply_text(
            f"회의록 모드 진행 중입니다.\n"
            f"- 제목: {status['title']}\n"
            f"- 시작: {status['started_at']}\n"
            f"- 메모: {status['entry_count']}건\n"
            f"- 첨부: {status['attachment_count']}건"
        )

    async def _finish_meeting_mode(self, message, closing_note: str = "") -> None:
        try:
            result = self._meeting_manager().finalize_session(
                str(message.chat_id),
                closing_note=closing_note,
            )
        except Exception as exc:
            await message.reply_text(f"?뚯쓽濡??뺣━???ㅽ뙣?덉뒿?덈떎: {exc}")
            return

        markdown = (result.get("markdown", "") or "").strip()
        preview = markdown[:3500] if markdown else "?뚯쓽濡??댁슜??鍮꾩뼱 ?덉뒿?덈떎."
        try:
            await message.reply_text(
                f"?뚯쓽濡??뺣━媛 ?꾨즺?섏뿀?듬땲??\n"
                f"- ?쒕ぉ: {result['title']}\n"
                f"- 硫붾え: {result['entry_count']}嫄?n"
                f"- 泥⑤?: {result['attachment_count']}嫄?n"
                f"- ??? `{result['markdown_path']}`\n\n"
                f"{preview}",
                parse_mode="Markdown",
            )
        except Exception:
            await message.reply_text(
                f"?뚯쓽濡??뺣━媛 ?꾨즺?섏뿀?듬땲??\n"
                f"- ?쒕ぉ: {result['title']}\n"
                f"- 硫붾え: {result['entry_count']}嫄?n"
                f"- 泥⑤?: {result['attachment_count']}嫄?n"
                f"- ??? {result['markdown_path']}\n\n"
                f"{preview}"
            )

    async def _cancel_meeting_mode(self, message) -> None:
        try:
            result = self._meeting_manager().cancel_session(str(message.chat_id))
        except Exception:
            await message.reply_text("?꾩옱 ?쒖꽦 ?뚯쓽濡??몄뀡???놁뒿?덈떎.")
            return

        await message.reply_text(
            f"회의록 모드를 취소했습니다.\n"
            f"- 제목: {result['title']}\n"
            f"- 누적 메모: {result['entry_count']}건"
        )

    async def _append_meeting_text(self, message, text: str) -> None:
        result = self._meeting_manager().append_text(
            str(message.chat_id),
            text,
            source="telegram_text",
        )
        await message.reply_text(
            f"?뚯쓽 硫붾え瑜???ν뻽?듬땲?? ?꾩옱 {result['entry_count']}嫄??꾩쟻?섏뿀?듬땲??"
        )

    async def _ingest_meeting_file(self, message, file_path: str, caption: str = "") -> bool:
        if not self._meeting_manager().has_active_session(str(message.chat_id)):
            return False

        try:
            result = self._meeting_manager().ingest_file(
                str(message.chat_id),
                file_path,
                caption=caption,
            )
        except Exception as exc:
            await message.reply_text(f"?뚯쓽濡?泥⑤? 泥섎━???ㅽ뙣?덉뒿?덈떎: {exc}")
            return True

        await message.reply_text(
            f"회의록 첨부를 반영했습니다.\n"
            f"- 유형: {result['kind']}\n"
            f"- 누적 메모: {result['entry_count']}건\n"
            f"- 첨부: {result['attachment_count']}건"
        )
        return True

    async def _reject_unauthorized_chat(self, message) -> bool:
        if not message:
            return True
        if CHAT_ID and str(message.chat_id) != CHAT_ID:
            try:
                await message.reply_text("?덉슜??梨꾪똿?먯꽌留??ъ슜?????덉뒿?덈떎.")
            except Exception:
                pass
            return True
        return False

    async def _on_message(self, update, context) -> None:
        message = update.message
        if not message or not message.text:
            return
        if await self._reject_unauthorized_chat(message):
            return

        text = message.text.strip()
        if not text:
            return

        if _looks_like_meeting_start_text(text):
            await self._start_meeting_mode(message, _extract_meeting_title(text) or "")
            return

        if self._meeting_manager().has_active_session(str(message.chat_id)):
            if _looks_like_meeting_finish_text(text):
                finish_note = _extract_meeting_finish_note(text)
                await self._finish_meeting_mode(message, finish_note)
                return
            if _is_meeting_status_text(text):
                await self._meeting_status(message)
                return
            if _is_meeting_cancel_text(text):
                await self._cancel_meeting_mode(message)
                return
            await self._append_meeting_text(message, text)
            return

        try:
            from src.core.integrations.google_auth import extract_auth_code, get_pending_auth

            if get_pending_auth() and extract_auth_code(text):
                logger.info("[Sora] auto-detected google auth code in plain text")
                await self._complete_google_auth(message, raw_text=text)
                return
        except Exception:
            pass

        logger.info("[Sora] inbound text: %s", text[:80])
        await self.task_queue.put((update, text, None))

    async def _complete_google_auth(self, message, raw_text: str) -> None:
        try:
            from src.core.integrations.google_auth import exchange_code, load_pending_flow

            flow = load_pending_flow()
            ok, detail = exchange_code(flow, raw_text)
            if ok:
                NeoAssistant._pending_oauth_flow = None
                await message.reply_text(
                    "Google ?곕룞???꾨즺?섏뿀?듬땲??\n"
                    "?댁젣 Gmail怨?Google Calendar 湲곕뒫???ъ슜?????덉뒿?덈떎."
                )
            else:
                await message.reply_text(detail)
        except Exception as exc:
            await message.reply_text(f"Google ?곕룞 泥섎━ 以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎: {exc}")

    async def _on_photo(self, update, context) -> None:
        message = update.message
        if not message or not message.photo:
            return
        if await self._reject_unauthorized_chat(message):
            return

        try:
            photo = message.photo[-1]
            file = await context.bot.get_file(photo.file_id)
            local_path = MEMORY_DIR / f"photo_{int(time.time())}.jpg"
            await file.download_to_drive(str(local_path))

            caption = (message.caption or "첨부 이미지를 분석해줘.").strip()
            if await self._ingest_meeting_file(message, str(local_path), caption=caption):
                return
            await self.task_queue.put((update, caption, str(local_path)))
        except Exception as exc:
            logger.error("[Sora] photo download failed: %s", exc, exc_info=True)
            try:
                await message.reply_text("이미지를 불러오지 못했습니다.")
            except Exception:
                pass

    async def _on_document(self, update, context) -> None:
        message = update.message
        if not message or not message.document:
            return
        if await self._reject_unauthorized_chat(message):
            return

        try:
            document = message.document
            file = await context.bot.get_file(document.file_id)
            filename = _safe_document_filename(document.file_name)
            local_path = MEMORY_DIR / filename
            await file.download_to_drive(str(local_path))

            caption = (message.caption or f"{filename} ?뚯씪???뺤씤?댁쨾.").strip()
            await self.task_queue.put((update, caption, str(local_path)))
        except Exception as exc:
            logger.error("[Sora] document download failed: %s", exc, exc_info=True)
            try:
                await message.reply_text("?뚯씪????ν븯吏 紐삵뻽?듬땲??")
            except Exception:
                pass

    async def _on_audio(self, update, context) -> None:
        message = update.message
        if not message:
            return
        if await self._reject_unauthorized_chat(message):
            return

        audio_obj = message.audio or message.voice
        if not audio_obj:
            return

        try:
            file = await context.bot.get_file(audio_obj.file_id)
            source_name = getattr(message.audio, "file_name", "") or ""
            suffix = Path(source_name).suffix.lower()
            if not suffix:
                suffix = ".ogg" if message.voice else ".bin"

            local_path = MEMORY_DIR / f"audio_{int(time.time())}{suffix}"
            await file.download_to_drive(str(local_path))

            caption = (message.caption or "???뚯꽦 ?뚯씪???뺤씤?댁쨾.").strip()
            if await self._ingest_meeting_file(message, str(local_path), caption=caption):
                return
            await self.task_queue.put((update, caption, str(local_path)))
        except Exception as exc:
            logger.error("[Sora] audio download failed: %s", exc, exc_info=True)
            try:
                await message.reply_text("?뚯꽦 ?뚯씪??泥섎━?섏? 紐삵뻽?듬땲??")
            except Exception:
                pass

    async def _worker(self) -> None:
        while True:
            update, text, file_path = await self.task_queue.get()
            message = update.message

            try:
                self._prune_recent_requests()
                fingerprint = self._make_request_fingerprint(str(message.chat_id), text, file_path)
                cached_reply = self._reuse_recent_reply_if_duplicate(fingerprint)
                if cached_reply:
                    try:
                        await message.reply_text(cached_reply)
                    except Exception:
                        pass
                    logger.info("[Sora] duplicate request reused: %s", fingerprint[:10])
                    continue

                single_fast_reply = None
                if not file_path:
                    single_fast_reply = _try_calendar_fastpath_reply(text, file_path=None)
                    if single_fast_reply:
                        rendered = single_fast_reply[:4000]
                        self._recent_requests[fingerprint] = time.monotonic()
                        self._recent_replies[fingerprint] = rendered
                        try:
                            await message.reply_text(rendered)
                        except Exception:
                            pass
                        logger.info("[Sora] outbound fastpath reply: %s", rendered[:80])
                        continue

                action = (
                    "upload_photo"
                    if file_path and Path(file_path).suffix.lower() in {".jpg", ".jpeg", ".png", ".webp", ".gif"}
                    else "typing"
                )
                try:
                    await message.chat.send_action(action)
                except Exception as exc:
                    logger.warning("[Sora] send_action failed, continuing without indicator: %s", exc)

                progress_msg = None
                try:
                    progress_msg = await message.reply_text("처리 중입니다...")
                except Exception:
                    pass

                tasks = self._split_compound_request(text) if not file_path else [text]
                if len(tasks) == 1:
                    reply = await self._process_via_redis_or_direct(
                        text=text,
                        chat_id=str(message.chat_id),
                        file_path=file_path,
                        progress_msg=progress_msg,
                    )
                else:
                    total = len(tasks)
                    results: list[str] = []
                    for idx, task_text in enumerate(tasks, start=1):
                        if progress_msg:
                            try:
                                await progress_msg.edit_text(f"{idx}/{total} 처리 중...")
                            except Exception:
                                pass
                        try:
                            part_reply = await self._process_via_redis_or_direct(
                                text=task_text,
                                chat_id=str(message.chat_id),
                                file_path=None,
                                progress_msg=None,
                            )
                        except Exception as part_exc:
                            logger.error("[Sora] subtask failure: %s", part_exc, exc_info=True)
                            part_reply = f"실패: {str(part_exc)[:140]}"
                        results.append(f"{idx}. {task_text}\n{part_reply}".strip())
                    reply = f"요청하신 {total}개 작업 처리 결과:\n\n" + "\n\n".join(results)

                rendered = (reply or "처리는 완료됐지만 응답 생성에 실패했습니다.")[:4000]
                self._recent_requests[fingerprint] = time.monotonic()
                self._recent_replies[fingerprint] = rendered
                if progress_msg:
                    try:
                        await progress_msg.edit_text(rendered, parse_mode="Markdown")
                    except Exception:
                        try:
                            await progress_msg.edit_text(rendered)
                        except Exception:
                            await message.reply_text(rendered)
                else:
                    try:
                        await message.reply_text(rendered, parse_mode="Markdown")
                    except Exception:
                        await message.reply_text(rendered)

                logger.info("[Sora] outbound reply: %s", rendered[:80])
            except Exception as exc:
                logger.error("[Sora] worker failure: %s", exc, exc_info=True)
                try:
                    await message.reply_text(f"처리 중 오류가 발생했습니다: {str(exc)[:300]}")
                except Exception:
                    pass
            finally:
                self.task_queue.task_done()
    async def _listen_progress(self, request_id: str, progress_msg) -> None:
        try:
            from telegram import InlineKeyboardButton, InlineKeyboardMarkup
            from src.core.queue.redis_bus import get_redis_bus

            bus = get_redis_bus()
            async for event in bus.subscribe_progress(request_id):
                status = event.get("status", "running")
                msg_text = str(event.get("message", "")).strip()
                if not msg_text:
                    continue

                if status == "confirm_required":
                    keyboard = InlineKeyboardMarkup(
                        [[
                            InlineKeyboardButton("?ㅽ뻾 ?뱀씤", callback_data=f"confirm:{request_id}:approved"),
                            InlineKeyboardButton("?붿껌 痍⑥냼", callback_data=f"confirm:{request_id}:rejected"),
                        ]]
                    )
                    try:
                        await progress_msg.edit_text(msg_text, reply_markup=keyboard, parse_mode="Markdown")
                    except Exception:
                        try:
                            await progress_msg.edit_text(msg_text, reply_markup=keyboard)
                        except Exception:
                            pass
                else:
                    try:
                        await progress_msg.edit_text(msg_text)
                    except Exception:
                        pass
        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.debug("[Sora] progress listener ended: %s", exc)

    async def _process_via_redis_or_direct(
        self,
        text: str,
        chat_id: str,
        file_path: str | None = None,
        progress_msg=None,
    ) -> str:
        fast_reply = _try_calendar_fastpath_reply(text, file_path=file_path)
        if fast_reply:
            logger.info("[Sora] calendar fastpath reply used (telegram path)")
            return fast_reply

        try:
            from src.core.queue.redis_bus import get_redis_bus

            bus = get_redis_bus()
            await bus.connect()
            try:
                result_timeout = int(os.getenv("SORA_REDIS_RESULT_TIMEOUT_SEC", "35"))
            except Exception:
                result_timeout = 35
            if result_timeout < 10:
                result_timeout = 10

            request_id = await bus.enqueue_request(
                text=text,
                channel="telegram",
                device_id="phone",
                session_id=f"telegram:{chat_id}",
                chat_id=chat_id,
                file_path=file_path or "",
            )
            self._last_request_id = request_id
            logger.info("[Sora] queued redis request: %s", request_id)

            progress_task = None
            if progress_msg:
                progress_task = asyncio.create_task(self._listen_progress(request_id, progress_msg))

            try:
                result = await bus.wait_for_result(request_id, timeout=result_timeout)
            finally:
                if progress_task and not progress_task.done():
                    progress_task.cancel()
                    try:
                        await progress_task
                    except asyncio.CancelledError:
                        pass

            reply = result.get("reply", "")
            if reply and not result.get("error"):
                return str(reply)

            error_code = str(result.get("error", "empty"))
            logger.warning("[Sora] redis path returned non-success result: %s", error_code)
            if _allow_direct_engine_fallback():
                logger.warning("[Sora] using direct engine fallback because SORA_ALLOW_DIRECT_ENGINE_FALLBACK=1")
                return await self.engine.process(text, file_path=file_path)
            return _brain_path_unavailable_message()
        except Exception as exc:
            if _allow_direct_engine_fallback():
                logger.warning("[Sora] redis path unavailable, using direct engine: %s", exc)
                return await self.engine.process(text, file_path=file_path)

            logger.error("[Sora] redis path unavailable and direct fallback disabled: %s", exc)
            return _brain_path_unavailable_message()

    async def _ensure_brain_path_ready(self) -> None:
        try:
            from src.core.queue.redis_bus import get_redis_bus

            bus = get_redis_bus()
            await bus.connect()
            logger.info("[Sora] redis/brain path preflight passed")
        except Exception as exc:
            if _allow_direct_engine_fallback():
                logger.warning("[Sora] redis preflight failed, but direct fallback is enabled: %s", exc)
                return

            logger.warning("[Sora] redis/brain path unavailable during startup (will use direct engine): %s", exc)

    async def _on_setup_google(self, update, context) -> None:
        message = update.message
        if await self._reject_unauthorized_chat(message):
            return

        try:
            from src.core.integrations.google_auth import is_authenticated

            if is_authenticated():
                await message.reply_text(
                    "Google ?곕룞? ?대? ?꾨즺?섏뼱 ?덉뒿?덈떎.\n?꾩슂?섎㈃ /revoke_google ?쇰줈 ?댁젣?섏꽭??"
                )
                return
        except Exception:
            pass

        try:
            from src.core.integrations.google_auth import generate_auth_url, get_pending_auth

            pending = get_pending_auth()
            auth_url, flow = generate_auth_url()
            NeoAssistant._pending_oauth_flow = flow
            intro = "?대? 吏꾪뻾 以묒씤 Google ?곕룞???덉뒿?덈떎.\n\n" if pending else "Google ?곕룞???쒖옉?⑸땲??\n\n"
            guide = (
                intro
                + "1. ?꾨옒 留곹겕瑜??댁뼱 Google 濡쒓렇?몄쓣 吏꾪뻾?섏꽭??\n"
                + "2. ?쒖떆???몄쬆 肄붾뱶瑜?蹂듭궗?섏꽭??\n"
                + "3. ?뱀씤 肄붾뱶 ??以꾨쭔 洹몃?濡?蹂대궡嫄곕굹, `/google_code ?몄쬆肄붾뱶` ?뺤떇?쇰줈 蹂대궡二쇱꽭??\n"
                + "4. ?곕룞 以묒뿉??`/setup_google`???ㅼ떆 ?ㅽ뻾?섏? 留덉꽭?? 媛??留덉?留됱뿉 諛쏆? 肄붾뱶留??좏슚?⑸땲??\n\n"
                + f"[Google ?곕룞 ?닿린]({auth_url})"
            )

            await message.reply_text(
                guide,
                parse_mode="Markdown",
                disable_web_page_preview=True,
            )
        except FileNotFoundError as exc:
            await message.reply_text(str(exc))
        except Exception as exc:
            await message.reply_text(f"Google ?곕룞 留곹겕瑜?留뚮뱾吏 紐삵뻽?듬땲?? {exc}")

    async def _on_google_code(self, update, context) -> None:
        message = update.message
        if await self._reject_unauthorized_chat(message):
            return

        raw_text = message.text or ""
        await self._complete_google_auth(message, raw_text=raw_text)

    async def _on_revoke_google(self, update, context) -> None:
        message = update.message
        if await self._reject_unauthorized_chat(message):
            return

        try:
            from src.core.integrations.google_auth import revoke_token

            revoked = revoke_token()
            NeoAssistant._pending_oauth_flow = None
            if revoked:
                await message.reply_text("Google ?곕룞???댁젣?덉뒿?덈떎.")
            else:
                await message.reply_text("?댁젣??Google ?좏겙???놁뒿?덈떎.")
        except Exception as exc:
            await message.reply_text(f"Google ?곕룞 ?댁젣 以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎: {exc}")

    async def _on_cancel(self, update, context) -> None:
        message = update.message
        if await self._reject_unauthorized_chat(message):
            return

        if not self._last_request_id:
            await message.reply_text("?꾩옱 痍⑥냼???뱀씤 ?湲??붿껌???놁뒿?덈떎.")
            return

        try:
            from src.core.queue.redis_bus import get_redis_bus

            bus = get_redis_bus()
            await bus.set_confirm(self._last_request_id, False, ttl=10)
            await message.reply_text("理쒓렐 ?뱀씤 ?湲??붿껌??痍⑥냼?덉뒿?덈떎.")
        except Exception as exc:
            await message.reply_text(f"?붿껌 痍⑥냼 以??ㅻ쪟媛 諛쒖깮?덉뒿?덈떎: {exc}")

    async def _on_confirm_callback(self, update, context) -> None:
        query = update.callback_query
        await query.answer()

        data = query.data or ""
        parts = data.split(":")
        if len(parts) != 3 or parts[0] != "confirm":
            return

        _, request_id, decision = parts
        approved = decision == "approved"

        try:
            from src.core.queue.redis_bus import get_redis_bus

            bus = get_redis_bus()
            await bus.set_confirm(request_id, approved)
            label = "실행 승인됨" if approved else "요청 취소됨"
            await query.edit_message_text(f"{label}\n요청 ID: `{request_id}`", parse_mode="Markdown")
        except Exception as exc:
            logger.error("[Sora] confirm callback failed: %s", exc, exc_info=True)

    async def _on_status(self, update, context) -> None:
        message = update.message
        if await self._reject_unauthorized_chat(message):
            return
        await self.task_queue.put((update, "?꾩옱 ?쒖뒪???곹깭瑜??붿빟?댁꽌 蹂닿퀬?댁쨾.", None))

    async def _on_meeting_start(self, update, context) -> None:
        message = update.message
        if await self._reject_unauthorized_chat(message):
            return
        title = " ".join(context.args or []).strip()
        await self._start_meeting_mode(message, title)

    async def _on_meeting_status(self, update, context) -> None:
        message = update.message
        if await self._reject_unauthorized_chat(message):
            return
        await self._meeting_status(message)

    async def _on_meeting_finish(self, update, context) -> None:
        message = update.message
        if await self._reject_unauthorized_chat(message):
            return
        closing_note = " ".join(context.args or []).strip()
        await self._finish_meeting_mode(message, closing_note)

    async def _on_meeting_cancel(self, update, context) -> None:
        message = update.message
        if await self._reject_unauthorized_chat(message):
            return
        await self._cancel_meeting_mode(message)

    async def _after_initialize(self, application) -> None:
        if not self._worker_task or self._worker_task.done():
            self._worker_task = asyncio.create_task(self._worker())

        if SEND_STARTUP_CHAT_NOTICE and CHAT_ID:
            await application.bot.send_message(
                chat_id=CHAT_ID,
                text=_build_startup_chat_notice(),
            )
            logger.info("[Sora] startup notice sent")

    def _build_application(self):
        from telegram.ext import (
            ApplicationBuilder,
            CallbackQueryHandler,
            CommandHandler,
            MessageHandler,
            filters,
        )

        app = (
            ApplicationBuilder()
            .token(BOT_TOKEN)
            .post_init(self._after_initialize)
            .build()
        )

        app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message))
        app.add_handler(MessageHandler(filters.PHOTO, self._on_photo))
        app.add_handler(MessageHandler(filters.Document.ALL, self._on_document))
        app.add_handler(MessageHandler(filters.AUDIO | filters.VOICE, self._on_audio))
        app.add_handler(CommandHandler("x", self._on_cancel))
        app.add_handler(CommandHandler("s", self._on_status))
        app.add_handler(CommandHandler("meeting_start", self._on_meeting_start))
        app.add_handler(CommandHandler("meeting_status", self._on_meeting_status))
        app.add_handler(CommandHandler("meeting_finish", self._on_meeting_finish))
        app.add_handler(CommandHandler("meeting_cancel", self._on_meeting_cancel))
        app.add_handler(CommandHandler("setup_google", self._on_setup_google))
        app.add_handler(CommandHandler("google_code", self._on_google_code))
        app.add_handler(CommandHandler("revoke_google", self._on_revoke_google))
        app.add_handler(CallbackQueryHandler(self._on_confirm_callback, pattern=r"^confirm:"))
        return app

    def run(self) -> None:
        if not BOT_TOKEN:
            logger.error("[Sora] NEO_ALERT_BOT_TOKEN is missing")
            return

        acquired, reason = self._claim_polling_slot()
        if not acquired:
            logger.warning("[Sora] polling already active: %s", reason)
            return

        try:
            asyncio.run(self._ensure_brain_path_ready())
        except Exception as exc:
            logger.error("[Sora] telegram adapter startup blocked: %s", exc)
            return

        # 2026-05-03 보강: 다른 host 가 polling 중이면 Conflict 발생.
        # 즉시 종료 대신 60s wait 후 무한 retry — 다른 host stop 시 자동 우승.
        # drop_pending_updates=True 로 매 시도마다 큐 비워 backlog 누적 방지.
        import time as _time
        _attempt = 0
        while True:
            _attempt += 1
            try:
                logger.info(f"[Sora] telegram adapter starting (attempt={_attempt})")
                app = self._build_application()
                app.run_polling(drop_pending_updates=True)
                # run_polling 정상 종료 (예: SIGINT) → 루프 탈출
                logger.info("[Sora] telegram polling ended cleanly")
                return
            except Exception as exc:
                # Conflict / 일시 네트워크 / etc — Conflict 가 가장 잦음
                msg = str(exc)
                if "Conflict" in msg or "conflict" in msg or "terminated by other" in msg:
                    logger.warning(f"[Sora] polling conflict (다른 host 점유) — 60s 후 retry: {msg[:120]}")
                    _time.sleep(60)
                else:
                    logger.warning(f"[Sora] polling 일시 중단 — 30s 후 retry: {msg[:120]}")
                    _time.sleep(30)

    async def _run_async(self) -> None:
        if not BOT_TOKEN:
            logger.error("[Sora] NEO_ALERT_BOT_TOKEN is missing")
            return

        acquired, reason = self._claim_polling_slot()
        if not acquired:
            logger.warning("[Sora] async polling already active: %s", reason)
            return

        try:
            await self._ensure_brain_path_ready()
        except Exception as exc:
            logger.error("[Sora] async telegram startup blocked: %s", exc)
            return

        logger.info("[Sora] telegram adapter async loop starting")
        app = self._build_application()

        async with app:
            await self._after_initialize(app)
            await app.updater.start_polling(drop_pending_updates=True)
            await app.start()
            logger.info("[Sora] polling started")

            while True:
                await asyncio.sleep(3600)

    def run_in_thread(self):
        import threading

        acquired, reason = self._claim_polling_slot()
        if not acquired:
            logger.warning("[Sora] polling thread already active: %s", reason)
            return None

        def _thread_target() -> None:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(self._run_async())
            except Exception as exc:
                logger.error("[Sora] telegram thread failed: %s", exc, exc_info=True)
            finally:
                loop.close()

        thread = threading.Thread(target=_thread_target, daemon=True, name="sora")
        thread.start()
        return thread


async def _neoassistant_on_message(self, update, context) -> None:
    message = update.message
    if not message or not message.text:
        return
    if await self._reject_unauthorized_chat(message):
        return

    text = message.text.strip()
    if not text:
        return

    if _looks_like_meeting_start_text(text):
        await self._start_meeting_mode(message, _extract_meeting_title(text) or "")
        return

    if self._meeting_manager().has_active_session(str(message.chat_id)):
        if _looks_like_meeting_finish_text(text):
            await self._finish_meeting_mode(message, _extract_meeting_finish_note(text))
            return
        if _is_meeting_status_text(text):
            await self._meeting_status(message)
            return
        if _is_meeting_cancel_text(text):
            await self._cancel_meeting_mode(message)
            return
        await self._append_meeting_text(message, text)
        return

    try:
        from src.core.integrations.google_auth import extract_auth_code, get_pending_auth

        if get_pending_auth() and extract_auth_code(text):
            logger.info("[Sora] auto-detected google auth code in plain text")
            await self._complete_google_auth(message, raw_text=text)
            return
    except Exception:
        pass

    logger.info("[Sora] inbound text: %s", text[:80])
    await self.task_queue.put((update, text, None))


async def _neoassistant_on_document(self, update, context) -> None:
    message = update.message
    if not message or not message.document:
        return
    if await self._reject_unauthorized_chat(message):
        return

    try:
        document = message.document
        file = await context.bot.get_file(document.file_id)
        filename = _safe_document_filename(document.file_name)
        local_path = MEMORY_DIR / filename
        await file.download_to_drive(str(local_path))

        caption = (message.caption or f"{filename} ?뚯씪???뺤씤?댁쨾.").strip()
        if await self._ingest_meeting_file(message, str(local_path), caption=caption):
            return
        await self.task_queue.put((update, caption, str(local_path)))
    except Exception as exc:
        logger.error("[Sora] document download failed: %s", exc, exc_info=True)
        try:
            await message.reply_text("?뚯씪??諛쏆븘?ㅼ? 紐삵뻽?듬땲??")
        except Exception:
            pass


NeoAssistant._on_message = _neoassistant_on_message
NeoAssistant._on_document = _neoassistant_on_document


if __name__ == "__main__":
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(name)s] %(levelname)s %(message)s",
    )
    NeoAssistant().run()

