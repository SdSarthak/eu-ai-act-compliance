from typing import List

from fastapi import APIRouter, Depends, Header, Request
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.billing import (
    CheckoutRequest,
    CheckoutResponse,
    PlanResponse,
    PortalResponse,
    SubscriptionResponse,
)
from app.services import billing as billing_service

router = APIRouter()


@router.get("/plans", response_model=List[PlanResponse])
def list_plans():
    """The subscription catalogue. Public so it can drive a pricing page."""
    return [plan.as_dict() for plan in billing_service.PLANS.values()]


@router.get("/subscription", response_model=SubscriptionResponse)
def get_subscription(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """The caller's plan, quota usage and Stripe linkage."""
    return billing_service.subscription_summary(db, current_user)


@router.post("/checkout", response_model=CheckoutResponse)
def create_checkout(
    payload: CheckoutRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Create a Stripe Checkout session for a paid plan."""
    return billing_service.create_checkout_session(db, current_user, payload.tier)


@router.post("/portal", response_model=PortalResponse)
def create_portal(current_user: User = Depends(get_current_user)):
    """Open the Stripe customer portal for the caller."""
    return billing_service.create_portal_session(current_user)


@router.post("/webhook")
async def stripe_webhook(
    request: Request,
    stripe_signature: str = Header(default=None, alias="Stripe-Signature"),
    db: Session = Depends(get_db),
):
    """Receive subscription lifecycle events from Stripe.

    Unauthenticated by design: the request is trusted only after the signature
    has been verified against ``STRIPE_WEBHOOK_SECRET``.
    """
    payload = await request.body()
    event = billing_service.verify_webhook(payload, stripe_signature)
    return billing_service.apply_webhook_event(db, event)
