#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$ROOT"

PYTHON_BIN="${PYTHON_BIN:-python3}"
if [ -x "/tmp/counteros-phase1-py311/bin/python" ]; then
  PYTHON_BIN="/tmp/counteros-phase1-py311/bin/python"
fi

PYTHONPATH=backend exec "$PYTHON_BIN" -m pytest backend/app/tests -q
