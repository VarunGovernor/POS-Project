#!/usr/bin/env sh
set -eu

ROOT="$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)"
cd "$ROOT"

required="
os/systemd/counteros-api.service
os/systemd/counteros-frontend.service
os/systemd/counteros-kiosk.service
os/kiosk/launch-kiosk.sh
os/install/install-counteros.sh
os/install/validate-host.sh
os/install/counteros.env.example
os/update/update-counteros.sh
.env.example
backend/.env.example
frontend/.env.example
scripts/dev/start-demo.sh
scripts/dev/reset-demo-db.sh
scripts/dev/seed-demo-data.sh
scripts/dev/run-backend.sh
scripts/dev/run-frontend.sh
scripts/test/run-backend-tests.sh
scripts/test/run-frontend-tests.sh
scripts/test/run-full-validation.sh
scripts/build/build-frontend.sh
scripts/backup/backup-local-db.sh
scripts/backup/restore-local-db.sh
docs/demo/DEMO_WALKTHROUGH.md
docs/demo/DEMO_CHECKLIST.md
docs/deployment/DEPLOYMENT_READINESS_CHECKLIST.md
docs/deployment/LOCAL_LINUX_DEPLOYMENT_NOTES.md
docs/handover/DEVELOPER_HANDOVER.md
docs/handover/CLIENT_DEMO_GUIDE.md
"

for file in $required; do
  [ -f "$file" ] || { echo "missing: $file" >&2; exit 1; }
done

user_path_pattern="/"Users/
if grep -R "$user_path_pattern" os/systemd; then
  echo "developer-specific path found in systemd template" >&2
  exit 1
fi

restart_label="Restart ""Service"
success_label="service restart ""success"
sd_word="systemd"
browser_mode_word="kiosk"
if grep -R "$restart_label\\|$success_label\\|$sd_word.*active\\|$browser_mode_word.*running" frontend/app backend/app; then
  echo "forbidden runtime UI/status text found" >&2
  exit 1
fi

echo "runtime-files=ok"
