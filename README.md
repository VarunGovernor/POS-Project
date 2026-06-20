# POS Appliance Platform / CounterOS

Offline-first local POS appliance MVP for a single counter device. It runs a
FastAPI backend, a Next.js frontend, and a local SQLite database with WAL mode.

Current implemented phase: Phase 11 - MVP Hardening and Acceptance Testing.

## Architecture

- Backend: FastAPI under `backend/app`
- Frontend: Next.js under `frontend/app`
- Database: local SQLite file from `COUNTEROS_DATABASE_PATH`
- Runtime templates: `os/systemd`, `os/kiosk`, `os/install`, `os/update`
- Scripts: `scripts/dev`, `scripts/test`, `scripts/build`, `scripts/install`

All API responses use the standard envelope with `success`, `data` or `error`,
and `request_id`.

## Implemented Phases

Phase 0 through Phase 11 are implemented:

- foundation, health, startup
- database/migrations/runtime state/audit
- auth, permissions, cashier sessions
- patients and catalog
- draft billing/autosave
- final bill, cash payment, receipt, sync outbox
- dev printer jobs
- recovery markers
- development sync retry foundation
- reports, settings, support, audit
- OS/kiosk packaging templates
- MVP hardening and acceptance tests

## Development Users

Development seed users only:

- `cashier` / `cashier123`
- `admin` / `admin123`

Do not use these passwords for production.

## Fresh Database Behavior

On backend startup, a fresh SQLite database is created, migrations run, and
development seed data is inserted. Set `COUNTEROS_DATABASE_PATH` to choose the
database file.

```sh
COUNTEROS_DATABASE_PATH=/tmp/counteros.sqlite3 scripts/dev/run-backend.sh
```

## Run Backend

```sh
scripts/dev/run-backend.sh
```

## Run Frontend

```sh
scripts/dev/run-frontend.sh
```

Open:

```text
http://127.0.0.1:3000/startup
```

## Tests And Build

```sh
scripts/test/run-backend-tests.sh
scripts/test/run-frontend-tests.sh
scripts/build/build-frontend.sh
```

## Runtime Validation

```sh
os/install/validate-host.sh
scripts/install/validate-runtime-files.sh
```

Systemd templates are safe templates only. They are not installed by normal
development commands.

## MVP Acceptance Flow

1. Start backend and frontend.
2. Open `/startup`.
3. Login as `cashier`.
4. Open cashier session.
5. Create/select patient.
6. Check catalog/services.
7. Create draft bill.
8. Add service item and edit quantity.
9. Refresh draft detail and confirm persistence.
10. Finalize cash bill with an `Idempotency-Key`.
11. Confirm bill, bill item, payment, receipt, sync event, and audit logs.
12. Retry duplicate finalization and confirm no duplicate bill.
13. Open bill detail and receipt preview.
14. Print receipt with dev printer.
15. Confirm duplicate original print is blocked.
16. Reprint receipt with reason.
17. Retry sync event with development adapter.
18. Run recovery scan.
19. Check reports, settings, support bundle, and audit logs.
20. Close cashier session.

The backend test `test_phase11_mvp_acceptance.py` runs this flow against a
fresh local database.

## Runtime Packaging

Templates and scripts:

- `os/systemd/counteros-api.service`
- `os/systemd/counteros-frontend.service`
- `os/systemd/counteros-kiosk.service`
- `os/kiosk/launch-kiosk.sh`
- `os/install/counteros.env.example`
- `os/install/install-counteros.sh`
- `os/install/validate-host.sh`
- `os/update/update-counteros.sh`

Production-like local launch order:

1. Review `os/install/counteros.env.example`.
2. Start backend with `scripts/dev/run-backend.sh`.
3. Start frontend with `scripts/dev/run-frontend.sh`.
4. Launch kiosk manually with `os/kiosk/launch-kiosk.sh` on Linux with Chromium.

Service checks, after manual Linux install:

```sh
systemctl status counteros-api counteros-frontend counteros-kiosk
journalctl -u counteros-api.service
```

## Known Limitations

- Development printer adapter only
- Development sync adapter only
- No real cloud sync yet
- No real hardware printer adapter yet
- No refunds yet
- No final bill void yet
- No gateway payments yet
- No pharmacy inventory yet
- No lab workflow yet
- No kiosk auto-install yet
- No automatic update execution yet

## Strictly Not Implemented Yet

Refunds, final bill void, gateway payments, real cloud sync, real printer
hardware integration, advanced analytics, pharmacy inventory, lab workflow,
service restart UI, and automatic OS installation/update execution.
