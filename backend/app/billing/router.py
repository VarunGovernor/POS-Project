from fastapi import APIRouter, Depends, Header, Query, Request

from app.auth.dependencies import require_permission
from app.billing.repository import (
    add_item,
    bill_detail,
    create_draft,
    draft_detail,
    finalize_draft,
    list_bills,
    list_drafts,
    pending_sync_events,
    receipt_by_bill,
    receipt_detail,
    remove_item,
    update_draft,
    update_item,
    void_draft,
)
from app.billing.schemas import DraftCreate, DraftUpdate, FinalizeDraft, ItemCreate, ItemUpdate, VoidDraft
from app.core.responses import success_response

router = APIRouter(prefix="/bills/drafts", tags=["bill-drafts"])
bills_router = APIRouter(prefix="/bills", tags=["bills"])
receipts_router = APIRouter(prefix="/receipts", tags=["receipts"])
sync_router = APIRouter(prefix="/sync", tags=["sync"])


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


@router.post("/{draft_id}/finalize")
async def finalize(
    draft_id: int,
    payload: FinalizeDraft,
    request: Request,
    idempotency_key: str | None = Header(default=None, alias="Idempotency-Key"),
    context: dict = Depends(require_permission("billing.bill.finalize")),
) -> dict:
    return success_response(
        request,
        finalize_draft(draft_id, payload, context, idempotency_key, str(request.url.path), request.state.request_id),
    )


@bills_router.get("")
async def bills(
    request: Request,
    status: str | None = None,
    patient_id: str | None = None,
    cashier_session_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    context: dict = Depends(require_permission("billing.bill.final.view")),
) -> dict:
    return success_response(request, list_bills(status, patient_id, cashier_session_id, page, page_size))


@bills_router.get("/{bill_id}")
async def bill(bill_id: int, request: Request, context: dict = Depends(require_permission("billing.bill.final.view"))) -> dict:
    return success_response(request, bill_detail(bill_id))


@receipts_router.get("/by-bill/{bill_id}")
async def receipt_for_bill(bill_id: int, request: Request, context: dict = Depends(require_permission("billing.receipt.view"))) -> dict:
    return success_response(request, receipt_by_bill(bill_id))


@receipts_router.get("/{receipt_id}")
async def receipt(receipt_id: int, request: Request, context: dict = Depends(require_permission("billing.receipt.view"))) -> dict:
    return success_response(request, receipt_detail(receipt_id))


@sync_router.get("/events")
async def sync_events(request: Request, context: dict = Depends(require_permission("sync.event.view"))) -> dict:
    return success_response(request, pending_sync_events())
