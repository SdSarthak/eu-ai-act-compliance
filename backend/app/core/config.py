import json
from pathlib import Path
from typing import List, Union

from pydantic import field_validator, model_validator
from pydantic_settings import BaseSettings

BACKEND_DIR = Path(__file__).resolve().parents[2]

# Values that mean "nobody set a real key". Booting a production environment
# with any of these would let anyone mint a valid token, so it is refused.
PLACEHOLDER_SECRET_KEYS = {
    "your-secret-key-change-in-production",
    "CHANGE_ME_GENERATE_A_RANDOM_48_BYTE_STRING",
    "changeme",
    "secret",
}

MIN_SECRET_KEY_LENGTH = 32


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

    # CORS. Deliberately typed as a plain string rather than List[str]:
    # pydantic-settings JSON-decodes complex fields inside the env source,
    # before any validator runs, so a comma-separated value would raise a
    # SettingsError at import time instead of reaching our parser.
    CORS_ORIGINS: str = "http://localhost:5173,http://localhost:3000"

    @field_validator("CORS_ORIGINS", mode="before")
    @classmethod
    def normalise_cors_origins(cls, value: Union[str, List[str]]) -> str:
        """Accept a list, a JSON array or a comma-separated string."""
        if isinstance(value, (list, tuple)):
            return ",".join(str(origin).strip() for origin in value)
        return str(value)

    @property
    def cors_origins(self) -> List[str]:
        """The allow-list as a list of origins.

        Accepts both the comma-separated form documented in `.env.example` and
        a JSON array, so either style of deployment config works.
        """
        raw = self.CORS_ORIGINS.strip()
        if not raw:
            return []
        if raw.startswith("["):
            try:
                parsed = json.loads(raw)
            except json.JSONDecodeError:
                pass
            else:
                if isinstance(parsed, list):
                    return [str(origin).strip() for origin in parsed if str(origin).strip()]
        return [origin.strip() for origin in raw.split(",") if origin.strip()]

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() == "production"

    @model_validator(mode="after")
    def enforce_production_secret_key(self) -> "Settings":
        """Refuse to boot a production environment on a placeholder signing key.

        Development keeps the convenient default so the app runs with no
        configuration at all, but shipping that key would make every JWT
        forgeable.
        """
        if not self.is_production:
            return self

        if self.SECRET_KEY in PLACEHOLDER_SECRET_KEYS:
            raise ValueError(
                "SECRET_KEY is still the placeholder value. Generate one with: "
                'python -c "import secrets; print(secrets.token_urlsafe(48))"'
            )
        if len(self.SECRET_KEY) < MIN_SECRET_KEY_LENGTH:
            raise ValueError(
                f"SECRET_KEY must be at least {MIN_SECRET_KEY_LENGTH} characters "
                "in production."
            )
        return self

    @property
    def stripe_enabled(self) -> bool:
        """Stripe API calls are only attempted when a secret key is configured."""
        return bool(self.STRIPE_SECRET_KEY)

    class Config:
        env_file = ".env"
        case_sensitive = True


settings = Settings()
