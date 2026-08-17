"""
Turning an uploaded document into text the language model can read.

Claim documents arrive as PDFs or as photographs of paperwork, and the two need
different treatment:

* A PDF with a text layer is extracted locally with pypdf. No model call, no
  cost, and the result is exact rather than transcribed.
* A PDF that is only scanned images has no text layer. pypdf returns nothing,
  and that is reported honestly rather than passed off as an empty document.
* An image is read by the vision model, because there is nothing else to do
  with it.

The previous behaviour decoded every non-PDF as UTF-8 with `errors="ignore"`,
which turned a JPEG into thousands of characters of mojibake and sent it to the
model as if it were a policy schedule.
"""

import io
import logging
from dataclasses import dataclass
from typing import Optional

from pypdf import PdfReader
from pypdf.errors import PdfReadError

logger = logging.getLogger(__name__)

# Insurance policies run long, and the model only needs the schedule pages.
MAX_PDF_PAGES = 15

# Below this, a "text layer" is really just page furniture or stray glyphs.
MIN_USEFUL_CHARS = 40

# Guards against a decompression bomb inflating into memory.
MAX_EXTRACTED_CHARS = 200_000


@dataclass(frozen=True)
class ExtractedText:
    """The outcome of reading a document."""

    text: Optional[str]
    #: Why extraction produced nothing, for the document's extraction_error.
    reason: Optional[str] = None
    #: True when a vision model is the only way to read this file.
    needs_vision: bool = False


def looks_like_pdf(content: bytes) -> bool:
    """Return whether the bytes begin with a PDF signature."""
    return content[:5] == b"%PDF-"


def looks_like_image(content: bytes) -> bool:
    """Return whether the bytes begin with a JPEG or PNG signature."""
    return content[:3] == b"\xff\xd8\xff" or content[:8] == b"\x89PNG\r\n\x1a\n"


def extract_pdf_text(content: bytes, max_pages: int = MAX_PDF_PAGES) -> ExtractedText:
    """
    Pull the text layer out of a PDF.

    Args:
        content: The raw PDF bytes.
        max_pages: Stop after this many pages.

    Returns:
        An `ExtractedText`. `needs_vision` is set when the file parses but holds
        no text, which is what a scanned document looks like.
    """
    try:
        reader = PdfReader(io.BytesIO(content))
    except (PdfReadError, ValueError, OSError) as exc:
        logger.warning("Could not parse PDF: %s", exc)
        return ExtractedText(None, reason="This PDF could not be read; it may be corrupt.")

    if reader.is_encrypted:
        # An empty password unlocks the common "owner password only" case.
        try:
            if reader.decrypt("") == 0:
                return ExtractedText(
                    None, reason="This PDF is password protected, so it could not be read."
                )
        except (PdfReadError, NotImplementedError) as exc:
            logger.warning("Could not decrypt PDF: %s", exc)
            return ExtractedText(
                None, reason="This PDF is password protected, so it could not be read."
            )

    pages: list[str] = []
    total = 0
    try:
        for index, page in enumerate(reader.pages):
            if index >= max_pages:
                logger.info("Stopped PDF extraction at %d pages", max_pages)
                break
            try:
                page_text = page.extract_text() or ""
            except Exception:
                # One unreadable page should not discard the rest of the policy.
                logger.warning("Skipped unreadable page %d", index)
                continue
            pages.append(page_text)
            total += len(page_text)
            if total >= MAX_EXTRACTED_CHARS:
                break
    except (PdfReadError, ValueError, OSError) as exc:
        logger.warning("PDF extraction failed part-way: %s", exc)
        if not pages:
            return ExtractedText(
                None, reason="This PDF could not be read; it may be corrupt."
            )

    text = "\n".join(pages).strip()

    if len(text) < MIN_USEFUL_CHARS:
        # Parsed fine but there is no text layer: a scan or a photo saved as PDF.
        return ExtractedText(
            None,
            reason="This PDF contains no selectable text, so it looks like a scan.",
            needs_vision=True,
        )

    return ExtractedText(text[:MAX_EXTRACTED_CHARS])


def extract_plain_text(content: bytes) -> ExtractedText:
    """
    Decode bytes that are genuinely text.

    Args:
        content: The raw file bytes.

    Returns:
        An `ExtractedText`, empty if the bytes are not valid text.
    """
    try:
        # strict, not errors="ignore": a binary file must fail here rather than
        # decode into mojibake that gets sent to the model as document content.
        text = content.decode("utf-8").strip()
    except UnicodeDecodeError:
        return ExtractedText(None, reason="This file is not readable as text.")

    if len(text) < MIN_USEFUL_CHARS:
        return ExtractedText(None, reason="This file contains too little text to read.")

    return ExtractedText(text[:MAX_EXTRACTED_CHARS])


def extract(content: bytes) -> ExtractedText:
    """
    Read a document, choosing the method from its actual bytes.

    Args:
        content: The raw file bytes.

    Returns:
        An `ExtractedText`. `needs_vision` marks files only a vision model can
        read: images, and PDFs with no text layer.
    """
    if not content:
        return ExtractedText(None, reason="The file is empty.")

    if looks_like_pdf(content):
        return extract_pdf_text(content)

    if looks_like_image(content):
        return ExtractedText(
            None, reason="Photographed document; read by the vision model.", needs_vision=True
        )

    return extract_plain_text(content)
