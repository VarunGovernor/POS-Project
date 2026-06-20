from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any

from app.auth.repository import audit, row_dict
from app.core.errors import AppError
from app.database.connection import connect, utc_now
from app.printer.adapter import adapter


def _job_number(seq: int) -> str:
    return f"HYD01-DEV001-PRINT-{datetime.now(timezone.utc).strftime('%Y%m%d')}-{seq:06d}"


def _job_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "job_number": row["job_number"],
        "job_type": row["job_type"],
        "status": row["status"],
        "attempt_count": row["attempt_count"],
        "printed_at": row["printed_at"],
        "failure_message": row["failure_message"],
    }


def _printer(conn) -> dict[str, Any] | None:
    return row_dict(conn.execute("SELECT * FROM printer_devices WHERE is_default = 1 ORDER BY id LIMIT 1").fetchone())


def printer_status_value() -> str:
    try:
        with connect() as conn:
            printer = _printer(conn)
            return printer["status"] if printer else "not_configured"
    except Exception:
        return "error"


def status() -> dict[str, Any]:
    with connect() as conn:
        printer = _printer(conn)
        queued = conn.execute("SELECT COUNT(*) AS c FROM printer_jobs WHERE status IN ('queued', 'printing')").fetchone()["c"]
        failed = conn.execute("SELECT COUNT(*) AS c FROM printer_jobs WHERE status = 'failed'").fetchone()["c"]
        last = conn.execute("SELECT MAX(printed_at) AS last_printed_at FROM printer_jobs WHERE status = 'printed'").fetchone()["last_printed_at"]
    return {
        "status": printer["status"] if printer else "not_configured",
        "printer": (
            {
                "id": str(printer["id"]),
                "printer_code": printer["printer_code"],
                "printer_name": printer["printer_name"],
                "printer_type": printer["printer_type"],
                "connection_type": printer["connection_type"],
                "is_default": bool(printer["is_default"]),
                "last_seen_at": printer["last_seen_at"],
            }
            if printer
            else None
        ),
        "queued_job_count": queued,
        "failed_job_count": failed,
        "last_printed_at": last,
    }


