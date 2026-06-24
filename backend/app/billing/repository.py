from __future__ import annotations

import hashlib
import json
import sqlite3
from datetime import datetime, timezone
from typing import Any

from app.auth.repository import audit, row_dict
from app.core.errors import AppError
from app.database.connection import connect, utc_now


def _as_id(value: str | None) -> int | None:
    return int(value) if value not in (None, "") else None


def _paise(value: float | int | None) -> int:
    return int(round(float(value or 0) * 100))


def _amount(value: int | None) -> float:
    return (value or 0) / 100


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


def _seq(conn: sqlite3.Connection, table: str) -> int:
    return conn.execute(f"SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM {table}").fetchone()["next_id"]


def _number(kind: str, seq: int) -> str:
    return f"HYD01-DEV001-{kind}-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{seq:06d}"


def _bill_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "bill_number": row["bill_number"],
        "status": row["status"],
        "currency": row["currency"],
        "subtotal_amount": _amount(row["subtotal_amount_paise"]),
        "discount_amount": _amount(row["discount_amount_paise"]),
        "tax_amount": _amount(row["tax_amount_paise"]),
        "total_amount": _amount(row["total_amount_paise"]),
        "sync_status": row["sync_status"],
        "finalized_at": row["finalized_at"],
    }


def _payment_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "payment_number": row["payment_number"],
        "payment_method": row["payment_method"],
        "status": row["status"],
        "amount": _amount(row["amount_paise"]),
        "received_amount": _amount(row["received_amount_paise"]),
        "change_amount": _amount(row["change_amount_paise"]),
        "paid_at": row["paid_at"],
    }


def _receipt_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "receipt_number": row["receipt_number"],
        "status": row["status"],
        "receipt_type": row["receipt_type"],
        "generated_at": row["generated_at"],
    }


def _sync_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {"id": str(row["id"]), "event_type": row["event_type"], "status": row["status"]}


def _request_hash(payload: dict[str, Any]) -> str:
    return hashlib.sha256(json.dumps(payload, sort_keys=True).encode()).hexdigest()


