from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.auth.repository import audit, row_dict
from app.core.errors import AppError
from app.database.connection import connect, utc_now


def _as_id(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


def _active_session(conn: sqlite3.Connection, device_id: int) -> dict[str, Any]:
    row = conn.execute(
        """
        SELECT * FROM cashier_sessions
        WHERE device_id = ? AND status = 'open'
        ORDER BY opened_at DESC LIMIT 1
        """,
        (device_id,),
    ).fetchone()
    if not row:
        raise AppError("SESSION_NOT_OPEN", "Open cashier session required.", 409)
    return dict(row)


def _draft_or_error(conn: sqlite3.Connection, draft_id: int, editable: bool = False) -> dict[str, Any]:
    row = conn.execute("SELECT * FROM bill_drafts WHERE id = ?", (draft_id,)).fetchone()
    if not row:
        raise AppError("BILL_DRAFT_NOT_FOUND", "Draft bill not found.", 404)
    draft = dict(row)
    if editable and draft["status"] != "draft":
        raise AppError("BILL_DRAFT_NOT_EDITABLE", "Draft bill is not editable.", 409)
    return draft


def _totals(conn: sqlite3.Connection, draft_id: int) -> dict[str, float]:
    row = conn.execute(
        """
        SELECT COALESCE(SUM(gross_amount), 0) AS subtotal,
               COALESCE(SUM(discount_amount), 0) AS discount,
               COALESCE(SUM(tax_amount), 0) AS tax,
               COALESCE(SUM(final_line_total), 0) AS total
        FROM bill_draft_items WHERE draft_id = ?
        """,
        (draft_id,),
    ).fetchone()
    now = utc_now()
    conn.execute(
        """
        UPDATE bill_drafts
        SET subtotal_amount = ?, discount_amount = ?, tax_amount = ?, total_amount = ?,
            last_autosaved_at = ?, updated_at = ?
        WHERE id = ?
        """,
        (row["subtotal"], row["discount"], row["tax"], row["total"], now, now, draft_id),
    )
    return {
        "subtotal_amount": row["subtotal"],
        "discount_amount": row["discount"],
        "tax_amount": row["tax"],
        "total_amount": row["total"],
    }


def _draft_summary(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "draft_number": row["draft_number"],
        "patient_name": row.get("patient_name"),
        "bill_type": row["bill_type"],
        "status": row["status"],
        "total_amount": row["total_amount"],
        "updated_at": row["updated_at"],
    }


def _draft_header(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "draft_number": row["draft_number"],
        "status": row["status"],
        "patient_id": str(row["patient_id"]) if row["patient_id"] is not None else None,
        "bill_type": row["bill_type"],
        "department_id": str(row["department_id"]) if row["department_id"] is not None else None,
        "doctor_id": str(row["doctor_id"]) if row["doctor_id"] is not None else None,
        "subtotal_amount": row["subtotal_amount"],
        "discount_amount": row["discount_amount"],
        "tax_amount": row["tax_amount"],
        "total_amount": row["total_amount"],
        "last_autosaved_at": row["last_autosaved_at"],
    }


def _item_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "service_id": str(row["service_id"]),
        "service_name_at_time": row["service_name_at_time"],
        "department_id_at_time": str(row["department_id_at_time"]) if row["department_id_at_time"] is not None else None,
        "department_name_at_time": row["department_name_at_time"],
        "quantity": row["quantity"],
        "unit_price_at_time": row["unit_price_at_time"],
        "gross_amount": row["gross_amount"],
        "discount_amount": row["discount_amount"],
        "tax_amount": row["tax_amount"],
        "final_line_total": row["final_line_total"],
        "catalog_version": row["catalog_version"],
        "price_version": row["price_version"],
    }


def _validate_line(quantity: float, unit_price: float, discount: float) -> tuple[float, float]:
    if quantity <= 0:
        raise AppError("BILL_ITEM_QUANTITY_INVALID", "Quantity must be greater than zero.", 422)
    gross = quantity * unit_price
    if discount < 0 or discount > gross:
        raise AppError("BILL_ITEM_DISCOUNT_INVALID", "Discount cannot make line total negative.", 422)
    return gross, gross - discount


