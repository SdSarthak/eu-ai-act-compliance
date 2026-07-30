"""Shared FastAPI dependencies for the v1 API."""

from fastapi import Depends, HTTPException, Path, status
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ai_system import AISystem
from app.models.compliance import ComplianceItem
from app.models.document import Document
from app.models.user import User


def get_owned_system(
    system_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> AISystem:
    """Load an AI system that belongs to the caller, or 404."""
    system = (
        db.query(AISystem)
        .filter(AISystem.id == system_id, AISystem.owner_id == current_user.id)
        .first()
    )
    if not system:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="AI system not found",
        )
    return system


def get_owned_document(
    document_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> Document:
    """Load a document that belongs to the caller, or 404."""
    document = (
        db.query(Document)
        .filter(Document.id == document_id, Document.owner_id == current_user.id)
        .first()
    )
    if not document:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Document not found",
        )
    return document


def get_owned_item(
    item_id: int = Path(..., ge=1),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
) -> ComplianceItem:
    """Load a compliance checklist item that belongs to the caller, or 404."""
    item = (
        db.query(ComplianceItem)
        .join(AISystem, ComplianceItem.ai_system_id == AISystem.id)
        .filter(ComplianceItem.id == item_id, AISystem.owner_id == current_user.id)
        .first()
    )
    if not item:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Compliance item not found",
        )
    return item
