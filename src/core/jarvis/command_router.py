# -*- coding: utf-8 -*-
"""
Jarvis Deterministic Command Router — 환각 차단 + 주입 방어 + lane 라우팅 (owner 문제 2.2)

설계: 20260524_JARVIS_ARCHITECTURE_v2.md §5.2 / §0.6 / §0.7
검증된 원칙: 위험 명령 execute 결정에서 LLM 배제 (Gemini Flash/Pro 둘 다 rm-rf 환각 실측).
위험 분류·allowlist 는 결정론(regex/코드), LLM 은 NL 이해·포맷만.

기능:
1) 주입 메타문자 선차단 (shell metachar: ; & | ` $() && || > < 등)
2) allowlist 바이너리 매칭: shlex.split + shell=False + 플래그/서브커맨드/경로 인자 검증 + path traversal 차단
3) 모호한 위험 자연어 → "대상·옵션 명시 재입력" 강제 (LLM 에 안 넘김)
4) lane 라우팅: approval / device_command / dangerous / code / design / image / video / chat
5) 위험도 = command_governor.classify_risk 재사용(있으면), 없으면 내장 최소셋 (단일 SSOT 지향)

순수 stdlib + optional governor import. shell=True 절대 금지.
"""
from __future__ import annotations

import os
import re
import shlex
import sys
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Optional

# ── command_governor.classify_risk 재사용 (위험 패턴 단일 SSOT). 실패 시 내장 fallback ──
try:  # pragma: no cover - import 경로 robust
    sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "security"))
    import command_governor as _gov  # type: ignore
    _classify_risk = _gov.classify_risk
except Exception:  # governor 미가용 → 내장 최소 위험셋
    _gov = None
    _FALLBACK_DANGER = [
        (re.compile(r'\brm\s+-[a-z]*r[a-z]*f|\brm\s+-[a-z]*f[a-z]*r', re.I), "rm -rf 계열"),
        (re.compile(r'\b(del|erase)\s+/[sf]|rmdir\s+/s', re.I), "Windows 강제/재귀 삭제"),
        (re.compile(r'\b(mkfs|format)\b|dd\s+.*of=/dev/', re.I), "디스크 포맷/덮어쓰기"),
        (re.compile(r'\b(DROP|TRUNCATE)\s+(TABLE|DATABASE|SCHEMA)', re.I), "DB 파괴"),
        (re.compile(r'Remove-Item\b.*-Recurse', re.I), "PowerShell 재귀 삭제"),
    ]

    def _classify_risk(command: str):
        if not command or not command.strip():
            return ("safe", "", "")
        for pat, reason in _FALLBACK_DANGER:
            if pat.search(command):
                return ("dangerous", reason, "대상 경로/범위 명시 확인")
        return ("safe", "", "")


# ── 1) 주입 메타문자 (구조화 실행에서 원천 차단) ──
_INJECTION_RE = re.compile(
    r'[;`]'                    # 명령 분리 / 백틱
    r'|\|\|?'                  # pipe / or
    r'|&&|&'                   # and / background
    r'|\$\(|\$\{|\$[A-Za-z_]'  # 명령치환 / 변수확장
    r'|>>|>|<'                 # 리다이렉션
    r'|\bIEX\b|\bInvoke-Expression\b'  # PowerShell RCE
    r'|\beval\b|\bexec\b'      # eval/exec
)

# ── path traversal / 허용 루트 ──
_TRAVERSAL_RE = re.compile(r'\.\.[\\/]|[\\/]\.\.|%2e%2e|\x00', re.I)


def _allowed_roots() -> list[str]:
    env = os.getenv("JARVIS_ALLOWED_ROOTS", "")
    if env:
        return [r for r in env.split(os.pathsep) if r]
    # 기본: 레포 루트(neo-genesis) + 시스템 temp (env 로 좁히기 권장)
    repo_root = Path(__file__).resolve().parents[3]
    import tempfile
    return [str(repo_root), tempfile.gettempdir()]


# ── 2) allowlist: 바이너리 → 허용 규칙 (0-pass safe lane. 변형 명령은 governor warn-then-obey 경유) ──
ALLOWED_COMMANDS: dict[str, dict] = {
    "ls": {"flags": {"-l", "-la", "-a", "-h", "--color=never"}, "path_arg": True},
    "dir": {"flags": set(), "path_arg": True},
    "df": {"flags": {"-h", "-H"}},
    "ps": {"flags": {"aux", "-ef", "-e"}},
    "whoami": {"flags": set()},
    "hostname": {"flags": set()},
    "pwd": {"flags": set()},
    "echo": {"flags": set(), "free_text_arg": True},
    "cat": {"flags": {"-n"}, "path_arg": True},
    "git": {"subcommands": {"status", "log", "diff", "pull", "fetch", "branch", "show"}},
    "npm": {"subcommands": {"run", "test", "ci", "list", "outdated"}},
    "pnpm": {"subcommands": {"run", "test", "list", "build"}},
    "node": {"flags": {"--version", "-v"}},
    "python": {"flags": {"--version", "-V"}},
    "docker": {"subcommands": {"ps", "images", "logs", "inspect", "stats"}},
    "systemctl": {"subcommands": {"status", "is-active", "list-units"}, "unit_re": r'^[A-Za-z0-9\-_.@]+\.(service|timer|socket)$'},
}


