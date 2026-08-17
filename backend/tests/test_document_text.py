"""
Tests for reading uploaded documents.

The behaviour that matters most is what happens to files that cannot be read:
a binary file must never decode into mojibake and reach the model as though it
were a policy schedule, and a scanned PDF must be reported as needing vision
rather than as an empty document.
"""

import io
import zlib

import pytest
from pypdf import PdfWriter

from app.services import document_text

POLICY_TEXT = (
    "MOTOR INSURANCE POLICY SCHEDULE\n"
    "Policy Number: POL-88213\n"
    "Insured Name: Asha Menon\n"
    "Status: Active\n"
    "Coverage Type: Comprehensive\n"
    "Valid From: 2026-01-01\n"
    "Valid To: 2026-12-31\n"
    "Own Damage: Covered\n"
    "Third Party Liability: Covered\n"
)


def pdf_with_text(text: str, pages: int = 1) -> bytes:
    """
    Build a PDF carrying a genuine text layer.

    pypdf can create pages but cannot typeset, so the content stream is written
    by hand. That is deliberate: it produces the same PDF structure a real
    document has, so the extraction path under test is the real one rather than
    a stub.
    """
    from pypdf.generic import DecodedStreamObject, DictionaryObject, NameObject

    lines = "".join(
        f"BT /F1 11 Tf 40 {800 - index * 16} Td ({line}) Tj ET\n"
        for index, line in enumerate(text.splitlines())
    )
    stream = f"q\n{lines}Q\n".encode("latin-1")

    writer = PdfWriter()
    for _ in range(pages):
        page = writer.add_blank_page(width=595, height=842)

        content = DecodedStreamObject()
        content.set_data(stream)
        page[NameObject("/Contents")] = writer._add_object(content)

        font = DictionaryObject()
        font[NameObject("/Type")] = NameObject("/Font")
        font[NameObject("/Subtype")] = NameObject("/Type1")
        font[NameObject("/BaseFont")] = NameObject("/Helvetica")

        fonts = DictionaryObject()
        fonts[NameObject("/F1")] = writer._add_object(font)
        resources = DictionaryObject()
        resources[NameObject("/Font")] = fonts
        page[NameObject("/Resources")] = resources

    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def blank_pdf(pages: int = 1) -> bytes:
    """Build a PDF with no text layer, as a scan would be."""
    writer = PdfWriter()
    for _ in range(pages):
        writer.add_blank_page(width=595, height=842)
    buffer = io.BytesIO()
    writer.write(buffer)
    return buffer.getvalue()


def png_bytes(w: int = 32, h: int = 32) -> bytes:
    """A small valid PNG."""
    import struct

    raw = b"".join(b"\x00" + bytes([120, 130, 140] * w) for _ in range(h))

    def chunk(tag, data):
        c = tag + data
        return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

    return (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", struct.pack(">IIBBBBB", w, h, 8, 2, 0, 0, 0))
        + chunk(b"IDAT", zlib.compress(raw))
        + chunk(b"IEND", b"")
    )


class TestFormatDetection:
    def test_pdf_is_detected_from_its_signature(self):
        assert document_text.looks_like_pdf(b"%PDF-1.7 rest")

    @pytest.mark.parametrize(
        "head", [b"\xff\xd8\xff\xe0", b"\x89PNG\r\n\x1a\n"]
    )
    def test_images_are_detected_from_their_signature(self, head):
        assert document_text.looks_like_image(head + b"body")

    def test_text_is_neither(self):
        assert not document_text.looks_like_pdf(b"Policy Number: X")
        assert not document_text.looks_like_image(b"Policy Number: X")


class TestPdfExtraction:
    def test_text_layer_is_extracted(self):
        result = document_text.extract(pdf_with_text(POLICY_TEXT))
        assert result.text is not None
        assert "POL-88213" in result.text
        assert "Comprehensive" in result.text

    def test_a_scan_is_reported_as_needing_vision(self):
        # A blank page parses fine but yields no text: that is what a scanned
        # policy looks like, and it must not read as "empty document".
        result = document_text.extract(blank_pdf())
        assert result.text is None
        assert result.needs_vision is True
        assert "scan" in result.reason.lower()

    def test_corrupt_pdf_is_reported_without_raising(self):
        result = document_text.extract(b"%PDF-1.7\nthis is not a real pdf")
        assert result.text is None
        assert result.needs_vision is False
        assert result.reason

    def test_page_limit_is_respected(self):
        result = document_text.extract_pdf_text(pdf_with_text(POLICY_TEXT, pages=40), max_pages=2)
        # Two pages of the same block, not forty.
        assert result.text is not None
        assert result.text.count("POL-88213") <= 2


class TestBinaryIsNeverTreatedAsText:
    def test_an_image_is_routed_to_vision_not_decoded(self):
        # The old behaviour decoded this with errors="ignore" and sent thousands
        # of characters of mojibake to the model as document content.
        result = document_text.extract(png_bytes())
        assert result.text is None
        assert result.needs_vision is True

    def test_arbitrary_binary_is_refused(self):
        result = document_text.extract(b"MZ\x90\x00" + bytes(range(256)) * 4)
        assert result.text is None
        assert result.needs_vision is False
        assert "not readable as text" in result.reason

    def test_empty_file_is_refused(self):
        result = document_text.extract(b"")
        assert result.text is None
        assert result.reason == "The file is empty."


class TestPlainText:
    def test_readable_text_passes_through(self):
        result = document_text.extract(POLICY_TEXT.encode("utf-8"))
        assert result.text is not None
        assert "POL-88213" in result.text

    def test_too_little_text_is_refused(self):
        result = document_text.extract(b"hi")
        assert result.text is None
        assert result.needs_vision is False

    def test_output_is_capped(self):
        huge = ("Policy Number: POL-1\n" * 40_000).encode("utf-8")
        result = document_text.extract(huge)
        assert result.text is not None
        assert len(result.text) <= document_text.MAX_EXTRACTED_CHARS
