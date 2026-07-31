"""Subscription plans and Stripe integration.

The plan catalogue is plain Python so quota enforcement works with or without
Stripe credentials; only the checkout, portal and webhook calls need a
configured ``STRIPE_SECRET_KEY``.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional

import stripe
from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.ai_system import AISystem
from app.models.document import DocumentType
from app.models.user import SubscriptionTier, User

BASIC_DOCUMENT_TYPES = [
    DocumentType.TECHNICAL_DOCUMENTATION,
    DocumentType.RISK_ASSESSMENT,
    DocumentType.CONFORMITY_DECLARATION,
]


@dataclass(frozen=True)
class Plan:
    tier: SubscriptionTier
    name: str
    price_usd_month: int
    # None means unlimited
    ai_system_limit: Optional[int]
    # None means every document type
    document_types: Optional[List[DocumentType]]
    features: List[str] = field(default_factory=list)

    @property
    def stripe_price_id(self) -> str:
        return {
            SubscriptionTier.STARTER: settings.STRIPE_PRICE_STARTER,
            SubscriptionTier.GROWTH: settings.STRIPE_PRICE_GROWTH,
            SubscriptionTier.SCALE: settings.STRIPE_PRICE_SCALE,
        }.get(self.tier, "")

    def allows_document_type(self, document_type: DocumentType) -> bool:
        return self.document_types is None or document_type in self.document_types

    def as_dict(self) -> dict:
        return {
            "tier": self.tier.value,
            "name": self.name,
            "price_usd_month": self.price_usd_month,
            "ai_system_limit": self.ai_system_limit,
            "document_types": (
                [document_type.value for document_type in self.document_types]
                if self.document_types is not None
                else [document_type.value for document_type in DocumentType]
            ),
            "features": self.features,
            "purchasable": self.tier != SubscriptionTier.FREE,
        }


PLANS: Dict[SubscriptionTier, Plan] = {
    SubscriptionTier.FREE: Plan(
        tier=SubscriptionTier.FREE,
        name="Free",
        price_usd_month=0,
        ai_system_limit=1,
        document_types=[DocumentType.RISK_ASSESSMENT],
        features=[
            "1 AI system",
            "Unlimited risk classifications",
            "Risk assessment report",
            "Compliance checklist tracking",
        ],
    ),
    SubscriptionTier.STARTER: Plan(
        tier=SubscriptionTier.STARTER,
        name="Starter",
        price_usd_month=99,
        ai_system_limit=1,
        document_types=BASIC_DOCUMENT_TYPES,
        features=[
            "1 AI system",
            "Technical documentation, risk assessment and declaration of conformity",
            "PDF export",
            "Compliance checklist tracking",
        ],
    ),
    SubscriptionTier.GROWTH: Plan(
        tier=SubscriptionTier.GROWTH,
        name="Growth",
        price_usd_month=299,
        ai_system_limit=5,
        document_types=None,
        features=[
            "5 AI systems",
            "Every document type",
            "PDF export",
            "Compliance checklist tracking",
        ],
    ),
    SubscriptionTier.SCALE: Plan(
        tier=SubscriptionTier.SCALE,
        name="Scale",
        price_usd_month=499,
        ai_system_limit=None,
        document_types=None,
        features=[
            "Unlimited AI systems",
            "Every document type",
            "PDF export",
            "Priority support",
        ],
    ),
}


def get_plan(tier: SubscriptionTier) -> Plan:
    return PLANS.get(tier, PLANS[SubscriptionTier.FREE])


def plan_for_user(user: User) -> Plan:
    return get_plan(user.subscription_tier or SubscriptionTier.FREE)


def tier_for_price_id(price_id: str) -> Optional[SubscriptionTier]:
    """Reverse lookup used when handling Stripe webhooks."""
    if not price_id:
        return None
    for tier, plan in PLANS.items():
        if plan.stripe_price_id and plan.stripe_price_id == price_id:
            return tier
    return None


def system_count(db: Session, user: User) -> int:
    return db.query(AISystem).filter(AISystem.owner_id == user.id).count()


def ensure_system_quota(db: Session, user: User) -> None:
    """Raise 402 when the user's plan has no room for another AI system."""
    plan = plan_for_user(user)
    if plan.ai_system_limit is None:
        return
    if system_count(db, user) >= plan.ai_system_limit:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"The {plan.name} plan covers {plan.ai_system_limit} AI system(s). "
                "Upgrade your plan to register more."
            ),
        )


