# -*- coding: utf-8 -*-
"""
Jarvis Worker Dispatch — lane → CLI 워커 호출 + 증거 기반 실행 진실 (ledger.tool_runs)

설계: 20260524_JARVIS_ARCHITECTURE_v2.md §4 / §0.6 / §0.7
검증된 라우팅: code=Codex CLI / design=Claude CLI(절약·비판) / chat=로컬 L1 / image·video=ComfyUI.
인증(검증): 공식 `claude`/`codex` CLI 바이너리 subprocess(구독 OAuth, ToS OK), raw 종량 API 키 미사용.

증거 게이트: dispatch 후 tool_runs 기록 → exit_code=0 + output_hash 있을 때만 "실행 완료" 보고 가능.
runner 주입 가능 → 라이브 CLI 호출 없이 테스트(섀도).
"""
from __future__ import annotations

import hashlib
import os
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "queue"))
sys.path.insert(0, str(Path(__file__).resolve().parents[0]))
import sqlite_ledger as ledger  # type: ignore  # noqa: E402
from command_router import Lane  # type: ignore  # noqa: E402

# Phase A 적대적 파트너(devil's advocate) — Claude 설계/리뷰 워커 system prompt 주입
CRITIC_SYSTEM = (
    "당신은 principal engineer다. 모든 제안에서 결함·리스크·더 단순한 대안 3가지를 먼저 찾아라. "
    "검증(validate)하지 말고 반증(refute)하라. owner가 명시 승인하기 전엔 동의하지 말 것."
)

_CODEX_MODEL = os.getenv("SORA_CODEX_MODEL", "")
_CLAUDE_MODEL = os.getenv("JARVIS_CLAUDE_MODEL", "")
_L1_MODEL = os.getenv("JARVIS_L1_MODEL", "qwen2.5:3b")


@dataclass
class RunResult:
    returncode: int
    stdout: str = ""
    stderr: str = ""


def build_worker_command(lane: Lane, prompt: str) -> Optional[list[str]]:
    """lane → 비대화형 CLI argv. None = CLI 아님(예: device/approval은 별도 경로)."""
    if lane == Lane.CODE:
        cmd = ["codex", "exec", "--json", "--sandbox", "workspace-write",
               "--ask-for-approval", "never"]
        if _CODEX_MODEL:
            cmd += ["-m", _CODEX_MODEL]
        cmd.append(prompt)
        return cmd
    if lane == Lane.DESIGN:
        # 주의(라이브 검증): `--bare`는 구독 OAuth 인증을 건너뛰어 "Not logged in" 유발 → 사용 금지.
        # 비용: --bare 없으면 cwd의 CLAUDE.md 를 로드(135K tok). 워커는 JARVIS_WORKER_CWD(깨끗한 dir)에서 실행 권장.
        cmd = ["claude", "-p", "--output-format", "json",
               "--dangerously-skip-permissions", "--append-system-prompt", CRITIC_SYSTEM]
        if _CLAUDE_MODEL:
            cmd += ["--model", _CLAUDE_MODEL]
        cmd.append(prompt)
        return cmd
    if lane == Lane.CHAT:
        # 로컬 L1 (Ollama). 클라우드 escalation 은 :cloud 모델로 model 만 교체.
        return ["ollama", "run", _L1_MODEL, prompt]
    if lane in (Lane.IMAGE, Lane.VIDEO):
        # ComfyUI 는 CLI 아님 → 별도 워커 큐 (여기선 미지원 표식)
        return None
    return None


def _real_runner(cmd: list[str], timeout: int = 300) -> RunResult:
    # stdin=DEVNULL: 비대화형 CLI 의 "no stdin" 3초 대기 제거.
    # cwd: JARVIS_WORKER_CWD(깨끗한 dir) 지정 시 CLAUDE.md 컨텍스트 로드 비용 회피.
    cwd = os.getenv("JARVIS_WORKER_CWD") or None
    # encoding=utf-8: Windows 기본 cp949 디코드가 UTF-8(한국어/이모지) CLI 출력을 깨뜨리는 버그 방지.
    p = subprocess.run(cmd, capture_output=True, encoding="utf-8", errors="replace",
                       timeout=timeout, shell=False, stdin=subprocess.DEVNULL, cwd=cwd)
    return RunResult(returncode=p.returncode, stdout=p.stdout or "", stderr=p.stderr or "")


def _hash(s: str) -> str:
    return hashlib.sha256((s or "").encode("utf-8")).hexdigest()[:32]


def dispatch(conn, *, job_id: str, lane: Lane, prompt: str,
             runner: Callable[[list[str]], RunResult] = _real_runner,
             dry_run: bool = False) -> dict:
    """워커 호출 + tool_runs 증거 기록. runner 주입으로 섀도 테스트 가능.

    반환: {tool, status, exit_code, can_report_success}
    """
    cmd = build_worker_command(lane, prompt)
    if cmd is None:
        ledger.record_tool_run(conn, job_id=job_id, tool_name=f"lane:{lane.value}",
                               status="blocked", exit_code=None)
        return {"tool": None, "status": "blocked", "exit_code": None,
                "can_report_success": False, "reason": f"{lane.value} 워커 미지원(CLI 아님)"}
    tool = cmd[0]
    if dry_run:
        ledger.record_tool_run(conn, job_id=job_id, tool_name=tool, status="planned")
        return {"tool": tool, "status": "planned", "exit_code": None,
                "can_report_success": False, "cmd": cmd}
    try:
        res = runner(cmd)
    except Exception as e:  # 실행 자체 실패
        ledger.record_tool_run(conn, job_id=job_id, tool_name=tool, status="failed", exit_code=-1)
        return {"tool": tool, "status": "failed", "exit_code": -1,
                "can_report_success": False, "reason": str(e)}
    ok = res.returncode == 0
    ledger.record_tool_run(
        conn, job_id=job_id, tool_name=tool,
        status="succeeded" if ok else "failed",
        exit_code=res.returncode,
        output_hash=_hash(res.stdout) if ok else None,
    )
    return {"tool": tool, "status": "succeeded" if ok else "failed",
            "exit_code": res.returncode,
            "can_report_success": ledger.can_report_success(conn, job_id=job_id),
            "stdout": res.stdout}
