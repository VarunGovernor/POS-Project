from __future__ import annotations

import json
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import APIRouter, Depends, Query, Request
from pydantic import BaseModel

from app.auth.dependencies import require_permission
from app.auth.repository import audit
from app.config import settings
from app.core.errors import AppError
from app.core.responses import success_response
from app.database.connection import connect, database_health, database_path, utc_now
from app.printer.repository import printer_status_value
from app.recovery.repository import recovery_status
from app.sync.repository import sync_status

router = APIRouter(tags=["operations"])


class SettingPatch(BaseModel):
    setting_key: str
    setting_value: str
    setting_scope: str = "device"


def _amount(paise: int | None) -> float:
    return (paise or 0) / 100


@router.get("/reports/today-collection")
async def today_collection(request: Request, context: dict = Depends(require_permission("report.today.view"))) -> dict:
    day = utc_now()[:10]
    with connect() as conn:
        row = conn.execute(
            """
            SELECT COUNT(*) AS bill_count,
                   COALESCE(SUM(subtotal_amount_paise), 0) AS gross,
                   COALESCE(SUM(discount_amount_paise), 0) AS discount,
                   COALESCE(SUM(tax_amount_paise), 0) AS tax,
                   COALESCE(SUM(total_amount_paise), 0) AS net
            FROM bills WHERE status = 'finalized' AND substr(finalized_at, 1, 10) = ?
            """,
            (day,),
        ).fetchone()
        cash = conn.execute(
            """
            SELECT COALESCE(SUM(amount_paise), 0) AS total FROM payments
            WHERE status = 'paid' AND payment_method = 'cash' AND substr(paid_at, 1, 10) = ?
            """,
            (day,),
        ).fetchone()["total"]
        receipts = conn.execute("SELECT COUNT(*) AS c FROM receipts WHERE substr(generated_at, 1, 10) = ?", (day,)).fetchone()["c"]
        printed = conn.execute("SELECT COUNT(DISTINCT receipt_id) AS c FROM printer_jobs WHERE status = 'printed' AND job_type = 'receipt_original'").fetchone()["c"]
        pending = conn.execute("SELECT COUNT(*) AS c FROM sync_events WHERE status IN ('pending', 'failed_retryable')").fetchone()["c"]
    return success_response(request, {
        "business_date": day,
        "currency": "INR",
        "bill_count": row["bill_count"],
        "gross_amount": _amount(row["gross"]),
        "discount_amount": _amount(row["discount"]),
        "tax_amount": _amount(row["tax"]),
        "net_amount": _amount(row["net"]),
        "cash_collected": _amount(cash),
        "receipt_count": receipts,
        "printed_receipt_count": printed,
        "pending_sync_count": pending,
    })


@router.get("/reports/cashier-session/{session_id}")
async def cashier_session_report(session_id: int, request: Request, context: dict = Depends(require_permission("report.session.view"))) -> dict:
    with connect() as conn:
        session = conn.execute(
            """
            SELECT cs.*, u.display_name AS cashier_name FROM cashier_sessions cs
            JOIN users u ON u.id = cs.cashier_user_id
            WHERE cs.id = ?
            """,
            (session_id,),
        ).fetchone()
        if not session:
            raise AppError("CASHIER_SESSION_NOT_FOUND", "Cashier session not found.", 404)
        summary = conn.execute(
            """
            SELECT COUNT(DISTINCT b.id) AS bill_count, COALESCE(SUM(p.amount_paise), 0) AS cash
            FROM bills b
            LEFT JOIN payments p ON p.bill_id = b.id AND p.status = 'paid' AND p.payment_method = 'cash'
            WHERE b.cashier_session_id = ? AND b.status = 'finalized'
            """,
            (session_id,),
        ).fetchone()
    return success_response(request, {
        "session": {
            "id": str(session["id"]),
            "session_number": session["session_number"],
            "status": session["status"],
            "cashier_name": session["cashier_name"],
            "opened_at": session["opened_at"],
            "closed_at": session["closed_at"],
        },
        "summary": {
            "bill_count": summary["bill_count"],
            "cash_collected": _amount(summary["cash"]),
            "opening_cash_amount": session["opening_cash_amount"],
            "expected_cash_amount": session["opening_cash_amount"] + _amount(summary["cash"]),
            "closing_cash_amount": session["closing_cash_amount"],
            "cash_difference_amount": session["cash_difference_amount"],
        },
    })


@router.get("/reports/department-collection")
async def department_collection(request: Request, context: dict = Depends(require_permission("report.department.view"))) -> dict:
    with connect() as conn:
        rows = conn.execute(
            """
            SELECT COALESCE(department_name_at_time, 'Unassigned') AS department_name,
                   COUNT(DISTINCT bill_id) AS bill_count,
                   COALESCE(SUM(final_line_total_paise), 0) AS total
            FROM bill_items
            GROUP BY department_name
            ORDER BY department_name
            """
        ).fetchall()
    return success_response(request, {"items": [{"department_name": row["department_name"], "bill_count": row["bill_count"], "net_amount": _amount(row["total"])} for row in rows]})


@router.get("/reports/pending-sync")
async def pending_sync(request: Request, context: dict = Depends(require_permission("report.view"))) -> dict:
    with connect() as conn:
        by_status = [dict(row) for row in conn.execute("SELECT status, COUNT(*) AS count FROM sync_events GROUP BY status").fetchall()]
        by_event_type = [dict(row) for row in conn.execute("SELECT event_type, COUNT(*) AS count FROM sync_events GROUP BY event_type").fetchall()]
    return success_response(request, {"by_status": by_status, "by_event_type": by_event_type})


