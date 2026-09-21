"""File validation, storage, and text extraction for uploaded CVs/references.

Uploaded files are stored under a generated id, never the original filename
(see docs/privacy.md), and are validated for type/size before anything else
touches them.
"""
import uuid
from pathlib import Path

from docx import Document as DocxDocument
from pypdf import PdfReader

MAX_FILE_SIZE_BYTES = 10 * 1024 * 1024  # 10 MB
ALLOWED_EXTENSIONS = {".pdf", ".docx"}


class UnsupportedFileTypeError(ValueError):
    pass


class FileTooLargeError(ValueError):
    pass


def validate_upload(original_filename: str, content: bytes) -> str:
    """Returns the validated lowercase extension, or raises."""
    ext = Path(original_filename).suffix.lower()
    if ext not in ALLOWED_EXTENSIONS:
        raise UnsupportedFileTypeError(f"Unsupported file type '{ext}'. Allowed: {sorted(ALLOWED_EXTENSIONS)}")
    if len(content) > MAX_FILE_SIZE_BYTES:
        raise FileTooLargeError(f"File exceeds the {MAX_FILE_SIZE_BYTES // (1024 * 1024)}MB limit")
    return ext


def save_upload(content: bytes, original_filename: str, storage_dir: Path) -> Path:
    """Persists raw bytes under a generated name and returns the stored path."""
    ext = validate_upload(original_filename, content)
    storage_dir.mkdir(parents=True, exist_ok=True)
    stored_name = f"{uuid.uuid4()}{ext}"
    path = storage_dir / stored_name
    path.write_bytes(content)
    return path


def extract_text(path: Path) -> str:
    ext = path.suffix.lower()
    if ext == ".pdf":
        return _extract_pdf_text(path)
    if ext == ".docx":
        return _extract_docx_text(path)
    raise UnsupportedFileTypeError(f"Unsupported file type '{ext}'")


def _extract_pdf_text(path: Path) -> str:
    reader = PdfReader(str(path))
    return "\n".join(page.extract_text() or "" for page in reader.pages).strip()


def _extract_docx_text(path: Path) -> str:
    doc = DocxDocument(str(path))
    return "\n".join(p.text for p in doc.paragraphs).strip()
