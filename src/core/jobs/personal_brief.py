# -*- coding: utf-8 -*-
"""Personal Brief Job — owner 개인 비서급 morning brief.

2026-05-12: STOP 해제 후 자비스급 proactive 첫 도입.

기존 `job_morning_report` (08:50) 는 SBU 회사 측 운영 보고.
이 모듈은 09:00 KST owner 본인용 비서급 brief — 회사 보고와 분리:

  - calendar_today()              → 오늘 일정
  - calendar_list_events(days=1)  → 내일 prep
  - gmail.list_unread(max=10)     → priority 미확인 메일

산출: 텔레그램 NEO_ALERT_BOT (@sora_yesol_bot) 발송.
"""
from __future__ import annotations

import json
import logging
import os
import time
import urllib.parse
import urllib.request
from datetime import datetime
from typing import Any

logger = logging.getLogger("neo.jobs.personal_brief")


def _safe_call(fn, *args, **kwargs) -> Any:
    """integration 호출 graceful — 토큰 없거나 권한 결손이어도 brief 자체는 계속."""
    try:
        return fn(*args, **kwargs)
    except Exception as e:
        logger.warning("[personal_brief] %s 실패: %s", getattr(fn, "__name__", "?"), e)
        return None


def _fetch_calendar_today() -> str:
    """오늘 이벤트 raw text — calendar_today() 반환 그대로 잘라 표시.

    2026-05-12: JSON `{"error": "..."}` 형식 → 한국어 친화 메시지로 변환.
    """
    try:
        from src.core.integrations.google_calendar import calendar_today
    except Exception as e:
        return f"📅 Calendar 모듈 미가용 (모듈 import 실패: {e})"
    raw = _safe_call(calendar_today)
    if raw is None:
        return "📅 Calendar 미연결 — 텔레그램에 `/setup_google` 입력해 재인증해주세요."

    # JSON 파싱 시도
    parsed = None
    if isinstance(raw, dict):
        parsed = raw
    elif isinstance(raw, str):
        try:
            parsed = json.loads(raw)
        except Exception:
            parsed = None

    # error 응답 친화 처리
    if isinstance(parsed, dict) and "error" in parsed:
        return "📅 Calendar 미연결 — 텔레그램에 `/setup_google` 입력해 재인증해주세요."

    # events 추출
    if isinstance(parsed, dict) and "events" in parsed:
        events = parsed["events"]
    elif isinstance(parsed, list):
        events = parsed
    else:
        # JSON 아닌 plain text
        return f"📅 {str(raw)[:500]}"

    if not events:
        return "📅 오늘 등록된 일정 없음."
    lines = ["📅 <b>오늘 일정</b>"]
    for ev in events[:8]:
        title = ev.get("summary", "(제목 없음)") if isinstance(ev, dict) else str(ev)[:50]
        start = ev.get("start", "") if isinstance(ev, dict) else ""
        if isinstance(start, dict):
            start = start.get("dateTime", "") or start.get("date", "")
        hhmm = start.split("T")[-1][:5] if "T" in start else "종일"
        lines.append(f"  • {hhmm} {title[:50]}")
    return "\n".join(lines)


def _fetch_tomorrow_prep() -> str:
    """내일 일정 lookahead — calendar_list_events(days=1)."""
    try:
        from src.core.integrations.google_calendar import calendar_list_events
    except Exception as e:
        return ""
    raw = _safe_call(calendar_list_events, 2, 10)  # 2일 범위 (오늘+내일)
    if raw is None:
        return ""
    try:
        if isinstance(raw, str):
            data = json.loads(raw)
        else:
            data = raw
        events = data.get("events", []) if isinstance(data, dict) else []
    except Exception:
        return ""
    # 내일 (KST) 기준 필터
    from datetime import timedelta, timezone
    KST = timezone(timedelta(hours=9))
    tomorrow = (datetime.now(KST) + timedelta(days=1)).date()
    tomorrow_events = []
    for ev in events:
        start = ev.get("start", "")
        if isinstance(start, dict):
            start = start.get("dateTime", "") or start.get("date", "")
        date_part = start.split("T")[0] if start else ""
        if date_part == tomorrow.isoformat():
            tomorrow_events.append(ev)
    if not tomorrow_events:
        return ""
    lines = ["", "🌅 <b>내일 prep</b>"]
    for ev in tomorrow_events[:5]:
        title = ev.get("summary", "(제목 없음)")
        start = ev.get("start", "")
        if isinstance(start, dict):
            start = start.get("dateTime", "") or start.get("date", "")
        hhmm = start.split("T")[-1][:5] if "T" in start else "종일"
        lines.append(f"  • {hhmm} {title[:50]}")
    return "\n".join(lines)


