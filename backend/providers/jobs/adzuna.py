"""Adzuna job provider. Requires ADZUNA_APP_ID/ADZUNA_APP_KEY (see
.env.example) — backend/providers/jobs/__init__.py only registers this
provider once both are configured, so its absence never blocks search
(Arbeitnow still works with no credentials at all).
"""
from datetime import date, datetime

import requests

from backend.providers.jobs.base import JobProvider, JobSearchError
from backend.schemas.job_listing import JobListing

API_URL_TEMPLATE = "https://api.adzuna.com/v1/api/jobs/{country}/search/1"
DEFAULT_COUNTRY = "de"  # Adzuna requires a country code; this app's context is Germany-centric.
RESULTS_PER_PAGE = 20
REQUEST_TIMEOUT_SECONDS = 10


class AdzunaProvider(JobProvider):
    name = "adzuna"

    def __init__(self, app_id: str, app_key: str):
        self._app_id = app_id
        self._app_key = app_key

    def search_jobs(
        self,
        keywords: str,
        country: str | None = None,
        location: str | None = None,
        published_after: date | None = None,
        work_model: str | None = None,
    ) -> list[JobListing]:
        params = {
            "app_id": self._app_id,
            "app_key": self._app_key,
            "results_per_page": RESULTS_PER_PAGE,
            "what": keywords,
            "content-type": "application/json",
        }
        if location:
            params["where"] = location
        if published_after:
            max_days_old = (date.today() - published_after).days
            if max_days_old >= 0:
                params["max_days_old"] = max_days_old

        country_code = (country or DEFAULT_COUNTRY).lower()
        url = API_URL_TEMPLATE.format(country=country_code)
        try:
            response = requests.get(url, params=params, timeout=REQUEST_TIMEOUT_SECONDS)
            response.raise_for_status()
            payload = response.json()
        except requests.RequestException as exc:
            raise JobSearchError(f"Adzuna search failed: {exc}") from exc

        listings = [
            listing
            for entry in payload.get("results", [])
            if (listing := self._normalize(entry, country_code)) is not None
        ]
        if work_model:
            listings = [listing for listing in listings if listing.remote_type == work_model]
        return listings

    def _normalize(self, entry: dict, country_code: str) -> JobListing | None:
        try:
            external_id = entry.get("id")
            title = entry.get("title")
            if not external_id or not title:
                return None
            company = (entry.get("company") or {}).get("display_name")
            location_name = (entry.get("location") or {}).get("display_name")
            publication_date = None
            created = entry.get("created")
            if created:
                publication_date = datetime.fromisoformat(created.replace("Z", "+00:00")).date()
            description = entry.get("description") or ""
            return JobListing(
                source=self.name,
                external_id=str(external_id),
                title=title,
                company=company,
                location=location_name,
                country=country_code.upper(),
                publication_date=publication_date,
                description=description,
                employment_type=entry.get("contract_type"),
                # Adzuna has no structured remote/hybrid/onsite field; a
                # best-effort text signal beats none, per the "where data
                # permit it" wording in docs/requirements.md.
                remote_type=self._guess_remote_type(description),
                salary_min=entry.get("salary_min"),
                salary_max=entry.get("salary_max"),
                currency=None,
                source_url=entry.get("redirect_url"),
            )
        except Exception:
            # A malformed entry is skipped, not allowed to break the whole search.
            return None

    @staticmethod
    def _guess_remote_type(description: str) -> str | None:
        text = description.lower()[:500]
        if "remote" not in text:
            return None
        negations = ("no remote", "not remote", "non-remote", "non remote")
        if any(negation in text for negation in negations):
            return None
        return "remote"
