"""Shared test fixtures.

The environment is configured before any application module is imported so the
settings singleton picks up a throwaway SQLite database and storage directory.
"""

import os
import shutil
import tempfile
from pathlib import Path

import pytest

TEST_DIR = Path(tempfile.mkdtemp(prefix="compliance-tests-"))

os.environ["DATABASE_URL"] = f"sqlite:///{(TEST_DIR / 'test.db').as_posix()}"
os.environ["DOCUMENT_STORAGE_DIR"] = str(TEST_DIR / "documents")
os.environ["SECRET_KEY"] = "test-secret-key"
os.environ["STRIPE_SECRET_KEY"] = ""
os.environ["STRIPE_WEBHOOK_SECRET"] = ""

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import Base, SessionLocal, engine  # noqa: E402
from app.main import app  # noqa: E402
from app.models.user import SubscriptionTier, User  # noqa: E402


def pytest_sessionfinish(session, exitstatus):
    shutil.rmtree(TEST_DIR, ignore_errors=True)


@pytest.fixture(autouse=True)
def fresh_database():
    """Every test starts from an empty schema."""
    Base.metadata.drop_all(bind=engine)
    Base.metadata.create_all(bind=engine)
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.close()


@pytest.fixture
def client():
    with TestClient(app) as test_client:
        yield test_client


DEFAULT_CREDENTIALS = {
    "email": "founder@hrtech.example",
    "password": "supersecret123",
    "full_name": "Ada Founder",
    "company_name": "HR Tech Labs",
}


def register_and_login(client: TestClient, **overrides) -> dict:
    """Create a user and return the Authorization header for it."""
    payload = {**DEFAULT_CREDENTIALS, **overrides}
    response = client.post("/api/v1/auth/register", json=payload)
    assert response.status_code == 201, response.text

    token_response = client.post(
        "/api/v1/auth/login",
        data={"username": payload["email"], "password": payload["password"]},
    )
    assert token_response.status_code == 200, token_response.text
    return {"Authorization": f"Bearer {token_response.json()['access_token']}"}


@pytest.fixture
def auth_headers(client):
    return register_and_login(client)


@pytest.fixture
def set_tier(db):
    """Move the test user onto another subscription tier."""

    def _set(tier: SubscriptionTier, email: str = DEFAULT_CREDENTIALS["email"]):
        user = db.query(User).filter(User.email == email).first()
        assert user is not None
        user.subscription_tier = tier
        db.commit()
        return user

    return _set


@pytest.fixture
def hr_questionnaire():
    """Answers describing a CV screening tool: the canonical high-risk case."""
    return {
        "use_case_category": "hr_recruitment",
        "hr_recruitment_screening": True,
        "affects_fundamental_rights": True,
        "makes_automated_decisions": True,
        "interacts_with_humans": False,
    }


@pytest.fixture
def ai_system(client, auth_headers):
    response = client.post(
        "/api/v1/ai-systems/",
        json={
            "name": "CV Screener",
            "description": "Ranks inbound applications for recruiter review.",
            "version": "2.1",
            "use_case": "CV Screening",
            "sector": "HR Tech",
        },
        headers=auth_headers,
    )
    assert response.status_code == 201, response.text
    return response.json()
