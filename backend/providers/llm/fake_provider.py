"""Deterministic stand-in for the real LLM call.

Used automatically when no ANTHROPIC_API_KEY is configured, and in unit
tests, so the rest of the app (persistence, verification workflow, UI) is
fully exercisable and testable without hitting a real API or requiring a key.
"""
import re

from backend.providers.llm.base import LLMProvider
from backend.schemas.evidence import ExtractedEvidenceItem
from backend.schemas.generation import (
    EvidenceForGeneration,
    GeneratedApplication,
    GeneratedClaim,
    RequirementMatchForGeneration,
)
from backend.schemas.job import ExtractedJobRequirements, ExtractedRequirementItem
from backend.schemas.matching import EvidenceForMatching, RequirementForMatching, TransferableClassification

_SOFT_REQUIREMENT_MARKERS = ("nice to have", "preferred", "plus", "bonus")
_LANGUAGE_PATTERN = re.compile(
    r"\b(German|English|French|Spanish)\b.{0,15}?\b([ABC][12]|fluent|native)\b", re.IGNORECASE
)

# keyword -> (display name, category)
_KNOWN_CONCEPTS: dict[str, tuple[str, str]] = {
    "python": ("Python", "technology"),
    "postgresql": ("PostgreSQL", "technology"),
    "sql": ("SQL", "technology"),
    "machine learning": ("Machine Learning", "skill"),
    "docker": ("Docker", "technology"),
    "java": ("Java", "technology"),
    "javascript": ("JavaScript", "technology"),
    "react": ("React", "technology"),
    "aws": ("AWS", "technology"),
    "kubernetes": ("Kubernetes", "technology"),
    "fastapi": ("FastAPI", "technology"),
    "django": ("Django", "technology"),
    "streamlit": ("Streamlit", "technology"),
}


class FakeLLMProvider(LLMProvider):
    def extract_evidence(self, document_text: str) -> list[ExtractedEvidenceItem]:
        lines = [line.strip() for line in document_text.splitlines() if line.strip()]
        items: list[ExtractedEvidenceItem] = []
        seen: set[str] = set()
        for line in lines:
            lowered = line.lower()
            for keyword, (display_name, category) in _KNOWN_CONCEPTS.items():
                if keyword in seen:
                    continue
                if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                    seen.add(keyword)
                    items.append(
                        ExtractedEvidenceItem(
                            category=category,
                            concept=display_name,
                            description=f"Mentions {display_name} in the document.",
                            source_text=line,
                            organization=None,
                            confidence="medium",
                        )
                    )
        return items

    def extract_job_requirements(self, description_text: str) -> ExtractedJobRequirements:
        lines = [line.strip() for line in description_text.splitlines() if line.strip()]
        requirements: list[ExtractedRequirementItem] = []
        seen: set[str] = set()
        for line in lines:
            lowered = line.lower()
            importance = "preferred" if any(marker in lowered for marker in _SOFT_REQUIREMENT_MARKERS) else "required"
            for keyword, (display_name, category) in _KNOWN_CONCEPTS.items():
                if keyword in seen:
                    continue
                if re.search(rf"\b{re.escape(keyword)}\b", lowered):
                    seen.add(keyword)
                    requirements.append(
                        ExtractedRequirementItem(
                            category=category, concept=display_name, importance=importance, source_text=line
                        )
                    )
            language_match = _LANGUAGE_PATTERN.search(line)
            if language_match:
                requirements.append(
                    ExtractedRequirementItem(
                        category="language",
                        concept=language_match.group(1).title(),
                        importance=importance,
                        language_level=language_match.group(2).upper(),
                        source_text=line,
                    )
                )
        title = lines[0][:255] if lines else "Untitled role"
        return ExtractedJobRequirements(title=title, requirements=requirements)

    def classify_transferable(
        self,
        requirement: RequirementForMatching,
        candidate_evidence: list[EvidenceForMatching],
    ) -> TransferableClassification:
        # The fake provider never upgrades a requirement to "transferable" —
        # it exists to keep the deterministic matching path fully testable
        # without an API key. Tests that exercise the transferable upgrade
        # path inject a small custom stub instead (see test_matching_engine.py).
        return TransferableClassification(is_transferable=False)

    def generate_application(
        self,
        candidate_name: str,
        job_title: str,
        company: str | None,
        verified_evidence: list[EvidenceForGeneration],
        requirement_matches: list[RequirementMatchForGeneration],
    ) -> GeneratedApplication:
        # Deliberately simple and always fully grounded: every claim it makes
        # cites a concept straight from verified_evidence. It exists to keep
        # the generation workflow testable without an API key. Tests that
        # exercise the claim validator's rejection path inject a small
        # custom stub that hallucinates instead (see test_generation.py).
        company_phrase = f" at {company}" if company else ""
        if not verified_evidence:
            return GeneratedApplication(
                tailored_summary=f"{candidate_name} is applying for the {job_title} role{company_phrase}.",
                emphasized_experience=[],
                cv_suggestions=["Add and approve some evidence in your profile before generating tailored suggestions."],
                cover_letter=(
                    f"Dear Hiring Team,\n\nI am writing to express interest in the {job_title} "
                    f"role{company_phrase}.\n\nSincerely,\n{candidate_name}"
                ),
                claims=[],
            )

        top_concepts = [e.concept for e in verified_evidence[:5]]
        concepts_sentence = ", ".join(top_concepts)
        cover_letter = (
            f"Dear Hiring Team,\n\n"
            f"I am writing to apply for the {job_title} role{company_phrase}. "
            f"My background includes hands-on experience with {concepts_sentence}.\n\n"
            f"Sincerely,\n{candidate_name}"
        )
        return GeneratedApplication(
            tailored_summary=f"{candidate_name} brings verified experience in {concepts_sentence}.",
            emphasized_experience=top_concepts,
            cv_suggestions=[f"Highlight your {concept} experience near the top of your CV." for concept in top_concepts[:3]],
            cover_letter=cover_letter,
            claims=[
                GeneratedClaim(statement=f"experience with {concept}", concept=concept) for concept in top_concepts
            ],
        )
