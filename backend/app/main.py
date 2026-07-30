import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.exc import SQLAlchemyError

from app.api.v1 import api_router
from app.core.config import settings
from app.core.database import init_db

logger = logging.getLogger(__name__)

app = FastAPI(
    title=settings.APP_NAME,
    description="API for EU AI Act compliance management - helping startups navigate AI regulations",
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc"
)

# Configure CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include API routes
app.include_router(api_router, prefix=settings.API_V1_PREFIX)


@app.on_event("startup")
def on_startup() -> None:
    """Ensure the schema exists.

    Creating tables at startup keeps `docker compose up` a one-liner. If the
    database is not reachable yet the app still boots so `/health` can report
    the problem instead of crash-looping.
    """
    try:
        init_db()
    except SQLAlchemyError as exc:
        logger.error("Database initialisation failed: %s", exc)


@app.get("/")
def root():
    return {
        "message": "EU AI Act Compliance Tool API",
        "docs": "/docs",
        "version": settings.APP_VERSION
    }


@app.get("/health")
def health_check():
    from app.core.database import engine

    database_ok = True
    try:
        with engine.connect():
            pass
    except SQLAlchemyError:
        database_ok = False

    return {
        "status": "healthy" if database_ok else "degraded",
        "database": "up" if database_ok else "down",
        "version": settings.APP_VERSION,
        "billing_enabled": settings.stripe_enabled,
    }
