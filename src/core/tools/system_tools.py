# -*- coding: utf-8 -*-
"""시스템/PC 관련 도구 — Phase 1-1 모듈화"""
import json
import logging
import os
import re
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent
PROFIT_ROOT = PROJECT_ROOT / "src" / "sbu" / "profit_center" / "profit"
load_dotenv(PROJECT_ROOT / ".env")

logger = logging.getLogger("neo.jarvis")

# 클라우드 모드 감지 (GCP 등 원격 서버에서 실행 시)
CLOUD_MODE = os.getenv("SORA_CLOUD_MODE", "").lower() in ("1", "true")
IS_LINUX = sys.platform.startswith("linux")


def run_daemon_job(job_name: str) -> str:
    """데몬 Job을 즉시 실행합니다.

    Args:
        job_name: 실행할 Job. 가능한 값: audit, harvest, blog, farm,
            report, godel, hive_cron, hive_orchestrator,
            toolpick_hive, cross_sync, morning_report, evening_report
    """
    valid = ["audit", "harvest", "blog", "farm", "report", "godel",
             "hive_cron", "hive_orchestrator", "toolpick_hive",
             "cross_sync", "morning_report", "evening_report"]
    if job_name not in valid:
        return json.dumps({"error": f"알 수 없는 Job: {job_name}", "valid": valid})

    try:
        result = subprocess.run(
            [sys.executable, str(PROJECT_ROOT / "neo_genesis_daemon.py"),
             "--once", job_name],
            capture_output=True, text=True, timeout=300,
            cwd=str(PROJECT_ROOT),
        )
        return json.dumps({
            "status": "success" if result.returncode == 0 else "failed",
            "output": result.stdout[-500:] if result.stdout else "",
            "error": result.stderr[-300:] if result.stderr else "",
        }, ensure_ascii=False)
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "timeout", "message": "5분 초과"})
    except Exception as e:
        return json.dumps({"status": "error", "message": str(e)})


def get_system_status() -> str:
    """전체 시스템 상태를 조회합니다. 헬스 모니터, 프로세스, 디스크 등."""
    status = {}
    status["cloud_mode"] = CLOUD_MODE

    health_file = PROJECT_ROOT / "src" / "core" / "data" / "health_state.json"
    if health_file.exists():
        try:
            status["health"] = json.loads(health_file.read_text(encoding="utf-8"))
        except Exception:
            status["health"] = "파일 읽기 실패"
    else:
        status["health"] = "헬스 파일 없음"

    if IS_LINUX:
        # 클라우드/Linux: psutil 기반 시스템 상태
        try:
            import psutil
            mem = psutil.virtual_memory()
            disk = psutil.disk_usage("/")
            status["cpu_percent"] = psutil.cpu_percent(interval=1)
            status["memory"] = f"사용 {mem.used / (1024**3):.1f}GB / 전체 {mem.total / (1024**3):.1f}GB ({mem.percent}%)"
            status["disk"] = f"사용 {disk.used / (1024**3):.1f}GB / 여유 {disk.free / (1024**3):.1f}GB"
            status["python_processes"] = len([p for p in psutil.process_iter(['name']) if 'python' in (p.info['name'] or '').lower()])
        except Exception as e:
            status["system_info"] = f"psutil 조회 실패: {e}"
    else:
        # Windows: PowerShell 기반
        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "Get-Process pythonw -ErrorAction SilentlyContinue | "
                 "Select-Object Id,CPU,WorkingSet64 | ConvertTo-Json"],
                capture_output=True, text=True, timeout=10,
            )
            if r.stdout.strip():
                status["daemon_process"] = json.loads(r.stdout)
            else:
                status["daemon_process"] = "실행 중이지 않음"
        except Exception:
            status["daemon_process"] = "확인 실패"

        try:
            r = subprocess.run(
                ["powershell", "-Command",
                 "Get-PSDrive D | Select-Object Used,Free | ConvertTo-Json"],
                capture_output=True, text=True, timeout=5,
            )
            if r.stdout.strip():
                disk = json.loads(r.stdout)
                free_gb = disk.get("Free", 0) / (1024**3)
                used_gb = disk.get("Used", 0) / (1024**3)
                status["disk_D"] = f"사용 {used_gb:.1f}GB / 여유 {free_gb:.1f}GB"
        except Exception:
            pass

    return json.dumps(status, ensure_ascii=False, default=str)


def get_today_schedule() -> str:
    """**SBU 데몬 운영 스케줄** 전체를 반환합니다 (owner 본인 일정 아님).

    이 도구는 Neo Genesis 데몬의 cron 스케줄 (ReviewLab/ToolPick/UR WRONG 등 SBU 운영 job)
    을 반환합니다. owner 본인의 캘린더 일정을 요청받으면 calendar_today 도구를 쓰세요.
    """
    schedule = [
        ("06:00", "감사국 정기 감사"),
        ("07:00", "리워드 수확기"),
        ("08:00", "ReviewLab 블로그 포스팅 #1"),
        ("08:30", "ToolPick HIVE MIND"),
        ("08:50", "업무 개시 보고"),
        ("09:00", "UR WRONG 크론 (배틀 생성)"),
        ("10:00", "HIVE MIND 오케스트레이터"),
        ("14:00", "ReviewLab 블로그 포스팅 #2"),
        ("14:30", "ToolPick HIVE MIND"),
        ("15:00", "UR WRONG 크론"),
        ("16:00", "HIVE MIND 오케스트레이터"),
        ("17:50", "업무 종료 보고"),
        ("18:00", "에어드롭 파밍"),
        ("20:30", "ToolPick HIVE MIND"),
        ("21:00", "UR WRONG 크론"),
        ("22:00", "일일 종합 리포트"),
    ]
    now = datetime.now().strftime("%H:%M")
    result = {"current_time": now, "schedule": []}
    for t, name in schedule:
        done = t < now
        result["schedule"].append({
            "time": t, "job": name,
            "status": "완료" if done else "대기"
        })
    return json.dumps(result, ensure_ascii=False)


def read_recent_logs(lines: int = 40) -> str:
    """데몬 로그 파일의 최근 N줄을 읽습니다.

    Args:
        lines: 읽을 줄 수 (기본 40, 최대 100)
    """
    lines = min(lines, 100)
    log_file = PROFIT_ROOT / "logs" / "daemon.log"
    if not log_file.exists():
        return json.dumps({"error": "로그 파일 없음"})
    try:
        all_lines = log_file.read_text(encoding="utf-8", errors="ignore").splitlines()
        recent = all_lines[-lines:]
        return json.dumps({
            "total_lines": len(all_lines),
            "showing": len(recent),
            "logs": "\n".join(recent),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)})


