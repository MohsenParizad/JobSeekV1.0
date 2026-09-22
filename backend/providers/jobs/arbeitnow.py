"""Arbeitnow job provider — a free public API needing no credentials.

The public job-board endpoint does not support server-side keyword search,
so this fetches a bounded number of pages and filters client-side. Field
names follow Arbeitnow's public API as of this writing; per-item parsing is
defensive so a future field change degrades gracefully (that listing is
skipped) instead of breaking search entirely.
"""
from datetime import UTC, date, datetime

import requests

from backend.providers.jobs.base import JobProvider, JobSearchError
from backend.schemas.job_listing import JobListing

API_URL = "https://www.arbeitnow.com/api/job-board-api"
MAX_PAGES = 3
REQUEST_TIMEOUT_SECONDS = 10


class ArbeitnowProvider(JobProvider):
    name = "arbeitnow"

    def search_jobs(
        self,
        keywords: str,
        country: str | None = None,
        location: str | None = None,
        published_after: date | None = None,
        work_model: str | None = None,
    ) -> list[JobListing]:
        try:
            raw_entries = self._fetch_entries()
        except requests.RequestException as exc:
            raise JobSearchError(f"Arbeitnow search failed: {exc}") from exc

        listings = [listing for entry in raw_entries if (listing := self._normalize(entry)) is not None]
        return [
            listing
            for listing in listings
            if self._matches_filters(listing, keywords, country, location, published_after, work_model)
        ]

    def _fetch_entries(self) -> list[dict]:
        entries: list[dict] = []
        url = API_URL
        for _ in range(MAX_PAGES):
            if not url:
                break
            response = requests.get(url, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
            entries.extend(payload.get("data", []))
            url = (payload.get("links") or {}).get("next")
        return entries

    def _normalize(self, entry: dict) -> JobListing | None:
        try:
            external_id = entry.get("slug") or entry.get("url")
            title = entry.get("title")
            if not external_id or not title:
                return None
            publication_date = None
            created_at = entry.get("created_at")
            if isinstance(created_at, (int, float)):
                publication_date = datetime.fromtimestamp(created_at, tz=UTC).date()
            job_types = entry.get("job_types") or []
            return JobListing(
                source=self.name,
                external_id=str(external_id),
                title=title,
                company=entry.get("company_name"),
                # Arbeitnow doesn't provide a distinct country field, so country
                # filtering below falls back to matching against location text.
                location=entry.get("location"),
                country=None,
                publication_date=publication_date,
                description=entry.get("description") or "",
                employment_type=", ".join(job_types) if job_types else None,
                remote_type="remote" if entry.get("remote") else None,
                salary_min=None,
                salary_max=None,
                currency=None,
                source_url=entry.get("url"),
            )
        except Exception:
            # A malformed entry is skipped, not allowed to break the whole search.
            return None

    @staticmethod
    def _matches_filters(
        listing: JobListing,
        keywords: str,
        country: str | None,
        location: str | None,
        published_after: date | None,
        work_model: str | None,
    ) -> bool:
        haystack = f"{listing.title} {listing.description}".lower()
        if keywords and keywords.lower() not in haystack:
            return False
        if location and (not listing.location or location.lower() not in listing.location.lower()):
            return False
        if country and (not listing.location or country.lower() not in listing.location.lower()):
            return False
        if published_after and listing.publication_date and listing.publication_date < published_after:
            return False
        if work_model and listing.remote_type != work_model:
            return False
        return True
