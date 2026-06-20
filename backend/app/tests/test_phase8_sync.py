import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import connect, initialize_database, utc_now
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    original_path = settings.database_path
    settings.database_path = str(tmp_path / "counteros-phase8-test.sqlite3")
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


def seed_event(status: str = "pending") -> int:
    now = utc_now()
    with connect() as conn:
        cur = conn.execute(
            """
            INSERT INTO sync_events (
                event_type, entity_type, entity_id, organization_id, branch_id, device_id,
                payload_json, status, attempt_count, idempotency_key, created_at, updated_at
            )
            VALUES ('BILL_FINALIZED', 'bill', '1', 1, 1, 1, '{"bill_id":"1"}', ?, 0, ?, ?, ?)
            """,
            (status, f"IDEM-{status}-{now}", now, now),
        )
        return int(cur.lastrowid)


def assert_error(body: dict, code: str) -> None:
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["request_id"].startswith("REQ-")


def test_phase8_tables_exist() -> None:
    with connect() as conn:
        tables = {row["name"] for row in conn.execute("SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'").fetchall()}
    assert {"sync_attempts", "sync_conflicts"}.issubset(tables)


def test_sync_status_requires_auth_and_returns_envelope(client: TestClient) -> None:
    no_auth = client.get("/api/v1/sync/status")
    assert no_auth.status_code == 401
    assert_error(no_auth.json(), "AUTH_SESSION_REQUIRED")

    token = login(client)
    response = client.get("/api/v1/sync/status", headers={**auth(token), "X-Request-ID": "REQ-SYNC"})
    assert response.status_code == 200
    assert response.json()["success"] is True
    assert response.json()["request_id"] == "REQ-SYNC"
    assert response.json()["data"]["adapter"] == "development"


def test_sync_events_list_detail_and_conflicts(client: TestClient) -> None:
    event_id = seed_event()
    token = login(client)
    listing = client.get("/api/v1/sync/events", headers=auth(token))
    detail = client.get(f"/api/v1/sync/events/{event_id}", headers=auth(token))
    conflicts = client.get("/api/v1/sync/conflicts", headers=auth(token))

    assert listing.json()["data"]["items"][0]["event_type"] == "BILL_FINALIZED"
    assert detail.json()["data"]["event"]["payload"]["bill_id"] == "1"
    assert conflicts.json()["data"]["items"] == []


def test_retry_all_and_single_create_attempts_and_update_status(client: TestClient) -> None:
    first = seed_event("pending")
    second = seed_event("failed_retryable")
    token = login(client)

    single = client.post(f"/api/v1/sync/events/{first}/retry", headers=auth(token))
    assert single.status_code == 200
    assert single.json()["data"]["event"]["status"] == "synced"

    summary = client.post("/api/v1/sync/retry", headers=auth(token))
    assert summary.status_code == 200
    assert summary.json()["data"] == {"attempted": 1, "synced": 1, "failed": 0, "conflicts": 0}

    with connect() as conn:
        statuses = {row["id"]: row["status"] for row in conn.execute("SELECT id, status FROM sync_events WHERE id IN (?, ?)", (first, second)).fetchall()}
        attempts = conn.execute("SELECT COUNT(*) AS c FROM sync_attempts").fetchone()["c"]
    assert statuses == {first: "synced", second: "synced"}
    assert attempts == 2


def test_non_retryable_events_are_blocked(client: TestClient) -> None:
    synced = seed_event("synced")
    permanent = seed_event("failed_permanent")
    token = login(client)

    for event_id in [synced, permanent]:
        response = client.post(f"/api/v1/sync/events/{event_id}/retry", headers=auth(token))
        assert response.status_code == 409
        assert_error(response.json(), "SYNC_EVENT_NOT_RETRYABLE")


def test_health_startup_and_permission_denied(client: TestClient) -> None:
    seed_event("pending")
    cashier = login(client, "cashier", "cashier123")

    assert client.get("/api/v1/health").json()["data"]["sync"] == "pending"
    assert client.get("/api/v1/startup/status").json()["data"]["sync_status"] == "pending"

    denied = client.post("/api/v1/sync/retry", headers=auth(cashier))
    assert denied.status_code == 403
    assert_error(denied.json(), "AUTH_PERMISSION_DENIED")
