# -*- coding: utf-8 -*-
"""
Jarvis Process Supervisor — kill-switch 의 "나머지 절반" (프로세스 신호 + 취소 토큰)

설계: 20260524_JARVIS_ARCHITECTURE_v2.md §0.7 (kill switch 정직 보정)
검증(보고서 #5): "DB 플래그는 새 작업만 즉시 막고, 이미 도는 프로세스(브라우저/셸/영상)는
SIGTERM + 취소토큰 supervisor 없이 0.5초 내 못 멈춘다. DB=진실원천, 프로세스신호=즉시성 계층."

이 모듈:
- lease_is_valid: ledger kill_switch epoch vs 워커 lease_epoch 비교 (진실 원천 = DB)
- CancellationToken: 장기 도구가 ~200ms 마다 .cancelled 폴링 → 협조적 취소
- ProcessSupervisor: spawn 한 subprocess(PID) 등록 → kill 시 terminate(→grace 후 kill) 브로드캐스트
- enforce_kill: kill 활성 시 등록 프로세스 전부 강제 종료

cross-platform (Popen.terminate/kill). 순수 stdlib + ledger.
"""
from __future__ import annotations

import sys
import threading
import time
from pathlib import Path
from typing import Optional

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "queue"))
import sqlite_ledger as ledger  # type: ignore  # noqa: E402


class CancelledError(Exception):
    """kill switch 또는 lease epoch 무효로 작업이 취소됨."""


def lease_is_valid(conn, lease_epoch: int) -> bool:
    """진실 원천: kill 비활성 AND 현재 kill epoch == 워커가 claim 한 lease_epoch.

    kill 발동 시 epoch 가 +1 되므로, 이전 epoch 로 일하던 워커는 즉시 무효.
    """
    row = conn.execute("SELECT enabled, epoch FROM kill_switch WHERE id=1").fetchone()
    if row is None:
        return False
    return (not row["enabled"]) and int(row["epoch"]) == int(lease_epoch)


class CancellationToken:
    """장기 도구(브라우저/셸/영상)가 step 마다 check() 또는 .cancelled 로 협조 취소."""

    def __init__(self, conn, lease_epoch: int):
        self._conn = conn
        self._lease_epoch = int(lease_epoch)

    @property
    def cancelled(self) -> bool:
        return not lease_is_valid(self._conn, self._lease_epoch)

    def check(self) -> None:
        if self.cancelled:
            raise CancelledError(f"kill switch / epoch 무효 (lease_epoch={self._lease_epoch})")


class ProcessSupervisor:
    """spawn 된 subprocess 들을 추적 → kill 시 일괄 종료 (즉시성 계층)."""

    def __init__(self, grace_sec: float = 2.0):
        self._procs: dict[int, object] = {}   # pid -> Popen
        self._lock = threading.Lock()
        self._grace = grace_sec

    def register(self, proc) -> None:
        with self._lock:
            self._procs[proc.pid] = proc

    def unregister(self, pid: int) -> None:
        with self._lock:
            self._procs.pop(pid, None)

    def _reap(self) -> None:
        with self._lock:
            dead = [pid for pid, p in self._procs.items() if p.poll() is not None]
            for pid in dead:
                self._procs.pop(pid, None)

    def terminate_all(self) -> int:
        """등록된 모든 살아있는 프로세스에 terminate → grace 후 미종료면 kill. 종료시킨 수 반환."""
        self._reap()
        with self._lock:
            procs = list(self._procs.values())
        terminated = 0
        for p in procs:
            if p.poll() is None:
                try:
                    p.terminate()  # cross-platform (POSIX SIGTERM / Win TerminateProcess)
                    terminated += 1
                except Exception:
                    pass
        # grace 대기 후 잔존 강제 kill
        deadline = time.monotonic() + self._grace
        for p in procs:
            remaining = max(0.0, deadline - time.monotonic())
            try:
                p.wait(timeout=remaining)
            except Exception:
                try:
                    p.kill()
                except Exception:
                    pass
        self._reap()
        return terminated

    @property
    def active_count(self) -> int:
        self._reap()
        with self._lock:
            return len(self._procs)


def enforce_kill(conn, supervisor: ProcessSupervisor) -> bool:
    """kill 활성이면 등록 프로세스 전부 종료. 종료 수행 여부 반환."""
    if ledger.is_kill_active(conn):
        supervisor.terminate_all()
        return True
    return False


class KillSwitchWatcher(threading.Thread):
    """백그라운드 폴링(기본 200ms): kill 활성 감지 시 supervisor.terminate_all() 호출.

    "텔레그램 한 단어 → 0.5초 내 동결" 의 즉시성 계층. DB write(새 claim 차단)는 ledger 가,
    이미 도는 프로세스 종료는 본 watcher 가 담당.
    """

    def __init__(self, conn_factory, supervisor: ProcessSupervisor, poll_sec: float = 0.2):
        super().__init__(daemon=True)
        self._conn_factory = conn_factory   # 스레드 전용 연결 생성자 (sqlite 스레드 안전)
        self._supervisor = supervisor
        self._poll = poll_sec
        self._stop = threading.Event()
        self.fired = False

    def run(self) -> None:
        conn = self._conn_factory()
        try:
            while not self._stop.is_set():
                if ledger.is_kill_active(conn):
                    self._supervisor.terminate_all()
                    self.fired = True
                    break
                self._stop.wait(self._poll)
        finally:
            try:
                conn.close()
            except Exception:
                pass

    def stop(self) -> None:
        self._stop.set()


if __name__ == "__main__":
    import tempfile, os, subprocess
    db = os.path.join(tempfile.mkdtemp(), "ks.db")
    c = ledger.connect(db)
    ledger.init_schema(c)
    cl = ledger.enqueue(c, source="cli", title="t", command="x")
    claim = ledger.claim(c, worker_id="w1")
    tok = CancellationToken(c, claim.lease_epoch)
    print("before kill, cancelled:", tok.cancelled)
    sup = ProcessSupervisor(grace_sec=1.0)
    p = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])
    sup.register(p)
    ledger.activate_kill_switch(c, reason="smoke", actor="owner")
    n = sup.terminate_all()
    print(f"after kill, cancelled: {tok.cancelled}, terminated: {n}, proc_alive: {p.poll() is None}")
