from __future__ import annotations

import json
from typing import Any

from app.auth.repository import audit
from app.core.errors import AppError
from app.database.connection import connect, utc_now

OPEN_STATUSES = ("open", "acknowledged")


def _marker_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "marker_code": row["marker_code"],
        "marker_type": row["marker_type"],
        "severity": row["severity"],
        "status": row["status"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "title": row["title"],
        "description": row["description"],
        "detected_at": row["detected_at"],
    }


def _code(conn) -> str:
    seq = conn.execute("SELECT COALESCE(MAX(id), 0) + 1 AS next_id FROM recovery_markers").fetchone()["next_id"]
    return f"REC-{utc_now()[:10].replace('-', '')}-{seq:06d}"


def _add_marker(conn, marker_type: str, severity: str, entity_type: str, entity_id: str, title: str, description: str, metadata: dict[str, Any] | None = None) -> None:
    exists = conn.execute(
        """
        SELECT id FROM recovery_markers
        WHERE marker_type = ? AND entity_type = ? AND entity_id = ? AND status IN ('open', 'acknowledged')
        """,
        (marker_type, entity_type, entity_id),
    ).fetchone()
    if exists:
        return
    now = utc_now()
    device = conn.execute("SELECT organization_id, branch_id, id AS device_id FROM devices ORDER BY id LIMIT 1").fetchone()
    conn.execute(
        """
        INSERT INTO recovery_markers (
            marker_code, marker_type, severity, status, entity_type, entity_id,
            organization_id, branch_id, device_id, title, description, detected_at,
            metadata_json, created_at, updated_at
        )
        VALUES (?, ?, ?, 'open', ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            _code(conn),
            marker_type,
            severity,
            entity_type,
            str(entity_id),
            device["organization_id"] if device else None,
            device["branch_id"] if device else None,
            device["device_id"] if device else None,
            title,
            description,
            now,
            json.dumps(metadata) if metadata else None,
            now,
            now,
        ),
    )


def scan_recovery() -> dict[str, Any]:
    with connect() as conn:
        for row in conn.execute("SELECT id FROM cashier_sessions WHERE status = 'open'").fetchall():
            _add_marker(conn, "ACTIVE_SESSION_FOUND", "warning", "cashier_session", row["id"], "Active cashier session found", "A cashier session is still open after startup.")
        for row in conn.execute("SELECT id FROM bill_drafts WHERE status = 'draft'").fetchall():
            _add_marker(conn, "OPEN_DRAFT_FOUND", "info", "bill_draft", row["id"], "Open draft found", "A draft bill is still open and can be continued.")
        for row in conn.execute("SELECT id FROM bills WHERE sync_status = 'pending'").fetchall():
            _add_marker(conn, "UNSYNCED_BILL_FOUND", "warning", "bill", row["id"], "Unsynced bill found", "A finalized bill is waiting in the local outbox.")
        for row in conn.execute("SELECT id FROM printer_jobs WHERE status IN ('queued', 'printing')").fetchall():
            _add_marker(conn, "PENDING_PRINT_JOB_FOUND", "warning", "printer_job", row["id"], "Pending print job found", "A printer job is queued or printing.")
        for row in conn.execute("SELECT id FROM printer_jobs WHERE status = 'failed'").fetchall():
            _add_marker(conn, "FAILED_PRINT_JOB_FOUND", "warning", "printer_job", row["id"], "Failed print job found", "A printer job failed and may be retried.")
    return recovery_status()


def recovery_status() -> dict[str, Any]:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT
                SUM(CASE WHEN status IN ('open', 'acknowledged') THEN 1 ELSE 0 END) AS open_count,
                SUM(CASE WHEN status IN ('open', 'acknowledged') AND severity = 'critical' THEN 1 ELSE 0 END) AS critical_count,
                SUM(CASE WHEN status IN ('open', 'acknowledged') AND severity = 'warning' THEN 1 ELSE 0 END) AS warning_count,
                SUM(CASE WHEN status IN ('open', 'acknowledged') AND severity = 'info' THEN 1 ELSE 0 END) AS info_count,
                MAX(detected_at) AS last_scan_at
            FROM recovery_markers
            """
        ).fetchone()
    critical = row["critical_count"] or 0
    warning = row["warning_count"] or 0
    return {
        "recovery_required": bool(critical or warning),
        "open_marker_count": row["open_count"] or 0,
        "critical_count": critical,
        "warning_count": warning,
        "info_count": row["info_count"] or 0,
        "last_scan_at": row["last_scan_at"],
    }


def recovery_required() -> bool:
    return recovery_status()["recovery_required"]


def list_markers(status: str | None, severity: str | None, marker_type: str | None, page: int, page_size: int) -> dict[str, Any]:
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if severity:
        clauses.append("severity = ?")
        params.append(severity)
    if marker_type:
        clauses.append("marker_type = ?")
        params.append(marker_type)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    offset = (page - 1) * page_size
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM recovery_markers {where}", params).fetchone()["c"]
        rows = conn.execute(f"SELECT * FROM recovery_markers {where} ORDER BY detected_at DESC LIMIT ? OFFSET ?", [*params, page_size, offset]).fetchall()
    return {"items": [_marker_payload(dict(row)) for row in rows], "page": page, "page_size": page_size, "total": total, "has_next": offset + len(rows) < total}


def resolve_marker(marker_id: int, action: str, notes: str | None, user_id: int, request_id: str | None) -> dict[str, Any]:
    if action not in {"acknowledged", "resolved", "ignored"}:
        raise AppError("RECOVERY_RESOLUTION_INVALID", "Invalid recovery resolution action.", 422)
    now = utc_now()
    with connect() as conn:
        row = conn.execute("SELECT * FROM recovery_markers WHERE id = ?", (marker_id,)).fetchone()
        if not row:
            raise AppError("RECOVERY_MARKER_NOT_FOUND", "Recovery marker not found.", 404)
        conn.execute(
            """
            UPDATE recovery_markers
            SET status = ?, resolved_at = ?, resolved_by_user_id = ?,
                resolution_action = ?, metadata_json = ?, updated_at = ?
            WHERE id = ?
            """,
            (action, now if action in {"resolved", "ignored"} else None, user_id, action, json.dumps({"notes": notes}) if notes else row["metadata_json"], now, marker_id),
        )
        updated = dict(conn.execute("SELECT * FROM recovery_markers WHERE id = ?", (marker_id,)).fetchone())
        audit(conn, "recovery.resolve", user_id=user_id, entity_type="recovery_marker", entity_id=str(marker_id), metadata={"action": action, "notes": notes}, request_id=request_id)
    return {"marker": _marker_payload(updated)}
