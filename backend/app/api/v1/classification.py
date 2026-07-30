from datetime import datetime, timedelta
from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.api.deps import get_owned_system
from app.core.database import get_db
from app.core.security import get_current_user
from app.models.ai_system import AISystem, RiskAssessment
from app.models.user import User
from app.schemas.ai_system import (
    RiskAssessmentResponse,
    RiskClassificationRequest,
    RiskClassificationResponse,
)
from app.services import compliance
from app.services.classification import classify_risk
from app.services.compliance import category_scores
from app.services.requirements import RequirementCategory

router = APIRouter()

# High-risk classifications should be revisited at least once a year.
ASSESSMENT_VALIDITY_DAYS = 365


@router.post("/classify", response_model=RiskClassificationResponse)
def classify_ai_system(
    data: RiskClassificationRequest,
    current_user: User = Depends(get_current_user),
):
    """Classify an AI system's risk level against the EU AI Act.

    This is a preliminary classification and is not persisted; use
    ``/classify/{system_id}`` to store the result against a registered system.
    """
    return classify_risk(data)


@router.post("/classify/{system_id}", response_model=RiskClassificationResponse)
def classify_and_save(
    data: RiskClassificationRequest,
    system: AISystem = Depends(get_owned_system),
    db: Session = Depends(get_db),
):
    """Classify a registered AI system and store the assessment.

    Saving a classification also regenerates the compliance checklist for the
    new risk level, preserving progress on obligations that still apply.
    """
    result = classify_risk(data)

    system.risk_level = result.risk_level
    system.questionnaire_responses = data.model_dump()

    items = compliance.refresh_system_compliance(db, system)
    scores = category_scores(items)

    assessment = RiskAssessment(
        ai_system_id=system.id,
        assessment_type="initial" if not system.risk_assessments else "periodic",
        risk_level=result.risk_level,
        findings=[
            {
                "type": "classification",
                "reasons": result.reasons,
                "applicable_articles": result.applicable_articles,
                "annex_iii_areas": result.annex_iii_areas,
                "confidence": result.confidence,
                "prohibited": result.prohibited,
            }
        ],
        recommendations=[
            {
                "requirements": result.requirements,
                "next_steps": result.next_steps,
            }
        ],
        overall_score=system.compliance_score,
        data_governance_score=scores.get(RequirementCategory.DATA_GOVERNANCE),
        transparency_score=scores.get(RequirementCategory.TRANSPARENCY),
        human_oversight_score=scores.get(RequirementCategory.HUMAN_OVERSIGHT),
        robustness_score=scores.get(RequirementCategory.ROBUSTNESS),
        valid_until=datetime.utcnow() + timedelta(days=ASSESSMENT_VALIDITY_DAYS),
    )
    db.add(assessment)
    db.commit()

    return result


@router.get(
    "/assessments/{system_id}",
    response_model=List[RiskAssessmentResponse],
)
def list_assessments(system: AISystem = Depends(get_owned_system)):
    """Assessment history for a system, newest first."""
    return system.risk_assessments
