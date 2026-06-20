from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_permission
from app.core.responses import success_response

router = APIRouter(prefix="/device", tags=["device"])


@router.get("/status")
async def device_status(request: Request, context: dict = Depends(require_permission("device.view"))) -> dict:
    device = context["device"]
    return success_response(
        request,
        {
            "device_id": str(device["id"]),
            "device_code": device["device_code"],
            "device_name": device["device_name"],
            "installation_id": device["installation_id"],
            "organization_id": str(device["organization_id"]),
            "branch_id": str(device["branch_id"]),
            "counter_name": device["counter_name"],
            "status": device["status"],
            "activation_status": device["activation_status"],
            "last_successful_sync_at": device["last_successful_sync_at"],
            "last_master_sync_at": device["last_master_sync_at"],
        },
    )
