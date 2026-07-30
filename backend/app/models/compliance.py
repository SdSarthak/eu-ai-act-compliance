from sqlalchemy import Column, Integer, String, Text, DateTime, Enum, ForeignKey
from sqlalchemy.orm import relationship
from datetime import datetime
import enum
from app.core.database import Base


class RequirementCategory(str, enum.Enum):
    RISK_MANAGEMENT = "risk_management"
    DATA_GOVERNANCE = "data_governance"
    DOCUMENTATION = "documentation"
    RECORD_KEEPING = "record_keeping"
    TRANSPARENCY = "transparency"
    HUMAN_OVERSIGHT = "human_oversight"
    ROBUSTNESS = "robustness"
    REGISTRATION = "registration"
    GOVERNANCE = "governance"


class ItemStatus(str, enum.Enum):
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    NOT_APPLICABLE = "not_applicable"


class ComplianceItem(Base):
    """A single obligation an AI system has to satisfy under the EU AI Act.

    Items are generated from the requirement catalogue for the system's risk
    level (see ``app.services.compliance``) and then tracked by the user.
    """

    __tablename__ = "compliance_items"

    id = Column(Integer, primary_key=True, index=True)
    ai_system_id = Column(
        Integer,
        ForeignKey("ai_systems.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )

    # Catalogue identity - stable across regenerations of the checklist
    code = Column(String(50), nullable=False, index=True)  # e.g. "art9_risk_mgmt"
    article = Column(String(50), nullable=False)           # e.g. "Article 9"
    title = Column(String(255), nullable=False)
    description = Column(Text)
    category = Column(Enum(RequirementCategory), nullable=False)

    # Tracking
    status = Column(Enum(ItemStatus), default=ItemStatus.PENDING, nullable=False)
    evidence_notes = Column(Text)
    completed_at = Column(DateTime, nullable=True)

    # Timestamps
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Relationships
    ai_system = relationship("AISystem", back_populates="compliance_items")
