#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
DB="${COUNTEROS_DATABASE_PATH:-$ROOT/backend/data/demo-counteros.sqlite3}"

echo "Demo seed uses backend startup migrations and development seed data."
echo "database=$DB"
echo "Run: COUNTEROS_DATABASE_PATH=\"$DB\" scripts/dev/run-backend.sh"
