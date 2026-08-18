"""Document and image ORM models: the evidence attached to a claim."""

import uuid
from typing import TYPE_CHECKING, Optional

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.dialects.postgresql import UUID as PGUUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.models.base import BaseModel
from app.schemas.enums import DocumentType

if TYPE_CHECKING:
    from app.models.claim import Claim

_DOCUMENT_TYPES = ", ".join(f"'{d.value}'" for d in DocumentType)


class Document(BaseModel):
    """A supporting document uploaded against a claim."""

    __tablename__ = "documents"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    document_type: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False, doc="Object storage key"
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Results of AI extraction over the document
    extracted_data: Mapped[Optional[dict]] = mapped_column(JSONB, nullable=True)
    extraction_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    extraction_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    claim: Mapped["Claim"] = relationship(back_populates="documents")

    __table_args__ = (
        CheckConstraint(
            f"document_type IS NULL OR document_type IN ({_DOCUMENT_TYPES})",
            name="valid_document_type",
        ),
        Index("idx_documents_claim_id", "claim_id"),
    )


class Image(BaseModel):
    """A vehicle damage photograph uploaded against a claim."""

    __tablename__ = "images"

    claim_id: Mapped[uuid.UUID] = mapped_column(
        PGUUID(as_uuid=True),
        ForeignKey("claims.id", ondelete="CASCADE"),
        nullable=False,
    )

    filename: Mapped[str] = mapped_column(String(255), nullable=False)
    file_path: Mapped[str] = mapped_column(
        String(500), nullable=False, doc="Object storage key"
    )
    file_size_bytes: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    mime_type: Mapped[Optional[str]] = mapped_column(String(100), nullable=True)

    # Results of AI damage analysis
    analyzed: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    analysis_status: Mapped[Optional[str]] = mapped_column(String(50), nullable=True)
    analysis_error: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    claim: Mapped["Claim"] = relationship(back_populates="images")

    __table_args__ = (
        Index("idx_images_claim_id", "claim_id"),
        Index("idx_images_analyzed", "analyzed"),
    )