def run_pc_command(command: str) -> str:
    """서버에서 셸 명령을 실행합니다. (Windows: PowerShell, Linux: bash)

    Args:
        command: 실행할 명령어
    """
    dangerous = ["rm -rf", "format", "del /s", "Remove-Item -Recurse /",
                 "Stop-Computer", "Restart-Computer", "mkfs", "dd if="]
    for d in dangerous:
        if d.lower() in command.lower():
            return json.dumps({"error": f"위험 명령 차단됨: {d}"})

    pc_timeout = int(os.getenv("PC_CMD_TIMEOUT", "60"))

    if IS_LINUX:
        # 클라우드/Linux: bash 사용
        try:
            result = subprocess.run(
                ["bash", "-c", command],
                capture_output=True, text=True, timeout=pc_timeout,
                cwd=str(PROJECT_ROOT),
                encoding="utf-8", errors="replace",
            )
            return json.dumps({
                "exit_code": result.returncode,
                "stdout": result.stdout[-1000:] if result.stdout else "",
                "stderr": result.stderr[-500:] if result.stderr else "",
                "shell": "bash (cloud)",
            }, ensure_ascii=False)
        except subprocess.TimeoutExpired:
            return json.dumps({"error": f"명령 실행 {pc_timeout}초 초과"})
        except Exception as e:
            return json.dumps({"error": str(e)})
    else:
        # Windows: PowerShell
        # Phase -1 C7: PowerShell && → ; 자동 치환 (글로벌 룰 #9)
        if "&&" in command:
            command = command.replace("&&", ";")
            logger.info(f"[PC] '&&' → ';' 자동 치환 적용: {command[:100]}")

        try:
            result = subprocess.run(
                ["powershell", "-Command", command],
                capture_output=True, text=True, timeout=pc_timeout,
                cwd=str(PROJECT_ROOT),
                encoding="utf-8", errors="replace",
            )
            return json.dumps({
                "exit_code": result.returncode,
                "stdout": result.stdout[-1000:] if result.stdout else "",
                "stderr": result.stderr[-500:] if result.stderr else "",
                "shell": "powershell (local)",
            }, ensure_ascii=False)
        except subprocess.TimeoutExpired:
            return json.dumps({"error": f"명령 실행 {pc_timeout}초 초과. PC_CMD_TIMEOUT 환경변수로 조정 가능"})
        except Exception as e:
            return json.dumps({"error": str(e)})


def check_environment(key_pattern: str = "") -> str:
    """환경변수 설정 상태를 확인합니다.

    Args:
        key_pattern: 검색할 환경변수 패턴 (빈 문자열이면 전체 출력)
    """
    env_file = PROJECT_ROOT / ".env"
    if not env_file.exists():
        return json.dumps({"error": ".env 파일 없음"})

    lines = env_file.read_text(encoding="utf-8").splitlines()
    result = {}
    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" in line:
            key, val = line.split("=", 1)
            if key_pattern and key_pattern.lower() not in key.lower():
                continue
            masked = val[:4] + "***" if len(val) > 4 else val
            result[key] = {"set": bool(val), "preview": masked}

    return json.dumps(result, ensure_ascii=False)


# ── 보안: 경로 접근 제한 ──────────────────────────

# 시스템 경로는 Sora가 접근 불가
_BLOCKED_PATHS = [
    "C:\\Windows", "C:\\Program Files", "C:\\Program Files (x86)",
    "/etc", "/usr", "/bin", "/sbin", "/boot",
]


def _is_safe_path(path: str) -> bool:
    """Sora가 접근해도 안전한 경로인지 확인"""
    for blocked in _BLOCKED_PATHS:
        if path.lower().startswith(blocked.lower()):
            return False
    return True


# ── 파일 읽기/쓰기/편집 도구 ──────────────────────────

