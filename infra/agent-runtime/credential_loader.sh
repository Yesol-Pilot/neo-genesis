#!/usr/bin/env bash
# Neo Genesis Master Credential Loader (Bash / Cron)
# ===================================================
#
# 모든 bash / cron / pre-commit hook 이 source 해서 환경변수 자동 로드.
#
# 사용법:
#   source infra/agent-runtime/credential_loader.sh
#   # 이후 $HF_TOKEN, $GITHUB_PAT_YESOL_PILOT 등 사용 가능
#
# 또는 verbose:
#   NEO_CRED_VERBOSE=1 source infra/agent-runtime/credential_loader.sh
#
# 설계 원칙:
# - 단일 SSOT: 디바이스별 표준 위치 자동 탐지
# - 부모 shell 의 set 변수는 유지 (cron/CI 안전, set -a 사용 안 함)
# - 빈 값 변수는 override (부모의 빈 export 무시)
# - Portable bash 3+ (macOS 호환)
#
# Reference: .agent/knowledge/MASTER_CREDENTIAL_ACCESS_STANDARD.md

_neo_load_one() {
    local path="$1"
    [ -f "$path" ] || return 0

    while IFS= read -r line || [ -n "$line" ]; do
        # skip comments + blanks
        case "$line" in
            ''|\#*) continue ;;
        esac
        # must contain =
        case "$line" in
            *=*) ;;
            *) continue ;;
        esac

        local key="${line%%=*}"
        local value="${line#*=}"
        # trim whitespace
        key="$(printf '%s' "$key" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        value="$(printf '%s' "$value" | sed -e 's/^[[:space:]]*//' -e 's/[[:space:]]*$//')"
        # skip empty key
        [ -z "$key" ] && continue
        # strip surrounding quotes
        case "$value" in
            \"*\") value="${value#\"}"; value="${value%\"}" ;;
            \'*\') value="${value#\'}"; value="${value%\'}" ;;
        esac
        # respect already-set non-empty vars; override empty
        local current
        current=$(printenv "$key" 2>/dev/null || true)
        if [ -z "$current" ] || [ -z "$(printf '%s' "$current" | tr -d '[:space:]')" ]; then
            export "$key=$value"
        fi
    done < "$path"
}

_neo_load_credentials() {
    local home_dir="${HOME:-$USERPROFILE}"
    local cwd
    cwd="$(pwd)"

    # 우선순위 순 후보
    local paths=(
        "$home_dir/.neo-genesis/credentials.env"
        "/d/00.test/neo-genesis/.env.local"
        "/d/00.test/neo-genesis/.env"
        "D:/00.test/neo-genesis/.env.local"
        "D:/00.test/neo-genesis/.env"
        "$home_dir/neo-genesis-runtime/.env.local"
        "$home_dir/neo-genesis-runtime/.env"
        "$home_dir/sora/secrets/.env"
        "/home/ysh/sora/secrets/.env"
        "$cwd/.env.local"
        "$cwd/.env"
    )

    local p
    local seen=""
    for p in "${paths[@]}"; do
        case ":$seen:" in
            *":$p:"*) continue ;;
        esac
        seen="$seen:$p"
        _neo_load_one "$p"
    done
}

_neo_load_credentials

# verbose flag — `NEO_CRED_VERBOSE=1 source credential_loader.sh` 시 진단 출력
if [ "${NEO_CRED_VERBOSE:-0}" = "1" ]; then
    echo "[credential_loader.sh] loaded keys (presence only):" >&2
    for k in HF_TOKEN GITHUB_PAT_YESOL_PILOT OPENAI_API_KEY ANTHROPIC_API_KEY GEMINI_API_KEY \
             WIKIDATA_USERNAME QUICKSTATEMENTS_TOKEN SUPABASE_ACCESS_TOKEN VERCEL_TOKEN \
             NEO_ALERT_BOT_TOKEN PC_AGENT_TOKEN; do
        v=$(printenv "$k" 2>/dev/null || true)
        if [ -n "$v" ]; then
            echo "  [OK]   $k (len=${#v})" >&2
        else
            echo "  [miss] $k" >&2
        fi
    done
fi
