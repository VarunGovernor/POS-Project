# POS Appliance Platform / CounterOS

Offline-first POS appliance platform foundation.

Current implemented phase: Phase 10 - OS and Kiosk Packaging Foundation.

Development seed users only:

- `cashier` / `cashier123`
- `admin` / `admin123`

Do not use these passwords for production.

## Backend

```sh
scripts/dev/run-backend.sh
```

## Frontend

```sh
scripts/dev/run-frontend.sh
```

## Tests

```sh
scripts/test/run-backend-tests.sh
scripts/test/run-frontend-tests.sh
scripts/build/build-frontend.sh
scripts/install/validate-runtime-files.sh
```

## Runtime Packaging Foundation

Systemd service templates live under `os/systemd/`. They use `/opt/counteros`
and `/etc/counteros/counteros.env` placeholders and are not installed by normal
development commands.

Validate host/runtime files:

```sh
os/install/validate-host.sh
scripts/install/validate-runtime-files.sh
```

Production-like local launch order:

1. Copy `os/install/counteros.env.example` to the target env file and review it.
2. Start backend with `scripts/dev/run-backend.sh`.
3. Start frontend with `scripts/dev/run-frontend.sh`.
4. Launch kiosk manually with `os/kiosk/launch-kiosk.sh` on a Linux host with Chromium.

Service status, once templates are manually installed on Linux:

```sh
systemctl status counteros-api counteros-frontend counteros-kiosk
journalctl -u counteros-api.service
```
