"""Pydantic schemas: the strict contract for what the LLM extraction call may
return, plus read models for the API/UI. Keeping these separate from the
SQLAlchemy models means the LLM's output shape can never accidentally leak
persistence details (or vice versa).
"""
from typing import Literal

from pydantic import BaseModel, Field

EvidenceCategoryLiteral = Literal["skill", "experience", "technology", "education", "project"]
ConfidenceLiteral = Literal["low", "medium", "high"]


class ExtractedEvidenceItem(BaseModel):
    """One evidence claim as produced by the extraction LLM call.

    `source_text` MUST be a verbatim (or near-verbatim) excerpt of the input
    document — the extraction prompt instructs the model accordingly, and the
    validator in extraction.py rejects items where it can't find a close
    match in the source text, which is how the pipeline avoids inventing
    evidence out of thin air.
    """

    category: EvidenceCategoryLiteral
    concept: str = Field(description="Short name of the skill/technology/role/degree/project, e.g. 'PostgreSQL'")
    description: str = Field(description="One sentence, human-readable summary of this evidence")
    source_text: str = Field(description="Verbatim excerpt from the document that supports this claim")
    organization: str | None = Field(default=None, description="Employer/institution this evidence relates to, if any")
    confidence: ConfidenceLiteral = Field(description="How explicitly the source text supports this claim")


class ExtractedEvidenceBatch(BaseModel):
    items: list[ExtractedEvidenceItem]


class EvidenceOut(BaseModel):
    """Read-model returned to the UI, including persistence + verification state."""

    id: str
    category: str
    concept: str
    description: str
    source_text: str
    organization: str | None
    confidence: str
    status: str

    model_config = {"from_attributes": True}
