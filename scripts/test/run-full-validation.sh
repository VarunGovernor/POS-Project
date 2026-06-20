#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$ROOT"

scripts/test/run-backend-tests.sh
scripts/test/run-frontend-tests.sh
scripts/build/build-frontend.sh
scripts/install/validate-runtime-files.sh

echo "host validation:"
os/install/validate-host.sh || true
echo "full-validation=ok"
