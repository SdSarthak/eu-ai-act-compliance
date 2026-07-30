from typing import List, Optional

from pydantic import BaseModel

from app.models.user import SubscriptionTier


class PlanResponse(BaseModel):
    tier: str
    name: str
    price_usd_month: int
    ai_system_limit: Optional[int]
    document_types: List[str]
    features: List[str]
    purchasable: bool


class SubscriptionResponse(BaseModel):
    tier: str
    plan_name: str
    price_usd_month: int
    ai_system_limit: Optional[int]
    ai_systems_used: int
    ai_systems_remaining: Optional[int]
    document_types: List[str]
    stripe_customer_id: Optional[str]
    stripe_subscription_id: Optional[str]
    billing_enabled: bool


class CheckoutRequest(BaseModel):
    tier: SubscriptionTier


class CheckoutResponse(BaseModel):
    checkout_url: str
    session_id: str


class PortalResponse(BaseModel):
    portal_url: str
