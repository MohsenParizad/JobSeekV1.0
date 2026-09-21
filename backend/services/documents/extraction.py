"""Turns raw document text into a list of structured, unverified evidence
items via an injected LLMProvider. Persistence is not this service's job —
see backend/services/evidence/store.py.
"""
from backend.providers.llm.base import LLMProvider
from backend.schemas.evidence import ExtractedEvidenceItem


class EvidenceExtractionService:
    def __init__(self, llm_provider: LLMProvider):
        self._llm_provider = llm_provider

    def extract(self, document_text: str) -> list[ExtractedEvidenceItem]:
        if not document_text.strip():
            return []
        return self._llm_provider.extract_evidence(document_text)
