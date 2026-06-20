import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import connect, initialize_database
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    original_path = settings.database_path
    settings.database_path = str(tmp_path / "counteros-phase2-test.sqlite3")
    initialize_database()
    yield
    settings.database_path = original_path


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient, username: str = "cashier", password: str = "cashier123") -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": username, "password": password, "counter_name": "OP Counter 1"},
    )
    assert response.status_code == 200
    return response.json()["data"]["session_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_error(body: dict, code: str) -> None:
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["request_id"].startswith("REQ-")


def test_phase2_tables_and_seed_users_exist() -> None:
    with connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }
        users = {row["username"] for row in conn.execute("SELECT username FROM users").fetchall()}

    assert {"users", "roles", "permissions", "role_permissions", "user_roles", "login_sessions", "cashier_sessions"}.issubset(tables)
    assert {"cashier", "admin"}.issubset(users)


def test_login_success(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "cashier", "password": "cashier123", "counter_name": "OP Counter 1"},
    )
    body = response.json()

    assert response.status_code == 200
    assert body["success"] is True
    assert body["data"]["offline_login"] is False
    assert body["data"]["user"]["username"] == "cashier"
    assert "session.open" in body["data"]["user"]["permissions"]


def test_login_invalid_password(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "cashier", "password": "bad", "counter_name": "OP Counter 1"},
    )

    assert response.status_code == 401
    assert_error(response.json(), "AUTH_INVALID_CREDENTIALS")


def test_offline_login_allowed(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/offline-login",
        json={"username": "cashier", "password": "cashier123", "counter_name": "OP Counter 1"},
    )

    assert response.status_code == 200
    assert response.json()["data"]["offline_login"] is True


def test_offline_login_blocked_when_user_not_allowed(client: TestClient) -> None:
    response = client.post(
        "/api/v1/auth/offline-login",
        json={"username": "admin", "password": "admin123", "counter_name": "OP Counter 1"},
    )

    assert response.status_code == 403
    assert_error(response.json(), "AUTH_OFFLINE_LOGIN_NOT_ALLOWED")


def test_auth_me_success(client: TestClient) -> None:
    token = login(client)
    response = client.get("/api/v1/auth/me", headers=auth(token))

    assert response.status_code == 200
    assert response.json()["data"]["user"]["username"] == "cashier"
    assert response.json()["data"]["login_session_id"]


def test_auth_me_without_token_returns_401(client: TestClient) -> None:
    response = client.get("/api/v1/auth/me")

    assert response.status_code == 401
    assert_error(response.json(), "AUTH_SESSION_REQUIRED")


def test_logout_success(client: TestClient) -> None:
    token = login(client)
    response = client.post("/api/v1/auth/logout", headers=auth(token))

    assert response.status_code == 200
    assert response.json()["data"]["status"] == "ok"
    assert client.get("/api/v1/auth/me", headers=auth(token)).status_code == 401


def test_device_status_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/device/status")

    assert response.status_code == 401
    assert_error(response.json(), "AUTH_SESSION_REQUIRED")


def test_device_status_success(client: TestClient) -> None:
    token = login(client)
    response = client.get("/api/v1/device/status", headers=auth(token))

    assert response.status_code == 200
    assert response.json()["data"]["activation_status"] == "active"


def test_current_session_returns_null_when_no_open_session(client: TestClient) -> None:
    token = login(client)
    response = client.get("/api/v1/sessions/current", headers=auth(token))

    assert response.status_code == 200
    assert response.json()["data"]["session"] is None


def test_open_duplicate_and_close_session(client: TestClient) -> None:
    token = login(client)
    open_response = client.post(
        "/api/v1/sessions/open",
        headers=auth(token),
        json={"counter_name": "OP Counter 1", "opening_cash_amount": 1000, "notes": "Morning shift"},
    )
    assert open_response.status_code == 200
    session = open_response.json()["data"]["session"]

    duplicate = client.post(
        "/api/v1/sessions/open",
        headers=auth(token),
        json={"counter_name": "OP Counter 1", "opening_cash_amount": 500, "notes": "Second shift"},
    )
    assert duplicate.status_code == 409
    assert_error(duplicate.json(), "CASHIER_SESSION_ALREADY_OPEN")

    close_response = client.post(
        "/api/v1/sessions/close",
        headers=auth(token),
        json={"session_id": session["id"], "closing_cash_amount": 1000, "notes": "Shift closed"},
    )
    closed = close_response.json()["data"]["session"]
    assert close_response.status_code == 200
    assert closed["status"] == "closed"
    assert closed["expected_cash_amount"] == 1000
    assert closed["cash_difference_amount"] == 0


def test_close_missing_session_blocked(client: TestClient) -> None:
    token = login(client)
    response = client.post(
        "/api/v1/sessions/close",
        headers=auth(token),
        json={"session_id": "999", "closing_cash_amount": 1000, "notes": "Missing"},
    )

    assert response.status_code == 404
    assert_error(response.json(), "CASHIER_SESSION_NOT_FOUND")


def test_permission_denied_when_permission_missing(client: TestClient) -> None:
    with connect() as conn:
        conn.execute(
            """
            DELETE FROM role_permissions
            WHERE role_id = 1
              AND permission_id = (SELECT id FROM permissions WHERE permission_code = 'session.open')
            """
        )
    token = login(client)
    response = client.post(
        "/api/v1/sessions/open",
        headers=auth(token),
        json={"counter_name": "OP Counter 1", "opening_cash_amount": 1000, "notes": "Denied"},
    )

    assert response.status_code == 403
    assert_error(response.json(), "AUTH_PERMISSION_DENIED")


def test_audit_log_created_for_login_and_session_actions(client: TestClient) -> None:
    token = login(client)
    session = client.post(
        "/api/v1/sessions/open",
        headers=auth(token),
        json={"counter_name": "OP Counter 1", "opening_cash_amount": 1000, "notes": "Open"},
    ).json()["data"]["session"]
    client.post(
        "/api/v1/sessions/close",
        headers=auth(token),
        json={"session_id": session["id"], "closing_cash_amount": 1000, "notes": "Close"},
    )

    with connect() as conn:
        actions = {row["action"] for row in conn.execute("SELECT action FROM audit_logs").fetchall()}

    assert {"auth.online_login", "session.open", "session.close"}.issubset(actions)
