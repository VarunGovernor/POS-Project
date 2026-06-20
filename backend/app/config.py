from pydantic import BaseModel


class Settings(BaseModel):
    api_version: str = "v1"
    app_version: str = "0.1.0"
    backend_version: str = "0.1.0"
    frontend_version: str = "0.1.0"
    database_version: str = "not_configured"
    environment: str = "development"


settings = Settings()
