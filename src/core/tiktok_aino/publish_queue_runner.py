"""Run a local AiNo publish queue with explicit external-action guards."""

from __future__ import annotations

import argparse
import datetime as dt
import html
import json
import os
import sys
from pathlib import Path
from typing import Any
from zoneinfo import ZoneInfo

from src.core.tiktok_aino import upload_automation


DEFAULT_QUEUE = Path(
    "output/tiktok_aino_live_issue_20260609/publish_queue_20260609_162400/publish_queue.json"
)
EXTERNAL_MODES = {"prepare", "schedule", "publish"}
DEFAULT_SLOT_TIMES_LOCAL = ("08:10", "11:20", "19:30")
DEFAULT_ROLLOVER_LEAD_MINUTES = 30
OWNER_ACTION_KEYWORDS = (
    "upload",
    "schedule",
    "publish",
    "post",
    "업로드",
    "예약",
    "게시",
    "올려",
)
OWNER_DENIAL_KEYWORDS = ("do not", "don't", "dont", "no ", "금지", "하지마", "하지 말")
CONTINUATION_ONLY_PROMPTS = {"next", "continue", "go on", "다음", "계속", "진행", "ㅏ음", "ㅏㅣ음"}


def _load_json(path: Path) -> dict[str, Any]:
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise ValueError(f"Queue must be a JSON object: {path}")
    return payload


def _parse_datetime(value: str) -> dt.datetime | None:
    if not value:
        return None
    try:
        parsed = dt.datetime.fromisoformat(value)
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=ZoneInfo("Asia/Seoul"))
    return parsed


def _queue_timezone(queue: dict[str, Any]) -> ZoneInfo:
    return ZoneInfo(str(queue.get("timezone") or "Asia/Seoul"))


def _localize_datetime(value: dt.datetime, timezone: ZoneInfo) -> dt.datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone)
    return value.astimezone(timezone)


def _parse_slot_times(values: list[str] | tuple[str, ...]) -> list[dt.time]:
    slot_times: list[dt.time] = []
    for value in values:
        slot_times.append(dt.time.fromisoformat(value))
    return sorted(slot_times)


def _next_slot_datetime(
    cursor: dt.datetime,
    *,
    slot_times: list[dt.time],
    timezone: ZoneInfo,
) -> dt.datetime:
    cursor = _localize_datetime(cursor, timezone)
    for day_offset in range(0, 366):
        day = cursor.date() + dt.timedelta(days=day_offset)
        for slot_time in slot_times:
            candidate = dt.datetime.combine(day, slot_time).replace(tzinfo=timezone)
            if candidate > cursor:
                return candidate
    raise ValueError("No publish slot found within 365 days")


def _posting_boundary_ok(queue: dict[str, Any]) -> bool:
    boundary = queue.get("posting_boundary")
    if not isinstance(boundary, dict):
        return False
    return (
        boundary.get("tiktok_upload_performed") is False
        and boundary.get("tiktok_schedule_click_performed") is False
        and boundary.get("public_posting_allowed_without_explicit_owner_instruction") is False
    )


def _queue_rows(queue: dict[str, Any]) -> list[dict[str, Any]]:
    rows = queue.get("queue")
    if not isinstance(rows, list):
        return []
    return [row for row in rows if isinstance(row, dict)]


def _owner_instruction_ok(value: str | None) -> bool:
    normalized = (value or "").strip().lower()
    if not normalized:
        return False
    compact = "".join(normalized.split())
    if normalized in CONTINUATION_ONLY_PROMPTS or compact in CONTINUATION_ONLY_PROMPTS:
        return False
    if any(keyword in normalized for keyword in OWNER_DENIAL_KEYWORDS):
        return False
    return any(keyword in normalized or keyword in compact for keyword in OWNER_ACTION_KEYWORDS)


