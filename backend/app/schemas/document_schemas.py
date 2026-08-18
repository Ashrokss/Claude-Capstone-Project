"""Request and response schemas for claim supporting documents."""

from datetime import datetime
from typing import Any, Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel, ORMModel
from app.schemas.enums import DocumentType, ProcessingStatus


class DocumentCreate(APIModel):
    """
    Metadata recorded after a document is written to object storage.

    The claim is taken from the request path, not the body.
    """

    filename: str = Field(..., min_length=1, max_length=255)
    document_type: Optional[DocumentType] = None
    file_path: str = Field(
        ..., min_length=1, max_length=500, description="Object storage key or path"
    )
    file_size_bytes: Optional[int] = Field(None, ge=0)
    mime_type: Optional[str] = Field(None, max_length=100)


class DocumentRead(ORMModel):
    """Document as returned by the API."""

    id: UUID
    claim_id: UUID

    filename: str
    document_type: Optional[DocumentType] = None
    file_path: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None

    extracted_data: Optional[dict[str, Any]] = None
    extraction_status: Optional[ProcessingStatus] = None
    extraction_error: Optional[str] = None

    created_at: datetime
    updated_at: datetime
