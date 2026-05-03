"""
Neo Genesis Master Credential Loader (Python)
==============================================

모든 에이전트(Claude / Codex / Sora / Gemini / Antigravity / Ollama 도구)가
이 모듈을 import 해서 환경변수를 자동으로 로드한다.

설계 원칙:
- 단일 SSOT: 마스터는 desktop-sol01 의 `D:/00.test/neo-genesis/.env.local`
- Cross-device: 디바이스별 표준 위치 자동 탐지 (Windows / Unix / Server)
- Override 안전: 부모 shell 에 이미 set 된 변수는 유지 (cron/CI 안전)
- 빈 값 override 허용: 부모에 빈 export 가 있으면 로컬 파일로 덮어씀
- 우선순위: 디바이스 로컬 캐시 > 프로젝트 로컬 > 서버 secrets

표준 사용법:
    from infra.agent_runtime.credential_loader import load_credentials
    load_credentials()
    # 이후 os.environ.get("HF_TOKEN") 등으로 접근

bash equivalent: `infra/agent-runtime/credential_loader.sh`

Reference: `.agent/knowledge/MASTER_CREDENTIAL_ACCESS_STANDARD.md`
"""
from __future__ import annotations

import os
import sys
from pathlib import Path
from typing import Iterable


# ════════════════════════════════════════════════════════════════
# 디바이스별 표준 lookup 위치 (우선순위 순)
# ════════════════════════════════════════════════════════════════

def _candidate_paths() -> list[Path]:
    """디바이스 / OS / runtime 별 lookup 후보 경로 (우선순위 순)."""
    home = Path.home()
    candidates: list[Path] = []

    # 1) 디바이스 로컬 캐시 (모든 fleet 디바이스 공통, mode 600)
    candidates.append(home / ".neo-genesis" / "credentials.env")

    # 2) 프로젝트 로컬 (.env.local 우선 + .env 폴백)
    #    Windows desktop-sol01 / desktop-yesol 표준 경로
    win_project = Path("D:/00.test/neo-genesis")
    candidates.append(win_project / ".env.local")
    candidates.append(win_project / ".env")

    # 3) Unix project root (ysh-server, mac-studio)
    unix_project = home / "neo-genesis-runtime"
    candidates.append(unix_project / ".env.local")
    candidates.append(unix_project / ".env")

    # 4) Sora 서버 secrets (ysh-server 운영)
    candidates.append(home / "sora" / "secrets" / ".env")
    candidates.append(Path("/home/ysh/sora/secrets/.env"))

    # 5) 호출자 cwd 기준 fallback (.env / .env.local)
    cwd = Path.cwd()
    candidates.append(cwd / ".env.local")
    candidates.append(cwd / ".env")

    # dedupe (preserve order)
    seen: set[str] = set()
    out: list[Path] = []
    for p in candidates:
        key = str(p)
        if key in seen:
            continue
        seen.add(key)
        out.append(p)
    return out


def _parse_env_line(line: str) -> tuple[str, str] | None:
    """`KEY=value` (with optional quoting) → (key, value). Comments / blanks → None."""
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        return None
    k, v = line.split("=", 1)
    k = k.strip()
    v = v.strip()
    # strip surrounding quotes
    if (v.startswith('"') and v.endswith('"')) or (v.startswith("'") and v.endswith("'")):
        v = v[1:-1]
    return (k, v) if k else None


def _load_env_file(path: Path, *, override_blank: bool = True, verbose: bool = False) -> int:
    """파일에서 환경변수 로드. Override 정책:
    - 이미 set + 비어있지 않은 변수 → 유지 (cron/CI 부모 shell 안전)
    - 빈 값 변수 → override 허용 (부모의 빈 export 무시)
    - 미정의 변수 → set
    """
    loaded = 0
    try:
        with path.open(encoding="utf-8") as f:
            for line in f:
                kv = _parse_env_line(line)
                if not kv:
                    continue
                k, v = kv
                cur = os.environ.get(k, "")
                if k not in os.environ:
                    os.environ[k] = v
                    loaded += 1
                elif override_blank and not cur.strip():
                    os.environ[k] = v
                    loaded += 1
    except (OSError, UnicodeDecodeError) as e:
        if verbose:
            print(f"[credential_loader] skip {path}: {type(e).__name__}: {e}",
                  file=sys.stderr)
    return loaded


def load_credentials(
    *,
    extra_paths: Iterable[Path | str] | None = None,
    verbose: bool = False,
) -> dict[str, int]:
    """모든 표준 lookup 위치에서 환경변수 로드.

    Returns:
        {path_str: loaded_count} — 어느 파일에서 몇 개 변수 로드됐는지
    """
    paths = _candidate_paths()
    if extra_paths:
        paths.extend(Path(p) for p in extra_paths)

    summary: dict[str, int] = {}
    for path in paths:
        if not path.exists():
            continue
        n = _load_env_file(path, verbose=verbose)
        if n > 0:
            summary[str(path)] = n
            if verbose:
                print(f"[credential_loader] {path}: {n} vars", file=sys.stderr)
    return summary


def require(*keys: str) -> None:
    """필수 환경변수 검증. 없으면 즉시 RuntimeError."""
    missing = [k for k in keys if not os.environ.get(k, "").strip()]
    if missing:
        raise RuntimeError(
            f"Required credentials missing: {missing}. "
            f"Run: python -c 'from infra.agent_runtime.credential_loader import load_credentials; load_credentials(verbose=True)'"
        )


def diagnose() -> None:
    """진단 출력 — 어떤 파일에서 어떤 키가 로드됐는지 (값은 숨김)."""
    summary = load_credentials(verbose=True)
    print("\n=== Loaded files ===")
    for path, n in summary.items():
        print(f"  {path}: {n} vars")

    print("\n=== Master credential keys (presence only, value redacted) ===")
    canonical = [
        "GITHUB_PAT_YESOL_PILOT",
        "HF_TOKEN",
        "OPENAI_API_KEY",
        "ANTHROPIC_API_KEY",
        "GEMINI_API_KEY",
        "GOOGLE_API_KEY",
        "PERPLEXITY_API_KEY",
        "WIKIDATA_USERNAME",
        "WIKIDATA_PASSWORD",
        "QUICKSTATEMENTS_TOKEN",
        "SUPABASE_ACCESS_TOKEN",
        "SUPABASE_URL",
        "SUPABASE_SERVICE_ROLE_KEY",
        "SORA_SUPABASE_URL",
        "SORA_SUPABASE_KEY",
        "VERCEL_TOKEN",
        "NEO_ALERT_BOT_TOKEN",
        "NEO_ALERT_CHAT_ID",
        "PC_AGENT_TOKEN",
        "DASHBOARD_TOKEN",
    ]
    for k in canonical:
        v = os.environ.get(k, "")
        if v.strip():
            print(f"  [OK]   {k}  (len={len(v)})")
        else:
            print(f"  [miss] {k}")


if __name__ == "__main__":
    diagnose()
