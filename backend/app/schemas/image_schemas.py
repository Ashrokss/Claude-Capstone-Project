"""Request and response schemas for vehicle damage images."""

from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import Field

from app.schemas.common import APIModel, ORMModel
from app.schemas.enums import ProcessingStatus


class ImageCreate(APIModel):
    """
    Metadata recorded after an image is written to object storage.

    The claim is taken from the request path, not the body.
    """

    filename: str = Field(..., min_length=1, max_length=255)
    file_path: str = Field(
        ..., min_length=1, max_length=500, description="Object storage key or path"
    )
    file_size_bytes: Optional[int] = Field(None, ge=0)
    mime_type: Optional[str] = Field(None, max_length=100)


class ImageRead(ORMModel):
    """Image as returned by the API."""

    id: UUID
    claim_id: UUID

    filename: str
    file_path: str
    file_size_bytes: Optional[int] = None
    mime_type: Optional[str] = None

    analyzed: bool = False
    analysis_status: Optional[ProcessingStatus] = None
    analysis_error: Optional[str] = None

    created_at: datetime
    updated_at: datetime