def read_file(file_path: str, start_line: int = 0, end_line: int = 0) -> str:
    """파일 내용을 읽어 반환합니다.

    Args:
        file_path: 읽을 파일 절대 경로
        start_line: 시작 줄 (0이면 전체, 1-indexed)
        end_line: 끝 줄 (0이면 전체)
    """
    p = Path(file_path)
    if not p.exists():
        return json.dumps({"error": "파일이 존재하지 않습니다: %s" % file_path})
    if not p.is_file():
        return json.dumps({"error": "파일이 아닙니다: %s" % file_path})

    try:
        content = p.read_text(encoding="utf-8", errors="replace")
        lines = content.splitlines()
        total = len(lines)

        if start_line > 0:
            s = max(0, start_line - 1)
            e = end_line if end_line > 0 else total
            e = min(e, total)
            selected = lines[s:e]
            return json.dumps({
                "path": file_path,
                "total_lines": total,
                "showing": "%d-%d" % (s + 1, e),
                "content": "\n".join(selected),
            }, ensure_ascii=False)
        else:
            # 전체 읽기 (최대 5000줄)
            if total > 5000:
                return json.dumps({
                    "path": file_path,
                    "total_lines": total,
                    "showing": "1-5000 (잘림)",
                    "content": "\n".join(lines[:5000]),
                    "truncated": True,
                }, ensure_ascii=False)
            return json.dumps({
                "path": file_path,
                "total_lines": total,
                "content": content,
            }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


def write_file(file_path: str, content: str) -> str:
    """파일을 생성하거나 덮어씁니다. 부모 디렉토리가 없으면 자동 생성됩니다.

    Args:
        file_path: 생성할 파일 절대 경로
        content: 파일 내용
    """
    if not _is_safe_path(file_path):
        return json.dumps({"error": "시스템 보호 경로는 접근할 수 없습니다: %s" % file_path})

    try:
        p = Path(file_path)
        p.parent.mkdir(parents=True, exist_ok=True)
        p.write_text(content, encoding="utf-8")
        return json.dumps({
            "status": "success",
            "path": file_path,
            "bytes": len(content.encode("utf-8")),
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


def edit_file(file_path: str, old_content: str, new_content: str) -> str:
    """파일의 특정 부분을 수정합니다. old_content가 파일 내에 정확히 존재해야 합니다.

    Args:
        file_path: 수정할 파일 절대 경로
        old_content: 기존 내용 (정확히 일치해야 함)
        new_content: 새 내용
    """
    if not _is_safe_path(file_path):
        return json.dumps({"error": "시스템 보호 경로는 접근할 수 없습니다: %s" % file_path})

    p = Path(file_path)
    if not p.exists():
        return json.dumps({"error": "파일이 존재하지 않습니다: %s" % file_path})

    try:
        text = p.read_text(encoding="utf-8")
        if old_content not in text:
            return json.dumps({
                "error": "old_content를 파일에서 찾을 수 없습니다",
                "hint": "정확한 텍스트 매치가 필요합니다",
            }, ensure_ascii=False)

        count = text.count(old_content)
        new_text = text.replace(old_content, new_content, 1)
        p.write_text(new_text, encoding="utf-8")
        return json.dumps({
            "status": "success",
            "path": file_path,
            "matches_found": count,
            "replaced": 1,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


# ── 파일 탐색 도구 ──────────────────────────

def list_directory(dir_path: str) -> str:
    """디렉토리 내용을 나열합니다. 파일과 하위 디렉토리 목록을 반환합니다.

    Args:
        dir_path: 디렉토리 절대 경로
    """
    p = Path(dir_path)
    if not p.exists():
        return json.dumps({"error": "디렉토리가 존재하지 않습니다: %s" % dir_path})
    if not p.is_dir():
        return json.dumps({"error": "디렉토리가 아닙니다: %s" % dir_path})

    try:
        items = []
        for child in sorted(p.iterdir()):
            info = {
                "name": child.name,
                "type": "dir" if child.is_dir() else "file",
            }
            if child.is_file():
                info["size_bytes"] = child.stat().st_size
            items.append(info)

        return json.dumps({
            "path": dir_path,
            "count": len(items),
            "items": items[:200],  # 최대 200개
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


def find_files(directory: str, pattern: str, max_depth: int = 5) -> str:
    """파일명 패턴으로 파일을 검색합니다 (glob 방식).

    Args:
        directory: 검색 시작 디렉토리
        pattern: 검색 패턴 (glob, 예: *.py, *test*)
        max_depth: 최대 탐색 깊이 (기본 5)
    """
    p = Path(directory)
    if not p.exists():
        return json.dumps({"error": "디렉토리가 존재하지 않습니다: %s" % directory})

    try:
        results = []
        for match in p.rglob(pattern):
            # 깊이 제한
            rel = match.relative_to(p)
            if len(rel.parts) > max_depth:
                continue
            # __pycache__, node_modules, .git 무시
            parts_lower = [p_part.lower() for p_part in rel.parts]
            if any(skip in parts_lower for skip in
                   ["__pycache__", "node_modules", ".git", ".next", "venv"]):
                continue
            results.append({
                "path": str(match),
                "type": "dir" if match.is_dir() else "file",
                "size": match.stat().st_size if match.is_file() else None,
            })
            if len(results) >= 50:
                break

        return json.dumps({
            "directory": directory,
            "pattern": pattern,
            "found": len(results),
            "results": results,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


def grep_code(query: str, search_path: str, file_pattern: str = "") -> str:
    """코드에서 텍스트 패턴을 검색합니다 (줄 단위 매칭).

    Args:
        query: 검색할 텍스트
        search_path: 검색 경로 (파일 또는 디렉토리)
        file_pattern: 파일 필터 (예: *.py, *.ts)
    """
    p = Path(search_path)
    if not p.exists():
        return json.dumps({"error": "경로가 존재하지 않습니다: %s" % search_path})

    try:
        matches = []
        files_to_search = []

        if p.is_file():
            files_to_search = [p]
        else:
            glob_pat = file_pattern if file_pattern else "*"
            files_to_search = list(p.rglob(glob_pat))

        skip_dirs = {"__pycache__", "node_modules", ".git", ".next", "venv", ".mypy_cache"}

        for fp in files_to_search:
            if not fp.is_file():
                continue
            # 바이너리/대용량 건너뛰기
            if fp.stat().st_size > 1_000_000:
                continue
            parts = set(fp.parts)
            if parts & skip_dirs:
                continue
            try:
                lines = fp.read_text(encoding="utf-8", errors="replace").splitlines()
                for i, line in enumerate(lines, 1):
                    if query.lower() in line.lower():
                        matches.append({
                            "file": str(fp),
                            "line": i,
                            "content": line.strip()[:200],
                        })
                        if len(matches) >= 50:
                            break
            except Exception:
                continue
            if len(matches) >= 50:
                break

        return json.dumps({
            "query": query,
            "path": search_path,
            "total_matches": len(matches),
            "matches": matches,
        }, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"error": str(e)[:300]})


# ══════════════════════════════════════════════════
# 원격 PC 제어 도구 (대시보드 REST API 경유)
# 데몬(텔레그램 봇)과 대시보드는 별도 프로세스이므로
# PC Agent Hub의 REST API를 호출하여 통신합니다.
# ══════════════════════════════════════════════════

import requests as _requests

_DASHBOARD_BASE = os.getenv("SORA_DASHBOARD_URL", "http://127.0.0.1:7700")
# 대시보드 EXECUTE 스코프 인증: 서비스 시크릿(SORA_DASHBOARD_SECRET) 우선,
# 미설정 시 레거시 DASHBOARD_TOKEN 폴백 (원격 PC 도구 인증 버그 수정 2026-05-20)
_DASHBOARD_TOKEN = os.getenv("SORA_DASHBOARD_SECRET") or os.getenv("DASHBOARD_TOKEN", "neo-genesis-2026")
_PC_HEADERS = {"Authorization": f"Bearer {_DASHBOARD_TOKEN}"}


def _pc_api_get(path: str, timeout: int = 30) -> dict:
    """대시보드 REST API GET 호출."""
    try:
        r = _requests.get(f"{_DASHBOARD_BASE}{path}", headers=_PC_HEADERS, timeout=timeout)
        return r.json()
    except Exception as e:
        return {"error": f"API 호출 실패: {str(e)[:200]}"}


def _pc_api_post(path: str, body: dict, timeout: int = 60) -> dict:
    """대시보드 REST API POST 호출."""
    try:
        r = _requests.post(f"{_DASHBOARD_BASE}{path}", json=body, headers=_PC_HEADERS, timeout=timeout)
        return r.json()
    except Exception as e:
        return {"error": f"API 호출 실패: {str(e)[:200]}"}


# ══════════════════════════════════════════════════════════════════════
# 단일PC 로컬 실행 백엔드 (2026-05-29 — WSL2 sora → powershell.exe 직접 interop)
# JARVIS_LOCAL_EXEC=1 이면 hub/agent WebSocket fabric 우회, WSL interop 으로 직접 실행.
# 단일PC(desktop-home) 운영 시 hub/agent/token/flapping 전부 제거.
# governor 게이트는 도구 함수 상단에서 이미 적용되므로 이 백엔드는 실행만 담당.
# ══════════════════════════════════════════════════════════════════════
_LOCAL_EXEC = os.getenv("JARVIS_LOCAL_EXEC", "").strip().lower() in ("1", "true", "yes")
# WSL interop: Windows 바이너리 절대경로 (PATH 의존 제거)
_PWSH = "/mnt/c/Windows/System32/WindowsPowerShell/v1.0/powershell.exe"


def _local_powershell(command: str, timeout: int = 60) -> dict:
    """WSL2 → powershell.exe 직접 실행 (interop). hub agent 의 exec 와 동일 출력 형태."""
    try:
        pwsh = _PWSH if os.path.exists(_PWSH) else "powershell.exe"
        proc = subprocess.run(
            [pwsh, "-NoProfile", "-NonInteractive", "-Command", command],
            capture_output=True, text=True, timeout=timeout,
            encoding="utf-8", errors="replace",
        )
        return {
            "exit_code": proc.returncode,
            "stdout": (proc.stdout or "")[:8000],
            "stderr": (proc.stderr or "")[:2000],
            "shell": "powershell(wsl-interop)",
        }
    except subprocess.TimeoutExpired:
        return {"error": f"명령 시간 초과 ({timeout}s)", "shell": "powershell(wsl-interop)"}
    except Exception as e:
        return {"error": f"로컬 실행 실패: {str(e)[:200]}", "shell": "powershell(wsl-interop)"}


def _local_dispatch(hub_command: str, payload: dict, timeout: int = 60) -> dict:
    """hub command type 을 로컬 powershell interop 으로 번역 실행."""
    p = payload or {}
    if hub_command == "exec":
        return _local_powershell(p.get("command", ""), timeout)
    if hub_command == "batch_exec":
        cmds = p.get("commands", []) or []
        results = []
        for c in cmds:
            results.append(_local_powershell(str(c), timeout))
        return {"batch": results, "count": len(results)}
    if hub_command == "system_status":
        ps = (
            "$os=Get-CimInstance Win32_OperatingSystem;"
            "$cpu=(Get-CimInstance Win32_Processor | Measure-Object -Property LoadPercentage -Average).Average;"
            "$d=Get-PSDrive C;"
            "[pscustomobject]@{hostname=$env:COMPUTERNAME;"
            "os=$os.Caption;"
            "ram_total_mb=[math]::Round($os.TotalVisibleMemorySize/1024);"
            "ram_free_mb=[math]::Round($os.FreePhysicalMemory/1024);"
            "cpu_load=$cpu;"
            "disk_c_free_gb=[math]::Round($d.Free/1GB,1);"
            "disk_c_used_gb=[math]::Round($d.Used/1GB,1)} | ConvertTo-Json -Compress"
        )
        r = _local_powershell(ps, timeout)
        try:
            return json.loads(r.get("stdout", "{}")) if r.get("stdout") else r
        except Exception:
            return r
    if hub_command == "read_file":
        path = p.get("path", "")
        r = _local_powershell(f"Get-Content -Raw -LiteralPath '{path}'", timeout)
        return {"path": path, "content": r.get("stdout", ""), "error": r.get("error")}
    if hub_command == "write_file":
        # content 를 base64 로 안전 전달 (escaping 회피)
        import base64
        path = p.get("path", "")
        content = p.get("content", "")
        b64 = base64.b64encode(content.encode("utf-8")).decode("ascii")
        ps = (
            f"$b=[System.Convert]::FromBase64String('{b64}');"
            f"$t=[System.Text.Encoding]::UTF8.GetString($b);"
            f"Set-Content -LiteralPath '{path}' -Value $t -NoNewline -Encoding UTF8;"
            f"Write-Output 'WROTE {path}'"
        )
        r = _local_powershell(ps, timeout)
        return {"path": path, "result": r.get("stdout", ""), "error": r.get("error")}
    if hub_command in ("claude_run", "claude_chat"):
        # WSL interop → claude CLI print 모드 (Windows 인증 공유). 구독 활용, $0.
        prompt = p.get("prompt", "") or p.get("message", "") or ""
        cwd = p.get("cwd", "") or ""
        claude_bin = "/root/.hermes/node/bin/claude"
        if not os.path.exists(claude_bin):
            return {"error": "claude CLI 미설치 (/root/.hermes/node/bin/claude)"}
        try:
            args = [claude_bin, "-p", prompt]
            proc = subprocess.run(args, capture_output=True, text=True,
                                  timeout=max(60, timeout), encoding="utf-8", errors="replace",
                                  cwd=cwd if cwd and os.path.isdir(cwd) else None)
            return {"exit_code": proc.returncode,
                    "stdout": (proc.stdout or "")[:6000],
                    "stderr": (proc.stderr or "")[:1000],
                    "tool": "claude_cli(wsl-interop)"}
        except subprocess.TimeoutExpired:
            return {"error": f"claude 시간 초과 ({timeout}s)"}
        except Exception as e:
            return {"error": f"claude 실행 실패: {str(e)[:150]}"}
    if hub_command == "git_status":
        cwd = p.get("cwd", ".")
        r = _local_powershell(f"cd '{cwd}'; git status --short 2>&1 | Select-Object -First 30; git log --oneline -3", timeout)
        return r
    return {"error": f"로컬 미지원 command: {hub_command} (단일PC interop 미번역 — 필요 시 추가)"}


def _device_call(pc_id: str, hub_command: str, payload: dict, timeout: int = 60) -> dict:
    """디바이스 실행 dispatch. JARVIS_LOCAL_EXEC=1 이면 로컬 interop, 아니면 hub API.

    단일PC 모드에서는 pc_id 무관하게 로컬 실행 (이 PC = 유일 디바이스).
    """
    if _LOCAL_EXEC:
        return _local_dispatch(hub_command, payload, timeout)
    return _pc_api_post(f"/api/pc-agents/{pc_id}/command",
                        {"command": hub_command, "payload": payload}, timeout)


def list_connected_pcs() -> str:
    """현재 연결된 원격 PC 목록을 조회합니다. home-pc(집), work-pc(회사) 등."""
    # 단일PC 로컬 모드: 이 PC(desktop-home) 가 유일 디바이스 (hub/agent 불요)
    if _LOCAL_EXEC:
        import socket
        host = os.getenv("JARVIS_LOCAL_AGENT_ID", "desktop-home")
        return json.dumps({host: {"online": True, "mode": "local-interop",
                                  "hostname": host, "via": "wsl-powershell"}},
                          ensure_ascii=False)
    result = _pc_api_get("/api/pc-agents")
    if not result or result == {}:
        return json.dumps({"message": "연결된 PC가 없습니다. 각 PC에서 sora_pc_agent.py를 실행하세요."})
    return json.dumps(result, ensure_ascii=False, default=str)


# 디바이스 자연어 별칭 → agent_id (owner 편집 가능: 키워드는 소문자 substring 매칭)
# 2026-05-20: "집 pc" 같은 자연어 지칭을 agent_id 로 해석 (deterministic 경로용)
DEVICE_ALIASES = {
    "desktop-home": ["집", "집pc", "집 pc", "집컴", "집 컴", "집컴퓨터", "집 컴퓨터", "홈", "home", "home-pc", "내 pc", "내pc", "이 pc", "데스크탑", "데스크톱"],
    "etribe-yesol": ["회사", "회사pc", "회사 pc", "회사컴", "회사 컴퓨터", "사무실", "work", "work-pc"],
    "linux-server": ["서버", "리눅스", "리눅스서버", "리눅스 서버", "server", "ysh", "ysh-server"],
    "yesol-asus": ["아수스", "asus", "노트북", "랩탑", "laptop"],
    # "맥" 단일 글자는 false positive(맥주/맥락) → 제거. 2글자+만 매칭.
    "mx-macbuild-mac-studio": ["mac", "맥북", "맥스튜디오", "맥 스튜디오", "mac-studio", "macstudio", "macbook"],
}


def resolve_device(phrase: str, connected_ids: list[str]) -> str | None:
    """자연어 디바이스 지칭(phrase)을 연결된 agent_id 로 해석.

    우선순위: (1) agent_id 직접 포함 → (2) 별칭 키워드 매칭 (연결된 것만) →
    (3) PC 가 1대만 연결됐고 phrase 에 pc/컴퓨터 언급 → 그 1대.
    해석 실패 시 None.
    """
    if not phrase:
        return None
    p = phrase.lower().strip()
    # (1) agent_id 직접 포함
    for aid in connected_ids:
        if aid.lower() in p:
            return aid
    # (2) 별칭 (연결된 것만, 긴 키워드 우선)
    best = None
    best_len = 0
    for aid, names in DEVICE_ALIASES.items():
        if aid not in connected_ids:
            continue
        for n in names:
            if n in p and len(n) > best_len:
                best, best_len = aid, len(n)
    if best:
        return best
    # (3) 단일 PC 폴백
    if len(connected_ids) == 1 and any(k in p for k in ["pc", "컴퓨터", "컴", "기기", "디바이스"]):
        return connected_ids[0]
    return None


def _governor_gate(pc_id: str, command_summary: str, command_type: str, payload: dict) -> str | None:
    """공통 governor 진입. 위험이면 stage_pending 결과(JSON 문자열) 반환, 안전이면 None.

    fail-closed: governor 모듈 자체가 import 실패 또는 분류 중 예외 → 위험 가능성을 가정해 차단.
    """
    try:
        from src.core.security import command_governor as _gov
    except Exception as e:
        return json.dumps({"governor": "ERROR",
                           "error": f"governor 모듈 로드 실패 — 안전상 차단: {str(e)[:200]}"},
                          ensure_ascii=False)
    try:
        level, reason, rec = _gov.classify_risk(command_summary)
    except Exception as e:
        return json.dumps({"governor": "ERROR",
                           "error": f"위험 분류 중 예외 — 안전상 차단: {str(e)[:200]}"},
                          ensure_ascii=False)
    if level == "dangerous":
        return _gov.stage_pending(pc_id, command_summary, reason, rec,
                                  command_type=command_type, payload=payload)
    return None


def _governor_audit(pc_id: str, command_type: str, command_summary: str, result) -> None:
    """공통 audit (실행 후 호출). 실패 무음 (governor.audit 자체가 best-effort)."""
    try:
        from src.core.security import command_governor as _gov
        _gov.audit(pc_id, command_type, command_summary, "executed", str(result)[:300])
    except Exception:
        pass


def remote_pc_command(pc_id: str, command: str) -> str:
    """원격 PC에서 셸 명령을 실행합니다.

    위험·비가역 명령(rm -rf, 포맷, force push, credential 외부전송 등)은 즉시
    실행하지 않고 위험/권고를 설명한 뒤 owner 확인을 요청합니다(warn-then-obey).
    owner가 '진행'하면 confirm_pending_command(internal) 로 실행됩니다.

    Args:
        pc_id: PC 식별자 (예: "home-pc", "work-pc"). list_connected_pcs로 확인 가능
        command: 실행할 명령어
    """
    payload = {"command": command}
    warn = _governor_gate(pc_id, command, "exec", payload)
    if warn is not None:
        return warn
    result = _device_call(pc_id, "exec", payload)
    _governor_audit(pc_id, "exec", command, result)
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_pc_screenshot(pc_id: str) -> str:
    """원격 PC의 스크린샷을 캡처합니다.

    Args:
        pc_id: PC 식별자 (예: "home-pc", "work-pc")
    """
    result = _device_call(pc_id, "screenshot", {"max_width": 1280, "quality": 75})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_pc_status(pc_id: str) -> str:
    """원격 PC의 시스템 상태(CPU, RAM, 디스크)를 조회합니다.

    Args:
        pc_id: PC 식별자 (예: "home-pc", "work-pc")
    """
    result = _device_call(pc_id, "system_status", {})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_pc_file_read(pc_id: str, file_path: str) -> str:
    """원격 PC의 파일을 읽습니다.

    Args:
        pc_id: PC 식별자
        file_path: 읽을 파일 경로
    """
    result = _device_call(pc_id, "read_file", {"path": file_path})
    return json.dumps(result, ensure_ascii=False, default=str)


_SENSITIVE_PATH_RE = re.compile(
    r'(\.env|\.ssh/|credential|secret|private_key|id_ed25519|id_rsa|'
    r'\.bashrc|\.bash_profile|\.profile|\.zshrc|'
    r'startup|autostart|cron|systemd|\.service|\.timer|launchctl|'
    r'/etc/(passwd|shadow|sudoers|hosts)|'
    r'C:\\Windows\\System32|registry|hosts)',
    re.I,
)


def remote_pc_file_write(pc_id: str, file_path: str, content: str) -> str:
    """원격 PC에 파일을 생성/덮어씁니다.

    민감 경로(.env, .ssh, startup, systemd, /etc/passwd 등)는 위험으로 분류 → warn-then-obey.

    Args:
        pc_id: PC 식별자
        file_path: 파일 경로
        content: 파일 내용
    """
    summary = f"write_file {file_path}"
    # 민감 경로 우선 분류
    if _SENSITIVE_PATH_RE.search(file_path or ""):
        try:
            from src.core.security import command_governor as _gov
            return _gov.stage_pending(
                pc_id, summary,
                "민감 파일 덮어쓰기 — 자격증명/시작스크립트/시스템파일 손상 가능",
                "경로/내용 재확인 후 진행. 백업 권장.",
                command_type="write_file",
                payload={"path": file_path, "content": content},
            )
        except Exception as e:
            return json.dumps({"governor": "ERROR", "error": f"governor 차단: {e}"}, ensure_ascii=False)
    # 일반 경로도 일반 governor 검사 (예: content에 위험 패턴 포함 시 알림)
    warn = _governor_gate(pc_id, summary, "write_file",
                          {"path": file_path, "content": content})
    if warn is not None:
        return warn
    result = _device_call(pc_id, "write_file", {"path": file_path, "content": content})
    _governor_audit(pc_id, "write_file", summary, result)
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_pc_process_list(pc_id: str, filter_name: str = "") -> str:
    """원격 PC의 프로세스 목록을 조회합니다.

    Args:
        pc_id: PC 식별자
        filter_name: 프로세스 이름 필터 (빈 문자열이면 전체)
    """
    if _LOCAL_EXEC:
        flt = (filter_name or "").replace("'", "")
        ps = ("Get-Process " + (f"-Name '*{flt}*' " if flt else "") +
              "| Select-Object -First 40 Id,ProcessName,@{N='MB';E={[math]::Round($_.WorkingSet64/1MB)}} "
              "| ConvertTo-Json -Compress")
        result = _local_powershell(ps)
    else:
        result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "process_list", "payload": {"filter": filter_name}})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_claude_run(pc_id: str, prompt: str, cwd: str = ".") -> str:
    """원격 PC에서 Claude CLI를 실행합니다.

    Args:
        pc_id: PC 식별자 (예: "home-pc", "linux-server")
        prompt: Claude에게 보낼 프롬프트
        cwd: 작업 디렉토리 (기본: 현재)
    """
    result = _device_call(pc_id, "claude_run", {"prompt": prompt, "cwd": cwd}, 180)
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_claude_chat(pc_id: str, message: str, session_id: str = "", cwd: str = ".") -> str:
    """원격 PC에서 Claude CLI 대화 세션에 메시지를 보냅니다.

    Args:
        pc_id: PC 식별자
        message: 메시지
        session_id: 세션 ID (빈 문자열이면 새 세션)
        cwd: 작업 디렉토리
    """
    result = _device_call(pc_id, "claude_chat", {"message": message, "session_id": session_id, "cwd": cwd}, 180)
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_docker_ps(pc_id: str) -> str:
    """원격 PC/서버의 Docker 컨테이너 목록을 조회합니다.

    Args:
        pc_id: PC 식별자 (주로 "linux-server")
    """
    result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "docker_ps", "payload": {}})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_docker_logs(pc_id: str, container_name: str, tail: int = 30) -> str:
    """원격 Docker 컨테이너 로그를 조회합니다.

    Args:
        pc_id: PC 식별자
        container_name: 컨테이너 이름
        tail: 마지막 N줄
    """
    result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "docker_logs", "payload": {"name": container_name, "tail": tail}})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_git_status(pc_id: str, cwd: str = ".") -> str:
    """원격 PC의 Git 저장소 상태를 확인합니다.

    Args:
        pc_id: PC 식별자
        cwd: Git 저장소 경로
    """
    result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "git_status", "payload": {"cwd": cwd}})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_web_search(pc_id: str, query: str) -> str:
    """원격 PC/서버에서 웹 검색합니다 (SearXNG).

    Args:
        pc_id: PC 식별자 (주로 "linux-server")
        query: 검색어
    """
    result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "web_search", "payload": {"query": query}})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_web_crawl(pc_id: str, url: str) -> str:
    """원격 PC/서버에서 웹페이지를 크롤링합니다 (Crawl4AI).

    Args:
        pc_id: PC 식별자 (주로 "linux-server")
        url: 크롤링할 URL
    """
    result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "web_crawl", "payload": {"url": url}})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_vercel_deploy(pc_id: str, cwd: str) -> str:
    """원격 PC에서 Vercel 프로덕션 배포합니다 (production 영향 — warn-then-obey).

    Args:
        pc_id: PC 식별자
        cwd: 프로젝트 경로
    """
    try:
        from src.core.security import command_governor as _gov
        return _gov.stage_pending(
            pc_id, f"vercel_deploy {cwd}",
            "Production 배포 — 라이브 트래픽 영향 + 빌드 실패 시 가용성 영향",
            "변경 사항 + 환경변수 + 빌드 로컬 검증 후 진행 권장",
            command_type="vercel_deploy",
            payload={"cwd": cwd},
        )
    except Exception as e:
        return json.dumps({"governor": "ERROR", "error": f"governor 차단: {e}"}, ensure_ascii=False)


