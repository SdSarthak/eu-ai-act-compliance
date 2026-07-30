from app.models.ai_system import RiskLevel
from app.models.compliance import ItemStatus
from app.services.compliance import compute_score, derive_status
from app.services.requirements import (
    HIGH_RISK_REQUIREMENTS,
    LIMITED_RISK_REQUIREMENTS,
    requirements_for,
)


class FakeItem:
    def __init__(self, status):
        self.status = status


class FakeSystem:
    def __init__(self, risk_level):
        self.risk_level = risk_level


def test_score_counts_in_progress_as_half():
    items = [
        FakeItem(ItemStatus.COMPLETED),
        FakeItem(ItemStatus.IN_PROGRESS),
        FakeItem(ItemStatus.PENDING),
        FakeItem(ItemStatus.PENDING),
    ]

    assert compute_score(items) == 38


def test_not_applicable_items_leave_the_denominator():
    items = [FakeItem(ItemStatus.COMPLETED), FakeItem(ItemStatus.NOT_APPLICABLE)]

    assert compute_score(items) == 100


def test_score_is_zero_without_a_checklist():
    assert compute_score([]) == 0


def test_prohibited_systems_are_never_marked_compliant():
    system = FakeSystem(RiskLevel.UNACCEPTABLE)

    assert derive_status(system, 100).value == "non_compliant"


def test_status_ladder():
    system = FakeSystem(RiskLevel.HIGH)

    assert derive_status(system, 0).value == "not_started"
    assert derive_status(system, 40).value == "in_progress"
    assert derive_status(system, 85).value == "under_review"
    assert derive_status(system, 100).value == "compliant"


def test_catalogue_sizes_match_the_risk_level():
    assert len(requirements_for(RiskLevel.HIGH)) == len(HIGH_RISK_REQUIREMENTS)
    assert len(requirements_for(RiskLevel.LIMITED)) == len(LIMITED_RISK_REQUIREMENTS)
    assert len(requirements_for(RiskLevel.HIGH, True)) > len(HIGH_RISK_REQUIREMENTS)


def test_requirement_codes_are_unique_within_a_catalogue():
    codes = [requirement.code for requirement in HIGH_RISK_REQUIREMENTS]

    assert len(codes) == len(set(codes))


# --- API surface ----------------------------------------------------------- #


def test_checklist_is_generated_on_first_access(client, auth_headers, ai_system):
    response = client.get(
        f"/api/v1/compliance/systems/{ai_system['id']}/checklist", headers=auth_headers
    )

    assert response.status_code == 200
    body = response.json()
    # An unclassified system falls back to the minimal-risk catalogue.
    assert body["total_items"] == len(requirements_for(RiskLevel.MINIMAL))
    assert body["compliance_score"] == 0


def test_classification_populates_the_high_risk_checklist(
    client, auth_headers, ai_system, hr_questionnaire
):
    client.post(
        f"/api/v1/classification/classify/{ai_system['id']}",
        json=hr_questionnaire,
        headers=auth_headers,
    )

    body = client.get(
        f"/api/v1/compliance/systems/{ai_system['id']}/checklist", headers=auth_headers
    ).json()

    assert body["risk_level"] == "high"
    assert body["total_items"] == len(HIGH_RISK_REQUIREMENTS)
    articles = {item["article"] for item in body["items"]}
    assert {"Article 9", "Article 10", "Article 14", "Article 49"} <= articles


def test_completing_items_raises_the_score(
    client, auth_headers, ai_system, hr_questionnaire
):
    system_id = ai_system["id"]
    client.post(
        f"/api/v1/classification/classify/{system_id}",
        json=hr_questionnaire,
        headers=auth_headers,
    )
    items = client.get(
        f"/api/v1/compliance/systems/{system_id}/checklist", headers=auth_headers
    ).json()["items"]

    for item in items:
        response = client.patch(
            f"/api/v1/compliance/items/{item['id']}",
            json={"status": "completed", "evidence_notes": "Signed off"},
            headers=auth_headers,
        )
        assert response.status_code == 200

    system = client.get(f"/api/v1/ai-systems/{system_id}", headers=auth_headers).json()
    assert system["compliance_score"] == 100
    assert system["compliance_status"] == "compliant"


