# -*- coding: utf-8 -*-
"""ts_outline 검증 — TS/TSX Typed Outline IR 추출 (owner 문제 2.3).

독립 실행: python tests/core/test_jarvis_ts_outline.py
"""
from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "src" / "core" / "jarvis"))
import ts_outline as T  # noqa: E402

TSX = b"""
export interface User { id: string; name: string }
export type Role = 'admin' | 'user'
enum Color { Red, Green }
export default function HomePage() { return null }
export function GET(req: Request) { return new Response() }
const useAuth = () => ({ user: null })
export const Card = ({ title }: { title: string }) => null
class Service { async fetchData() { return 1 } }
function helper() { return 2 }
"""

TS = b"""
export interface Config { url: string }
export function buildClient(c: Config) { return c }
function InternalThing() { return 0 }
"""


class TsOutlineTest(unittest.TestCase):
    def setUp(self):
        self.tsx = {d.name: d for d in T.extract(TSX, is_tsx=True)}
        self.ts = {d.name: d for d in T.extract(TS, is_tsx=False)}

    def test_interface_type_enum(self):
        self.assertEqual(self.tsx["User"].kind, "interface")
        self.assertTrue(self.tsx["User"].exported)
        self.assertEqual(self.tsx["Role"].kind, "type")
        self.assertTrue(self.tsx["Role"].exported)
        self.assertEqual(self.tsx["Color"].kind, "enum")
        self.assertFalse(self.tsx["Color"].exported)

    def test_default_component(self):
        d = self.tsx["HomePage"]
        self.assertEqual(d.kind, "component")
        self.assertTrue(d.exported)
        self.assertTrue(d.default_export)

    def test_route_handler(self):
        self.assertEqual(self.tsx["GET"].kind, "route_handler")
        self.assertTrue(self.tsx["GET"].exported)

    def test_hook(self):
        self.assertEqual(self.tsx["useAuth"].kind, "hook")

    def test_arrow_component_exported(self):
        d = self.tsx["Card"]
        self.assertEqual(d.kind, "component")
        self.assertTrue(d.exported)

    def test_class_and_method(self):
        self.assertEqual(self.tsx["Service"].kind, "class")
        self.assertEqual(self.tsx["fetchData"].kind, "method")
        self.assertTrue(self.tsx["fetchData"].is_async)

    def test_non_exported_function(self):
        # helper 은 소문자 시작(PascalCase 아님) → component 아닌 function, 비-export
        self.assertEqual(self.tsx["helper"].kind, "function")
        self.assertFalse(self.tsx["helper"].exported)

    def test_ts_no_component_classification(self):
        # .ts(비 tsx) 에서 PascalCase function 은 component 로 오분류되면 안 됨
        self.assertEqual(self.ts["buildClient"].kind, "function")
        self.assertEqual(self.ts["InternalThing"].kind, "function")  # is_tsx=False → component 아님
        self.assertEqual(self.ts["Config"].kind, "interface")

    def test_line_numbers(self):
        self.assertEqual(self.tsx["User"].line, 2)  # 첫 줄 비어있음 → 2

    def test_signature_captured(self):
        self.assertIn("interface User", self.tsx["User"].signature)

    def test_canonical_rel(self):
        root = Path(tempfile.mkdtemp())
        f = root / "src" / "app" / "page.tsx"
        f.parent.mkdir(parents=True)
        f.write_text("export default function P(){return null}")
        self.assertEqual(T.canonical_rel(root, f), "src/app/page.tsx")

    def test_extract_file(self):
        d = Path(tempfile.mkdtemp())
        fp = d / "comp.tsx"
        fp.write_bytes(b"export const useThing = () => 1\n")
        out = {x.name: x for x in T.extract_file(fp)}
        self.assertEqual(out["useThing"].kind, "hook")


if __name__ == "__main__":
    unittest.main(verbosity=2)