def _create_job(conn, printer: dict[str, Any], receipt: dict[str, Any] | None, job_type: str, user_id: int, payload: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    seq = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM printer_jobs").fetchone()["next_id"]
    conn.execute(
        """
        INSERT INTO printer_jobs (
            job_number, organization_id, branch_id, device_id, printer_device_id, receipt_id,
            bill_id, job_type, status, attempt_count, max_attempts, payload_json,
            created_by_user_id, created_at, updated_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, 'queued', 0, 3, ?, ?, ?, ?)
        """,
        (
            _job_number(seq),
            receipt["organization_id"] if receipt else printer["organization_id"],
            receipt["branch_id"] if receipt else printer["branch_id"],
            receipt["device_id"] if receipt else printer["device_id"],
            printer["id"], receipt["id"] if receipt else None, receipt["bill_id"] if receipt else None, job_type, json.dumps(payload), user_id, now, now,
        ),
    )
    return dict(conn.execute("SELECT * FROM printer_jobs ORDER BY id DESC LIMIT 1").fetchone())


def _attempt(conn, job: dict[str, Any], printer: dict[str, Any]) -> dict[str, Any]:
    now = utc_now()
    payload = json.loads(job["payload_json"])
    ok, failure = adapter.print_payload(printer, payload)
    conn.execute(
        """
        UPDATE printer_jobs
        SET status = ?, attempt_count = attempt_count + 1, failure_message = ?,
            printed_at = ?, last_attempt_at = ?, updated_at = ?
        WHERE id = ?
        """,
        ("printed" if ok else "failed", failure, now if ok else None, now, now, job["id"]),
    )
    conn.execute("UPDATE printer_devices SET last_seen_at = ?, updated_at = ? WHERE id = ?", (now, now, printer["id"]))
    return dict(conn.execute("SELECT * FROM printer_jobs WHERE id = ?", (job["id"],)).fetchone())


def test_print(user_id: int, request_id: str | None) -> dict[str, Any]:
    with connect() as conn:
        printer = _printer(conn)
        if not printer or printer["status"] != "active":
            raise AppError("PRINTER_NOT_CONFIGURED", "Printer is not configured.", 409)
        payload = {"test": True, "printer": printer["printer_code"]}
        job = _create_job(conn, printer, None, "test_print", user_id, payload)
        job = _attempt(conn, job, printer)
        audit(conn, "printer.test", user_id=user_id, entity_type="printer_job", entity_id=str(job["id"]), request_id=request_id)
    return {"job": _job_payload(job)}


def jobs(status_filter: str | None, receipt_id: str | None, bill_id: str | None, page: int, page_size: int) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if status_filter:
        clauses.append("status = ?")
        params.append(status_filter)
    if receipt_id:
        clauses.append("receipt_id = ?")
        params.append(int(receipt_id))
    if bill_id:
        clauses.append("bill_id = ?")
        params.append(int(bill_id))
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM printer_jobs {where}", params).fetchone()["c"]
        rows = conn.execute(f"SELECT * FROM printer_jobs {where} ORDER BY id DESC LIMIT ? OFFSET ?", [*params, page_size, offset]).fetchall()
    return {"items": [_job_payload(dict(row)) for row in rows], "page": page, "page_size": page_size, "total": total, "has_next": offset + len(rows) < total}


def print_receipt(receipt_id: int, user_id: int, request_id: str | None, reprint_reason: str | None = None) -> dict[str, Any]:
    job_type = "receipt_reprint" if reprint_reason is not None else "receipt_original"
    with connect() as conn:
        printer = _printer(conn)
        if not printer or printer["status"] != "active":
            raise AppError("PRINTER_NOT_CONFIGURED", "Printer is not configured.", 409)
        receipt = row_dict(conn.execute("SELECT * FROM receipts WHERE id = ?", (receipt_id,)).fetchone())
        if not receipt:
            raise AppError("RECEIPT_NOT_FOUND", "Receipt not found.", 404)
        if job_type == "receipt_original" and conn.execute(
            "SELECT id FROM printer_jobs WHERE receipt_id = ? AND job_type = 'receipt_original' AND status = 'printed'",
            (receipt_id,),
        ).fetchone():
            raise AppError("RECEIPT_ALREADY_PRINTED", "Receipt already printed. Use reprint.", 409)
        payload = json.loads(receipt["receipt_payload_json"])
        if reprint_reason is not None:
            payload = {**payload, "reprint_reason": reprint_reason}
        job = _create_job(conn, printer, receipt, job_type, user_id, payload)
        job = _attempt(conn, job, printer)
        audit(
            conn,
            "receipt.reprint" if reprint_reason is not None else "receipt.print",
            user_id=user_id,
            entity_type="printer_job",
            entity_id=str(job["id"]),
            metadata={"reason": reprint_reason} if reprint_reason else None,
            request_id=request_id,
        )
    return {"job": _job_payload(job)}


def retry_job(job_id: int, user_id: int, request_id: str | None) -> dict[str, Any]:
    with connect() as conn:
        job = row_dict(conn.execute("SELECT * FROM printer_jobs WHERE id = ?", (job_id,)).fetchone())
        if not job:
            raise AppError("PRINTER_JOB_NOT_FOUND", "Printer job not found.", 404)
        if job["status"] != "failed":
            raise AppError("PRINTER_JOB_NOT_RETRYABLE", "Only failed jobs can be retried.", 409)
        if job["attempt_count"] >= job["max_attempts"]:
            raise AppError("PRINTER_JOB_MAX_ATTEMPTS_REACHED", "Printer job max attempts reached.", 409)
        printer = _printer(conn)
        if not printer or printer["status"] != "active":
            raise AppError("PRINTER_NOT_CONFIGURED", "Printer is not configured.", 409)
        job = _attempt(conn, job, printer)
        audit(conn, "printer.job.retry", user_id=user_id, entity_type="printer_job", entity_id=str(job["id"]), request_id=request_id)
    return {"job": _job_payload(job)}
