from app.models.user import SubscriptionTier


def test_create_and_list(client, auth_headers, ai_system):
    listed = client.get("/api/v1/ai-systems/", headers=auth_headers).json()

    assert [system["name"] for system in listed] == ["CV Screener"]
    assert ai_system["risk_level"] is None
    assert ai_system["compliance_score"] == 0


def test_get_returns_checklist_progress(client, auth_headers, ai_system):
    response = client.get(f"/api/v1/ai-systems/{ai_system['id']}", headers=auth_headers)

    assert response.status_code == 200
    body = response.json()
    assert body["requirements_total"] == 0
    assert body["requirements_completed"] == 0
    assert body["questionnaire_responses"] == {}


def test_update_changes_fields(client, auth_headers, ai_system):
    response = client.put(
        f"/api/v1/ai-systems/{ai_system['id']}",
        json={"description": "Now also ranks internal candidates.", "version": "3.0"},
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["version"] == "3.0"
    assert response.json()["name"] == "CV Screener"


def test_delete_removes_the_system_and_its_documents(
    client, auth_headers, ai_system, hr_questionnaire
):
    system_id = ai_system["id"]
    client.post(
        f"/api/v1/classification/classify/{system_id}",
        json=hr_questionnaire,
        headers=auth_headers,
    )
    client.post(
        "/api/v1/documents/generate",
        json={"document_type": "risk_assessment", "ai_system_id": system_id},
        headers=auth_headers,
    )

    assert (
        client.delete(f"/api/v1/ai-systems/{system_id}", headers=auth_headers).status_code
        == 204
    )
    assert client.get(f"/api/v1/ai-systems/{system_id}", headers=auth_headers).status_code == 404
    assert client.get("/api/v1/documents/", headers=auth_headers).json() == []


def test_free_plan_allows_one_system(client, auth_headers, ai_system):
    response = client.post(
        "/api/v1/ai-systems/", json={"name": "Second system"}, headers=auth_headers
    )

    assert response.status_code == 402
    assert "Upgrade" in response.json()["detail"]


def test_growth_plan_raises_the_quota(client, auth_headers, ai_system, set_tier):
    set_tier(SubscriptionTier.GROWTH)

    for index in range(4):
        response = client.post(
            "/api/v1/ai-systems/",
            json={"name": f"System {index}"},
            headers=auth_headers,
        )
        assert response.status_code == 201

    assert (
        client.post(
            "/api/v1/ai-systems/", json={"name": "Sixth"}, headers=auth_headers
        ).status_code
        == 402
    )


def test_scale_plan_is_unlimited(client, auth_headers, ai_system, set_tier):
    set_tier(SubscriptionTier.SCALE)

    for index in range(10):
        response = client.post(
            "/api/v1/ai-systems/",
            json={"name": f"System {index}"},
            headers=auth_headers,
        )
        assert response.status_code == 201


def test_name_is_required(client, auth_headers):
    assert (
        client.post("/api/v1/ai-systems/", json={"name": ""}, headers=auth_headers).status_code
        == 422
    )
