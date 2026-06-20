#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
DB="${COUNTEROS_DATABASE_PATH:-$ROOT/backend/data/demo-counteros.sqlite3}"

echo "CounterOS demo"
echo "database=$DB"
echo "backend=http://127.0.0.1:8000"
echo "frontend=http://127.0.0.1:3000/startup"

COUNTEROS_DATABASE_PATH="$DB" "$ROOT/scripts/dev/run-backend.sh" &
BACKEND_PID=$!
"$ROOT/scripts/dev/run-frontend.sh" &
FRONTEND_PID=$!

cleanup() {
  kill "$BACKEND_PID" "$FRONTEND_PID" 2>/dev/null || true
}
trap cleanup INT TERM EXIT

wait
