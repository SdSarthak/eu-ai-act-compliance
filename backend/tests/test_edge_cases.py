"""Boundary and failure-mode coverage for the paths a real deployment hits.

These are the cases that used to return a 500, silently create a duplicate
account, or leave a file behind on disk.
"""

from pathlib import Path

import pytest

from app.models.document import Document
from app.models.user import SubscriptionTier, User
from app.services import billing as billing_service
from app.services import documents as document_service


@pytest.fixture
def classified_system(client, auth_headers, ai_system, hr_questionnaire):
    client.post(
        f"/api/v1/classification/classify/{ai_system['id']}",
        json=hr_questionnaire,
        headers=auth_headers,
    )
    return ai_system


# --- Email identity -------------------------------------------------------- #


def test_registration_is_case_insensitive_about_the_email(client):
    first = client.post(
        "/api/v1/auth/register",
        json={"email": "Ada@Example.COM", "password": "supersecret123"},
    )
    assert first.status_code == 201, first.text
    assert first.json()["email"] == "ada@example.com"

    duplicate = client.post(
        "/api/v1/auth/register",
        json={"email": "ada@example.com", "password": "supersecret123"},
    )
    assert duplicate.status_code == 400
    assert duplicate.json()["detail"] == "Email already registered"


def test_login_accepts_the_email_in_any_casing(client):
    client.post(
        "/api/v1/auth/register",
        json={"email": "ada@example.com", "password": "supersecret123"},
    )

    response = client.post(
        "/api/v1/auth/login",
        data={"username": "  ADA@Example.com ", "password": "supersecret123"},
    )

    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


def test_a_password_keeps_its_surrounding_whitespace(client):
    """Stripping the password would silently change the stored credential."""
    password = "  pass word  "
    client.post(
        "/api/v1/auth/register",
        json={"email": "spaced@example.com", "password": password},
    )

    assert (
        client.post(
            "/api/v1/auth/login",
            data={"username": "spaced@example.com", "password": password},
        ).status_code
        == 200
    )
    assert (
        client.post(
            "/api/v1/auth/login",
            data={"username": "spaced@example.com", "password": password.strip()},
        ).status_code
        == 401
    )


# --- Input bounds at the API boundary -------------------------------------- #