def create_draft(data: Any, context: dict[str, Any], request_id: str | None) -> dict[str, Any]:
    now = utc_now()
    device = context["device"]
    with connect() as conn:
        session = _active_session(conn, device["id"])
        seq = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM bill_drafts").fetchone()["next_id"]
        draft_number = f"HYD01-DEV001-DRAFT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{seq:06d}"
        conn.execute(
            """
            INSERT INTO bill_drafts (
                draft_number, organization_id, branch_id, device_id, cashier_session_id,
                cashier_user_id, patient_id, bill_type, department_id, doctor_id, status,
                subtotal_amount, discount_amount, tax_amount, total_amount, notes,
                last_autosaved_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft', 0, 0, 0, 0, ?, ?, ?, ?)
            """,
            (
                draft_number,
                device["organization_id"],
                device["branch_id"],
                device["id"],
                session["id"],
                context["user"]["id"],
                _as_id(data.patient_id),
                data.bill_type,
                _as_id(data.department_id),
                _as_id(data.doctor_id),
                data.notes,
                now,
                now,
                now,
            ),
        )
        draft = dict(conn.execute("SELECT * FROM bill_drafts WHERE draft_number = ?", (draft_number,)).fetchone())
        audit(conn, "bill_draft.create", user_id=context["user"]["id"], entity_type="bill_draft", entity_id=str(draft["id"]), request_id=request_id)
    return {"draft": _draft_header(draft)}


def list_drafts(status: str | None, patient_id: str | None, cashier_session_id: str | None, page: int, page_size: int) -> dict[str, Any]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    clauses = ["bd.organization_id = 1"]
    params: list[Any] = []
    if status:
        clauses.append("bd.status = ?")
        params.append(status)
    if patient_id:
        clauses.append("bd.patient_id = ?")
        params.append(int(patient_id))
    if cashier_session_id:
        clauses.append("bd.cashier_session_id = ?")
        params.append(int(cashier_session_id))
    where = " AND ".join(clauses)
    offset = (page - 1) * page_size
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS total FROM bill_drafts bd WHERE {where}", params).fetchone()["total"]
        rows = conn.execute(
            f"""
            SELECT bd.*, p.full_name AS patient_name
            FROM bill_drafts bd
            LEFT JOIN patients p ON p.id = bd.patient_id
            WHERE {where}
            ORDER BY bd.updated_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
    return {"items": [_draft_summary(dict(row)) for row in rows], "page": page, "page_size": page_size, "total": total, "has_next": offset + len(rows) < total}


def draft_detail(draft_id: int) -> dict[str, Any]:
    with connect() as conn:
        draft = _draft_or_error(conn, draft_id)
        patient = row_dict(conn.execute("SELECT id, full_name, phone FROM patients WHERE id = ?", (draft["patient_id"],)).fetchone()) if draft["patient_id"] else None
        department = row_dict(conn.execute("SELECT id, department_name FROM departments WHERE id = ?", (draft["department_id"],)).fetchone()) if draft["department_id"] else None
        doctor = row_dict(conn.execute("SELECT id, full_name FROM doctors WHERE id = ?", (draft["doctor_id"],)).fetchone()) if draft["doctor_id"] else None
        items = [dict(row) for row in conn.execute("SELECT * FROM bill_draft_items WHERE draft_id = ? ORDER BY id", (draft_id,)).fetchall()]
    return {
        "draft": {
            **_draft_header(draft),
            "patient": ({**patient, "id": str(patient["id"])} if patient else None),
            "department": ({**department, "id": str(department["id"])} if department else None),
            "doctor": ({**doctor, "id": str(doctor["id"])} if doctor else None),
            "items": [_item_payload(item) for item in items],
        }
    }


def update_draft(draft_id: int, data: Any, user_id: int, request_id: str | None) -> dict[str, Any]:
    now = utc_now()
    with connect() as conn:
        _draft_or_error(conn, draft_id, editable=True)
        conn.execute(
            """
            UPDATE bill_drafts
            SET patient_id = ?, department_id = ?, doctor_id = ?, notes = ?,
                last_autosaved_at = ?, updated_at = ?
            WHERE id = ?
            """,
            (_as_id(data.patient_id), _as_id(data.department_id), _as_id(data.doctor_id), data.notes, now, now, draft_id),
        )
        draft = dict(conn.execute("SELECT * FROM bill_drafts WHERE id = ?", (draft_id,)).fetchone())
        audit(conn, "bill_draft.update", user_id=user_id, entity_type="bill_draft", entity_id=str(draft_id), request_id=request_id)
    return {"draft": _draft_header(draft)}


def add_item(draft_id: int, data: Any, context: dict[str, Any], request_id: str | None) -> dict[str, Any]:
    now = utc_now()
    with connect() as conn:
        draft = _draft_or_error(conn, draft_id, editable=True)
        service = conn.execute(
            """
            SELECT s.*, d.department_name, sp.price_amount, sp.currency, sp.price_version
            FROM services s
            LEFT JOIN departments d ON d.id = s.department_id
            LEFT JOIN service_prices sp ON sp.service_id = s.id AND sp.status = 'active'
            WHERE s.id = ? AND s.status = 'active'
            """,
            (int(data.service_id),),
        ).fetchone()
        if not service:
            raise AppError("SERVICE_NOT_FOUND", "Active service not found.", 404)
        gross, final = _validate_line(data.quantity, service["price_amount"], data.discount_amount)
        conn.execute(
            """
            INSERT INTO bill_draft_items (
                draft_id, organization_id, branch_id, device_id, service_id, service_code_at_time,
                service_name_at_time, department_id_at_time, department_name_at_time, doctor_id,
                quantity, unit_price_at_time, gross_amount, discount_amount, tax_amount,
                final_line_total, catalog_version, price_version, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 0, ?, ?, ?, ?, ?, ?)
            """,
            (
                draft_id, draft["organization_id"], draft["branch_id"], draft["device_id"], service["id"],
                service["service_code"], service["service_name"], service["department_id"], service["department_name"],
                _as_id(data.doctor_id), data.quantity, service["price_amount"], gross, data.discount_amount,
                final, service["catalog_version"], service["price_version"], data.notes, now, now,
            ),
        )
        item = dict(conn.execute("SELECT * FROM bill_draft_items WHERE draft_id = ? ORDER BY id DESC LIMIT 1", (draft_id,)).fetchone())
        totals = _totals(conn, draft_id)
        last = conn.execute("SELECT last_autosaved_at FROM bill_drafts WHERE id = ?", (draft_id,)).fetchone()["last_autosaved_at"]
        audit(conn, "bill_draft.item_add", user_id=context["user"]["id"], entity_type="bill_draft", entity_id=str(draft_id), request_id=request_id)
    return {"item": _item_payload(item), "totals": totals, "last_autosaved_at": last}


def update_item(draft_id: int, item_id: int, data: Any) -> dict[str, Any]:
    now = utc_now()
    with connect() as conn:
        _draft_or_error(conn, draft_id, editable=True)
        item = conn.execute("SELECT * FROM bill_draft_items WHERE id = ? AND draft_id = ?", (item_id, draft_id)).fetchone()
        if not item:
            raise AppError("BILL_DRAFT_ITEM_NOT_FOUND", "Draft item not found.", 404)
        gross, final = _validate_line(data.quantity, item["unit_price_at_time"], data.discount_amount)
        conn.execute(
            """
            UPDATE bill_draft_items
            SET quantity = ?, gross_amount = ?, discount_amount = ?, final_line_total = ?,
                notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (data.quantity, gross, data.discount_amount, final, data.notes, now, item_id),
        )
        updated = dict(conn.execute("SELECT * FROM bill_draft_items WHERE id = ?", (item_id,)).fetchone())
        totals = _totals(conn, draft_id)
        last = conn.execute("SELECT last_autosaved_at FROM bill_drafts WHERE id = ?", (draft_id,)).fetchone()["last_autosaved_at"]
    return {"item": _item_payload(updated), "totals": totals, "last_autosaved_at": last}


