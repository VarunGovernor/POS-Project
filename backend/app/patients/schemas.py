from pydantic import BaseModel


class PatientCreate(BaseModel):
    full_name: str
    phone: str | None = None
    gender: str | None = None
    age_years: int | None = None
    address_line1: str | None = None
