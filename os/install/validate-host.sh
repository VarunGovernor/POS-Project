#!/usr/bin/env sh
set -eu

echo "CounterOS host validation"

case "$(uname -s)" in
  Linux) echo "os=Linux" ;;
  *) echo "unsupported_os=$(uname -s)"; echo "Linux appliance install only. Dev scripts may still run." ;;
esac

for cmd in python3 node npm sqlite3; do
  if command -v "$cmd" >/dev/null 2>&1; then
    echo "$cmd=ok"
  else
    echo "$cmd=missing"
  fi
done

if command -v chromium >/dev/null 2>&1 || command -v chromium-browser >/dev/null 2>&1 || command -v google-chrome >/dev/null 2>&1; then
  echo "chromium=ok"
else
  echo "chromium=missing"
fi
