"""Document and image upload and removal for a claim."""

import logging
from typing import Annotated, Optional
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import get_async_session
from app.core.security import CurrentUserDep, assert_can_access_claim
from app.models import Document, Image
from app.schemas.detail_schemas import DeletedResponse
from app.schemas.document_schemas import DocumentRead
from app.schemas.enums import DocumentType
from app.schemas.image_schemas import ImageRead
from app.services import claim_service, storage_service
from app.services.storage_service import StorageNotConfigured

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/claims/{claim_id}", tags=["Evidence"])

DbSession = Annotated[AsyncSession, Depends(get_async_session)]


async def _authorised_claim(db: AsyncSession, claim_id: UUID, user):
    """
    Load a claim and confirm the caller may attach evidence to it.

    Args:
        db: Active database session.
        claim_id: Claim primary key.
        user: The authenticated caller.

    Returns:
        The claim.

    Raises:
        HTTPException: 404 if absent or not visible to this caller.
    """
    claim = await claim_service.get_claim(db, claim_id)
    if claim is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Claim not found")
    assert_can_access_claim(user, claim.created_by_user_id)
    return claim


def _storage_unavailable(exc: StorageNotConfigured) -> HTTPException:
    """Translate a missing storage configuration into a clear 503."""
    logger.error("Upload rejected: %s", exc)
    return HTTPException(
        status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
        detail="File storage is not configured on the server.",
    )


@router.post(
    "/documents",
    response_model=DocumentRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a supporting document",
)
async def upload_document(
    claim_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    file: UploadFile = File(...),
    document_type: Optional[DocumentType] = Form(None),
):
    """Store a document against a claim and mark it awaiting extraction."""
    await _authorised_claim(db, claim_id, user)

    payload, mime = await storage_service.validate_upload(
        file,
        allowed_mimes=storage_service.document_mimes(),
        max_size_mb=settings.max_document_size_mb,
    )

    safe_name = storage_service.sanitise_filename(file.filename or "document")
    path = storage_service.build_path(claim_id, "documents", safe_name)

    try:
        stored = await storage_service.upload(payload, path, mime)
    except StorageNotConfigured as exc:
        raise _storage_unavailable(exc) from exc

    document = Document(
        claim_id=claim_id,
        filename=safe_name,
        document_type=document_type.value if document_type else None,
        file_path=stored.path,
        file_size_bytes=stored.size_bytes,
        mime_type=stored.mime_type,
        extraction_status="PENDING",
    )
    db.add(document)
    await db.commit()
    await db.refresh(document)

    logger.info("Document %s uploaded for claim %s", document.id, claim_id)
    return DocumentRead.model_validate(document)


@router.post(
    "/images",
    response_model=ImageRead,
    status_code=status.HTTP_201_CREATED,
    summary="Upload a damage photograph",
)
async def upload_image(
    claim_id: UUID,
    db: DbSession,
    user: CurrentUserDep,
    file: UploadFile = File(...),
):
    """Store a damage photograph against a claim and mark it awaiting analysis."""
    await _authorised_claim(db, claim_id, user)

    payload, mime = await storage_service.validate_upload(
        file,
        allowed_mimes=storage_service.image_mimes(),
        max_size_mb=settings.max_image_size_mb,
    )

    safe_name = storage_service.sanitise_filename(file.filename or "image")
    path = storage_service.build_path(claim_id, "images", safe_name)

    try:
        stored = await storage_service.upload(payload, path, mime)
    except StorageNotConfigured as exc:
        raise _storage_unavailable(exc) from exc

    image = Image(
        claim_id=claim_id,
        filename=safe_name,
        file_path=stored.path,
        file_size_bytes=stored.size_bytes,
        mime_type=stored.mime_type,
        analysis_status="PENDING",
        analyzed=False,
    )
    db.add(image)
    await db.commit()
    await db.refresh(image)

    logger.info("Image %s uploaded for claim %s", image.id, claim_id)
    return ImageRead.model_validate(image)


@router.delete(
    "/documents/{document_id}",
    response_model=DeletedResponse,
    summary="Remove a document",
)
async def delete_document(
    claim_id: UUID, document_id: UUID, db: DbSession, user: CurrentUserDep
):
    """Delete a document record and its stored file."""
    await _authorised_claim(db, claim_id, user)

    document = await db.scalar(
        select(Document).where(Document.id == document_id, Document.claim_id == claim_id)
    )
    if document is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Document not found on this claim"
        )

    # Storage first: if it fails, the row survives and the file is still
    # reachable, which is recoverable. The reverse leaves an orphaned file.
    removed = await storage_service.delete(document.file_path)
    if not removed:
        logger.warning("Storage delete failed for %s; removing the record anyway", document.file_path)

    await db.delete(document)
    await db.commit()
    return DeletedResponse(id=str(document_id), storage_removed=removed)


@router.delete(
    "/images/{image_id}",
    response_model=DeletedResponse,
    summary="Remove an image",
)
async def delete_image(claim_id: UUID, image_id: UUID, db: DbSession, user: CurrentUserDep):
    """Delete an image record and its stored file."""
    await _authorised_claim(db, claim_id, user)

    image = await db.scalar(
        select(Image).where(Image.id == image_id, Image.claim_id == claim_id)
    )
    if image is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND, detail="Image not found on this claim"
        )

    removed = await storage_service.delete(image.file_path)
    if not removed:
        logger.warning("Storage delete failed for %s; removing the record anyway", image.file_path)

    await db.delete(image)
    await db.commit()
    return DeletedResponse(id=str(image_id), storage_removed=removed)
