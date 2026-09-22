"""Schemas for the application-generation layer.

`EvidenceForGeneration`/`RequirementMatchForGeneration` are the context
passed to the LLM — plain data, decoupled from the ORM. `GeneratedClaim` is
the generation model's own self-reported list of checkable claims embedded
in the material it wrote; `ClaimValidation` is the deterministic validator's
verdict on each one (see services/generation/validator.py).
"""
from pydantic import BaseModel, Field


class EvidenceForGeneration(BaseModel):
    id: str
    concept: str
    description: str
    category: str


class RequirementMatchForGeneration(BaseModel):
    concept: str
    importance: str
    match_type: str  # "direct" | "related" | "transferable" | "missing"


class GeneratedClaim(BaseModel):
    """One concrete, checkable factual claim embedded in the generated text
    (e.g. "experience with PostgreSQL"). The generation model reports these
    itself, alongside the prose, so every claim it makes can be checked.
    """

    statement: str = Field(description="The claim as phrased in the generated text")
    concept: str = Field(description="The underlying skill/technology/experience concept being claimed")


class GeneratedApplication(BaseModel):
    tailored_summary: str
    emphasized_experience: list[str] = Field(description="Existing evidence concepts worth emphasizing for this job")
    cv_suggestions: list[str]
    cover_letter: str
    claims: list[GeneratedClaim] = Field(
        description="Every concrete, checkable claim made across the fields above"
    )


class ClaimValidation(BaseModel):
    statement: str
    concept: str
    supported: bool
    matched_evidence_concept: str | None = None
