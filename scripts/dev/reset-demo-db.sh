#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
DB="${COUNTEROS_DATABASE_PATH:-$ROOT/backend/data/demo-counteros.sqlite3}"

if [ "${1:-}" != "--yes" ]; then
  echo "Demo/local development reset only."
  echo "Refusing to delete $DB without --yes."
  exit 1
fi

rm -f "$DB" "$DB-wal" "$DB-shm"
echo "removed demo database: $DB"
echo "start backend to recreate and seed development data"
