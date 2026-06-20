MIGRATION_ID = "PHASE_9_REPORTS_SUPPORT"
DESCRIPTION = "Create Phase 9 support bundle metadata."

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS support_bundles (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        bundle_id TEXT NOT NULL UNIQUE,
        status TEXT NOT NULL CHECK (status IN ('created', 'failed')),
        file_path TEXT NOT NULL,
        metadata_json TEXT NOT NULL,
        created_by_user_id INTEGER NULL,
        created_at TEXT NOT NULL
    )
    """,
]
