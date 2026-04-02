# -*- coding: utf-8 -*-
"""시스템/PC 관련 도구 — Phase 1-1 모듈화"""
import json
import logging
import os
import subprocess
import sys
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
    """오늘의 데몬 스케줄 전체를 반환합니다."""
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
_DASHBOARD_TOKEN = os.getenv("DASHBOARD_TOKEN", "neo-genesis-2026")
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


def list_connected_pcs() -> str:
    """현재 연결된 원격 PC 목록을 조회합니다. home-pc(집), work-pc(회사) 등."""
    result = _pc_api_get("/api/pc-agents")
    if not result or result == {}:
        return json.dumps({"message": "연결된 PC가 없습니다. 각 PC에서 sora_pc_agent.py를 실행하세요."})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_pc_command(pc_id: str, command: str) -> str:
    """원격 PC에서 셸 명령을 실행합니다.

    Args:
        pc_id: PC 식별자 (예: "home-pc", "work-pc"). list_connected_pcs로 확인 가능
        command: 실행할 명령어
    """
    result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "exec", "payload": {"command": command}})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_pc_screenshot(pc_id: str) -> str:
    """원격 PC의 스크린샷을 캡처합니다.

    Args:
        pc_id: PC 식별자 (예: "home-pc", "work-pc")
    """
    result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "screenshot", "payload": {"max_width": 1280, "quality": 75}})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_pc_status(pc_id: str) -> str:
    """원격 PC의 시스템 상태(CPU, RAM, 디스크)를 조회합니다.

    Args:
        pc_id: PC 식별자 (예: "home-pc", "work-pc")
    """
    result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "system_status", "payload": {}})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_pc_file_read(pc_id: str, file_path: str) -> str:
    """원격 PC의 파일을 읽습니다.

    Args:
        pc_id: PC 식별자
        file_path: 읽을 파일 경로
    """
    result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "read_file", "payload": {"path": file_path}})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_pc_file_write(pc_id: str, file_path: str, content: str) -> str:
    """원격 PC에 파일을 생성/덮어씁니다.

    Args:
        pc_id: PC 식별자
        file_path: 파일 경로
        content: 파일 내용
    """
    result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "write_file", "payload": {"path": file_path, "content": content}})
    return json.dumps(result, ensure_ascii=False, default=str)


def remote_pc_process_list(pc_id: str, filter_name: str = "") -> str:
    """원격 PC의 프로세스 목록을 조회합니다.

    Args:
        pc_id: PC 식별자
        filter_name: 프로세스 이름 필터 (빈 문자열이면 전체)
    """
    result = _pc_api_post(f"/api/pc-agents/{pc_id}/command", {"command": "process_list", "payload": {"filter": filter_name}})
    return json.dumps(result, ensure_ascii=False, default=str)


TOOLS = [
    # ── 로컬/클라우드 서버 도구 ──
    run_daemon_job,
    get_system_status,
    get_today_schedule,
    read_recent_logs,
    run_pc_command,
    check_environment,
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
]
