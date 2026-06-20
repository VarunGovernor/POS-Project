from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import require_permission
from app.auth.repository import close_cashier_session, current_cashier_session, open_cashier_session, session_payload
from app.core.responses import success_response

router = APIRouter(prefix="/sessions", tags=["sessions"])


class OpenSessionRequest(BaseModel):
    counter_name: str
    opening_cash_amount: float
    notes: str | None = None


class CloseSessionRequest(BaseModel):
    session_id: str
    closing_cash_amount: float
    notes: str | None = None


@router.get("/current")
async def current_session(request: Request, context: dict = Depends(require_permission("session.view"))) -> dict:
    session = current_cashier_session(context["device"]["id"])
    return success_response(request, {"session": session_payload(session)})


@router.post("/open")
async def open_session(payload: OpenSessionRequest, request: Request, context: dict = Depends(require_permission("session.open"))) -> dict:
    session = open_cashier_session(
        context["user"]["id"],
        context["device"],
        payload.counter_name,
        payload.opening_cash_amount,
        payload.notes,
        request.state.request_id,
    )
    return success_response(request, {"session": session})


@router.post("/close")
async def close_session(payload: CloseSessionRequest, request: Request, context: dict = Depends(require_permission("session.close"))) -> dict:
    session = close_cashier_session(
        context["user"]["id"],
        int(payload.session_id),
        payload.closing_cash_amount,
        payload.notes,
        request.state.request_id,
    )
    return success_response(request, {"session": session})
