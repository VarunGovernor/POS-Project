from fastapi import APIRouter, Depends, Query, Request

from app.auth.dependencies import require_permission
from app.core.responses import success_response
from app.patients.repository import create_patient, get_patient, search_patients
from app.patients.schemas import PatientCreate

router = APIRouter(prefix="/patients", tags=["patients"])


@router.get("")
async def list_patients(
    request: Request,
    q: str | None = None,
    phone: str | None = None,
    patient_number: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=25, ge=1, le=100),
    context: dict = Depends(require_permission("patient.view")),
) -> dict:
    return success_response(request, search_patients(q, phone, patient_number, page, page_size))


@router.post("")
async def create_patient_route(
    payload: PatientCreate,
    request: Request,
    context: dict = Depends(require_permission("patient.create")),
) -> dict:
    return success_response(request, create_patient(payload, context["user"]["id"], request.state.request_id))


@router.get("/{patient_id}")
async def patient_detail(
    patient_id: int,
    request: Request,
    context: dict = Depends(require_permission("patient.view")),
) -> dict:
    return success_response(request, get_patient(patient_id))
