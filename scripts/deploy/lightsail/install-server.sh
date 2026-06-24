#!/usr/bin/env sh
set -eu

APP_DIR="${COUNTEROS_APP_DIR:-/opt/counteros}"

sudo apt-get update
sudo apt-get install -y git curl ca-certificates nginx python3 python3-venv python3-pip

if ! command -v node >/dev/null 2>&1; then
  curl -fsSL https://deb.nodesource.com/setup_lts.x | sudo -E bash -
  sudo apt-get install -y nodejs
fi

sudo npm install -g pm2
sudo mkdir -p "$APP_DIR" /var/log/counteros
sudo chown -R "$USER":"$USER" "$APP_DIR" /var/log/counteros

cat <<EOF
Server bootstrap complete.

Next steps:
1. Clone or copy the repo into $APP_DIR/POS-Project
2. Create backend/.env and frontend/.env if needed; do not commit secrets.
3. From the repo root:
   pm2 start scripts/deploy/lightsail/ecosystem.config.cjs
   pm2 save
   pm2 startup
4. Install scripts/deploy/lightsail/nginx-pos.conf into /etc/nginx/sites-available/pos
EOF
