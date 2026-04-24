#!/usr/bin/env python3
# -*- coding: utf-8 -*-
from __future__ import annotations

import argparse
import asyncio
import html
import json
import os
import re
import socket
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

load_dotenv(PROJECT_ROOT / ".env", override=True)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

from src.core.queue.redis_bus import get_redis_bus  # noqa: E402
from src.core.telegram_sender import send_html_message  # noqa: E402


ARTIFACT_DIR = PROJECT_ROOT / "data" / "automation" / "ai_ops_brief"
SHARED_BRAIN_DIR = PROJECT_ROOT / ".agent" / "shared-brain"
AI_OPS_INBOX_MD = SHARED_BRAIN_DIR / "ai-ops-brief-inbox.md"
AI_OPS_INBOX_JSONL = SHARED_BRAIN_DIR / "ai-ops-brief-inbox.jsonl"
DEFAULT_TIMEOUT_SEC = 180.0
AUTOMATION_NAME = "daily-ai-brief"
OPERATIONAL_GATES = """Operational gates:
- Treat this as report-only unless authority_tier/action_gate explicitly permits a local change.
- Use authority_tier, action_gate, control_focus, eval_method, novelty, and effective_score before recommending execution.
- External API mutations, notifications, deploys, credential changes, billing, DNS, production, or irreversible actions require G4/G5 approval.
- Every recommended action must include Plan-Execute-Verify evidence or a dry-run/eval path.
"""


def _read_brief(input_file: str | None) -> str:
    if input_file:
        return Path(input_file).read_text(encoding="utf-8").strip()
    return sys.stdin.read().strip()


def _ensure_artifact_dir() -> Path:
    ARTIFACT_DIR.mkdir(parents=True, exist_ok=True)
    return ARTIFACT_DIR


def _build_sora_request(brief_text: str) -> str:
    return (
        "다음은 매일 오전 9시에 자동 수집된 AI Ops Brief입니다.\n"
        "당신은 Sora입니다. 이 브리프를 대표님의 AI 활용 능력과 작업 환경을 강화하는 방향으로 검토하세요.\n\n"
        "규칙:\n"
        "- 원문을 반복하지 말고 고신호만 남기세요.\n"
        "- 대표님께 바로 보고할 수 있는 명확한 보고문을 작성하세요.\n"
        "- 오늘 바로 실행할 액션 1개와 이번 주 실험 1~2개를 고르세요.\n"
        "- 반복 활용할 프롬프트, 규칙, 자동화, 환경 강화 후보를 내재화 후보로 제안하세요.\n"
        "- 과대광고, 저신호 항목, 낮은 우선순위 항목은 버리세요.\n"
        "- 한국어, 결론 우선, 직접적이고 사실 중심으로 쓰세요.\n"
        "- 마지막 문장은 질문으로 끝내지 말고, 이미 확정된 다음 조치로 끝내세요.\n"
        "- '시작할까요?'가 아니라 '다음 실행 항목은 ...입니다.'처럼 보고하세요.\n\n"
        "출력 형식:\n"
        "1. 오늘의 핵심 결론\n"
        "2. 대표님 보고\n"
        "3. 즉시 실행 1개\n"
        "4. 이번 주 실험 1~2개\n"
        "5. 내재화 후보\n\n"
        "[AI Ops Brief 원문 시작]\n"
        f"{OPERATIONAL_GATES}\n"
        f"{brief_text}\n"
        "[AI Ops Brief 원문 끝]"
    )


def _render_html_report(reply_text: str) -> str:
    lines = [line.rstrip() for line in reply_text.strip().splitlines()]
    rendered: list[str] = ["<b>Sora AI Ops Brief</b>"]
    for line in lines:
        if not line.strip():
            rendered.append("")
            continue
        escaped = html.escape(line)
        if line[:1].isdigit() and "." in line[:4]:
            rendered.append(f"<b>{escaped}</b>")
        else:
            rendered.append(escaped)
    return "\n".join(rendered).strip()


