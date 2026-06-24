from pydantic import BaseModel


class RegistrationCreate(BaseModel):
    registration_type: str
    patient_name: str | None = None
    mobile_number: str | None = None
    age_years: int | None = None
    gender: str | None = None
    department_id: str | None = None
    doctor_id: str | None = None
    visit_type: str | None = None
    ward: str | None = None
    room_or_bed: str | None = None
    attender_name: str | None = None
    deposit_amount: float | None = None
    priority: str | None = None
    sample_status: str | None = None
    prescription_reference: str | None = None
    notes: str | None = None


class RegistrationUpdate(BaseModel):
    patient_name: str | None = None
    mobile_number: str | None = None
    age_years: int | None = None
    gender: str | None = None
    department_id: str | None = None
    doctor_id: str | None = None
    visit_type: str | None = None
    ward: str | None = None
    room_or_bed: str | None = None
    attender_name: str | None = None
    deposit_amount: float | None = None
    priority: str | None = None
    sample_status: str | None = None
    prescription_reference: str | None = None
    status: str | None = None
    billing_status: str | None = None
    notes: str | None = None
