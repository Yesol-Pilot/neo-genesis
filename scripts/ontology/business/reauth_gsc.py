"""Re-authenticate Google Search Console OAuth (refresh token 만료 복구).

GSC refresh token 이 expired/revoked 되면 kpi_fetch GSC live 가 막힌다.
이 스크립트는 InstalledAppFlow(run_local_server)로 owner 의 기존 Google 계정
동의를 1회 받아 새 refresh_token 을 발급, .env.local 에 in-place 갱신한다.

보안: 토큰은 stdout 에 절대 출력하지 않음 (앞 6자 fingerprint 만). owner 의
기존 계정 OAuth = explicit 권한 필요 — owner 가 브라우저 탭에서 'Allow' 1회 클릭.

Usage:
    python scripts/ontology/business/reauth_gsc.py
    # → 브라우저 탭이 열림 → owner 가 Google 계정 Allow → .env.local 자동 갱신
"""
from __future__ import annotations

import sys
from pathlib import Path

try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")  # type: ignore[attr-defined]
except Exception:
    pass

REPO_ROOT = Path(__file__).resolve().parents[3]
ENV_LOCAL = REPO_ROOT / ".env.local"
CLIENT_SECRET = Path("D:/00.test/_secrets/neo-gsc-oauth-client.json")
SCOPES = ["https://www.googleapis.com/auth/webmasters.readonly"]
TOKEN_ENV_KEY = "GOOGLE_SEARCH_CONSOLE_REFRESH_TOKEN"


def update_env_local(new_token: str) -> bool:
    """Replace the refresh-token line in .env.local in place. Preserve all else."""
    if not ENV_LOCAL.exists():
        print(f"[ERROR] {ENV_LOCAL} not found", file=sys.stderr)
        return False
    lines = ENV_LOCAL.read_text(encoding="utf-8").splitlines()
    found = False
    for i, line in enumerate(lines):
        if line.strip().startswith(f"{TOKEN_ENV_KEY}="):
            lines[i] = f"{TOKEN_ENV_KEY}={new_token}"
            found = True
            break
    if not found:
        lines.append(f"{TOKEN_ENV_KEY}={new_token}")
    # backup before write
    backup = ENV_LOCAL.with_suffix(".local.bak-pre-gsc-reauth")
    backup.write_text(ENV_LOCAL.read_text(encoding="utf-8"), encoding="utf-8")
    ENV_LOCAL.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return True


def main() -> int:
    if not CLIENT_SECRET.exists():
        print(f"[ERROR] OAuth client not found: {CLIENT_SECRET}", file=sys.stderr)
        return 2
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        print("[ERROR] pip install google-auth-oauthlib", file=sys.stderr)
        return 2

    print("=" * 64)
    print("GSC 재인증 — 브라우저 탭이 곧 열립니다.")
    print("owner: Google 계정 선택 → 'Allow' 1회 클릭하면 끝.")
    print("=" * 64, flush=True)

    flow = InstalledAppFlow.from_client_secrets_file(str(CLIENT_SECRET), SCOPES)
    # opens default browser; blocks until consent redirect hits localhost
    creds = flow.run_local_server(port=0, prompt="consent",
                                  authorization_prompt_message="브라우저에서 동의해주세요: {url}",
                                  success_message="완료. 이 탭을 닫아도 됩니다.")
    rt = creds.refresh_token
    if not rt:
        print("[ERROR] no refresh_token returned (prompt=consent 필요)", file=sys.stderr)
        return 1
    ok = update_env_local(rt)
    if ok:
        # secret hygiene: only fingerprint, never full token
        print(f"[OK] new refresh_token 발급 + .env.local 갱신 (fp={rt[:6]}..., len={len(rt)})")
        print("[OK] backup: .env.local.bak-pre-gsc-reauth")
        print("[NEXT] python scripts/ontology/business/kpi_fetch.py --source gsc")
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
