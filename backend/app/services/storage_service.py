"""
File storage backed by Supabase Storage.

Uploads go to a private bucket and are handed back to clients as short-lived
signed URLs. Claim evidence includes number plates, documents and accident
photographs, so nothing here is world-readable.
"""

import logging
import mimetypes
import re
import uuid
from dataclasses import dataclass
from typing import Optional
from uuid import UUID

import httpx
from fastapi import HTTPException, UploadFile, status

from app.core.config import settings

logger = logging.getLogger(__name__)

# Magic numbers, checked because a client-supplied extension or content-type is
# not evidence of what the bytes actually are.
_SIGNATURES: tuple[tuple[bytes, str], ...] = (
    (b"\xff\xd8\xff", "image/jpeg"),
    (b"\x89PNG\r\n\x1a\n", "image/png"),
    (b"%PDF-", "application/pdf"),
)

_EXTENSION_BY_MIME = {
    "image/jpeg": {"jpg", "jpeg"},
    "image/png": {"png"},
    "application/pdf": {"pdf"},
}

_UNSAFE_FILENAME = re.compile(r"[^A-Za-z0-9._-]+")


@dataclass(frozen=True)
class StoredFile:
    """The result of a successful upload."""

    path: str
    filename: str
    size_bytes: int
    mime_type: str


class StorageNotConfigured(RuntimeError):
    """Raised when Supabase Storage credentials are absent."""


def _require_config() -> tuple[str, str]:
    """
    Return the Supabase base URL and service key.

    Returns:
        A tuple of (project URL, service role key).

    Raises:
        StorageNotConfigured: If either value is missing or still a placeholder.
    """
    url = (settings.supabase_url or "").strip().rstrip("/")
    key = (settings.supabase_service_role_key or "").strip()

    if not url or "your_" in url.lower():
        raise StorageNotConfigured("SUPABASE_URL is not configured")
    if not key or key.lower().startswith("your_"):
        raise StorageNotConfigured(
            "SUPABASE_SERVICE_ROLE_KEY is not configured; uploads are disabled"
        )
    return url, key


def sanitise_filename(name: str) -> str:
    """
    Reduce a client filename to something safe to store.

    Args:
        name: The original filename.

    Returns:
        A filename with directory separators and unusual characters removed.
    """
    # Take the basename only: a client may send "../../etc/passwd".
    base = name.replace("\\", "/").split("/")[-1].strip() or "upload"
    cleaned = _UNSAFE_FILENAME.sub("_", base).lstrip(".")
    return (cleaned or "upload")[:120]


def detect_mime(head: bytes, filename: str) -> Optional[str]:
    """
    Identify a file from its leading bytes.

    Args:
        head: The first bytes of the file.
        filename: The declared filename, used only to disambiguate.

    Returns:
        The detected MIME type, or None if unrecognised.
    """
    for signature, mime in _SIGNATURES:
        if head.startswith(signature):
            return mime
    return None


async def validate_upload(
    file: UploadFile, *, allowed_mimes: set[str], max_size_mb: int
) -> tuple[bytes, str]:
    """
    Read an upload into memory and check its size and true type.

    Args:
        file: The incoming upload.
        allowed_mimes: MIME types this endpoint accepts.
        max_size_mb: Size ceiling in megabytes.

    Returns:
        A tuple of (file bytes, detected MIME type).

    Raises:
        HTTPException: 413 if oversized, 415 if the type is not accepted.
    """
    max_bytes = max_size_mb * 1024 * 1024

    payload = await file.read()
    await file.close()

    if not payload:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST, detail="The uploaded file is empty"
        )

    if len(payload) > max_bytes:
        raise HTTPException(
            status_code=status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            detail=f"File exceeds the {max_size_mb}MB limit",
        )

    detected = detect_mime(payload[:16], file.filename or "")
    if detected is None or detected not in allowed_mimes:
        readable = ", ".join(sorted(e.upper() for m in allowed_mimes for e in _EXTENSION_BY_MIME.get(m, {m})))
        raise HTTPException(
            status_code=status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
            detail=f"Unsupported file type. Accepted formats: {readable}",
        )

    return payload, detected


def build_path(claim_id: UUID, kind: str, filename: str) -> str:
    """
    Build the object key for a piece of claim evidence.

    Args:
        claim_id: Owning claim.
        kind: Either "documents" or "images".
        filename: Sanitised filename.

    Returns:
        An object key of the form `claims/{claim_id}/{kind}/{unique}-{filename}`.
    """
    # The random prefix keeps two uploads of "photo.jpg" from colliding.
    return f"claims/{claim_id}/{kind}/{uuid.uuid4().hex[:8]}-{filename}"


