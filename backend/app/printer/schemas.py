from pydantic import BaseModel


class ReprintRequest(BaseModel):
    reason: str | None = None
