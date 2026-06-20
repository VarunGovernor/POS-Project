from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_permission
from app.core.responses import success_response
from app.printer.repository import jobs, print_receipt, retry_job, status, test_print
from app.printer.schemas import ReprintRequest

router = APIRouter(prefix="/printer", tags=["printer"])
receipt_router = APIRouter(prefix="/receipts", tags=["receipts"])


@router.get("/status")
async def printer_status(request: Request, context: dict = Depends(require_permission("printer.view"))) -> dict:
    return success_response(request, status())


@router.post("/test")
async def printer_test(request: Request, context: dict = Depends(require_permission("printer.test"))) -> dict:
    return success_response(request, test_print(context["user"]["id"], request.state.request_id))


@router.get("/jobs")
async def printer_jobs(
    request: Request,
    status: str | None = None,
    receipt_id: str | None = None,
    bill_id: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    context: dict = Depends(require_permission("printer.view")),
) -> dict:
    return success_response(request, jobs(status, receipt_id, bill_id, page, page_size))


@router.post("/jobs/{job_id}/retry")
async def retry(job_id: int, request: Request, context: dict = Depends(require_permission("printer.job.retry"))) -> dict:
    return success_response(request, retry_job(job_id, context["user"]["id"], request.state.request_id))


@receipt_router.post("/{receipt_id}/print")
async def print_original(receipt_id: int, request: Request, context: dict = Depends(require_permission("printer.receipt.print"))) -> dict:
    return success_response(request, print_receipt(receipt_id, context["user"]["id"], request.state.request_id))


@receipt_router.post("/{receipt_id}/reprint")
async def reprint(receipt_id: int, payload: ReprintRequest, request: Request, context: dict = Depends(require_permission("printer.receipt.reprint"))) -> dict:
    return success_response(request, print_receipt(receipt_id, context["user"]["id"], request.state.request_id, payload.reason))
