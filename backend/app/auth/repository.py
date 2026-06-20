from __future__ import annotations

import json
import sqlite3
from datetime import datetime, timedelta, timezone
from typing import Any
from uuid import uuid4

from app.auth.security import new_token, verify_password
from app.core.errors import AppError
from app.database.connection import connect, utc_now


SESSION_HOURS = 12


def parse_time(value: str) -> datetime:
    return datetime.fromisoformat(value)


def row_dict(row: sqlite3.Row | None) -> dict[str, Any] | None:
    return dict(row) if row else None


def audit(
    conn: sqlite3.Connection,
    action: str,
    severity: str = "info",
    user_id: int | None = None,
    entity_type: str | None = None,
    entity_id: str | None = None,
    metadata: dict[str, Any] | None = None,
    request_id: str | None = None,
) -> None:
    device = get_device(conn)
    conn.execute(
        """
        INSERT INTO audit_logs (
            audit_id, organization_id, branch_id, device_id, actor_user_id, action,
            entity_type, entity_id, severity, metadata_json, request_id, created_at
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            f"AUD-{uuid4()}",
            device["organization_id"] if device else None,
            device["branch_id"] if device else None,
            device["id"] if device else None,
            str(user_id) if user_id else None,
            action,
            entity_type,
            entity_id,
            severity,
            json.dumps(metadata) if metadata else None,
            request_id,
            utc_now(),
        ),
    )


def get_user_by_username(conn: sqlite3.Connection, username: str) -> dict[str, Any] | None:
    return row_dict(
        conn.execute(
            """
            SELECT * FROM users
            WHERE organization_id = 1 AND username = ? AND status = 'active'
            """,
            (username,),
        ).fetchone()
    )


def user_roles_permissions(conn: sqlite3.Connection, user_id: int) -> tuple[list[str], list[str]]:
    roles = [
        row["role_code"]
        for row in conn.execute(
            """
            SELECT r.role_code FROM roles r
            JOIN user_roles ur ON ur.role_id = r.id
            WHERE ur.user_id = ? AND r.status = 'active'
            ORDER BY r.role_code
            """,
            (user_id,),
        ).fetchall()
    ]
    permissions = [
        row["permission_code"]
        for row in conn.execute(
            """
            SELECT DISTINCT p.permission_code FROM permissions p
            JOIN role_permissions rp ON rp.permission_id = p.id
            JOIN user_roles ur ON ur.role_id = rp.role_id
            WHERE ur.user_id = ?
            ORDER BY p.permission_code
            """,
            (user_id,),
        ).fetchall()
    ]
    return roles, permissions


def public_user(conn: sqlite3.Connection, user: dict[str, Any]) -> dict[str, Any]:
    roles, permissions = user_roles_permissions(conn, user["id"])
    return {
        "id": str(user["id"]),
        "username": user["username"],
        "display_name": user["display_name"],
        "roles": roles,
        "permissions": permissions,
    }


def login(username: str, password: str, login_mode: str, request_id: str | None) -> dict[str, Any]:
    with connect() as conn:
        user = get_user_by_username(conn, username)
        if not user or not verify_password(password, user["password_hash"]):
            raise AppError("AUTH_INVALID_CREDENTIALS", "Invalid username or password.", 401)
        if login_mode == "offline" and not bool(user["offline_login_allowed"]):
            raise AppError("AUTH_OFFLINE_LOGIN_NOT_ALLOWED", "Offline login not allowed.", 403)

        now = datetime.now(timezone.utc)
        expires_at = now + timedelta(hours=SESSION_HOURS)
        token = new_token()
        device = get_device(conn)
        conn.execute(
            """
            INSERT INTO login_sessions (
                user_id, device_id, session_token, status, login_mode, started_at,
                expires_at, created_at, updated_at
            )
            VALUES (?, ?, ?, 'active', ?, ?, ?, ?, ?)
            """,
            (
                user["id"],
                device["id"] if device else None,
                token,
                login_mode,
                now.isoformat(),
                expires_at.isoformat(),
                now.isoformat(),
                now.isoformat(),
            ),
        )
        conn.execute(
            "UPDATE users SET last_successful_login_at = ?, updated_at = ? WHERE id = ?",
            (now.isoformat(), now.isoformat(), user["id"]),
        )
        audit(conn, f"auth.{login_mode}_login", user_id=user["id"], request_id=request_id)
        return {
            "session_token": token,
            "user": public_user(conn, user),
            "offline_login": login_mode == "offline",
            "expires_at": expires_at.isoformat(),
        }


def load_context(token: str) -> dict[str, Any] | None:
    with connect() as conn:
        row = conn.execute(
            """
            SELECT s.*, u.username, u.display_name, u.status AS user_status
            FROM login_sessions s
            JOIN users u ON u.id = s.user_id
            WHERE s.session_token = ? AND s.status = 'active'
            """,
            (token,),
        ).fetchone()
        if not row or row["user_status"] != "active" or parse_time(row["expires_at"]) <= datetime.now(timezone.utc):
            return None
        user = {"id": row["user_id"], "username": row["username"], "display_name": row["display_name"]}
        roles, permissions = user_roles_permissions(conn, row["user_id"])
        return {
            "session": dict(row),
            "user": {**user, "roles": roles, "permissions": permissions},
            "device": get_device(conn),
        }


def logout(token: str, request_id: str | None) -> None:
    with connect() as conn:
        session = conn.execute("SELECT * FROM login_sessions WHERE session_token = ?", (token,)).fetchone()
        if not session or session["status"] != "active":
            raise AppError("AUTH_SESSION_REQUIRED", "Active auth session required.", 401)
        now = utc_now()
        conn.execute(
            "UPDATE login_sessions SET status = 'ended', ended_at = ?, updated_at = ? WHERE id = ?",
            (now, now, session["id"]),
        )
        audit(conn, "auth.logout", user_id=session["user_id"], request_id=request_id)


def get_device(conn: sqlite3.Connection) -> dict[str, Any] | None:
    row = conn.execute("SELECT * FROM devices ORDER BY id LIMIT 1").fetchone()
    return row_dict(row)


def current_cashier_session(device_id: int) -> dict[str, Any] | None:
    with connect() as conn:
        return row_dict(
            conn.execute(
                """
                SELECT * FROM cashier_sessions
                WHERE device_id = ? AND status = 'open'
                ORDER BY opened_at DESC LIMIT 1
                """,
                (device_id,),
            ).fetchone()
        )


def session_payload(session: dict[str, Any] | None) -> dict[str, Any] | None:
    if not session:
        return None
    return {**session, "id": str(session["id"])}


def open_cashier_session(
    user_id: int,
    device: dict[str, Any],
    counter_name: str,
    opening_cash_amount: float,
    notes: str | None,
    request_id: str | None,
) -> dict[str, Any]:
    with connect() as conn:
        existing = conn.execute(
            "SELECT id FROM cashier_sessions WHERE device_id = ? AND status = 'open'",
            (device["id"],),
        ).fetchone()
        if existing:
            raise AppError("CASHIER_SESSION_ALREADY_OPEN", "Cashier session already open.", 409)
        now = utc_now()
        session_number = f"CS-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}-{device['id']}-{uuid4().hex[:6]}"
        conn.execute(
            """
            INSERT INTO cashier_sessions (
                session_number, organization_id, branch_id, device_id, cashier_user_id,
                counter_name, status, opening_cash_amount, opened_at, notes, created_at, updated_at
            )
            VALUES (?, ?, ?, ?, ?, ?, 'open', ?, ?, ?, ?, ?)
            """,
            (
                session_number,
                device["organization_id"],
                device["branch_id"],
                device["id"],
                user_id,
                counter_name,
                opening_cash_amount,
                now,
                notes,
                now,
                now,
            ),
        )
        session = row_dict(conn.execute("SELECT * FROM cashier_sessions WHERE session_number = ?", (session_number,)).fetchone())
        audit(conn, "session.open", user_id=user_id, entity_type="cashier_session", entity_id=str(session["id"]), request_id=request_id)
        return session_payload(session)


def close_cashier_session(user_id: int, session_id: int, closing_cash_amount: float, notes: str | None, request_id: str | None) -> dict[str, Any]:
    with connect() as conn:
        session = row_dict(conn.execute("SELECT * FROM cashier_sessions WHERE id = ?", (session_id,)).fetchone())
        if not session:
            raise AppError("CASHIER_SESSION_NOT_FOUND", "Cashier session not found.", 404)
        if session["status"] != "open":
            raise AppError("CASHIER_SESSION_NOT_OPEN", "Cashier session is not open.", 409)
        paid_cash = conn.execute(
            """
            SELECT COALESCE(SUM(amount_paise), 0) AS total
            FROM payments
            WHERE cashier_session_id = ? AND status = 'paid' AND payment_method = 'cash'
            """,
            (session_id,),
        ).fetchone()["total"] / 100
        expected = float(session["opening_cash_amount"]) + paid_cash
        difference = float(closing_cash_amount) - expected
        now = utc_now()
        conn.execute(
            """
            UPDATE cashier_sessions
            SET status = 'closed', closing_cash_amount = ?, expected_cash_amount = ?,
                cash_difference_amount = ?, closed_at = ?, notes = ?, updated_at = ?
            WHERE id = ?
            """,
            (closing_cash_amount, expected, difference, now, notes, now, session_id),
        )
        updated = row_dict(conn.execute("SELECT * FROM cashier_sessions WHERE id = ?", (session_id,)).fetchone())
        audit(conn, "session.close", user_id=user_id, entity_type="cashier_session", entity_id=str(session_id), request_id=request_id)
        return session_payload(updated)
