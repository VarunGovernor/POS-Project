from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import connect, initialize_database
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    original_path = settings.database_path
    settings.database_path = str(tmp_path / "counteros-phase11-test.sqlite3")
    initialize_database()
    yield
    settings.database_path = original_path


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def post(client: TestClient, path: str, token: str, data: dict, extra_headers: dict | None = None) -> dict:
    response = client.post(path, headers={**auth(token), **(extra_headers or {})}, json=data)
    body = response.json()
    assert body["request_id"].startswith("REQ-")
    assert response.status_code == 200, body
    assert body["success"] is True
    return body["data"]


def get(client: TestClient, path: str, token: str) -> dict:
    response = client.get(path, headers=auth(token))
    body = response.json()
    assert body["request_id"].startswith("REQ-")
    assert response.status_code == 200, body
    assert body["success"] is True
    return body["data"]


def test_full_mvp_flow_from_fresh_database(client: TestClient) -> None:
    login = client.post("/api/v1/auth/login", json={"username": "cashier", "password": "cashier123", "counter_name": "OP Counter 1"})
    token = login.json()["data"]["session_token"]

    session = post(client, "/api/v1/sessions/open", token, {"counter_name": "OP Counter 1", "opening_cash_amount": 1000})["session"]
    patient = post(client, "/api/v1/patients", token, {"full_name": "Acceptance Patient", "phone": "9999999999"})["patient"]
    assert get(client, "/api/v1/catalog/services", token)["items"]
    draft = post(client, "/api/v1/bills/drafts", token, {"patient_id": patient["id"], "bill_type": "op", "department_id": "1", "doctor_id": "1"})["draft"]
    item = post(client, f"/api/v1/bills/drafts/{draft['id']}/items", token, {"service_id": "1", "quantity": 1})["item"]

    updated = client.patch(f"/api/v1/bills/drafts/{draft['id']}/items/{item['id']}", headers=auth(token), json={"quantity": 2, "discount_amount": 0})
    assert updated.status_code == 200
    assert updated.json()["data"]["totals"]["total_amount"] == 1000

    persisted = get(client, f"/api/v1/bills/drafts/{draft['id']}", token)["draft"]
    assert persisted["items"][0]["quantity"] == 2

    finalized = post(
        client,
        f"/api/v1/bills/drafts/{draft['id']}/finalize",
        token,
        {"payment_method": "cash", "received_amount": 1000},
        {"Idempotency-Key": "MVP-FINALIZE"},
    )
    retry = client.post(f"/api/v1/bills/drafts/{draft['id']}/finalize", headers={**auth(token), "Idempotency-Key": "MVP-FINALIZE"}, json={"payment_method": "cash", "received_amount": 1000})
    assert retry.status_code == 200
    assert retry.json()["data"]["bill"]["id"] == finalized["bill"]["id"]

    bill_id = finalized["bill"]["id"]
    receipt_id = finalized["receipt"]["id"]
    assert get(client, f"/api/v1/bills/{bill_id}", token)["bill"]["payment"]["status"] == "paid"
    assert get(client, f"/api/v1/receipts/by-bill/{bill_id}", token)["receipt"]["id"] == receipt_id

    print_job = post(client, f"/api/v1/receipts/{receipt_id}/print", token, {})["job"]
    assert print_job["status"] == "printed"
    duplicate_print = client.post(f"/api/v1/receipts/{receipt_id}/print", headers=auth(token), json={})
    assert duplicate_print.status_code == 409
    assert duplicate_print.json()["error"]["code"] == "RECEIPT_ALREADY_PRINTED"
    assert post(client, f"/api/v1/receipts/{receipt_id}/reprint", token, {"reason": "Acceptance copy"})["job"]["job_type"] == "receipt_reprint"

    sync_before = get(client, "/api/v1/sync/status", token)
    assert sync_before["status"] == "pending"
    sync_event_id = get(client, "/api/v1/sync/events", token)["items"][0]["id"]
    assert post(client, f"/api/v1/sync/events/{sync_event_id}/retry", token, {})["event"]["status"] == "synced"
    assert get(client, "/api/v1/sync/status", token)["status"] == "ok"

    recovery = post(client, "/api/v1/recovery/scan", token, {})
    assert recovery["open_marker_count"] >= 1

    report = get(client, "/api/v1/reports/today-collection", token)
    assert report["bill_count"] == 1
    assert report["cash_collected"] == 1000

    readonly = client.patch("/api/v1/settings", headers=auth(token), json={"setting_key": "environment", "setting_value": "production", "setting_scope": "device"})
    assert readonly.status_code == 403
    admin_token = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123", "counter_name": "OP Counter 1"}).json()["data"]["session_token"]
    readonly_admin = client.patch("/api/v1/settings", headers=auth(admin_token), json={"setting_key": "environment", "setting_value": "production", "setting_scope": "device"})
    assert readonly_admin.status_code == 409
    assert client.patch("/api/v1/settings", headers=auth(admin_token), json={"setting_key": "receipt.header", "setting_value": "MVP Hospital", "setting_scope": "device"}).status_code == 200

    bundle = post(client, "/api/v1/support/bundle", admin_token, {})["bundle"]
    bundle_json = Path(bundle["file_path"]).read_text()
    assert "password" not in bundle_json.lower()
    assert get(client, "/api/v1/audit/logs", admin_token)["items"]

    closed = post(client, "/api/v1/sessions/close", token, {"session_id": session["id"], "closing_cash_amount": 2000})["session"]
    assert closed["status"] == "closed"
    assert closed["expected_cash_amount"] == 2000
    assert closed["cash_difference_amount"] == 0

    with connect() as conn:
        counts = {table: conn.execute(f"SELECT COUNT(*) AS c FROM {table}").fetchone()["c"] for table in ["bills", "bill_items", "payments", "receipts", "sync_events", "sync_attempts", "printer_jobs", "audit_logs"]}
    assert counts["bills"] == 1
    assert counts["bill_items"] == 1
    assert counts["payments"] == 1
    assert counts["receipts"] == 1
    assert counts["sync_events"] == 1
    assert counts["sync_attempts"] == 1
    assert counts["printer_jobs"] == 2
    assert counts["audit_logs"] >= 10
