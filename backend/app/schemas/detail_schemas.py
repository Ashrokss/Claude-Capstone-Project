"""
Composite response schemas.

Kept separate from the per-entity schema modules so those stay free of
cross-imports.
"""

from typing import Optional

from pydantic import Field

from app.schemas.assessment_schemas import AssessmentRead
from app.schemas.claim_schemas import ClaimRead
from app.schemas.common import ORMModel
from app.schemas.decision_schemas import DecisionRead
from app.schemas.document_schemas import DocumentRead
from app.schemas.enums import AssessmentStatus
from app.schemas.image_schemas import ImageRead


class ClaimDetail(ClaimRead):
    """A claim with all of its evidence, analysis, and decision history."""

    documents: list[DocumentRead] = Field(default_factory=list)
    images: list[ImageRead] = Field(default_factory=list)
    assessment: Optional[AssessmentRead] = Field(
        None, description="The most recent assessment, if analysis has run"
    )
    decision: Optional[DecisionRead] = Field(
        None, description="The most recent human decision, if one has been made"
    )


class ClaimCreatedResponse(ORMModel):
    """Response for a successful claim submission."""

    id: str
    claim_number: str
    status: str
    analysis_queued: bool = Field(
        ..., description="Whether the claim was accepted for AI analysis"
    )


class AnalysisStatusResponse(ORMModel):
    """Response for a queued or in-flight analysis."""

    claim_id: str
    status: str = Field(..., description="QUEUED, PROCESSING, COMPLETE, or FAILED")
    message: str
    queue_depth: Optional[int] = None


class AssessmentStatusResponse(ORMModel):
    """
    Returned by the assessment endpoint while analysis is still running.

    `steps` lets the UI show progress rather than an indeterminate spinner.
    """

    claim_id: str
    assessment_status: AssessmentStatus
    message: str
    steps: list[str] = Field(default_factory=list)


class AnalyticsResponse(ORMModel):
    """KPI figures for the adjuster dashboard."""

    total_claims: int
    pending_review: int
    high_risk_claims: int
    fast_track_claims: int
    processed_this_week: int
    average_processing_time_hours: Optional[float] = Field(
        None, description="Mean hours from submission to first decision; null if none decided"
    )


class DeletedResponse(ORMModel):
    """Acknowledgement for a successful delete."""

    id: str
    deleted: bool = True
    storage_removed: bool = Field(
        ..., description="False if the database row went but the stored file did not"
    )
