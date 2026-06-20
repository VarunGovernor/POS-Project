MIGRATION_ID = "PHASE_8_SYNC_FOUNDATION"
DESCRIPTION = "Create Phase 8 sync management tables and statuses."

STATEMENTS = [
    """
    CREATE TABLE IF NOT EXISTS sync_events_new (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        event_type TEXT NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        organization_id INTEGER NOT NULL,
        branch_id INTEGER NOT NULL,
        device_id INTEGER NOT NULL,
        payload_json TEXT NOT NULL,
        status TEXT NOT NULL CHECK (
            status IN (
                'pending', 'syncing', 'synced', 'failed_retryable',
                'failed_permanent', 'conflict', 'ignored_duplicate'
            )
        ),
        attempt_count INTEGER NOT NULL DEFAULT 0,
        last_attempt_at TEXT NULL,
        next_attempt_at TEXT NULL,
        idempotency_key TEXT NOT NULL,
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL
    )
    """,
    """
    INSERT OR IGNORE INTO sync_events_new (
        id, event_type, entity_type, entity_id, organization_id, branch_id, device_id,
        payload_json, status, attempt_count, last_attempt_at, next_attempt_at,
        idempotency_key, created_at, updated_at
    )
    SELECT id, event_type, entity_type, entity_id, organization_id, branch_id, device_id,
           payload_json, status, attempt_count, last_attempt_at, next_attempt_at,
           idempotency_key, created_at, updated_at
    FROM sync_events
    """,
    "DROP TABLE IF EXISTS sync_events",
    "ALTER TABLE sync_events_new RENAME TO sync_events",
    """
    CREATE TABLE IF NOT EXISTS sync_attempts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_event_id INTEGER NOT NULL,
        attempt_number INTEGER NOT NULL,
        status TEXT NOT NULL CHECK (status IN ('success', 'failed', 'skipped')),
        request_payload_json TEXT NULL,
        response_payload_json TEXT NULL,
        failure_message TEXT NULL,
        started_at TEXT NOT NULL,
        completed_at TEXT NULL,
        created_at TEXT NOT NULL,
        FOREIGN KEY (sync_event_id) REFERENCES sync_events(id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS sync_conflicts (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        sync_event_id INTEGER NOT NULL,
        entity_type TEXT NOT NULL,
        entity_id TEXT NOT NULL,
        conflict_type TEXT NOT NULL,
        local_payload_json TEXT NOT NULL,
        server_payload_json TEXT NULL,
        resolution_status TEXT NOT NULL CHECK (resolution_status IN ('open', 'resolved', 'ignored')),
        created_at TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        FOREIGN KEY (sync_event_id) REFERENCES sync_events(id)
    )
    """,
]
