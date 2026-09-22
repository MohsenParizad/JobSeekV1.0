from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import EvidenceOut, EvidenceUpdate
from backend.models.evidence import EvidenceStatus
from backend.services.evidence.store import EvidenceStore

router = APIRouter(tags=["evidence"])


@router.get("/candidates/{candidate_id}/evidence", response_model=list[EvidenceOut])
def list_evidence(
    candidate_id: str,
    status: EvidenceStatus | None = Query(None),
    db: Session = Depends(get_db),
) -> list[EvidenceOut]:
    items = EvidenceStore(db).list_evidence(candidate_id, status=status)
    return [EvidenceOut.model_validate(e) for e in items]


@router.patch("/evidence/{evidence_id}", response_model=EvidenceOut)
def update_evidence(evidence_id: str, payload: EvidenceUpdate, db: Session = Depends(get_db)) -> EvidenceOut:
    store = EvidenceStore(db)
    try:
        if payload.action == "approve":
            evidence = store.approve(evidence_id, concept=payload.concept, description=payload.description)
        else:
            evidence = store.reject(evidence_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    return EvidenceOut.model_validate(evidence)
