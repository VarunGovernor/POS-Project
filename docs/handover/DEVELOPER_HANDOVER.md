# Developer Handover

## Architecture Summary

CounterOS is a local-first POS appliance MVP. FastAPI serves local APIs,
Next.js serves the UI, and SQLite stores durable local data.

## Backend Structure

- `auth`: login, sessions, roles, permissions, audit helper
- `billing`: drafts, final bills, payments, receipts, outbox creation
- `catalog`: departments, doctors, services, prices
- `patients`: local patient foundation
- `printer`: development printer adapter and print jobs
- `recovery`: recovery markers and scanner
- `sync`: development sync adapter and retry foundation
- `operations`: reports, settings, support, audit APIs
- `database`: connection, migrations, seed data

## Frontend Structure

Screens live under `frontend/app`. Shared API calls live in
`frontend/lib/api/client.ts`.

## Database And Migrations

Migrations are Python modules in `backend/app/database/migrations`. Startup
applies pending migrations and seeds development data.

## API Envelope Rules

Success:

```json
{"success": true, "data": {}, "request_id": "REQ-..."}
```

Error:

```json
{"success": false, "error": {"code": "...", "message": "...", "details": {}}, "request_id": "REQ-..."}
```

## Request ID Rules

Every API response includes `request_id`. Caller-provided `X-Request-ID` is
preserved.

## Auth And Permissions

Bearer token login sessions are local. Permissions are seeded for cashier and
admin roles. Protected APIs use permission dependencies.

## Billing Flow

Drafts are durable. Finalization copies draft snapshots into final bill rows,
creates cash payment, receipt, sync event, audit logs, and marks draft
finalized in one transaction path.

## Finalization Rules

Finalization requires an `Idempotency-Key`. Reusing the same key returns the
same result. A different key cannot finalize the same draft twice.

## Receipt And Printer Flow

Receipt generation happens during finalization. Print/reprint creates printer
jobs. The current adapter is development-only.

## Recovery Flow

Recovery scan creates idempotent markers for open sessions, open drafts,
unsynced bills, printer jobs, and stale syncing events. Resolving markers does
not mutate business records.

## Sync Foundation

Sync events are local outbox rows. Manual retry uses the development adapter
and records sync attempts. No cloud upload exists yet.

## Reports, Settings, Support

Reports are live queries over local bills, payments, items, and sync events.
Settings support readonly protection. Support bundles contain safe metadata.

## Runtime Scripts

- `scripts/dev/start-demo.sh`
- `scripts/dev/reset-demo-db.sh`
- `scripts/test/run-full-validation.sh`
- `scripts/backup/backup-local-db.sh`
- `scripts/backup/restore-local-db.sh`

## Testing Commands

```sh
scripts/test/run-backend-tests.sh
scripts/test/run-frontend-tests.sh
scripts/build/build-frontend.sh
scripts/test/run-full-validation.sh
```

## Known Limitations

Development printer adapter only, development sync adapter only, no real cloud
sync, no real hardware printer adapter, no refunds, no final bill void, no
gateway payments, no pharmacy inventory, no lab workflow, no kiosk auto-install.

## Next Recommended Phases

1. Real printer adapter.
2. Real cloud sync endpoint.
3. Production user/role management.
4. Receipt format approval.
5. Linux hardware deployment test.