def ensure_document_type_allowed(user: User, document_type: DocumentType) -> None:
    """Raise 402 when the document type is not part of the user's plan."""
    plan = plan_for_user(user)
    if not plan.allows_document_type(document_type):
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=(
                f"{document_type.value.replace('_', ' ').title()} is not included "
                f"in the {plan.name} plan. Upgrade to generate it."
            ),
        )


def subscription_summary(db: Session, user: User) -> dict:
    plan = plan_for_user(user)
    used = system_count(db, user)
    return {
        "tier": plan.tier.value,
        "plan_name": plan.name,
        "price_usd_month": plan.price_usd_month,
        "ai_system_limit": plan.ai_system_limit,
        "ai_systems_used": used,
        "ai_systems_remaining": (
            None if plan.ai_system_limit is None else max(plan.ai_system_limit - used, 0)
        ),
        "document_types": plan.as_dict()["document_types"],
        "stripe_customer_id": user.stripe_customer_id,
        "stripe_subscription_id": user.stripe_subscription_id,
        "billing_enabled": settings.stripe_enabled,
    }


def _require_stripe() -> None:
    if not settings.stripe_enabled:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Billing is not configured on this deployment.",
        )
    stripe.api_key = settings.STRIPE_SECRET_KEY


def create_checkout_session(db: Session, user: User, tier: SubscriptionTier) -> dict:
    """Start a Stripe Checkout session for a paid plan."""
    _require_stripe()

    plan = get_plan(tier)
    if plan.tier == SubscriptionTier.FREE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="The free plan does not require checkout.",
        )
    if not plan.stripe_price_id:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"No Stripe price is configured for the {plan.name} plan.",
        )

    try:
        if not user.stripe_customer_id:
            customer = stripe.Customer.create(
                email=user.email,
                name=user.full_name or user.company_name or user.email,
                metadata={"user_id": str(user.id)},
            )
            user.stripe_customer_id = customer["id"]
            db.flush()

        session = stripe.checkout.Session.create(
            mode="subscription",
            customer=user.stripe_customer_id,
            line_items=[{"price": plan.stripe_price_id, "quantity": 1}],
            success_url=f"{settings.FRONTEND_URL}/billing?checkout=success",
            cancel_url=f"{settings.FRONTEND_URL}/billing?checkout=cancelled",
            client_reference_id=str(user.id),
            metadata={"user_id": str(user.id), "tier": plan.tier.value},
        )
    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe rejected the request: {exc.user_message or 'unknown error'}",
        )

    db.commit()
    return {"checkout_url": session["url"], "session_id": session["id"]}


def create_portal_session(user: User) -> dict:
    """Open the Stripe customer portal so a user can manage their subscription."""
    _require_stripe()

    if not user.stripe_customer_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This account has no Stripe customer yet.",
        )

    try:
        session = stripe.billing_portal.Session.create(
            customer=user.stripe_customer_id,
            return_url=f"{settings.FRONTEND_URL}/billing",
        )
    except stripe.error.StripeError as exc:
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail=f"Stripe rejected the request: {exc.user_message or 'unknown error'}",
        )

    return {"portal_url": session["url"]}


def verify_webhook(payload: bytes, signature: Optional[str]) -> dict:
    """Verify and parse a Stripe webhook payload."""
    if not settings.STRIPE_WEBHOOK_SECRET:
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Webhook handling is not configured on this deployment.",
        )
    if not signature:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Missing Stripe-Signature header.",
        )

    try:
        return stripe.Webhook.construct_event(
            payload, signature, settings.STRIPE_WEBHOOK_SECRET
        )
    except (ValueError, stripe.error.SignatureVerificationError):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid Stripe webhook signature.",
        )


