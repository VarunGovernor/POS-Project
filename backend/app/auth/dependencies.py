from typing import Callable

from fastapi import Depends, Header

from app.auth.repository import load_context
from app.core.errors import AppError


def current_context(authorization: str | None = Header(default=None)) -> dict:
    if not authorization or not authorization.startswith("Bearer "):
        raise AppError("AUTH_SESSION_REQUIRED", "Active auth session required.", 401)
    context = load_context(authorization.removeprefix("Bearer ").strip())
    if not context:
        raise AppError("AUTH_SESSION_REQUIRED", "Active auth session required.", 401)
    return context


def require_permission(permission: str) -> Callable:
    def dependency(context: dict = Depends(current_context)) -> dict:
        if permission not in context["user"]["permissions"]:
            raise AppError("AUTH_PERMISSION_DENIED", "Permission denied.", 403)
        return context

    return dependency
