import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import connect, initialize_database
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    original_path = settings.database_path
    settings.database_path = str(tmp_path / "counteros-phase13-test.sqlite3")
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


def test_registration_tables_exist() -> None:
    with connect() as conn:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table'").fetchall()}

    assert {"hospital_registrations", "hospital_registration_events"}.issubset(tables)


def test_get_registrations_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/registrations")

    assert response.status_code == 401
    assert_error(response.json(), "AUTH_SESSION_REQUIRED")


def test_get_registrations_returns_seeded_op_and_ip_data(client: TestClient) -> None:
    token = login(client)

    op = client.get("/api/v1/registrations?registration_type=op", headers=auth(token))
    ip = client.get("/api/v1/registrations?registration_type=ip", headers=auth(token))

    assert op.status_code == 200
    assert ip.status_code == 200
    assert op.json()["data"]["total"] >= 5
    assert ip.json()["data"]["total"] >= 4


def test_post_op_and_ip_registration_work(client: TestClient) -> None:
    token = login(client)

    op = client.post("/api/v1/registrations", headers=auth(token), json={"registration_type": "op", "patient_name": "Test OP", "department_id": "1", "doctor_id": "1"})
    ip = client.post("/api/v1/registrations", headers=auth(token), json={"registration_type": "ip", "patient_name": "Test IP", "ward": "General Ward", "room_or_bed": "G10", "deposit_amount": 1000})

    assert op.status_code == 200
    assert op.json()["data"]["registration"]["token_number"].startswith("T-")
    assert ip.status_code == 200
    assert ip.json()["data"]["registration"]["admission_number"].startswith("ADM-")


def test_check_in_and_send_to_billing_update_status_and_audit(client: TestClient) -> None:
    token = login(client)
    created = client.post("/api/v1/registrations", headers=auth(token), json={"registration_type": "op", "patient_name": "Billing Patient"}).json()["data"]["registration"]

    checked = client.post(f"/api/v1/registrations/{created['id']}/check-in", headers=auth(token))
    sent = client.post(f"/api/v1/registrations/{created['id']}/send-to-billing", headers=auth(token))

    assert checked.json()["data"]["registration"]["status"] == "checked_in"
    assert sent.json()["data"]["registration"]["billing_status"] == "sent_to_billing"
    assert sent.json()["data"]["billing_context"]["registration_number"] == created["registration_number"]
    with connect() as conn:
        actions = {row["action"] for row in conn.execute("SELECT action FROM audit_logs").fetchall()}
    assert {"registration.create", "registration.check_in", "registration.send_to_billing"}.issubset(actions)


def test_registration_permissions_enforced(client: TestClient) -> None:
    with connect() as conn:
        conn.execute(
            """
            DELETE FROM role_permissions
            WHERE role_id = 1
              AND permission_id = (SELECT id FROM permissions WHERE permission_code = 'registration.create')
            """
        )
    token = login(client)
    response = client.post("/api/v1/registrations", headers=auth(token), json={"registration_type": "op", "patient_name": "Denied"})

    assert response.status_code == 403
    assert_error(response.json(), "AUTH_PERMISSION_DENIED")
