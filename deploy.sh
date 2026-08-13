#!/usr/bin/env bash
# deploy.sh — push local changes to the DigitalOcean production server
# Usage:  ./deploy.sh           (deploy current branch)
#         ./deploy.sh --no-build (skip rebuild, just restart containers)
set -euo pipefail

SERVER="root@64.227.191.87"
REMOTE_DIR="/opt/ayuraai"
BRANCH=$(git rev-parse --abbrev-ref HEAD)
COMMIT=$(git rev-parse --short HEAD)

echo "▶ Deploying branch '$BRANCH' @ $COMMIT to $SERVER"

# ── 1. Sync files ────────────────────────────────────────────────────────────
echo "▶ Syncing files..."
# .env IS the production .env and must sync. .env.local must NOT: it is a local
# override that blanks the observability keys, and prod has no business carrying
# a file whose whole purpose is to switch reporting off.
rsync -az --delete \
  --exclude='.git' \
  --exclude='.env.local' \
  --exclude='client/node_modules' \
  --exclude='server/venv' \
  --exclude='server/data/chromadb' \
  --exclude='server/__pycache__' \
  --exclude='server/.pytest_cache' \
  --exclude='**/__pycache__' \
  --exclude='*.pyc' \
  ./ "$SERVER:$REMOTE_DIR/"

if [[ "${1:-}" == "--no-build" ]]; then
  echo "▶ Skipping build (--no-build). Restarting containers..."
  ssh "$SERVER" "cd $REMOTE_DIR && docker compose restart api worker web"
  echo "✅ Restarted. No rebuild."
  exit 0
fi

# ── 2. Build & restart ───────────────────────────────────────────────────────
echo "▶ Building containers on server..."
# `bash -o pipefail`, not a bare pipeline: ssh reports the exit status of the
# LAST command in the remote pipeline, so `docker compose build | tail` returned
# tail's 0 even when the build failed. This script's own `set -e` then saw
# success, went on to recreate the containers from the PREVIOUS images, and
# printed "✅ Deploy complete" over a deploy that had shipped nothing. The health
# check did not catch it either: it only probes /api/health, which the stale api
# image answers perfectly well.
# tail -40 because -6 truncated the actual compiler/bundler error to the frame
# around it, leaving only "did not complete successfully: exit code: 1".
ssh "$SERVER" "cd $REMOTE_DIR && bash -o pipefail -c 'docker compose build --no-cache api web worker 2>&1 | tail -40'"

echo "▶ Restarting services..."
# `up --force-recreate` intermittently races with its own container teardown
# ("Error response from daemon: removal of container … is already in progress")
# when a prior run left an orphaned/renamed container behind — leaving the OLD
# containers running and the new build un-applied. Deterministically stop+remove
# the three app services first, then a plain `up -d` recreates them fresh from the
# new images: no --force-recreate, no race. Retried once in case teardown is slow.
#
# The two halves are separated by `;`, not `&&`, and removal is best-effort. Joined
# by `&&` a failed removal skipped the bring-up entirely — and removal is exactly
# what loses this race. On 2026-08-14 `rm -fs` hit "removal already in progress",
# exited non-zero, `up -d` never ran, and production sat with api, web and worker
# removed until it was recreated by hand. Note the failure mode inverted: the
# comment above describes the old containers being left RUNNING, which is benign.
# This left nothing running at all.
#
# Failing to remove a container is survivable. Failing to start one is an outage,
# so bring-up must not be conditional on anything.
_recreate() {
  ssh "$SERVER" "cd $REMOTE_DIR && { docker compose rm -fs api web worker || true; } ; docker compose up -d --remove-orphans api web worker"
}
# `if ! cmd` rather than `cmd || { ... }`: under `set -e` a failing command on the
# right of `||` still aborts the script, so the recovery hint below would never have
# printed on the one path that needs it.
if ! _recreate; then
  echo "⚠️  restart raced — settling 6s and retrying once..."
  sleep 6
  if ! _recreate; then
    echo "❌ Containers did not come up. The site is DOWN. Recover with:"
    echo "   ssh $SERVER 'cd $REMOTE_DIR && docker compose up -d --remove-orphans api web worker'"
    exit 1
  fi
fi

# ── 3. Health check ──────────────────────────────────────────────────────────
echo "▶ Waiting for API to come up..."
sleep 12
STATUS=$(curl -sf -H "Host: ayuraai.in" https://ayuraai.in/api/health | python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('status','unknown'))" 2>/dev/null || echo "unreachable")

if [[ "$STATUS" == "healthy" ]]; then
  echo "✅ Deploy complete — https://ayuraai.in is healthy ($BRANCH @ $COMMIT)"
else
  echo "⚠️  Deploy finished but health check returned: $STATUS"
  echo "    Check logs: ssh $SERVER 'docker compose -f $REMOTE_DIR/docker-compose.yml logs api --tail=30'"
  exit 1
fi
