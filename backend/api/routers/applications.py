from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import ClaimValidationOut, GenerateApplicationRequest, GeneratedApplicationOut
from backend.models.evidence import EvidenceStatus
from backend.models.generation import GeneratedApplicationRecord
from backend.providers.llm import get_llm_provider
from backend.schemas.generation import ClaimValidation
from backend.services.evidence.store import EvidenceStore
from backend.services.generation.service import generate_application_material, revalidate
from backend.services.generation.store import GenerationStore

router = APIRouter(prefix="/applications", tags=["applications"])


@router.post("/generate", response_model=GeneratedApplicationOut)
def generate(payload: GenerateApplicationRequest, db: Session = Depends(get_db)) -> GeneratedApplicationOut:
    try:
        record, validations = generate_application_material(
            db, payload.candidate_id, payload.candidate_name, payload.job_id, get_llm_provider()
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _build_generated_out(record, validations)


@router.get("/{job_id}", response_model=GeneratedApplicationOut)
def get_latest(job_id: str, candidate_id: str, db: Session = Depends(get_db)) -> GeneratedApplicationOut:
    record = GenerationStore(db).get_latest(candidate_id, job_id)
    if record is None:
        raise HTTPException(status_code=404, detail="No generated application yet")
    verified_evidence = EvidenceStore(db).list_evidence(candidate_id, status=EvidenceStatus.APPROVED)
    validations = revalidate(record, verified_evidence)
    return _build_generated_out(record, validations)


def _build_generated_out(
    record: GeneratedApplicationRecord, validations: list[ClaimValidation]
) -> GeneratedApplicationOut:
    return GeneratedApplicationOut(
        id=record.id,
        job_id=record.job_id,
        candidate_id=record.candidate_id,
        tailored_summary=record.tailored_summary,
        emphasized_experience=record.emphasized_experience,
        cv_suggestions=record.cv_suggestions,
        cover_letter=record.cover_letter,
        validations=[ClaimValidationOut(**v.model_dump()) for v in validations],
    )
