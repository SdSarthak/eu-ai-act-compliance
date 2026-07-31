from fastapi import APIRouter, Depends, status
from sqlalchemy.orm import Session
from typing import List

from app.api.deps import get_owned_system
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.compliance import ItemStatus
from app.models.user import User
from app.models.ai_system import AISystem
from app.schemas.ai_system import (
    AISystemCreate,
    AISystemDetailResponse,
    AISystemUpdate,
    AISystemResponse,
)
from app.services import billing, compliance
from app.services import documents as documents_service

router = APIRouter()


def _to_detail(system: AISystem) -> AISystemDetailResponse:
    items = list(system.compliance_items)
    return AISystemDetailResponse(
        **AISystemResponse.model_validate(system).model_dump(),
        questionnaire_responses=system.questionnaire_responses or {},
        requirements_total=len(items),
        requirements_completed=sum(
            1 for item in items if item.status == ItemStatus.COMPLETED
        ),
    )


@router.post("/", response_model=AISystemResponse, status_code=status.HTTP_201_CREATED)
def create_ai_system(
    system_data: AISystemCreate,
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Create a new AI system for compliance tracking."""
    billing.ensure_system_quota(db, current_user)

    ai_system = AISystem(
        owner_id=current_user.id,
        name=system_data.name,
        description=system_data.description,
        version=system_data.version,
        use_case=system_data.use_case,
        sector=system_data.sector,
        questionnaire_responses={},
    )
    db.add(ai_system)
    db.commit()
    db.refresh(ai_system)
    return ai_system


@router.get("/", response_model=List[AISystemResponse])
def list_ai_systems(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """List all AI systems for the current user."""
    return (
        db.query(AISystem)
        .filter(AISystem.owner_id == current_user.id)
        .order_by(AISystem.created_at.desc())
        .all()
    )


@router.get("/{system_id}", response_model=AISystemDetailResponse)
def get_ai_system(system: AISystem = Depends(get_owned_system)):
    """Get a specific AI system, including its checklist progress."""
    return _to_detail(system)


@router.put("/{system_id}", response_model=AISystemDetailResponse)
def update_ai_system(
    system_data: AISystemUpdate,
    system: AISystem = Depends(get_owned_system),
    db: Session = Depends(get_db),
):
    """Update an AI system."""
    update_data = system_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(system, field, value)

    db.commit()
    db.refresh(system)
    return _to_detail(system)


@router.delete("/{system_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_ai_system(
    system: AISystem = Depends(get_owned_system),
    db: Session = Depends(get_db),
):
    """Delete an AI system along with its assessments, checklist and documents."""
    # The document rows cascade, but their rendered PDFs are not in the
    # database and would otherwise stay in the storage directory forever.
    stale_pdfs = [document.file_path for document in system.documents]

    db.delete(system)
    db.commit()

    for file_path in stale_pdfs:
        documents_service.remove_pdf(file_path)


@router.post("/{system_id}/recalculate", response_model=AISystemDetailResponse)
def recalculate_compliance(
    system: AISystem = Depends(get_owned_system),
    db: Session = Depends(get_db),
):
    """Regenerate the checklist from the current risk level and rescore."""
    compliance.refresh_system_compliance(db, system)
    db.commit()
    db.refresh(system)
    return _to_detail(system)