def _parse_brief_items(brief_text: str) -> list[dict[str, str]]:
    items: list[dict[str, str]] = []
    current: dict[str, str] | None = None

    for raw_line in brief_text.splitlines():
        line = raw_line.strip()
        heading = re.match(r"^###\s+\d+\.\s+(.+)$", line)
        if heading:
            if current:
                items.append(current)
            current = {"title": heading.group(1).strip()}
            continue

        if current and line.startswith("- ") and ":" in line:
            key, value = line[2:].split(":", 1)
            current[key.strip()] = value.strip()

    if current:
        items.append(current)
    return items


def _clean_title(title: str, limit: int = 110) -> str:
    title = re.sub(r"\s+", " ", title).strip()
    title = re.sub(r"\b(Product|Announcements)\s+[A-Z][a-z]{2}\s+\d{1,2},\s+\d{4}\b", "", title).strip()
    if len(title) > limit:
        return title[: limit - 3].rstrip() + "..."
    return title


def _top_item_title(items: list[dict[str, str]]) -> str:
    if not items:
        return "상위 AI 업데이트"
    return _clean_title(items[0].get("title", "상위 AI 업데이트"))


def _render_fallback_report(brief_text: str) -> str:
    items = _parse_brief_items(brief_text)
    top_items = items[:3]

    lines = [
        "<b>Sora AI Ops Brief</b>",
        "<b>오늘 결론:</b> Sora 내부화 큐가 일시적으로 막혀 원문 분석 대신 안전 fallback 보고로 보냅니다. 핵심 신호만 추려 실행 중심으로 정리했습니다.",
        "",
        "<b>핵심 신호</b>",
    ]

    if not top_items:
        lines.append("- 오늘 수집된 고신호 항목이 없습니다.")
    else:
        for idx, item in enumerate(top_items, 1):
            title = _clean_title(item.get("title", "Untitled"))
            source = item.get("source", "unknown")
            authority_tier = item.get("authority_tier", "G0")
            eval_method = item.get("eval_method", "manual triage")
            relevance = item.get("why_it_matters", "실무 적용 가능성 확인 필요")
            url = item.get("url", "")
            line = f"{idx}. <b>{html.escape(title)}</b> ({html.escape(source)})"
            if url:
                line += f"\n{html.escape(url)}"
            line += f"\n의미: {html.escape(relevance)}"
            line += f"\nauthority_tier: {html.escape(authority_tier)}"
            line += f"\neval_method: {html.escape(eval_method)}"
            lines.append(line)

    first_title = _top_item_title(top_items)
    lines.extend(
        [
            "",
            "<b>오늘 실행 1개</b>",
            f"- {html.escape(first_title)}를 기준으로 현재 Codex/Sora 자동화에 바로 반영할 프롬프트, 모델 선택, 반복 작업 1개를 점검합니다.",
            "",
            "<b>이번 주 실험</b>",
            "- 브리프 수집 결과를 원문 나열이 아니라 '도입 여부 / 비용 / 위험 / 바로 할 일' 형식으로 재평가합니다.",
            "- Redis/Sora 내부화가 죽어도 사용자 보고는 계속 가고, 내재화 실패만 별도 운영 이슈로 남깁니다.",
            "",
            "<b>내재화 후보</b>",
            "- AI 뉴스는 '정보'가 아니라 '내 자동화 환경을 강화할 변경 후보'로만 저장합니다.",
            "- 저신호 항목은 링크만 보존하고 보고 본문에서는 제외합니다.",
        ]
    )
    return "\n".join(lines).strip()


def _write_fallback_artifact(brief_text: str, reason: str, source_path: Path | None = None) -> Path:
    artifact_dir = _ensure_artifact_dir()
    stem = _artifact_stem(source_path)
    output_path = artifact_dir / f"{stem}_sora_fallback.md"
    body = [
        "# Sora AI Ops Brief Fallback",
        f"- generated_at: {datetime.now().astimezone().isoformat()}",
        f"- reason: {reason}",
        f"- source_path: {source_path or ''}",
        "",
        "## fallback_report_html",
        _render_fallback_report(brief_text),
        "",
    ]
    output_path.write_text("\n".join(body).strip() + "\n", encoding="utf-8")
    return output_path


