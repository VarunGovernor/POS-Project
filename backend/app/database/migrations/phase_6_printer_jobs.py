MIGRATION_ID = "PHASE_6_PRINTER_JOBS"
DESCRIPTION = "Create Phase 6 printer device and job tables."

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS printer_devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        printer_code TEXT NOT NULL UNIQUE,
        printer_name TEXT NOT NULL,
        printer_type TEXT NOT NULL CHECK (printer_type IN ('thermal', 'a4', 'dev', 'unknown')),
        connection_type TEXT NOT NULL CHECK (connection_type IN ('usb', 'network', 'system', 'dev', 'unknown')),
        connection_config_json TEXT NULL,
        status TEXT NOT NULL CHECK (status IN ('active', 'inactive', 'error', 'not_configured')),
        is_default INTEGER NOT NULL DEFAULT 0,
        last_seen_at TEXT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id),
        FOREIGN KEY (device_id) REFERENCES devices(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS printer_jobs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        job_number TEXT NOT NULL UNIQUE,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        printer_device_id INTEGER NULL,
        receipt_id INTEGER NULL,
        bill_id INTEGER NULL,
        job_type TEXT NOT NULL CHECK (job_type IN ('receipt_original', 'receipt_reprint', 'test_print')),
        status TEXT NOT NULL CHECK (status IN ('queued', 'printing', 'printed', 'failed', 'cancelled')),
        attempt_count INTEGER NOT NULL DEFAULT 0,
        max_attempts INTEGER NOT NULL DEFAULT 3,
        payload_json TEXT NOT NULL,
        failure_message TEXT NULL,
        printed_at TEXT NULL,
        last_attempt_at TEXT NULL,
        created_by_user_id INTEGER NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (printer_device_id) REFERENCES printer_devices(id),
        FOREIGN KEY (receipt_id) REFERENCES receipts(id),
        FOREIGN KEY (bill_id) REFERENCES bills(id),
        FOREIGN KEY (created_by_user_id) REFERENCES users(id)
    )
    """,
]