async def upload(payload: bytes, path: str, mime_type: str) -> StoredFile:
    """
    Write bytes to the storage bucket.

    Args:
        payload: File contents.
        path: Destination object key.
        mime_type: Content type to store against the object.

    Returns:
        A `StoredFile` describing the stored object.

    Raises:
        StorageNotConfigured: If credentials are absent.
        HTTPException: 502 if Supabase rejects the upload.
    """
    base, key = _require_config()
    endpoint = f"{base}/storage/v1/object/{settings.storage_bucket}/{path}"

    async with httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds) as client:
        response = await client.post(
            endpoint,
            content=payload,
            headers={
                "Authorization": f"Bearer {key}",
                "Content-Type": mime_type,
                "x-upsert": "false",
            },
        )

    if response.status_code >= 400:
        logger.error(
            "Supabase Storage upload failed (%s): %s", response.status_code, response.text[:300]
        )
        raise HTTPException(
            status_code=status.HTTP_502_BAD_GATEWAY,
            detail="Could not store the uploaded file. Please try again.",
        )

    return StoredFile(
        path=path,
        filename=path.rsplit("/", 1)[-1],
        size_bytes=len(payload),
        mime_type=mime_type,
    )


async def signed_url(path: str, ttl_seconds: Optional[int] = None) -> Optional[str]:
    """
    Mint a time-limited URL for a stored object.

    Args:
        path: Object key.
        ttl_seconds: Lifetime; defaults to the configured TTL.

    Returns:
        A signed URL, or None if one could not be produced.
    """
    try:
        base, key = _require_config()
    except StorageNotConfigured:
        return None

    ttl = ttl_seconds or settings.signed_url_ttl_seconds
    endpoint = f"{base}/storage/v1/object/sign/{settings.storage_bucket}/{path}"

    try:
        async with httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds) as client:
            response = await client.post(
                endpoint,
                json={"expiresIn": ttl},
                headers={"Authorization": f"Bearer {key}"},
            )
        if response.status_code >= 400:
            logger.warning("Could not sign %s: %s", path, response.text[:200])
            return None
        return f"{base}/storage/v1{response.json()['signedURL']}"
    except (httpx.HTTPError, KeyError, ValueError):
        logger.exception("Failed to sign storage URL for %s", path)
        return None


async def delete(path: str) -> bool:
    """
    Remove an object from the bucket.

    Args:
        path: Object key.

    Returns:
        True if the object was removed or already absent.
    """
    try:
        base, key = _require_config()
    except StorageNotConfigured:
        return False

    endpoint = f"{base}/storage/v1/object/{settings.storage_bucket}/{path}"
    try:
        async with httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds) as client:
            response = await client.delete(
                endpoint, headers={"Authorization": f"Bearer {key}"}
            )
        # 404 means the goal state already holds.
        return response.status_code < 400 or response.status_code == 404
    except httpx.HTTPError:
        logger.exception("Failed to delete storage object %s", path)
        return False


async def download(path: str) -> Optional[bytes]:
    """
    Fetch an object's bytes, for AI analysis.

    Args:
        path: Object key.

    Returns:
        The file contents, or None if unavailable.
    """
    try:
        base, key = _require_config()
    except StorageNotConfigured:
        return None

    endpoint = f"{base}/storage/v1/object/{settings.storage_bucket}/{path}"
    try:
        async with httpx.AsyncClient(timeout=settings.ai_request_timeout_seconds) as client:
            response = await client.get(
                endpoint, headers={"Authorization": f"Bearer {key}"}
            )
        if response.status_code >= 400:
            logger.warning("Could not download %s: %s", path, response.status_code)
            return None
        return response.content
    except httpx.HTTPError:
        logger.exception("Failed to download storage object %s", path)
        return None


def image_mimes() -> set[str]:
    """Return accepted image MIME types from configuration."""
    return {
        mime
        for mime, exts in _EXTENSION_BY_MIME.items()
        if exts & set(settings.allowed_image_formats_list)
    }


def document_mimes() -> set[str]:
    """Return accepted document MIME types from configuration."""
    return {
        mime
        for mime, exts in _EXTENSION_BY_MIME.items()
        if exts & set(settings.allowed_document_formats_list)
    }