@router.get("/settings")
async def list_settings(request: Request, setting_scope: str | None = None, setting_key: str | None = None, context: dict = Depends(require_permission("settings.view"))) -> dict:
    clauses, params = [], []
    if setting_scope:
        clauses.append("setting_scope = ?")
        params.append(setting_scope)
    if setting_key:
        clauses.append("setting_key = ?")
        params.append(setting_key)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    with connect() as conn:
        rows = conn.execute(f"SELECT * FROM settings {where} ORDER BY setting_scope, setting_key", params).fetchall()
    return success_response(request, {"items": [{**dict(row), "id": str(row["id"]), "is_readonly": bool(row["is_readonly"])} for row in rows]})


@router.patch("/settings")
async def update_setting(payload: SettingPatch, request: Request, context: dict = Depends(require_permission("settings.update"))) -> dict:
    now = utc_now()
    with connect() as conn:
        row = conn.execute("SELECT * FROM settings WHERE setting_key = ? AND setting_scope = ?", (payload.setting_key, payload.setting_scope)).fetchone()
        if not row:
            raise AppError("SETTING_NOT_FOUND", "Setting not found.", 404)
        if row["is_readonly"]:
            raise AppError("SETTING_READONLY", "Readonly setting cannot be updated.", 409)
        conn.execute("UPDATE settings SET setting_value = ?, updated_at = ? WHERE id = ?", (payload.setting_value, now, row["id"]))
        audit(conn, "settings.update", user_id=context["user"]["id"], entity_type="setting", entity_id=str(row["id"]), request_id=request.state.request_id)
        updated = dict(conn.execute("SELECT * FROM settings WHERE id = ?", (row["id"],)).fetchone())
    return success_response(request, {"setting": {**updated, "id": str(updated["id"]), "is_readonly": bool(updated["is_readonly"])}})


@router.get("/support/status")
async def support_status(request: Request, context: dict = Depends(require_permission("support.view"))) -> dict:
    db = database_health()
    sync = sync_status()
    recovery = recovery_status()
    support_dir = database_path().parent / "support"
    support_dir.mkdir(parents=True, exist_ok=True)
    with connect() as conn:
        failed_print = conn.execute("SELECT COUNT(*) AS c FROM printer_jobs WHERE status = 'failed'").fetchone()["c"]
    return success_response(request, {
        "api": "ok",
        "database": db["status"],
        "printer": printer_status_value(),
        "sync": sync["status"],
        "recovery": "required" if recovery["recovery_required"] else "ok",
        "storage": "ok" if support_dir.exists() else "error",
        "app_version": settings.app_version,
        "backend_version": settings.backend_version,
        "database_version": db["database_version"],
        "pending_sync_count": sync["pending_count"] + sync["failed_retryable_count"],
        "failed_sync_count": sync["failed_permanent_count"],
        "failed_print_job_count": failed_print,
        "open_recovery_marker_count": recovery["open_marker_count"],
    })


@router.post("/support/bundle")
async def support_bundle(request: Request, context: dict = Depends(require_permission("support.bundle.create"))) -> dict:
    now = utc_now()
    bundle_id = f"SUP-{uuid4()}"
    support_dir = database_path().parent / "support"
    support_dir.mkdir(parents=True, exist_ok=True)
    path = support_dir / f"{bundle_id}.json"
    metadata: dict[str, Any] = {"created_at": now, "database_version": database_health()["database_version"], "sync": sync_status(), "recovery": recovery_status()}
    path.write_text(json.dumps(metadata, indent=2), encoding="utf-8")
    with connect() as conn:
        conn.execute(
            "INSERT INTO support_bundles (bundle_id, status, file_path, metadata_json, created_by_user_id, created_at) VALUES (?, 'created', ?, ?, ?, ?)",
            (bundle_id, str(path), json.dumps(metadata), context["user"]["id"], now),
        )
        audit(conn, "support.bundle.create", user_id=context["user"]["id"], entity_type="support_bundle", entity_id=bundle_id, request_id=request.state.request_id)
    return success_response(request, {"bundle": {"bundle_id": bundle_id, "status": "created", "file_path": str(path), "created_at": now}})


@router.get("/audit/logs")
async def audit_logs(
    request: Request,
    action: str | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    severity: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    context: dict = Depends(require_permission("audit.view")),
) -> dict:
    clauses: list[str] = []
    params: list[Any] = []
    for column, value in [("action", action), ("entity_type", entity_type), ("entity_id", entity_id), ("severity", severity)]:
        if value:
            clauses.append(f"{column} = ?")
            params.append(value)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    offset = (page - 1) * page_size
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM audit_logs {where}", params).fetchone()["c"]
        rows = conn.execute(f"SELECT * FROM audit_logs {where} ORDER BY created_at DESC LIMIT ? OFFSET ?", [*params, page_size, offset]).fetchall()
    items = []
    for row in rows:
        item = dict(row)
        item["id"] = str(item["id"])
        item["metadata"] = json.loads(item["metadata_json"]) if item["metadata_json"] else None
        item.pop("metadata_json", None)
        items.append(item)
    return success_response(request, {"items": items, "page": page, "page_size": page_size, "total": total, "has_next": offset + len(items) < total})
