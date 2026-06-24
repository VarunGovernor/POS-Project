import pytest
import json
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


def open_session(client: TestClient, token: str) -> None:
    response = client.post("/api/v1/sessions/open", headers=auth(token), json={"counter_name": "OP Counter 1", "opening_cash_amount": 1000})
    assert response.status_code == 200


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


def test_send_to_billing_context_includes_op_ip_and_emergency_fields(client: TestClient) -> None:
    token = login(client)
    op = client.get("/api/v1/registrations?registration_type=op", headers=auth(token)).json()["data"]["items"][0]
    ip = client.get("/api/v1/registrations?registration_type=ip", headers=auth(token)).json()["data"]["items"][0]
    emergency = client.get("/api/v1/registrations?registration_type=emergency", headers=auth(token)).json()["data"]["items"][0]

    op_context = client.post(f"/api/v1/registrations/{op['id']}/send-to-billing", headers=auth(token)).json()["data"]["billing_context"]
    ip_context = client.post(f"/api/v1/registrations/{ip['id']}/send-to-billing", headers=auth(token)).json()["data"]["billing_context"]
    emergency_context = client.post(f"/api/v1/registrations/{emergency['id']}/send-to-billing", headers=auth(token)).json()["data"]["billing_context"]

    assert op_context["token_number"]
    assert ip_context["admission_number"]
    assert ip_context["ward"]
    assert ip_context["room_or_bed"]
    assert emergency_context["priority"]


def test_receipt_payload_includes_registration_context(client: TestClient) -> None:
    token = login(client)
    open_session(client, token)
    registration = client.get("/api/v1/registrations?registration_type=emergency", headers=auth(token)).json()["data"]["items"][0]
    context = client.post(f"/api/v1/registrations/{registration['id']}/send-to-billing", headers=auth(token)).json()["data"]["billing_context"]
    patient = client.post("/api/v1/patients", headers=auth(token), json={"full_name": context["patient_name"], "phone": context["mobile_number"]}).json()["data"]["patient"]
    draft = client.post(
        "/api/v1/bills/drafts",
        headers=auth(token),
        json={
            "patient_id": patient["id"],
            "bill_type": "op",
            "department_id": context["department_id"],
            "doctor_id": context["doctor_id"],
            "notes": f"REGCTX:{json.dumps(context)}\n{context['notes']}",
        },
    ).json()["data"]["draft"]
    client.post(f"/api/v1/bills/drafts/{draft['id']}/items", headers=auth(token), json={"service_id": "1"})
    finalized = client.post(f"/api/v1/bills/drafts/{draft['id']}/finalize", headers={**auth(token), "Idempotency-Key": "REG-RECEIPT"}, json={"payment_method": "cash", "received_amount": 500}).json()["data"]
    receipt = client.get(f"/api/v1/receipts/{finalized['receipt']['id']}", headers=auth(token)).json()["data"]["receipt"]

    assert receipt["receipt_payload"]["registration"]["registration_number"] == context["registration_number"]
    assert receipt["receipt_payload"]["registration"]["priority"] == context["priority"]


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
