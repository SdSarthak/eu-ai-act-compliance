from fastapi import APIRouter
from app.api.v1 import auth, ai_systems, billing, compliance, documents, classification

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["Authentication"])
api_router.include_router(ai_systems.router, prefix="/ai-systems", tags=["AI Systems"])
api_router.include_router(classification.router, prefix="/classification", tags=["Risk Classification"])
api_router.include_router(compliance.router, prefix="/compliance", tags=["Compliance"])
api_router.include_router(documents.router, prefix="/documents", tags=["Documents"])
api_router.include_router(billing.router, prefix="/billing", tags=["Billing"])
