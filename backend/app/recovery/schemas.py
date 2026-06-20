from pydantic import BaseModel


class ResolveMarker(BaseModel):
    marker_id: str
    resolution_action: str
    notes: str | None = None
