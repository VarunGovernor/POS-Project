MIGRATION_ID = "PHASE_5_FINAL_BILLING"
DESCRIPTION = "Create Phase 5 final billing, receipt, outbox, and idempotency tables."

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS bills (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_number TEXT NOT NULL UNIQUE,
        draft_id INTEGER NOT NULL UNIQUE,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        cashier_session_id INTEGER NOT NULL,
        cashier_user_id INTEGER NOT NULL,
        patient_id INTEGER NOT NULL,
        bill_type TEXT NOT NULL,
        department_id INTEGER NULL,
        doctor_id INTEGER NULL,
        status TEXT NOT NULL CHECK (status IN ('finalized', 'voided')),
        currency TEXT NOT NULL,
        subtotal_amount_paise INTEGER NOT NULL,
        discount_amount_paise INTEGER NOT NULL,
        tax_amount_paise INTEGER NOT NULL,
        total_amount_paise INTEGER NOT NULL,
        finalized_at TEXT NOT NULL,
        idempotency_key TEXT NOT NULL,
        sync_status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (draft_id) REFERENCES bill_drafts(id),
        FOREIGN KEY (patient_id) REFERENCES patients(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bill_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bill_id INTEGER NOT NULL,
        draft_item_id INTEGER NOT NULL,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        service_id INTEGER NOT NULL,
        service_code_at_time TEXT NOT NULL,
        service_name_at_time TEXT NOT NULL,
        department_id_at_time INTEGER NULL,
        department_name_at_time TEXT NULL,
        doctor_id INTEGER NULL,
        quantity REAL NOT NULL,
        unit_price_paise INTEGER NOT NULL,
        gross_amount_paise INTEGER NOT NULL,
        discount_amount_paise INTEGER NOT NULL,
        tax_amount_paise INTEGER NOT NULL,
        final_line_total_paise INTEGER NOT NULL,
        catalog_version TEXT NOT NULL,
        price_version TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (bill_id) REFERENCES bills(id),
        FOREIGN KEY (draft_item_id) REFERENCES bill_draft_items(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS payments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        payment_number TEXT NOT NULL UNIQUE,
        bill_id INTEGER NOT NULL,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        cashier_session_id INTEGER NOT NULL,
        cashier_user_id INTEGER NOT NULL,
        payment_method TEXT NOT NULL CHECK (payment_method IN ('cash')),
        status TEXT NOT NULL CHECK (status IN ('paid')),
        currency TEXT NOT NULL,
        amount_paise INTEGER NOT NULL,
        received_amount_paise INTEGER NULL,
        change_amount_paise INTEGER NULL,
        idempotency_key TEXT NOT NULL,
        paid_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (bill_id) REFERENCES bills(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS receipts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        receipt_number TEXT NOT NULL UNIQUE,
        bill_id INTEGER NOT NULL,
        payment_id INTEGER NOT NULL,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        cashier_session_id INTEGER NOT NULL,
        cashier_user_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('generated')),
        receipt_type TEXT NOT NULL CHECK (receipt_type IN ('original')),
        receipt_payload_json TEXT NOT NULL,
        generated_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (bill_id) REFERENCES bills(id),
        FOREIGN KEY (payment_id) REFERENCES payments(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sync_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('pending')),
        attempt_count INTEGER NOT NULL DEFAULT 0,
        last_attempt_at TEXT NULL,
        next_attempt_at TEXT NULL,
        idempotency_key TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS idempotency_keys (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        idempotency_key TEXT NOT NULL UNIQUE,
        request_method TEXT NOT NULL,
        request_path TEXT NOT NULL,
        request_hash TEXT NOT NULL,
        response_payload_json TEXT NULL,
        status TEXT NOT NULL CHECK (status IN ('processing', 'completed', 'failed')),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
]
