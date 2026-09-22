"""Persistence boundary for generated application material."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.generation import GeneratedApplicationRecord
from backend.schemas.generation import GeneratedApplication


class GenerationStore:
    def __init__(self, session: Session):
        self._session = session

    def save(self, candidate_id: str, job_id: str, generated: GeneratedApplication) -> GeneratedApplicationRecord:
        record = GeneratedApplicationRecord(
            candidate_id=candidate_id,
            job_id=job_id,
            tailored_summary=generated.tailored_summary,
            emphasized_experience=generated.emphasized_experience,
            cv_suggestions=generated.cv_suggestions,
            cover_letter=generated.cover_letter,
            claims=[claim.model_dump() for claim in generated.claims],
        )
        self._session.add(record)
        self._session.commit()
        self._session.refresh(record)
        return record

    def get_latest(self, candidate_id: str, job_id: str) -> GeneratedApplicationRecord | None:
        stmt = (
            select(GeneratedApplicationRecord)
            .where(GeneratedApplicationRecord.candidate_id == candidate_id, GeneratedApplicationRecord.job_id == job_id)
            .order_by(GeneratedApplicationRecord.created_at.desc())
        )
        return self._session.scalars(stmt).first()
