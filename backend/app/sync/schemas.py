from pydantic import BaseModel


class RetryRequest(BaseModel):
    reason: str | None = None
