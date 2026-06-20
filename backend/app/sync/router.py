from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_permission
from app.core.responses import success_response
from app.sync.repository import event_detail, list_conflicts, list_events, retry_all, retry_one, sync_status

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status")
async def status(request: Request, context: dict = Depends(require_permission("sync.status.view"))) -> dict:
    return success_response(request, sync_status())


@router.get("/events")
async def events(
    request: Request,
    status: str | None = None,
    event_type: str | None = None,
    entity_type: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    context: dict = Depends(require_permission("sync.event.view")),
) -> dict:
    return success_response(request, list_events(status, event_type, entity_type, page, page_size))


@router.get("/events/{event_id}")
async def detail(event_id: int, request: Request, context: dict = Depends(require_permission("sync.event.view"))) -> dict:
    return success_response(request, event_detail(event_id))


@router.post("/retry")
async def retry(request: Request, context: dict = Depends(require_permission("sync.run"))) -> dict:
    return success_response(request, retry_all(context["user"]["id"], request.state.request_id))


@router.post("/events/{event_id}/retry")
async def retry_event(event_id: int, request: Request, context: dict = Depends(require_permission("sync.event.retry"))) -> dict:
    return success_response(request, retry_one(event_id, context["user"]["id"], request.state.request_id))


@router.get("/conflicts")
async def conflicts(request: Request, context: dict = Depends(require_permission("sync.conflict.view"))) -> dict:
    return success_response(request, list_conflicts())
