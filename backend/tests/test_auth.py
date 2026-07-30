from tests.conftest import DEFAULT_CREDENTIALS, register_and_login


def test_register_returns_the_created_user(client):
    response = client.post("/api/v1/auth/register", json=DEFAULT_CREDENTIALS)

    assert response.status_code == 201
    body = response.json()
    assert body["email"] == DEFAULT_CREDENTIALS["email"]
    assert body["subscription_tier"] == "free"
    assert "hashed_password" not in body


def test_register_rejects_a_duplicate_email(client):
    client.post("/api/v1/auth/register", json=DEFAULT_CREDENTIALS)
    response = client.post("/api/v1/auth/register", json=DEFAULT_CREDENTIALS)

    assert response.status_code == 400
    assert response.json()["detail"] == "Email already registered"


def test_register_rejects_a_short_password(client):
    response = client.post(
        "/api/v1/auth/register",
        json={**DEFAULT_CREDENTIALS, "password": "short"},
    )

    assert response.status_code == 422


def test_login_rejects_a_wrong_password(client):
    client.post("/api/v1/auth/register", json=DEFAULT_CREDENTIALS)

    response = client.post(
        "/api/v1/auth/login",
        data={"username": DEFAULT_CREDENTIALS["email"], "password": "wrong-password"},
    )

    assert response.status_code == 401


def test_me_requires_a_token(client):
    assert client.get("/api/v1/auth/me").status_code == 401


def test_me_rejects_a_malformed_token(client):
    response = client.get(
        "/api/v1/auth/me", headers={"Authorization": "Bearer not-a-jwt"}
    )

    assert response.status_code == 401


def test_me_returns_the_authenticated_user(client, auth_headers):
    response = client.get("/api/v1/auth/me", headers=auth_headers)

    assert response.status_code == 200
    assert response.json()["company_name"] == DEFAULT_CREDENTIALS["company_name"]


def test_profile_can_be_updated(client, auth_headers):
    response = client.patch(
        "/api/v1/auth/me",
        json={"company_name": "HR Tech Labs BV"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["company_name"] == "HR Tech Labs BV"


def test_users_cannot_see_each_others_systems(client, auth_headers):
    client.post("/api/v1/ai-systems/", json={"name": "Mine"}, headers=auth_headers)

    other = register_and_login(client, email="other@example.com")
    assert client.get("/api/v1/ai-systems/", headers=other).json() == []
    assert client.get("/api/v1/ai-systems/1", headers=other).status_code == 404
