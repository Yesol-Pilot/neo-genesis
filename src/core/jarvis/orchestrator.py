# -*- coding: utf-8 -*-
"""
Jarvis Orchestrator — 전 파이프라인 (게이트 → 라우팅 → 2-Phase 거버넌스 → 워커 → 증거보고)

설계: 20260524_JARVIS_ARCHITECTURE_v2.md §2(2-Phase Sovereignty) / §3 / §0.6 / §0.7
"기본 호출자 = 오케스트레이터" (Hermes도 CLI도 아님). 섀도 빌드 — 라이브 telegram/agent_router 무변경.

흐름:
  1) gateway_guard.check_inbound  : owner allowlist + dedup + rate-limit (LLM 前)
  2) command_router.route         : 결정론 lane 분류 (LLM 미사용)
  3) Phase A/B 거버넌스:
     - APPROVAL  → 보류 작업 승인(decide_approval) → 실행
     - DANGEROUS(challenge) → 모호한 위험: 재입력 요구, 실행 X
     - DANGEROUS(explicit)  → waiting_approval 작업 + confirm_id 발급(warn-then-obey, 실행 X)
     - DEVICE_COMMAND       → hub 경로(여기선 표식)
     - 그 외(code/design/chat) → enqueue → claim → worker_dispatch → 증거게이트 보고
  4) 보고: tool_runs 증거 없으면 "실행 완료" 금지 (환각 차단)
"""
from __future__ import annotations

import hashlib
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "queue"))
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
import sqlite_ledger as ledger  # type: ignore  # noqa: E402
import gateway_guard as gw  # type: ignore  # noqa: E402
import command_router as cr  # type: ignore  # noqa: E402
import worker_dispatch as wd  # type: ignore  # noqa: E402


