import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import connect, initialize_database
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    original_path = settings.database_path
    settings.database_path = str(tmp_path / "counteros-phase5-test.sqlite3")
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


def setup_draft(client: TestClient, token: str, with_item: bool = True) -> dict:
    client.post("/api/v1/sessions/open", headers=auth(token), json={"counter_name": "OP Counter 1", "opening_cash_amount": 1000})
    patient = client.post("/api/v1/patients", headers=auth(token), json={"full_name": "Ravi Kumar"}).json()["data"]["patient"]
    draft = client.post(
        "/api/v1/bills/drafts",
        headers=auth(token),
        json={"patient_id": patient["id"], "bill_type": "op", "department_id": "1", "doctor_id": "1"},
    ).json()["data"]["draft"]
    if with_item:
        client.post(f"/api/v1/bills/drafts/{draft['id']}/items", headers=auth(token), json={"service_id": "1", "quantity": 1})
    return draft


def idem(key: str = "IDEM-1") -> dict[str, str]:
    return {"Idempotency-Key": key}


def assert_error(body: dict, code: str) -> None:
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["request_id"].startswith("REQ-")


def test_phase5_tables_exist() -> None:
    with connect() as conn:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()}

    assert {"bills", "bill_items", "payments", "receipts", "sync_events", "idempotency_keys"}.issubset(tables)


def test_finalize_requires_auth_active_session_and_idempotency_key(client: TestClient) -> None:
    token = login(client)
    draft = setup_draft(client, token)

    no_auth = client.post(f"/api/v1/bills/drafts/{draft['id']}/finalize", json={"payment_method": "cash", "received_amount": 500})
    assert no_auth.status_code == 401
    assert_error(no_auth.json(), "AUTH_SESSION_REQUIRED")

    no_key = client.post(f"/api/v1/bills/drafts/{draft['id']}/finalize", headers=auth(token), json={"payment_method": "cash", "received_amount": 500})
    assert no_key.status_code == 400
    assert_error(no_key.json(), "IDEMPOTENCY_KEY_REQUIRED")

    with connect() as conn:
        conn.execute("UPDATE cashier_sessions SET status = 'closed'")
    no_session = client.post(
        f"/api/v1/bills/drafts/{draft['id']}/finalize",
        headers={**auth(token), **idem("NOSESSION")},
        json={"payment_method": "cash", "received_amount": 500},
    )
    assert no_session.status_code == 409
    assert_error(no_session.json(), "SESSION_NOT_OPEN")


def test_finalize_blocks_empty_unsupported_and_insufficient(client: TestClient) -> None:
    token = login(client)
    empty = setup_draft(client, token, with_item=False)
    blocked = client.post(f"/api/v1/bills/drafts/{empty['id']}/finalize", headers={**auth(token), **idem("EMPTY")}, json={"payment_method": "cash", "received_amount": 500})
    assert blocked.status_code == 422
    assert_error(blocked.json(), "DRAFT_HAS_NO_ITEMS")

    draft = setup_draft(client, token)
    unsupported = client.post(f"/api/v1/bills/drafts/{draft['id']}/finalize", headers={**auth(token), **idem("CARD")}, json={"payment_method": "card", "received_amount": 500})
    assert unsupported.status_code == 422
    assert_error(unsupported.json(), "PAYMENT_METHOD_NOT_SUPPORTED")

    insufficient = client.post(f"/api/v1/bills/drafts/{draft['id']}/finalize", headers={**auth(token), **idem("LOWCASH")}, json={"payment_method": "cash", "received_amount": 499})
    assert insufficient.status_code == 422
    assert_error(insufficient.json(), "PAYMENT_AMOUNT_INSUFFICIENT")


