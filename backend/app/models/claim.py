"""Claim ORM model."""

import uuid
from datetime import date, time
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    CheckConstraint,
    Date,
    Index,
    Integer,
    String,
    Text,
    Time,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.schemas.enums import ClaimStatus

if TYPE_CHECKING:
    from app.models.assessment import Assessment
    from app.models.decision import HumanDecision
    from app.models.evidence import Document, Image

_STATUS_VALUES = ", ".join(f"'{s.value}'" for s in ClaimStatus)


class Claim(BaseModel):
    """A motor insurance claim submitted by a customer."""

    __tablename__ = "claims"

    claim_number: Mapped[str] = mapped_column(
        String(20), unique=True, nullable=False, doc="Format: VC-YYYY-NNNNN"
    )

    # Customer
    customer_name: Mapped[str] = mapped_column(String(255), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False)
    phone: Mapped[str] = mapped_column(String(20), nullable=False)

    # Vehicle
    vehicle_make: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_model: Mapped[str] = mapped_column(String(100), nullable=False)
    vehicle_year: Mapped[int] = mapped_column(Integer, nullable=False)
    registration_number: Mapped[str] = mapped_column(String(50), nullable=False)

    # Policy and incident
    policy_number: Mapped[str] = mapped_column(String(50), nullable=False)
    incident_date: Mapped[date] = mapped_column(Date, nullable=False)
    incident_time: Mapped[Optional[time]] = mapped_column(Time, nullable=True)
    incident_location: Mapped[Optional[str]] = mapped_column(String(500), nullable=True)
    incident_type: Mapped[str] = mapped_column(String(50), nullable=False)
    incident_description: Mapped[str] = mapped_column(Text, nullable=False)

    # Damage detail supplied by the customer
    damaged_areas: Mapped[Optional[list]] = mapped_column(JSONB, nullable=True)
    severity_slider: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    damage_notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Status
    status: Mapped[str] = mapped_column(
        String(50), nullable=False, server_default=ClaimStatus.SUBMITTED.value
    )
    created_by_user_id: Mapped[Optional[uuid.UUID]] = mapped_column(
        PGUUID(as_uuid=True), nullable=True, doc="Supabase auth user who submitted it"
    )

    # Children are deleted with the claim; ON DELETE CASCADE covers writes that
    # bypass the ORM, and passive_deletes lets Postgres do the work.
    documents: Mapped[list["Document"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", passive_deletes=True
    )
    images: Mapped[list["Image"]] = relationship(
        back_populates="claim", cascade="all, delete-orphan", passive_deletes=True
    )
    assessments: Mapped[list["Assessment"]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="Assessment.created_at.desc()",
    )
    decisions: Mapped[list["HumanDecision"]] = relationship(
        back_populates="claim",
        cascade="all, delete-orphan",
        passive_deletes=True,
        order_by="HumanDecision.created_at.desc()",
    )

    __table_args__ = (
        CheckConstraint(f"status IN ({_STATUS_VALUES})", name="valid_status"),
        CheckConstraint(
            "severity_slider IS NULL OR (severity_slider BETWEEN 0 AND 5)",
            name="valid_severity_slider",
        ),
        Index("idx_claims_status", "status"),
        # Plain btree: Postgres scans it backwards for the dashboard's
        # newest-first ordering, so a DESC index buys nothing here.
        Index("idx_claims_created_at", "created_at"),
        Index("idx_claims_customer_email", "email"),
        Index("idx_claims_policy_number", "policy_number"),
        Index("idx_claims_created_by_user_id", "created_by_user_id"),
    )