class Lane(str, Enum):
    APPROVAL = "approval"          # "진행"/confirm → confirm_pending
    DEVICE_COMMAND = "device_cmd"  # "<device>에서 <cmd> 실행" 결정론 fastpath
    DANGEROUS = "dangerous"        # 위험 → governor warn-then-obey
    CODE = "code"                  # Codex CLI
    DESIGN = "design"              # Claude CLI (설계/비판)
    IMAGE = "image"                # 로컬 ComfyUI
    VIDEO = "video"                # 로컬 ComfyUI
    CHAT = "chat"                  # 로컬 L1 (qwen2.5:3b)


@dataclass
class RouteDecision:
    lane: Lane
    risk: str = "safe"            # safe | dangerous
    reason: str = ""
    recommendation: str = ""
    suggested_engine: str = ""    # codex_cli | claude_cli | comfyui | local_l1 | governor
    safe_argv: Optional[list[str]] = None
    challenge: Optional[str] = None  # 모호한 위험 NL → 재입력 요구 메시지
    matched: str = ""
    meta: dict = field(default_factory=dict)


# ── 라우팅 키워드 (한/영) ──
# 한국어 어미(해/해줘/줘) 때문에 \b(word boundary) 사용 금지 — 전체 메시지 앵커(^…$)로 구분.
# 승인 = 메시지가 사실상 "진행/승인/.." (+어미) 단독이거나, "/approve <id>" / "confirm <id>".
_APPROVAL_RE = re.compile(
    r'^\s*(?:진행|승인|approve|confirm|go|ok|오케이|오키)(?:해|해줘|할게|시켜|줘)?\s*$'
    r'|^\s*(?:/approve|/confirm|confirm|approve)\s+\S+',
    re.I)
# "<device>에서 <cmd> 실행/돌려/구동/해(줘)" — 동사 뒤 어미(\S*) 허용 + 문장 끝 앵커.
_DEVICE_RE = re.compile(r'(.{1,24}?)\s*에서\s+(.+?)\s*(?:실행|돌려|돌리|구동|run|해)\S*\s*$', re.I)
_DANGER_KO_EN = re.compile(r'(지워|삭제|밀어|날려|초기화|포맷|format|delete|drop|wipe|destroy|rm\b|del\b)', re.I)
_LANE_KEYWORDS: list[tuple[Lane, str, re.Pattern]] = [
    (Lane.CODE, "codex_cli", re.compile(r'(코드|구현|리팩터|리팩토링|디버그|버그|빌드|테스트|배포|커밋|commit|push|pull|merge|refactor|debug|build|deploy|fix|PR|패치|patch|lint)', re.I)),
    (Lane.DESIGN, "claude_cli", re.compile(r'(설계|아키텍처|architecture|리뷰|검토|비판|전략|기획|design|review|critique|plan|tradeoff|분석해|평가해)', re.I)),
    (Lane.IMAGE, "comfyui", re.compile(r'(이미지|그림|사진|그려|image|picture|일러스트|썸네일|thumbnail)', re.I)),
    (Lane.VIDEO, "comfyui", re.compile(r'(영상|비디오|동영상|video|클립|clip)', re.I)),
]


def has_injection(raw: str) -> bool:
    return bool(_INJECTION_RE.search(raw or ""))


def build_safe_argv(raw_command: str, *, max_len: int = 2048) -> list[str]:
    """shlex.split + allowlist 검증. 통과 시 안전 argv, 실패 시 ValueError. shell=False 전제."""
    if not raw_command or not raw_command.strip():
        raise ValueError("빈 명령")
    if len(raw_command) > max_len:
        raise ValueError("명령 길이 초과")
    if has_injection(raw_command):
        raise ValueError("셸 인젝션 메타문자 탐지")
    try:
        tokens = shlex.split(raw_command, posix=True)
    except ValueError as e:
        raise ValueError(f"파싱 불가: {e}")
    if not tokens:
        raise ValueError("토큰 없음")
    name = tokens[0].lower()
    spec = ALLOWED_COMMANDS.get(name)
    if spec is None:
        raise ValueError(f"허용되지 않은 바이너리: {tokens[0]!r}")
    argv = [name]
    roots = _allowed_roots()
    for tok in tokens[1:]:
        if tok.startswith("-"):
            if tok not in spec.get("flags", set()):
                raise ValueError(f"허용되지 않은 플래그: {tok!r}")
            argv.append(tok)
        elif "subcommands" in spec:
            if tok in spec["subcommands"]:
                argv.append(tok)
            elif spec.get("unit_re") and re.match(spec["unit_re"], tok):
                argv.append(tok)
            else:
                raise ValueError(f"허용되지 않은 서브커맨드/인자: {tok!r}")
        elif spec.get("path_arg"):
            if _TRAVERSAL_RE.search(tok):
                raise ValueError(f"path traversal 의심: {tok!r}")
            resolved = str(Path(tok).resolve())
            if roots and not any(resolved.startswith(r) for r in roots):
                raise ValueError(f"허용 루트 밖 경로: {tok!r}")
            argv.append(tok)
        elif spec.get("free_text_arg"):
            argv.append(tok)  # echo 등: injection 은 이미 위에서 차단됨
        else:
            raise ValueError(f"허용되지 않은 인자: {tok!r}")
    return argv