def finalize_draft(
    draft_id: int,
    data: Any,
    context: dict[str, Any],
    idempotency_key: str | None,
    request_path: str,
    request_id: str | None,
) -> dict[str, Any]:
    if not idempotency_key:
        raise AppError("IDEMPOTENCY_KEY_REQUIRED", "Idempotency-Key header is required.", 400)
    if data.payment_method != "cash":
        raise AppError("PAYMENT_METHOD_NOT_SUPPORTED", "Only cash payment is supported.", 422)
    request_hash = _request_hash(data.model_dump())
    now = utc_now()
    device = context["device"]
    with connect() as conn:
        idem = conn.execute("SELECT * FROM idempotency_keys WHERE idempotency_key = ?", (idempotency_key,)).fetchone()
        if idem:
            if idem["request_hash"] != request_hash:
                raise AppError("IDEMPOTENCY_KEY_CONFLICT", "Idempotency key was used with different payload.", 409)
            if idem["status"] == "completed" and idem["response_payload_json"]:
                return json.loads(idem["response_payload_json"])
        else:
            conn.execute(
                """
                INSERT INTO idempotency_keys (
                    idempotency_key, request_method, request_path, request_hash, status, created_at, updated_at
                )
                VALUES (?, 'POST', ?, ?, 'processing', ?, ?)
                """,
                (idempotency_key, request_path, request_hash, now, now),
            )

        if conn.execute("SELECT id FROM bills WHERE draft_id = ?", (draft_id,)).fetchone():
            raise AppError("DUPLICATE_FINALIZATION_BLOCKED", "Draft already finalized.", 409)

        session = _active_session(conn, device["id"])
        draft = _draft_or_error(conn, draft_id, editable=True)
        if not draft["patient_id"]:
            raise AppError("PATIENT_REQUIRED", "Patient is required to finalize bill.", 422)
        items = [dict(row) for row in conn.execute("SELECT * FROM bill_draft_items WHERE draft_id = ? ORDER BY id", (draft_id,)).fetchall()]
        if not items:
            raise AppError("DRAFT_HAS_NO_ITEMS", "Draft has no items.", 422)
        _totals(conn, draft_id)
        draft = _draft_or_error(conn, draft_id, editable=True)
        total_paise = _paise(draft["total_amount"])
        received_paise = _paise(data.received_amount if data.received_amount is not None else draft["total_amount"])
        if received_paise < total_paise:
            raise AppError("PAYMENT_AMOUNT_INSUFFICIENT", "Cash received is less than bill total.", 422)

        bill_number = _number("BILL", _seq(conn, "bills"))
        payment_number = _number("PAY", _seq(conn, "payments"))
        receipt_number = _number("RCPT", _seq(conn, "receipts"))
        conn.execute(
            """
            INSERT INTO bills (
                bill_number, draft_id, organization_id, branch_id, device_id, cashier_session_id,
                cashier_user_id, patient_id, bill_type, department_id, doctor_id, status, currency,
                subtotal_amount_paise, discount_amount_paise, tax_amount_paise, total_amount_paise,
                finalized_at, idempotency_key, sync_status, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'finalized', 'INR', ?, ?, ?, ?, ?, ?, 'pending', ?, ?)
            """,
            (
                bill_number, draft_id, draft["organization_id"], draft["branch_id"], draft["device_id"],
                session["id"], context["user"]["id"], draft["patient_id"], draft["bill_type"],
                draft["department_id"], draft["doctor_id"], _paise(draft["subtotal_amount"]),
                _paise(draft["discount_amount"]), _paise(draft["tax_amount"]), total_paise,
                now, idempotency_key, now, now,
            ),
        )
        bill = dict(conn.execute("SELECT * FROM bills WHERE bill_number = ?", (bill_number,)).fetchone())
        for item in items:
            conn.execute(
                """
                INSERT INTO bill_items (
                    bill_id, draft_item_id, organization_id, branch_id, device_id, service_id,
                    service_code_at_time, service_name_at_time, department_id_at_time,
                    department_name_at_time, doctor_id, quantity, unit_price_paise,
                    gross_amount_paise, discount_amount_paise, tax_amount_paise,
                    final_line_total_paise, catalog_version, price_version, created_at, updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    bill["id"], item["id"], item["organization_id"], item["branch_id"], item["device_id"],
                    item["service_id"], item["service_code_at_time"], item["service_name_at_time"],
                    item["department_id_at_time"], item["department_name_at_time"], item["doctor_id"],
                    item["quantity"], _paise(item["unit_price_at_time"]), _paise(item["gross_amount"]),
                    _paise(item["discount_amount"]), _paise(item["tax_amount"]),
                    _paise(item["final_line_total"]), item["catalog_version"], item["price_version"], now, now,
                ),
            )
        conn.execute(
            """
            INSERT INTO payments (
                payment_number, bill_id, organization_id, branch_id, device_id, cashier_session_id,
                cashier_user_id, payment_method, status, currency, amount_paise, received_amount_paise,
                change_amount_paise, idempotency_key, paid_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, 'cash', 'paid', 'INR', ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                payment_number, bill["id"], bill["organization_id"], bill["branch_id"], bill["device_id"],
                bill["cashier_session_id"], bill["cashier_user_id"], total_paise, received_paise,
                received_paise - total_paise, idempotency_key, now, now, now,
            ),
        )
        payment = dict(conn.execute("SELECT * FROM payments WHERE payment_number = ?", (payment_number,)).fetchone())
        receipt_json = _build_receipt_payload(conn, bill, payment, receipt_number)
        conn.execute(
            """
            INSERT INTO receipts (
                receipt_number, bill_id, payment_id, organization_id, branch_id, device_id,
                cashier_session_id, cashier_user_id, status, receipt_type, receipt_payload_json,
                generated_at, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'generated', 'original', ?, ?, ?, ?)
            """,
            (
                receipt_number, bill["id"], payment["id"], bill["organization_id"], bill["branch_id"],
                bill["device_id"], bill["cashier_session_id"], bill["cashier_user_id"],
                json.dumps(receipt_json), now, now, now,
            ),
        )
        receipt = dict(conn.execute("SELECT * FROM receipts WHERE receipt_number = ?", (receipt_number,)).fetchone())
        sync_payload = {"bill_id": bill["id"], "bill_number": bill["bill_number"], "total_amount_paise": total_paise}
        conn.execute(
            """
            INSERT INTO sync_events (
                event_type, entity_type, entity_id, organization_id, branch_id, device_id,
                payload_json, status, attempt_count, idempotency_key, created_at, updated_at
            )
            VALUES ('BILL_FINALIZED', 'bill', ?, ?, ?, ?, ?, 'pending', 0, ?, ?, ?)
            """,
            (str(bill["id"]), bill["organization_id"], bill["branch_id"], bill["device_id"], json.dumps(sync_payload), idempotency_key, now, now),
        )
        sync_event = dict(conn.execute("SELECT * FROM sync_events WHERE entity_type = 'bill' AND entity_id = ?", (str(bill["id"]),)).fetchone())
        conn.execute("UPDATE bill_drafts SET status = 'finalized', updated_at = ?, last_autosaved_at = ? WHERE id = ?", (now, now, draft_id))

        for action, entity_type, entity_id in [
            ("bill.finalize", "bill", bill["id"]),
            ("payment.cash.create", "payment", payment["id"]),
            ("receipt.generate", "receipt", receipt["id"]),
            ("sync_event.create", "sync_event", sync_event["id"]),
        ]:
            audit(conn, action, user_id=context["user"]["id"], entity_type=entity_type, entity_id=str(entity_id), request_id=request_id)

        response = {
            "bill": _bill_payload(bill),
            "payment": _payment_payload(payment),
            "receipt": _receipt_payload(receipt),
            "sync_event": _sync_payload(sync_event),
        }
        conn.execute(
            "UPDATE idempotency_keys SET response_payload_json = ?, status = 'completed', updated_at = ? WHERE idempotency_key = ?",
            (json.dumps(response), now, idempotency_key),
        )
    return response


