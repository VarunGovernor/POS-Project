from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.config import settings
from app.database.migrations.phase_1_initial_schema import (
    DESCRIPTION,
    MIGRATION_ID,
    STATEMENTS,
)

REQUIRED_TABLES = {
    "organizations",
    "branches",
    "devices",
    "settings",
    "migration_records",
    "app_runtime_state",
    "audit_logs",
}

_init_lock = Lock()
_last_init_error: str | None = None


def utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def database_path() -> Path:
    return Path(settings.database_path)


def connect() -> sqlite3.Connection:
    path = database_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    configure_connection(conn)
    return conn


def configure_connection(conn: sqlite3.Connection) -> None:
    conn.execute("PRAGMA journal_mode = WAL")
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA synchronous = FULL")
    conn.execute("PRAGMA busy_timeout = 5000")


def initialize_database() -> None:
    global _last_init_error
    with _init_lock:
        try:
            with connect() as conn:
                apply_migrations(conn)
                seed_development_data(conn)
                write_startup_state(conn, "ready")
            _last_init_error = None
        except Exception as exc:
            _last_init_error = str(exc)
            raise


def apply_migrations(conn: sqlite3.Connection) -> None:
    now = utc_now()
    try:
        for statement in STATEMENTS:
            conn.execute(statement)
        conn.execute(
            """
            INSERT INTO migration_records (
                migration_id, description, status, started_at, completed_at, created_at
            )
            VALUES (?, ?, 'applied', ?, ?, ?)
            ON CONFLICT(migration_id) DO UPDATE SET
                status = 'applied',
                completed_at = excluded.completed_at,
                failure_message = NULL
            """,
            (MIGRATION_ID, DESCRIPTION, now, now, now),
        )
    except Exception as exc:
        if _table_exists(conn, "migration_records"):
            conn.execute(
                """
                INSERT OR REPLACE INTO migration_records (
                    migration_id, description, status, started_at, completed_at,
                    failure_message, created_at
                )
                VALUES (?, ?, 'failed', ?, NULL, ?, ?)
                """,
                (MIGRATION_ID, DESCRIPTION, now, str(exc), now),
            )
        raise


def seed_development_data(conn: sqlite3.Connection) -> None:
    now = utc_now()
    conn.execute(
        """
        INSERT OR IGNORE INTO organizations (
            id, organization_code, organization_name, status, created_at, updated_at
        )
        VALUES (1, 'DEV_ORG', 'Development Organization', 'active', ?, ?)
        """,
        (now, now),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO branches (
            id, organization_id, branch_code, branch_name, status, created_at, updated_at
        )
        VALUES (1, 1, 'DEV_BRANCH', 'Development Branch', 'active', ?, ?)
        """,
        (now, now),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO devices (
            id, organization_id, branch_id, device_code, device_name, counter_name,
            installation_id, status, activation_status, created_at, updated_at
        )
        VALUES (
            1, 1, 1, 'DEV_DEVICE', 'Development Device', 'Development Counter',
            'DEV-INSTALLATION', 'active', 'not_activated', ?, ?
        )
        """,
        (now, now),
    )
    conn.execute(
        """
        INSERT OR IGNORE INTO settings (
            id, organization_id, branch_id, device_id, setting_key, setting_value,
            setting_scope, is_readonly, created_at, updated_at
        )
        VALUES (1, 1, 1, 1, 'environment', 'development', 'device', 1, ?, ?)
        """,
        (now, now),
    )


def write_startup_state(conn: sqlite3.Connection, startup_status: str) -> None:
    now = utc_now()
    existing_id = conn.execute("SELECT id FROM app_runtime_state ORDER BY id LIMIT 1").fetchone()
    if existing_id:
        conn.execute(
            """
            UPDATE app_runtime_state
            SET last_started_at = ?, current_app_version = ?,
                current_database_version = ?, startup_status = ?, updated_at = ?
            WHERE id = ?
            """,
            (now, settings.app_version, MIGRATION_ID, startup_status, now, existing_id["id"]),
        )
        return
    conn.execute(
        """
        INSERT INTO app_runtime_state (
            device_id, last_started_at, current_app_version, current_database_version,
            startup_status, shutdown_status, created_at, updated_at
        )
        VALUES (1, ?, ?, ?, ?, 'unknown', ?, ?)
        """,
        (now, settings.app_version, MIGRATION_ID, startup_status, now, now),
    )


def database_health() -> dict[str, Any]:
    try:
        with connect() as conn:
            journal_mode = conn.execute("PRAGMA journal_mode").fetchone()[0]
            foreign_keys = bool(conn.execute("PRAGMA foreign_keys").fetchone()[0])
            version = latest_migration(conn)
            tables_present = required_tables_present(conn)
            ok = journal_mode.lower() == "wal" and foreign_keys and bool(version) and tables_present
            return {
                "status": "ok" if ok else "error",
                "database_engine": "sqlite",
                "journal_mode": journal_mode.lower(),
                "foreign_keys": foreign_keys,
                "database_version": version or "unknown",
                "migration_status": "ok" if version == MIGRATION_ID else "error",
                "required_tables_present": tables_present,
            }
    except Exception as exc:
        return {
            "status": "error",
            "database_engine": "sqlite",
            "journal_mode": "unknown",
            "foreign_keys": False,
            "database_version": "unknown",
            "migration_status": "error",
            "required_tables_present": False,
            "error": _last_init_error or str(exc),
        }


def latest_migration(conn: sqlite3.Connection) -> str | None:
    if not _table_exists(conn, "migration_records"):
        return None
    row = conn.execute(
        """
        SELECT migration_id FROM migration_records
        WHERE status = 'applied'
        ORDER BY completed_at DESC, id DESC
        LIMIT 1
        """
    ).fetchone()
    return row["migration_id"] if row else None


def required_tables_present(conn: sqlite3.Connection) -> bool:
    rows = conn.execute(
        "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
    ).fetchall()
    names = {row["name"] for row in rows}
    return REQUIRED_TABLES.issubset(names)


def _table_exists(conn: sqlite3.Connection, table: str) -> bool:
    return (
        conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ?",
            (table,),
        ).fetchone()
        is not None
    )
