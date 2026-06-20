from __future__ import annotations

import json
from typing import Any

from app.auth.repository import audit, row_dict
from app.core.errors import AppError
from app.database.connection import connect, utc_now
from app.sync.adapter import adapter_name, send_event

RETRYABLE = {"pending", "failed_retryable"}


def _event_payload(row: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": str(row["id"]),
        "event_type": row["event_type"],
        "entity_type": row["entity_type"],
        "entity_id": row["entity_id"],
        "status": row["status"],
        "attempt_count": row["attempt_count"],
        "last_attempt_at": row["last_attempt_at"],
        "next_attempt_at": row["next_attempt_at"],
        "created_at": row["created_at"],
    }


def sync_status() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute("SELECT status, COUNT(*) AS c FROM sync_events GROUP BY status").fetchall()
        counts = {row["status"]: row["c"] for row in rows}
        last_attempt = conn.execute("SELECT MAX(started_at) AS at FROM sync_attempts").fetchone()["at"]
        last_success = conn.execute("SELECT MAX(completed_at) AS at FROM sync_attempts WHERE status = 'success'").fetchone()["at"]
    pending = counts.get("pending", 0) + counts.get("failed_retryable", 0)
    conflicts = counts.get("conflict", 0)
    failed_permanent = counts.get("failed_permanent", 0)
    status = "error" if failed_permanent else "pending" if pending or conflicts else "ok"
    return {
        "status": status,
        "pending_count": counts.get("pending", 0),
        "syncing_count": counts.get("syncing", 0),
        "synced_count": counts.get("synced", 0),
        "failed_retryable_count": counts.get("failed_retryable", 0),
        "failed_permanent_count": failed_permanent,
        "conflict_count": conflicts,
        "last_successful_sync_at": last_success,
        "last_attempt_at": last_attempt,
        "adapter": adapter_name(),
    }


def list_events(status: str | None, event_type: str | None, entity_type: str | None, page: int, page_size: int) -> dict[str, Any]:
    page = max(page, 1)
    page_size = min(max(page_size, 1), 100)
    clauses: list[str] = []
    params: list[Any] = []
    if status:
        clauses.append("status = ?")
        params.append(status)
    if event_type:
        clauses.append("event_type = ?")
        params.append(event_type)
    if entity_type:
        clauses.append("entity_type = ?")
        params.append(entity_type)
    where = f"WHERE {' AND '.join(clauses)}" if clauses else ""
    offset = (page - 1) * page_size
    with connect() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM sync_events {where}", params).fetchone()["c"]
        rows = conn.execute(
            f"SELECT * FROM sync_events {where} ORDER BY created_at DESC, id DESC LIMIT ? OFFSET ?",
            [*params, page_size, offset],
        ).fetchall()
    return {"items": [_event_payload(dict(row)) for row in rows], "page": page, "page_size": page_size, "total": total, "has_next": offset + len(rows) < total}


def event_detail(event_id: int) -> dict[str, Any]:
    with connect() as conn:
        event = row_dict(conn.execute("SELECT * FROM sync_events WHERE id = ?", (event_id,)).fetchone())
        if not event:
            raise AppError("SYNC_EVENT_NOT_FOUND", "Sync event not found.", 404)
        attempts = [dict(row) for row in conn.execute("SELECT * FROM sync_attempts WHERE sync_event_id = ? ORDER BY id", (event_id,)).fetchall()]
    return {
        "event": {
            **_event_payload(event),
            "payload": json.loads(event["payload_json"]),
            "attempts": [
                {
                    "id": str(row["id"]),
                    "attempt_number": row["attempt_number"],
                    "status": row["status"],
                    "failure_message": row["failure_message"],
                    "started_at": row["started_at"],
                    "completed_at": row["completed_at"],
                }
                for row in attempts
            ],
        }
    }


def retry_one(event_id: int, user_id: int | None = None, request_id: str | None = None) -> dict[str, Any]:
    with connect() as conn:
        event = row_dict(conn.execute("SELECT * FROM sync_events WHERE id = ?", (event_id,)).fetchone())
        if not event:
            raise AppError("SYNC_EVENT_NOT_FOUND", "Sync event not found.", 404)
        if event["status"] not in RETRYABLE:
            raise AppError("SYNC_EVENT_NOT_RETRYABLE", "Sync event is not retryable.", 409)
        event = _attempt(conn, event, user_id, request_id)
    return {"event": _event_payload(event)}


def retry_all(user_id: int | None = None, request_id: str | None = None) -> dict[str, Any]:
    attempted = synced = failed = conflicts = 0
    with connect() as conn:
        rows = [dict(row) for row in conn.execute("SELECT * FROM sync_events WHERE status IN ('pending', 'failed_retryable') ORDER BY created_at, id").fetchall()]
        for event in rows:
            attempted += 1
            updated = _attempt(conn, event, user_id, request_id)
            synced += updated["status"] == "synced"
            failed += updated["status"] == "failed_retryable"
            conflicts += updated["status"] == "conflict"
    return {"attempted": attempted, "synced": synced, "failed": failed, "conflicts": conflicts}


def _attempt(conn, event: dict[str, Any], user_id: int | None, request_id: str | None) -> dict[str, Any]:
    now = utc_now()
    conn.execute("UPDATE sync_events SET status = 'syncing', last_attempt_at = ?, updated_at = ? WHERE id = ?", (now, now, event["id"]))
    attempt_number = int(event["attempt_count"]) + 1
    try:
        response = send_event(event)
        completed = utc_now()
        conn.execute(
            """
            INSERT INTO sync_attempts (
                sync_event_id, attempt_number, status, request_payload_json,
                response_payload_json, started_at, completed_at, created_at
            )
            VALUES (?, ?, 'success', ?, ?, ?, ?, ?)
            """,
            (event["id"], attempt_number, event["payload_json"], json.dumps(response), now, completed, now),
        )
        conn.execute(
            "UPDATE sync_events SET status = 'synced', attempt_count = ?, last_attempt_at = ?, next_attempt_at = NULL, updated_at = ? WHERE id = ?",
            (attempt_number, completed, completed, event["id"]),
        )
        audit(conn, "sync.event.synced", user_id=user_id, entity_type="sync_event", entity_id=str(event["id"]), request_id=request_id)
    except AppError as exc:
        completed = utc_now()
        conn.execute(
            """
            INSERT INTO sync_attempts (
                sync_event_id, attempt_number, status, request_payload_json,
                failure_message, started_at, completed_at, created_at
            )
            VALUES (?, ?, 'failed', ?, ?, ?, ?, ?)
            """,
            (event["id"], attempt_number, event["payload_json"], exc.message, now, completed, now),
        )
        conn.execute(
            "UPDATE sync_events SET status = 'failed_retryable', attempt_count = ?, last_attempt_at = ?, updated_at = ? WHERE id = ?",
            (attempt_number, completed, completed, event["id"]),
        )
    return dict(conn.execute("SELECT * FROM sync_events WHERE id = ?", (event["id"],)).fetchone())


def list_conflicts() -> dict[str, Any]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM sync_conflicts ORDER BY created_at DESC, id DESC").fetchall()
    return {
        "items": [
            {
                "id": str(row["id"]),
                "sync_event_id": str(row["sync_event_id"]),
                "entity_type": row["entity_type"],
                "entity_id": row["entity_id"],
                "conflict_type": row["conflict_type"],
                "resolution_status": row["resolution_status"],
                "created_at": row["created_at"],
            }
            for row in rows
        ]
    }