def _build_receipt_payload(conn: sqlite3.Connection, bill: dict[str, Any], payment: dict[str, Any], receipt_number: str) -> dict[str, Any]:
    org = conn.execute("SELECT organization_name FROM organizations WHERE id = ?", (bill["organization_id"],)).fetchone()
    branch = conn.execute("SELECT branch_name FROM branches WHERE id = ?", (bill["branch_id"],)).fetchone()
    device = conn.execute("SELECT device_code, counter_name FROM devices WHERE id = ?", (bill["device_id"],)).fetchone()
    patient = conn.execute("SELECT full_name, patient_number FROM patients WHERE id = ?", (bill["patient_id"],)).fetchone()
    draft = conn.execute("SELECT notes FROM bill_drafts WHERE id = ?", (bill["draft_id"],)).fetchone()
    department = conn.execute("SELECT department_name FROM departments WHERE id = ?", (bill["department_id"],)).fetchone() if bill["department_id"] else None
    doctor = conn.execute("SELECT full_name FROM doctors WHERE id = ?", (bill["doctor_id"],)).fetchone() if bill["doctor_id"] else None
    cashier = conn.execute("SELECT display_name FROM users WHERE id = ?", (bill["cashier_user_id"],)).fetchone()
    items = [
        {
            "service_name": row["service_name_at_time"],
            "quantity": row["quantity"],
            "unit_price": _amount(row["unit_price_paise"]),
            "line_total": _amount(row["final_line_total_paise"]),
        }
        for row in conn.execute("SELECT * FROM bill_items WHERE bill_id = ? ORDER BY id", (bill["id"],)).fetchall()
    ]
    registration_context = _registration_context_from_notes(draft["notes"] if draft else None)
    return {
        "hospital_or_organization_name": org["organization_name"],
        "branch_name": branch["branch_name"],
        "device_code": device["device_code"],
        "counter_name": device["counter_name"],
        "bill_number": bill["bill_number"],
        "receipt_number": receipt_number,
        "patient_name": patient["full_name"],
        "patient_number": patient["patient_number"],
        "department_name": department["department_name"] if department else registration_context.get("department_name"),
        "doctor_name": doctor["full_name"] if doctor else registration_context.get("doctor_name"),
        "cashier_name": cashier["display_name"],
        "bill_type": bill["bill_type"],
        "registration": registration_context,
        "items": items,
        "subtotal_amount": _amount(bill["subtotal_amount_paise"]),
        "discount_amount": _amount(bill["discount_amount_paise"]),
        "tax_amount": _amount(bill["tax_amount_paise"]),
        "total_amount": _amount(bill["total_amount_paise"]),
        "payment_method": payment["payment_method"],
        "amount_paid": _amount(payment["amount_paise"]),
        "received_amount": _amount(payment["received_amount_paise"]),
        "change_amount": _amount(payment["change_amount_paise"]),
        "currency": bill["currency"],
        "generated_at": payment["paid_at"],
    }


