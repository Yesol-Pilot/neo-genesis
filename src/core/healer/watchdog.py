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
            "health_url": None,  # HTTP 엔드포인트 없음 → 프로세스 존재 확인
            "start_module": "src.core.neo_scheduler",
            "process_name": "neo_scheduler",
            "timeout_ms": 3000,
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
        """프로세스 존재 확인."""
        try:
            cmd = (
                f"Get-Process -ErrorAction SilentlyContinue | "
                f"Where-Object {{ $_.CommandLine -like '*{svc['process_name']}*' }} | "
                f"Select-Object Id, CPU | ConvertTo-Json"
            )
            r = subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=10,
            )
            if r.stdout.strip():
                return {"alive": True, "details": f"{svc['display']} 프로세스 존재"}
            return {"alive": False, "details": f"{svc['display']} 프로세스 없음"}
        except Exception as e:
            return {"alive": False, "details": f"확인 실패: {e}"}

    def _kill_service(self, svc: dict):
        """기존 서비스 프로세스 종료."""
        try:
            cmd = (
                f"Get-Process -ErrorAction SilentlyContinue | "
                f"Where-Object {{ $_.CommandLine -like '*{svc['process_name']}*' }} | "
                f"Stop-Process -Force -ErrorAction SilentlyContinue"
            )
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", cmd],
                capture_output=True, text=True, timeout=10,
            )
        except Exception:
            pass
