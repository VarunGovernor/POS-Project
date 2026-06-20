#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$ROOT/backend"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ -x "/tmp/counteros-phase1-py311/bin/python" ]; then
  PYTHON_BIN="/tmp/counteros-phase1-py311/bin/python"
fi

PYTHONPATH=. exec "$PYTHON_BIN" -m uvicorn app.main:app --host "${COUNTEROS_HOST:-127.0.0.1}" --port "${COUNTEROS_BACKEND_PORT:-8000}" --reload
