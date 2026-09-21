"""LLMProvider interface. Nothing outside this package should import an SDK
client directly — services depend on this abstraction so the underlying
model is swappable (see docs/architecture.md), the same pattern used for
job providers in later releases.
"""
from abc import ABC, abstractmethod

from backend.schemas.evidence import ExtractedEvidenceItem


class LLMProvider(ABC):
    @abstractmethod
    def extract_evidence(self, document_text: str) -> list[ExtractedEvidenceItem]:
        """Extract structured, provenance-tracked evidence from raw CV/reference text."""
        raise NotImplementedError
