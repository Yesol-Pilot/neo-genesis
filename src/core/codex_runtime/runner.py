# -*- coding: utf-8 -*-
"""Run Codex CLI safely for Sora."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
import time
from dataclasses import dataclass
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
RUNTIME_DIR = PROJECT_ROOT / "src" / "core" / "data" / "assistant_memory" / "codex_runtime"
RUNTIME_DIR.mkdir(parents=True, exist_ok=True)

WRITE_KEYWORDS = (
    "수정", "변경", "고쳐", "만들", "추가", "작성", "삭제",
    "배포", "커밋", "push", "rename", "move", "실행",
)


def _build_command(base_args: list[str]) -> list[str]:
    codex_bin = os.getenv("SORA_CODEX_CLI", "codex")

    if os.name != "nt":
        return [codex_bin, *base_args]

    resolved = shutil.which(codex_bin) or codex_bin
    if str(resolved).lower().endswith(".ps1"):
        basedir = Path(str(resolved)).resolve().parent
        node_exe = basedir / "node.exe"
        codex_js = basedir / "node_modules" / "@openai" / "codex" / "bin" / "codex.js"
        if node_exe.exists() and codex_js.exists():
            return [str(node_exe), str(codex_js), *base_args]
        return [
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-File",
            str(resolved),
            *base_args,
        ]
    return [str(resolved), *base_args]


@dataclass
class CodexRunResult:
    reply: str
    thread_id: str
    duration_ms: int
    sandbox: str
    stderr_summary: str = ""


def _infer_sandbox(user_text: str, file_path: str = "") -> str:
    haystack = f"{user_text}\n{file_path}".lower()
    if any(keyword in haystack for keyword in WRITE_KEYWORDS):
        return "workspace-write"
    return "read-only"


def _summarize_stderr(stderr: str) -> str:
    if not stderr:
        return ""
    ignore_markers = (
        "plugins::",
        "state db",
        "shell snapshot",
        "worker quit with fatal",
        "<html>",
        "<head>",
        "<body>",
        "<style",
        "<script",
        "cloudflare",
        "chatgpt.com/backend-api/plugins",
    )
    lines = []
    for raw_line in stderr.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.startswith("<"):
            continue
        if any(marker in line for marker in ignore_markers):
            continue
        lines.append(line)
    return "\n".join(lines[:8])[:1200]


def _extract_reply_from_jsonl(stdout: str) -> tuple[str, str]:
    reply = ""
    thread_id = ""
    for raw_line in stdout.splitlines():
        line = raw_line.strip()
        if not line or not line.startswith("{"):
            continue
        try:
            event = json.loads(line)
        except json.JSONDecodeError:
            continue
        if event.get("type") == "thread.started":
            thread_id = event.get("thread_id", thread_id)
        item = event.get("item") or {}
        if item.get("type") == "agent_message" and item.get("text"):
            reply = str(item["text"]).strip()
    return reply, thread_id


def summarize_codex_failure(stderr: str, returncode: int) -> str:
    summary = _summarize_stderr(stderr)
    if summary:
        return f"Codex 실행 실패 (exit={returncode})\n{summary}"
    return f"Codex 실행 실패 (exit={returncode})"


def run_codex_request(
    *,
    prompt: str,
    user_text: str,
    file_path: str = "",
) -> CodexRunResult:
    model = os.getenv("SORA_CODEX_MODEL", "").strip()
    timeout_sec = int(os.getenv("SORA_CODEX_TIMEOUT_SEC", "180"))
    sandbox = _infer_sandbox(user_text, file_path=file_path)

    with tempfile.NamedTemporaryFile(delete=False, suffix=".txt") as temp_file:
        output_path = Path(temp_file.name)
    prompt_path = RUNTIME_DIR / f"prompt_{int(time.time() * 1000)}.md"
    prompt_path.write_text(prompt, encoding="utf-8")

    command = _build_command([
        "exec",
        "--skip-git-repo-check",
        "--ephemeral",
        "--json",
        "--color",
        "never",
        "--sandbox",
        sandbox,
        "-C",
        str(PROJECT_ROOT),
        "-o",
        str(output_path),
    ])
    if model:
        command.extend(["-m", model])
    command.append(
        (
            "You are executing as Sora. "
            f"Read the UTF-8 request bundle at '{prompt_path.as_posix()}' "
            "and follow it as the sole request/context source. "
            "Reply to the end user in Korean only. "
            "Do not mention internal file paths or internal runtime details."
        )
    )

    started_at = time.time()
    completed = subprocess.run(
        command,
        cwd=str(PROJECT_ROOT),
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_sec,
    )
    duration_ms = int((time.time() - started_at) * 1000)

    reply, thread_id = _extract_reply_from_jsonl(completed.stdout)
    stderr_summary = _summarize_stderr(completed.stderr) if completed.returncode != 0 else ""

    if not reply and output_path.exists():
        reply = output_path.read_text(encoding="utf-8", errors="ignore").strip()

    try:
        output_path.unlink(missing_ok=True)
    except Exception:
        pass
    try:
        prompt_path.unlink(missing_ok=True)
    except Exception:
        pass

    if completed.returncode != 0:
        raise RuntimeError(summarize_codex_failure(completed.stderr, completed.returncode))

    if not reply:
        raise RuntimeError("Codex가 빈 응답을 반환했습니다.")

    return CodexRunResult(
        reply=reply,
        thread_id=thread_id,
        duration_ms=duration_ms,
        sandbox=sandbox,
        stderr_summary=stderr_summary,
    )
