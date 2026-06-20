from pydantic import BaseModel


class DraftCreate(BaseModel):
    patient_id: str | None = None
    bill_type: str = "op"
    department_id: str | None = None
    doctor_id: str | None = None
    notes: str | None = None


class DraftUpdate(BaseModel):
    patient_id: str | None = None
    department_id: str | None = None
    doctor_id: str | None = None
    notes: str | None = None


class ItemCreate(BaseModel):
    service_id: str
    quantity: float = 1
    discount_amount: float = 0
    doctor_id: str | None = None
    notes: str | None = None


class ItemUpdate(BaseModel):
    quantity: float
    discount_amount: float = 0
    notes: str | None = None


class VoidDraft(BaseModel):
    reason: str | None = None
