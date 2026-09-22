"""The canonical, provider-agnostic job schema (see docs/requirements.md).

Every JobProvider normalizes its raw API response into this shape, so
nothing downstream — deduplication, persistence, the UI — needs to know
which provider a listing came from.
"""
from datetime import date
from typing import Literal

from pydantic import BaseModel

WorkModelLiteral = Literal["remote", "hybrid", "onsite"]


class JobListing(BaseModel):
    source: str  # "arbeitnow" | "adzuna" | ...
    external_id: str
    title: str
    company: str | None = None
    location: str | None = None
    country: str | None = None
    publication_date: date | None = None
    description: str
    employment_type: str | None = None
    remote_type: WorkModelLiteral | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    source_url: str | None = None
