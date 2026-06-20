import pytest
from fastapi.testclient import TestClient

from app.config import settings
from app.database.connection import connect, initialize_database
from app.main import app


@pytest.fixture(autouse=True)
def isolated_database(tmp_path):
    original_path = settings.database_path
    settings.database_path = str(tmp_path / "counteros-phase3-test.sqlite3")
    initialize_database()
    yield
    settings.database_path = original_path


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


def login(client: TestClient) -> str:
    response = client.post(
        "/api/v1/auth/login",
        json={"username": "cashier", "password": "cashier123", "counter_name": "OP Counter 1"},
    )
    assert response.status_code == 200
    return response.json()["data"]["session_token"]


def auth(token: str) -> dict[str, str]:
    return {"Authorization": f"Bearer {token}"}


def assert_success(body: dict) -> None:
    assert body["success"] is True
    assert isinstance(body["data"], dict)
    assert body["request_id"].startswith("REQ-")


def assert_error(body: dict, code: str) -> None:
    assert body["success"] is False
    assert body["error"]["code"] == code
    assert body["request_id"].startswith("REQ-")


def test_phase3_tables_exist() -> None:
    with connect() as conn:
        tables = {
            row["name"]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
        }

    assert {
        "patients",
        "departments",
        "doctors",
        "services",
        "price_lists",
        "service_prices",
        "tax_rules",
        "master_sync_state",
    }.issubset(tables)


def test_patients_requires_auth(client: TestClient) -> None:
    response = client.get("/api/v1/patients")

    assert response.status_code == 401
    assert_error(response.json(), "AUTH_SESSION_REQUIRED")


def test_patients_returns_standard_envelope(client: TestClient) -> None:
    token = login(client)
    response = client.get("/api/v1/patients", headers=auth(token))
    body = response.json()

    assert response.status_code == 200
    assert_success(body)
    assert body["data"]["items"] == []


def test_create_patient_validates_full_name(client: TestClient) -> None:
    token = login(client)
    response = client.post("/api/v1/patients", headers=auth(token), json={"full_name": "   "})

    assert response.status_code == 422
    assert_error(response.json(), "PATIENT_FULL_NAME_REQUIRED")


def test_create_and_get_patient(client: TestClient) -> None:
    token = login(client)
    created = client.post(
        "/api/v1/patients",
        headers=auth(token),
        json={
            "full_name": "Ravi Kumar",
            "phone": "9999999999",
            "gender": "male",
            "age_years": 35,
            "address_line1": "Hyderabad",
        },
    )
    patient = created.json()["data"]["patient"]

    assert created.status_code == 200
    assert patient["patient_number"] == "P-0001"
    assert patient["sync_status"] == "pending"

    detail = client.get(f"/api/v1/patients/{patient['id']}", headers=auth(token))
    assert detail.status_code == 200
    assert detail.json()["data"]["patient"]["full_name"] == "Ravi Kumar"

    search = client.get("/api/v1/patients?q=Ravi", headers=auth(token))
    assert search.json()["data"]["total"] == 1


def test_catalog_services_seed_and_search(client: TestClient) -> None:
    token = login(client)
    response = client.get("/api/v1/catalog/services", headers=auth(token))
    body = response.json()

    assert response.status_code == 200
    assert_success(body)
    assert body["data"]["total"] == 3
    first = body["data"]["items"][0]
    assert "catalog_version" in first
    assert "price_version" in first
    assert first["currency"] == "INR"

    search = client.get("/api/v1/catalog/services?q=CBC", headers=auth(token))
    assert search.status_code == 200
    assert search.json()["data"]["items"][0]["service_code"] == "CBC"


def test_catalog_departments_doctors_and_master_sync_state(client: TestClient) -> None:
    token = login(client)

    departments = client.get("/api/v1/catalog/departments", headers=auth(token))
    doctors = client.get("/api/v1/catalog/doctors", headers=auth(token))
    sync_state = client.get("/api/v1/catalog/master-sync-state", headers=auth(token))

    assert departments.status_code == 200
    assert len(departments.json()["data"]["items"]) == 3
    assert doctors.status_code == 200
    assert doctors.json()["data"]["items"][0]["full_name"] == "Dr. Dev General"
    assert sync_state.status_code == 200
    assert len(sync_state.json()["data"]["items"]) >= 5


def test_permission_denied_when_patient_permission_missing(client: TestClient) -> None:
    with connect() as conn:
        conn.execute(
            """
            DELETE FROM role_permissions
            WHERE role_id = 1
              AND permission_id = (SELECT id FROM permissions WHERE permission_code = 'patient.view')
            """
        )
    token = login(client)
    response = client.get("/api/v1/patients", headers=auth(token))

    assert response.status_code == 403
    assert_error(response.json(), "AUTH_PERMISSION_DENIED")


def test_audit_log_created_for_patient_creation(client: TestClient) -> None:
    token = login(client)
    client.post("/api/v1/patients", headers=auth(token), json={"full_name": "Ravi Kumar"})

    with connect() as conn:
        actions = {row["action"] for row in conn.execute("SELECT action FROM audit_logs").fetchall()}

    assert "patient.create" in actions


def test_request_id_appears_in_catalog_response(client: TestClient) -> None:
    token = login(client)
    response = client.get(
        "/api/v1/catalog/departments",
        headers={**auth(token), "X-Request-ID": "REQ-PHASE3"},
    )

    assert response.json()["request_id"] == "REQ-PHASE3"
