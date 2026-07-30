from datetime import datetime
from typing import Dict, List, Optional

from pydantic import BaseModel

from app.models.ai_system import ComplianceStatus, RiskLevel
from app.models.compliance import ItemStatus, RequirementCategory


class ComplianceItemResponse(BaseModel):
    id: int
    ai_system_id: int
    code: str
    article: str
    title: str
    description: Optional[str]
    category: RequirementCategory
    status: ItemStatus
    evidence_notes: Optional[str]
    completed_at: Optional[datetime]
    updated_at: datetime

    class Config:
        from_attributes = True


class ComplianceItemUpdate(BaseModel):
    status: Optional[ItemStatus] = None
    evidence_notes: Optional[str] = None


class ComplianceChecklistResponse(BaseModel):
    ai_system_id: int
    ai_system_name: str
    risk_level: Optional[RiskLevel]
    compliance_status: ComplianceStatus
    compliance_score: int
    total_items: int
    completed_items: int
    in_progress_items: int
    not_applicable_items: int
    category_scores: Dict[str, int]
    items: List[ComplianceItemResponse]


class ComplianceOverviewResponse(BaseModel):
    total_systems: int
    unclassified_systems: int
    total_documents: int
    average_compliance_score: int
    systems_by_risk_level: Dict[str, int]
    systems_by_status: Dict[str, int]
    total_requirements: int
    open_requirements: int
    action_required: int
