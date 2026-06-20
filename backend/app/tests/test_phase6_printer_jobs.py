import json

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import connect, initialize_database
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    original_path = settings.database_path
    settings.database_path = str(tmp_path / "counteros-phase6-test.sqlite3")
    initialize_database()
    yield
    settings.database_path = original_path


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient, username: str = "cashier", password: str = "cashier123") -> str:
    response = client.post("/api/v1/auth/login", json={"username": username, "password": password, "counter_name": "OP Counter 1"})
    assert response.status_code == 200
    return response.json()["data"]["session_token"]


def finalized_receipt(client: TestClient, token: str) -> tuple[str, str]:
    client.post("/api/v1/sessions/open", headers=auth(token), json={"counter_name": "OP Counter 1", "opening_cash_amount": 1000})
    patient = client.post("/api/v1/patients", headers=auth(token), json={"full_name": "Ravi Kumar"}).json()["data"]["patient"]
    draft = client.post("/api/v1/bills/drafts", headers=auth(token), json={"patient_id": patient["id"], "bill_type": "op"}).json()["data"]["draft"]
    client.post(f"/api/v1/bills/drafts/{draft['id']}/items", headers=auth(token), json={"service_id": "1"})
    final = client.post(
        f"/api/v1/bills/drafts/{draft['id']}/finalize",
        headers={**auth(token), "Idempotency-Key": "PRINT-IDEM"},
        json={"payment_method": "cash", "received_amount": 500},
    ).json()["data"]
    return final["bill"]["id"], final["receipt"]["id"]


def assert_error(body: dict, code: str) -> None:
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["request_id"].startswith("REQ-")


def test_printer_tables_exist() -> None:
    with connect() as conn:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()}

    assert {"printer_devices", "printer_jobs"}.issubset(tables)


def test_printer_status_requires_auth_and_returns_envelope(client: TestClient) -> None:
    no_auth = client.get("/api/v1/printer/status")
    assert no_auth.status_code == 401
    assert_error(no_auth.json(), "AUTH_SESSION_REQUIRED")

    token = login(client)
    response = client.get("/api/v1/printer/status", headers={**auth(token), "X-Request-ID": "REQ-PRINT"})
    body = response.json()
    assert response.status_code == 200
    assert body["success"] is True
    assert body["request_id"] == "REQ-PRINT"
    assert body["data"]["status"] == "active"
    assert body["data"]["printer"]["printer_type"] == "dev"


def test_printer_test_creates_job_and_jobs_list(client: TestClient) -> None:
    admin = login(client, "admin", "admin123")
    response = client.post("/api/v1/printer/test", headers=auth(admin))
    assert response.status_code == 200
    assert response.json()["data"]["job"]["job_type"] == "test_print"
    assert response.json()["data"]["job"]["status"] == "printed"

    jobs = client.get("/api/v1/printer/jobs", headers=auth(admin))
    assert jobs.status_code == 200
    assert jobs.json()["data"]["items"][0]["job_type"] == "test_print"


def test_receipt_print_duplicate_and_reprint_audit(client: TestClient) -> None:
    token = login(client)
    bill_id, receipt_id = finalized_receipt(client, token)

    original = client.post(f"/api/v1/receipts/{receipt_id}/print", headers=auth(token))
    assert original.status_code == 200
    assert original.json()["data"]["job"]["job_type"] == "receipt_original"
    assert original.json()["data"]["job"]["status"] == "printed"

    duplicate = client.post(f"/api/v1/receipts/{receipt_id}/print", headers=auth(token))
    assert duplicate.status_code == 409
    assert_error(duplicate.json(), "RECEIPT_ALREADY_PRINTED")

    reprint = client.post(f"/api/v1/receipts/{receipt_id}/reprint", headers=auth(token), json={"reason": "Customer requested duplicate copy"})
    assert reprint.status_code == 200
    assert reprint.json()["data"]["job"]["job_type"] == "receipt_reprint"

    jobs = client.get(f"/api/v1/printer/jobs?bill_id={bill_id}", headers=auth(token))
    assert jobs.json()["data"]["total"] == 2
    with connect() as conn:
        audit_rows = [dict(row) for row in conn.execute("SELECT action, metadata_json FROM audit_logs WHERE action LIKE 'receipt.%'").fetchall()]
    assert {"receipt.print", "receipt.reprint"}.issubset({row["action"] for row in audit_rows})
    assert "Customer requested duplicate copy" in json.dumps(audit_rows)


def test_retry_failed_job_and_blocks_non_failed_or_maxed(client: TestClient) -> None:
    token = login(client)
    _, receipt_id = finalized_receipt(client, token)
    job = client.post(f"/api/v1/receipts/{receipt_id}/print", headers=auth(token)).json()["data"]["job"]

    non_failed = client.post(f"/api/v1/printer/jobs/{job['id']}/retry", headers=auth(token))
    assert non_failed.status_code == 409
    assert_error(non_failed.json(), "PRINTER_JOB_NOT_RETRYABLE")

    with connect() as conn:
        conn.execute("UPDATE printer_jobs SET status = 'failed', attempt_count = 1, failure_message = 'paper out' WHERE id = ?", (job["id"],))
    retried = client.post(f"/api/v1/printer/jobs/{job['id']}/retry", headers=auth(token))
    assert retried.status_code == 200
    assert retried.json()["data"]["job"]["status"] == "printed"

    with connect() as conn:
        conn.execute("UPDATE printer_jobs SET status = 'failed', attempt_count = max_attempts WHERE id = ?", (job["id"],))
    maxed = client.post(f"/api/v1/printer/jobs/{job['id']}/retry", headers=auth(token))
    assert maxed.status_code == 409
    assert_error(maxed.json(), "PRINTER_JOB_MAX_ATTEMPTS_REACHED")


def test_printer_status_when_not_configured_and_health_startup(client: TestClient) -> None:
    token = login(client)
    with connect() as conn:
        conn.execute("DELETE FROM printer_devices")

    status = client.get("/api/v1/printer/status", headers=auth(token))
    assert status.json()["data"]["status"] == "not_configured"
    assert client.get("/api/v1/health").json()["data"]["printer"] == "not_configured"
    assert client.get("/api/v1/startup/status").json()["data"]["printer_status"] == "not_configured"

    test = client.post("/api/v1/printer/test", headers=auth(login(client, "admin", "admin123")))
    assert test.status_code == 409
    assert_error(test.json(), "PRINTER_NOT_CONFIGURED")


def test_permission_denied_when_printer_permission_missing(client: TestClient) -> None:
    token = login(client)
    with connect() as conn:
        conn.execute(
            """
            DELETE FROM role_permissions
            WHERE role_id = 1
              AND permission_id = (SELECT id FROM permissions WHERE permission_code = 'printer.view')
            """
        )
    response = client.get("/api/v1/printer/status", headers=auth(token))
    assert response.status_code == 403
    assert_error(response.json(), "AUTH_PERMISSION_DENIED")
