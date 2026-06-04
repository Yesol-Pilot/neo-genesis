#!/usr/bin/env bash
set -euo pipefail

ROLE="${1:-control}"
INTERVAL_SECONDS="${AINO_HA_INTERVAL_SECONDS:-60}"
PYTHON_BIN="${AINO_PYTHON:-python3}"
ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

export AINO_HA_ENABLED="${AINO_HA_ENABLED:-true}"
if [[ -f "$HOME/.neo-genesis/credentials.env" ]]; then
  while IFS= read -r raw_line || [[ -n "$raw_line" ]]; do
    line="${raw_line#"${raw_line%%[![:space:]]*}"}"
    line="${line%"${line##*[![:space:]]}"}"
    [[ -z "$line" || "$line" == \#* || "$line" != *=* ]] && continue
    key="${line%%=*}"
    value="${line#*=}"
    key="${key#"${key%%[![:space:]]*}"}"
    key="${key%"${key##*[![:space:]]}"}"
    value="${value#"${value%%[![:space:]]*}"}"
    value="${value%"${value##*[![:space:]]}"}"
    if [[ "$value" == \"*\" && "$value" == *\" ]]; then
      value="${value:1:${#value}-2}"
    elif [[ "$value" == \'*\' && "$value" == *\' ]]; then
      value="${value:1:${#value}-2}"
    fi
    [[ -n "$key" && -z "${!key:-}" ]] && export "$key=$value"
  done < "$HOME/.neo-genesis/credentials.env"
fi

if [[ "$ROLE" == "generate" || "$ROLE" == "monitor" ]]; then
  "$PYTHON_BIN" -m src.core.tiktok_aino.ha_publisher release-node-leases --operation "$ROLE" >/dev/null 2>&1 || true
fi

while true; do
  "$PYTHON_BIN" -m src.core.tiktok_aino.ha_publisher heartbeat --capability "$ROLE" >/dev/null 2>&1 || true
  if [[ "$ROLE" == "control" ]]; then
    "$PYTHON_BIN" -m src.core.tiktok_aino.ha_publisher controller-once
  else
    "$PYTHON_BIN" -m src.core.tiktok_aino.ha_publisher worker-once --operation "$ROLE"
  fi
  if [[ "${AINO_HA_ONCE:-false}" == "true" ]]; then
    break
  fi
  sleep "$INTERVAL_SECONDS"
done
