"""Persistence boundary for jobs and their extracted requirements."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.job import Job, JobRequirement
from backend.schemas.job import ExtractedJobRequirements


class JobStore:
    def __init__(self, session: Session):
        self._session = session

    def save_job(
        self,
        extracted: ExtractedJobRequirements,
        raw_description: str,
        source: str = "manual",
    ) -> Job:
        job = Job(
            title=extracted.title,
            company=extracted.company,
            source=source,
            seniority=extracted.seniority,
            work_model=extracted.work_model,
            raw_description=raw_description,
        )
        self._session.add(job)
        self._session.flush()  # assigns job.id so requirements can reference it

        requirements = [
            JobRequirement(
                job_id=job.id,
                category=item.category,
                concept=item.concept,
                importance=item.importance,
                language_level=item.language_level,
                source_text=item.source_text,
            )
            for item in extracted.requirements
        ]
        self._session.add_all(requirements)
        self._session.commit()
        self._session.refresh(job)
        return job

    def get_job(self, job_id: str) -> Job | None:
        return self._session.get(Job, job_id)

    def list_jobs(self) -> list[Job]:
        return list(self._session.scalars(select(Job).order_by(Job.created_at.desc())))
