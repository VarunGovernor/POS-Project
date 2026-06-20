import sqlite3

import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import (
    MIGRATION_ID,
    REQUIRED_TABLES,
    connect,
    initialize_database,
)
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    original_path = settings.database_path
    settings.database_path = str(tmp_path / "counteros-test.sqlite3")
    initialize_database()
    yield
    settings.database_path = original_path


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def assert_success_envelope(body: dict) -> None:
    assert body["success"] is True
    assert isinstance(body["data"], dict)
    assert body["request_id"].startswith("REQ-")


def test_fresh_database_initializes_with_required_tables() -> None:
    with connect() as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
        ).fetchall()

    assert REQUIRED_TABLES.issubset({row["name"] for row in rows})


def test_sqlite_wal_and_foreign_keys_enabled() -> None:
    with connect() as conn:
        assert conn.execute("PRAGMA journal_mode").fetchone()[0].lower() == "wal"
        assert conn.execute("PRAGMA foreign_keys").fetchone()[0] == 1


def test_migration_and_runtime_state_exist() -> None:
    with connect() as conn:
        migration = conn.execute(
            "SELECT migration_id, status FROM migration_records WHERE migration_id = ?",
            (MIGRATION_ID,),
        ).fetchone()
        runtime = conn.execute("SELECT startup_status FROM app_runtime_state LIMIT 1").fetchone()

    assert dict(migration) == {"migration_id": MIGRATION_ID, "status": "applied"}
    assert runtime["startup_status"] == "ready"


def test_audit_log_foreign_keys_are_enforced() -> None:
    with pytest.raises(sqlite3.IntegrityError):
        with connect() as conn:
            conn.execute(
                """
                INSERT INTO audit_logs (
                    audit_id, organization_id, action, severity, created_at
                )
                VALUES ('AUDIT-BAD-FK', 999, 'test', 'info', '2026-01-01T00:00:00Z')
                """
            )


def test_database_health_returns_standard_success_response(client: TestClient) -> None:
    response = client.get("/api/v1/health/database")
    body = response.json()

    assert response.status_code == 200
    assert_success_envelope(body)
    assert body["data"] == {
        "status": "ok",
        "database_engine": "sqlite",
        "journal_mode": "wal",
        "foreign_keys": True,
        "database_version": MIGRATION_ID,
        "migration_status": "ok",
        "required_tables_present": True,
    }


def test_health_returns_standard_success_response(client: TestClient) -> None:
    response = client.get("/api/v1/health")
    body = response.json()

    assert response.status_code == 200
    assert_success_envelope(body)
    assert body["data"]["status"] == "ok"
    assert body["data"]["database"] == "ok"
    assert body["data"]["migration"] == "ok"


def test_version_returns_standard_success_response(client: TestClient) -> None:
    response = client.get("/api/v1/health/version")
    body = response.json()

    assert response.status_code == 200
    assert_success_envelope(body)
    assert body["data"]["api_version"] == "v1"
    assert body["data"]["app_version"] == "0.1.0"
    assert body["data"]["database_version"] == MIGRATION_ID


def test_startup_status_returns_standard_success_response(client: TestClient) -> None:
    response = client.get("/api/v1/startup/status")
    body = response.json()

    assert response.status_code == 200
    assert_success_envelope(body)
    assert body["data"]["startup_status"] == "ready"
    assert body["data"]["database_status"] == "ok"
    assert body["data"]["migration_status"] == "ok"
    assert body["data"]["recovery_required"] is False


def test_request_id_header_reused_in_response(client: TestClient) -> None:
    response = client.get("/api/v1/health/database", headers={"X-Request-ID": "REQ-TEST-123"})
    body = response.json()

    assert body["request_id"] == "REQ-TEST-123"
    assert response.headers["X-Request-ID"] == "REQ-TEST-123"