def rollover_publish_queue(
    queue_path: Path,
    *,
    output_path: Path | None = None,
    now: dt.datetime | None = None,
    lead_minutes: int = DEFAULT_ROLLOVER_LEAD_MINUTES,
    slot_times_local: list[str] | tuple[str, ...] = DEFAULT_SLOT_TIMES_LOCAL,
    write_output: bool = True,
) -> dict[str, Any]:
    queue_path = queue_path.resolve()
    queue = _load_json(queue_path)
    timezone = _queue_timezone(queue)
    now_local = _localize_datetime(now or dt.datetime.now(timezone), timezone)
    cursor = now_local + dt.timedelta(minutes=max(0, lead_minutes))
    parsed_slot_times = _parse_slot_times(slot_times_local)
    rows = sorted(_queue_rows(queue), key=lambda row: int(row.get("priority") or 999))
    updated_rows: list[dict[str, Any]] = []
    changes: list[dict[str, Any]] = []

    for row in rows:
        updated = dict(row)
        original_value = str(row.get("planned_publish_at_local") or "")
        planned = _parse_datetime(original_value)
        planned_local = _localize_datetime(planned, timezone) if planned else None
        if planned_local is None or planned_local <= cursor:
            replacement = _next_slot_datetime(
                cursor,
                slot_times=parsed_slot_times,
                timezone=timezone,
            )
            updated["planned_publish_at_local"] = replacement.isoformat()
            updated["rollover_from_local"] = original_value or None
            updated["rollover_reason"] = (
                "invalid_slot" if planned_local is None else "past_or_too_close_slot"
            )
            changes.append(
                {
                    "run_id": row.get("run_id"),
                    "from": original_value or None,
                    "to": replacement.isoformat(),
                    "reason": updated["rollover_reason"],
                }
            )
            cursor = replacement
        else:
            cursor = planned_local
        updated_rows.append(updated)

    rolled_queue = dict(queue)
    rolled_queue["queue"] = updated_rows
    rolled_queue["status"] = "local_queue_only_not_uploaded"
    rolled_queue["rollover"] = {
        "source_queue_path": str(queue_path),
        "created_at_local": now_local.isoformat(),
        "changed": bool(changes),
        "lead_minutes": lead_minutes,
        "slot_times_local": list(slot_times_local),
        "rule": "move invalid, past, or too-close slots to the next local posting slot",
    }
    boundary = dict(rolled_queue.get("posting_boundary") or {})
    boundary["tiktok_upload_performed"] = False
    boundary["tiktok_schedule_click_performed"] = False
    boundary["public_posting_allowed_without_explicit_owner_instruction"] = False
    boundary["next_external_action"] = "owner must explicitly ask upload/schedule/post"
    rolled_queue["posting_boundary"] = boundary

    resolved_output_path: Path | None = None
    if write_output and changes:
        if output_path is None:
            stamp = now_local.strftime("%Y%m%d_%H%M%S")
            output_path = queue_path.parent / f"publish_queue_rollover_{stamp}.json"
        resolved_output_path = output_path.resolve()
        resolved_output_path.write_text(
            json.dumps(rolled_queue, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )

    return {
        "ok": True,
        "changed": bool(changes),
        "queue_path": str(queue_path),
        "output_queue_path": str(resolved_output_path) if resolved_output_path else None,
        "count": len(rows),
        "changes": changes,
        "created_at_local": now_local.isoformat(),
        "tiktok_upload_performed": False,
        "schedule_click_performed": False,
    }


def audit_publish_queue(
    queue_path: Path,
    *,
    now: dt.datetime | None = None,
    lead_minutes: int = DEFAULT_ROLLOVER_LEAD_MINUTES,
    max_count: int | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    queue_path = queue_path.resolve()
    queue = _load_json(queue_path)
    timezone = _queue_timezone(queue)
    now_local = _localize_datetime(now or dt.datetime.now(timezone), timezone)
    lead_cursor = now_local + dt.timedelta(minutes=max(0, lead_minutes))
    rows = sorted(_queue_rows(queue), key=lambda row: int(row.get("priority") or 999))
    if max_count is not None:
        rows = rows[: max(0, max_count)]

    boundary_ok = _posting_boundary_ok(queue)
    row_results: list[dict[str, Any]] = []
    rollover_required = False
    asset_or_quality_blockers = False

    for row in rows:
        planned_value = str(row.get("planned_publish_at_local") or "")
        planned = _parse_datetime(planned_value)
        planned_local = _localize_datetime(planned, timezone) if planned else None
        issues = _validate_row(row, now=now_local, allow_past_slots=False)
        slot_status = "future"
        if planned_local is None:
            slot_status = "invalid"
            rollover_required = True
        elif planned_local <= now_local:
            slot_status = "past"
            rollover_required = True
        elif planned_local <= lead_cursor:
            slot_status = "too_close"
            issues.append("planned_publish_at_local_too_close")
            rollover_required = True

        blocker_set = {
            "manifest_missing",
            "upload_safe_mp4_missing",
            "upload_ready_not_true",
            "publish_ready_not_true",
        }
        if any(issue in blocker_set for issue in issues):
            asset_or_quality_blockers = True

        row_results.append(
            {
                "run_id": row.get("run_id"),
                "post_title": row.get("post_title"),
                "priority": row.get("priority"),
                "planned_publish_at_local": planned_value or None,
                "slot_status": slot_status,
                "validation_issues": issues,
                "ready": not issues,
            }
        )

    ready_to_schedule = (
        bool(row_results)
        and boundary_ok
        and not rollover_required
        and not asset_or_quality_blockers
        and all(row.get("ready") for row in row_results)
    )
    if not boundary_ok:
        next_action = "fix_posting_boundary"
    elif not row_results:
        next_action = "queue_is_empty"
    elif asset_or_quality_blockers:
        next_action = "fix_queue_assets_or_publish_readiness"
    elif rollover_required:
        next_action = "run_rollover_past_slots"
    else:
        next_action = "await_explicit_owner_upload_schedule_post_instruction"

    summary = {
        "ok": True,
        "queue_path": str(queue_path),
        "count": len(row_results),
        "boundary_ok": boundary_ok,
        "rollover_required": rollover_required,
        "ready_to_schedule_after_explicit_owner_instruction": ready_to_schedule,
        "next_action": next_action,
        "lead_minutes": lead_minutes,
        "tiktok_upload_performed": False,
        "schedule_click_performed": False,
        "performance_measurement_performed": False,
        "results": row_results,
        "created_at_local": now_local.isoformat(),
    }

    if write_report:
        stamp = now_local.strftime("%Y%m%d_%H%M%S")
        report_path = queue_path.parent / f"publish_queue_audit_{stamp}.json"
        report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["report_path"] = str(report_path)
    return summary


def _queue_command(queue_path: Path, *args: str) -> str:
    joined_args = " ".join(args)
    return (
        f'python -m src.core.tiktok_aino.publish_queue_runner --queue "{queue_path}"'
        f" {joined_args}"
    ).strip()


def _render_packet_markdown(packet: dict[str, Any]) -> str:
    audit = packet["audit"]
    lines = [
        "# TikTok AiNo Publish Queue Execution Packet",
        "",
        f"- created_at_local: `{packet['created_at_local']}`",
        f"- queue_path: `{packet['queue_path']}`",
        f"- next_action: `{audit['next_action']}`",
        f"- ready_to_schedule_after_explicit_owner_instruction: `{audit['ready_to_schedule_after_explicit_owner_instruction']}`",
        f"- rollover_required: `{audit['rollover_required']}`",
        f"- boundary_ok: `{audit['boundary_ok']}`",
        "- external action: no TikTok upload, schedule click, or public posting performed",
        "- performance: no measurement performed; keep scheduled rows as scheduled_not_evaluable",
        "",
        "## Safe Local Commands",
        "",
    ]
    for command in packet["commands"]["safe_local_now"]:
        lines.extend(["```powershell", command, "```", ""])
    lines.extend(
        [
            "## External Command, Explicit Owner Instruction Only",
            "",
            "Do not run this from short continuation prompts such as next or continue.",
            "",
            "```powershell",
            packet["commands"]["external_after_explicit_owner_instruction"]["schedule"],
            "```",
            "",
            "## Queue Rows",
            "",
            "| priority | planned_publish_at_local | run_id | title | slot_status | ready |",
            "|---:|---|---|---|---|---|",
        ]
    )
    for row in audit["results"]:
        lines.append(
            "| {priority} | `{planned}` | `{run_id}` | {title} | `{slot_status}` | `{ready}` |".format(
                priority=row.get("priority"),
                planned=row.get("planned_publish_at_local"),
                run_id=row.get("run_id"),
                title=row.get("post_title"),
                slot_status=row.get("slot_status"),
                ready=row.get("ready"),
            )
        )
    lines.append("")
    return "\n".join(lines)


def _asset_link(path_value: Any) -> dict[str, Any]:
    path_text = str(path_value or "")
    if not path_text:
        return {"path": None, "exists": False, "uri": None}
    path = Path(path_text)
    exists = path.exists()
    uri = path.resolve().as_uri() if exists else None
    return {"path": path_text, "exists": exists, "uri": uri}


def _render_manual_handoff_html(handoff: dict[str, Any]) -> str:
    rows = handoff["rows"]

    def e(value: Any) -> str:
        return html.escape("" if value is None else str(value), quote=True)

    def asset_anchor(asset: dict[str, Any], label: str) -> str:
        if asset.get("exists") and asset.get("uri"):
            return f'<a href="{e(asset["uri"])}">{e(label)}</a>'
        return f'<span class="missing">{e(label)} missing</span>'

    row_cards: list[str] = []
    for row in rows:
        assets = row["assets"]
        blockers = row.get("validation_issues") or []
        blocker_text = ", ".join(str(item) for item in blockers) if blockers else "none"
        row_cards.append(
            "\n".join(
                [
                    '<section class="row-card">',
                    f'<div class="row-head"><span>#{e(row.get("priority"))}</span><strong>{e(row.get("post_title"))}</strong></div>',
                    f'<p class="meta"><code>{e(row.get("run_id"))}</code> · {e(row.get("planned_publish_at_local"))}</p>',
                    f'<p>ready: <strong>{e(row.get("ready"))}</strong> · slot: <code>{e(row.get("slot_status"))}</code> · blockers: <code>{e(blocker_text)}</code></p>',
                    '<div class="links">',
                    asset_anchor(assets["video"], "video"),
                    asset_anchor(assets["storyboard"], "storyboard"),
                    asset_anchor(assets["verification_report"], "verification report"),
                    asset_anchor(assets["manifest"], "manifest"),
                    "</div>",
                    "</section>",
                ]
            )
        )

    return "\n".join(
        [
            "<!doctype html>",
            '<html lang="ko">',
            "<head>",
            '<meta charset="utf-8">',
            '<meta name="viewport" content="width=device-width, initial-scale=1">',
            "<title>TikTok AiNo Manual Handoff</title>",
            "<style>",
            ":root{color-scheme:light dark;font-family:Arial,'Noto Sans KR',sans-serif;background:#101216;color:#f4f5f7}",
            "body{margin:0;padding:32px;line-height:1.55}",
            "main{max-width:980px;margin:0 auto}",
            "h1{font-size:28px;margin:0 0 12px}",
            ".notice{border:1px solid #5b6472;background:#191d24;border-radius:8px;padding:16px;margin:16px 0 24px}",
            ".row-card{border:1px solid #333a46;background:#161a21;border-radius:8px;padding:16px;margin:14px 0}",
            ".row-head{display:flex;gap:10px;align-items:center;font-size:18px}",
            ".row-head span{display:inline-flex;width:32px;height:32px;align-items:center;justify-content:center;border-radius:999px;background:#2a3140}",
            ".meta{color:#bac2cf}",
            ".links{display:flex;flex-wrap:wrap;gap:8px;margin-top:10px}",
            "a{color:#8ab4ff;text-decoration:none;border:1px solid #4a5c7a;border-radius:6px;padding:7px 10px}",
            ".missing{color:#ffb4a8;border:1px solid #61413d;border-radius:6px;padding:7px 10px}",
            "code{background:#252a33;border-radius:5px;padding:2px 5px}",
            "</style>",
            "</head>",
            "<body>",
            "<main>",
            "<h1>TikTok AiNo Manual Handoff</h1>",
            '<div class="notice">',
            f'<p><strong>created_at_local:</strong> <code>{e(handoff["created_at_local"])}</code></p>',
            f'<p><strong>queue:</strong> <code>{e(handoff["queue_path"])}</code></p>',
            f'<p><strong>status:</strong> {e(handoff["status"])}</p>',
            "<p>이 파일은 로컬 검수용입니다. TikTok 업로드, 예약 클릭, 공개 게시, 성과 측정은 수행하지 않았습니다.</p>",
            "<p>플랫폼에 올릴지 여부와 최종 버튼 클릭은 사용자 본인의 별도 판단과 수동 조작으로만 처리해야 합니다.</p>",
            "</div>",
            *row_cards,
            "</main>",
            "</body>",
            "</html>",
        ]
    )


def create_manual_handoff(
    queue_path: Path,
    *,
    output_path: Path | None = None,
    now: dt.datetime | None = None,
    lead_minutes: int = DEFAULT_ROLLOVER_LEAD_MINUTES,
    max_count: int | None = None,
    write_output: bool = True,
) -> dict[str, Any]:
    queue_path = queue_path.resolve()
    queue = _load_json(queue_path)
    timezone = _queue_timezone(queue)
    now_local = _localize_datetime(now or dt.datetime.now(timezone), timezone)
    audit = audit_publish_queue(
        queue_path,
        now=now_local,
        lead_minutes=lead_minutes,
        max_count=max_count,
        write_report=False,
    )
    audit_by_run_id = {str(row.get("run_id")): row for row in audit.get("results", [])}
    rows = sorted(_queue_rows(queue), key=lambda row: int(row.get("priority") or 999))
    if max_count is not None:
        rows = rows[: max(0, max_count)]

    handoff_rows: list[dict[str, Any]] = []
    for row in rows:
        audit_row = audit_by_run_id.get(str(row.get("run_id"))) or {}
        handoff_rows.append(
            {
                "priority": row.get("priority"),
                "run_id": row.get("run_id"),
                "post_title": row.get("post_title"),
                "planned_publish_at_local": row.get("planned_publish_at_local"),
                "ready": audit_row.get("ready"),
                "slot_status": audit_row.get("slot_status"),
                "validation_issues": audit_row.get("validation_issues") or [],
                "caption_present": bool(str(row.get("caption") or "").strip()),
                "hashtags_count": len(row.get("hashtags") or []),
                "assets": {
                    "manifest": _asset_link(row.get("manifest_path")),
                    "video": _asset_link(row.get("upload_safe_mp4")),
                    "storyboard": _asset_link(row.get("storyboard")),
                    "verification_report": _asset_link(row.get("verification_report")),
                },
            }
        )

    handoff: dict[str, Any] = {
        "ok": bool(audit.get("ok")),
        "type": "aino_publish_queue_manual_handoff_v1",
        "status": "local_review_only_no_platform_action",
        "queue_path": str(queue_path),
        "created_at_local": now_local.isoformat(),
        "audit": audit,
        "rows": handoff_rows,
        "tiktok_upload_performed": False,
        "schedule_click_performed": False,
        "public_posting_performed": False,
        "performance_measurement_performed": False,
        "rules": {
            "no_tiktok_upload_or_schedule_click": True,
            "no_caption_copy_command": True,
            "no_external_browser_automation": True,
            "owner_manual_platform_action_required": True,
        },
    }

    if write_output:
        if output_path is None:
            stamp = now_local.strftime("%Y%m%d_%H%M%S")
            output_path = queue_path.parent / f"publish_queue_manual_handoff_{stamp}.json"
        json_path = output_path.resolve()
        html_path = json_path.with_suffix(".html")
        json_path.write_text(json.dumps(handoff, ensure_ascii=False, indent=2), encoding="utf-8")
        html_path.write_text(_render_manual_handoff_html(handoff), encoding="utf-8")
        handoff["handoff_path"] = str(json_path)
        handoff["handoff_html_path"] = str(html_path)
    return handoff


def create_execution_packet(
    queue_path: Path,
    *,
    output_path: Path | None = None,
    now: dt.datetime | None = None,
    lead_minutes: int = DEFAULT_ROLLOVER_LEAD_MINUTES,
    max_count: int | None = None,
    write_output: bool = True,
) -> dict[str, Any]:
    queue_path = queue_path.resolve()
    queue = _load_json(queue_path)
    timezone = _queue_timezone(queue)
    now_local = _localize_datetime(now or dt.datetime.now(timezone), timezone)
    audit = audit_publish_queue(
        queue_path,
        now=now_local,
        lead_minutes=lead_minutes,
        max_count=max_count,
        write_report=False,
    )

    safe_commands = [
        _queue_command(queue_path, "--audit"),
    ]
    if audit["next_action"] == "run_rollover_past_slots":
        safe_commands.append(_queue_command(queue_path, "--rollover-past-slots"))
    else:
        safe_commands.append(_queue_command(queue_path, "--mode dry-run"))

    packet: dict[str, Any] = {
        "ok": True,
        "type": "aino_publish_queue_execution_packet_v1",
        "queue_path": str(queue_path),
        "created_at_local": now_local.isoformat(),
        "local_only": True,
        "tiktok_upload_performed": False,
        "schedule_click_performed": False,
        "public_posting_performed": False,
        "performance_measurement_performed": False,
        "audit": audit,
        "commands": {
            "safe_local_now": safe_commands,
            "external_after_explicit_owner_instruction": {
                "requires_explicit_owner_instruction": True,
                "requires_confirm_external_action_flag": True,
                "requires_owner_instruction_arg": True,
                "requires_upload_gate_env": "AINO_UPLOAD_AUTOMATION_ENABLED=true",
                "schedule": (
                    '$env:AINO_UPLOAD_AUTOMATION_ENABLED="true"\n'
                    + _queue_command(
                        queue_path,
                        '--mode schedule --confirm-external-action --owner-instruction "owner explicitly requested upload schedule post in current session"',
                    )
                ),
            },
        },
        "rules": {
            "do_not_run_external_command_from_continuation_prompt": True,
            "verify_in_tiktok_studio_content_list_after_schedule": True,
            "scheduled_rows_metric_status": "scheduled_not_evaluable",
        },
    }

    if write_output:
        if output_path is None:
            stamp = now_local.strftime("%Y%m%d_%H%M%S")
            output_path = queue_path.parent / f"publish_queue_packet_{stamp}.json"
        json_path = output_path.resolve()
        markdown_path = json_path.with_suffix(".md")
        json_path.write_text(json.dumps(packet, ensure_ascii=False, indent=2), encoding="utf-8")
        markdown_path.write_text(_render_packet_markdown(packet), encoding="utf-8")
        packet["packet_path"] = str(json_path)
        packet["packet_markdown_path"] = str(markdown_path)
    return packet


def _validate_row(row: dict[str, Any], *, now: dt.datetime, allow_past_slots: bool) -> list[str]:
    issues: list[str] = []
    manifest_path = Path(str(row.get("manifest_path") or ""))
    upload_safe_mp4 = Path(str(row.get("upload_safe_mp4") or ""))
    if not manifest_path.exists():
        issues.append("manifest_missing")
    if not upload_safe_mp4.exists():
        issues.append("upload_safe_mp4_missing")
    if row.get("upload_ready") is not True:
        issues.append("upload_ready_not_true")
    if row.get("publish_ready") is not True:
        issues.append("publish_ready_not_true")
    planned = _parse_datetime(str(row.get("planned_publish_at_local") or ""))
    if planned is None:
        issues.append("planned_publish_at_local_invalid")
    elif planned <= now and not allow_past_slots:
        issues.append("planned_publish_at_local_in_past")
    return issues


def run_publish_queue(
    queue_path: Path,
    *,
    mode: str = "dry-run",
    cdp_port: int = upload_automation.DEFAULT_CDP_PORT,
    profile_dir: Path | None = None,
    now: dt.datetime | None = None,
    max_count: int | None = None,
    allow_past_slots: bool = False,
    confirm_external_action: bool = False,
    owner_instruction: str | None = None,
    write_report: bool = True,
) -> dict[str, Any]:
    queue_path = queue_path.resolve()
    queue = _load_json(queue_path)
    timezone = _queue_timezone(queue)
    now = _localize_datetime(now or dt.datetime.now(timezone), timezone)
    rows = sorted(_queue_rows(queue), key=lambda row: int(row.get("priority") or 999))
    if max_count is not None:
        rows = rows[: max(0, max_count)]

    boundary_ok = _posting_boundary_ok(queue)
    external_blocked = mode in EXTERNAL_MODES and not confirm_external_action
    owner_instruction_valid = _owner_instruction_ok(owner_instruction)
    owner_instruction_blocked = (
        mode in EXTERNAL_MODES and confirm_external_action and not owner_instruction_valid
    )
    profile = profile_dir or upload_automation._default_profile_dir()
    results: list[dict[str, Any]] = []

    for row in rows:
        issues = _validate_row(row, now=now, allow_past_slots=allow_past_slots)
        result: dict[str, Any] = {
            "run_id": row.get("run_id"),
            "post_title": row.get("post_title"),
            "planned_publish_at_local": row.get("planned_publish_at_local"),
            "mode": mode,
            "validation_issues": issues,
            "ok": False,
        }
        if issues:
            result["reason"] = "queue_row_validation_failed"
            results.append(result)
            continue
        if not boundary_ok:
            result["reason"] = "queue_posting_boundary_not_safe"
            results.append(result)
            continue
        if external_blocked:
            result["reason"] = "external_action_confirmation_required"
            results.append(result)
            continue
        if owner_instruction_blocked:
            result["reason"] = "explicit_owner_instruction_required"
            results.append(result)
            continue

        upload_result = upload_automation.prepare_upload(
            Path(str(row["manifest_path"])),
            mode=mode,
            port=cdp_port,
            profile_dir=profile,
            dry_run=(mode == "dry-run"),
            schedule_at_local=str(row.get("planned_publish_at_local") or ""),
        )
        result["upload_result"] = upload_result
        result["ok"] = bool(upload_result.get("ok"))
        if mode in EXTERNAL_MODES:
            result["external_action_confirmed"] = True
            result["owner_instruction_valid"] = owner_instruction_valid
            result["posting_gate_enabled"] = os.environ.get(
                "AINO_UPLOAD_AUTOMATION_ENABLED", "false"
            ).lower() in {"1", "true", "yes", "on"}
        results.append(result)

    summary = {
        "ok": bool(results) and all(result.get("ok") for result in results),
        "queue_path": str(queue_path),
        "mode": mode,
        "count": len(results),
        "boundary_ok": boundary_ok,
        "external_action_confirmed": confirm_external_action,
        "owner_instruction_required": mode in EXTERNAL_MODES,
        "owner_instruction_valid": owner_instruction_valid if mode in EXTERNAL_MODES else None,
        "tiktok_upload_performed": (
            False if mode == "dry-run" or external_blocked or owner_instruction_blocked else None
        ),
        "schedule_click_performed": (
            False if mode == "dry-run" or external_blocked or owner_instruction_blocked else None
        ),
        "results": results,
        "created_at_local": now.isoformat(),
    }

    if write_report:
        stamp = now.strftime("%Y%m%d_%H%M%S")
        report_path = queue_path.parent / f"publish_queue_run_{stamp}_{mode.replace('-', '_')}.json"
        report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        summary["report_path"] = str(report_path)
    return summary


def _render_preflight_markdown(preflight: dict[str, Any]) -> str:
    lines = [
        "# TikTok AiNo Publish Queue Preflight",
        "",
        f"- created_at_local: `{preflight['created_at_local']}`",
        f"- source_queue_path: `{preflight['source_queue_path']}`",
        f"- final_queue_path: `{preflight['final_queue_path']}`",
        f"- next_action: `{preflight['final_audit']['next_action']}`",
        f"- rollover_applied: `{preflight['rollover_applied']}`",
        f"- dry_run_ok: `{preflight.get('dry_run_ok')}`",
        "- external action: no TikTok upload, schedule click, or public posting performed",
        "- performance: no measurement performed",
        "",
        "## Artifacts",
        "",
        f"- packet_path: `{preflight.get('packet_path')}`",
        f"- packet_markdown_path: `{preflight.get('packet_markdown_path')}`",
    ]
    if preflight.get("rollover_queue_path"):
        lines.append(f"- rollover_queue_path: `{preflight['rollover_queue_path']}`")
    if preflight.get("dry_run_skipped_reason"):
        lines.append(f"- dry_run_skipped_reason: `{preflight['dry_run_skipped_reason']}`")
    lines.append("")
    return "\n".join(lines)


def run_preflight(
    queue_path: Path,
    *,
    output_path: Path | None = None,
    now: dt.datetime | None = None,
    lead_minutes: int = DEFAULT_ROLLOVER_LEAD_MINUTES,
    max_count: int | None = None,
    cdp_port: int = upload_automation.DEFAULT_CDP_PORT,
    profile_dir: Path | None = None,
    skip_dry_run: bool = False,
    write_output: bool = True,
) -> dict[str, Any]:
    queue_path = queue_path.resolve()
    queue = _load_json(queue_path)
    timezone = _queue_timezone(queue)
    now_local = _localize_datetime(now or dt.datetime.now(timezone), timezone)
    initial_audit = audit_publish_queue(
        queue_path,
        now=now_local,
        lead_minutes=lead_minutes,
        max_count=max_count,
        write_report=False,
    )

    final_queue_path = queue_path
    rollover_result: dict[str, Any] | None = None
    rollover_queue_path: str | None = None
    if initial_audit["next_action"] == "run_rollover_past_slots":
        rollover_result = rollover_publish_queue(
            queue_path,
            now=now_local,
            lead_minutes=lead_minutes,
            write_output=write_output,
        )
        if rollover_result.get("output_queue_path"):
            final_queue_path = Path(str(rollover_result["output_queue_path"]))
            rollover_queue_path = str(final_queue_path)

    final_audit = audit_publish_queue(
        final_queue_path,
        now=now_local,
        lead_minutes=lead_minutes,
        max_count=max_count,
        write_report=False,
    )
    packet_result = create_execution_packet(
        final_queue_path,
        now=now_local,
        lead_minutes=lead_minutes,
        max_count=max_count,
        write_output=write_output,
    )

    dry_run_result: dict[str, Any] | None = None
    dry_run_skipped_reason: str | None = None
    if skip_dry_run:
        dry_run_skipped_reason = "skip_preflight_dry_run"
    elif not final_audit.get("ready_to_schedule_after_explicit_owner_instruction"):
        dry_run_skipped_reason = str(final_audit.get("next_action") or "final_audit_not_ready")
    else:
        dry_run_result = run_publish_queue(
            final_queue_path,
            mode="dry-run",
            cdp_port=cdp_port,
            profile_dir=profile_dir,
            now=now_local,
            max_count=max_count,
            write_report=False,
        )

    preflight = {
        "ok": bool(final_audit.get("ok"))
        and bool(packet_result.get("ok"))
        and (dry_run_result is None or bool(dry_run_result.get("ok"))),
        "type": "aino_publish_queue_preflight_v1",
        "source_queue_path": str(queue_path),
        "final_queue_path": str(final_queue_path),
        "created_at_local": now_local.isoformat(),
        "initial_audit": initial_audit,
        "rollover_applied": bool(rollover_queue_path),
        "rollover": rollover_result,
        "rollover_queue_path": rollover_queue_path,
        "final_audit": final_audit,
        "packet": packet_result,
        "packet_path": packet_result.get("packet_path"),
        "packet_markdown_path": packet_result.get("packet_markdown_path"),
        "dry_run": dry_run_result,
        "dry_run_ok": bool(dry_run_result.get("ok")) if dry_run_result else None,
        "dry_run_skipped_reason": dry_run_skipped_reason,
        "tiktok_upload_performed": False,
        "schedule_click_performed": False,
        "public_posting_performed": False,
        "performance_measurement_performed": False,
    }

    if write_output:
        if output_path is None:
            stamp = now_local.strftime("%Y%m%d_%H%M%S")
            output_path = final_queue_path.parent / f"publish_queue_preflight_{stamp}.json"
        json_path = output_path.resolve()
        markdown_path = json_path.with_suffix(".md")
        json_path.write_text(json.dumps(preflight, ensure_ascii=False, indent=2), encoding="utf-8")
        markdown_path.write_text(_render_preflight_markdown(preflight), encoding="utf-8")
        preflight["preflight_path"] = str(json_path)
        preflight["preflight_markdown_path"] = str(markdown_path)
    return preflight


def _print_json(payload: dict[str, Any]) -> None:
    text = json.dumps(payload, ensure_ascii=False, indent=2)
    try:
        print(text)
    except UnicodeEncodeError:
        sys.stdout.buffer.write(text.encode("utf-8", errors="replace") + b"\n")


def _parse_now_arg(value: str | None) -> dt.datetime | None:
    if not value:
        return None
    parsed = _parse_datetime(value)
    if parsed is None:
        raise ValueError(f"Invalid --now-local value: {value}")
    return parsed


def main() -> int:
    parser = argparse.ArgumentParser(description="Run a local AiNo publish queue with safety gates.")
    parser.add_argument("--queue", type=Path, default=DEFAULT_QUEUE)
    parser.add_argument("--mode", choices=["dry-run", "prepare", "schedule", "publish"], default="dry-run")
    parser.add_argument("--cdp-port", type=int, default=int(os.environ.get("AINO_CHROME_CDP_PORT", upload_automation.DEFAULT_CDP_PORT)))
    parser.add_argument("--profile-dir", type=Path)
    parser.add_argument("--max-count", type=int)
    parser.add_argument("--now-local")
    parser.add_argument("--allow-past-slots", action="store_true")
    parser.add_argument("--confirm-external-action", action="store_true")
    parser.add_argument("--owner-instruction")
    parser.add_argument("--no-write-report", action="store_true")
    parser.add_argument("--audit", action="store_true")
    parser.add_argument("--packet", action="store_true")
    parser.add_argument("--packet-output", type=Path)
    parser.add_argument("--manual-handoff", action="store_true")
    parser.add_argument("--manual-handoff-output", type=Path)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--preflight-output", type=Path)
    parser.add_argument("--skip-preflight-dry-run", action="store_true")
    parser.add_argument("--rollover-past-slots", action="store_true")
    parser.add_argument("--rollover-output", type=Path)
    parser.add_argument("--rollover-lead-minutes", type=int, default=DEFAULT_ROLLOVER_LEAD_MINUTES)
    parser.add_argument("--slot-times-local", nargs="+", default=list(DEFAULT_SLOT_TIMES_LOCAL))
    args = parser.parse_args()
    now_local = _parse_now_arg(args.now_local)

    if args.audit:
        result = audit_publish_queue(
            args.queue,
            now=now_local,
            lead_minutes=args.rollover_lead_minutes,
            max_count=args.max_count,
            write_report=not args.no_write_report,
        )
        _print_json(result)
        return 0 if result.get("ok") else 2

    if args.packet:
        result = create_execution_packet(
            args.queue,
            output_path=args.packet_output,
            now=now_local,
            lead_minutes=args.rollover_lead_minutes,
            max_count=args.max_count,
            write_output=not args.no_write_report,
        )
        _print_json(result)
        return 0 if result.get("ok") else 2

    if args.manual_handoff:
        result = create_manual_handoff(
            args.queue,
            output_path=args.manual_handoff_output,
            now=now_local,
            lead_minutes=args.rollover_lead_minutes,
            max_count=args.max_count,
            write_output=not args.no_write_report,
        )
        _print_json(result)
        return 0 if result.get("ok") else 2

    if args.preflight:
        result = run_preflight(
            args.queue,
            output_path=args.preflight_output,
            now=now_local,
            lead_minutes=args.rollover_lead_minutes,
            max_count=args.max_count,
            cdp_port=args.cdp_port,
            profile_dir=args.profile_dir,
            skip_dry_run=args.skip_preflight_dry_run,
            write_output=not args.no_write_report,
        )
        _print_json(result)
        return 0 if result.get("ok") else 2

    if args.rollover_past_slots:
        result = rollover_publish_queue(
            args.queue,
            output_path=args.rollover_output,
            now=now_local,
            lead_minutes=args.rollover_lead_minutes,
            slot_times_local=args.slot_times_local,
            write_output=not args.no_write_report,
        )
        _print_json(result)
        return 0 if result.get("ok") else 2

    result = run_publish_queue(
        args.queue,
        mode=args.mode,
        cdp_port=args.cdp_port,
        profile_dir=args.profile_dir,
        now=now_local,
        max_count=args.max_count,
        allow_past_slots=args.allow_past_slots,
        confirm_external_action=args.confirm_external_action,
        owner_instruction=args.owner_instruction,
        write_report=not args.no_write_report,
    )
    _print_json(result)
    return 0 if result.get("ok") else 2


if __name__ == "__main__":
    raise SystemExit(main())
