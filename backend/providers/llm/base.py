"""LLMProvider interface. Nothing outside this package should import an SDK
client directly — services depend on this abstraction so the underlying
model is swappable (see docs/architecture.md), the same pattern used for
job providers in later releases.
"""
from abc import ABC, abstractmethod

from backend.schemas.evidence import ExtractedEvidenceItem
from backend.schemas.generation import EvidenceForGeneration, GeneratedApplication, RequirementMatchForGeneration
from backend.schemas.job import ExtractedJobRequirements
from backend.schemas.matching import EvidenceForMatching, RequirementForMatching, TransferableClassification


class LLMProvider(ABC):
    @abstractmethod
    def extract_evidence(self, document_text: str) -> list[ExtractedEvidenceItem]:
        """Extract structured, provenance-tracked evidence from raw CV/reference text."""
        raise NotImplementedError

    @abstractmethod
    def extract_job_requirements(self, description_text: str) -> ExtractedJobRequirements:
        """Extract structured, provenance-tracked requirements from a job description."""
        raise NotImplementedError

    @abstractmethod
    def classify_transferable(
        self,
        requirement: RequirementForMatching,
        candidate_evidence: list[EvidenceForMatching],
    ) -> TransferableClassification:
        """Best-effort classification of whether any of the candidate's verified
        evidence plausibly transfers to a requirement that the deterministic
        matcher (backend/services/matching/engine.py) already found no
        direct or related evidence for. Called only for that fallback case —
        it can never override a deterministic match.
        """
        raise NotImplementedError

    @abstractmethod
    def generate_application(
        self,
        candidate_name: str,
        job_title: str,
        company: str | None,
        verified_evidence: list[EvidenceForGeneration],
        requirement_matches: list[RequirementMatchForGeneration],
    ) -> GeneratedApplication:
        """Draft tailored application material (summary, CV suggestions, cover
        letter), grounded only in `verified_evidence`, plus a self-reported
        list of every checkable claim made — which
        backend/services/generation/validator.py then independently checks
        against that same evidence. The model is instructed never to assert
        a qualification `verified_evidence` doesn't support, but that
        instruction is advisory; the validator is the actual safeguard.
        """
        raise NotImplementedError
