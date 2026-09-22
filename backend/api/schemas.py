"""API request/response DTOs.

Deliberately separate from backend/schemas/* (those are LLM I/O contracts)
and from the SQLAlchemy models — the API layer has its own shape so a
change to either side doesn't ripple through the other (see
docs/architecture.md's layering principle).
"""
from datetime import date
from typing import Literal

from pydantic import BaseModel


class CandidateCreate(BaseModel):
    name: str
    email: str | None = None


class CandidateOut(BaseModel):
    id: str
    name: str
    email: str | None

    model_config = {"from_attributes": True}


class EvidenceOut(BaseModel):
    id: str
    category: str
    concept: str
    description: str
    source_text: str
    organization: str | None
    confidence: str
    status: str

    model_config = {"from_attributes": True}


class EvidenceUpdate(BaseModel):
    action: Literal["approve", "reject"]
    concept: str | None = None
    description: str | None = None


class JobListingOut(BaseModel):
    source: str
    external_id: str
    title: str
    company: str | None = None
    location: str | None = None
    country: str | None = None
    publication_date: date | None = None
    description: str
    employment_type: str | None = None
    remote_type: str | None = None
    salary_min: float | None = None
    salary_max: float | None = None
    currency: str | None = None
    source_url: str | None = None


class JobSearchResponse(BaseModel):
    listings: list[JobListingOut]
    provider_errors: dict[str, str]


class JobRequirementOut(BaseModel):
    id: str
    category: str
    concept: str
    importance: str
    language_level: str | None
    source_text: str

    model_config = {"from_attributes": True}


class JobOut(BaseModel):
    id: str
    title: str
    company: str | None
    source: str
    seniority: str | None
    work_model: str | None
    location: str | None
    country: str | None
    publication_date: date | None
    source_url: str | None
    raw_description: str
    requirements: list[JobRequirementOut] = []

    model_config = {"from_attributes": True}


class AnalyzeJobRequest(BaseModel):
    candidate_id: str
    description_text: str | None = None
    job_id: str | None = None


class MatchedEvidenceOut(BaseModel):
    id: str
    concept: str


class RequirementMatchOut(BaseModel):
    requirement_id: str
    concept: str
    category: str
    importance: str
    match_type: str
    explanation: str
    matched_evidence: list[MatchedEvidenceOut]


class JobMatchOut(BaseModel):
    id: str
    job_id: str
    candidate_id: str
    score: float
    requirement_matches: list[RequirementMatchOut]


class GenerateApplicationRequest(BaseModel):
    candidate_id: str
    candidate_name: str
    job_id: str


class ClaimValidationOut(BaseModel):
    statement: str
    concept: str
    supported: bool
    matched_evidence_concept: str | None


class GeneratedApplicationOut(BaseModel):
    id: str
    job_id: str
    candidate_id: str
    tailored_summary: str
    emphasized_experience: list[str]
    cv_suggestions: list[str]
    cover_letter: str
    validations: list[ClaimValidationOut]
