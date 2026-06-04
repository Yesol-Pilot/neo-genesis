# -*- coding: utf-8 -*-
"""orchestrator e2e (섀도) — 게이트→라우팅→2-Phase→워커→증거보고 전 파이프라인.

라이브 CLI(codex/claude/ollama) 호출 없이 fake runner 주입. 라이브 시스템 무변경.
독립 실행: python tests/core/test_jarvis_orchestrator_e2e.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import unittest
from pathlib import Path

_JARVIS = Path(__file__).resolve().parents[2] / "src" / "core" / "jarvis"
_QUEUE = Path(__file__).resolve().parents[2] / "src" / "core" / "queue"
sys.path.insert(0, str(_QUEUE))
sys.path.insert(0, str(_JARVIS))
import sqlite_ledger as ledger  # noqa: E402
import worker_dispatch as wd  # noqa: E402
import orchestrator as O  # noqa: E402

OWNER = "1566967334"


def ok_runner(cmd):
    """성공 워커 시뮬레이션 (exit 0 + stdout)."""
    return wd.RunResult(returncode=0, stdout='{"result":"done"}', stderr="")


def fail_runner(cmd):
    """실패 워커 시뮬레이션 (exit 1) — 환각 보고 차단 검증용."""
    return wd.RunResult(returncode=1, stdout="", stderr="boom")


class OrchestratorE2ETest(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "orch.db")
        self.conn = ledger.connect(self.db)
        ledger.init_schema(self.conn)

    def tearDown(self):
        self.conn.close()

    def _msg(self, text, uid, runner=ok_runner, chat=OWNER):
        return O.handle_message(self.conn, source="telegram", update_id=str(uid),
                                chat_id=chat, user_id=chat, text=text,
                                owner_chat_id=OWNER, runner=runner)

    # 일반 코드 작업 → 실행 + 증거 기반 성공 보고
    def test_code_task_executes_with_evidence(self):
        r = self._msg("로그인 버그 디버그 해줘", 1)
        self.assertEqual(r["action"], "executed")
        self.assertEqual(r["engine"], "codex_cli")
        self.assertTrue(r["dispatch"]["can_report_success"])
        self.assertIn("실행 완료", r["report"])

    # 워커 실패 시 "실행 완료" 거짓 보고 차단 (증거 게이트 = 환각 방지)
    def test_failed_worker_no_false_success(self):
        r = self._msg("리팩터링 해줘", 2, runner=fail_runner)
        self.assertFalse(r["dispatch"]["can_report_success"])
        self.assertNotIn("실행 완료", r["report"])
        self.assertIn("증거 없음", r["report"])

    # 설계 요청 → Claude lane
    def test_design_routes_to_claude(self):
        r = self._msg("이 아키텍처 비판적으로 검토해줘", 3)
        self.assertEqual(r["engine"], "claude_cli")

    # 모호한 위험 → 재입력 challenge (실행 X)
    def test_ambiguous_danger_challenge(self):
        r = self._msg("그 폴더 싹 지워", 4)
        self.assertEqual(r["action"], "challenge")
        self.assertIn("명시", r["report"])

    # 명시 위험 → warn + confirm_id (실행 X) → "진행" → 실행 (Phase A→B)
    def test_explicit_danger_warn_then_obey(self):
        r1 = self._msg("rm -rf /home/ysh/old 실행", 5)
        self.assertEqual(r1["action"], "warn")
        self.assertIn("confirm_id", r1)
        # waiting_approval 작업 1건 존재, 아직 미실행
        cnt = self.conn.execute("SELECT COUNT(*) n FROM jobs WHERE status='waiting_approval'").fetchone()["n"]
        self.assertEqual(cnt, 1)
        # owner "진행" → 승인 후 실행
        r2 = self._msg("진행", 6)
        self.assertEqual(r2["action"], "approved_executed")

    # 게이트: 비-owner 차단
    def test_unauthorized_blocked(self):
        r = self._msg("뭐든 해줘", 7, chat="99999")
        self.assertEqual(r["action"], "unauthorized")

    # 게이트: 중복 update 무시
    def test_dedupe(self):
        a = self._msg("같은 메시지야", 100)
        b = self._msg("같은 메시지야", 100)
        self.assertEqual(b["action"], "duplicate")

    # kill switch 활성 → 실행 거부
    def test_kill_switch_blocks(self):
        ledger.activate_kill_switch(self.conn, reason="test", actor="owner")
        r = self._msg("코드 빌드 해줘", 8)
        self.assertIn(r["action"], ("frozen", "no_claim"))
        self.assertNotIn("실행 완료", r["report"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
