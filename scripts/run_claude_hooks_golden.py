#!/usr/bin/env python3
"""Run Claude Code hook golden tests.

The hooks live under the owner's home directory because Claude Code executes
them from global runtime settings. This runner verifies both the settings
contract and the file-backed hook behavior without requiring Claude Code to run.
"""
from __future__ import annotations

import argparse
import json
import os
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path
from typing import Any

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SUITE = REPO_ROOT / "tests" / "hooks_golden" / "core_v1.json"
HOME = Path(os.environ.get("USERPROFILE") or Path.home())
CLAUDE_DIR = HOME / ".claude"
HOOK_DIR = CLAUDE_DIR / "hooks"
SETTINGS_PATH = CLAUDE_DIR / "settings.json"


@dataclass
class Result:
    test_id: str
    status: str
    severity: str
    detail: str = ""


def _load_suite(path: Path) -> dict[str, Any]:
    # utf-8-sig 로 읽어 Windows PowerShell 의 UTF-8 BOM (Out-File 기본) 도 안전 파싱
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _run_hook(hook: str, stdin_payload: str, timeout_s: int = 30, env_overrides: dict[str, str] | None = None) -> subprocess.CompletedProcess[str]:
    """Run a PowerShell hook with stdin. 30s timeout per test (prompt spec)."""
    hook_path = HOOK_DIR / hook
    env = os.environ.copy()
    if env_overrides:
        env.update(env_overrides)
    return subprocess.run(
        ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-File", str(hook_path)],
        input=stdin_payload,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
        timeout=timeout_s,
        env=env,
    )


def _expand_templates(value: Any) -> Any:
    if isinstance(value, dict):
        return {k: _expand_templates(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_expand_templates(v) for v in value]
    if value == "__FAKE_TELEGRAM_TOKEN__":
        return "123456789:" + ("A" * 35)
    return value


def _case_settings_events(case: dict[str, Any]) -> Result:
    settings = json.loads(SETTINGS_PATH.read_text(encoding="utf-8"))
    actual = sorted((settings.get("hooks") or {}).keys())
    expected = sorted(case["expected_events"])
    ok = actual == expected
    return Result(
        case["id"],
        "PASS" if ok else "FAIL",
        case["severity"],
        f"expected={expected}; actual={actual}",
    )


def _case_hook_files_exist(case: dict[str, Any]) -> Result:
    missing = [name for name in case["expected_files"] if not (HOOK_DIR / name).exists()]
    return Result(
        case["id"],
        "PASS" if not missing else "FAIL",
        case["severity"],
        "missing=" + ",".join(missing) if missing else "all file-backed hooks exist",
    )


def _case_hook_exit(case: dict[str, Any]) -> Result:
    if "stdin_raw" in case:
        stdin_payload = case["stdin_raw"]
    else:
        stdin_payload = json.dumps(_expand_templates(case.get("stdin", {})), ensure_ascii=False)

    # 격리된 audit dir — 실 운영 ~/.claude/audit 무영향 보장
    # CLAUDE_AUDIT_DIR env 가 모든 8 hooks 의 audit path 를 우선 결정 (fallback = USERPROFILE\.claude\audit)
    with tempfile.TemporaryDirectory(prefix="hook_golden_audit_") as tmp_audit:
        env_overrides = dict(case.get("env_overrides", {}))
        env_overrides.setdefault("CLAUDE_AUDIT_DIR", tmp_audit)

        try:
            proc = _run_hook(case["hook"], stdin_payload, env_overrides=env_overrides)
        except Exception as exc:  # pragma: no cover - failure detail for local runner
            return Result(case["id"], "FAIL", case["severity"], f"{type(exc).__name__}: {exc}")

        expected_exit = int(case.get("expect_exit", 0))
        stdout = proc.stdout or ""
        stderr = proc.stderr or ""
        ok = proc.returncode == expected_exit
        for needle in case.get("stdout_contains", []):
            ok = ok and needle in stdout
        for needle in case.get("stdout_not_contains", []):
            ok = ok and needle not in stdout

        # 선택: expected_audit_files 검증 — case 가 audit log 파일 생성을 요구하면 검사
        for expected_file_glob in case.get("expected_audit_files", []):
            matches = list(Path(tmp_audit).glob(expected_file_glob))
            if not matches:
                ok = False
                stderr = f"missing audit file matching '{expected_file_glob}' in {tmp_audit}\n" + stderr

        detail = (
            f"exit={proc.returncode}, expected_exit={expected_exit}, "
            f"stdout={stdout[:180]!r}, stderr={stderr[:180]!r}"
        )
    return Result(case["id"], "PASS" if ok else "FAIL", case["severity"], detail)


def _case_static_contains(case: dict[str, Any]) -> Result:
    content = (HOOK_DIR / case["hook"]).read_text(encoding="utf-8")
    missing = [needle for needle in case["contains"] if needle not in content]
    return Result(
        case["id"],
        "PASS" if not missing else "FAIL",
        case["severity"],
        "missing=" + ",".join(missing) if missing else "all static markers present",
    )


def _execute(case: dict[str, Any]) -> Result:
    case_type = case["type"]
    if case_type == "settings_events":
        return _case_settings_events(case)
    if case_type == "hook_files_exist":
        return _case_hook_files_exist(case)
    if case_type == "hook_exit":
        return _case_hook_exit(case)
    if case_type == "static_contains":
        return _case_static_contains(case)
    return Result(case["id"], "FAIL", case.get("severity", "P2"), f"unknown type: {case_type}")


def _format(results: list[Result]) -> str:
    counts = {"PASS": 0, "FAIL": 0}
    for result in results:
        counts[result.status] = counts.get(result.status, 0) + 1

    lines = [
        "=" * 70,
        " Claude Hooks Golden - core_v1",
        "=" * 70,
        f" Total: {len(results)} | PASS={counts.get('PASS', 0)} | FAIL={counts.get('FAIL', 0)}",
        "-" * 70,
    ]
    for result in results:
        marker = "OK" if result.status == "PASS" else "FAIL"
        lines.append(f" [{marker}] [{result.severity}] {result.test_id}: {result.detail}")
    lines.append("=" * 70)
    return "\n".join(lines)


def main(argv: list[str]) -> int:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="Run Claude hooks golden tests")
    parser.add_argument("--suite", default=str(DEFAULT_SUITE))
    parser.add_argument("--report", choices=["text", "json"], default="text")
    args = parser.parse_args(argv)

    suite = _load_suite(Path(args.suite))
    results = [_execute(case) for case in suite.get("tests", [])]

    declared = suite.get("total_count")
    if declared is not None and declared != len(results):
        results.insert(0, Result("SUITE_TOTAL", "FAIL", "P0", f"declared={declared}, actual={len(results)}"))

    if args.report == "json":
        print(json.dumps([result.__dict__ for result in results], ensure_ascii=False, indent=2))
    else:
        print(_format(results))

    return 1 if any(result.status == "FAIL" for result in results) else 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv[1:]))
