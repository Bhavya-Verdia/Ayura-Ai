#!/usr/bin/env bash
# `nginx -t` on client/nginx.conf + security-headers.conf, in the image the
# Dockerfile's runtime stage uses, before a deploy can ship them. A config that
# fails here leaves the production web container unable to start.
#
# Needs docker. Uses a throwaway self-signed certificate at the path nginx.conf
# names, and resolves the `api` upstream to localhost, which is all `nginx -t`
# checks of either.
set -euo pipefail
cd "$(dirname "$0")/.."

image=$(awk '/^FROM nginx/ { print $2 }' Dockerfile)
[ -n "$image" ] || { echo "no 'FROM nginx' stage in Dockerfile" >&2; exit 1; }

tmp=$(mktemp -d "${TMPDIR:-/tmp}/check-nginx.XXXXXX")
trap 'rm -rf "$tmp"' EXIT
mkdir -p "$tmp/live/ayuraai.in"
openssl req -x509 -newkey rsa:2048 -nodes -days 1 -subj /CN=ayuraai.in \
  -keyout "$tmp/live/ayuraai.in/privkey.pem" -out "$tmp/live/ayuraai.in/fullchain.pem" 2>/dev/null
# mktemp makes the directory owner-only; the container reads it as another
# user wherever docker runs in a VM (Docker Desktop, Colima). Throwaway key.
chmod -R a+rX "$tmp"

docker run --rm --add-host api:127.0.0.1 \
  -v "$tmp:/etc/letsencrypt:ro" \
  -v "$PWD/nginx.conf:/etc/nginx/conf.d/default.conf:ro" \
  -v "$PWD/security-headers.conf:/etc/nginx/snippets/security-headers.conf:ro" \
  --entrypoint nginx "$image" -t
