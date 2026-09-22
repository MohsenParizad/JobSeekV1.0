"""Shared keyword/synonym text-matching primitives.

Used by both the MatchingEngine (job requirement vs. candidate evidence)
and the claim validator (generated application text vs. candidate evidence)
— the same deterministic grounding discipline applies in both places, so
the logic lives in one spot instead of being duplicated.
"""
import re

_STOPWORDS = {"and", "the", "with", "of", "in", "for", "a", "an", "to", "on"}

# variant -> canonical form, so e.g. "Postgres" and "PostgreSQL" are treated as the same concept
_SYNONYMS: dict[str, str] = {
    "postgres": "postgresql",
    "psql": "postgresql",
    "ml": "machine learning",
    "js": "javascript",
    "k8s": "kubernetes",
}


def normalize(text: str) -> str:
    return re.sub(r"[^a-z0-9 ]", " ", text.lower()).strip()


def canonical(term: str) -> str:
    return _SYNONYMS.get(term, term)


def significant_tokens(text: str) -> set[str]:
    return {token for token in normalize(text).split() if len(token) >= 3 and token not in _STOPWORDS}


def concept_matches(concept: str, other_concept: str, other_context: str = "") -> bool:
    """True if `concept` names the same thing as `other_concept` (exact match
    or known synonym), or `concept` appears as a whole word inside
    `other_context` (e.g. a free-text description mentioning it).
    """
    norm_concept = normalize(concept)
    if not norm_concept:
        return False
    norm_other = normalize(other_concept)
    if norm_concept == norm_other:
        return True
    if canonical(norm_concept) == canonical(norm_other):
        return True
    return bool(re.search(rf"\b{re.escape(norm_concept)}\b", normalize(other_context)))


def concepts_related(concept: str, other_concept: str, other_context: str = "") -> bool:
    """True if `concept` shares at least one significant word with
    `other_concept`/`other_context` — a looser signal than `concept_matches`.
    """
    concept_tokens = significant_tokens(concept)
    other_tokens = significant_tokens(other_concept) | significant_tokens(other_context)
    return bool(concept_tokens & other_tokens)