def _artifact_stem(source_path: Path | None = None) -> str:
    if source_path and source_path.name.endswith("_brief.md"):
        return source_path.name[: -len("_brief.md")]
    return datetime.now().strftime("%Y%m%d_%H%M%S")


def _build_pending_internalization_markdown(
    brief_text: str,
    generated_at: datetime,
    reason: str,
    source_path: Path | None = None,
) -> str:
    items = _parse_brief_items(brief_text)[:5]
    lines = [
        f"## AI Ops Brief Pending Internalization - {generated_at.strftime('%Y-%m-%d %H:%M:%S %Z')}".rstrip(),
        "",
        "- status: pending",
        f"- reason: {reason}",
        "- owner_goal: AI 관련 뉴스/정보를 매일 선별해 대표님의 AI 활용능력과 환경을 강화한다.",
        "- sora_action: 다음 Sora 세션에서 아래 항목을 보고서/프롬프트/자동화/환경설정 내재화 후보로 재검토한다.",
    ]
    if source_path:
        lines.append(f"- source_path: {source_path}")

    lines.extend(["", "### High-signal items"])
    if not items:
        lines.append("- No parsed items. Review the raw brief source.")
    else:
        for idx, item in enumerate(items, 1):
            title = _clean_title(item.get("title", "Untitled"))
            source = item.get("source", "unknown")
            url = item.get("url", "")
            why = item.get("why_it_matters", "n/a")
            authority_tier = item.get("authority_tier", "G0")
            action_gate = item.get("action_gate", "report-only")
            eval_method = item.get("eval_method", "manual triage")
            lines.append(f"{idx}. {title} ({source})")
            if url:
                lines.append(f"   - url: {url}")
            lines.append(f"   - why: {why}")
            lines.append(f"   - authority_tier: {authority_tier}")
            lines.append(f"   - action_gate: {action_gate}")
            lines.append(f"   - eval_method: {eval_method}")

    lines.extend(
        [
            "",
            "### Internalization rule",
            "- Keep only signals that can improve prompts, automations, model routing, agent reliability, cost control, or operator workflow.",
            "- Discard hype and low-signal product announcements unless they change today's operating decisions.",
        ]
    )
    return "\n".join(lines).strip() + "\n"


def _record_pending_internalization(
    brief_text: str,
    reason: str,
    source_path: Path | None = None,
    now: datetime | None = None,
) -> dict[str, str]:
    generated_at = now or datetime.now().astimezone()
    SHARED_BRAIN_DIR.mkdir(parents=True, exist_ok=True)

    markdown = _build_pending_internalization_markdown(
        brief_text=brief_text,
        generated_at=generated_at,
        reason=reason,
        source_path=source_path,
    )
    previous = ""
    if AI_OPS_INBOX_MD.exists():
        previous = AI_OPS_INBOX_MD.read_text(encoding="utf-8", errors="ignore").strip()
    AI_OPS_INBOX_MD.write_text(markdown + ("\n" + previous + "\n" if previous else ""), encoding="utf-8")

    payload: dict[str, Any] = {
        "ts": generated_at.isoformat(),
        "status": "pending",
        "reason": reason,
        "source_path": str(source_path) if source_path else "",
        "items": _parse_brief_items(brief_text)[:5],
    }
    with AI_OPS_INBOX_JSONL.open("a", encoding="utf-8") as fp:
        fp.write(json.dumps(payload, ensure_ascii=False) + "\n")

    return {
        "inbox_markdown": str(AI_OPS_INBOX_MD),
        "inbox_jsonl": str(AI_OPS_INBOX_JSONL),
    }