def remote_git_commit_push(pc_id: str, cwd: str, message: str) -> str:
    """원격 PC에서 Git commit + push합니다 (원격 히스토리 변경 — warn-then-obey).

    Args:
        pc_id: PC 식별자
        cwd: Git 저장소 경로
        message: 커밋 메시지
    """
    summary = f"git commit+push {cwd}: {message[:80]}"
    try:
        from src.core.security import command_governor as _gov
        return _gov.stage_pending(
            pc_id, summary,
            "원격 저장소 push — 히스토리에 영구 기록, 협업자 영향, secret 포함 시 노출",
            "git diff/status 확인 후 진행. secret/.env 미포함 확인 권장.",
            command_type="git_commit_push",
            payload={"cwd": cwd, "message": message},
        )
    except Exception as e:
        return json.dumps({"governor": "ERROR", "error": f"governor 차단: {e}"}, ensure_ascii=False)


def remote_batch_exec(pc_id: str, commands: list[str]) -> str:
    """원격 PC에서 여러 명령을 순차 실행합니다.

    Args:
        pc_id: PC 식별자
        commands: 명령 목록 (최대 10개)
    """
    summary = " && ".join(str(x) for x in (commands or []))
    # 위험 분류는 각 명령 개별 + 합산
    try:
        from src.core.security import command_governor as _gov
        for _c in (commands or []):
            level, reason, rec = _gov.classify_risk(str(_c))
            if level == "dangerous":
                # 원본 commands 리스트를 payload에 보존 → confirm 시 batch_exec API 그대로 호출
                return _gov.stage_pending(
                    pc_id, summary,
                    f"배치 내 위험 명령: {reason}", rec,
                    command_type="batch_exec",
                    payload={"commands": list(commands)},
                )
    except Exception as e:
        return json.dumps({"governor": "ERROR",
                           "error": f"위험 분류 실패 — 안전상 차단: {str(e)[:200]}"},
                          ensure_ascii=False)
    result = _device_call(pc_id, "batch_exec", {"commands": commands})
    _governor_audit(pc_id, "batch_exec", summary, result)
    return json.dumps(result, ensure_ascii=False, default=str)


