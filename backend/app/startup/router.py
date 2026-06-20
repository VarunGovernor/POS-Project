from fastapi import APIRouter, Request

from app.config import settings
from app.core.responses import success_response
from app.database.connection import database_health, local_device_status

router = APIRouter(prefix="/startup", tags=["startup"])


@router.get("/status")
async def startup_status(request: Request) -> dict:
    db = database_health()
    db_ok = db["status"] == "ok"
    device_status = local_device_status()
    return success_response(
        request,
        {
            "startup_status": "ready" if db_ok else "error",
            "api_status": "ok",
            "database_status": db["status"],
            "recovery_required": False,
            "migration_status": db["migration_status"],
            "device_status": device_status,
            "license_status": "not_configured",
            "tenant_status": "not_configured",
            "printer_status": "not_configured",
            "sync_status": "not_configured",
            "app_version": settings.app_version,
            "backend_version": settings.backend_version,
            "frontend_version": settings.frontend_version,
            "database_version": db["database_version"],
        },
    )
