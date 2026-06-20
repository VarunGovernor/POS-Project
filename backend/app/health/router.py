from fastapi import APIRouter, Request

from app.config import settings
from app.core.responses import success_response
from app.database.connection import database_health, local_device_status
from app.printer.repository import printer_status_value

router = APIRouter(prefix="/health", tags=["health"])


@router.get("")
async def health(request: Request) -> dict:
    db = database_health()
    device_status = local_device_status()
    printer_status = printer_status_value()
    return success_response(
        request,
        {
            "status": "ok" if db["status"] == "ok" else "error",
            "api": "ok",
            "database": db["status"],
            "sync": "not_configured",
            "printer": printer_status,
            "storage": "not_configured",
            "license": "not_configured",
            "device": device_status,
            "tenant": "not_configured",
            "migration": db["migration_status"],
            "unsynced_event_count": 0,
            "failed_event_count": 0,
            "last_sync_at": None,
            "last_backup_at": None,
        },
    )


@router.get("/database")
async def database(request: Request) -> dict:
    return success_response(request, database_health())


@router.get("/version")
async def version(request: Request) -> dict:
    db = database_health()
    return success_response(
        request,
        {
            "api_version": settings.api_version,
            "app_version": settings.app_version,
            "backend_version": settings.backend_version,
            "frontend_version": settings.frontend_version,
            "database_version": db["database_version"],
            "environment": settings.environment,
        },
    )
