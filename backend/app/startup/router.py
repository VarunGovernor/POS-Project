from fastapi import APIRouter, Request

from app.config import settings
from app.core.responses import success_response

router = APIRouter(prefix="/startup", tags=["startup"])


@router.get("/status")
async def startup_status(request: Request) -> dict:
    return success_response(
        request,
        {
            "startup_status": "ready",
            "api_status": "ok",
            "database_status": "not_configured",
            "recovery_required": False,
            "migration_status": "not_configured",
            "device_status": "not_configured",
            "license_status": "not_configured",
            "tenant_status": "not_configured",
            "printer_status": "not_configured",
            "sync_status": "not_configured",
            "app_version": settings.app_version,
            "backend_version": settings.backend_version,
            "frontend_version": settings.frontend_version,
            "database_version": settings.database_version,
        },
    )
