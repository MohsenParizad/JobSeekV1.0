from pathlib import Path

import docx
import pytest
from pypdf import PdfWriter

from backend.services.documents.parser import (
    FileTooLargeError,
    MAX_FILE_SIZE_BYTES,
    UnsupportedFileTypeError,
    extract_text,
    save_upload,
    validate_upload,
)


def test_validate_upload_rejects_unsupported_extension():
    with pytest.raises(UnsupportedFileTypeError):
        validate_upload("resume.txt", b"hello")


def test_validate_upload_rejects_oversized_file():
    oversized = b"0" * (MAX_FILE_SIZE_BYTES + 1)
    with pytest.raises(FileTooLargeError):
        validate_upload("resume.pdf", oversized)


def test_save_upload_never_stores_original_filename(tmp_path):
    stored_path = save_upload(b"%PDF-1.4 fake content", "very_personal_cv.pdf", tmp_path)
    assert stored_path.exists()
    assert stored_path.name != "very_personal_cv.pdf"
    assert stored_path.suffix == ".pdf"


def test_extract_text_from_docx(tmp_path):
    doc = docx.Document()
    doc.add_paragraph("Experienced with Python and PostgreSQL.")
    docx_path = tmp_path / "cv.docx"
    doc.save(docx_path)

    text = extract_text(docx_path)
    assert "Python" in text
    assert "PostgreSQL" in text


def test_extract_text_from_pdf(tmp_path: Path):
    writer = PdfWriter()
    writer.add_blank_page(width=200, height=200)
    pdf_path = tmp_path / "cv.pdf"
    with open(pdf_path, "wb") as fh:
        writer.write(fh)

    # A blank page has no extractable text, but the dispatch must not raise.
    assert extract_text(pdf_path) == ""


def test_extract_text_rejects_unsupported_extension(tmp_path):
    other_path = tmp_path / "cv.txt"
    other_path.write_text("hello")
    with pytest.raises(UnsupportedFileTypeError):
        extract_text(other_path)
