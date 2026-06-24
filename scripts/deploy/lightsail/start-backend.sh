#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../../.." && pwd)"
cd "$ROOT/backend"

if [ -f ".env" ]; then
  set -a
  . ./.env
  set +a
fi

python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt

export COUNTEROS_HOST="${COUNTEROS_HOST:-127.0.0.1}"
export COUNTEROS_BACKEND_PORT="${COUNTEROS_BACKEND_PORT:-8000}"
export COUNTEROS_ENV="${COUNTEROS_ENV:-production}"
export COUNTEROS_DATABASE_PATH="${COUNTEROS_DATABASE_PATH:-$ROOT/backend/data/counteros.sqlite3}"

PYTHONPATH=. python -c "from app.database.connection import initialize_database; initialize_database()"
exec python -m uvicorn app.main:app --host "$COUNTEROS_HOST" --port "$COUNTEROS_BACKEND_PORT"
