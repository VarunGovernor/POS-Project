MIGRATION_ID = "PHASE_2_AUTH_SESSIONS"
DESCRIPTION = "Create Phase 2 auth, permission, and cashier session tables."

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NULL,
        username TEXT NOT NULL,
        password_hash TEXT NOT NULL,
        display_name TEXT NOT NULL,
        status TEXT NOT NULL,
        offline_login_allowed INTEGER NOT NULL DEFAULT 0,
        last_successful_login_at TEXT NULL,
        permission_version TEXT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (organization_id, username),
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        organization_id INTEGER NULL,
        role_code TEXT NOT NULL,
        role_name TEXT NOT NULL,
        description TEXT NULL,
        status TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        UNIQUE (organization_id, role_code),
        FOREIGN KEY (organization_id) REFERENCES organizations(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        permission_code TEXT NOT NULL UNIQUE,
        permission_name TEXT NOT NULL,
        description TEXT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS role_permissions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        role_id INTEGER NOT NULL,
        permission_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (role_id, permission_id),
        FOREIGN KEY (role_id) REFERENCES roles(id),
        FOREIGN KEY (permission_id) REFERENCES permissions(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS user_roles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        role_id INTEGER NOT NULL,
        created_at TEXT NOT NULL,
        UNIQUE (user_id, role_id),
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (role_id) REFERENCES roles(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS login_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER NOT NULL,
        device_id INTEGER NULL,
        session_token TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL,
        login_mode TEXT NOT NULL CHECK (login_mode IN ('online', 'offline')),
        started_at TEXT NOT NULL,
        expires_at TEXT NOT NULL,
        ended_at TEXT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (user_id) REFERENCES users(id),
        FOREIGN KEY (device_id) REFERENCES devices(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS cashier_sessions (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        session_number TEXT NOT NULL UNIQUE,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        cashier_user_id INTEGER NOT NULL,
        counter_name TEXT NOT NULL,
        status TEXT NOT NULL CHECK (
            status IN ('open', 'closing', 'closed', 'force_closed', 'recovered')
        ),
        opening_cash_amount REAL NOT NULL,
        closing_cash_amount REAL NULL,
        expected_cash_amount REAL NULL,
        cash_difference_amount REAL NULL,
        opened_at TEXT NOT NULL,
        closed_at TEXT NULL,
        notes TEXT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (organization_id) REFERENCES organizations(id),
        FOREIGN KEY (branch_id) REFERENCES branches(id),
        FOREIGN KEY (device_id) REFERENCES devices(id),
        FOREIGN KEY (cashier_user_id) REFERENCES users(id)
    )
    """,
]
