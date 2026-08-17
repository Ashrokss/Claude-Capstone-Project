"""
Request and response schemas for human review decisions.

A decision is the point where a person takes responsibility for the outcome,
so the payload requirements differ by decision type.
"""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import EmailStr, Field, model_validator

from app.schemas.common import APIModel, ORMModel
from app.schemas.enums import DecisionType


class DecisionCreate(APIModel):
    """Payload for `POST /api/claims/{claim_id}/decision`."""

    decision: DecisionType
    reviewer_name: str = Field(..., min_length=1, max_length=255)
    reviewer_email: Optional[EmailStr] = Field(None, max_length=255)
    reviewer_id: Optional[UUID] = None

    decision_comments: Optional[str] = Field(None, max_length=5000)
    requested_information: Optional[str] = Field(
        None, max_length=5000, description="Required when decision is REQUESTED_INFO"
    )
    investigation_notes: Optional[str] = Field(
        None, max_length=5000, description="Required when decision is ESCALATED"
    )

    @model_validator(mode="after")
    def require_context_for_decision(self) -> "DecisionCreate":
        """
        Enforce the detail each decision type needs.

        Asking for more information without saying what is missing, or
        escalating without a reason, leaves the next handler with nothing to
        act on.
        """
        if self.decision is DecisionType.REQUESTED_INFO and not (
            self.requested_information or ""
        ).strip():
            raise ValueError(
                "requested_information is required when decision is REQUESTED_INFO"
            )

        if self.decision is DecisionType.ESCALATED and not (
            self.investigation_notes or ""
        ).strip():
            raise ValueError(
                "investigation_notes is required when decision is ESCALATED"
            )

        return self


class DecisionRead(ORMModel):
    """Decision as returned by `GET /api/claims/{claim_id}/decision`."""

    id: UUID
    claim_id: UUID

    decision: DecisionType
    reviewer_name: str
    reviewer_email: Optional[EmailStr] = None
    reviewer_id: Optional[UUID] = None

    decision_comments: Optional[str] = None
    requested_information: Optional[str] = None
    investigation_notes: Optional[str] = None

    created_at: datetime