# ── confirm map: command_type → hub command name ──
# 원래 command_type 을 보존해서 confirm 시 동일 의미로 실행 (batch != exec)
_CONFIRM_HUB_CMD = {
    "exec": "exec",
    "batch_exec": "batch_exec",
    "write_file": "write_file",
    "vercel_deploy": "vercel_deploy",
    "git_commit_push": "_GIT_COMMIT_PUSH_SEQUENCE_",  # 두 단계라 특수
    "npm_build_deploy": "_NPM_BUILD_DEPLOY_SEQUENCE_",
}


def _confirm_pending_command_internal(confirm_id: str = "") -> str:
    """[INTERNAL] sora_engine 의 deterministic fastpath 섹션 9 에서만 호출.

    LLM 노출 금지 — Gemini가 직접 호출하면 owner-intent 우회. fastpath 가 owner의
    명시적 "진행" 발화를 deterministic 으로 감지한 후 이 함수를 호출한다.
    """
    try:
        from src.core.security import command_governor as _gov
    except Exception as e:
        return json.dumps({"error": f"governor 로드 실패: {e}"}, ensure_ascii=False)
    item = _gov.take_pending(confirm_id)
    if not item:
        return json.dumps({"error": "보류 중인 명령이 없습니다 (이미 실행됐거나 만료됨)."}, ensure_ascii=False)
    pc_id = item["pc_id"]
    command = item["command"]
    ctype = item.get("command_type", "exec")
    payload = item.get("payload") or {"command": command}
    hub_cmd = _CONFIRM_HUB_CMD.get(ctype, "exec")
    try:
        if hub_cmd == "_GIT_COMMIT_PUSH_SEQUENCE_":
            cwd = payload.get("cwd", ".")
            msg = payload.get("message", "")
            if _LOCAL_EXEC:
                commit = _local_powershell(f"cd '{cwd}'; git commit -am '{msg}'", 60)
                push = _local_powershell(f"cd '{cwd}'; git push", 120)
            else:
                commit = _pc_api_post(f"/api/pc-agents/{pc_id}/command",
                                       {"command": "git_commit", "payload": payload})
                push = _pc_api_post(f"/api/pc-agents/{pc_id}/command",
                                    {"command": "git_push", "payload": {"cwd": cwd}})
            result = {"commit": commit, "push": push}
        elif hub_cmd == "_NPM_BUILD_DEPLOY_SEQUENCE_":
            cwd = payload.get("cwd", ".")
            if _LOCAL_EXEC:
                build = _local_powershell(f"cd '{cwd}'; npm run build", 180)
                deploy = _local_powershell(f"cd '{cwd}'; npx vercel --prod --yes", 180)
                result = {"build": build, "deploy": deploy}
            else:
                build = _pc_api_post(f"/api/pc-agents/{pc_id}/command",
                                      {"command": "npm_build", "payload": payload})
                if isinstance(build, dict) and build.get("status") == "success":
                    deploy = _pc_api_post(f"/api/pc-agents/{pc_id}/command",
                                           {"command": "vercel_deploy", "payload": payload, "timeout": 180})
                else:
                    deploy = "빌드 실패로 배포 건너뜀"
                result = {"build": build, "deploy": deploy}
        else:
            tmo = 180 if ctype in ("vercel_deploy", "npm_build_deploy") else 60
            if hub_cmd in ("vercel_deploy",) and _LOCAL_EXEC:
                result = _local_powershell(f"cd '{payload.get('cwd', '.')}'; npx vercel --prod --yes", tmo)
            else:
                result = _device_call(pc_id, hub_cmd, payload, tmo)
    except Exception as e:
        result = {"error": f"실행 실패: {e}"}
    _gov.audit(pc_id, ctype, command, "confirmed_executed", str(result)[:300])
    return json.dumps({"executed": command, "pc_id": pc_id,
                       "command_type": ctype, "result": result},
                      ensure_ascii=False, default=str)


