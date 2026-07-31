from pydantic import BaseModel, ConfigDict, Field
from typing import Optional, Dict, Any, List
from datetime import datetime
from app.models.ai_system import RiskLevel, ComplianceStatus


class AISystemCreate(BaseModel):
    # Without stripping, ``"   "`` satisfies min_length and registers a system
    # with a blank name that the UI cannot show.
    model_config = ConfigDict(str_strip_whitespace=True)

    name: str = Field(min_length=1, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = Field(default=None, max_length=50)
    use_case: Optional[str] = Field(default=None, max_length=255)
    sector: Optional[str] = Field(default=None, max_length=255)


class AISystemUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    name: Optional[str] = Field(default=None, min_length=1, max_length=255)
    description: Optional[str] = None
    version: Optional[str] = Field(default=None, max_length=50)
    use_case: Optional[str] = Field(default=None, max_length=255)
    sector: Optional[str] = Field(default=None, max_length=255)
    questionnaire_responses: Optional[Dict[str, Any]] = None


class AISystemResponse(BaseModel):
    id: int
    name: str
    description: Optional[str]
    version: Optional[str]
    use_case: Optional[str]
    sector: Optional[str]
    risk_level: Optional[RiskLevel]
    compliance_status: ComplianceStatus
    compliance_score: int
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class AISystemDetailResponse(AISystemResponse):
    questionnaire_responses: Optional[Dict[str, Any]] = None
    requirements_total: int = 0
    requirements_completed: int = 0


# Risk Classification
class RiskClassificationRequest(BaseModel):
    """Questionnaire for EU AI Act risk classification.

    Field groups follow the structure of the Act so answers map one-to-one onto
    the provision that makes them relevant.
    """

    model_config = ConfigDict(str_strip_whitespace=True)

    # Basic use case. Persisted verbatim into ``questionnaire_responses``, so it
    # is bounded to keep an unbounded request body out of the database.
    use_case_category: str = Field(default="other", max_length=100)

    # Prohibited practices (Article 5)
    social_scoring: bool = False
    subliminal_manipulation: bool = False
    exploits_vulnerabilities: bool = False
    realtime_remote_biometric_id: bool = False
    predictive_policing_profiling: bool = False
    untargeted_facial_scraping: bool = False
    emotion_recognition_workplace: bool = False
    biometric_categorization_sensitive: bool = False

    # High-risk indicators (Article 6)
    is_safety_component: bool = False  # Safety component of an Annex I product
    affects_fundamental_rights: bool = False  # Employment, education, services
    uses_biometric_data: bool = False
    makes_automated_decisions: bool = True  # Decisions without human review

    # Specific high-risk areas (Annex III)
    critical_infrastructure: bool = False
    education_access_or_evaluation: bool = False
    hr_recruitment_screening: bool = False  # CV filtering, candidate ranking
    hr_promotion_termination: bool = False  # Promotion/termination decisions
    essential_services_access: bool = False
    credit_worthiness: bool = False
    insurance_risk_assessment: bool = False
    law_enforcement: bool = False
    border_control: bool = False
    justice_system: bool = False
    democratic_processes: bool = False

    # Derogation from the high-risk regime (Article 6(3))
    purely_preparatory_task: bool = False
    human_reviews_every_decision: bool = False

    # Transparency (Article 50)
    interacts_with_humans: bool = True  # Chatbots, virtual assistants
    generates_synthetic_content: bool = False  # Deepfakes, AI-generated media
    emotion_recognition: bool = False
    biometric_categorization: bool = False

    # General-purpose AI models (Chapter V)
    is_general_purpose_model: bool = False


class RiskClassificationResponse(BaseModel):
    risk_level: RiskLevel
    confidence: float  # 0-1
    reasons: List[str]
    requirements: List[str]
    next_steps: List[str]
    applicable_articles: List[str] = []
    annex_iii_areas: List[str] = []
    prohibited: bool = False


class RiskAssessmentResponse(BaseModel):
    id: int
    ai_system_id: int
    assessment_type: str
    risk_level: RiskLevel
    overall_score: int
    data_governance_score: Optional[int]
    transparency_score: Optional[int]
    human_oversight_score: Optional[int]
    robustness_score: Optional[int]
    findings: List[Dict[str, Any]]
    recommendations: List[Dict[str, Any]]
    assessed_at: datetime

    class Config:
        from_attributes = True
