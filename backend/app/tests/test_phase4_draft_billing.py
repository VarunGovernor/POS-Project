import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import connect, initialize_database
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    original_path = settings.database_path
    settings.database_path = str(tmp_path / "counteros-phase4-test.sqlite3")
    initialize_database()
    yield
    settings.database_path = original_path


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def login(client: TestClient) -> str:
    response = client.post("/api/v1/auth/login", json={"username": "cashier", "password": "cashier123", "counter_name": "OP Counter 1"})
    assert response.status_code == 200
    return response.json()["data"]["session_token"]


def open_session(client: TestClient, token: str) -> str:
    response = client.post("/api/v1/sessions/open", headers=auth(token), json={"counter_name": "OP Counter 1", "opening_cash_amount": 1000})
    assert response.status_code == 200
    return response.json()["data"]["session"]["id"]


def create_patient(client: TestClient, token: str) -> str:
    response = client.post("/api/v1/patients", headers=auth(token), json={"full_name": "Ravi Kumar", "phone": "9999999999"})
    assert response.status_code == 200
    return response.json()["data"]["patient"]["id"]


def create_draft(client: TestClient, token: str, patient_id: str) -> dict:
    response = client.post(
        "/api/v1/bills/drafts",
        headers=auth(token),
        json={"patient_id": patient_id, "bill_type": "op", "department_id": "1", "doctor_id": "1", "notes": "OP visit"},
    )
    assert response.status_code == 200
    return response.json()["data"]["draft"]


def assert_error(body: dict, code: str) -> None:
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["request_id"].startswith("REQ-")


def test_draft_tables_exist() -> None:
    with connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()
        }

    assert {"bill_drafts", "bill_draft_items"}.issubset(tables)


def test_create_draft_requires_auth(client: TestClient) -> None:
    response = client.post("/api/v1/bills/drafts", json={"bill_type": "op"})

    assert response.status_code == 401
    assert_error(response.json(), "AUTH_SESSION_REQUIRED")


def test_create_draft_requires_active_session(client: TestClient) -> None:
    token = login(client)
    patient_id = create_patient(client, token)
    response = client.post("/api/v1/bills/drafts", headers=auth(token), json={"patient_id": patient_id, "bill_type": "op"})

    assert response.status_code == 409
    assert_error(response.json(), "SESSION_NOT_OPEN")


def test_draft_create_list_detail_and_header_update(client: TestClient) -> None:
    token = login(client)
    open_session(client, token)
    patient_id = create_patient(client, token)
    draft = create_draft(client, token, patient_id)

    assert draft["draft_number"].startswith("HYD01-DEV001-DRAFT-")
    assert draft["total_amount"] == 0

    listing = client.get("/api/v1/bills/drafts", headers=auth(token))
    assert listing.status_code == 200
    assert listing.json()["data"]["items"][0]["patient_name"] == "Ravi Kumar"

    detail = client.get(f"/api/v1/bills/drafts/{draft['id']}", headers=auth(token))
    assert detail.status_code == 200
    assert detail.json()["data"]["draft"]["patient"]["full_name"] == "Ravi Kumar"

    updated = client.patch(f"/api/v1/bills/drafts/{draft['id']}", headers=auth(token), json={"patient_id": patient_id, "department_id": "2", "doctor_id": "1", "notes": "Updated"})
    assert updated.status_code == 200
    assert updated.json()["data"]["draft"]["department_id"] == "2"


