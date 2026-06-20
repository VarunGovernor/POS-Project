MIGRATION_ID = "PHASE_3_PATIENT_CATALOG"
DESCRIPTION = "Create Phase 3 patient and catalog foundation tables."

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS patients (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NULL,
        patient_number TEXT NOT NULL,
        full_name TEXT NOT NULL,
        phone TEXT NULL,
        gender TEXT NULL,
        age_years INTEGER NULL,
        address_line1 TEXT NULL,
        status TEXT NOT NULL,
        sync_status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (organization_id, patient_number),
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS departments (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NULL,
        department_code TEXT NOT NULL,
        department_name TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (organization_id, department_code),
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS doctors (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NULL,
        department_id INTEGER NULL,
        doctor_code TEXT NOT NULL,
        full_name TEXT NOT NULL,
        specialization TEXT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (organization_id, doctor_code),
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id),
        FOREIGN KEY (department_id) REFERENCES departments(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS services (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NULL,
        department_id INTEGER NULL,
        service_code TEXT NOT NULL,
        service_name TEXT NOT NULL,
        service_type TEXT NOT NULL CHECK (service_type IN ('op', 'lab', 'pharmacy', 'general', 'other')),
        status TEXT NOT NULL,
        catalog_version TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (organization_id, service_code),
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id),
        FOREIGN KEY (department_id) REFERENCES departments(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS price_lists (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NULL,
        price_list_code TEXT NOT NULL,
        price_list_name TEXT NOT NULL,
        status TEXT NOT NULL,
        effective_from TEXT NULL,
        effective_to TEXT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (organization_id, price_list_code),
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS service_prices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NULL,
        service_id INTEGER NOT NULL,
        price_list_id INTEGER NULL,
        price_amount REAL NOT NULL,
        currency TEXT NOT NULL,
        price_version TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (service_id, price_list_id),
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id),
        FOREIGN KEY (service_id) REFERENCES services(id),
        FOREIGN KEY (price_list_id) REFERENCES price_lists(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS tax_rules (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NULL,
        tax_code TEXT NOT NULL,
        tax_name TEXT NOT NULL,
        tax_rate REAL NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (organization_id, tax_code),
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS master_sync_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NULL,
        master_type TEXT NOT NULL,
        version_code TEXT NOT NULL,
        last_successful_sync_at TEXT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (organization_id, master_type),
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id)
    )
    """,
]