def test_finalize_creates_bill_payment_receipt_sync_and_marks_draft(client: TestClient) -> None:
    token = login(client)
    draft = setup_draft(client, token)
    response = client.post(
        f"/api/v1/bills/drafts/{draft['id']}/finalize",
        headers={**auth(token), **idem()},
        json={"payment_method": "cash", "received_amount": 1000, "notes": "Cash received"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["bill"]["total_amount"] == 500
    assert body["data"]["payment"]["change_amount"] == 500
    assert body["data"]["receipt"]["status"] == "generated"
    assert body["data"]["sync_event"]["event_type"] == "BILL_FINALIZED"

    with connect() as conn:
        counts = {
            name: conn.execute(f"SELECT COUNT(*) AS c FROM {name}").fetchone()["c"]
            for name in ["bills", "bill_items", "payments", "receipts", "sync_events"]
        }
        draft_status = conn.execute("SELECT status FROM bill_drafts WHERE id = ?", (draft["id"],)).fetchone()["status"]
        bill_item = conn.execute("SELECT service_name_at_time, unit_price_paise, price_version FROM bill_items").fetchone()

    assert counts == {"bills": 1, "bill_items": 1, "payments": 1, "receipts": 1, "sync_events": 1}
    assert draft_status == "finalized"
    assert dict(bill_item) == {"service_name_at_time": "OP Consultation", "unit_price_paise": 50000, "price_version": "PRICE-DEV-001"}


def test_finalize_idempotency_and_duplicate_block(client: TestClient) -> None:
    token = login(client)
    draft = setup_draft(client, token)
    first = client.post(f"/api/v1/bills/drafts/{draft['id']}/finalize", headers={**auth(token), **idem("SAME")}, json={"payment_method": "cash", "received_amount": 500})
    retry = client.post(f"/api/v1/bills/drafts/{draft['id']}/finalize", headers={**auth(token), **idem("SAME")}, json={"payment_method": "cash", "received_amount": 500})
    other_key = client.post(f"/api/v1/bills/drafts/{draft['id']}/finalize", headers={**auth(token), **idem("OTHER")}, json={"payment_method": "cash", "received_amount": 500})

    assert first.status_code == 200
    assert retry.status_code == 200
    assert retry.json()["data"]["bill"]["id"] == first.json()["data"]["bill"]["id"]
    assert other_key.status_code == 409
    assert_error(other_key.json(), "DUPLICATE_FINALIZATION_BLOCKED")
    with connect() as conn:
        assert conn.execute("SELECT COUNT(*) AS c FROM bills").fetchone()["c"] == 1


def test_bills_receipts_sync_endpoints_and_audits(client: TestClient) -> None:
    token = login(client)
    draft = setup_draft(client, token)
    finalized = client.post(f"/api/v1/bills/drafts/{draft['id']}/finalize", headers={**auth(token), **idem("READS")}, json={"payment_method": "cash", "received_amount": 500}).json()["data"]
    bill_id = finalized["bill"]["id"]
    receipt_id = finalized["receipt"]["id"]

    listing = client.get("/api/v1/bills", headers=auth(token))
    detail = client.get(f"/api/v1/bills/{bill_id}", headers=auth(token))
    by_bill = client.get(f"/api/v1/receipts/by-bill/{bill_id}", headers=auth(token))
    receipt = client.get(f"/api/v1/receipts/{receipt_id}", headers=auth(token))
    sync = client.get("/api/v1/sync/events", headers={**auth(token), "X-Request-ID": "REQ-FINAL"})

    assert listing.json()["data"]["items"][0]["bill_number"].startswith("HYD01-DEV001-BILL-")
    assert detail.json()["data"]["bill"]["items"][0]["service_name_at_time"] == "OP Consultation"
    assert by_bill.json()["data"]["receipt"]["receipt_payload"]["patient_name"] == "Ravi Kumar"
    assert receipt.json()["data"]["receipt"]["receipt_payload"]["payment_method"] == "cash"
    assert sync.json()["data"]["items"][0]["event_type"] == "BILL_FINALIZED"
    assert sync.json()["request_id"] == "REQ-FINAL"

    with connect() as conn:
        actions = {row["action"] for row in conn.execute("SELECT action FROM audit_logs").fetchall()}

    assert {"bill.finalize", "payment.cash.create", "receipt.generate", "sync_event.create"}.issubset(actions)