# SQLite and a 64-bit BIGINT both stop here; anything larger is not a row id.
_MAX_ROW_ID = 2 ** 63 - 1


def _coerce_user_id(raw: object) -> Optional[int]:
    """Read a user id out of Stripe metadata without trusting its shape.

    Metadata is free-form text that Stripe echoes back verbatim, so a stale or
    hand-edited value can be non-numeric or absurdly large. Both used to raise
    (``ValueError`` / ``OverflowError``) out of the webhook handler as a 500,
    which makes Stripe retry an event that can never succeed.
    """
    if raw is None or isinstance(raw, bool):
        return None
    try:
        value = int(str(raw).strip())
    except (TypeError, ValueError):
        return None
    if value <= 0 or value > _MAX_ROW_ID:
        return None
    return value


def _user_for_event(db: Session, obj: dict) -> Optional[User]:
    metadata = obj.get("metadata") or {}
    user_id = _coerce_user_id(
        metadata.get("user_id") or obj.get("client_reference_id")
    )
    if user_id is not None:
        user = db.query(User).filter(User.id == user_id).first()
        if user:
            return user

    customer_id = obj.get("customer")
    if customer_id:
        return (
            db.query(User).filter(User.stripe_customer_id == customer_id).first()
        )
    return None


def _tier_from_subscription(subscription: dict) -> Optional[SubscriptionTier]:
    items = (subscription.get("items") or {}).get("data") or []
    for item in items:
        price_id = (item.get("price") or {}).get("id")
        tier = tier_for_price_id(price_id)
        if tier:
            return tier
    metadata_tier = (subscription.get("metadata") or {}).get("tier")
    if metadata_tier:
        try:
            return SubscriptionTier(metadata_tier)
        except ValueError:
            return None
    return None


def apply_webhook_event(db: Session, event: dict) -> dict:
    """Update the local subscription state from a Stripe event.

    Returns a small summary so the endpoint can report what it did; unknown
    event types are acknowledged and ignored, which is what Stripe expects.
    """
    event_type = event.get("type", "")
    data = event.get("data") or {}
    obj = (data.get("object") if isinstance(data, dict) else None) or {}
    if not isinstance(obj, dict):
        # A malformed payload must be acknowledged, not crash the endpoint.
        return {"handled": False, "reason": "malformed event payload"}

    if event_type == "checkout.session.completed":
        user = _user_for_event(db, obj)
        if not user:
            return {"handled": False, "reason": "unknown user"}
        tier_value = (obj.get("metadata") or {}).get("tier")
        if tier_value:
            try:
                user.subscription_tier = SubscriptionTier(tier_value)
            except ValueError:
                pass
        user.stripe_customer_id = obj.get("customer") or user.stripe_customer_id
        user.stripe_subscription_id = obj.get("subscription") or user.stripe_subscription_id
        db.commit()
        return {"handled": True, "tier": user.subscription_tier.value}

    if event_type in ("customer.subscription.created", "customer.subscription.updated"):
        user = _user_for_event(db, obj)
        if not user:
            return {"handled": False, "reason": "unknown user"}
        status_value = obj.get("status")
        if status_value in ("canceled", "unpaid", "incomplete_expired"):
            user.subscription_tier = SubscriptionTier.FREE
            user.stripe_subscription_id = None
        else:
            tier = _tier_from_subscription(obj)
            if tier:
                user.subscription_tier = tier
            user.stripe_subscription_id = obj.get("id")
        db.commit()
        return {"handled": True, "tier": user.subscription_tier.value}

    if event_type == "customer.subscription.deleted":
        user = _user_for_event(db, obj)
        if not user:
            return {"handled": False, "reason": "unknown user"}
        user.subscription_tier = SubscriptionTier.FREE
        user.stripe_subscription_id = None
        db.commit()
        return {"handled": True, "tier": user.subscription_tier.value}

    return {"handled": False, "reason": f"ignored event type {event_type}"}
