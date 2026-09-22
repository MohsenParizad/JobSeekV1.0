"""JobProvider interface — the same swappable-backend pattern as LLMProvider
(backend/providers/llm/base.py). Adding a new job source means writing one
new class here; nothing in search orchestration, deduplication, or the
matching engine needs to change (see the Extensibility NFR).
"""
from abc import ABC, abstractmethod
from datetime import date

from backend.schemas.job_listing import JobListing


class JobSearchError(Exception):
    """Raised when a provider's search call fails (network error, bad
    response, missing credentials). Callers catch this per-provider so one
    provider's outage never breaks search entirely (see the Reliability NFR
    in docs/requirements.md — Adzuna being down must not break Arbeitnow).
    """


class JobProvider(ABC):
    name: str

    @abstractmethod
    def search_jobs(
        self,
        keywords: str,
        country: str | None = None,
        location: str | None = None,
        published_after: date | None = None,
        work_model: str | None = None,
    ) -> list[JobListing]:
        raise NotImplementedError
