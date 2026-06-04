# -*- coding: utf-8 -*-
"""gateway_guard 검증 — owner allowlist / dedup / token bucket.

독립 실행: python tests/core/test_jarvis_gateway_guard.py
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
import gateway_guard as G  # noqa: E402

OWNER = "1566967334"


class GatewayGuardTest(unittest.TestCase):
    def setUp(self):
        self.db = os.path.join(tempfile.mkdtemp(), "gw.db")
        self.conn = ledger.connect(self.db)
        ledger.init_schema(self.conn)

    def tearDown(self):
        self.conn.close()

    def _inbound(self, update_id, chat_id, text="hi", user_id=None):
        return G.check_inbound(self.conn, source="telegram", update_id=str(update_id),
                               chat_id=str(chat_id), user_id=str(user_id or chat_id),
                               text=text, owner_chat_id=OWNER)

    def test_owner_only(self):
        self.assertEqual(self._inbound(1, OWNER).action, G.Action.ACCEPT)
        self.assertEqual(self._inbound(2, "99999").action, G.Action.UNAUTHORIZED)

    def test_dedupe(self):
        d1 = self._inbound(100, OWNER, "같은메시지")
        self.assertEqual(d1.action, G.Action.ACCEPT)
        d2 = self._inbound(100, OWNER, "같은메시지")
        self.assertEqual(d2.action, G.Action.DUPLICATE)
        self.assertEqual(d1.request_id, d2.request_id)

    def test_rate_limit(self):
        # owner capacity=5 → 6번째부터 거부 (각 update_id 다르게 = dedup 통과)
        results = [self._inbound(200 + i, OWNER, f"msg{i}").action for i in range(7)]
        accepts = [a for a in results if a == G.Action.ACCEPT]
        limited = [a for a in results if a == G.Action.RATE_LIMITED]
        self.assertEqual(len(accepts), 5, results)
        self.assertGreaterEqual(len(limited), 1, results)

    def test_cost_route(self):
        # video 버킷 capacity=2 → 3번째 거부
        self.assertTrue(G.check_cost_route(self.conn, route="video"))
        self.assertTrue(G.check_cost_route(self.conn, route="video"))
        self.assertFalse(G.check_cost_route(self.conn, route="video"))
        # local 버킷은 넉넉
        self.assertTrue(G.check_cost_route(self.conn, route="local"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
