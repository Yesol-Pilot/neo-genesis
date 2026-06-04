# -*- coding: utf-8 -*-
"""
Jarvis control-plane ledger 검증 — fencing / kill switch / approval FSM / dedup / token bucket / evidence gate.

독립 실행: `python tests/core/test_sqlite_fencing_queue.py`
(pytest/unittest 디스커버리에도 호환)

정본: src/core/queue/sqlite_ledger.py
"""
from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# 레포 패키지 설정과 무관하게 모듈을 import (standalone 실행 보장)
_QUEUE_DIR = Path(__file__).resolve().parents[2] / "src" / "core" / "queue"
sys.path.insert(0, str(_QUEUE_DIR))
import sqlite_ledger as L  # noqa: E402


class LedgerTest(unittest.TestCase):
    def setUp(self):
        self.dir = tempfile.mkdtemp()
        self.db = os.path.join(self.dir, "test.db")
        self.conn = L.connect(self.db)
        L.init_schema(self.conn)

    def tearDown(self):
        self.conn.close()

    # 1) 큐 happy path
    def test_enqueue_claim_complete(self):
        jid = L.enqueue(self.conn, source="cli", title="t", command="git status")
        c = L.claim(self.conn, worker_id="w1")
        self.assertIsNotNone(c)
        self.assertEqual(c.job_id, jid)
        ok = L.complete(self.conn, job_id=jid, worker_id="w1",
                        fencing_token=c.fencing_token, lease_epoch=c.lease_epoch)
        self.assertTrue(ok)
        row = self.conn.execute("SELECT status FROM jobs WHERE job_id=?", (jid,)).fetchone()
        self.assertEqual(row["status"], "succeeded")

    # 2) fencing — stale worker 의 늦은 commit 거부 (핵심 불변식)
    def test_fencing_blocks_stale_worker(self):
        jid = L.enqueue(self.conn, source="cli", title="t", command="cmd")
        # worker A 가 아주 짧은 lease 로 claim → 즉시 만료
        a = L.claim(self.conn, worker_id="A", lease_ttl=0)
        self.assertIsNotNone(a)
        time.sleep(0.01)
        # worker B 가 만료된 job 을 재-claim (더 높은 fencing token)
        b = L.claim(self.conn, worker_id="B")
        self.assertIsNotNone(b)
        self.assertGreater(b.fencing_token, a.fencing_token)
        # A 가 늦게 깨어나 commit 시도 → 거부 (0 rows)
        a_ok = L.complete(self.conn, job_id=jid, worker_id="A",
                          fencing_token=a.fencing_token, lease_epoch=a.lease_epoch)
        self.assertFalse(a_ok, "stale worker A 의 commit 은 fencing 으로 거부돼야 함")
        # B 는 정상 commit
        b_ok = L.complete(self.conn, job_id=jid, worker_id="B",
                          fencing_token=b.fencing_token, lease_epoch=b.lease_epoch)
        self.assertTrue(b_ok)
        # stale_commit_blocked 감사 1건 이상
        n = self.conn.execute(
            "SELECT COUNT(*) n FROM audit WHERE event_type='stale_commit_blocked'").fetchone()["n"]
        self.assertGreaterEqual(n, 1)

    # 3) kill switch — claim 거부 + in-flight commit 거부 + epoch bump
    def test_kill_switch_freezes(self):
        jid = L.enqueue(self.conn, source="cli", title="t", command="cmd")
        c = L.claim(self.conn, worker_id="w1")
        new_epoch = L.activate_kill_switch(self.conn, reason="test halt", actor="owner")
        self.assertTrue(L.is_kill_active(self.conn))
        # 활성 중 claim 불가
        self.assertIsNone(L.claim(self.conn, worker_id="w2"))
        # in-flight worker 의 commit 거부 (epoch 불일치)
        ok = L.complete(self.conn, job_id=jid, worker_id="w1",
                        fencing_token=c.fencing_token, lease_epoch=c.lease_epoch)
        self.assertFalse(ok, "kill 이후 in-flight commit 은 거부돼야 함")
        self.assertGreater(new_epoch, c.lease_epoch)
        # job frozen
        st = self.conn.execute("SELECT status FROM jobs WHERE job_id=?", (jid,)).fetchone()["status"]
        self.assertEqual(st, "frozen")
        # 해제 후 재가동
        L.clear_kill_switch(self.conn, actor="owner")
        self.assertFalse(L.is_kill_active(self.conn))

    # 4) ingress dedup — update_id + content_hash
    def test_dedupe(self):
        ch = L.content_hash("chat1", "u1", "안녕", "")
        dup1, rid1 = L.seen_or_mark(self.conn, source="telegram", update_id="100", chash=ch)
        self.assertFalse(dup1)
        dup2, rid2 = L.seen_or_mark(self.conn, source="telegram", update_id="100", chash=ch)
        self.assertTrue(dup2)
        self.assertEqual(rid1, rid2)
        # 다른 update_id 인데 같은 content → content_hash 2차 키로 중복
        dup3, _ = L.seen_or_mark(self.conn, source="telegram", update_id="101", chash=ch)
        self.assertTrue(dup3)

    # 5) token bucket — capacity 소진 후 거부, refill 후 허용
    def test_token_bucket(self):
        key = "chat:owner"
        # capacity 3, refill 매우 느리게
        self.assertTrue(L.token_bucket_consume(self.conn, key=key, capacity=3, refill_per_sec=0.0001))
        self.assertTrue(L.token_bucket_consume(self.conn, key=key, capacity=3, refill_per_sec=0.0001))
        self.assertTrue(L.token_bucket_consume(self.conn, key=key, capacity=3, refill_per_sec=0.0001))
        self.assertFalse(L.token_bucket_consume(self.conn, key=key, capacity=3, refill_per_sec=0.0001),
                         "capacity 소진 후 거부돼야 함")
        # 빠른 refill 버킷은 즉시 허용
        self.assertTrue(L.token_bucket_consume(self.conn, key="fast", capacity=1, refill_per_sec=1000))

    # 6) approval FSM — 승인 / 만료 / action 변경 재승인 / 바인딩 위반
    def test_approval_fsm(self):
        # 정상 승인
        aid, cid = L.request_approval(self.conn, chat_id="c1", user_id="u1",
                                      action_hash="H1", summary="rm -rf 위험", ttl=60)
        st = L.decide_approval(self.conn, approval_id=aid, confirm_id=cid,
                               chat_id="c1", user_id="u1", current_action_hash="H1", approve=True)
        self.assertEqual(st, "approved")

        # action 변경 시 재승인 강제 (TOCTOU)
        aid2, cid2 = L.request_approval(self.conn, chat_id="c1", user_id="u1",
                                        action_hash="H2", summary="배포", ttl=60)
        st2 = L.decide_approval(self.conn, approval_id=aid2, confirm_id=cid2,
                                chat_id="c1", user_id="u1", current_action_hash="H2_CHANGED", approve=True)
        self.assertEqual(st2, "invalid")

        # 바인딩 위반 (다른 user 가 버튼 탭)
        aid3, cid3 = L.request_approval(self.conn, chat_id="c1", user_id="u1",
                                        action_hash="H3", summary="x", ttl=60)
        st3 = L.decide_approval(self.conn, approval_id=aid3, confirm_id=cid3,
                                chat_id="c1", user_id="ATTACKER", current_action_hash="H3", approve=True)
        self.assertEqual(st3, "invalid")

        # 만료
        aid4, cid4 = L.request_approval(self.conn, chat_id="c1", user_id="u1",
                                        action_hash="H4", summary="x", ttl=0)
        time.sleep(0.01)
        st4 = L.decide_approval(self.conn, approval_id=aid4, confirm_id=cid4,
                                chat_id="c1", user_id="u1", current_action_hash="H4", approve=True)
        self.assertEqual(st4, "expired")

    # 7) 증거 게이트 — tool_runs 없으면 성공 보고 불가
    def test_evidence_gate(self):
        jid = L.enqueue(self.conn, source="cli", title="t", command="cmd")
        self.assertFalse(L.can_report_success(self.conn, job_id=jid), "증거 없으면 성공 보고 불가")
        # 실패한 run 으로는 여전히 불가
        L.record_tool_run(self.conn, job_id=jid, tool_name="shell", status="failed", exit_code=1)
        self.assertFalse(L.can_report_success(self.conn, job_id=jid))
        # 성공 + exit 0 + output_hash → 허용
        L.record_tool_run(self.conn, job_id=jid, tool_name="shell", status="succeeded",
                          exit_code=0, output_hash="abc123")
        self.assertTrue(L.can_report_success(self.conn, job_id=jid))

    # 8) 멱등 enqueue
    def test_idempotent_enqueue(self):
        j1 = L.enqueue(self.conn, source="cron", title="daily", command="x", idempotency_key="daily-20260524")
        j2 = L.enqueue(self.conn, source="cron", title="daily", command="x", idempotency_key="daily-20260524")
        self.assertEqual(j1, j2, "동일 idempotency_key 는 같은 job 반환")


if __name__ == "__main__":
    unittest.main(verbosity=2)
