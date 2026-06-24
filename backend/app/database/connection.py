from __future__ import annotations

import sqlite3
from datetime import datetime, timezone
from pathlib import Path
from threading import Lock
from typing import Any

from app.config import settings
from app.auth.security import hash_password
from app.database.migrations import phase_1_initial_schema, phase_2_auth_sessions, phase_3_patient_catalog, phase_4_draft_billing, phase_5_final_billing, phase_6_printer_jobs, phase_7_recovery_foundation, phase_8_sync_foundation, phase_9_reports_support, phase_13_hospital_registration

MIGRATIONS = [phase_1_initial_schema, phase_2_auth_sessions, phase_3_patient_catalog, phase_4_draft_billing, phase_5_final_billing, phase_6_printer_jobs, phase_7_recovery_foundation, phase_8_sync_foundation, phase_9_reports_support, phase_13_hospital_registration]
LATEST_MIGRATION_ID = phase_13_hospital_registration.MIGRATION_ID
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
    "sync_attempts",
    "sync_conflicts",
    "idempotency_keys",
    "printer_devices",
    "printer_jobs",
    "recovery_markers",
    "support_bundles",
    "hospital_registrations",
    "hospital_registration_events",
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
        if _table_exists(conn, "migration_records"):
            applied = conn.execute(
                "SELECT 1 FROM migration_records WHERE migration_id = ? AND status = 'applied'",
                (migration.MIGRATION_ID,),
            ).fetchone()
            if applied:
                continue
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
    conn.execute(
        """
        INSERT OR IGNORE INTO settings (
            id, organization_id, branch_id, device_id, setting_key, setting_value,
            setting_scope, is_readonly, created_at, updated_at
        )
        VALUES (2, 1, 1, 1, 'receipt.header', 'CounterOS Hospital', 'device', 0, ?, ?)
        """,
        (now, now),
    )
    seed_phase_2_data(conn, now)
    seed_phase_3_data(conn, now)
    seed_phase_6_data(conn, now)


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
        ("sync.status.view", "View sync status"),
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
        ("sync.event.retry", "Retry sync events"),
        ("sync.run", "Run sync"),
        ("sync.conflict.view", "View sync conflicts"),
        ("report.view", "View reports"),
        ("report.today.view", "View today collection report"),
        ("report.session.view", "View cashier session report"),
        ("report.department.view", "View department collection report"),
        ("settings.update", "Update settings"),
        ("support.bundle.create", "Create support bundle"),
        ("printer.view", "View printer"),
        ("printer.test", "Test printer"),
        ("printer.receipt.print", "Print receipts"),
        ("printer.receipt.reprint", "Reprint receipts"),
        ("printer.job.retry", "Retry printer jobs"),
        ("recovery.view", "View recovery"),
        ("recovery.resolve", "Resolve recovery markers"),
        ("recovery.scan", "Run recovery scan"),
        ("registration.view", "View registrations"),
        ("registration.create", "Create registrations"),
        ("registration.update", "Update registrations"),
        ("registration.send_to_billing", "Send registrations to billing"),
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
            "sync.status.view",
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
            "sync.event.retry",
            "report.view",
            "report.today.view",
            "report.session.view",
            "settings.view",
            "support.view",
            "printer.view",
            "printer.receipt.print",
            "printer.receipt.reprint",
            "printer.job.retry",
            "recovery.view",
            "recovery.scan",
            "registration.view",
            "registration.create",
            "registration.update",
            "registration.send_to_billing",
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


def seed_phase_6_data(conn: sqlite3.Connection, now: str) -> None:
    if not _table_exists(conn, "printer_devices"):
        return
    conn.execute(
        """
        INSERT OR IGNORE INTO printer_devices (
            id, organization_id, branch_id, device_id, printer_code, printer_name,
            printer_type, connection_type, connection_config_json, status, is_default,
            last_seen_at, created_at, updated_at
        )
        VALUES (
            1, 1, 1, 1, 'DEV-PRINTER', 'Development Printer',
            'dev', 'dev', '{"mode":"development"}', 'active', 1,
            ?, ?, ?
        )
        """,
        (now, now, now),
    )


