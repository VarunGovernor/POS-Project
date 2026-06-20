MIGRATION_ID = "PHASE_7_RECOVERY_FOUNDATION"
DESCRIPTION = "Create Phase 7 recovery marker table."

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS recovery_markers (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        marker_code TEXT NOT NULL UNIQUE,
        marker_type TEXT NOT NULL CHECK (
            marker_type IN (
                'UNCLEAN_SHUTDOWN', 'ACTIVE_SESSION_FOUND', 'OPEN_DRAFT_FOUND',
                'UNSYNCED_BILL_FOUND', 'PENDING_PRINT_JOB_FOUND', 'FAILED_PRINT_JOB_FOUND',
                'STALE_SYNCING_EVENT_FOUND', 'UNKNOWN_PAYMENT_FOUND', 'DATABASE_STARTUP_ERROR',
                'MIGRATION_FAILURE', 'DEVICE_TAMPER_WARNING', 'LICENSE_REQUIRES_REVIEW'
            )
        ),
        severity TEXT NOT NULL CHECK (severity IN ('info', 'warning', 'critical')),
        status TEXT NOT NULL CHECK (status IN ('open', 'acknowledged', 'resolved', 'ignored')),
        entity_type TEXT NULL,
        entity_id TEXT NULL,
        organization_id INTEGER NULL,
        branch_id INTEGER NULL,
        device_id INTEGER NULL,
        cashier_session_id INTEGER NULL,
        title TEXT NOT NULL,
        description TEXT NOT NULL,
        detected_at TEXT NOT NULL,
        resolved_at TEXT NULL,
        resolved_by_user_id INTEGER NULL,
        resolution_action TEXT NULL,
        metadata_json TEXT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
]
