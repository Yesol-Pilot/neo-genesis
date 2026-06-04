# -*- coding: utf-8 -*-
"""
Jarvis TS/TSX Typed Outline IR — Python ast 가 못 푸는 TypeScript/TSX 정적 분석 (owner 문제 2.3)

설계: 20260524_JARVIS_ARCHITECTURE_v2.md §5.3 / §0.7
검증된 접근: py-tree-sitter + tree-sitter-typescript (증분·오류내성 파싱). 코드 원문 통째로 LLM 에
넘기지 않고, interface/type/enum/function/component/hook/class/method/route 골격만 콤팩트 IR 로 추출.

API (검증 2026-05, py-tree-sitter 최신): Query(lang, str) + QueryCursor(q).matches(node).
.ts → language_typescript(), .tsx/.jsx → language_tsx() (분리 필수).

WSL 경로(2.3 후반): lock key = (repo_id, rel_posix) — 절대경로 미사용(검증 보고서 #5). wslpath 양방향 brige.
순수: tree_sitter + tree_sitter_typescript (외부 LLM/네트워크 0).
"""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import asdict, dataclass
from functools import lru_cache
from pathlib import Path
from typing import Optional

from tree_sitter import Language, Parser, Query, QueryCursor
import tree_sitter_typescript as _tsts


@lru_cache(maxsize=2)
def _lang(is_tsx: bool) -> Language:
    return Language(_tsts.language_tsx() if is_tsx else _tsts.language_typescript())


_HOOK_RE = re.compile(r'^use[A-Z]')
_ROUTE = {"GET", "POST", "PUT", "DELETE", "PATCH", "HEAD", "OPTIONS"}

# 각 패턴이 선언노드 @decl + 이름노드 @name 캡처 (matches() 로 매치별 그룹 유지)
_QUERY_SRC = """
(interface_declaration name: (type_identifier) @name) @decl
(type_alias_declaration name: (type_identifier) @name) @decl
(enum_declaration name: (identifier) @name) @decl
(function_declaration name: (identifier) @name) @decl
(class_declaration name: (type_identifier) @name) @decl
(method_definition name: (property_identifier) @name) @decl
(lexical_declaration (variable_declarator
    name: (identifier) @name
    value: [(arrow_function) (function_expression)])) @decl
"""

_KIND = {
    "interface_declaration": "interface",
    "type_alias_declaration": "type",
    "enum_declaration": "enum",
    "function_declaration": "function",
    "class_declaration": "class",
    "method_definition": "method",
    "lexical_declaration": "function",  # arrow/expr const → 아래서 hook/component 재분류
}


@dataclass
class DeclIR:
    kind: str
    name: str
    line: int
    exported: bool = False
    default_export: bool = False
    is_async: bool = False
    signature: str = ""

    def to_dict(self) -> dict:
        return asdict(self)


def _signature(src: bytes, decl) -> str:
    raw = src[decl.start_byte:decl.end_byte]
    # 첫 줄 또는 본문 '{' 직전까지, 최대 120자
    head = raw.split(b"{", 1)[0].split(b"\n", 1)[0].strip()
    return head.decode("utf-8", "replace")[:120]


def extract(source: bytes, *, is_tsx: bool) -> list[DeclIR]:
    """TS/TSX 소스 → Typed Outline IR 리스트."""
    lang = _lang(is_tsx)
    tree = Parser(lang).parse(source)
    cur = QueryCursor(Query(lang, _QUERY_SRC))
    out: list[DeclIR] = []
    for _pat_idx, caps in cur.matches(tree.root_node):
        if "decl" not in caps or "name" not in caps:
            continue
        decl = caps["decl"][0]
        name_node = caps["name"][0]
        name = source[name_node.start_byte:name_node.end_byte].decode("utf-8", "replace")
        kind = _KIND.get(decl.type, "unknown")

        # exported / default: 부모(또는 조부모)가 export_statement 인지
        parent = decl.parent
        exported = parent is not None and parent.type == "export_statement"
        default_export = False
        if exported:
            pre = source[parent.start_byte:decl.start_byte]
            default_export = b"default" in pre

        is_async = source[decl.start_byte:decl.start_byte + 6] == b"async " \
            or b"async" in source[decl.start_byte:decl.start_byte + 24].split(b"(", 1)[0]

        # function 재분류: hook / component / route_handler
        if kind == "function":
            if _HOOK_RE.match(name):
                kind = "hook"
            elif name in _ROUTE:
                kind = "route_handler"
            elif name[:1].isupper() and is_tsx:
                kind = "component"

        out.append(DeclIR(kind=kind, name=name, line=name_node.start_point[0] + 1,
                          exported=exported, default_export=default_export,
                          is_async=is_async, signature=_signature(source, decl)))
    out.sort(key=lambda d: d.line)
    return out


_TS_EXT = {".ts", ".mts", ".cts"}
_TSX_EXT = {".tsx", ".jsx", ".js", ".mjs"}


def extract_file(path: str | Path) -> list[DeclIR]:
    p = Path(path)
    is_tsx = p.suffix.lower() in _TSX_EXT
    return extract(p.read_bytes(), is_tsx=is_tsx)


def outline_dir(root: str | Path) -> dict[str, list[dict]]:
    """디렉토리 전체 outline (node_modules/.next/dist 제외)."""
    root = Path(root)
    skip = {"node_modules", ".next", "dist", ".git", "build"}
    result: dict[str, list[dict]] = {}
    for ext in (*_TS_EXT, *_TSX_EXT):
        for fp in root.rglob(f"*{ext}"):
            if any(s in fp.parts for s in skip):
                continue
            try:
                result[fp.relative_to(root).as_posix()] = [d.to_dict() for d in extract_file(fp)]
            except Exception as e:
                result[fp.relative_to(root).as_posix()] = [{"error": str(e)}]
    return result


# ── WSL ↔ Windows 경로 (2.3 후반) — lock key = (repo_id, rel_posix), 절대경로 미사용 ──
def is_wsl() -> bool:
    try:
        return "microsoft" in Path("/proc/version").read_text().lower()
    except Exception:
        return False


def canonical_rel(repo_root: str | Path, path: str | Path) -> str:
    """lock/cache/memory 키용 정규 상대경로 (posix). 절대경로 차이(Win/WSL)를 흡수."""
    rr = Path(repo_root).resolve()
    return Path(path).resolve().relative_to(rr).as_posix()


@lru_cache(maxsize=256)
def to_wsl(win_path: str) -> str:
    return subprocess.run(["wslpath", "-u", win_path], capture_output=True, text=True,
                          check=True).stdout.strip()


@lru_cache(maxsize=256)
def to_win(posix_path: str) -> str:
    return subprocess.run(["wslpath", "-w", posix_path], capture_output=True, text=True,
                          check=True).stdout.strip()


if __name__ == "__main__":
    import json
    sample = b"""
export interface User { id: string; name: string }
export type Role = 'admin' | 'user'
export default function HomePage() { return null }
export function GET(req: Request) { return new Response() }
const useAuth = () => ({ user: null })
export const Card = ({title}: {title:string}) => null
class Service { async fetch() {} }
"""
    for d in extract(sample, is_tsx=True):
        print(f"{d.kind:14} {d.name:12} L{d.line} exported={d.exported} default={d.default_export}")
    print(json.dumps([d.to_dict() for d in extract(sample, is_tsx=True)], ensure_ascii=False)[:200])
