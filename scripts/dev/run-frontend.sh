#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$ROOT/frontend"

command -v npm >/dev/null 2>&1 || { echo "npm missing" >&2; exit 1; }
exec npm run dev -- --hostname "${COUNTEROS_HOST:-127.0.0.1}" --port "${COUNTEROS_FRONTEND_PORT:-3000}"
