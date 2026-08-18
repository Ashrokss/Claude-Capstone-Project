"""Assessment ORM models: the AI's analysis of a claim and its findings."""

import uuid
from decimal import Decimal
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel, CreatedAtMixin, SerializerMixin, UUIDPrimaryKeyMixin
from app.models.base import Base
from app.schemas.enums import AssessmentStatus, ClaimPriority, FraudRiskLevel

if TYPE_CHECKING:
    from app.models.claim import Claim

_ASSESSMENT_STATUSES = ", ".join(f"'{s.value}'" for s in AssessmentStatus)
_FRAUD_LEVELS = ", ".join(f"'{f.value}'" for f in FraudRiskLevel)
_PRIORITIES = ", ".join(f"'{p.value}'" for p in ClaimPriority)

# Confidence and risk scores are percentages.
_PERCENT = "BETWEEN 0 AND 100"


class Assessment(BaseModel):
    """One AI analysis run over a claim."""

    __tablename__ = "assessments"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    # Extracted claim information
    extracted_incident_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    extracted_collision_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    incident_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Damage
    total_estimated_repair_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    damage_confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Policy
    policy_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    coverage_assessment: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    coverage_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    coverage_gaps: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)

    # Fraud
    fraud_risk_level: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    fraud_risk_score: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    # Priority and recommendation
    claim_priority: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    priority_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    recommended_action: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Summary
    final_summary: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    overall_confidence: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    assessment_status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=AssessmentStatus.PENDING.value
    )

    claim: Mapped["Claim"] = relationship(back_populates="assessments")
    damage_items: Mapped[list["DamageItem"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )
    fraud_indicators: Mapped[list["FraudIndicator"]] = relationship(
        back_populates="assessment", cascade="all, delete-orphan", passive_deletes=True
    )

    __table_args__ = (
        CheckConstraint(
            f"assessment_status IN ({_ASSESSMENT_STATUSES})", name="valid_assessment_status"
        ),
        CheckConstraint(
            f"fraud_risk_level IS NULL OR fraud_risk_level IN ({_FRAUD_LEVELS})",
            name="valid_fraud_risk_level",
        ),
        CheckConstraint(
            f"claim_priority IS NULL OR claim_priority IN ({_PRIORITIES})",
            name="valid_claim_priority",
        ),
        CheckConstraint(
            f"fraud_risk_score IS NULL OR fraud_risk_score {_PERCENT}",
            name="valid_fraud_risk_score",
        ),
        CheckConstraint(
            f"damage_confidence IS NULL OR damage_confidence {_PERCENT}",
            name="valid_damage_confidence",
        ),
        CheckConstraint(
            f"overall_confidence IS NULL OR overall_confidence {_PERCENT}",
            name="valid_overall_confidence",
        ),
        Index("idx_assessments_claim_id", "claim_id"),
        Index("idx_assessments_claim_priority", "claim_priority"),
        Index("idx_assessments_fraud_risk_level", "fraud_risk_level"),
    )


class DamageItem(Base, UUIDPrimaryKeyMixin, CreatedAtMixin, SerializerMixin):
    """A single damaged part identified within an assessment."""

    __tablename__ = "damage_items"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )

    part_name: Mapped[str] = mapped_column(String(255), nullable=False)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    estimated_repair_cost: Mapped[Optional[Decimal]] = mapped_column(
        Numeric(12, 2), nullable=True
    )
    repair_cost_reasoning: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    assessment: Mapped["Assessment"] = relationship(back_populates="damage_items")

    __table_args__ = (Index("idx_damage_items_assessment_id", "assessment_id"),)


class FraudIndicator(Base, UUIDPrimaryKeyMixin, CreatedAtMixin, SerializerMixin):
    """A single fraud signal raised within an assessment."""

    __tablename__ = "fraud_indicators"

    assessment_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("assessments.id", ondelete="CASCADE"),
        nullable=False,
    )

    indicator_name: Mapped[str] = mapped_column(String(255), nullable=False)
    indicator_category: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)
    severity: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    evidence: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Why this indicator was flagged"
    )

    assessment: Mapped["Assessment"] = relationship(back_populates="fraud_indicators")

    __table_args__ = (Index("idx_fraud_indicators_assessment_id", "assessment_id"),)
