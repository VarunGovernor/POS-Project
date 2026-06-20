from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.config import settings
from app.auth.security import hash_password
from app.database.migrations import phase_1_initial_schema, phase_2_auth_sessions, phase_3_patient_catalog, phase_4_draft_billing, phase_5_final_billing

MIGRATIONS = [phase_1_initial_schema, phase_2_auth_sessions, phase_3_patient_catalog, phase_4_draft_billing, phase_5_final_billing]
LATEST_MIGRATION_ID = phase_5_final_billing.MIGRATION_ID
MIGRATION_ID = LATEST_MIGRATION_ID

REQUIRED_TABLES = {
    "organizations",
    "branches",
    "devices",
    "settings",
    "migration_records",
    "app_runtime_state",
    "audit_logs",
    "users",
    "roles",
    "permissions",
    "role_permissions",
    "user_roles",
    "login_sessions",
    "cashier_sessions",
    "patients",
    "departments",
    "doctors",
    "services",
    "price_lists",
    "service_prices",
    "tax_rules",
    "master_sync_state",
    "bill_drafts",
    "bill_draft_items",
    "bills",
    "bill_items",
    "payments",
    "receipts",
    "sync_events",
    "idempotency_keys",
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
    for migration in MIGRATIONS:
        now = utc_now()
        try:
            for statement in migration.STATEMENTS:
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
                (migration.MIGRATION_ID, migration.DESCRIPTION, now, now, now),
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
                    (migration.MIGRATION_ID, migration.DESCRIPTION, now, str(exc), now),
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
            'DEV-INSTALLATION', 'active', 'active', ?, ?
        )
        """,
        (now, now),
    )
    conn.execute(
        "UPDATE devices SET activation_status = 'active', updated_at = ? WHERE id = 1",
        (now,),
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
    seed_phase_2_data(conn, now)
    seed_phase_3_data(conn, now)


def seed_phase_2_data(conn: sqlite3.Connection, now: str) -> None:
    if not _table_exists(conn, "users"):
        return

    permissions = [
        ("auth.login", "Login"),
        ("session.view", "View cashier session"),
        ("session.open", "Open cashier session"),
        ("session.close", "Close cashier session"),
        ("device.view", "View device"),
        ("settings.view", "View settings"),
        ("support.view", "View support"),
        ("audit.view", "View audit"),
        ("health.view", "View health"),
        ("patient.view", "View patients"),
        ("patient.create", "Create patients"),
        ("catalog.service.view", "View services"),
        ("catalog.department.view", "View departments"),
        ("catalog.doctor.view", "View doctors"),
        ("sync.master.view", "View master sync state"),
        ("billing.bill.view", "View bill drafts"),
        ("billing.bill.create", "Create bill drafts"),
        ("billing.bill.edit", "Edit bill drafts"),
        ("billing.bill.void_draft", "Void bill drafts"),
        ("billing.bill.finalize", "Finalize bills"),
        ("billing.bill.final.view", "View final bills"),
        ("billing.payment.cash.create", "Create cash payments"),
        ("billing.receipt.view", "View receipts"),
        ("billing.receipt.generate", "Generate receipts"),
        ("sync.event.view", "View sync events"),
    ]
    for code, name in permissions:
        conn.execute(
            """
            INSERT OR IGNORE INTO permissions (
                permission_code, permission_name, description, created_at, updated_at
            )
            VALUES (?, ?, NULL, ?, ?)
            """,
            (code, name, now, now),
        )

    roles = [
        (1, "cashier", "Cashier", "Can manage own cashier session"),
        (2, "admin", "Admin", "Development admin/support user"),
    ]
    for role_id, code, name, description in roles:
        conn.execute(
            """
            INSERT OR IGNORE INTO roles (
                id, organization_id, role_code, role_name, description, status, created_at, updated_at
            )
            VALUES (?, 1, ?, ?, ?, 'active', ?, ?)
            """,
            (role_id, code, name, description, now, now),
        )

    users = [
        (1, "cashier", "cashier123", "Cashier", 1),
        (2, "admin", "admin123", "Admin", 0),
    ]
    for user_id, username, password, display_name, offline_allowed in users:
        conn.execute(
            """
            INSERT OR IGNORE INTO users (
                id, organization_id, branch_id, username, password_hash, display_name,
                status, offline_login_allowed, permission_version, created_at, updated_at
            )
            VALUES (?, 1, 1, ?, ?, ?, 'active', ?, ?, ?, ?)
            """,
            (user_id, username, hash_password(password), display_name, offline_allowed, LATEST_MIGRATION_ID, now, now),
        )

    role_permissions = {
        1: [
            "auth.login",
            "session.view",
            "session.open",
            "session.close",
            "device.view",
            "patient.view",
            "patient.create",
            "catalog.service.view",
            "catalog.department.view",
            "catalog.doctor.view",
            "sync.master.view",
            "billing.bill.view",
            "billing.bill.create",
            "billing.bill.edit",
            "billing.bill.void_draft",
            "billing.bill.finalize",
            "billing.bill.final.view",
            "billing.payment.cash.create",
            "billing.receipt.view",
            "billing.receipt.generate",
            "sync.event.view",
        ],
        2: [code for code, _ in permissions],
    }
    for role_id, codes in role_permissions.items():
        for code in codes:
            conn.execute(
                """
                INSERT OR IGNORE INTO role_permissions (role_id, permission_id, created_at)
                SELECT ?, id, ? FROM permissions WHERE permission_code = ?
                """,
                (role_id, now, code),
            )

    conn.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id, created_at) VALUES (1, 1, ?)", (now,))
    conn.execute("INSERT OR IGNORE INTO user_roles (user_id, role_id, created_at) VALUES (2, 2, ?)", (now,))


def seed_phase_3_data(conn: sqlite3.Connection, now: str) -> None:
    if not _table_exists(conn, "services"):
        return

    departments = [
        (1, "GEN-MED", "General Medicine"),
        (2, "LAB", "Laboratory"),
        (3, "PHARM", "Pharmacy"),
    ]
    for department_id, code, name in departments:
        conn.execute(
            """
            INSERT OR IGNORE INTO departments (
                id, organization_id, branch_id, department_code, department_name, status, created_at, updated_at
            )
            VALUES (?, 1, 1, ?, ?, 'active', ?, ?)
            """,
            (department_id, code, name, now, now),
        )

    conn.execute(
        """
        INSERT OR IGNORE INTO doctors (
            id, organization_id, branch_id, department_id, doctor_code, full_name,
            specialization, status, created_at, updated_at
        )
        VALUES (1, 1, 1, 1, 'DR-GEN-1', 'Dr. Dev General', 'General Medicine', 'active', ?, ?)
        """,
        (now, now),
    )

    services = [
        (1, 1, "OP-CONSULT", "OP Consultation", "op"),
        (2, 2, "CBC", "CBC Test", "lab"),
        (3, 1, "GEN-SERVICE", "General Service", "general"),
    ]
    for service_id, department_id, code, name, service_type in services:
        conn.execute(
            """
            INSERT OR IGNORE INTO services (
                id, organization_id, branch_id, department_id, service_code, service_name,
                service_type, status, catalog_version, created_at, updated_at
            )
            VALUES (?, 1, 1, ?, ?, ?, ?, 'active', 'CAT-DEV-001', ?, ?)
            """,
            (service_id, department_id, code, name, service_type, now, now),
        )

    conn.execute(
        """
        INSERT OR IGNORE INTO price_lists (
            id, organization_id, branch_id, price_list_code, price_list_name, status,
            effective_from, effective_to, created_at, updated_at
        )
        VALUES (1, 1, 1, 'STANDARD', 'Standard Price List', 'active', NULL, NULL, ?, ?)
        """,
        (now, now),
    )

    prices = [(1, 500), (2, 300), (3, 100)]
    for service_id, amount in prices:
        conn.execute(
            """
            INSERT OR IGNORE INTO service_prices (
                organization_id, branch_id, service_id, price_list_id, price_amount,
                currency, price_version, status, created_at, updated_at
            )
            VALUES (1, 1, ?, 1, ?, 'INR', 'PRICE-DEV-001', 'active', ?, ?)
            """,
            (service_id, amount, now, now),
        )

    conn.execute(
        """
        INSERT OR IGNORE INTO tax_rules (
            id, organization_id, branch_id, tax_code, tax_name, tax_rate, status, created_at, updated_at
        )
        VALUES (1, 1, 1, 'GST-0', 'No Tax', 0, 'active', ?, ?)
        """,
        (now, now),
    )

    for master_type in ["departments", "doctors", "services", "prices", "tax_rules"]:
        conn.execute(
            """
            INSERT OR IGNORE INTO master_sync_state (
                organization_id, branch_id, master_type, version_code, last_successful_sync_at,
                status, created_at, updated_at
            )
            VALUES (1, 1, ?, 'DEV-001', NULL, 'local_seeded', ?, ?)
            """,
            (master_type, now, now),
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
            (now, settings.app_version, LATEST_MIGRATION_ID, startup_status, now, existing_id["id"]),
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
        (now, settings.app_version, LATEST_MIGRATION_ID, startup_status, now, now),
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
                "migration_status": "ok" if version == LATEST_MIGRATION_ID else "error",
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


def local_device_status() -> str:
    try:
        with connect() as conn:
            row = conn.execute("SELECT status FROM devices ORDER BY id LIMIT 1").fetchone()
            return row["status"] if row else "not_configured"
    except Exception:
        return "error"


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
