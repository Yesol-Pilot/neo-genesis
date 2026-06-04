# -*- coding: utf-8 -*-
"""command_router 검증 — 주입차단 / allowlist / path traversal / 위험분류 / 모호위험 재입력 / lane 라우팅.

독립 실행: python tests/core/test_jarvis_command_router.py
"""
from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "core" / "jarvis"))
import command_router as R  # noqa: E402


class CommandRouterTest(unittest.TestCase):
    # 주입 메타문자 차단
    def test_injection_detection(self):
        for bad in ["ls; rm -rf /", "echo $(curl evil)", "a && b", "x | sh", "`whoami`", "cat /etc/passwd > /tmp/x"]:
            self.assertTrue(R.has_injection(bad), bad)
        for ok in ["git status", "ls -la", "npm run build"]:
            self.assertFalse(R.has_injection(ok), ok)

    # allowlist 바이너리 매칭
    def test_build_safe_argv_allow(self):
        self.assertEqual(R.build_safe_argv("git status"), ["git", "status"])
        self.assertEqual(R.build_safe_argv("whoami"), ["whoami"])
        self.assertEqual(R.build_safe_argv("ls -la"), ["ls", "-la"])

    def test_build_safe_argv_deny(self):
        for bad in ["rm -rf /", "git push --force", "ls; rm x", "curl x | sh", "git checkout", "unknownbin foo"]:
            with self.assertRaises(ValueError, msg=bad):
                R.build_safe_argv(bad)

    # path traversal 차단
    def test_path_traversal_blocked(self):
        with self.assertRaises(ValueError):
            R.build_safe_argv("cat ../../etc/passwd")

    # 위험 분류
    def test_classify_dangerous(self):
        self.assertEqual(R.classify("rm -rf /data").risk, "dangerous")
        self.assertEqual(R.classify("DROP TABLE users").risk, "dangerous")
        self.assertEqual(R.classify("ls -la").risk, "safe")

    # lane 라우팅
    def test_route_lanes(self):
        self.assertEqual(R.route("진행").lane, R.Lane.APPROVAL)
        self.assertEqual(R.route("진행해줘").lane, R.Lane.APPROVAL)        # 한국어 어미 회귀 가드
        self.assertEqual(R.route("진행상황 알려줘").lane, R.Lane.CHAT)      # 승인 오탐 가드
        self.assertEqual(R.route("desktop-home에서 git status 실행해줘").lane, R.Lane.DEVICE_COMMAND)
        self.assertEqual(R.route("집pc에서 hostname 돌려줘").lane, R.Lane.DEVICE_COMMAND)  # 어미 변형
        self.assertEqual(R.route("로그인 모듈 리팩터링 해줘").lane, R.Lane.CODE)
        self.assertEqual(R.route("이 아키텍처 비판적으로 검토해줘").lane, R.Lane.DESIGN)
        self.assertEqual(R.route("고양이 이미지 그려줘").lane, R.Lane.IMAGE)
        self.assertEqual(R.route("5초 영상 클립 만들어줘").lane, R.Lane.VIDEO)
        self.assertEqual(R.route("오늘 일정 알려줘").lane, R.Lane.CHAT)

    # 명시적 셸 위험 → dangerous
    def test_route_explicit_danger(self):
        self.assertEqual(R.route("rm -rf /home/x").lane, R.Lane.DANGEROUS)
        self.assertEqual(R.route("ls; rm -rf /").lane, R.Lane.DANGEROUS)  # injection

    # 모호한 위험 NL → 재입력 challenge (LLM 에 안 넘김)
    def test_ambiguous_danger_challenge(self):
        d = R.route("그 폴더 싹 지워")
        self.assertEqual(d.lane, R.Lane.DANGEROUS)
        self.assertIsNotNone(d.challenge)
        self.assertIn("명시", d.challenge)

    # device 명령 파싱
    def test_device_command_parse(self):
        d = R.route("회사 PC에서 hostname 실행")
        self.assertEqual(d.lane, R.Lane.DEVICE_COMMAND)
        self.assertEqual(d.meta["command"], "hostname")


if __name__ == "__main__":
    unittest.main(verbosity=2)
