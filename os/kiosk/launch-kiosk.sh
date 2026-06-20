#!/usr/bin/env sh
set -eu

URL="${COUNTEROS_FRONTEND_URL:-http://127.0.0.1:3000/startup}"

if command -v chromium >/dev/null 2>&1; then
  BROWSER=chromium
elif command -v chromium-browser >/dev/null 2>&1; then
  BROWSER=chromium-browser
elif command -v google-chrome >/dev/null 2>&1; then
  BROWSER=google-chrome
else
  echo "CounterOS kiosk needs chromium, chromium-browser, or google-chrome in PATH." >&2
  exit 1
fi

exec "$BROWSER" --kiosk --no-first-run --disable-infobars "$URL"
