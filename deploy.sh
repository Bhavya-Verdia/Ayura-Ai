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
rsync -az --delete \
  --exclude='.git' \
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
ssh "$SERVER" "cd $REMOTE_DIR && docker compose build --no-cache api web worker 2>&1 | tail -6"

echo "▶ Restarting services..."
# `up --force-recreate` intermittently races with its own container teardown
# ("Error response from daemon: removal of container … is already in progress")
# when a prior run left an orphaned/renamed container behind — leaving the OLD
# containers running and the new build un-applied. Deterministically stop+remove
# the three app services first, then a plain `up -d` recreates them fresh from the
# new images: no --force-recreate, no race. Retried once in case teardown is slow.
_recreate() {
  ssh "$SERVER" "cd $REMOTE_DIR && docker compose rm -fs api web worker && docker compose up -d --remove-orphans api web worker"
}
_recreate || { echo "⚠️  restart raced — settling 6s and retrying once..."; sleep 6; _recreate; }

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