def seed_phase_3_data(conn: sqlite3.Connection, now: str) -> None:
    if not _table_exists(conn, "services"):
        return

    departments = [
        (1, "GEN-MED", "General Medicine"),
        (2, "LAB", "Laboratory"),
        (3, "PHARM", "Pharmacy"),
        (4, "PEDS", "Pediatrics"),
        (5, "ORTHO", "Orthopedics"),
        (6, "ER", "Emergency"),
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
    doctors = [
        (2, 4, "DR-PED-1", "Dr. Mehta", "Pediatrics"),
        (3, 5, "DR-ORTH-1", "Dr. Reddy", "Orthopedics"),
        (4, 1, "DR-GEN-2", "Dr. Sharma", "General Medicine"),
        (5, 6, "DR-ER-1", "Dr. Iyer", "Emergency Medicine"),
    ]
    for doctor_id, department_id, code, name, specialization in doctors:
        conn.execute(
            """
            INSERT OR IGNORE INTO doctors (
                id, organization_id, branch_id, department_id, doctor_code, full_name,
                specialization, status, created_at, updated_at
            )
            VALUES (?, 1, 1, ?, ?, ?, ?, 'active', ?, ?)
            """,
            (doctor_id, department_id, code, name, specialization, now, now),
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

    seed_phase_13_data(conn, now)


def seed_phase_13_data(conn: sqlite3.Connection, now: str) -> None:
    if not _table_exists(conn, "hospital_registrations"):
        return
    rows = [
        ("OP-1001", "op", "Ravi Kumar", "9876543210", 42, "male", 1, 4, "new", "T-1001", None, None, None, None, None, None, None, None, "registered", "ready_for_billing", "Fever and cough"),
        ("OP-1002", "op", "Ananya Rao", "9988776655", 8, "female", 4, 2, "new", "T-1002", None, None, None, None, None, None, None, None, "checked_in", "ready_for_billing", "Pediatric consult"),
        ("OP-1003", "op", "Suresh Naidu", "9123456780", 51, "male", 5, 3, "new", "T-1003", None, None, None, None, None, None, None, None, "registered", "pending", "Knee pain"),
        ("OP-1004", "op", "Priya Menon", "9000011111", 34, "female", 1, 1, "new", "T-1004", None, None, None, None, None, None, None, None, "registered", "pending", "General consultation"),
        ("OP-1005", "op", "Vikram Singh", "9000022222", 46, "male", 1, 4, "new", "T-1005", None, None, None, None, None, None, None, None, "checked_in", "ready_for_billing", "Diabetes follow-up"),
        ("IP-1006", "ip", "Mohan Reddy", "9000033333", 63, "male", 1, 1, None, None, "ADM-1006", "General Ward", "Bed G12", "Sita Reddy", 500000, None, None, None, "admitted", "pending", "Observation"),
        ("IP-1007", "ip", "Lakshmi Devi", "9000044444", 58, "female", 1, 4, None, None, "ADM-1007", "Semi Private", "Room SP04", "Ramesh Devi", 1000000, None, None, None, "admitted", "pending", "Inpatient admission"),
        ("IP-1008", "ip", "Fatima Khan", "9000055555", 67, "female", 6, 5, None, None, "ADM-1008", "ICU", "Bed ICU-03", "Aamir Khan", 2500000, None, None, None, "admitted", "pending", "ICU admission"),
        ("IP-1009", "ip", "Arjun Patel", "9000066666", 39, "male", 5, 3, None, None, "ADM-1009", "Ortho Ward", "Bed O07", "Neha Patel", 800000, None, None, None, "admitted", "pending", "Fracture care"),
        ("ER-1010", "emergency", "Unknown Patient", None, None, None, 6, 5, None, None, None, None, None, None, None, "high", None, None, "active", "ready_for_billing", "Brought by ambulance"),
        ("ER-1011", "emergency", "Kiran P", "9000077777", 29, "male", 6, 5, None, None, None, None, None, None, None, "medium", None, None, "active", "ready_for_billing", "Minor trauma"),
        ("ER-1012", "emergency", "Meena L", "9000088888", 45, "female", 6, 5, None, None, None, None, None, None, None, "high", None, None, "active", "pending", "Chest pain"),
        ("FU-1013", "follow_up", "Deepa Nair", "9000099999", 37, "female", 1, 1, "follow_up", "T-1013", None, None, None, None, None, None, None, None, "registered", "pending", "Follow-up visit"),
        ("FU-1014", "follow_up", "Rahul Bose", "9011111111", 44, "male", 5, 3, "follow_up", "T-1014", None, None, None, None, None, None, None, None, "checked_in", "ready_for_billing", "Post-op review"),
        ("FU-1015", "follow_up", "Nisha Verma", "9022222222", 31, "female", 4, 2, "follow_up", "T-1015", None, None, None, None, None, None, None, None, "registered", "pending", "Review"),
        ("LAB-1016", "lab", "Amit Shah", "9033333333", 55, "male", 2, None, None, None, None, None, None, None, None, None, "sample_pending", None, "registered", "pending", "CBC"),
        ("LAB-1017", "lab", "Geeta Joshi", "9044444444", 49, "female", 2, None, None, None, None, None, None, None, None, None, "sample_collected", None, "active", "ready_for_billing", "Lipid profile"),
        ("LAB-1018", "lab", "Naveen Rao", "9055555555", 27, "male", 2, None, None, None, None, None, None, None, None, None, "sample_pending", None, "registered", "pending", "Blood sugar"),
        ("PH-1019", "pharmacy_walkin", "Sunita Das", "9066666666", 52, "female", 3, None, None, None, None, None, None, None, None, None, None, "RX-8841", "registered", "pending", "Prescription refill"),
        ("PH-1020", "pharmacy_walkin", "Harish Gowda", "9077777777", 61, "male", 3, None, None, None, None, None, None, None, None, None, None, "RX-8842", "registered", "ready_for_billing", "Walk-in medicine"),
        ("PH-1021", "pharmacy_walkin", "Pooja Kulkarni", "9088888888", 26, "female", 3, None, None, None, None, None, None, None, None, None, None, "RX-8843", "registered", "pending", "Prescription purchase"),
    ]
    for row in rows:
        conn.execute(
            """
            INSERT OR IGNORE INTO hospital_registrations (
                registration_number, organization_id, branch_id, device_id, registration_type,
                patient_name, mobile_number, age_years, gender, department_id, doctor_id,
                visit_type, token_number, admission_number, ward, room_or_bed, attender_name,
                deposit_amount_paise, priority, sample_status, prescription_reference, status,
                billing_status, notes, created_by_user_id, created_at, updated_at
            )
            VALUES (?, 1, 1, 1, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1, ?, ?)
            """,
            (*row, now, now),
        )
        registration_id = conn.execute("SELECT id FROM hospital_registrations WHERE registration_number = ?", (row[0],)).fetchone()["id"]
        conn.execute(
            """
            INSERT OR IGNORE INTO hospital_registration_events (id, registration_id, event_type, notes, created_by_user_id, created_at)
            VALUES (?, ?, 'seeded', 'Demo seed', 1, ?)
            """,
            (registration_id, registration_id, now),
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
