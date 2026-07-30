"""Compliance checklist generation, scoring and portfolio reporting.

A system's checklist is derived from its risk level: every obligation in the
catalogue becomes a trackable :class:`ComplianceItem`. Re-running the sync after
a re-classification keeps the user's progress on items that still apply and
drops the ones that no longer do.
"""

from datetime import datetime
from typing import Dict, Iterable, List, Optional

from sqlalchemy.orm import Session

from app.models.ai_system import AISystem, ComplianceStatus, RiskLevel
from app.models.compliance import ComplianceItem, ItemStatus, RequirementCategory
from app.models.document import Document
from app.models.user import User
from app.services.requirements import Requirement, requirements_for

# Partially-done work counts for half a point so the dashboard moves as soon as
# a team starts on an obligation.
STATUS_WEIGHTS: Dict[ItemStatus, float] = {
    ItemStatus.PENDING: 0.0,
    ItemStatus.IN_PROGRESS: 0.5,
    ItemStatus.COMPLETED: 1.0,
}

CATEGORY_SCORE_FIELDS = {
    RequirementCategory.DATA_GOVERNANCE: "data_governance_score",
    RequirementCategory.TRANSPARENCY: "transparency_score",
    RequirementCategory.HUMAN_OVERSIGHT: "human_oversight_score",
    RequirementCategory.ROBUSTNESS: "robustness_score",
}


def _is_general_purpose(ai_system: AISystem) -> bool:
    responses = ai_system.questionnaire_responses or {}
    return bool(responses.get("is_general_purpose_model"))


def catalogue_for(ai_system: AISystem) -> List[Requirement]:
    """The obligations that currently apply to ``ai_system``."""
    risk_level = ai_system.risk_level or RiskLevel.MINIMAL
    return requirements_for(risk_level, _is_general_purpose(ai_system))


def sync_checklist(db: Session, ai_system: AISystem) -> List[ComplianceItem]:
    """Align the stored checklist with the catalogue for the current risk level.

    Existing items keep their status and evidence notes; obligations that no
    longer apply are removed; new ones are appended as pending.
    """
    catalogue = catalogue_for(ai_system)
    wanted = {requirement.code: requirement for requirement in catalogue}

    existing = {item.code: item for item in ai_system.compliance_items}

    for code, item in existing.items():
        if code not in wanted:
            db.delete(item)

    for requirement in catalogue:
        item = existing.get(requirement.code)
        if item is None:
            item = ComplianceItem(
                ai_system_id=ai_system.id,
                code=requirement.code,
                article=requirement.article,
                title=requirement.title,
                description=requirement.description,
                category=requirement.category,
                status=ItemStatus.PENDING,
            )
            db.add(item)
        else:
            # Keep wording in sync with the catalogue without losing progress.
            item.article = requirement.article
            item.title = requirement.title
            item.description = requirement.description
            item.category = requirement.category

    db.flush()
    db.refresh(ai_system)
    return list(ai_system.compliance_items)


def compute_score(items: Iterable[ComplianceItem]) -> int:
    """Percentage of applicable obligations that are done (0-100)."""
    all_items = list(items)
    applicable = [
        item for item in all_items if item.status != ItemStatus.NOT_APPLICABLE
    ]
    if not applicable:
        # Every obligation was waived, or there are none to begin with.
        return 100 if all_items else 0

    earned = sum(STATUS_WEIGHTS.get(item.status, 0.0) for item in applicable)
    return int(round(100 * earned / len(applicable)))


def category_scores(items: Iterable[ComplianceItem]) -> Dict[RequirementCategory, int]:
    """Per-category completion, used to fill the risk assessment sub-scores."""
    buckets: Dict[RequirementCategory, List[ComplianceItem]] = {}
    for item in items:
        buckets.setdefault(item.category, []).append(item)
    return {category: compute_score(group) for category, group in buckets.items()}


def derive_status(ai_system: AISystem, score: int) -> ComplianceStatus:
    """Map a score onto the coarse status shown in the UI."""
    if ai_system.risk_level == RiskLevel.UNACCEPTABLE:
        return ComplianceStatus.NON_COMPLIANT
    if ai_system.risk_level is None:
        return ComplianceStatus.NOT_STARTED
    if score >= 100:
        return ComplianceStatus.COMPLIANT
    if score >= 80:
        return ComplianceStatus.UNDER_REVIEW
    if score > 0:
        return ComplianceStatus.IN_PROGRESS
    return ComplianceStatus.NOT_STARTED


def refresh_system_compliance(db: Session, ai_system: AISystem) -> List[ComplianceItem]:
    """Regenerate the checklist, then recompute score and status."""
    items = sync_checklist(db, ai_system)
    ai_system.compliance_score = compute_score(items)
    ai_system.compliance_status = derive_status(ai_system, ai_system.compliance_score)
    db.flush()
    return items


def recalculate(db: Session, ai_system: AISystem) -> None:
    """Recompute score and status from the checklist as it stands."""
    items = list(ai_system.compliance_items)
    ai_system.compliance_score = compute_score(items)
    ai_system.compliance_status = derive_status(ai_system, ai_system.compliance_score)
    db.flush()


def apply_item_update(
    db: Session,
    item: ComplianceItem,
    status: Optional[ItemStatus] = None,
    evidence_notes: Optional[str] = None,
) -> ComplianceItem:
    """Update one checklist item and roll the change up to the system."""
    if status is not None:
        item.status = status
        item.completed_at = datetime.utcnow() if status == ItemStatus.COMPLETED else None
    if evidence_notes is not None:
        item.evidence_notes = evidence_notes

    db.flush()
    recalculate(db, item.ai_system)
    return item


def build_overview(db: Session, user: User) -> dict:
    """Portfolio-level numbers for the dashboard."""
    systems: List[AISystem] = (
        db.query(AISystem).filter(AISystem.owner_id == user.id).all()
    )
    document_count = (
        db.query(Document).filter(Document.owner_id == user.id).count()
    )

    by_risk_level = {level.value: 0 for level in RiskLevel}
    by_status = {status.value: 0 for status in ComplianceStatus}
    unclassified = 0
    open_items = 0
    total_items = 0

    for system in systems:
        if system.risk_level is None:
            unclassified += 1
        else:
            by_risk_level[system.risk_level.value] += 1
        by_status[system.compliance_status.value] += 1
        for item in system.compliance_items:
            total_items += 1
            if item.status in (ItemStatus.PENDING, ItemStatus.IN_PROGRESS):
                open_items += 1

    average_score = (
        int(round(sum(system.compliance_score for system in systems) / len(systems)))
        if systems
        else 0
    )

    return {
        "total_systems": len(systems),
        "unclassified_systems": unclassified,
        "total_documents": document_count,
        "average_compliance_score": average_score,
        "systems_by_risk_level": by_risk_level,
        "systems_by_status": by_status,
        "total_requirements": total_items,
        "open_requirements": open_items,
        "action_required": by_risk_level[RiskLevel.UNACCEPTABLE.value]
        + by_risk_level[RiskLevel.HIGH.value]
        + unclassified,
    }
