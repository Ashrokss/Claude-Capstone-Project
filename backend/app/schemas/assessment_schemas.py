"""
Response schemas for AI assessments.

Assessments are produced by the AI orchestrator rather than submitted by a
client, so these are read-oriented. The `*Create` variants exist so the
orchestrator can validate model output before it is persisted.
"""

from datetime import datetime
from decimal import Decimal
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel, ORMModel
from app.schemas.enums import (
    AssessmentStatus,
    ClaimPriority,
    CoverageAssessment,
    DamageSeverity,
    FraudRiskLevel,
    IndicatorSeverity,
    PolicyStatus,
    RecommendedAction,
)


class DamageItemBase(APIModel):
    """A single damaged part with its cost estimate."""

    part_name: str = Field(..., min_length=1, max_length=255)
    severity: Optional[DamageSeverity] = None
    estimated_repair_cost: Optional[Decimal] = Field(None, ge=0, max_digits=12, decimal_places=2)
    repair_cost_reasoning: Optional[str] = None


class DamageItemCreate(DamageItemBase):
    """Damage item as emitted by the AI orchestrator."""


class DamageItemRead(ORMModel):
    """Damage item as returned by the API."""

    id: UUID
    assessment_id: UUID
    part_name: str
    severity: Optional[DamageSeverity] = None
    estimated_repair_cost: Optional[Decimal] = None
    repair_cost_reasoning: Optional[str] = None
    created_at: datetime


class FraudIndicatorBase(APIModel):
    """A single fraud signal detected during analysis."""

    indicator_name: str = Field(..., min_length=1, max_length=255)
    indicator_category: Optional[str] = Field(None, max_length=100)
    severity: Optional[IndicatorSeverity] = None
    description: Optional[str] = None
    evidence: Optional[str] = Field(None, description="Why this indicator was flagged")


class FraudIndicatorCreate(FraudIndicatorBase):
    """Fraud indicator as emitted by the AI orchestrator."""


class FraudIndicatorRead(ORMModel):
    """Fraud indicator as returned by the API."""

    id: UUID
    assessment_id: UUID
    indicator_name: str
    indicator_category: Optional[str] = None
    severity: Optional[IndicatorSeverity] = None
    description: Optional[str] = None
    evidence: Optional[str] = None
    created_at: datetime


class AssessmentBase(APIModel):
    """Assessment fields produced by the AI orchestrator."""

    # Extracted claim information
    extracted_incident_type: Optional[str] = Field(None, max_length=50)
    extracted_collision_type: Optional[str] = Field(None, max_length=50)
    incident_summary: Optional[str] = None

    # Damage
    total_estimated_repair_cost: Optional[Decimal] = Field(
        None, ge=0, max_digits=12, decimal_places=2
    )
    damage_confidence: Optional[int] = Field(None, ge=0, le=100)

    # Policy
    policy_status: Optional[PolicyStatus] = None
    coverage_assessment: Optional[CoverageAssessment] = None
    coverage_reasoning: Optional[str] = None
    coverage_gaps: Optional[list[str]] = None

    # Fraud
    fraud_risk_level: Optional[FraudRiskLevel] = None
    fraud_risk_score: Optional[int] = Field(None, ge=0, le=100)

    # Priority and recommendation
    claim_priority: Optional[ClaimPriority] = None
    priority_reasoning: Optional[str] = None
    recommended_action: Optional[RecommendedAction] = None

    # Summary
    final_summary: Optional[str] = None
    overall_confidence: Optional[int] = Field(None, ge=0, le=100)


class AssessmentCreate(AssessmentBase):
    """Assessment payload validated before persistence, with its child rows."""

    damage_items: list[DamageItemCreate] = Field(default_factory=list)
    fraud_indicators: list[FraudIndicatorCreate] = Field(default_factory=list)


class AssessmentRead(ORMModel):
    """Assessment as returned by `GET /api/claims/{claim_id}/assessment`."""

    id: UUID
    claim_id: UUID

    extracted_incident_type: Optional[str] = None
    extracted_collision_type: Optional[str] = None
    incident_summary: Optional[str] = None

    total_estimated_repair_cost: Optional[Decimal] = Field(None, ge=0)
    damage_confidence: Optional[int] = Field(None, ge=0, le=100)

    policy_status: Optional[PolicyStatus] = None
    coverage_assessment: Optional[CoverageAssessment] = None
    coverage_reasoning: Optional[str] = None
    coverage_gaps: Optional[list[str]] = None

    fraud_risk_level: Optional[FraudRiskLevel] = None
    fraud_risk_score: Optional[int] = Field(None, ge=0, le=100)

    claim_priority: Optional[ClaimPriority] = None
    priority_reasoning: Optional[str] = None
    recommended_action: Optional[RecommendedAction] = None

    final_summary: Optional[str] = None
    overall_confidence: Optional[int] = Field(None, ge=0, le=100)

    assessment_status: AssessmentStatus = AssessmentStatus.PENDING
    created_at: datetime
    updated_at: datetime

    damage_items: list[DamageItemRead] = Field(default_factory=list)
    fraud_indicators: list[FraudIndicatorRead] = Field(default_factory=list)
