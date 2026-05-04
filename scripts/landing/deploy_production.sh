#!/usr/bin/env bash
# Manual production deploy for neogenesis.app
#
# Why this exists: as of 2026-05-04, the Vercel auto-deploy webhook on
# `Yesol-Pilot/landing` is not firing on push events. `gh api repos/Yesol-Pilot/landing/hooks`
# returns an empty array, and no auto-deployment was created for landing commit
# `c4b73ba` (P13). Reconnecting the Vercel-GitHub integration requires an owner
# login to vercel.com/yesol-pilots-projects/landing/settings/git → Reconnect.
#
# Until the webhook is reconnected, this script is the canonical fallback to
# trigger a production deploy after pushing to `Yesol-Pilot/landing master`.
#
# Usage:
#   bash scripts/landing/deploy_production.sh
#   # or from the project root: ./scripts/landing/deploy_production.sh
#
# What this does:
#   1. cd to src/landing
#   2. Verify origin/master is up-to-date with the local working tree
#   3. Run `npx vercel --prod --yes`
#   4. Verify the live URL aliases neogenesis.app
#
# Side effects:
#   - Creates a production deployment on Vercel (counts toward Hobby plan limits)
#   - Triggers a postbuild IndexNow ping (some endpoints may 403 until owner
#     completes Bing Webmaster Tools verification — this is expected and not a
#     deploy blocker)

set -euo pipefail

# Resolve project root regardless of where the script is invoked from
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/../.." && pwd )"
LANDING_DIR="$PROJECT_ROOT/src/landing"

if [[ ! -d "$LANDING_DIR" ]]; then
  echo "[deploy] ERROR: landing directory not found at $LANDING_DIR" >&2
  exit 1
fi

cd "$LANDING_DIR"

echo "[deploy] Verifying landing repo state..."
LOCAL_HEAD=$(git rev-parse HEAD)
REMOTE_HEAD=$(git rev-parse origin/master)
if [[ "$LOCAL_HEAD" != "$REMOTE_HEAD" ]]; then
  echo "[deploy] WARNING: local HEAD ($LOCAL_HEAD) does not match origin/master ($REMOTE_HEAD)"
  echo "[deploy] Push first or accept that this deploy reflects local-only state."
  read -r -p "Continue anyway? (y/N) " ans
  if [[ "$ans" != "y" && "$ans" != "Y" ]]; then
    echo "[deploy] Aborted."
    exit 1
  fi
fi

echo "[deploy] Triggering Vercel production deployment for commit $(git rev-parse --short HEAD)..."
npx vercel --prod --yes

echo ""
echo "[deploy] Verifying live alias..."
HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" "https://neogenesis.app/")
if [[ "$HTTP_CODE" == "200" ]]; then
  echo "[deploy] OK https://neogenesis.app/ returns $HTTP_CODE"
else
  echo "[deploy] WARNING https://neogenesis.app/ returns $HTTP_CODE (expected 200)"
fi

echo "[deploy] Done. If this script ran successfully but auto-deploy is still"
echo "[deploy] not firing on git push, owner needs to reconnect the Vercel-GitHub"
echo "[deploy] integration at:"
echo "[deploy]   https://vercel.com/yesol-pilots-projects/landing/settings/git"
