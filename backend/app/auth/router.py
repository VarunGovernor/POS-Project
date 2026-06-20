from pydantic import BaseModel
from fastapi import APIRouter, Depends, Request

from app.auth.dependencies import current_context
from app.auth.repository import login, logout
from app.core.responses import success_response

router = APIRouter(prefix="/auth", tags=["auth"])


class LoginRequest(BaseModel):
    username: str
    password: str
    counter_name: str | None = None


@router.post("/login")
async def login_route(payload: LoginRequest, request: Request) -> dict:
    return success_response(request, login(payload.username, payload.password, "online", request.state.request_id))


@router.post("/offline-login")
async def offline_login_route(payload: LoginRequest, request: Request) -> dict:
    return success_response(request, login(payload.username, payload.password, "offline", request.state.request_id))


@router.get("/me")
async def me(request: Request, context: dict = Depends(current_context)) -> dict:
    return success_response(
        request,
        {
            "user": {**context["user"], "id": str(context["user"]["id"])},
            "login_session_id": str(context["session"]["id"]),
            "expires_at": context["session"]["expires_at"],
        },
    )


@router.post("/logout")
async def logout_route(request: Request, context: dict = Depends(current_context)) -> dict:
    logout(context["session"]["session_token"], request.state.request_id)
    return success_response(request, {"status": "ok"})
