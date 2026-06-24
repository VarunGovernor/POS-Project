#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)"
cd "$ROOT/frontend"

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

export HOSTNAME="${COUNTEROS_FRONTEND_HOST:-127.0.0.1}"
export PORT="${COUNTEROS_FRONTEND_PORT:-3000}"
export NEXT_PUBLIC_COUNTEROS_API_BASE_URL="${NEXT_PUBLIC_COUNTEROS_API_BASE_URL:-/api/v1}"

npm ci
npm run build
exec npm run start -- --hostname "$HOSTNAME" --port "$PORT"