# 외부 노출 alias (하위 호환 — fastpath만 사용)
confirm_pending_command = _confirm_pending_command_internal


# ══════════════════════════════════════════════════════════════════════
# 자비스 가시성 도구 (M10 — owner 텔레그램으로 상태/감사 확인)
# ══════════════════════════════════════════════════════════════════════

def jarvis_web_search(query: str, num_results: int = 5) -> str:
    """무키 웹 검색 (DuckDuckGo). 자격증명 불요 — 단일PC 자비스용.

    빠른 사실/뉴스 확인용. 깊은 크롤은 별도. owner "X 검색해줘 / 최신 X 뉴스" 류.

    Args:
        query: 검색어
        num_results: 결과 개수 (기본 5)
    """
    try:
        # DuckDuckGo Instant Answer (무키, 안정)
        ia = _requests.get("https://api.duckduckgo.com/",
                           params={"q": query, "format": "json", "no_html": "1", "skip_disambig": "1"},
                           timeout=12, headers={"User-Agent": "Mozilla/5.0 jarvis"}).json()
        out = {"query": query, "results": []}
        if ia.get("AbstractText"):
            out["answer"] = ia["AbstractText"][:500]
            out["source"] = ia.get("AbstractURL", "")
        for t in (ia.get("RelatedTopics") or [])[:num_results]:
            if isinstance(t, dict) and t.get("Text"):
                out["results"].append({"text": t["Text"][:200], "url": t.get("FirstURL", "")})
        # Instant Answer 가 비면 HTML lite 폴백 (DDG lite 는 POST 필요)
        if not out.get("answer") and not out["results"]:
            import re as _re
            html = _requests.post("https://lite.duckduckgo.com/lite/",
                                  data={"q": query}, timeout=12,
                                  headers={"User-Agent": "Mozilla/5.0"}).text
            # lite 결과: <a href="URL" class='result-link'>TITLE</a> (href 가 class 앞, 작은따옴표)
            links = _re.findall(r'href="(https?://[^"]+)"[^>]*class=[\'"]result-link[\'"]>(.*?)</a>', html, _re.S)
            snips = _re.findall(r'class=[\'"]result-snippet[\'"][^>]*>(.*?)</td>', html, _re.S)
            def _clean(s):
                return _re.sub(r'<[^>]+>', '', s or '').strip()[:200]
            seen = set()
            for i, (url, title) in enumerate(links):
                if url in seen:
                    continue
                seen.add(url)
                snip = _clean(snips[i]) if i < len(snips) else ""
                out["results"].append({"title": _clean(title), "url": url, "snippet": snip})
                if len(out["results"]) >= num_results:
                    break
        if not out.get("answer") and not out["results"]:
            out["note"] = "결과 없음 (DDG instant answer + lite 모두 빈 응답)"
        return json.dumps(out, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"query": query, "error": f"웹 검색 실패: {str(e)[:150]}"}, ensure_ascii=False)