def remove_item(draft_id: int, item_id: int) -> dict[str, Any]:
    with connect() as conn:
        _draft_or_error(conn, draft_id, editable=True)
        item = conn.execute("SELECT id FROM bill_draft_items WHERE id = ? AND draft_id = ?", (item_id, draft_id)).fetchone()
        if not item:
            raise AppError("BILL_DRAFT_ITEM_NOT_FOUND", "Draft item not found.", 404)
        conn.execute("DELETE FROM bill_draft_items WHERE id = ?", (item_id,))
        totals = _totals(conn, draft_id)
        last = conn.execute("SELECT last_autosaved_at FROM bill_drafts WHERE id = ?", (draft_id,)).fetchone()["last_autosaved_at"]
    return {"removed": True, "totals": totals, "last_autosaved_at": last}


def void_draft(draft_id: int, reason: str | None, user_id: int, request_id: str | None) -> dict[str, Any]:
    now = utc_now()
    with connect() as conn:
        _draft_or_error(conn, draft_id, editable=True)
        conn.execute("UPDATE bill_drafts SET status = 'voided', notes = ?, updated_at = ?, last_autosaved_at = ? WHERE id = ?", (reason, now, now, draft_id))
        draft = dict(conn.execute("SELECT * FROM bill_drafts WHERE id = ?", (draft_id,)).fetchone())
        audit(conn, "bill_draft.void", user_id=user_id, entity_type="bill_draft", entity_id=str(draft_id), request_id=request_id)
    return {"draft": _draft_header(draft)}
