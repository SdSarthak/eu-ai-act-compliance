import pytest

from app.models.ai_system import RiskLevel
from app.schemas.ai_system import RiskClassificationRequest
from app.services.classification import classify_risk


def build(**overrides) -> RiskClassificationRequest:
    return RiskClassificationRequest(**{"use_case_category": "other", **overrides})


@pytest.mark.parametrize(
    "field",
    [
        "social_scoring",
        "subliminal_manipulation",
        "exploits_vulnerabilities",
        "realtime_remote_biometric_id",
        "predictive_policing_profiling",
        "untargeted_facial_scraping",
        "emotion_recognition_workplace",
        "biometric_categorization_sensitive",
    ],
)
def test_article_5_practices_are_unacceptable(field):
    result = classify_risk(build(**{field: True}))

    assert result.risk_level == RiskLevel.UNACCEPTABLE
    assert result.prohibited is True
    assert result.confidence >= 0.95
    assert any("Article 5" in article for article in result.applicable_articles)


def test_prohibition_overrides_every_other_signal():
    result = classify_risk(
        build(social_scoring=True, hr_recruitment_screening=True, interacts_with_humans=True)
    )

    assert result.risk_level == RiskLevel.UNACCEPTABLE


@pytest.mark.parametrize(
    "field,expected_area",
    [
        ("hr_recruitment_screening", "Recruitment and candidate selection"),
        ("hr_promotion_termination", "Employment decisions and worker management"),
        ("credit_worthiness", "Creditworthiness assessment"),
        ("insurance_risk_assessment", "Life and health insurance pricing"),
        ("law_enforcement", "Law enforcement"),
        ("border_control", "Migration, asylum and border control"),
        ("justice_system", "Administration of justice"),
        ("democratic_processes", "Democratic processes"),
        ("critical_infrastructure", "Critical infrastructure"),
        ("education_access_or_evaluation", "Education and vocational training"),
        ("essential_services_access", "Access to essential public services"),
    ],
)
def test_annex_iii_areas_are_high_risk(field, expected_area):
    result = classify_risk(build(**{field: True}))

    assert result.risk_level == RiskLevel.HIGH
    assert expected_area in result.annex_iii_areas


def test_cv_screening_is_high_risk_with_the_full_requirement_set():
    result = classify_risk(
        build(
            use_case_category="hr_recruitment",
            hr_recruitment_screening=True,
            affects_fundamental_rights=True,
        )
    )

    assert result.risk_level == RiskLevel.HIGH
    assert result.confidence >= 0.9
    assert any("Article 9" in requirement for requirement in result.requirements)
    assert any("Article 14" in requirement for requirement in result.requirements)
    assert any("Article 49" in requirement for requirement in result.requirements)


def test_safety_component_is_high_risk_without_an_annex_area():
    result = classify_risk(build(is_safety_component=True, interacts_with_humans=False))

    assert result.risk_level == RiskLevel.HIGH
    assert "Article 6(1)" in result.applicable_articles


def test_fundamental_rights_alone_is_high_risk_but_low_confidence():
    result = classify_risk(
        build(affects_fundamental_rights=True, interacts_with_humans=False)
    )

    assert result.risk_level == RiskLevel.HIGH
    assert result.confidence < 0.7


def test_article_6_3_derogation_downgrades_a_narrow_task():
    result = classify_risk(
        build(
            hr_recruitment_screening=True,
            purely_preparatory_task=True,
            human_reviews_every_decision=True,
            interacts_with_humans=True,
        )
    )

    assert result.risk_level == RiskLevel.LIMITED
    assert "Article 6(3)" in result.applicable_articles
    assert result.confidence < 0.7


def test_derogation_does_not_apply_to_biometric_systems():
    result = classify_risk(
        build(
            uses_biometric_data=True,
            purely_preparatory_task=True,
            human_reviews_every_decision=True,
        )
    )

    assert result.risk_level == RiskLevel.HIGH


def test_chatbot_is_limited_risk():
    result = classify_risk(build(interacts_with_humans=True))

    assert result.risk_level == RiskLevel.LIMITED
    assert any("Article 50" in article for article in result.applicable_articles)
    assert any("Article 50(1)" in requirement for requirement in result.requirements)


def test_synthetic_content_is_limited_risk():
    result = classify_risk(
        build(interacts_with_humans=False, generates_synthetic_content=True)
    )

    assert result.risk_level == RiskLevel.LIMITED


def test_spam_filter_is_minimal_risk():
    result = classify_risk(
        build(interacts_with_humans=False, makes_automated_decisions=True)
    )

    assert result.risk_level == RiskLevel.MINIMAL
    assert result.annex_iii_areas == []


def test_high_risk_systems_also_carry_article_50_duties():
    result = classify_risk(
        build(hr_recruitment_screening=True, interacts_with_humans=True)
    )

    assert result.risk_level == RiskLevel.HIGH
    assert "Article 50(1)" in result.applicable_articles


def test_general_purpose_models_add_chapter_v_obligations():
    result = classify_risk(build(is_general_purpose_model=True))

    assert any("Article 53" in requirement for requirement in result.requirements)


def test_confidence_is_always_a_probability():
    result = classify_risk(build())

    assert 0.0 < result.confidence <= 1.0


# --- API surface ----------------------------------------------------------- #


def test_classify_endpoint_requires_auth(client):
    response = client.post(
        "/api/v1/classification/classify", json={"use_case_category": "other"}
    )

    assert response.status_code == 401


def test_classify_endpoint_does_not_persist(client, auth_headers, ai_system):
    client.post(
        "/api/v1/classification/classify",
        json={"use_case_category": "hr_recruitment", "hr_recruitment_screening": True},
        headers=auth_headers,
    )

    stored = client.get(f"/api/v1/ai-systems/{ai_system['id']}", headers=auth_headers)
    assert stored.json()["risk_level"] is None


def test_classify_and_save_updates_the_system(
    client, auth_headers, ai_system, hr_questionnaire
):
    response = client.post(
        f"/api/v1/classification/classify/{ai_system['id']}",
        json=hr_questionnaire,
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert response.json()["risk_level"] == "high"

    stored = client.get(
        f"/api/v1/ai-systems/{ai_system['id']}", headers=auth_headers
    ).json()
    assert stored["risk_level"] == "high"
    assert stored["requirements_total"] > 0
    assert stored["questionnaire_responses"]["hr_recruitment_screening"] is True


def test_classify_and_save_records_an_assessment(
    client, auth_headers, ai_system, hr_questionnaire
):
    client.post(
        f"/api/v1/classification/classify/{ai_system['id']}",
        json=hr_questionnaire,
        headers=auth_headers,
    )

    assessments = client.get(
        f"/api/v1/classification/assessments/{ai_system['id']}", headers=auth_headers
    ).json()

    assert len(assessments) == 1
    assert assessments[0]["risk_level"] == "high"
    assert assessments[0]["findings"][0]["confidence"] > 0.5


def test_classify_and_save_404s_for_an_unknown_system(client, auth_headers):
    response = client.post(
        "/api/v1/classification/classify/999",
        json={"use_case_category": "other"},
        headers=auth_headers,
    )

    assert response.status_code == 404
