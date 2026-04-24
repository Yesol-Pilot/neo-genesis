# -*- coding: utf-8 -*-
"""Best-effort single-instance helpers for long-running Neo Genesis services."""
from __future__ import annotations

import atexit
import os
from pathlib import Path

try:
    import psutil
except ImportError:  # pragma: no cover - runtime fallback
    psutil = None

_REGISTERED_CLEANUPS: set[tuple[str, int]] = set()


def _normalize_matchers(matchers: list[str] | tuple[str, ...]) -> tuple[str, ...]:
    return tuple(m.strip().lower() for m in matchers if str(m).strip())


def _is_python_process(cmdline: list[str]) -> bool:
    if not cmdline:
        return False
    executable = Path(cmdline[0]).name.lower()
    return executable.startswith("python") or executable == "py"


def _matches_process(cmdline: list[str], matchers: tuple[str, ...]) -> bool:
    if not _is_python_process(cmdline):
        return False
    joined = " ".join(cmdline).lower()
    return any(matcher in joined for matcher in matchers)


def list_matching_processes(
    matchers: list[str] | tuple[str, ...],
    *,
    exclude_pid: int | None = None,
) -> list[dict]:
    """Return live Python processes whose command line matches any marker."""
    if psutil is None:
        return []

    normalized = _normalize_matchers(matchers)
    if not normalized:
        return []

    matches: list[dict] = []
    for process in psutil.process_iter(["pid", "cmdline"]):
        pid = process.info.get("pid")
        if exclude_pid is not None and pid == exclude_pid:
            continue
        cmdline = process.info.get("cmdline") or []
        if _matches_process(cmdline, normalized):
            matches.append({"pid": pid, "cmdline": cmdline})
    return matches


def _pid_matches(pid: int, matchers: tuple[str, ...]) -> bool:
    if psutil is None or pid <= 0:
        return False
    try:
        process = psutil.Process(pid)
        return _matches_process(process.cmdline(), matchers)
    except (psutil.Error, OSError):
        return False


def _read_pid(lock_path: Path) -> int | None:
    try:
        raw = lock_path.read_text(encoding="utf-8").strip()
        return int(raw) if raw else None
    except (OSError, ValueError):
        return None


def release_single_instance(lock_path: str | Path, current_pid: int | None = None) -> None:
    """Delete the lock file only if it belongs to the current process."""
    path = Path(lock_path)
    owner_pid = _read_pid(path)
    current_pid = current_pid or os.getpid()
    if owner_pid not in (None, current_pid):
        return
    try:
        path.unlink()
    except FileNotFoundError:
        return
    except OSError:
        return


def _register_cleanup(lock_path: Path, current_pid: int) -> None:
    key = (str(lock_path), current_pid)
    if key in _REGISTERED_CLEANUPS:
        return
    atexit.register(release_single_instance, lock_path, current_pid)
    _REGISTERED_CLEANUPS.add(key)


def claim_single_instance(
    lock_path: str | Path,
    matchers: list[str] | tuple[str, ...],
    *,
    current_pid: int | None = None,
) -> tuple[bool, str]:
    """Claim a PID file for a long-running process.

    The lock is best-effort: it first scans live Python processes, then falls
    back to the PID file for stale-lock cleanup.
    """
    path = Path(lock_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    current_pid = current_pid or os.getpid()
    normalized = _normalize_matchers(matchers)
    if not normalized:
        raise ValueError("single-instance matchers are required")

    live_matches = list_matching_processes(normalized, exclude_pid=current_pid)
    if live_matches:
        pid = live_matches[0]["pid"]
        return False, f"이미 실행 중인 인스턴스 감지 (PID {pid})"

    existing_pid = _read_pid(path)
    if existing_pid == current_pid:
        _register_cleanup(path, current_pid)
        return True, f"현재 프로세스가 이미 락 보유 (PID {current_pid})"

    if existing_pid and _pid_matches(existing_pid, normalized):
        return False, f"PID 파일이 살아있는 인스턴스를 가리킴 (PID {existing_pid})"

    if path.exists():
        release_single_instance(path, existing_pid or current_pid)

    try:
        with path.open("x", encoding="utf-8") as handle:
            handle.write(str(current_pid))
    except FileExistsError:
        existing_pid = _read_pid(path)
        if existing_pid and existing_pid != current_pid and _pid_matches(existing_pid, normalized):
            return False, f"경합 중인 인스턴스 감지 (PID {existing_pid})"
        live_matches = list_matching_processes(normalized, exclude_pid=current_pid)
        if live_matches:
            pid = live_matches[0]["pid"]
            return False, f"경합 중인 인스턴스 감지 (PID {pid})"
        try:
            path.unlink()
        except OSError:
            pass
        with path.open("x", encoding="utf-8") as handle:
            handle.write(str(current_pid))

    _register_cleanup(path, current_pid)
    return True, f"단일 인스턴스 락 확보 ({path.name})"
