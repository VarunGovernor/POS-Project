from __future__ import annotations

import os
from typing import Any

from app.config import settings
from app.core.errors import AppError


def adapter_name() -> str:
    return "development" if settings.environment == "development" else "not_configured"


def adapter_status() -> str:
    return adapter_name()


def send_event(event: dict[str, Any]) -> dict[str, Any]:
    if settings.environment != "development" and not os.getenv("COUNTEROS_SYNC_ENDPOINT"):
        raise AppError("SYNC_ENDPOINT_NOT_CONFIGURED", "Sync endpoint is not configured.", 503)
    return {
        "adapter": adapter_name(),
        "accepted": True,
        "remote_reference": f"local-sync-{event['id']}",
    }


def send_batch(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    return [send_event(event) for event in events]
