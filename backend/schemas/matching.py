"""Schemas for the matching layer.

`RequirementForMatching`/`EvidenceForMatching` are the context passed to an
LLMProvider for the optional transferable-evidence classification — plain
data, decoupled from the ORM, so providers never import SQLAlchemy models.
"""
from pydantic import BaseModel, Field


class RequirementForMatching(BaseModel):
    concept: str
    category: str
    importance: str
    source_text: str


class EvidenceForMatching(BaseModel):
    id: str
    concept: str
    description: str
    category: str


class TransferableClassification(BaseModel):
    """Output of the LLM's transferable-evidence check. `evidence_indices`
    refer to positions in the `EvidenceForMatching` list passed alongside
    the requirement — never a free-form claim, so the result can be
    validated against the actual list before being trusted.
    """

    is_transferable: bool
    evidence_indices: list[int] = Field(default_factory=list)
    explanation: str | None = None