def classify(raw_command: str) -> RouteDecision:
    """구조화 명령 위험 분류 (주입 → governor 위험패턴 순). lane 미포함."""
    if has_injection(raw_command):
        return RouteDecision(lane=Lane.DANGEROUS, risk="dangerous",
                             reason="셸 인젝션 메타문자", recommendation="구조화(argv) 형식으로 재입력",
                             suggested_engine="governor", matched="injection")
    level, reason, rec = _classify_risk(raw_command)
    if level == "dangerous":
        return RouteDecision(lane=Lane.DANGEROUS, risk="dangerous", reason=reason,
                             recommendation=rec, suggested_engine="governor", matched="danger_pattern")
    return RouteDecision(lane=Lane.CHAT, risk="safe", suggested_engine="local_l1")


def route(text: str) -> RouteDecision:
    """자연어/명령 입력 → lane 결정 (결정론). LLM 미사용.

    우선순위: approval > injection/danger(구조화 명령) > device_command
            > 모호한 위험 NL(재입력 강제) > code/design/image/video > chat.
    """
    t = (text or "").strip()
    if not t:
        return RouteDecision(lane=Lane.CHAT, suggested_engine="local_l1")

    # 1) 승인
    if _APPROVAL_RE.search(t):
        return RouteDecision(lane=Lane.APPROVAL, suggested_engine="governor", matched="approval")

    # 2) 주입/위험 (명시적 셸 명령처럼 보이는 입력)
    if has_injection(t):
        return RouteDecision(lane=Lane.DANGEROUS, risk="dangerous", reason="셸 인젝션 메타문자",
                             recommendation="구조화(argv)로 재입력", suggested_engine="governor", matched="injection")
    level, reason, rec = _classify_risk(t)
    if level == "dangerous":
        return RouteDecision(lane=Lane.DANGEROUS, risk="dangerous", reason=reason,
                             recommendation=rec, suggested_engine="governor", matched="danger_pattern")

    # 3) "<device>에서 <cmd> 실행" 결정론 fastpath
    m = _DEVICE_RE.search(t)
    if m:
        return RouteDecision(lane=Lane.DEVICE_COMMAND, suggested_engine="device_hub",
                             matched="device_pattern",
                             meta={"device_phrase": m.group(1).strip(), "command": m.group(2).strip()})

    # 4) 모호한 위험 NL ("폴더 싹 지워" 등 — 대상/옵션 불명) → 재입력 강제 (LLM 에 안 넘김)
    if _DANGER_KO_EN.search(t):
        return RouteDecision(
            lane=Lane.DANGEROUS, risk="dangerous", reason="모호한 위험 명령 (대상/범위 불명확)",
            recommendation="명시적 재입력 필요", suggested_engine="governor", matched="ambiguous_danger",
            challenge=("위험 작업입니다. 자연어 승인으로 실행하지 않습니다.\n"
                       "대상 장치 · 정확한 경로/리소스 · 옵션 · 예상 영향 범위를 명시해 다시 입력하세요.\n"
                       "예: /exec --device desktop-home --tool <allowlisted> --target <경로> --mode dry_run"))

    # 5) lane 키워드
    for lane, engine, pat in _LANE_KEYWORDS:
        if pat.search(t):
            return RouteDecision(lane=lane, suggested_engine=engine, matched="keyword")

    # 6) 기본 = 일반 대화 → 로컬 L1
    return RouteDecision(lane=Lane.CHAT, suggested_engine="local_l1", matched="default")


# ── 자가 진단 ──
if __name__ == "__main__":
    samples = [
        "진행", "desktop-home에서 git status 실행해줘", "rm -rf /home/x", "그 폴더 싹 지워",
        "로그인 컴포넌트 리팩터링 해줘", "이 아키텍처 비판적으로 검토해줘", "고양이 이미지 그려줘",
        "5초 클립 영상 만들어줘", "오늘 날씨 어때?", "ls -la; rm -rf /",
    ]
    for s in samples:
        d = route(s)
        print(f"[{d.lane.value:11}] {d.suggested_engine:11} risk={d.risk:9} <- {s[:40]}")
    print("\nbuild_safe_argv tests:")
    for cmd in ["git status", "ls -la", "rm -rf /", "git push --force", "echo hi; rm x"]:
        try:
            print(f"  OK   {build_safe_argv(cmd)}  <- {cmd}")
        except ValueError as e:
            print(f"  DENY ({e})  <- {cmd}")
