from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import CandidateCreate, CandidateOut
from backend.services.evidence.store import EvidenceStore

router = APIRouter(prefix="/candidates", tags=["candidates"])


@router.post("", response_model=CandidateOut)
def create_or_get_candidate(payload: CandidateCreate, db: Session = Depends(get_db)) -> CandidateOut:
    candidate = EvidenceStore(db).get_or_create_candidate(payload.name, payload.email)
    return CandidateOut.model_validate(candidate)


@router.get("/{candidate_id}", response_model=CandidateOut)
def get_candidate(candidate_id: str, db: Session = Depends(get_db)) -> CandidateOut:
    candidate = EvidenceStore(db).get_candidate(candidate_id)
    if candidate is None:
        raise HTTPException(status_code=404, detail="Candidate not found")
    return CandidateOut.model_validate(candidate)
