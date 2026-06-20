from typing import Any

from fastapi import Request
from fastapi.responses import JSONResponse


def get_request_id(request: Request) -> str:
    return getattr(request.state, "request_id", "REQ-UNKNOWN")


def success_response(request: Request, data: dict[str, Any]) -> dict[str, Any]:
    return {
        "success": True,
        "data": data,
        "request_id": get_request_id(request),
    }


def error_response(
    request: Request,
    code: str,
    message: str,
    status_code: int = 500,
    details: dict[str, Any] | None = None,
) -> JSONResponse:
    return JSONResponse(
        status_code=status_code,
        content={
            "success": False,
            "error": {
                "code": code,
                "message": message,
                "details": details or {},
            },
            "request_id": get_request_id(request),
        },
    )