def test_document_title_longer_than_the_column_is_rejected(client, auth_headers):
    response = client.post(
        "/api/v1/documents/",
        json={"title": "T" * 256, "document_type": "risk_assessment"},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_document_title_cannot_be_blank(client, auth_headers):
    for title in ("", "   ", "\t\n"):
        response = client.post(
            "/api/v1/documents/",
            json={"title": title, "document_type": "risk_assessment"},
            headers=auth_headers,
        )
        assert response.status_code == 422, title


def test_document_title_is_stored_stripped(client, auth_headers):
    response = client.post(
        "/api/v1/documents/",
        json={"title": "  Policy  ", "document_type": "risk_assessment"},
        headers=auth_headers,
    )

    assert response.status_code == 201, response.text
    assert response.json()["title"] == "Policy"


def test_ai_system_name_cannot_be_whitespace_only(client, auth_headers):
    response = client.post(
        "/api/v1/ai-systems/", json={"name": "   "}, headers=auth_headers
    )

    assert response.status_code == 422


@pytest.mark.parametrize("system_id", [0, -1])
def test_generate_rejects_a_non_positive_system_id(client, auth_headers, system_id):
    response = client.post(
        "/api/v1/documents/generate",
        json={"document_type": "risk_assessment", "ai_system_id": system_id},
        headers=auth_headers,
    )

    assert response.status_code == 422


def test_use_case_category_is_bounded(client, auth_headers):
    response = client.post(
        "/api/v1/classification/classify",
        json={"use_case_category": "x" * 101},
        headers=auth_headers,
    )

    assert response.status_code == 422


# --- Stripe webhook payloads we do not control ----------------------------- #


def _checkout_event(obj: dict) -> dict:
    return {"type": "checkout.session.completed", "data": {"object": obj}}


def test_webhook_ignores_a_non_numeric_user_id(db):
    result = billing_service.apply_webhook_event(
        db, _checkout_event({"metadata": {"user_id": "not-a-number", "tier": "growth"}})
    )

    assert result == {"handled": False, "reason": "unknown user"}


def test_webhook_ignores_an_out_of_range_user_id(db):
    result = billing_service.apply_webhook_event(
        db, _checkout_event({"client_reference_id": "9" * 40})
    )

    assert result == {"handled": False, "reason": "unknown user"}


def test_webhook_tolerates_a_malformed_payload(db):
    result = billing_service.apply_webhook_event(
        db, {"type": "checkout.session.completed", "data": {"object": ["not", "a", "dict"]}}
    )

    assert result["handled"] is False


def test_webhook_still_resolves_a_valid_numeric_user_id(db, client, auth_headers):
    user = db.query(User).first()

    result = billing_service.apply_webhook_event(
        db,
        _checkout_event(
            {"metadata": {"user_id": str(user.id), "tier": "growth"}, "customer": "cus_1"}
        ),
    )

    assert result == {"handled": True, "tier": "growth"}
    db.refresh(user)
    assert user.subscription_tier == SubscriptionTier.GROWTH


# --- PDF rendering: partial writes, replacement, cleanup ------------------- #


class _StubDocument:
    """Just enough of a Document for the renderer."""

    def __init__(self, doc_id=1, version="1.0", title="Stub", content="# Hi\n\nBody."):
        self.id = doc_id
        self.version = version
        self.title = title
        self.content = content


def test_a_failed_render_leaves_no_partial_file(tmp_path, monkeypatch):
    class Exploding:
        def __init__(self, *args, **kwargs):
            pass

        def build(self, story):
            raise RuntimeError("reportlab blew up")

    monkeypatch.setattr(document_service, "SimpleDocTemplate", Exploding)

    with pytest.raises(RuntimeError):
        document_service.export_pdf(_StubDocument(), output_dir=str(tmp_path))

    assert list(tmp_path.iterdir()) == []


def test_re_export_replaces_the_previous_render(tmp_path):
    document = _StubDocument()

    first = document_service.export_pdf(document, output_dir=str(tmp_path))
    document.content = "# Different\n\nMuch longer body.\n\n- one\n- two\n"
    second = document_service.export_pdf(document, output_dir=str(tmp_path))

    assert first == second
    assert [p.name for p in tmp_path.iterdir()] == [Path(first).name]
    assert Path(first).read_bytes().startswith(b"%PDF")


def test_the_pdf_filename_never_contains_a_path_separator(tmp_path):
    path = document_service.export_pdf(
        _StubDocument(version="../../etc/passwd"), output_dir=str(tmp_path)
    )

    assert Path(path).parent == tmp_path
    assert Path(path).name == "document-1-v.._.._etc_passwd.pdf"


def test_pdf_download_fails_cleanly_when_rendering_breaks(
    client, auth_headers, db, classified_system, monkeypatch
):
    document = client.post(
        "/api/v1/documents/generate",
        json={"document_type": "risk_assessment", "ai_system_id": classified_system["id"]},
        headers=auth_headers,
    ).json()

    def boom(*args, **kwargs):
        raise RuntimeError("reportlab blew up")

    monkeypatch.setattr(document_service, "export_pdf", boom)

    response = client.get(
        f"/api/v1/documents/{document['id']}/pdf", headers=auth_headers
    )

    assert response.status_code == 500
    assert response.json()["detail"] == "The document could not be rendered to PDF."
    stored = db.query(Document).filter(Document.id == document["id"]).first()
    assert stored.file_path is None


def test_content_disposition_survives_a_hostile_title(client, auth_headers):
    document = client.post(
        "/api/v1/documents/",
        json={
            "title": 'quarterly/report\\v2 "final"',
            "document_type": "risk_assessment",
            "content": "# Report\n\nBody.",
        },
        headers=auth_headers,
    ).json()

    response = client.get(
        f"/api/v1/documents/{document['id']}/pdf", headers=auth_headers
    )

    assert response.status_code == 200
    disposition = response.headers["content-disposition"]
    # Path separators and quotes are replaced, not merely percent-encoded.
    assert "quarterly-report-v2%20-final-.pdf" in disposition
    assert "%5C" not in disposition and "%22" not in disposition


def test_deleting_a_document_whose_pdf_is_already_gone(
    client, auth_headers, db, classified_system
):
    document = client.post(
        "/api/v1/documents/generate",
        json={"document_type": "risk_assessment", "ai_system_id": classified_system["id"]},
        headers=auth_headers,
    ).json()
    client.get(f"/api/v1/documents/{document['id']}/pdf", headers=auth_headers)

    stored = db.query(Document).filter(Document.id == document["id"]).first()
    Path(stored.file_path).unlink()

    response = client.delete(
        f"/api/v1/documents/{document['id']}", headers=auth_headers
    )

    assert response.status_code == 204
    assert db.query(Document).filter(Document.id == document["id"]).first() is None


def test_editing_content_removes_the_orphaned_pdf(
    client, auth_headers, db, classified_system
):
    document = client.post(
        "/api/v1/documents/generate",
        json={"document_type": "risk_assessment", "ai_system_id": classified_system["id"]},
        headers=auth_headers,
    ).json()
    client.get(f"/api/v1/documents/{document['id']}/pdf", headers=auth_headers)
    rendered = Path(
        db.query(Document).filter(Document.id == document["id"]).first().file_path
    )
    assert rendered.exists()

    client.patch(
        f"/api/v1/documents/{document['id']}",
        json={"content": "# Rewritten\n\nBody."},
        headers=auth_headers,
    )

    assert not rendered.exists()


def test_deleting_a_system_removes_its_rendered_pdfs(
    client, auth_headers, db, classified_system
):
    document = client.post(
        "/api/v1/documents/generate",
        json={"document_type": "risk_assessment", "ai_system_id": classified_system["id"]},
        headers=auth_headers,
    ).json()
    client.get(f"/api/v1/documents/{document['id']}/pdf", headers=auth_headers)
    rendered = Path(
        db.query(Document).filter(Document.id == document["id"]).first().file_path
    )
    assert rendered.exists()

    response = client.delete(
        f"/api/v1/ai-systems/{classified_system['id']}", headers=auth_headers
    )

    assert response.status_code == 204
    assert not rendered.exists()


def test_remove_pdf_is_a_noop_for_a_missing_path(tmp_path):
    document_service.remove_pdf(None)
    document_service.remove_pdf("")
    document_service.remove_pdf(str(tmp_path / "never-existed.pdf"))
