"""Human decision ORM model: the point where a person owns the outcome."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import CheckConstraint, ForeignKey, Index, String, Text
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import Base, CreatedAtMixin, SerializerMixin, UUIDPrimaryKeyMixin
from app.schemas.enums import DecisionType

if TYPE_CHECKING:
    from app.models.claim import Claim

_DECISIONS = ", ".join(f"'{d.value}'" for d in DecisionType)


class HumanDecision(Base, UUIDPrimaryKeyMixin, CreatedAtMixin, SerializerMixin):
    """A reviewer's decision on a claim. Append-only: decisions are not edited."""

    __tablename__ = "human_decisions"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    decision: Mapped[str] = mapped_column(String(50), nullable=False)
    reviewer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    reviewer_email: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    reviewer_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, doc="Supabase auth user who decided"
    )

    decision_comments: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requested_information: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Set when decision is REQUESTED_INFO"
    )
    investigation_notes: Mapped[Optional[str]] = mapped_column(
        Text, nullable=True, doc="Set when decision is ESCALATED"
    )

    claim: Mapped["Claim"] = relationship(back_populates="decisions")

    __table_args__ = (
        CheckConstraint(f"decision IN ({_DECISIONS})", name="valid_decision"),
        Index("idx_human_decisions_claim_id", "claim_id"),
        Index("idx_human_decisions_created_at", "created_at"),
    )