def get_jarvis_status() -> str:
    """자비스 전체 스택 상태를 한 번에 조회합니다.

    포함: 연결된 PC 목록 + 보류 명령 개수 + 최근 감사 로그 1줄 + governor 패턴 수.
    owner 가 "자비스 상태", "자비스 잘 있어?", "jarvis 헬스" 등으로 물을 때 호출.
    """
    try:
        from src.core.security import command_governor as _gov
        gov_ok = True
        pending = _gov.pending_count()
        pattern_count = len(_gov._DANGER_RULES)
        try:
            last_audit = ""
            if _gov.AUDIT_PATH.exists():
                with open(_gov.AUDIT_PATH, "r", encoding="utf-8") as f:
                    lines = f.readlines()
                if lines:
                    last_audit = lines[-1].strip()[:300]
        except Exception:
            last_audit = "(audit 읽기 실패)"
    except Exception as e:
        return json.dumps({"jarvis_status": "GOVERNOR_DOWN", "error": str(e)[:200]}, ensure_ascii=False)
    pcs = _pc_api_get("/api/pc-agents")
    if not isinstance(pcs, dict):
        pcs = {}
    online = [k for k, v in pcs.items() if isinstance(v, dict) and v.get("online")]
    return json.dumps({
        "jarvis_status": "OK" if (gov_ok and online) else "DEGRADED",
        "governor": {"loaded": gov_ok, "danger_patterns": pattern_count, "pending_count": pending},
        "agents": {"online": online, "all": list(pcs.keys())},
        "last_audit": last_audit,
    }, ensure_ascii=False, default=str)


