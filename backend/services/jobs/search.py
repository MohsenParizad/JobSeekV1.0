"""Searches all configured job providers, tolerating individual provider
failures (see the Reliability NFR in docs/requirements.md — Adzuna being
down must not break Arbeitnow search), and deduplicates the combined
results before returning them.
"""
from dataclasses import dataclass, field
from datetime import date

from backend.providers.jobs.base import JobProvider, JobSearchError
from backend.schemas.job_listing import JobListing
from backend.services.jobs.deduplication import deduplicate_listings


@dataclass
class JobSearchResult:
    listings: list[JobListing]
    provider_errors: dict[str, str] = field(default_factory=dict)  # provider name -> error message


def search_all_providers(
    providers: list[JobProvider],
    keywords: str,
    country: str | None = None,
    location: str | None = None,
    published_after: date | None = None,
    work_model: str | None = None,
) -> JobSearchResult:
    all_listings: list[JobListing] = []
    provider_errors: dict[str, str] = {}
    for provider in providers:
        try:
            all_listings.extend(
                provider.search_jobs(
                    keywords,
                    country=country,
                    location=location,
                    published_after=published_after,
                    work_model=work_model,
                )
            )
        except JobSearchError as exc:
            provider_errors[provider.name] = str(exc)
    return JobSearchResult(listings=deduplicate_listings(all_listings), provider_errors=provider_errors)
