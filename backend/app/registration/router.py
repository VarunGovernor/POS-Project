from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_permission
from app.core.responses import success_response
from app.registration.schemas import RegistrationCreate, RegistrationUpdate
from app.registration.service import check_in, create_registration, get_registration, list_registrations, send_to_billing, update_registration

router = APIRouter(prefix="/registrations", tags=["registrations"])


@router.get("")
async def registrations(
    request: Request,
    registration_type: str | None = None,
    status: str | None = None,
    billing_status: str | None = None,
    q: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    context: dict = Depends(require_permission("registration.view")),
) -> dict:
    return success_response(request, list_registrations(registration_type, status, billing_status, q, page, page_size))


@router.post("")
async def create(payload: RegistrationCreate, request: Request, context: dict = Depends(require_permission("registration.create"))) -> dict:
    return success_response(request, create_registration(payload, context, request.state.request_id))


@router.get("/{registration_id}")
async def detail(registration_id: int, request: Request, context: dict = Depends(require_permission("registration.view"))) -> dict:
    return success_response(request, get_registration(registration_id))


@router.patch("/{registration_id}")
async def patch(registration_id: int, payload: RegistrationUpdate, request: Request, context: dict = Depends(require_permission("registration.update"))) -> dict:
    return success_response(request, update_registration(registration_id, payload, context, request.state.request_id))


@router.post("/{registration_id}/check-in")
async def post_check_in(registration_id: int, request: Request, context: dict = Depends(require_permission("registration.update"))) -> dict:
    return success_response(request, check_in(registration_id, context, request.state.request_id))


@router.post("/{registration_id}/send-to-billing")
async def post_send_to_billing(registration_id: int, request: Request, context: dict = Depends(require_permission("registration.send_to_billing"))) -> dict:
    return success_response(request, send_to_billing(registration_id, context, request.state.request_id))
