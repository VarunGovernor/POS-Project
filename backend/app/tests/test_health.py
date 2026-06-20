from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def assert_success_envelope(body: dict) -> None:
    assert body["success"] is True
    assert isinstance(body["data"], dict)
    assert body["request_id"].startswith("REQ-")


def test_health_returns_standard_success_response() -> None:
    response = client.get("/api/v1/health")
    body = response.json()

    assert response.status_code == 200
    assert_success_envelope(body)
    assert body["data"]["status"] == "ok"
    assert body["data"]["database"] == "not_configured"


def test_version_returns_standard_success_response() -> None:
    response = client.get("/api/v1/health/version")
    body = response.json()

    assert response.status_code == 200
    assert_success_envelope(body)
    assert body["data"]["api_version"] == "v1"
    assert body["data"]["app_version"] == "0.1.0"


def test_startup_status_returns_standard_success_response() -> None:
    response = client.get("/api/v1/startup/status")
    body = response.json()

    assert response.status_code == 200
    assert_success_envelope(body)
    assert body["data"]["startup_status"] == "ready"
    assert body["data"]["recovery_required"] is False


def test_request_id_header_reused_in_response() -> None:
    response = client.get("/api/v1/health", headers={"X-Request-ID": "REQ-TEST-123"})
    body = response.json()

    assert body["request_id"] == "REQ-TEST-123"
    assert response.headers["X-Request-ID"] == "REQ-TEST-123"
