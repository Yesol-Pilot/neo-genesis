# -*- coding: utf-8 -*-
"""process_supervisor 검증 — kill-switch 프로세스 계층 (취소토큰 + 프로세스 종료).

독립 실행: python tests/core/test_jarvis_process_supervisor.py
"""
from __future__ import annotations

import os
import subprocess
import sys
import tempfile
import time
import unittest
from pathlib import Path

_JARVIS = Path(__file__).resolve().parents[2] / "src" / "core" / "jarvis"
_QUEUE = Path(__file__).resolve().parents[2] / "src" / "core" / "queue"
sys.path.insert(0, str(_QUEUE))
sys.path.insert(0, str(_JARVIS))
import sqlite_ledger as ledger  # noqa: E402
import process_supervisor as PS  # noqa: E402


class ProcessSupervisorTest(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "ks.db")
        self.conn = ledger.connect(self.db)
        ledger.init_schema(self.conn)

    def tearDown(self):
        self.conn.close()

    def _claim(self):
        ledger.enqueue(self.conn, source="cli", title="t", command="x")
        return ledger.claim(self.conn, worker_id="w1")

    def _sleeper(self):
        return subprocess.Popen([sys.executable, "-c", "import time; time.sleep(30)"])

    # lease_is_valid: 정상 claim 은 valid, kill 후 무효
    def test_lease_validity(self):
        claim = self._claim()
        self.assertTrue(PS.lease_is_valid(self.conn, claim.lease_epoch))
        ledger.activate_kill_switch(self.conn, reason="t", actor="owner")
        self.assertFalse(PS.lease_is_valid(self.conn, claim.lease_epoch))

    # CancellationToken: kill 후 cancelled True + check() 예외
    def test_cancellation_token(self):
        claim = self._claim()
        tok = PS.CancellationToken(self.conn, claim.lease_epoch)
        self.assertFalse(tok.cancelled)
        tok.check()  # 예외 없어야 함
        ledger.activate_kill_switch(self.conn, reason="t", actor="owner")
        self.assertTrue(tok.cancelled)
        with self.assertRaises(PS.CancelledError):
            tok.check()

    # ProcessSupervisor: 등록 프로세스 terminate_all 로 종료
    def test_terminate_all(self):
        sup = PS.ProcessSupervisor(grace_sec=2.0)
        procs = [self._sleeper() for _ in range(3)]
        for p in procs:
            sup.register(p)
        self.assertEqual(sup.active_count, 3)
        n = sup.terminate_all()
        self.assertEqual(n, 3)
        time.sleep(0.2)
        for p in procs:
            self.assertIsNotNone(p.poll(), "프로세스가 종료돼야 함")
        self.assertEqual(sup.active_count, 0)

    # enforce_kill: kill 활성 시 프로세스 종료
    def test_enforce_kill(self):
        sup = PS.ProcessSupervisor(grace_sec=2.0)
        p = self._sleeper()
        sup.register(p)
        # kill 비활성 → enforce 안 함
        self.assertFalse(PS.enforce_kill(self.conn, sup))
        self.assertIsNone(p.poll())
        # kill 활성 → 종료
        ledger.activate_kill_switch(self.conn, reason="t", actor="owner")
        self.assertTrue(PS.enforce_kill(self.conn, sup))
        time.sleep(0.2)
        self.assertIsNotNone(p.poll())

    # KillSwitchWatcher: 백그라운드 폴링이 kill 감지 → 종료 (즉시성 계층)
    def test_watcher_background(self):
        sup = PS.ProcessSupervisor(grace_sec=2.0)
        p = self._sleeper()
        sup.register(p)
        watcher = PS.KillSwitchWatcher(lambda: ledger.connect(self.db), sup, poll_sec=0.1)
        watcher.start()
        time.sleep(0.3)
        ledger.activate_kill_switch(self.conn, reason="t", actor="owner")
        t0 = time.monotonic()
        while watcher.is_alive() and time.monotonic() - t0 < 5:
            time.sleep(0.1)
        watcher.stop()
        self.assertTrue(watcher.fired, "watcher 가 kill 을 감지해야 함")
        time.sleep(0.2)
        self.assertIsNotNone(p.poll(), "watcher 가 프로세스를 종료시켜야 함")


if __name__ == "__main__":
    unittest.main(verbosity=2)
