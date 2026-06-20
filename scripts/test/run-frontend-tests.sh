#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$ROOT/frontend"

command -v npm >/dev/null 2>&1 || { echo "npm missing" >&2; exit 1; }
exec npm test
