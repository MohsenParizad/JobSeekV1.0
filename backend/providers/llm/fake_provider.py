"""Deterministic stand-in for the real LLM call.

Used automatically when no ANTHROPIC_API_KEY is configured, and in unit
tests, so the rest of the app (persistence, verification workflow, UI) is
fully exercisable and testable without hitting a real API or requiring a key.
"""
import re

from backend.providers.llm.base import LLMProvider
from backend.schemas.evidence import ExtractedEvidenceItem

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
