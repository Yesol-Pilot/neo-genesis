# -*- coding: utf-8 -*-
"""
ServiceWatchdog — 핵심 서비스 생존 감시 + 자동 재시작

소라의 핵심 인프라(대시보드, 스케줄러)가 죽으면
자동으로 감지하고 재시작합니다.
"""
import logging
import os
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional
from urllib.request import urlopen, Request
from urllib.error import URLError

try:
    import psutil
except ImportError:
    psutil = None

from src.core.runtime.single_instance import list_matching_processes

logger = logging.getLogger("neo.healer.watchdog")

_PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent.parent


class ServiceWatchdog:
    """핵심 서비스 생존 감시 + 자동 재시작."""

    # 서비스 정의 — 환경변수와 기본값 조합
    SERVICES = {
        # 클라우드 모드에서는 supervisord가 Gateway를 관리하므로 Watchdog 체크 비활성화
        # "sora_dashboard": {
        #     "display": "소라 대시보드",
        #     "health_url": f"http://localhost:{os.getenv('SORA_DASHBOARD_PORT', '7700')}/api/status",
        #     "start_module": "src.core.sora_dashboard",
        #     "process_name": "sora_dashboard",
        #     "timeout_ms": 5000,
        # },
        "neo_scheduler": {
            "display": "네오 스케줄러",
            "health_url": None,
            "start_module": "src.core.neo_scheduler",
            "process_name": "neo_scheduler",
            "timeout_ms": 3000,
            "managed_by_daemon": True,
        },
    }

    def __init__(self):
        self._restart_count: dict[str, int] = {}
        self._max_restarts = int(os.getenv("WATCHDOG_MAX_RESTARTS", "3"))

    def check(self, service_name: str) -> dict:
        """서비스 상태 확인.

        Returns:
            {"alive": bool, "details": str}
        """
        svc = self.SERVICES.get(service_name)
        if not svc:
            return {"alive": False, "details": f"알 수 없는 서비스: {service_name}"}

        # HTTP 헬스체크
        if svc["health_url"]:
            return self._check_http(svc)

        # 통합 데몬에 내장된 스케줄러는 별도 프로세스가 없어도 정상일 수 있다.
        if svc.get("managed_by_daemon"):
            daemon_status = self._check_integrated_daemon_scheduler()
            if daemon_status["alive"]:
                return daemon_status

        # 프로세스 존재 확인
        return self._check_process(svc)

    def check_all(self) -> dict:
        """모든 서비스 상태 확인."""
        results = {}
        for name in self.SERVICES:
            results[name] = self.check(name)
        return results

    def restart(self, service_name: str) -> str:
        """서비스 재시작."""
        svc = self.SERVICES.get(service_name)
        if not svc:
            return f"알 수 없는 서비스: {service_name}"

        if svc.get("managed_by_daemon"):
            daemon_status = self._check_integrated_daemon_scheduler()
            if daemon_status["alive"]:
                msg = "[Watchdog] 통합 데몬이 이미 스케줄러를 포함하고 있어 재시작을 건너뜀"
                logger.info(msg)
                return msg

        # 재시작 횟수 제한
        count = self._restart_count.get(service_name, 0)
        if count >= self._max_restarts:
            msg = f"[Watchdog] {svc['display']} 재시작 횟수 초과 ({count}/{self._max_restarts})"
            logger.error(msg)
            return msg

        try:
            # 기존 프로세스 킬
            self._kill_service(svc)
            time.sleep(1)

            # 새로 시작
            cmd = [sys.executable, "-m", svc["start_module"]]
            subprocess.Popen(
                cmd,
                cwd=str(_PROJECT_ROOT),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW
                if sys.platform == "win32" else 0,
            )

            self._restart_count[service_name] = count + 1
            msg = f"[Watchdog] {svc['display']} 재시작 완료 ({count + 1}회차)"
            logger.info(msg)
            return msg

        except Exception as e:
            msg = f"[Watchdog] {svc['display']} 재시작 실패: {e}"
            logger.error(msg)
            return msg

    def reset_restart_count(self, service_name: Optional[str] = None):
        """재시작 카운터 초기화 (매일 자정에 호출)."""
        if service_name:
            self._restart_count.pop(service_name, None)
        else:
            self._restart_count.clear()

    def _check_http(self, svc: dict) -> dict:
        """HTTP 헬스체크."""
        try:
            timeout_s = svc.get("timeout_ms", 5000) / 1000
            req = Request(svc["health_url"], method="GET")
            with urlopen(req, timeout=timeout_s) as resp:
                if resp.status == 200:
                    return {"alive": True, "details": f"{svc['display']} OK"}
                return {"alive": False, "details": f"HTTP {resp.status}"}
        except URLError as e:
            return {"alive": False, "details": f"연결 불가: {e.reason}"}
        except Exception as e:
            return {"alive": False, "details": f"헬스체크 실패: {e}"}

    def _check_process(self, svc: dict) -> dict:
        """프로세스 존재 확인.

        2026-04-29 보강: Linux 컨테이너에서 powershell 미설치로 FileNotFoundError 발생 후
        매 5분마다 false-positive 재시작 시도되던 문제 fix.
        managed_by_daemon=True 서비스는 Linux 에서 worker 안에 통합돼 별도 process 가 없는 게
        정상이므로 환경 미지원 / 프로세스 부재 시 alive=True 로 graceful 처리.
        """
        try:
            if self._find_service_pids(svc):
                return {"alive": True, "details": f"{svc['display']} 프로세스 존재"}
            # 2026-04-29: Linux 에서 managed_by_daemon 서비스는 worker 통합이 정상
            if sys.platform != "win32" and svc.get("managed_by_daemon"):
                return {"alive": True, "details": f"{svc['display']} (Linux: worker 내부 통합 가정)"}
            return {"alive": False, "details": f"{svc['display']} 프로세스 없음"}
        except FileNotFoundError as e:
            # 2026-04-29: powershell 등 환경 미지원 도구 → managed_by_daemon 이면 정상 가정
            if svc.get("managed_by_daemon"):
                return {"alive": True, "details": f"{svc['display']} (환경 도구 미지원, 데몬 통합 가정: {e.filename})"}
            return {"alive": False, "details": f"확인 실패: {e}"}
        except Exception as e:
            return {"alive": False, "details": f"확인 실패: {e}"}

    def _kill_service(self, svc: dict):
        """기존 서비스 프로세스 종료."""
        try:
            pids = self._find_service_pids(svc)
            if pids and psutil:
                for pid in pids:
                    try:
                        psutil.Process(pid).kill()
                    except (psutil.Error, OSError):
                        pass
                return

            if sys.platform == "win32":
                cmd = (
                    "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
                    f"Where-Object {{ $_.CommandLine -like '*{svc['process_name']}*' }} | "
                    "ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }"
                )
                subprocess.run(
                    ["powershell", "-NoProfile", "-Command", cmd],
                    capture_output=True, text=True, timeout=10,
                )
        except Exception:
            pass

    def _find_service_pids(self, svc: dict) -> list[int]:
        matches = list_matching_processes([svc["process_name"]])
        pids = [int(match["pid"]) for match in matches if match.get("pid")]
        if pids or sys.platform != "win32":
            return pids

        cmd = (
            "Get-CimInstance Win32_Process -ErrorAction SilentlyContinue | "
            f"Where-Object {{ $_.CommandLine -like '*{svc['process_name']}*' }} | "
            "Select-Object -ExpandProperty ProcessId"
        )
        result = subprocess.run(
            ["powershell", "-NoProfile", "-Command", cmd],
            capture_output=True, text=True, timeout=10,
        )
        return [int(line.strip()) for line in (result.stdout or "").splitlines() if line.strip().isdigit()]

    def _check_integrated_daemon_scheduler(self) -> dict:
        """통합 데몬 내부 스케줄러 상태 확인.

        현재 운영 구조에서는 APScheduler가 `neo_genesis_daemon.py` 내부에 통합되어
        별도 `neo_scheduler` 프로세스가 없어도 정상이다. 따라서 데몬 PID와 대시보드
        헬스 상태를 우선 기준으로 본다.
        """
        try:
            live_daemons = list_matching_processes(["neo_genesis_daemon.py"])
            if live_daemons:
                count = len(live_daemons)
                details = "통합 데몬 내부 스케줄러로 운영 중"
                if count > 1:
                    details += f" (중복 데몬 {count}개 감지)"
                return {"alive": True, "details": details}

            daemon_pid_file = _PROJECT_ROOT / "daemon.pid"
            if daemon_pid_file.exists():
                daemon_pid = daemon_pid_file.read_text(encoding="utf-8").strip()
                if daemon_pid:
                    if psutil and daemon_pid.isdigit() and psutil.pid_exists(int(daemon_pid)):
                        return {"alive": True, "details": "통합 데몬 내부 스케줄러로 운영 중"}
                    if sys.platform == "win32":
                        cmd = (
                            f"$p = Get-Process -Id {daemon_pid} -ErrorAction SilentlyContinue; "
                            "if ($p) { 'RUNNING' }"
                        )
                        r = subprocess.run(
                            ["powershell", "-NoProfile", "-Command", cmd],
                            capture_output=True, text=True, timeout=5,
                        )
                        if "RUNNING" in (r.stdout or ""):
                            return {"alive": True, "details": "통합 데몬 내부 스케줄러로 운영 중"}
        except Exception:
            pass

        return {"alive": False, "details": "통합 데몬 미감지"}