def _registration_context_from_notes(notes: str | None) -> dict[str, Any]:
    if not notes or not notes.startswith("REGCTX:"):
        return {}
    first_line = notes.splitlines()[0]
    try:
        return json.loads(first_line.removeprefix("REGCTX:"))
    except json.JSONDecodeError:
        return {}


def list_bills(status: str | None, patient_id: str | None, cashier_session_id: str | None, page: int, page_size: int) -> dict[str, Any]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    clauses = ["b.organization_id = 1"]
    params: list[Any] = []
    if status:
        clauses.append("b.status = ?")
        params.append(status)
    if patient_id:
        clauses.append("b.patient_id = ?")
        params.append(int(patient_id))
    if cashier_session_id:
        clauses.append("b.cashier_session_id = ?")
        params.append(int(cashier_session_id))
    where = " AND ".join(clauses)
    offset = (page - 1) * page_size
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS total FROM bills b WHERE {where}", params).fetchone()["total"]
        rows = conn.execute(
            f"""
            SELECT b.*, p.full_name AS patient_name
            FROM bills b LEFT JOIN patients p ON p.id = b.patient_id
            WHERE {where}
            ORDER BY b.finalized_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, page_size, offset],
        ).fetchall()
    items = [{**_bill_payload(dict(row)), "patient_name": row["patient_name"]} for row in rows]
    return {"items": items, "page": page, "page_size": page_size, "total": total, "has_next": offset + len(rows) < total}


def bill_detail(bill_id: int) -> dict[str, Any]:
    with connect() as conn:
        bill = row_dict(conn.execute("SELECT * FROM bills WHERE id = ?", (bill_id,)).fetchone())
        if not bill:
            raise AppError("BILL_NOT_FOUND", "Bill not found.", 404)
        patient = row_dict(conn.execute("SELECT id, full_name, phone, patient_number FROM patients WHERE id = ?", (bill["patient_id"],)).fetchone())
        department = row_dict(conn.execute("SELECT id, department_name FROM departments WHERE id = ?", (bill["department_id"],)).fetchone()) if bill["department_id"] else None
        doctor = row_dict(conn.execute("SELECT id, full_name FROM doctors WHERE id = ?", (bill["doctor_id"],)).fetchone()) if bill["doctor_id"] else None
        items = [dict(row) for row in conn.execute("SELECT * FROM bill_items WHERE bill_id = ? ORDER BY id", (bill_id,)).fetchall()]
        payment = row_dict(conn.execute("SELECT * FROM payments WHERE bill_id = ?", (bill_id,)).fetchone())
        receipt = row_dict(conn.execute("SELECT * FROM receipts WHERE bill_id = ?", (bill_id,)).fetchone())
    return {
        "bill": {
            **_bill_payload(bill),
            "patient": ({**patient, "id": str(patient["id"])} if patient else None),
            "department": ({**department, "id": str(department["id"])} if department else None),
            "doctor": ({**doctor, "id": str(doctor["id"])} if doctor else None),
            "items": [
                {
                    "id": str(item["id"]),
                    "service_name_at_time": item["service_name_at_time"],
                    "quantity": item["quantity"],
                    "unit_price": _amount(item["unit_price_paise"]),
                    "final_line_total": _amount(item["final_line_total_paise"]),
                    "catalog_version": item["catalog_version"],
                    "price_version": item["price_version"],
                }
                for item in items
            ],
            "payment": _payment_payload(payment) if payment else None,
            "receipt": _receipt_payload(receipt) if receipt else None,
        }
    }


def receipt_by_bill(bill_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = row_dict(conn.execute("SELECT * FROM receipts WHERE bill_id = ?", (bill_id,)).fetchone())
    if not row:
        raise AppError("RECEIPT_NOT_FOUND", "Receipt not found.", 404)
    return {"receipt": {**_receipt_payload(row), "receipt_payload": json.loads(row["receipt_payload_json"])}}


def receipt_detail(receipt_id: int) -> dict[str, Any]:
    with connect() as conn:
        row = row_dict(conn.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,)).fetchone())
    if not row:
        raise AppError("RECEIPT_NOT_FOUND", "Receipt not found.", 404)
    return {"receipt": {**_receipt_payload(row), "receipt_payload": json.loads(row["receipt_payload_json"])}}


def pending_sync_events() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT id, event_type, entity_type, entity_id, status, attempt_count, created_at
            FROM sync_events WHERE status = 'pending' ORDER BY id
            """
        ).fetchall()
    return {"items": [{**dict(row), "id": str(row["id"])} for row in rows]}
