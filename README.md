# POS Appliance Platform / CounterOS

Offline-first POS appliance platform foundation.

Current implemented phase: Phase 4 - Draft Billing and Autosave.

Development seed users only:

- `cashier` / `cashier123`
- `admin` / `admin123`

Do not use these passwords for production.

## Backend

```powershell
PYTHONPATH=backend python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

## Frontend

```powershell
cd frontend
npm install
npm run dev -- --hostname 127.0.0.1 --port 3000
```

## Tests

```powershell
cd backend
PYTHONPATH=. python -m pytest app/tests

cd ../frontend
npm test
npm run build
```