def get_jarvis_audit_summary(hours: int = 24) -> str:
    """최근 N시간(기본 24h) 감사 로그 요약.

    owner 가 "오늘 자비스 뭐 했어", "감사 로그", "최근 실행 명령" 등으로 물을 때 호출.

    Args:
        hours: 최근 N 시간 (기본 24)
    """
    try:
        from src.core.security import command_governor as _gov
        if not _gov.AUDIT_PATH.exists():
            return json.dumps({"summary": "audit 로그 없음"}, ensure_ascii=False)
        cutoff_ts = time.time() - max(1, int(hours)) * 3600
    except Exception as e:
        return json.dumps({"error": str(e)[:200]}, ensure_ascii=False)
    counts = {"executed": 0, "warned": 0, "confirmed_executed": 0, "blocked_error": 0}
    recent_warned = []
    recent_executed = []
    try:
        from datetime import datetime as _dt
        with open(_gov.AUDIT_PATH, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    e = json.loads(line)
                except Exception:
                    continue
                ts_s = e.get("ts", "")
                try:
                    ts_v = _dt.fromisoformat(ts_s).timestamp()
                    if ts_v < cutoff_ts:
                        continue
                except Exception:
                    pass
                dec = e.get("decision", "")
                counts[dec] = counts.get(dec, 0) + 1
                if dec == "warned" and len(recent_warned) < 5:
                    recent_warned.append({"cmd": e.get("command", "")[:120],
                                          "reason": e.get("result_summary", "")[:120]})
                elif dec in ("executed", "confirmed_executed") and len(recent_executed) < 5:
                    recent_executed.append({"cmd": e.get("command", "")[:120],
                                            "pc": e.get("pc_id", "")})
    except Exception as e:
        return json.dumps({"error": f"audit 파싱 실패: {e}"}, ensure_ascii=False)
    return json.dumps({
        "window_hours": hours,
        "counts": counts,
        "total": sum(counts.values()),
        "recent_warned": recent_warned,
        "recent_executed": recent_executed,
    }, ensure_ascii=False, default=str)


def remote_npm_build_deploy(pc_id: str, cwd: str) -> str:
    """원격 PC에서 npm build + Vercel 배포를 실행합니다 (production 영향 — warn-then-obey).

    Args:
        pc_id: PC 식별자
        cwd: 프로젝트 경로
    """
    try:
        from src.core.security import command_governor as _gov
        return _gov.stage_pending(
            pc_id, f"npm_build + vercel_deploy {cwd}",
            "Production 빌드+배포 — 라이브 트래픽 영향. 빌드 실패 시 부분 배포 가능",
            "변경 사항 + 환경변수 + 로컬 빌드 검증 후 진행",
            command_type="npm_build_deploy",
            payload={"cwd": cwd},
        )
    except Exception as e:
        return json.dumps({"governor": "ERROR", "error": f"governor 차단: {e}"}, ensure_ascii=False)


CALLABLE_TOOLS_REGISTRY_PATH = PROJECT_ROOT / ".agent" / "registries" / "callable_tools.json"
EXTERNAL_TOOL_CAPABILITIES_REGISTRY_PATH = PROJECT_ROOT / ".agent" / "registries" / "external_tool_capabilities.json"


def refresh_callable_tools_registry(updated_by: str = "agent") -> str:
    """Refresh the shared callable-tools registry for all agents.

    Args:
        updated_by: Agent or operator name to record in the registry.
    """
    script = PROJECT_ROOT / "scripts" / "agent" / "update_callable_tools_registry.py"
    if not script.exists():
        return json.dumps({"status": "error", "error": f"registry script not found: {script}"}, ensure_ascii=False)

    try:
        result = subprocess.run(
            [sys.executable, str(script), "--updated-by", updated_by or "agent"],
            capture_output=True,
            text=True,
            timeout=90,
            cwd=str(PROJECT_ROOT),
            encoding="utf-8",
            errors="replace",
        )
        payload = {
            "status": "success" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "registry_path": str(CALLABLE_TOOLS_REGISTRY_PATH),
        }
        if CALLABLE_TOOLS_REGISTRY_PATH.exists():
            registry = json.loads(CALLABLE_TOOLS_REGISTRY_PATH.read_text(encoding="utf-8"))
            payload.update({
                "tool_count": registry.get("tool_count"),
                "agent_count": registry.get("agent_count"),
                "registry_revision": registry.get("registry_revision"),
                "generated_at": registry.get("generated_at"),
            })
        return json.dumps(payload, ensure_ascii=False, default=str)
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "timeout", "message": "registry refresh exceeded 90 seconds"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


def list_callable_tools(agent_id: str = "", refresh: bool = False) -> str:
    """List tools from the shared callable-tools registry.

    Args:
        agent_id: Optional agent route id. If set, only that agent's tools are returned.
        refresh: Refresh the registry before reading it.
    """
    if refresh or not CALLABLE_TOOLS_REGISTRY_PATH.exists():
        refreshed = json.loads(refresh_callable_tools_registry("agent"))
        if refreshed.get("status") not in ("success", "failed") and not CALLABLE_TOOLS_REGISTRY_PATH.exists():
            return json.dumps(refreshed, ensure_ascii=False, default=str)

    if not CALLABLE_TOOLS_REGISTRY_PATH.exists():
        return json.dumps({"status": "error", "error": "callable tools registry does not exist"}, ensure_ascii=False)

    try:
        registry = json.loads(CALLABLE_TOOLS_REGISTRY_PATH.read_text(encoding="utf-8"))
        tools = registry.get("tools", [])
        compact_tools = [
            {
                "name": item.get("name"),
                "module": item.get("module"),
                "signature": item.get("signature"),
                "authority_tier": item.get("policy", {}).get("authority_tier"),
                "action": item.get("policy", {}).get("action"),
                "requires_approval": item.get("policy", {}).get("requires_approval"),
                "status": item.get("status"),
            }
            for item in tools
        ]

        if agent_id:
            route = registry.get("agent_routes", {}).get(agent_id)
            if not route:
                return json.dumps({
                    "status": "not_found",
                    "agent_id": agent_id,
                    "available_agents": sorted(registry.get("agent_routes", {}).keys()),
                }, ensure_ascii=False)
            allowed = set(route.get("tool_names", []))
            selected = [item for item in compact_tools if item.get("name") in allowed]
            return json.dumps({
                "status": "success",
                "generated_at": registry.get("generated_at"),
                "registry_revision": registry.get("registry_revision"),
                "agent_id": agent_id,
                "route": route,
                "tools": selected,
            }, ensure_ascii=False, default=str)

        return json.dumps({
            "status": "success",
            "generated_at": registry.get("generated_at"),
            "registry_revision": registry.get("registry_revision"),
            "tool_count": registry.get("tool_count"),
            "agent_count": registry.get("agent_count"),
            "indexes": registry.get("indexes", {}),
            "available_agents": sorted(registry.get("agent_routes", {}).keys()),
            "tools": compact_tools,
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


def refresh_external_tool_capability_registry(updated_by: str = "agent") -> str:
    """Refresh the shared external tool capability registry.

    Args:
        updated_by: Agent or operator name to record in the registry.
    """
    script = PROJECT_ROOT / "scripts" / "agent" / "update_external_tool_capability_registry.py"
    if not script.exists():
        return json.dumps({"status": "error", "error": f"registry script not found: {script}"}, ensure_ascii=False)

    try:
        result = subprocess.run(
            [sys.executable, str(script), "--updated-by", updated_by or "agent"],
            capture_output=True,
            text=True,
            timeout=60,
            cwd=str(PROJECT_ROOT),
            encoding="utf-8",
            errors="replace",
        )
        payload = {
            "status": "success" if result.returncode == 0 else "failed",
            "exit_code": result.returncode,
            "stdout": result.stdout[-2000:] if result.stdout else "",
            "stderr": result.stderr[-2000:] if result.stderr else "",
            "registry_path": str(EXTERNAL_TOOL_CAPABILITIES_REGISTRY_PATH),
        }
        if EXTERNAL_TOOL_CAPABILITIES_REGISTRY_PATH.exists():
            registry = json.loads(EXTERNAL_TOOL_CAPABILITIES_REGISTRY_PATH.read_text(encoding="utf-8"))
            payload.update({
                "capability_count": registry.get("capability_count"),
                "registry_revision": registry.get("registry_revision"),
                "generated_at": registry.get("generated_at"),
            })
        return json.dumps(payload, ensure_ascii=False, default=str)
    except subprocess.TimeoutExpired:
        return json.dumps({"status": "timeout", "message": "external registry refresh exceeded 60 seconds"}, ensure_ascii=False)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


def list_external_tool_capabilities(
    namespace: str = "",
    capability_type: str = "",
    status: str = "",
    refresh: bool = False,
) -> str:
    """List Codex/session external tool capabilities.

    Args:
        namespace: Optional namespace filter, for example web, plugin, codex_app.
        capability_type: Optional capability type filter.
        status: Optional status filter.
        refresh: Refresh the external capability registry before reading it.
    """
    if refresh or not EXTERNAL_TOOL_CAPABILITIES_REGISTRY_PATH.exists():
        refreshed = json.loads(refresh_external_tool_capability_registry("agent"))
        if refreshed.get("status") not in ("success", "failed") and not EXTERNAL_TOOL_CAPABILITIES_REGISTRY_PATH.exists():
            return json.dumps(refreshed, ensure_ascii=False, default=str)

    if not EXTERNAL_TOOL_CAPABILITIES_REGISTRY_PATH.exists():
        return json.dumps({"status": "error", "error": "external tool capability registry does not exist"}, ensure_ascii=False)

    try:
        registry = json.loads(EXTERNAL_TOOL_CAPABILITIES_REGISTRY_PATH.read_text(encoding="utf-8"))
        capabilities = registry.get("capabilities", [])

        def _matches(item: dict) -> bool:
            if namespace and item.get("namespace") != namespace:
                return False
            if capability_type and item.get("capability_type") != capability_type:
                return False
            if status and item.get("status") != status:
                return False
            return True

        selected = [
            {
                "id": item.get("id"),
                "namespace": item.get("namespace"),
                "tool": item.get("tool"),
                "display_name": item.get("display_name"),
                "capability_type": item.get("capability_type"),
                "status": item.get("status"),
                "callable_by": item.get("callable_by", []),
                "handoff_required_for": item.get("handoff_required_for", []),
                "authority_tier": item.get("authority_tier"),
                "external_side_effect": item.get("external_side_effect"),
                "description": item.get("description"),
            }
            for item in capabilities
            if _matches(item)
        ]
        return json.dumps({
            "status": "success",
            "generated_at": registry.get("generated_at"),
            "registry_revision": registry.get("registry_revision"),
            "capability_count": registry.get("capability_count"),
            "returned_count": len(selected),
            "indexes": registry.get("indexes", {}),
            "capabilities": selected,
        }, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


def list_agent_tool_capabilities(scope: str = "all", agent_id: str = "", refresh: bool = False) -> str:
    """List local callable tools and external session capabilities together.

    Args:
        scope: all, local, or external.
        agent_id: Optional local agent route id for local tool filtering.
        refresh: Refresh selected registries before reading them.
    """
    normalized_scope = (scope or "all").lower()
    if normalized_scope not in ("all", "local", "external"):
        return json.dumps({"status": "error", "error": "scope must be all, local, or external"}, ensure_ascii=False)

    result = {
        "status": "success",
        "scope": normalized_scope,
        "agent_id": agent_id,
        "local": None,
        "external": None,
    }
    try:
        if normalized_scope in ("all", "local"):
            result["local"] = json.loads(list_callable_tools(agent_id=agent_id, refresh=refresh))
        if normalized_scope in ("all", "external"):
            result["external"] = json.loads(list_external_tool_capabilities(refresh=refresh))
        return json.dumps(result, ensure_ascii=False, default=str)
    except Exception as e:
        return json.dumps({"status": "error", "error": str(e)}, ensure_ascii=False)


TOOLS = [
    # ── 로컬/클라우드 서버 도구 ──
    run_daemon_job,
    get_system_status,
    get_today_schedule,
    read_recent_logs,
    run_pc_command,
    check_environment,
    list_callable_tools,
    refresh_callable_tools_registry,
    list_external_tool_capabilities,
    refresh_external_tool_capability_registry,
    list_agent_tool_capabilities,
    read_file,
    write_file,
    edit_file,
    list_directory,
    find_files,
    grep_code,
    # ── 원격 PC 제어 도구 ──
    list_connected_pcs,
    remote_pc_command,
    remote_pc_screenshot,
    remote_pc_status,
    remote_pc_file_read,
    remote_pc_file_write,
    remote_pc_process_list,
    # ── Claude CLI 제어 ──
    remote_claude_run,
    remote_claude_chat,
    # ── Docker/Git 관리 ──
    remote_docker_ps,
    remote_docker_logs,
    remote_git_status,
    remote_git_commit_push,
    # ── 웹 (검색 + 크롤링) ──
    remote_web_search,
    remote_web_crawl,
    # ── CI/CD (빌드 + 배포) ──
    remote_vercel_deploy,
    remote_npm_build_deploy,
    # ── 다중 명령 ──
    remote_batch_exec,
    # 주의: confirm_pending_command는 ALL_TOOLS에서 제외됨.
    # LLM이 owner 명시적 "진행" 의도를 우회해 자동 confirm 호출할 위험 → sora_engine
    # _tool_intent_fastpath 섹션 9 (deterministic) 에서만 호출되도록 격리.
    # get_jarvis_status/get_jarvis_audit_summary는 함수 정의 후 TOOLS.extend로 추가됨 (NameError 회피).
]

# 자비스 가시성 도구 추가 (정의는 위 라인. TOOLS.extend 로 순서 무관 추가)
try:
    TOOLS.extend([get_jarvis_status, get_jarvis_audit_summary, jarvis_web_search])
except NameError:
    pass  # 함수 정의 누락된 빌드에서도 import 자체는 실패하지 않도록
