from pathlib import Path
from typing import List, Union

from pydantic import field_validator
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parents[2]


class Settings(BaseSettings):
    # App
    APP_NAME: str = "EU AI Act Compliance Tool"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    API_V1_PREFIX: str = "/api/v1"

    # Database
    DATABASE_URL: str = "postgresql://postgres:postgres@localhost:5432/compliance_db"

    # JWT
    SECRET_KEY: str = "your-secret-key-change-in-production"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30

    # Stripe
    STRIPE_SECRET_KEY: str = ""
    STRIPE_PUBLISHABLE_KEY: str = ""
    STRIPE_WEBHOOK_SECRET: str = ""

    # Pricing (Stripe Price IDs)
    STRIPE_PRICE_STARTER: str = ""  # $99/mo
    STRIPE_PRICE_GROWTH: str = ""   # $299/mo
    STRIPE_PRICE_SCALE: str = ""    # $499/mo

    # Used to build Stripe success/cancel redirect URLs
    FRONTEND_URL: str = "http://localhost:5173"

    # Where generated PDFs are written
    DOCUMENT_STORAGE_DIR: str = str(BACKEND_DIR / "storage" / "documents")

    # CORS
    CORS_ORIGINS: List[str] = ["http://localhost:5173", "http://localhost:3000"]

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def split_cors_origins(cls, value: Union[str, List[str]]) -> Union[str, List[str]]:
        """Accept either a JSON list or a comma-separated string from the env."""
        if isinstance(value, str):
            stripped = value.strip()
            if stripped.startswith("["):
                return value  # let pydantic parse the JSON form
            return [origin.strip() for origin in stripped.split(",") if origin.strip()]
        return value

    @property
    def stripe_enabled(self) -> bool:
        """Stripe API calls are only attempted when a secret key is configured."""
        return bool(self.STRIPE_SECRET_KEY)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
