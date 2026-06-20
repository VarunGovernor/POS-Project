import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import connect, initialize_database
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    original_path = settings.database_path
    settings.database_path = str(tmp_path / "counteros-phase9-test.sqlite3")
    initialize_database()
    yield
    settings.database_path = original_path


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str = "admin", password: str = "admin123") -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password, "counter_name": "OP Counter 1"})
    assert response.status_code == 200
    return response.json()["data"]["session_token"]


def finalized_bill(client: TestClient, token: str) -> dict:
    client.post("/api/v1/sessions/open", headers=auth(token), json={"counter_name": "OP Counter 1", "opening_cash_amount": 1000})
    patient = client.post("/api/v1/patients", headers=auth(token), json={"full_name": "Report Patient"}).json()["data"]["patient"]
    draft = client.post("/api/v1/bills/drafts", headers=auth(token), json={"patient_id": patient["id"], "bill_type": "op", "department_id": "1", "doctor_id": "1"}).json()["data"]["draft"]
    client.post(f"/api/v1/bills/drafts/{draft['id']}/items", headers=auth(token), json={"service_id": "1", "quantity": 1})
    return client.post(f"/api/v1/bills/drafts/{draft['id']}/finalize", headers={**auth(token), "Idempotency-Key": "PHASE9"}, json={"payment_method": "cash", "received_amount": 500}).json()["data"]


def assert_error(body: dict, code: str) -> None:
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["request_id"].startswith("REQ-")


def test_reports_require_auth_and_return_real_totals(client: TestClient) -> None:
    assert_error(client.get("/api/v1/reports/today-collection").json(), "AUTH_SESSION_REQUIRED")
    token = login(client)
    bill = finalized_bill(client, token)

    today = client.get("/api/v1/reports/today-collection", headers={**auth(token), "X-Request-ID": "REQ-REPORT"})
    session = client.get("/api/v1/reports/cashier-session/1", headers=auth(token))
    department = client.get("/api/v1/reports/department-collection", headers=auth(token))
    pending = client.get("/api/v1/reports/pending-sync", headers=auth(token))

    assert today.status_code == 200
    assert today.json()["request_id"] == "REQ-REPORT"
    assert today.json()["data"]["bill_count"] == 1
    assert today.json()["data"]["net_amount"] == bill["bill"]["total_amount"]
    assert session.json()["data"]["summary"]["cash_collected"] == 500
    assert department.json()["data"]["items"][0]["department_name"] == "General Medicine"
    assert pending.json()["data"]["by_status"][0]["status"] == "pending"


def test_settings_list_update_readonly_and_audit(client: TestClient) -> None:
    admin = login(client)
    cashier = login(client, "cashier", "cashier123")
    listed = client.get("/api/v1/settings", headers=auth(cashier))
    assert listed.status_code == 200
    assert any(item["setting_key"] == "receipt.header" for item in listed.json()["data"]["items"])

    readonly = client.patch("/api/v1/settings", headers=auth(admin), json={"setting_key": "environment", "setting_value": "production", "setting_scope": "device"})
    assert readonly.status_code == 409
    assert_error(readonly.json(), "SETTING_READONLY")

    updated = client.patch("/api/v1/settings", headers=auth(admin), json={"setting_key": "receipt.header", "setting_value": "Phase 9 Hospital", "setting_scope": "device"})
    assert updated.status_code == 200
    assert updated.json()["data"]["setting"]["setting_value"] == "Phase 9 Hospital"
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) AS c FROM audit_logs WHERE action = 'settings.update'").fetchone()["c"] == 1


def test_support_status_bundle_and_audit(client: TestClient) -> None:
    token = login(client)
    finalized_bill(client, token)
    status = client.get("/api/v1/support/status", headers=auth(token))
    bundle = client.post("/api/v1/support/bundle", headers=auth(token))

    assert status.status_code == 200
    assert status.json()["data"]["database"] == "ok"
    assert status.json()["data"]["pending_sync_count"] == 1
    path = Path(bundle.json()["data"]["bundle"]["file_path"])
    assert path.exists()
    data = json.loads(path.read_text())
    assert "password" not in json.dumps(data).lower()
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) AS c FROM audit_logs WHERE action = 'support.bundle.create'").fetchone()["c"] == 1


def test_audit_logs_permission_and_entries(client: TestClient) -> None:
    admin = login(client)
    cashier = login(client, "cashier", "cashier123")
    denied = client.get("/api/v1/audit/logs", headers=auth(cashier))
    assert denied.status_code == 403
    assert_error(denied.json(), "AUTH_PERMISSION_DENIED")

    logs = client.get("/api/v1/audit/logs", headers=auth(admin))
    assert logs.status_code == 200
    assert logs.json()["success"] is True
    assert logs.json()["data"]["items"]


def test_permission_denied_for_cashier_settings_update(client: TestClient) -> None:
    cashier = login(client, "cashier", "cashier123")
    response = client.patch("/api/v1/settings", headers=auth(cashier), json={"setting_key": "receipt.header", "setting_value": "Nope", "setting_scope": "device"})
    assert response.status_code == 403
    assert_error(response.json(), "AUTH_PERMISSION_DENIED")
