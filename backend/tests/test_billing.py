from app.models.document import DocumentType
from app.models.user import SubscriptionTier, User
from app.services import billing


def test_plans_are_public(client):
    response = client.get("/api/v1/billing/plans")

    assert response.status_code == 200
    tiers = [plan["tier"] for plan in response.json()]
    assert tiers == ["free", "starter", "growth", "scale"]
    assert [plan["price_usd_month"] for plan in response.json()] == [0, 99, 299, 499]


def test_plan_prices_match_the_public_pricing():
    assert billing.get_plan(SubscriptionTier.STARTER).price_usd_month == 99
    assert billing.get_plan(SubscriptionTier.GROWTH).price_usd_month == 299
    assert billing.get_plan(SubscriptionTier.SCALE).price_usd_month == 499
    assert billing.get_plan(SubscriptionTier.SCALE).ai_system_limit is None


def test_document_type_gating_per_plan():
    free = billing.get_plan(SubscriptionTier.FREE)
    growth = billing.get_plan(SubscriptionTier.GROWTH)

    assert free.allows_document_type(DocumentType.RISK_ASSESSMENT)
    assert not free.allows_document_type(DocumentType.INCIDENT_REPORT)
    assert all(
        growth.allows_document_type(document_type) for document_type in DocumentType
    )


def test_subscription_summary_reports_quota(client, auth_headers, ai_system):
    body = client.get("/api/v1/billing/subscription", headers=auth_headers).json()

    assert body["tier"] == "free"
    assert body["ai_systems_used"] == 1
    assert body["ai_systems_remaining"] == 0
    assert body["billing_enabled"] is False


def test_subscription_requires_auth(client):
    assert client.get("/api/v1/billing/subscription").status_code == 401


def test_checkout_is_unavailable_without_stripe_credentials(client, auth_headers):
    response = client.post(
        "/api/v1/billing/checkout", json={"tier": "growth"}, headers=auth_headers
    )

    assert response.status_code == 503


def test_webhook_is_rejected_without_a_configured_secret(client):
    response = client.post("/api/v1/billing/webhook", content=b"{}")

    assert response.status_code == 503


def test_tier_lookup_by_price_id_returns_none_when_unconfigured():
    assert billing.tier_for_price_id("") is None
    assert billing.tier_for_price_id("price_does_not_exist") is None


def test_checkout_completed_event_upgrades_the_user(db, client, auth_headers):
    user = db.query(User).first()

    result = billing.apply_webhook_event(
        db,
        {
            "type": "checkout.session.completed",
            "data": {
                "object": {
                    "customer": "cus_test_123",
                    "subscription": "sub_test_123",
                    "client_reference_id": str(user.id),
                    "metadata": {"user_id": str(user.id), "tier": "growth"},
                }
            },
        },
    )

    db.refresh(user)
    assert result["handled"] is True
    assert user.subscription_tier == SubscriptionTier.GROWTH
    assert user.stripe_customer_id == "cus_test_123"
    assert user.stripe_subscription_id == "sub_test_123"


def test_subscription_deleted_event_downgrades_to_free(db, client, auth_headers):
    user = db.query(User).first()
    user.subscription_tier = SubscriptionTier.SCALE
    user.stripe_customer_id = "cus_test_456"
    user.stripe_subscription_id = "sub_test_456"
    db.commit()

    billing.apply_webhook_event(
        db,
        {
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_test_456", "id": "sub_test_456"}},
        },
    )

    db.refresh(user)
    assert user.subscription_tier == SubscriptionTier.FREE
    assert user.stripe_subscription_id is None


def test_cancelled_subscription_update_downgrades_to_free(db, client, auth_headers):
    user = db.query(User).first()
    user.subscription_tier = SubscriptionTier.GROWTH
    user.stripe_customer_id = "cus_test_789"
    db.commit()

    billing.apply_webhook_event(
        db,
        {
            "type": "customer.subscription.updated",
            "data": {
                "object": {
                    "id": "sub_test_789",
                    "customer": "cus_test_789",
                    "status": "canceled",
                }
            },
        },
    )

    db.refresh(user)
    assert user.subscription_tier == SubscriptionTier.FREE


def test_unknown_event_types_are_acknowledged(db):
    result = billing.apply_webhook_event(db, {"type": "invoice.paid", "data": {}})

    assert result["handled"] is False


def test_events_for_unknown_customers_are_ignored(db):
    result = billing.apply_webhook_event(
        db,
        {
            "type": "customer.subscription.deleted",
            "data": {"object": {"customer": "cus_nobody"}},
        },
    )

    assert result == {"handled": False, "reason": "unknown user"}
