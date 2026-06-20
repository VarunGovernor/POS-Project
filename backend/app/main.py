import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError

from app.core.errors import AppError
from app.core.logging import configure_logging
from app.core.request_id import RequestIdMiddleware
from app.core.responses import error_response
from app.auth.router import router as auth_router
from app.billing.router import bills_router, receipts_router, router as billing_router
from app.catalog.router import router as catalog_router
from app.database.connection import initialize_database
from app.device.router import router as device_router
from app.health.router import router as health_router
from app.patients.router import router as patients_router
from app.printer.router import receipt_router as printer_receipt_router, router as printer_router
from app.recovery.repository import scan_recovery
from app.recovery.router import router as recovery_router
from app.sessions.router import router as sessions_router
from app.startup.router import router as startup_router
from app.sync.router import router as sync_router

configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        initialize_database()
        scan_recovery()
    except Exception as exc:
        logger.error("Database startup failed: %s", exc)
    yield


app = FastAPI(title="CounterOS Local API", version="0.1.0", lifespan=lifespan)
app.add_middleware(RequestIdMiddleware)

api_prefix = "/api/v1"
app.include_router(auth_router, prefix=api_prefix)
app.include_router(billing_router, prefix=api_prefix)
app.include_router(bills_router, prefix=api_prefix)
app.include_router(catalog_router, prefix=api_prefix)
app.include_router(device_router, prefix=api_prefix)
app.include_router(health_router, prefix=api_prefix)
app.include_router(patients_router, prefix=api_prefix)
app.include_router(printer_router, prefix=api_prefix)
app.include_router(printer_receipt_router, prefix=api_prefix)
app.include_router(recovery_router, prefix=api_prefix)
app.include_router(receipts_router, prefix=api_prefix)
app.include_router(sessions_router, prefix=api_prefix)
app.include_router(startup_router, prefix=api_prefix)
app.include_router(sync_router, prefix=api_prefix)


@app.exception_handler(AppError)
async def app_error_handler(request: Request, exc: AppError):
    return error_response(
        request,
        code=exc.code,
        message=exc.message,
        status_code=exc.status_code,
        details=exc.details,
    )


@app.exception_handler(RequestValidationError)
async def validation_error_handler(request: Request, exc: RequestValidationError):
    return error_response(
        request,
        code="VALIDATION_ERROR",
        message="Request validation failed.",
        status_code=422,
        details={"errors": exc.errors()},
    )


@app.exception_handler(Exception)
async def unhandled_error_handler(request: Request, exc: Exception):
    return error_response(
        request,
        code="INTERNAL_SERVER_ERROR",
        message="Unexpected server error.",
        status_code=500,
    )
