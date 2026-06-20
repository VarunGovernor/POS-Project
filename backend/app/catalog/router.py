from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_permission
from app.catalog.repository import list_departments, list_doctors, master_sync_state, search_services
from app.core.responses import success_response

router = APIRouter(prefix="/catalog", tags=["catalog"])


@router.get("/services")
async def services(
    request: Request,
    q: str | None = None,
    service_type: str | None = None,
    department_id: str | None = None,
    status: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    context: dict = Depends(require_permission("catalog.service.view")),
) -> dict:
    return success_response(request, search_services(q, service_type, department_id, status, page, page_size))


@router.get("/departments")
async def departments(request: Request, context: dict = Depends(require_permission("catalog.department.view"))) -> dict:
    return success_response(request, list_departments())


@router.get("/doctors")
async def doctors(
    request: Request,
    q: str | None = None,
    department_id: str | None = None,
    status: str | None = None,
    context: dict = Depends(require_permission("catalog.doctor.view")),
) -> dict:
    return success_response(request, list_doctors(q, department_id, status))


@router.get("/master-sync-state")
async def sync_state(request: Request, context: dict = Depends(require_permission("sync.master.view"))) -> dict:
    return success_response(request, master_sync_state())
