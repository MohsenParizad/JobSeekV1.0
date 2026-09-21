"""Deterministic requirement-vs-evidence matcher.

Direct and related matches are pure keyword/synonym logic with no LLM
involved, so matching keeps working even if the AI provider is unavailable
(see the Reliability NFR in docs/requirements.md). An LLMProvider is only
consulted, optionally, to try to upgrade an otherwise-missing requirement to
"transferable" — it is never asked about, and can never override, a
requirement the deterministic pass already classified as direct or related.

This intentionally stays a keyword/synonym matcher rather than a semantic
one: it's cheap, fully offline, and its decisions are easy to explain,
which matters more here than recall. See docs/architecture.md.
"""
import re
from dataclasses import dataclass

from backend.models.evidence import Evidence
from backend.models.job import JobRequirement
from backend.providers.llm.base import LLMProvider
from backend.schemas.matching import EvidenceForMatching, RequirementForMatching

_STOPWORDS = {"and", "the", "with", "of", "in", "for", "a", "an", "to", "on"}

# variant -> canonical form, so e.g. "Postgres" and "PostgreSQL" are treated as the same concept
_SYNONYMS: dict[str, str] = {
    "postgres": "postgresql",
    "psql": "postgresql",
    "ml": "machine learning",
    "js": "javascript",
    "k8s": "kubernetes",
}

_MATCH_WEIGHTS = {"direct": 3, "related": 2, "transferable": 1, "missing": 0}
_IMPORTANCE_WEIGHTS = {"required": 1.0, "preferred": 0.5}


@dataclass
class MatchResult:
    match_type: str  # "direct" | "related" | "transferable" | "missing"
    matched_evidence_ids: list[str]
    explanation: str


def _normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).strip()


def _canonical(term: str) -> str:
    return _SYNONYMS.get(term, term)


def _significant_tokens(text: str) -> set[str]:
    return {token for token in _normalize(text).split() if len(token) >= 3 and token not in _STOPWORDS}


class MatchingEngine:
    def __init__(self, llm_provider: LLMProvider | None = None):
        self._llm_provider = llm_provider

    def match(self, requirement: JobRequirement, verified_evidence: list[Evidence]) -> MatchResult:
        direct = self._first_match(requirement, verified_evidence, self._is_direct)
        if direct is not None:
            return MatchResult(
                "direct", [direct.id], f"'{requirement.concept}' matches verified evidence '{direct.concept}'."
            )

        related = self._first_match(requirement, verified_evidence, self._is_related)
        if related is not None:
            return MatchResult(
                "related",
                [related.id],
                f"'{requirement.concept}' is related to verified evidence '{related.concept}'.",
            )

        if self._llm_provider is not None and verified_evidence:
            classification = self._llm_provider.classify_transferable(
                RequirementForMatching(
                    concept=requirement.concept,
                    category=requirement.category.value,
                    importance=requirement.importance.value,
                    source_text=requirement.source_text,
                ),
                [
                    EvidenceForMatching(
                        id=e.id, concept=e.concept, description=e.description, category=e.category.value
                    )
                    for e in verified_evidence
                ],
            )
            if classification.is_transferable and classification.evidence_indices:
                linked = [verified_evidence[i] for i in classification.evidence_indices]
                return MatchResult(
                    "transferable",
                    [e.id for e in linked],
                    classification.explanation or "Classified as transferable evidence.",
                )

        return MatchResult("missing", [], f"No verified evidence supports '{requirement.concept}'.")

    @staticmethod
    def _first_match(requirement, evidence_list, predicate):
        for evidence in evidence_list:
            if predicate(requirement, evidence):
                return evidence
        return None

    @staticmethod
    def _is_direct(requirement: JobRequirement, evidence: Evidence) -> bool:
        norm_req = _normalize(requirement.concept)
        norm_ev = _normalize(evidence.concept)
        if not norm_req:
            return False
        if norm_req == norm_ev:
            return True
        if _canonical(norm_req) == _canonical(norm_ev):
            return True
        return bool(re.search(rf"\b{re.escape(norm_req)}\b", _normalize(evidence.description)))

    @staticmethod
    def _is_related(requirement: JobRequirement, evidence: Evidence) -> bool:
        req_tokens = _significant_tokens(requirement.concept)
        ev_tokens = _significant_tokens(evidence.concept) | _significant_tokens(evidence.description)
        return bool(req_tokens & ev_tokens)


def score_matches(pairs: list[tuple[JobRequirement, MatchResult]]) -> float:
    """Deterministic, explainable fit score (0-100), computed programmatically
    rather than asked of the LLM (see docs/requirements.md's AI-safety NFR).
    A required requirement counts double a preferred one; an all-direct,
    required-only job scores 100.
    """
    total = 0.0
    max_total = 0.0
    for requirement, result in pairs:
        importance_weight = _IMPORTANCE_WEIGHTS[requirement.importance.value]
        total += _MATCH_WEIGHTS[result.match_type] * importance_weight
        max_total += _MATCH_WEIGHTS["direct"] * importance_weight
    if max_total == 0:
        return 0.0
    return round(100 * total / max_total, 1)
