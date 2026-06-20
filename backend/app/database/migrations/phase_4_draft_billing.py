MIGRATION_ID = "PHASE_4_DRAFT_BILLING"
DESCRIPTION = "Create Phase 4 draft billing tables."

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS bill_drafts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        draft_number TEXT NOT NULL UNIQUE,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        cashier_session_id INTEGER NOT NULL,
        cashier_user_id INTEGER NOT NULL,
        patient_id INTEGER NULL,
        bill_type TEXT NOT NULL,
        department_id INTEGER NULL,
        doctor_id INTEGER NULL,
        status TEXT NOT NULL CHECK (status IN ('draft', 'voided', 'finalized')),
        subtotal_amount REAL NOT NULL DEFAULT 0,
        discount_amount REAL NOT NULL DEFAULT 0,
        tax_amount REAL NOT NULL DEFAULT 0,
        total_amount REAL NOT NULL DEFAULT 0,
        notes TEXT NULL,
        last_autosaved_at TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id),
        FOREIGN KEY (device_id) REFERENCES devices(id),
        FOREIGN KEY (cashier_session_id) REFERENCES cashier_sessions(id),
        FOREIGN KEY (cashier_user_id) REFERENCES users(id),
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (department_id) REFERENCES departments(id),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS bill_draft_items (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        draft_id INTEGER NOT NULL,
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
        unit_price_at_time REAL NOT NULL,
        gross_amount REAL NOT NULL,
        discount_amount REAL NOT NULL DEFAULT 0,
        tax_amount REAL NOT NULL DEFAULT 0,
        final_line_total REAL NOT NULL,
        catalog_version TEXT NOT NULL,
        price_version TEXT NOT NULL,
        notes TEXT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (draft_id) REFERENCES bill_drafts(id),
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id),
        FOREIGN KEY (device_id) REFERENCES devices(id),
        FOREIGN KEY (service_id) REFERENCES services(id),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id)
    )
    """,
]
