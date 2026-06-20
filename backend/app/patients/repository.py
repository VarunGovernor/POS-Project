from __future__ import annotations

from typing import Any

from app.auth.repository import audit
from app.core.errors import AppError
from app.database.connection import connect, utc_now


def patient_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "patient_number": row["patient_number"],
        "full_name": row["full_name"],
        "phone": row["phone"],
        "gender": row["gender"],
        "age_years": row["age_years"],
        "sync_status": row["sync_status"],
    }


def patient_detail(row: dict[str, Any]) -> dict[str, Any]:
    return {
        **patient_summary(row),
        "organization_id": str(row["organization_id"]),
        "branch_id": str(row["branch_id"]) if row["branch_id"] is not None else None,
        "address_line1": row["address_line1"],
        "status": row["status"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def search_patients(
    q: str | None,
    phone: str | None,
    patient_number: str | None,
    page: int,
    page_size: int,
) -> dict[str, Any]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    clauses = ["organization_id = 1"]
    params: list[Any] = []
    if q:
        clauses.append("LOWER(full_name) LIKE ?")
        params.append(f"%{q.lower()}%")
    if phone:
        clauses.append("phone LIKE ?")
        params.append(f"%{phone}%")
    if patient_number:
        clauses.append("patient_number = ?")
        params.append(patient_number)
    where = " AND ".join(clauses)
    offset = (page - 1) * page_size
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS total FROM patients WHERE {where}", params).fetchone()["total"]
        rows = conn.execute(
            f"""
            SELECT * FROM patients
            WHERE {where}
            ORDER BY updated_at DESC, id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
    return {
        "items": [patient_summary(dict(row)) for row in rows],
        "page": page,
        "page_size": page_size,
        "total": total,
        "has_next": offset + len(rows) < total,
    }


def create_patient(data: Any, user_id: int, request_id: str | None) -> dict[str, Any]:
    full_name = data.full_name.strip()
    if not full_name:
        raise AppError("PATIENT_FULL_NAME_REQUIRED", "Patient full_name is required.", 422)
    now = utc_now()
    with connect() as conn:
        next_id = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM patients").fetchone()["next_id"]
        patient_number = f"P-{next_id:04d}"
        conn.execute(
            """
            INSERT INTO patients (
                organization_id, branch_id, patient_number, full_name, phone, gender,
                age_years, address_line1, status, sync_status, created_at, updated_at
            )
            VALUES (1, 1, ?, ?, ?, ?, ?, ?, 'active', 'pending', ?, ?)
            """,
            (
                patient_number,
                full_name,
                data.phone,
                data.gender,
                data.age_years,
                data.address_line1,
                now,
                now,
            ),
        )
        row = dict(conn.execute("SELECT * FROM patients WHERE patient_number = ?", (patient_number,)).fetchone())
        audit(conn, "patient.create", user_id=user_id, entity_type="patient", entity_id=str(row["id"]), request_id=request_id)
    return {"patient": patient_summary(row)}


def get_patient(patient_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute("SELECT * FROM patients WHERE id = ? AND organization_id = 1", (patient_id,)).fetchone()
    if not row:
        raise AppError("PATIENT_NOT_FOUND", "Patient not found.", 404)
    return {"patient": patient_detail(dict(row))}
