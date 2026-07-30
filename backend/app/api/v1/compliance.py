from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_owned_item, get_owned_system
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ai_system import AISystem
from app.models.compliance import ComplianceItem, ItemStatus
from app.models.user import User
from app.schemas.compliance import (
    ComplianceChecklistResponse,
    ComplianceItemResponse,
    ComplianceItemUpdate,
    ComplianceOverviewResponse,
)
from app.services import compliance as compliance_service

router = APIRouter()


def _checklist_payload(system: AISystem) -> ComplianceChecklistResponse:
    items: List[ComplianceItem] = list(system.compliance_items)
    scores = compliance_service.category_scores(items)
    return ComplianceChecklistResponse(
        ai_system_id=system.id,
        ai_system_name=system.name,
        risk_level=system.risk_level,
        compliance_status=system.compliance_status,
        compliance_score=system.compliance_score,
        total_items=len(items),
        completed_items=sum(1 for i in items if i.status == ItemStatus.COMPLETED),
        in_progress_items=sum(1 for i in items if i.status == ItemStatus.IN_PROGRESS),
        not_applicable_items=sum(
            1 for i in items if i.status == ItemStatus.NOT_APPLICABLE
        ),
        category_scores={
            category.value: score for category, score in scores.items()
        },
        items=[ComplianceItemResponse.model_validate(item) for item in items],
    )


@router.get("/overview", response_model=ComplianceOverviewResponse)
def get_overview(
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """Portfolio-level compliance numbers for the dashboard."""
    return compliance_service.build_overview(db, current_user)


@router.get(
    "/systems/{system_id}/checklist",
    response_model=ComplianceChecklistResponse,
)
def get_checklist(
    system: AISystem = Depends(get_owned_system),
    db: Session = Depends(get_db),
):
    """The obligations for one AI system and their current status.

    The checklist is generated on first access so a system that has just been
    classified always has something to work through.
    """
    if not system.compliance_items:
        compliance_service.refresh_system_compliance(db, system)
        db.commit()
        db.refresh(system)
    return _checklist_payload(system)


@router.post(
    "/systems/{system_id}/checklist/sync",
    response_model=ComplianceChecklistResponse,
)
def sync_checklist(
    system: AISystem = Depends(get_owned_system),
    db: Session = Depends(get_db),
):
    """Rebuild the checklist from the catalogue, keeping existing progress."""
    compliance_service.refresh_system_compliance(db, system)
    db.commit()
    db.refresh(system)
    return _checklist_payload(system)


@router.patch("/items/{item_id}", response_model=ComplianceItemResponse)
def update_item(
    payload: ComplianceItemUpdate,
    item: ComplianceItem = Depends(get_owned_item),
    db: Session = Depends(get_db),
):
    """Mark an obligation as started, done or not applicable."""
    compliance_service.apply_item_update(
        db,
        item,
        status=payload.status,
        evidence_notes=payload.evidence_notes,
    )
    db.commit()
    db.refresh(item)
    return item
