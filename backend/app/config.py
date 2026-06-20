import os
from pathlib import Path

from pydantic import BaseModel

DEFAULT_DATABASE_PATH = str(Path(__file__).resolve().parents[1] / "data" / "counteros.sqlite3")


class Settings(BaseModel):
    api_version: str = "v1"
    app_version: str = "0.1.0"
    backend_version: str = "0.1.0"
    frontend_version: str = "0.1.0"
    database_version: str = "not_configured"
    database_path: str = os.getenv("COUNTEROS_DATABASE_PATH", DEFAULT_DATABASE_PATH)
    environment: str = "development"


settings = Settings()