def test_partial_progress_moves_the_score(
    client, auth_headers, ai_system, hr_questionnaire
):
    system_id = ai_system["id"]
    client.post(
        f"/api/v1/classification/classify/{system_id}",
        json=hr_questionnaire,
        headers=auth_headers,
    )
    items = client.get(
        f"/api/v1/compliance/systems/{system_id}/checklist", headers=auth_headers
    ).json()["items"]

    client.patch(
        f"/api/v1/compliance/items/{items[0]['id']}",
        json={"status": "in_progress"},
        headers=auth_headers,
    )

    body = client.get(
        f"/api/v1/compliance/systems/{system_id}/checklist", headers=auth_headers
    ).json()
    assert 0 < body["compliance_score"] < 100
    assert body["in_progress_items"] == 1


def test_reclassification_preserves_progress_on_shared_obligations(
    client, auth_headers, ai_system, hr_questionnaire
):
    system_id = ai_system["id"]
    client.post(
        f"/api/v1/classification/classify/{system_id}",
        json=hr_questionnaire,
        headers=auth_headers,
    )
    items = client.get(
        f"/api/v1/compliance/systems/{system_id}/checklist", headers=auth_headers
    ).json()["items"]
    literacy = next(item for item in items if item["article"] == "Article 4")

    client.patch(
        f"/api/v1/compliance/items/{literacy['id']}",
        json={"status": "completed"},
        headers=auth_headers,
    )

    # Re-classify as a plain chatbot: the Article 4 obligation still applies.
    client.post(
        f"/api/v1/classification/classify/{system_id}",
        json={"use_case_category": "customer_service", "interacts_with_humans": True},
        headers=auth_headers,
    )

    body = client.get(
        f"/api/v1/compliance/systems/{system_id}/checklist", headers=auth_headers
    ).json()
    assert body["risk_level"] == "limited"
    assert body["total_items"] == len(LIMITED_RISK_REQUIREMENTS)
    carried_over = next(item for item in body["items"] if item["article"] == "Article 4")
    assert carried_over["status"] == "completed"


def test_sync_endpoint_is_idempotent(client, auth_headers, ai_system):
    system_id = ai_system["id"]
    first = client.post(
        f"/api/v1/compliance/systems/{system_id}/checklist/sync", headers=auth_headers
    ).json()
    second = client.post(
        f"/api/v1/compliance/systems/{system_id}/checklist/sync", headers=auth_headers
    ).json()

    assert first["total_items"] == second["total_items"]
    assert [item["code"] for item in first["items"]] == [
        item["code"] for item in second["items"]
    ]


def test_items_of_other_users_are_not_reachable(client, auth_headers, ai_system):
    from tests.conftest import register_and_login

    items = client.get(
        f"/api/v1/compliance/systems/{ai_system['id']}/checklist", headers=auth_headers
    ).json()["items"]
    other = register_and_login(client, email="intruder@example.com")

    response = client.patch(
        f"/api/v1/compliance/items/{items[0]['id']}",
        json={"status": "completed"},
        headers=other,
    )

    assert response.status_code == 404


def test_overview_aggregates_the_portfolio(
    client, auth_headers, ai_system, hr_questionnaire
):
    client.post(
        f"/api/v1/classification/classify/{ai_system['id']}",
        json=hr_questionnaire,
        headers=auth_headers,
    )

    overview = client.get("/api/v1/compliance/overview", headers=auth_headers).json()

    assert overview["total_systems"] == 1
    assert overview["systems_by_risk_level"]["high"] == 1
    assert overview["unclassified_systems"] == 0
    assert overview["open_requirements"] == len(HIGH_RISK_REQUIREMENTS)
    assert overview["action_required"] == 1