def test_add_edit_remove_item_recalculates_totals_and_snapshots(client: TestClient) -> None:
    token = login(client)
    open_session(client, token)
    patient_id = create_patient(client, token)
    draft = create_draft(client, token, patient_id)

    add = client.post(f"/api/v1/bills/drafts/{draft['id']}/items", headers=auth(token), json={"service_id": "1", "quantity": 1, "discount_amount": 0, "doctor_id": "1"})
    assert add.status_code == 200
    item = add.json()["data"]["item"]
    assert item["service_name_at_time"] == "OP Consultation"
    assert item["unit_price_at_time"] == 500
    assert add.json()["data"]["totals"]["total_amount"] == 500

    with connect() as conn:
        conn.execute("UPDATE service_prices SET price_amount = 999 WHERE service_id = 1")

    edit = client.patch(f"/api/v1/bills/drafts/{draft['id']}/items/{item['id']}", headers=auth(token), json={"quantity": 2, "discount_amount": 50, "notes": "Discount"})
    assert edit.status_code == 200
    assert edit.json()["data"]["item"]["unit_price_at_time"] == 500
    assert edit.json()["data"]["totals"]["total_amount"] == 950

    remove = client.delete(f"/api/v1/bills/drafts/{draft['id']}/items/{item['id']}", headers=auth(token))
    assert remove.status_code == 200
    assert remove.json()["data"]["removed"] is True
    assert remove.json()["data"]["totals"]["total_amount"] == 0


def test_quantity_and_discount_validation(client: TestClient) -> None:
    token = login(client)
    open_session(client, token)
    draft = create_draft(client, token, create_patient(client, token))

    bad_qty = client.post(f"/api/v1/bills/drafts/{draft['id']}/items", headers=auth(token), json={"service_id": "1", "quantity": 0})
    assert bad_qty.status_code == 422
    assert_error(bad_qty.json(), "BILL_ITEM_QUANTITY_INVALID")

    bad_discount = client.post(f"/api/v1/bills/drafts/{draft['id']}/items", headers=auth(token), json={"service_id": "1", "quantity": 1, "discount_amount": 600})
    assert bad_discount.status_code == 422
    assert_error(bad_discount.json(), "BILL_ITEM_DISCOUNT_INVALID")


def test_void_draft_and_block_edits(client: TestClient) -> None:
    token = login(client)
    open_session(client, token)
    draft = create_draft(client, token, create_patient(client, token))

    voided = client.post(f"/api/v1/bills/drafts/{draft['id']}/void", headers=auth(token), json={"reason": "Patient cancelled visit"})
    assert voided.status_code == 200
    assert voided.json()["data"]["draft"]["status"] == "voided"

    edit = client.patch(f"/api/v1/bills/drafts/{draft['id']}", headers=auth(token), json={"notes": "Nope"})
    assert edit.status_code == 409
    assert_error(edit.json(), "BILL_DRAFT_NOT_EDITABLE")


def test_permission_denied_and_audit_logs(client: TestClient) -> None:
    token = login(client)
    open_session(client, token)
    patient_id = create_patient(client, token)
    with connect() as conn:
        conn.execute(
            """
            DELETE FROM role_permissions
            WHERE role_id = 1
              AND permission_id = (SELECT id FROM permissions WHERE permission_code = 'billing.bill.create')
            """
        )
    denied = client.post("/api/v1/bills/drafts", headers=auth(token), json={"patient_id": patient_id, "bill_type": "op"})
    assert denied.status_code == 403
    assert_error(denied.json(), "AUTH_PERMISSION_DENIED")

    admin = client.post("/api/v1/auth/login", json={"username": "admin", "password": "admin123", "counter_name": "OP Counter 1"}).json()["data"]["session_token"]
    draft = create_draft(client, admin, patient_id)
    item = client.post(f"/api/v1/bills/drafts/{draft['id']}/items", headers=auth(admin), json={"service_id": "1"}).json()["data"]["item"]
    client.post(f"/api/v1/bills/drafts/{draft['id']}/void", headers=auth(admin), json={"reason": "Cancel"})

    with connect() as conn:
        actions = {row["action"] for row in conn.execute("SELECT action FROM audit_logs").fetchall()}

    assert item["id"]
    assert {"bill_draft.create", "bill_draft.item_add", "bill_draft.void"}.issubset(actions)


def test_request_id_appears_in_draft_response(client: TestClient) -> None:
    token = login(client)
    response = client.get("/api/v1/bills/drafts", headers={**auth(token), "X-Request-ID": "REQ-PHASE4"})

    assert response.json()["request_id"] == "REQ-PHASE4"
