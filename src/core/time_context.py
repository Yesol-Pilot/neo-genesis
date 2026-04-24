# -*- coding: utf-8 -*-
"""Time context helpers for Sora prompts and date-sensitive requests."""
from __future__ import annotations

import os
import re
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

DEFAULT_TIMEZONE = os.getenv("SORA_TIMEZONE", "Asia/Seoul")
KST = ZoneInfo(DEFAULT_TIMEZONE)
_WEEKDAYS_KO = ["월", "화", "수", "목", "금", "토", "일"]
_RELATIVE_DATE_PATTERN = re.compile(
    r"(오늘|내일|어제|모레|글피|이번 ?주|다음 ?주|지난 ?주|이번 ?달|다음 ?달|"
    r"월요일|화요일|수요일|목요일|금요일|토요일|일요일|"
    r"today|tomorrow|yesterday|this week|next week|last week|current date|current time)",
    re.IGNORECASE,
)


def get_local_now() -> datetime:
    """Return an aware datetime in Sora's operating timezone."""
    return datetime.now(KST)


def needs_explicit_time_context(text: str) -> bool:
    """Detect whether the request is likely to depend on relative date/time interpretation."""
    if not text:
        return False
    return bool(_RELATIVE_DATE_PATTERN.search(text))


def build_time_context_block(now: datetime | None = None) -> str:
    """Build a compact absolute time anchor for the model."""
    now = now or get_local_now()
    today = now.date()
    yesterday = today - timedelta(days=1)
    tomorrow = today + timedelta(days=1)
    weekday_ko = _WEEKDAYS_KO[now.weekday()]
    return (
        "현재 시간 기준:\n"
        f"- timezone: {DEFAULT_TIMEZONE}\n"
        f"- now: {now.strftime('%Y-%m-%d %H:%M:%S')} ({weekday_ko})\n"
        f"- today: {today.isoformat()}\n"
        f"- tomorrow: {tomorrow.isoformat()}\n"
        f"- yesterday: {yesterday.isoformat()}\n"
        "- 상대 날짜 표현을 해석할 때는 반드시 위 절대 날짜를 기준으로 답한다."
    )


def inject_time_context(text: str) -> str:
    """Prepend explicit time context when the request depends on relative dates."""
    if not needs_explicit_time_context(text):
        return text
    return (
        "[시간 기준]\n"
        f"{build_time_context_block()}\n\n"
        "[사용자 요청]\n"
        f"{text}"
    )
