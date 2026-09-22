"""Persistence boundary for jobs and their extracted requirements."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.job import Job, JobRequirement
from backend.models.util import utcnow
from backend.schemas.job import ExtractedJobRequirements
from backend.schemas.job_listing import JobListing


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

    def save_job_listing(self, listing: JobListing) -> Job:
        """Persists a job-search result with no requirements yet (those get
        attached on demand — see `attach_requirements`). Idempotent per
        (source, external_id): re-saving a listing already fetched in an
        earlier search returns the existing row instead of duplicating it.
        """
        existing = self._session.scalar(
            select(Job).where(Job.source == listing.source, Job.external_id == listing.external_id)
        )
        if existing is not None:
            return existing

        job = Job(
            title=listing.title,
            company=listing.company,
            source=listing.source,
            raw_description=listing.description,
            external_id=listing.external_id,
            location=listing.location,
            country=listing.country,
            publication_date=listing.publication_date,
            employment_type=listing.employment_type,
            remote_type=listing.remote_type,
            salary_min=listing.salary_min,
            salary_max=listing.salary_max,
            currency=listing.currency,
            source_url=listing.source_url,
            retrieved_at=utcnow(),
        )
        self._session.add(job)
        self._session.commit()
        self._session.refresh(job)
        return job

    def attach_requirements(self, job_id: str, extracted: ExtractedJobRequirements) -> Job:
        """Adds extracted requirements to an existing Job (a search result
        the candidate chose to analyze). No-ops if it already has
        requirements, so re-analyzing is safe to call repeatedly.
        """
        job = self.get_job(job_id)
        if job is None:
            raise ValueError(f"Job {job_id} not found")
        if job.requirements:
            return job

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
        if job.seniority is None and extracted.seniority:
            job.seniority = extracted.seniority
        if job.work_model is None and extracted.work_model:
            job.work_model = extracted.work_model
        self._session.commit()
        self._session.refresh(job)
        return job
