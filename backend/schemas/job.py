"""Pydantic schemas: the strict contract for what the job-requirement
extraction LLM call may return, plus read models. Mirrors the pattern in
schemas/evidence.py — the LLM never talks to the ORM directly.
"""
from typing import Literal

from pydantic import BaseModel, Field

RequirementCategoryLiteral = Literal["skill", "technology", "language", "education", "experience"]
ImportanceLiteral = Literal["required", "preferred"]
SeniorityLiteral = Literal["entry", "junior", "professional", "lead"]
WorkModelLiteral = Literal["remote", "hybrid", "onsite"]


class ExtractedRequirementItem(BaseModel):
    """One requirement as produced by the extraction LLM call.

    `source_text` MUST be a verbatim (or near-verbatim) excerpt of the job
    description — the same grounding discipline used for candidate evidence
    (see schemas/evidence.py), so a matching result can always point back to
    the exact sentence that stated the requirement.
    """

    category: RequirementCategoryLiteral
    concept: str = Field(description="Short name of the requirement, e.g. 'Python' or 'German'")
    importance: ImportanceLiteral
    language_level: str | None = Field(default=None, description="Only set when category is 'language', e.g. 'B2'")
    source_text: str = Field(description="Verbatim excerpt from the job description that states this requirement")


class ExtractedJobRequirements(BaseModel):
    title: str
    company: str | None = None
    seniority: SeniorityLiteral | None = None
    work_model: WorkModelLiteral | None = None
    requirements: list[ExtractedRequirementItem]


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
    seniority: str | None
    work_model: str | None
    raw_description: str

    model_config = {"from_attributes": True}