async def _deliver_async(brief_text: str, timeout_sec: float, source_path: Path | None = None) -> dict[str, str]:
    now = datetime.now()
    artifact_dir = _ensure_artifact_dir()
    stem = _artifact_stem(source_path) if source_path else now.strftime("%Y%m%d_%H%M%S")
    parsed_items = _parse_brief_items(brief_text)
    authority_tiers = sorted({item.get("authority_tier", "G0") for item in parsed_items if item.get("authority_tier")})
    if source_path:
        input_path = source_path
    else:
        input_path = artifact_dir / f"{stem}_brief.md"
        input_path.write_text(brief_text + "\n", encoding="utf-8")

    bus = get_redis_bus()
    try:
        request_id = await bus.enqueue_request(
            text=_build_sora_request(brief_text),
            channel="automation",
            device_id=os.getenv("COMPUTERNAME") or socket.gethostname(),
            session_id=f"automation:{AUTOMATION_NAME}",
            metadata={
                "automation": AUTOMATION_NAME,
                "kind": "daily_ai_ops_brief",
                "source_path": str(input_path),
                "safety_mode": "report_only_until_gate_allows_side_effects",
                "authority_tiers": authority_tiers or ["G0"],
                "parsed_item_count": len(parsed_items),
                "trace_required": True,
            },
        )
        result = await bus.wait_for_result(request_id, timeout=timeout_sec)
    finally:
        await bus.close()
    reply_text = str(result.get("reply", "") or "").strip()
    error_text = str(result.get("error", "") or "").strip()

    output_path = artifact_dir / f"{stem}_sora_reply.md"
    if reply_text:
        output_path.write_text(reply_text + "\n", encoding="utf-8")

    if error_text:
        raise RuntimeError(f"Sora delivery failed: {error_text}")
    if not reply_text:
        raise RuntimeError("Sora delivery failed: empty reply")

    return {
        "request_id": request_id,
        "input_path": str(input_path),
        "output_path": str(output_path),
        "reply_text": reply_text,
    }


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Deliver the daily AI ops brief to Sora and forward the reviewed result to Telegram."
    )
    parser.add_argument("--input-file", help="UTF-8 file containing the AI ops brief. Defaults to stdin.")
    parser.add_argument("--timeout-sec", type=float, default=DEFAULT_TIMEOUT_SEC)
    parser.add_argument("--skip-telegram", action="store_true", help="Do not forward the Sora result to Telegram.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and render fallback preview without Redis, Telegram, or shared-brain writes.")
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    brief_text = _read_brief(args.input_file)
    if not brief_text:
        raise SystemExit("AI ops brief is empty")
    source_path = Path(args.input_file).resolve() if args.input_file else None

    if args.dry_run:
        items = _parse_brief_items(brief_text)
        print(f"dry_run=1")
        print(f"parsed_items={len(items)}")
        print(_render_fallback_report(brief_text))
        return 0

    try:
        result = asyncio.run(_deliver_async(brief_text, timeout_sec=args.timeout_sec, source_path=source_path))
    except Exception as exc:
        reason = str(exc)
        if source_path is None:
            artifact_dir = _ensure_artifact_dir()
            source_path = artifact_dir / f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_brief.md"
            source_path.write_text(brief_text + "\n", encoding="utf-8")
        fallback_path = _write_fallback_artifact(brief_text, reason=reason, source_path=source_path)
        inbox = _record_pending_internalization(brief_text, reason=reason, source_path=source_path)

        fallback_ok = args.skip_telegram or send_html_message(_render_fallback_report(brief_text))
        if fallback_ok:
            print(f"fallback_reason={reason}")
            print("sora_delivery=fallback_sent")
            print(f"sora_fallback_artifact={fallback_path}")
            print(f"sora_internalization_pending={inbox['inbox_markdown']}")
            return 0

        send_html_message(
            "<b>Sora AI Ops Brief delivery failed</b>\n"
            "브리프 생성은 완료됐지만 텔레그램 전송에 실패했습니다. 로컬 로그 확인이 필요합니다."
        )
        raise

    reply_text = result["reply_text"]

    if not args.skip_telegram:
        html_body = _render_html_report(reply_text)
        ok = send_html_message(html_body)
        if not ok:
            raise SystemExit("Sora delivered the brief, but Telegram forwarding failed")

    print(f"request_id={result['request_id']}")
    print(f"input_path={result['input_path']}")
    print(f"output_path={result['output_path']}")
    print(reply_text)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
