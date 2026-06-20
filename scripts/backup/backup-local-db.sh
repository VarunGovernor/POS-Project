#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
DB="${COUNTEROS_DATABASE_PATH:-$ROOT/backend/data/counteros.sqlite3}"
BACKUP_DIR="${COUNTEROS_BACKUP_DIR:-$ROOT/backend/data/backups}"
STAMP="$(date +%Y%m%d-%H%M%S)"

[ -f "$DB" ] || { echo "database not found: $DB" >&2; exit 1; }
mkdir -p "$BACKUP_DIR"

BASE="$BACKUP_DIR/counteros-$STAMP.sqlite3"
cp "$DB" "$BASE"
[ -f "$DB-wal" ] && cp "$DB-wal" "$BASE-wal"
[ -f "$DB-shm" ] && cp "$DB-shm" "$BASE-shm"

echo "backup=$BASE"
