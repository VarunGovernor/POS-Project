#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
DB="${COUNTEROS_DATABASE_PATH:-$ROOT/backend/data/counteros.sqlite3}"
BACKUP="${1:-}"
YES="${2:-}"

[ -n "$BACKUP" ] || { echo "usage: scripts/backup/restore-local-db.sh BACKUP_FILE [--yes]" >&2; exit 1; }
[ -f "$BACKUP" ] || { echo "backup not found: $BACKUP" >&2; exit 1; }

if pgrep -f "uvicorn app.main:app" >/dev/null 2>&1; then
  echo "backend appears to be running; stop it before restore" >&2
  exit 1
fi

if [ "$YES" != "--yes" ]; then
  echo "Refusing to restore $BACKUP to $DB without --yes."
  exit 1
fi

mkdir -p "$(dirname "$DB")"
cp "$BACKUP" "$DB"
[ -f "$BACKUP-wal" ] && cp "$BACKUP-wal" "$DB-wal" || rm -f "$DB-wal"
[ -f "$BACKUP-shm" ] && cp "$BACKUP-shm" "$DB-shm" || rm -f "$DB-shm"
echo "restored=$DB"