def _action_hash(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def handle_message(conn, *, source: str, update_id: str, chat_id: str, user_id: str,
                   text: str, owner_chat_id: str,
                   runner=wd._real_runner, dry_run: bool = False) -> dict:
    """텔레그램/슬랙 인입 1건 처리. 반환 dict(action/lane/report/...)."""
    # 1) 게이트 (LLM 前)
    gd = gw.check_inbound(conn, source=source, update_id=update_id, chat_id=chat_id,
                          user_id=user_id, text=text, owner_chat_id=owner_chat_id)
    if gd.action != gw.Action.ACCEPT:
        return {"action": gd.action.value, "report": gd.reason, "request_id": gd.request_id}

    # 2) 결정론 라우팅
    rd = cr.route(text)

    # 3) 거버넌스
    # 3a) 승인: 보류된 waiting_approval 작업을 찾아 승인 → 실행
    if rd.lane == cr.Lane.APPROVAL:
        row = conn.execute(
            "SELECT j.job_id, j.command, a.approval_id FROM jobs j "
            "JOIN approvals a ON a.job_id=j.job_id "
            "WHERE j.chat_id=? AND j.status='waiting_approval' AND a.state='requested' "
            "ORDER BY j.created_at DESC LIMIT 1", (str(chat_id),)).fetchone()
        if row is None:
            return {"action": "approval", "lane": rd.lane.value, "report": "보류 중인 위험 작업이 없습니다."}
        # 실 confirm_id 매칭은 inline button 경유 (여기선 텍스트 '진행' → 최근 1건 승인)
        # decide_approval 은 confirm_id 검증 포함 — 텍스트 경로는 owner 단독이므로 job 기준 승인 처리
        with ledger.immediate_tx(conn):
            conn.execute("UPDATE approvals SET state='approved', decided_at=strftime('%s','now') WHERE approval_id=?", (row["approval_id"],))
            conn.execute("UPDATE jobs SET status='queued' WHERE job_id=?", (row["job_id"],))
            ledger.audit(conn, actor=str(user_id), event_type="approval_approved",
                         job_id=row["job_id"], decision="approved")
        return _run_job(conn, job_id=row["job_id"], text=row["command"], runner=runner, dry_run=dry_run,
                        extra={"action": "approved_executed"})

    # 3b) 모호한 위험 → 재입력 강제 (실행 X)
    if rd.lane == cr.Lane.DANGEROUS and rd.challenge:
        return {"action": "challenge", "lane": rd.lane.value, "risk": "dangerous",
                "report": rd.challenge, "reason": rd.reason}

    # 3c) 명시 위험 → waiting_approval 작업 + confirm_id (warn-then-obey Phase A)
    if rd.lane == cr.Lane.DANGEROUS:
        job_id = ledger.enqueue(conn, source=source, title="위험 명령 보류", command=text,
                                chat_id=str(chat_id), risk_tier="G3", status="waiting_approval")
        approval_id, confirm_id = ledger.request_approval(
            conn, chat_id=str(chat_id), user_id=str(user_id), action_hash=_action_hash(text),
            summary=rd.reason or "위험 명령", risk_tier="G3", job_id=job_id)
        return {"action": "warn", "lane": rd.lane.value, "risk": "dangerous", "job_id": job_id,
                "confirm_id": confirm_id,
                "report": (f"⚠️ 위험: {rd.reason}\n권고: {rd.recommendation}\n"
                           f"그래도 실행하려면 '진행' 또는 inline 승인 버튼. (60초)")}

    # 3d) 디바이스 명령 (hub 경로)
    if rd.lane == cr.Lane.DEVICE_COMMAND:
        return {"action": "device_command", "lane": rd.lane.value,
                "device_phrase": rd.meta.get("device_phrase"), "command": rd.meta.get("command"),
                "report": f"[hub] {rd.meta.get('device_phrase')} → {rd.meta.get('command')} (governor 경유 실행)"}

    # 3e) 일반(code/design/chat) → enqueue → 실행
    job_id = ledger.enqueue(conn, source=source, title=text[:60], command=text,
                            chat_id=str(chat_id), risk_tier="G1")
    return _run_job(conn, job_id=job_id, text=text, runner=runner, dry_run=dry_run,
                    lane=rd.lane, suggested_engine=rd.suggested_engine,
                    extra={"action": "executed", "lane": rd.lane.value, "engine": rd.suggested_engine})


def _run_job(conn, *, job_id: str, text: str, runner, dry_run: bool,
             lane=None, suggested_engine="", extra=None) -> dict:
    """claim → dispatch → 증거게이트 보고."""
    if lane is None:
        lane = cr.route(text).lane
    if ledger.is_kill_active(conn):
        return {"action": "frozen", "report": "🛑 kill switch 활성 — 실행 거부", "job_id": job_id}
    claim = ledger.claim(conn, worker_id="orchestrator")
    if claim is None:
        return {"action": "no_claim", "report": "작업 claim 실패(kill 또는 경쟁)", "job_id": job_id}
    disp = wd.dispatch(conn, job_id=claim.job_id, lane=lane, prompt=text, runner=runner, dry_run=dry_run)
    # 증거 게이트: tool_runs 근거 있을 때만 succeeded
    if disp.get("can_report_success"):
        ledger.complete(conn, job_id=claim.job_id, worker_id="orchestrator",
                        fencing_token=claim.fencing_token, lease_epoch=claim.lease_epoch,
                        status="succeeded", result_summary=disp.get("status", ""))
        report = f"✅ 실행 완료 ({disp.get('tool')})"
    else:
        ledger.complete(conn, job_id=claim.job_id, worker_id="orchestrator",
                        fencing_token=claim.fencing_token, lease_epoch=claim.lease_epoch,
                        status="failed", error_summary=disp.get("status", ""))
        report = f"⚠️ 실행 시도/실패 — 증거 없음 (status={disp.get('status')}, exit={disp.get('exit_code')})"
    out = {"job_id": claim.job_id, "report": report, "dispatch": disp}
    out.update(extra or {})
    return out
