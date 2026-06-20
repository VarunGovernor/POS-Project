from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_permission
from app.billing.repository import add_item, create_draft, draft_detail, list_drafts, remove_item, update_draft, update_item, void_draft
from app.billing.schemas import DraftCreate, DraftUpdate, ItemCreate, ItemUpdate, VoidDraft
from app.core.responses import success_response

router = APIRouter(prefix="/bills/drafts", tags=["bill-drafts"])


@router.post("")
async def create(payload: DraftCreate, request: Request, context: dict = Depends(require_permission("billing.bill.create"))) -> dict:
    return success_response(request, create_draft(payload, context, request.state.request_id))


@router.get("")
async def drafts(
    request: Request,
    status: str | None = None,
    patient_id: str | None = None,
    cashier_session_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    context: dict = Depends(require_permission("billing.bill.view")),
) -> dict:
    return success_response(request, list_drafts(status, patient_id, cashier_session_id, page, page_size))


@router.get("/{draft_id}")
async def detail(draft_id: int, request: Request, context: dict = Depends(require_permission("billing.bill.view"))) -> dict:
    return success_response(request, draft_detail(draft_id))


@router.patch("/{draft_id}")
async def patch_draft(draft_id: int, payload: DraftUpdate, request: Request, context: dict = Depends(require_permission("billing.bill.edit"))) -> dict:
    return success_response(request, update_draft(draft_id, payload, context["user"]["id"], request.state.request_id))


@router.post("/{draft_id}/items")
async def post_item(draft_id: int, payload: ItemCreate, request: Request, context: dict = Depends(require_permission("billing.bill.edit"))) -> dict:
    return success_response(request, add_item(draft_id, payload, context, request.state.request_id))


@router.patch("/{draft_id}/items/{item_id}")
async def patch_item(draft_id: int, item_id: int, payload: ItemUpdate, request: Request, context: dict = Depends(require_permission("billing.bill.edit"))) -> dict:
    return success_response(request, update_item(draft_id, item_id, payload))


@router.delete("/{draft_id}/items/{item_id}")
async def delete_item(draft_id: int, item_id: int, request: Request, context: dict = Depends(require_permission("billing.bill.edit"))) -> dict:
    return success_response(request, remove_item(draft_id, item_id))


@router.post("/{draft_id}/void")
async def void(draft_id: int, payload: VoidDraft, request: Request, context: dict = Depends(require_permission("billing.bill.void_draft"))) -> dict:
    return success_response(request, void_draft(draft_id, payload.reason, context["user"]["id"], request.state.request_id))
