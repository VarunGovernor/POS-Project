# POS Appliance Platform / CounterOS

Offline-first POS appliance platform foundation.

Current implemented phase: Phase 0 - Project Foundation.

## Backend

```powershell
cd backend
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
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
python -m pytest app/tests

cd ../frontend
npm test
npm run build
```
