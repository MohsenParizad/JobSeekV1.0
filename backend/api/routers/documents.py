from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import EvidenceOut
from backend.config import settings
from backend.models.evidence import DocumentType
from backend.providers.llm import get_llm_provider
from backend.services.documents.extraction import EvidenceExtractionService
from backend.services.documents.parser import (
    FileTooLargeError,
    UnsupportedFileTypeError,
    extract_text,
    save_upload,
)
from backend.services.evidence.store import EvidenceStore

router = APIRouter(prefix="/candidates/{candidate_id}/documents", tags=["documents"])


@router.post("", response_model=list[EvidenceOut])
async def upload_document(
    candidate_id: str,
    document_type: DocumentType = Form(...),
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> list[EvidenceOut]:
    content = await file.read()
    try:
        stored_path = save_upload(content, file.filename or "upload", settings.document_storage_dir)
    except (UnsupportedFileTypeError, FileTooLargeError) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    document_text = extract_text(stored_path)
    store = EvidenceStore(db)
    document = store.save_document(candidate_id, document_type, file.filename or "upload", stored_path, document_text)
    items = EvidenceExtractionService(get_llm_provider()).extract(document_text)
    saved = store.save_pending_evidence(candidate_id, document.id, items)
    return [EvidenceOut.model_validate(e) for e in saved]
