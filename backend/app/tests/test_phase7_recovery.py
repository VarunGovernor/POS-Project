import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import connect, initialize_database, utc_now
from app.main import app
from app.recovery.repository import scan_recovery


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    original_path = settings.database_path
    settings.database_path = str(tmp_path / "counteros-phase7-test.sqlite3")
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


def assert_error(body: dict, code: str) -> None:
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["request_id"].startswith("REQ-")


def seed_recovery_sources() -> None:
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO cashier_sessions (
                id, session_number, organization_id, branch_id, device_id, cashier_user_id,
                counter_name, status, opening_cash_amount, opened_at, created_at, updated_at
            )
            VALUES (10, 'CS-REC', 1, 1, 1, 1, 'OP Counter 1', 'open', 1000, ?, ?, ?)
            """,
            (now, now, now),
        )
        conn.execute(
            """
            INSERT INTO bill_drafts (
                id, draft_number, organization_id, branch_id, device_id, cashier_session_id,
                cashier_user_id, patient_id, bill_type, status, subtotal_amount, discount_amount,
                tax_amount, total_amount, last_autosaved_at, created_at, updated_at
            )
            VALUES (10, 'DRAFT-REC', 1, 1, 1, 10, 1, NULL, 'op', 'draft', 0, 0, 0, 0, ?, ?, ?)
            """,
            (now, now, now),
        )
        conn.execute(
            """
            INSERT INTO patients (
                id, organization_id, branch_id, patient_number, full_name, status, sync_status, created_at, updated_at
            )
            VALUES (10, 1, 1, 'P-REC', 'Recovery Patient', 'active', 'pending', ?, ?)
            """,
            (now, now),
        )
        conn.execute(
            """
            INSERT INTO bills (
                id, bill_number, draft_id, organization_id, branch_id, device_id, cashier_session_id,
                cashier_user_id, patient_id, bill_type, status, currency, subtotal_amount_paise,
                discount_amount_paise, tax_amount_paise, total_amount_paise, finalized_at,
                idempotency_key, sync_status, created_at, updated_at
            )
            VALUES (10, 'BILL-REC', 10, 1, 1, 1, 10, 1, 10, 'op', 'finalized', 'INR', 100, 0, 0, 100, ?, 'REC', 'pending', ?, ?)
            """,
            (now, now, now),
        )
        for job_id, status in [(10, "queued"), (11, "failed")]:
            conn.execute(
                """
                INSERT INTO printer_jobs (
                    id, job_number, organization_id, branch_id, device_id, printer_device_id,
                    receipt_id, bill_id, job_type, status, attempt_count, max_attempts,
                    payload_json, created_by_user_id, created_at, updated_at
                )
                VALUES (?, ?, 1, 1, 1, 1, NULL, NULL, 'test_print', ?, 0, 3, '{}', 1, ?, ?)
                """,
                (job_id, f"PRINT-REC-{job_id}", status, now, now),
            )


def test_recovery_markers_table_exists() -> None:
    with connect() as conn:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()}
    assert "recovery_markers" in tables


def test_scanner_detects_sources_and_avoids_duplicates() -> None:
    seed_recovery_sources()
    first = scan_recovery()
    second = scan_recovery()
    with connect() as conn:
        marker_types = {row["marker_type"] for row in conn.execute("SELECT marker_type FROM recovery_markers").fetchall()}
        count = conn.execute("SELECT COUNT(*) AS c FROM recovery_markers").fetchone()["c"]

    assert first["warning_count"] == 4
    assert second["open_marker_count"] == first["open_marker_count"]
    assert count == 5
    assert {
        "ACTIVE_SESSION_FOUND",
        "OPEN_DRAFT_FOUND",
        "UNSYNCED_BILL_FOUND",
        "PENDING_PRINT_JOB_FOUND",
        "FAILED_PRINT_JOB_FOUND",
    }.issubset(marker_types)


def test_recovery_status_requires_auth_and_returns_envelope(client: TestClient) -> None:
    no_auth = client.get("/api/v1/recovery/status")
    assert no_auth.status_code == 401
    assert_error(no_auth.json(), "AUTH_SESSION_REQUIRED")

    token = login(client)
    response = client.get("/api/v1/recovery/status", headers={**auth(token), "X-Request-ID": "REQ-REC"})
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["request_id"] == "REQ-REC"


def test_work_items_scan_resolve_and_audit(client: TestClient) -> None:
    seed_recovery_sources()
    cashier = login(client)
    admin = login(client, "admin", "admin123")

    scan = client.post("/api/v1/recovery/scan", headers=auth(cashier))
    assert scan.status_code == 200
    items = client.get("/api/v1/recovery/work-items", headers=auth(cashier)).json()["data"]["items"]
    assert items

    denied = client.post("/api/v1/recovery/resolve", headers=auth(cashier), json={"marker_id": items[0]["id"], "resolution_action": "acknowledged"})
    assert denied.status_code == 403
    assert_error(denied.json(), "AUTH_PERMISSION_DENIED")

    resolved = client.post("/api/v1/recovery/resolve", headers=auth(admin), json={"marker_id": items[0]["id"], "resolution_action": "acknowledged", "notes": "Reviewed"})
    assert resolved.status_code == 200
    assert resolved.json()["data"]["marker"]["status"] == "acknowledged"
    with connect() as conn:
        actions = {row["action"] for row in conn.execute("SELECT action FROM audit_logs").fetchall()}
    assert "recovery.resolve" in actions


def test_cashier_cannot_resolve_critical_marker(client: TestClient) -> None:
    token = login(client)
    now = utc_now()
    with connect() as conn:
        conn.execute(
            """
            INSERT INTO recovery_markers (
                marker_code, marker_type, severity, status, title, description,
                detected_at, created_at, updated_at
            )
            VALUES ('REC-CRIT', 'DATABASE_STARTUP_ERROR', 'critical', 'open', 'Critical', 'Critical marker', ?, ?, ?)
            """,
            (now, now, now),
        )
    response = client.post("/api/v1/recovery/resolve", headers=auth(token), json={"marker_id": "1", "resolution_action": "resolved"})
    assert response.status_code == 403
    assert_error(response.json(), "AUTH_PERMISSION_DENIED")


def test_health_and_startup_reflect_recovery_required(client: TestClient) -> None:
    seed_recovery_sources()
    scan_recovery()
    assert client.get("/api/v1/health").json()["data"]["recovery"] == "required"
    assert client.get("/api/v1/startup/status").json()["data"]["recovery_required"] is True
