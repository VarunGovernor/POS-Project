#!/usr/bin/env sh
set -eu

DRY_RUN=0
CONFIRM=0
for arg in "$@"; do
  [ "$arg" = "--dry-run" ] && DRY_RUN=1
  [ "$arg" = "--confirm" ] && CONFIRM=1
done

echo "CounterOS update foundation"
echo "Reminder: take a database backup before updating."

if [ "$DRY_RUN" = "1" ]; then
  echo "dry-run: would fetch source, build frontend, run tests, and restart reviewed services"
  exit 0
fi

if [ "$CONFIRM" != "1" ]; then
  echo "Refusing to stop/restart services without --confirm."
  exit 1
fi

echo "Update execution is intentionally not automated yet."
