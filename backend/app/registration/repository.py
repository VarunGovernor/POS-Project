from __future__ import annotations

from typing import Any

from app.auth.repository import audit, row_dict
from app.core.errors import AppError
from app.database.connection import connect, utc_now

REGISTRATION_TYPES = {"op", "ip", "emergency", "follow_up", "lab", "pharmacy_walkin"}
STATUSES = {"registered", "checked_in", "admitted", "active", "completed", "cancelled"}
BILLING_STATUSES = {"pending", "ready_for_billing", "sent_to_billing", "billed"}


def _as_id(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


def _paise(value: float | int | None) -> int | None:
    return int(round(float(value) * 100)) if value is not None else None


def _amount(value: int | None) -> float | None:
    return value / 100 if value is not None else None


def _row(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "registration_number": row["registration_number"],
        "registration_type": row["registration_type"],
        "patient_id": str(row["patient_id"]) if row["patient_id"] is not None else None,
        "patient_name": row["patient_name"],
        "mobile_number": row["mobile_number"],
        "age_years": row["age_years"],
        "gender": row["gender"],
        "department_id": str(row["department_id"]) if row["department_id"] is not None else None,
        "department_name": row.get("department_name"),
        "doctor_id": str(row["doctor_id"]) if row["doctor_id"] is not None else None,
        "doctor_name": row.get("doctor_name"),
        "visit_type": row["visit_type"],
        "token_number": row["token_number"],
        "admission_number": row["admission_number"],
        "ward": row["ward"],
        "room_or_bed": row["room_or_bed"],
        "attender_name": row["attender_name"],
        "deposit_amount": _amount(row["deposit_amount_paise"]),
        "priority": row["priority"],
        "sample_status": row["sample_status"],
        "prescription_reference": row["prescription_reference"],
        "status": row["status"],
        "billing_status": row["billing_status"],
        "notes": row["notes"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


def _get(conn, registration_id: int) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT hr.*, d.department_name, dr.full_name AS doctor_name
        FROM hospital_registrations hr
        LEFT JOIN departments d ON d.id = hr.department_id
        LEFT JOIN doctors dr ON dr.id = hr.doctor_id
        WHERE hr.id = ? AND hr.organization_id = 1
        """,
        (registration_id,),
    ).fetchone()
    if not row:
        raise AppError("REGISTRATION_NOT_FOUND", "Registration not found.", 404)
    return dict(row)


def _event(conn, registration_id: int, event_type: str, user_id: int | None, notes: str | None = None) -> None:
    conn.execute(
        """
        INSERT INTO hospital_registration_events (registration_id, event_type, notes, created_by_user_id, created_at)
        VALUES (?, ?, ?, ?, ?)
        """,
        (registration_id, event_type, notes, user_id, utc_now()),
    )


def _validate(data: Any) -> str:
    registration_type = data.registration_type
    if registration_type not in REGISTRATION_TYPES:
        raise AppError("REGISTRATION_TYPE_INVALID", "Invalid registration type.", 422)
    if registration_type != "emergency" and not (data.patient_name or "").strip():
        raise AppError("REGISTRATION_PATIENT_REQUIRED", "Patient name is required.", 422)
    return (data.patient_name or "Unknown Patient").strip()


def _number(conn, registration_type: str) -> str:
    prefix = {"op": "OP", "ip": "IP", "emergency": "ER", "follow_up": "FU", "lab": "LAB", "pharmacy_walkin": "PH"}[registration_type]
    next_id = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM hospital_registrations").fetchone()["next_id"]
    return f"{prefix}-{1000 + next_id}"


def list_registrations(registration_type: str | None, status: str | None, billing_status: str | None, q: str | None, page: int, page_size: int) -> dict[str, Any]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    clauses = ["hr.organization_id = 1"]
    params: list[Any] = []
    if registration_type:
        clauses.append("hr.registration_type = ?")
        params.append(registration_type)
    if status:
        clauses.append("hr.status = ?")
        params.append(status)
    if billing_status:
        clauses.append("hr.billing_status = ?")
        params.append(billing_status)
    if q:
        clauses.append("(LOWER(hr.patient_name) LIKE ? OR hr.mobile_number LIKE ? OR hr.registration_number LIKE ?)")
        params.extend([f"%{q.lower()}%", f"%{q}%", f"%{q}%"])
    where = " AND ".join(clauses)
    offset = (page - 1) * page_size
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS total FROM hospital_registrations hr WHERE {where}", params).fetchone()["total"]
        rows = conn.execute(
            f"""
            SELECT hr.*, d.department_name, dr.full_name AS doctor_name
            FROM hospital_registrations hr
            LEFT JOIN departments d ON d.id = hr.department_id
            LEFT JOIN doctors dr ON dr.id = hr.doctor_id
            WHERE {where}
            ORDER BY hr.created_at DESC, hr.id DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
    return {"items": [_row(dict(row)) for row in rows], "page": page, "page_size": page_size, "total": total, "has_next": offset + len(rows) < total}


def get_registration(registration_id: int) -> dict[str, Any]:
    with connect() as conn:
        registration = _row(_get(conn, registration_id))
        events = [dict(row) | {"id": str(row["id"]), "registration_id": str(row["registration_id"])} for row in conn.execute("SELECT * FROM hospital_registration_events WHERE registration_id = ? ORDER BY id", (registration_id,)).fetchall()]
    return {"registration": registration, "events": events}


def create_registration(data: Any, context: dict[str, Any], request_id: str | None) -> dict[str, Any]:
    patient_name = _validate(data)
    now = utc_now()
    device = context["device"]
    with connect() as conn:
        registration_number = _number(conn, data.registration_type)
        token_number = registration_number.replace("OP-", "T-").replace("FU-", "T-") if data.registration_type in {"op", "follow_up"} else None
        admission_number = registration_number.replace("IP-", "ADM-") if data.registration_type == "ip" else None
        conn.execute(
            """
            INSERT INTO hospital_registrations (
                registration_number, organization_id, branch_id, device_id, registration_type,
                patient_name, mobile_number, age_years, gender, department_id, doctor_id,
                visit_type, token_number, admission_number, ward, room_or_bed, attender_name,
                deposit_amount_paise, priority, sample_status, prescription_reference, status,
                billing_status, notes, created_by_user_id, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'registered', 'pending', ?, ?, ?, ?)
            """,
            (
                registration_number, device["organization_id"], device["branch_id"], device["id"], data.registration_type,
                patient_name, data.mobile_number, data.age_years, data.gender, _as_id(data.department_id), _as_id(data.doctor_id),
                data.visit_type, token_number, admission_number, data.ward, data.room_or_bed, data.attender_name,
                _paise(data.deposit_amount), data.priority, data.sample_status, data.prescription_reference, data.notes,
                context["user"]["id"], now, now,
            ),
        )
        row = _get(conn, conn.execute("SELECT last_insert_rowid()").fetchone()[0])
        _event(conn, row["id"], "created", context["user"]["id"], data.notes)
        audit(conn, "registration.create", user_id=context["user"]["id"], entity_type="hospital_registration", entity_id=str(row["id"]), request_id=request_id)
    return {"registration": _row(row)}


def update_registration(registration_id: int, data: Any, context: dict[str, Any], request_id: str | None) -> dict[str, Any]:
    values = data.model_dump(exclude_unset=True)
    if "status" in values and values["status"] not in STATUSES:
        raise AppError("REGISTRATION_STATUS_INVALID", "Invalid registration status.", 422)
    if "billing_status" in values and values["billing_status"] not in BILLING_STATUSES:
        raise AppError("REGISTRATION_BILLING_STATUS_INVALID", "Invalid billing status.", 422)
    if "deposit_amount" in values:
        values["deposit_amount_paise"] = _paise(values.pop("deposit_amount"))
    for key in ["department_id", "doctor_id"]:
        if key in values:
            values[key] = _as_id(values[key])
    if not values:
        return get_registration(registration_id)
    values["updated_at"] = utc_now()
    with connect() as conn:
        _get(conn, registration_id)
        assignments = ", ".join(f"{key} = ?" for key in values)
        conn.execute(f"UPDATE hospital_registrations SET {assignments} WHERE id = ?", [*values.values(), registration_id])
        _event(conn, registration_id, "updated", context["user"]["id"])
        audit(conn, "registration.update", user_id=context["user"]["id"], entity_type="hospital_registration", entity_id=str(registration_id), request_id=request_id)
        row = _get(conn, registration_id)
    return {"registration": _row(row)}


def check_in(registration_id: int, context: dict[str, Any], request_id: str | None) -> dict[str, Any]:
    now = utc_now()
    with connect() as conn:
        current = _get(conn, registration_id)
        status = "admitted" if current["registration_type"] == "ip" else "checked_in"
        billing_status = "ready_for_billing" if current["registration_type"] in {"op", "follow_up", "lab", "pharmacy_walkin"} else current["billing_status"]
        conn.execute("UPDATE hospital_registrations SET status = ?, billing_status = ?, updated_at = ? WHERE id = ?", (status, billing_status, now, registration_id))
        _event(conn, registration_id, "checked_in", context["user"]["id"])
        audit(conn, "registration.check_in", user_id=context["user"]["id"], entity_type="hospital_registration", entity_id=str(registration_id), request_id=request_id)
        row = _get(conn, registration_id)
    return {"registration": _row(row)}


def send_to_billing(registration_id: int, context: dict[str, Any], request_id: str | None) -> dict[str, Any]:
    now = utc_now()
    with connect() as conn:
        current = _get(conn, registration_id)
        conn.execute("UPDATE hospital_registrations SET billing_status = 'sent_to_billing', updated_at = ? WHERE id = ?", (now, registration_id))
        _event(conn, registration_id, "sent_to_billing", context["user"]["id"])
        audit(conn, "registration.send_to_billing", user_id=context["user"]["id"], entity_type="hospital_registration", entity_id=str(registration_id), request_id=request_id)
        row = _get(conn, registration_id)
    registration = _row(row)
    return {
        "registration": registration,
        "billing_context": {
            "registration_id": registration["id"],
            "registration_number": registration["registration_number"],
            "registration_type": registration["registration_type"],
            "patient_name": registration["patient_name"],
            "patient_id": registration["patient_id"],
            "department_id": registration["department_id"],
            "doctor_id": registration["doctor_id"],
            "department_name": registration["department_name"],
            "doctor_name": registration["doctor_name"],
            "notes": f"From {registration['registration_type'].upper()} Registration {registration['registration_number']}",
        },
    }
