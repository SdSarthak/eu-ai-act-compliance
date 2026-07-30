from pathlib import Path as FilePath
from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, status
from fastapi.responses import FileResponse
from sqlalchemy.orm import Session

from app.api.deps import get_owned_document, get_owned_system
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ai_system import AISystem
from app.models.document import Document, DocumentType
from app.models.user import User
from app.schemas.document import (
    DocumentCreate,
    DocumentGenerateRequest,
    DocumentResponse,
    DocumentUpdate,
)
from app.services import billing
from app.services import documents as document_service

router = APIRouter()


@router.get("/templates")
def list_templates(current_user: User = Depends(get_current_user)):
    """The document types this account can generate."""
    plan = billing.plan_for_user(current_user)
    return [
        {
            "document_type": document_type.value,
            "label": document_type.value.replace("_", " ").title(),
            "available": plan.allows_document_type(document_type),
        }
        for document_type in DocumentType
        if document_type in document_service.TEMPLATES
    ]


@router.post("/", response_model=DocumentResponse, status_code=status.HTTP_201_CREATED)
def create_document(
    doc_data: DocumentCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a document by hand, for example to attach an existing policy."""
    if doc_data.ai_system_id is not None:
        owns_system = (
            db.query(AISystem)
            .filter(
                AISystem.id == doc_data.ai_system_id,
                AISystem.owner_id == current_user.id,
            )
            .first()
        )
        if not owns_system:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="AI system not found",
            )

    document = Document(
        owner_id=current_user.id,
        title=doc_data.title,
        document_type=doc_data.document_type,
        ai_system_id=doc_data.ai_system_id,
        content=doc_data.content,
    )
    db.add(document)
    db.commit()
    db.refresh(document)
    return document


@router.get("/", response_model=List[DocumentResponse])
def list_documents(
    ai_system_id: Optional[int] = Query(default=None, ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List documents for the current user, optionally filtered by AI system."""
    query = db.query(Document).filter(Document.owner_id == current_user.id)
    if ai_system_id is not None:
        query = query.filter(Document.ai_system_id == ai_system_id)
    return query.order_by(Document.created_at.desc()).all()


@router.get("/{document_id}", response_model=DocumentResponse)
def get_document(document: Document = Depends(get_owned_document)):
    """Get a specific document."""
    return document


@router.patch("/{document_id}", response_model=DocumentResponse)
def update_document(
    doc_data: DocumentUpdate,
    document: Document = Depends(get_owned_document),
    db: Session = Depends(get_db),
):
    """Edit a document's title, content or review status."""
    update_data = doc_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(document, field, value)

    if "content" in update_data:
        # The stored PDF no longer matches the content; drop it so the next
        # export regenerates from scratch.
        document.file_path = None

    db.commit()
    db.refresh(document)
    return document


@router.post("/generate", response_model=DocumentResponse)
def generate_document(
    request: DocumentGenerateRequest,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Generate a compliance document for an AI system."""
    ai_system = (
        db.query(AISystem)
        .filter(
            AISystem.id == request.ai_system_id,
            AISystem.owner_id == current_user.id,
        )
        .first()
    )
    if not ai_system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )

    billing.ensure_document_type_allowed(current_user, request.document_type)

    try:
        document = document_service.generate_document(
            db,
            ai_system,
            current_user,
            request.document_type,
            request.include_recommendations,
        )
    except KeyError as exc:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(exc).strip("'"),
        )

    db.commit()
    db.refresh(document)
    return document


@router.post("/systems/{system_id}/generate-all", response_model=List[DocumentResponse])
def generate_document_pack(
    system: AISystem = Depends(get_owned_system),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Generate every document type the caller's plan allows for one system."""
    plan = billing.plan_for_user(current_user)
    generated = [
        document_service.generate_document(db, system, current_user, document_type)
        for document_type in DocumentType
        if document_type in document_service.TEMPLATES
        and plan.allows_document_type(document_type)
    ]
    if not generated:
        raise HTTPException(
            status_code=status.HTTP_402_PAYMENT_REQUIRED,
            detail=f"The {plan.name} plan does not include any document types.",
        )

    db.commit()
    for document in generated:
        db.refresh(document)
    return generated


@router.get("/{document_id}/pdf")
def download_document_pdf(
    document: Document = Depends(get_owned_document),
    db: Session = Depends(get_db),
):
    """Render the document to PDF and stream it back."""
    if not document.content:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This document has no content to export.",
        )

    path = FilePath(document.file_path) if document.file_path else None
    if path is None or not path.exists():
        document.file_path = document_service.export_pdf(document)
        db.commit()
        path = FilePath(document.file_path)

    filename = f"{document.title.replace('/', '-')}.pdf"
    return FileResponse(path, media_type="application/pdf", filename=filename)


@router.delete("/{document_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_document(
    document: Document = Depends(get_owned_document),
    db: Session = Depends(get_db),
):
    """Delete a document and any PDF rendered from it."""
    if document.file_path:
        FilePath(document.file_path).unlink(missing_ok=True)

    db.delete(document)
    db.commit()
