from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_permission
from app.core.responses import success_response
from app.recovery.repository import list_markers, recovery_status, resolve_marker, scan_recovery
from app.recovery.schemas import ResolveMarker

router = APIRouter(prefix="/recovery", tags=["recovery"])


@router.get("/status")
async def status(request: Request, context: dict = Depends(require_permission("recovery.view"))) -> dict:
    return success_response(request, recovery_status())


@router.get("/work-items")
async def work_items(
    request: Request,
    status: str | None = None,
    severity: str | None = None,
    marker_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    context: dict = Depends(require_permission("recovery.view")),
) -> dict:
    return success_response(request, list_markers(status, severity, marker_type, page, page_size))


@router.post("/scan")
async def scan(request: Request, context: dict = Depends(require_permission("recovery.scan"))) -> dict:
    return success_response(request, scan_recovery())


@router.post("/resolve")
async def resolve(payload: ResolveMarker, request: Request, context: dict = Depends(require_permission("recovery.resolve"))) -> dict:
    return success_response(request, resolve_marker(int(payload.marker_id), payload.resolution_action, payload.notes, context["user"]["id"], request.state.request_id))
