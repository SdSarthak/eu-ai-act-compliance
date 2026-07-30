import pytest

from app.models.document import DocumentType
from app.models.user import SubscriptionTier
from app.services.documents import TEMPLATES, markdown_to_story, next_version, _styles


@pytest.fixture
def classified_system(client, auth_headers, ai_system, hr_questionnaire):
    client.post(
        f"/api/v1/classification/classify/{ai_system['id']}",
        json=hr_questionnaire,
        headers=auth_headers,
    )
    return ai_system


def test_every_document_type_has_a_template():
    assert set(TEMPLATES) == set(DocumentType)


@pytest.mark.parametrize("document_type", list(DocumentType))
def test_all_templates_render_without_leftover_placeholders(
    client, auth_headers, classified_system, set_tier, document_type
):
    set_tier(SubscriptionTier.GROWTH)

    response = client.post(
        "/api/v1/documents/generate",
        json={
            "document_type": document_type.value,
            "ai_system_id": classified_system["id"],
        },
        headers=auth_headers,
    )

    assert response.status_code == 200, response.text
    content = response.json()["content"]
    assert "$" not in content
    assert "CV Screener" in content
    assert content.startswith("# ")


def test_generated_document_reflects_the_classification(
    client, auth_headers, classified_system, set_tier
):
    set_tier(SubscriptionTier.GROWTH)

    content = client.post(
        "/api/v1/documents/generate",
        json={
            "document_type": "risk_assessment",
            "ai_system_id": classified_system["id"],
        },
        headers=auth_headers,
    ).json()["content"]

    assert "High risk" in content
    assert "Annex III, point 4(a)" in content
    assert "HR Tech Labs" in content


def test_generated_document_includes_the_checklist_state(
    client, auth_headers, classified_system, set_tier
):
    set_tier(SubscriptionTier.GROWTH)
    items = client.get(
        f"/api/v1/compliance/systems/{classified_system['id']}/checklist",
        headers=auth_headers,
    ).json()["items"]
    client.patch(
        f"/api/v1/compliance/items/{items[0]['id']}",
        json={"status": "completed", "evidence_notes": "Training delivered in Q1"},
        headers=auth_headers,
    )

    content = client.post(
        "/api/v1/documents/generate",
        json={
            "document_type": "technical_documentation",
            "ai_system_id": classified_system["id"],
        },
        headers=auth_headers,
    ).json()["content"]

    assert "[x]" in content
    assert "Training delivered in Q1" in content


def test_free_plan_is_limited_to_the_risk_assessment(
    client, auth_headers, classified_system
):
    allowed = client.post(
        "/api/v1/documents/generate",
        json={
            "document_type": "risk_assessment",
            "ai_system_id": classified_system["id"],
        },
        headers=auth_headers,
    )
    blocked = client.post(
        "/api/v1/documents/generate",
        json={
            "document_type": "human_oversight_plan",
            "ai_system_id": classified_system["id"],
        },
        headers=auth_headers,
    )

    assert allowed.status_code == 200
    assert blocked.status_code == 402


def test_templates_endpoint_reports_availability(client, auth_headers):
    body = client.get("/api/v1/documents/templates", headers=auth_headers).json()

    available = {row["document_type"] for row in body if row["available"]}
    assert available == {"risk_assessment"}
    assert len(body) == len(DocumentType)


def test_generate_all_produces_the_whole_pack(
    client, auth_headers, classified_system, set_tier
):
    set_tier(SubscriptionTier.SCALE)

    response = client.post(
        f"/api/v1/documents/systems/{classified_system['id']}/generate-all",
        headers=auth_headers,
    )

    assert response.status_code == 200
    assert len(response.json()) == len(DocumentType)


def test_regenerating_bumps_the_version(client, auth_headers, classified_system):
    payload = {
        "document_type": "risk_assessment",
        "ai_system_id": classified_system["id"],
    }
    first = client.post("/api/v1/documents/generate", json=payload, headers=auth_headers)
    second = client.post("/api/v1/documents/generate", json=payload, headers=auth_headers)

    assert first.json()["version"] == "1.0"
    assert second.json()["version"] == "1.1"


def test_next_version_ignores_unparsable_versions():
    class Doc:
        def __init__(self, version):
            self.version = version

    assert next_version([]) == "1.0"
    assert next_version([Doc("1.0"), Doc("draft"), Doc(None)]) == "1.1"
    assert next_version([Doc("1.4")]) == "1.5"


def test_pdf_export_returns_a_pdf(client, auth_headers, classified_system):
    document = client.post(
        "/api/v1/documents/generate",
        json={
            "document_type": "risk_assessment",
            "ai_system_id": classified_system["id"],
        },
        headers=auth_headers,
    ).json()

    response = client.get(
        f"/api/v1/documents/{document['id']}/pdf", headers=auth_headers
    )

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert response.content.startswith(b"%PDF")


def test_editing_content_invalidates_the_cached_pdf(
    client, auth_headers, classified_system
):
    document = client.post(
        "/api/v1/documents/generate",
        json={
            "document_type": "risk_assessment",
            "ai_system_id": classified_system["id"],
        },
        headers=auth_headers,
    ).json()
    client.get(f"/api/v1/documents/{document['id']}/pdf", headers=auth_headers)

    updated = client.patch(
        f"/api/v1/documents/{document['id']}",
        json={"content": "# Revised\n\nManual edit.", "status": "reviewed"},
        headers=auth_headers,
    )

    assert updated.status_code == 200
    assert updated.json()["file_path"] is None
    assert updated.json()["status"] == "reviewed"

    regenerated = client.get(
        f"/api/v1/documents/{document['id']}/pdf", headers=auth_headers
    )
    assert regenerated.status_code == 200


def test_documents_can_be_filtered_by_system(client, auth_headers, classified_system):
    client.post(
        "/api/v1/documents/generate",
        json={
            "document_type": "risk_assessment",
            "ai_system_id": classified_system["id"],
        },
        headers=auth_headers,
    )

    matching = client.get(
        f"/api/v1/documents/?ai_system_id={classified_system['id']}", headers=auth_headers
    ).json()
    other = client.get("/api/v1/documents/?ai_system_id=999", headers=auth_headers).json()

    assert len(matching) == 1
    assert other == []


def test_generate_404s_for_an_unknown_system(client, auth_headers):
    response = client.post(
        "/api/v1/documents/generate",
        json={"document_type": "risk_assessment", "ai_system_id": 999},
        headers=auth_headers,
    )

    assert response.status_code == 404


def test_delete_removes_the_document(client, auth_headers, classified_system):
    document = client.post(
        "/api/v1/documents/generate",
        json={
            "document_type": "risk_assessment",
            "ai_system_id": classified_system["id"],
        },
        headers=auth_headers,
    ).json()

    assert (
        client.delete(
            f"/api/v1/documents/{document['id']}", headers=auth_headers
        ).status_code
        == 204
    )
    assert client.get("/api/v1/documents/", headers=auth_headers).json() == []


def test_markdown_conversion_handles_every_block_type():
    markdown = (
        "# Title\n"
        "## Section\n"
        "### Subsection\n"
        "Body text with **bold** and an <angle> bracket.\n"
        "\n"
        "- bullet one\n"
        "- bullet two\n"
        "\n"
        "1. step one\n"
        "2. step two\n"
        "\n"
        "---\n"
    )

    story = markdown_to_story(markdown, _styles())

    assert len(story) >= 7


def test_markdown_conversion_never_returns_an_empty_story():
    assert markdown_to_story("", _styles())