def _fetch_unread_gmail(max_results: int = 8) -> str:
    """미확인 메일 요약 — 발신자 + 제목."""
    try:
        from src.core.integrations.gmail import list_unread
    except Exception:
        return ""
    msgs = _safe_call(list_unread, max_results)
    if msgs is None:
        return ""
    if not msgs:
        return "\n📧 <b>미확인 메일</b>: 없음"
    lines = [f"\n📧 <b>미확인 메일 {len(msgs)}건</b>"]
    for m in msgs[:max_results]:
        if isinstance(m, dict):
            sender = m.get("from", m.get("sender", "?"))[:30]
            subject = m.get("subject", "(제목 없음)")[:50]
            lines.append(f"  • {sender}: {subject}")
        else:
            lines.append(f"  • {str(m)[:80]}")
    return "\n".join(lines)


def _send_telegram(text: str) -> bool:
    """NEO_ALERT_BOT (@sora_yesol_bot) 로 전송."""
    tok = os.getenv("NEO_ALERT_BOT_TOKEN", "")
    cid = os.getenv("OWNER_TELEGRAM_CHAT_ID") or os.getenv("NEO_ALERT_CHAT_ID", "")
    if not tok or not cid:
        logger.warning("[personal_brief] TG creds 미설정 — send skip")
        return False
    try:
        payload = urllib.parse.urlencode({
            "chat_id": cid,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }).encode()
        req = urllib.request.Request(
            f"https://api.telegram.org/bot{tok}/sendMessage",
            data=payload, method="POST",
        )
        with urllib.request.urlopen(req, timeout=10) as r:
            res = json.loads(r.read())
            return bool(res.get("ok"))
    except Exception as e:
        logger.error("[personal_brief] telegram send 실패: %s", e)
        return False


def run_personal_brief() -> dict:
    """09:00 KST cron entry point.

    Returns:
        {"sent": bool, "sections": int, "preview": str}
    """
    t0 = time.time()
    from datetime import timedelta, timezone
    KST = timezone(timedelta(hours=9))
    now = datetime.now(KST)

    sections = [
        f"🤖 <b>개인 비서 brief — {now.strftime('%Y-%m-%d (%a) %H:%M')}</b>",
        "",
    ]

    # 1. 오늘 일정
    sections.append(_fetch_calendar_today())

    # 2. 내일 prep
    tomorrow = _fetch_tomorrow_prep()
    if tomorrow:
        sections.append(tomorrow)

    # 3. 미확인 메일
    unread = _fetch_unread_gmail()
    if unread:
        sections.append(unread)

    # 4. 빈 brief 차단 (전부 fail 시 owner 에게 무의미한 알림 방지)
    body = "\n".join(s for s in sections if s)
    if body.count("\n") < 3:
        body += "\n\n(외부 API 응답 없음 — gcal_token / GOOGLE_APPLICATION_CREDENTIALS 점검 필요)"

    sent = _send_telegram(body)
    latency_ms = (time.time() - t0) * 1000
    logger.info("[personal_brief] sent=%s latency=%.0fms", sent, latency_ms)
    return {
        "sent": sent,
        "sections": len([s for s in sections if s]),
        "latency_ms": round(latency_ms, 1),
        "preview": body[:200],
    }


if __name__ == "__main__":
    # 단독 실행: python -m src.core.jobs.personal_brief
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
    result = run_personal_brief()
    print(json.dumps(result, ensure_ascii=False, indent=2))
