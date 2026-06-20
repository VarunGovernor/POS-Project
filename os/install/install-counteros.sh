#!/usr/bin/env sh
set -eu

DRY_RUN=0
[ "${1:-}" = "--dry-run" ] && DRY_RUN=1

echo "CounterOS install foundation"
echo "target=/opt/counteros"
echo "env=/etc/counteros/counteros.env"
echo "data=/var/lib/counteros"
echo "logs=/var/log/counteros"

if [ "$DRY_RUN" = "1" ]; then
  echo "dry-run: no files changed"
  exit 0
fi

echo "No automatic install is performed by this foundation script."
echo "Run validate-host.sh, review os/systemd/*.service, then copy files manually with sudo if approved."
