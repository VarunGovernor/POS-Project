MIGRATION_ID = "PHASE_13_HOSPITAL_REGISTRATION"
DESCRIPTION = "Create hospital registration foundation tables."

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS hospital_registrations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registration_number TEXT NOT NULL UNIQUE,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_id INTEGER NULL,
        patient_id INTEGER NULL,
        registration_type TEXT NOT NULL CHECK (registration_type IN ('op', 'ip', 'emergency', 'follow_up', 'lab', 'pharmacy_walkin')),
        patient_name TEXT NOT NULL,
        mobile_number TEXT NULL,
        age_years INTEGER NULL,
        gender TEXT NULL,
        department_id INTEGER NULL,
        doctor_id INTEGER NULL,
        visit_type TEXT NULL,
        token_number TEXT NULL,
        admission_number TEXT NULL,
        ward TEXT NULL,
        room_or_bed TEXT NULL,
        attender_name TEXT NULL,
        deposit_amount_paise INTEGER NULL,
        priority TEXT NULL,
        sample_status TEXT NULL,
        prescription_reference TEXT NULL,
        status TEXT NOT NULL CHECK (status IN ('registered', 'checked_in', 'admitted', 'active', 'completed', 'cancelled')),
        billing_status TEXT NOT NULL CHECK (billing_status IN ('pending', 'ready_for_billing', 'sent_to_billing', 'billed')),
        notes TEXT NULL,
        created_by_user_id INTEGER NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id),
        FOREIGN KEY (device_id) REFERENCES devices(id),
        FOREIGN KEY (patient_id) REFERENCES patients(id),
        FOREIGN KEY (department_id) REFERENCES departments(id),
        FOREIGN KEY (doctor_id) REFERENCES doctors(id),
        FOREIGN KEY (created_by_user_id) REFERENCES users(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS hospital_registration_events (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        registration_id INTEGER NOT NULL,
        event_type TEXT NOT NULL,
        notes TEXT NULL,
        created_by_user_id INTEGER NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (registration_id) REFERENCES hospital_registrations(id),
        FOREIGN KEY (created_by_user_id) REFERENCES users(id)
    )
    """,
    "CREATE INDEX IF NOT EXISTS idx_hospital_registrations_type_status ON hospital_registrations (registration_type, status, billing_status)",
    "CREATE INDEX IF NOT EXISTS idx_hospital_registrations_patient_name ON hospital_registrations (patient_name)",
]
