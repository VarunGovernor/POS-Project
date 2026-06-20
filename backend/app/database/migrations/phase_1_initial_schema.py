MIGRATION_ID = "PHASE_1_INITIAL_SCHEMA"
DESCRIPTION = "Create Phase 1 database foundation tables."

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_code TEXT NOT NULL UNIQUE,
        organization_name TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS branches (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_code TEXT NOT NULL,
        branch_name TEXT NOT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (organization_id) REFERENCES organizations(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS devices (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_code TEXT NOT NULL UNIQUE,
        device_name TEXT NOT NULL,
        counter_name TEXT NOT NULL,
        installation_id TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL,
        activation_status TEXT NOT NULL,
        last_successful_sync_at TEXT NULL,
        last_master_sync_at TEXT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS settings (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NULL,
        branch_id INTEGER NULL,
        device_id INTEGER NULL,
        setting_key TEXT NOT NULL,
        setting_value TEXT NOT NULL,
        setting_scope TEXT NOT NULL,
        is_readonly INTEGER NOT NULL DEFAULT 0,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id),
        FOREIGN KEY (device_id) REFERENCES devices(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS migration_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        migration_id TEXT NOT NULL UNIQUE,
        description TEXT NOT NULL,
        status TEXT NOT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT NULL,
        failure_message TEXT NULL,
        created_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS app_runtime_state (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        device_id INTEGER NULL,
        last_started_at TEXT NULL,
        last_clean_shutdown_at TEXT NULL,
        last_unclean_shutdown_detected_at TEXT NULL,
        current_app_version TEXT NOT NULL,
        current_database_version TEXT NOT NULL,
        startup_status TEXT NOT NULL,
        shutdown_status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (device_id) REFERENCES devices(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS audit_logs (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        audit_id TEXT NOT NULL UNIQUE,
        organization_id INTEGER NULL,
        branch_id INTEGER NULL,
        device_id INTEGER NULL,
        actor_user_id TEXT NULL,
        action TEXT NOT NULL,
        entity_type TEXT NULL,
        entity_id TEXT NULL,
        severity TEXT NOT NULL,
        metadata_json TEXT NULL,
        request_id TEXT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id),
        FOREIGN KEY (device_id) REFERENCES devices(id)
    )
    """,
]
