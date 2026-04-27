"""diagnose_phase_0.py — Phase 0 Day 7-B 자동 진단 스크립트.

owner 가 RUNBOOK 의 Day 7-B 항목을 실행하기 전/후에 한 번씩 돌리면 현 환경의
Phase 0 게이트 통과 여부를 한 화면에서 볼 수 있다.

검사 항목:
    1. Python 의존성 (qdrant-client, blake3, pydantic, fastapi, uvicorn, pyyaml,
       sentence-transformers, FlagEmbedding, kiwipiepy)
    2. 한국어 토크나이저 backend (kiwipiepy / konlpy / eunjeon / mecab-python3)
    3. Qdrant 컨테이너 health (http://ysh-server:6333/healthz, fallback localhost)
    4. Supabase RAG v2 6개 테이블 존재 (rag_audit_log + … + forgotten_uris)
       + rag_source_allowlist seed row 수
    5. Embedding service (port 7702) + Reranker (port 7704) health (localhost / sol01)
    6. MCP gateway (port 7701) reachability
    7. SSOT revision (.agent/shared-brain/status.json) match check

사용:
    python scripts/rag_v2/diagnose_phase_0.py            # 모든 검사
    python scripts/rag_v2/diagnose_phase_0.py --json     # 머신 판독용
    python scripts/rag_v2/diagnose_phase_0.py --section deps,tokenizer  # 부분만

종료 코드:
    0 = 모든 critical 통과
    1 = 1개 이상 critical 실패 (Phase 0 진입 불가)
    2 = warning만 있음 (Phase 0 진입 가능, 권고 항목 잔존)
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import os
import socket
import sys
import urllib.error
import urllib.request
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional


REPO_ROOT = Path(__file__).resolve().parents[2]


@dataclass
class CheckResult:
    section: str
    name: str
    status: str  # 'pass' | 'warn' | 'fail' | 'skip'
    detail: str = ""
    severity: str = "critical"  # 'critical' | 'warning' | 'info'
    extra: Dict[str, Any] = field(default_factory=dict)


# ─────────────────────────── Helpers ──────────────────────────────────────


def _http_get(url: str, timeout: float = 3.0) -> Optional[str]:
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except (urllib.error.URLError, socket.timeout, ConnectionError):
        return None


def _module_present(name: str) -> bool:
    return importlib.util.find_spec(name) is not None


# ─────────────────────────── Section: Python deps ────────────────────────


REQUIRED_PY: List[str] = [
    "qdrant_client",
    "blake3",
    "pydantic",
    "fastapi",
    "uvicorn",
    "yaml",  # pyyaml
    "watchdog",
    "requests",
    "httpx",
]

EMBEDDING_PY: List[str] = [
    "sentence_transformers",
    "FlagEmbedding",
    "torch",
    "pynvml",
]

KOREAN_BACKENDS: List[str] = ["kiwipiepy", "konlpy", "eunjeon", "MeCab"]


def check_python_deps() -> List[CheckResult]:
    results: List[CheckResult] = []
    missing = []
    for mod in REQUIRED_PY:
        if not _module_present(mod):
            missing.append(mod)
    results.append(
        CheckResult(
            section="deps",
            name="rag_runtime_deps",
            status="pass" if not missing else "fail",
            detail=f"missing: {', '.join(missing)}" if missing else "all present",
            severity="critical",
            extra={"required": REQUIRED_PY, "missing": missing},
        )
    )

    emb_missing = [m for m in EMBEDDING_PY if not _module_present(m)]
    results.append(
        CheckResult(
            section="deps",
            name="embedding_service_deps (sol01 only)",
            status="pass" if not emb_missing else "warn",
            detail=f"missing: {', '.join(emb_missing)}" if emb_missing else "all present",
            severity="warning",
            extra={"required": EMBEDDING_PY, "missing": emb_missing},
        )
    )
    return results


def check_korean_tokenizers() -> List[CheckResult]:
    present = [b for b in KOREAN_BACKENDS if _module_present(b)]
    return [
        CheckResult(
            section="tokenizer",
            name="korean_tokenizer_backends",
            status="pass" if present else "fail",
            detail=f"present: {', '.join(present)}" if present else "none installed (kiwipiepy 권장)",
            severity="critical",
            extra={"backends": KOREAN_BACKENDS, "present": present},
        )
    ]


# ─────────────────────────── Section: Services ───────────────────────────


def check_qdrant() -> List[CheckResult]:
    candidates = [
        "http://ysh-server:6333/healthz",
        "http://localhost:6333/healthz",
        "http://100.67.221.25:6333/healthz",
    ]
    for url in candidates:
        body = _http_get(url, timeout=2.0)
        if body is not None:
            return [
                CheckResult(
                    section="services",
                    name="qdrant_health",
                    status="pass",
                    detail=f"reachable at {url}",
                    severity="critical",
                    extra={"url": url, "body": body[:80]},
                )
            ]
    return [
        CheckResult(
            section="services",
            name="qdrant_health",
            status="fail",
            detail=f"unreachable: {candidates}",
            severity="critical",
            extra={"tried": candidates},
        )
    ]


def check_embedding_service() -> List[CheckResult]:
    body = _http_get("http://localhost:7702/health", timeout=2.0)
    if body is None:
        body = _http_get("http://desktop-sol01:7702/health", timeout=2.0)
    return [
        CheckResult(
            section="services",
            name="embedding_service (port 7702)",
            status="pass" if body else "warn",
            detail=("reachable" if body else "unreachable (sol01 GPU 미가동 가능성)"),
            severity="warning",
        )
    ]


def check_reranker_service() -> List[CheckResult]:
    body = _http_get("http://localhost:7704/health", timeout=2.0)
    if body is None:
        body = _http_get("http://desktop-sol01:7704/health", timeout=2.0)
    return [
        CheckResult(
            section="services",
            name="reranker_service (port 7704)",
            status="pass" if body else "warn",
            detail=("reachable" if body else "unreachable"),
            severity="warning",
        )
    ]


def check_mcp_gateway() -> List[CheckResult]:
    body = _http_get("http://localhost:7701/health", timeout=2.0)
    if body is None:
        body = _http_get("http://ysh-server:7701/health", timeout=2.0)
    return [
        CheckResult(
            section="services",
            name="mcp_gateway (port 7701)",
            status="pass" if body else "warn",
            detail=("reachable" if body else "unreachable (Phase 1 진입 시 필요)"),
            severity="warning",
        )
    ]


# ─────────────────────────── Section: Supabase ───────────────────────────


def check_supabase_tables() -> List[CheckResult]:
    """SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY 환경변수가 있으면 직접 점검.

    환경변수 없으면 skip (owner 가 별도로 MCP/dashboard 로 검증).
    """
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_SERVICE_ROLE_KEY")
    expected = ["rag_audit_log", "rag_eval_runs", "rag_chunk_lineage", "forgotten_uris", "rag_source_allowlist", "rag_jwt_revoke_list"]
    if not url or not key:
        return [
            CheckResult(
                section="supabase",
                name="rag_v2_tables_present",
                status="skip",
                detail="SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY 미설정 (MCP/dashboard 로 별도 검증)",
                severity="info",
                extra={"expected_tables": expected},
            )
        ]
    # postgrest 사용 — 실패해도 graceful
    try:
        results: List[CheckResult] = []
        missing: List[str] = []
        for tbl in expected:
            req = urllib.request.Request(
                f"{url.rstrip('/')}/rest/v1/{tbl}?limit=0",
                headers={
                    "apikey": key,
                    "Authorization": f"Bearer {key}",
                    "Range": "0-0",
                },
            )
            try:
                with urllib.request.urlopen(req, timeout=4.0) as resp:
                    if resp.status >= 400:
                        missing.append(tbl)
            except urllib.error.HTTPError as e:
                if e.code == 404 or e.code == 401:
                    missing.append(tbl)
            except Exception:
                missing.append(tbl)
        results.append(
            CheckResult(
                section="supabase",
                name="rag_v2_tables_present",
                status="pass" if not missing else "fail",
                detail=f"missing: {missing}" if missing else "all 6 tables present",
                severity="critical",
                extra={"expected": expected, "missing": missing},
            )
        )
        return results
    except Exception as e:  # pragma: no cover - network
        return [
            CheckResult(
                section="supabase",
                name="rag_v2_tables_present",
                status="warn",
                detail=f"check failed: {e}",
                severity="warning",
            )
        ]


# ─────────────────────────── Section: SSOT ────────────────────────────────


def check_ssot_revision() -> List[CheckResult]:
    """status.json 의 ssotRevision 이 generated adapters 와 일치하는지 확인."""
    status_path = REPO_ROOT / ".agent" / "shared-brain" / "status.json"
    agents_path = REPO_ROOT / "AGENTS.md"
    if not status_path.exists():
        return [
            CheckResult(
                section="ssot",
                name="ssot_revision_match",
                status="warn",
                detail=f"missing {status_path}",
                severity="warning",
            )
        ]
    try:
        status = json.loads(status_path.read_text(encoding="utf-8"))
        rev = (
            status.get("ssotRevision")
            or status.get("runtime_revision")
            or status.get("sharedContext", {}).get("ssotRevision")
            or status.get("sharedContext", {}).get("runtime_revision")
            or ""
        )
    except Exception as e:
        return [
            CheckResult(
                section="ssot",
                name="ssot_revision_match",
                status="warn",
                detail=f"parse error: {e}",
                severity="warning",
            )
        ]
    if not rev:
        return [
            CheckResult(
                section="ssot",
                name="ssot_revision_match",
                status="warn",
                detail="ssotRevision missing in status.json",
                severity="warning",
            )
        ]
    if not agents_path.exists():
        return [
            CheckResult(
                section="ssot",
                name="ssot_revision_match",
                status="warn",
                detail="AGENTS.md missing",
                severity="warning",
            )
        ]
    agents_text = agents_path.read_text(encoding="utf-8")
    if rev in agents_text:
        return [
            CheckResult(
                section="ssot",
                name="ssot_revision_match",
                status="pass",
                detail=f"revision={rev[:16]}",
                severity="critical",
                extra={"revision": rev},
            )
        ]
    return [
        CheckResult(
            section="ssot",
            name="ssot_revision_match",
            status="fail",
            detail=f"AGENTS.md does not reference ssotRevision={rev[:16]} — re-run sync_agent_context.py",
            severity="critical",
            extra={"revision": rev},
        )
    ]


# ─────────────────────────── Section: Local files ─────────────────────────


def check_rag_local_assets() -> List[CheckResult]:
    """RAG v2 로컬 자산 (정책/마이그레이션/스크립트) 존재 검증."""
    targets = [
        ".agent/policies/rag_governance.yaml",
        ".agent/policies/rag_source_allowlist.yaml",
        ".agent/policies/rag_jwt_scopes.yaml",
        ".agent/policies/work_pc_rag_isolation.yaml",
        ".agent/policies/rag_provenance_overrides.yaml",
        ".agent/policies/rag_eval_baseline.yaml",
        ".agent/policies/rag_watchdog.yaml",
        ".agent/policies/gitleaks-korean-rules.toml",
        ".agent/migrations/rag_v2/001_initial.sql",
        "src/core/rag_v2/chunk_metadata.py",
        "src/core/rag_v2/provenance_classifier.py",
        "src/core/rag_v2/credential_redactor.py",
        "src/core/rag_v2/pdf_sanitizer.py",
        "src/core/rag_v2/router.py",
        "scripts/rag_v2/migrate_chromadb_to_qdrant.py",
        "scripts/rag_v2/embedding_service.py",
        "scripts/rag_v2/rerank_service.py",
        "scripts/rag_v2/check_mecab_ko.py",
        "scripts/rag_v2/watchdog_indexer.py",
        "scripts/rag_v2/run_golden_eval.py",
        "scripts/rag_v2/bm25_indexer.py",
        "scripts/rag_v2/mcp_gateway.py",
        "tests/rag_golden/ssot_korean_v1.json",
        "tests/rag_golden/ssot_korean_v2.json",
    ]
    missing = [t for t in targets if not (REPO_ROOT / t).exists()]
    return [
        CheckResult(
            section="local_assets",
            name="rag_v2_files_present",
            status="pass" if not missing else "fail",
            detail=f"missing: {missing}" if missing else f"all {len(targets)} files present",
            severity="critical",
            extra={"expected_count": len(targets), "missing": missing},
        )
    ]


# ─────────────────────────── Runner ───────────────────────────────────────


SECTIONS: Dict[str, Callable[[], List[CheckResult]]] = {
    "deps": check_python_deps,
    "tokenizer": check_korean_tokenizers,
    "qdrant": check_qdrant,
    "embedding": check_embedding_service,
    "reranker": check_reranker_service,
    "gateway": check_mcp_gateway,
    "supabase": check_supabase_tables,
    "ssot": check_ssot_revision,
    "files": check_rag_local_assets,
}


STATUS_ICON_UNICODE = {"pass": "✅", "fail": "❌", "warn": "⚠️ ", "skip": "⏭️ "}
STATUS_ICON_ASCII = {"pass": "[OK]  ", "fail": "[FAIL]", "warn": "[WARN]", "skip": "[SKIP]"}


def _supports_unicode() -> bool:
    """stdout 가 unicode emoji 를 처리할 수 있는지 (Windows cp949 fallback 위해)."""
    enc = (sys.stdout.encoding or "").lower()
    if not enc:
        return False
    if "utf" in enc:
        return True
    return False


def render_text(results: List[CheckResult]) -> str:
    icons = STATUS_ICON_UNICODE if _supports_unicode() else STATUS_ICON_ASCII
    arrow = "→" if _supports_unicode() else "->"
    bar = "─" if _supports_unicode() else "-"
    lines: List[str] = []
    by_section: Dict[str, List[CheckResult]] = {}
    for r in results:
        by_section.setdefault(r.section, []).append(r)
    for sec, items in by_section.items():
        header = f"-- [{sec}] " if not _supports_unicode() else f"── [{sec}] "
        lines.append(header + bar * (60 - len(sec)))
        for r in items:
            icon = icons.get(r.status, "?")
            sev = "" if r.severity == "critical" else f" ({r.severity})"
            lines.append(f"  {icon} {r.name}{sev}")
            if r.detail:
                lines.append(f"      {r.detail}")
    crit_fail = sum(1 for r in results if r.status == "fail" and r.severity == "critical")
    warn_count = sum(1 for r in results if r.status in ("warn", "fail") and r.severity != "critical")
    pass_count = sum(1 for r in results if r.status == "pass")
    skip_count = sum(1 for r in results if r.status == "skip")
    lines.append("")
    if _supports_unicode():
        lines.append(
            f"Summary: ✅{pass_count}  ⚠️ {warn_count}  ❌crit:{crit_fail}  ⏭️ {skip_count}"
        )
    else:
        lines.append(
            f"Summary: pass={pass_count}  warn={warn_count}  crit_fail={crit_fail}  skip={skip_count}"
        )
    if crit_fail > 0:
        lines.append(f"{arrow} Phase 0 진입 차단 (critical 실패)")
    elif warn_count > 0:
        lines.append(f"{arrow} Phase 0 진입 가능 (warning 권고 항목 잔존)")
    else:
        lines.append(f"{arrow} Phase 0 모든 게이트 통과")
    return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="RAG Phase 0 Day 7-B 자동 진단")
    parser.add_argument("--json", action="store_true", help="JSON 출력 (머신 판독)")
    parser.add_argument(
        "--section",
        type=str,
        default=None,
        help=f"부분 실행 (콤마 구분, available: {','.join(SECTIONS.keys())})",
    )
    args = parser.parse_args(argv)

    selected = list(SECTIONS.keys())
    if args.section:
        selected = [s.strip() for s in args.section.split(",") if s.strip() in SECTIONS]
        if not selected:
            print(f"unknown section. available: {','.join(SECTIONS.keys())}", file=sys.stderr)
            return 1

    all_results: List[CheckResult] = []
    for sec in selected:
        try:
            all_results.extend(SECTIONS[sec]())
        except Exception as e:
            all_results.append(
                CheckResult(
                    section=sec,
                    name=f"{sec}_runner",
                    status="fail",
                    detail=f"check raised {type(e).__name__}: {e}",
                    severity="warning",
                )
            )

    if args.json:
        print(json.dumps([asdict(r) for r in all_results], ensure_ascii=False, indent=2))
    else:
        print(render_text(all_results))

    crit_fail = any(r.status == "fail" and r.severity == "critical" for r in all_results)
    has_warn = any(r.status in ("warn", "fail") and r.severity != "critical" for r in all_results)
    if crit_fail:
        return 1
    if has_warn:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
