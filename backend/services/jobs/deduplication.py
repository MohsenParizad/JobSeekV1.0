"""Deterministic cross-provider vacancy deduplication.

Deliberately not an LLM call — conventional normalization is cheap,
reliable, and reuses the same primitives as matching/claim validation (see
docs/requirements.md's explicit guidance to start deduplication with
conventional algorithms, not an LLM).
"""
from backend.schemas.job_listing import JobListing
from backend.services.text_matching import normalize


def _dedup_key(listing: JobListing) -> tuple[str, str, str]:
    return (
        normalize(listing.company or ""),
        normalize(listing.title),
        normalize(listing.location or ""),
    )


def deduplicate_listings(listings: list[JobListing]) -> list[JobListing]:
    """Collapses listings with the same normalized company + title + location
    (typically the same vacancy posted on multiple providers), keeping the
    first occurrence."""
    seen: set[tuple[str, str, str]] = set()
    deduped = []
    for listing in listings:
        key = _dedup_key(listing)
        if key in seen:
            continue
        seen.add(key)
        deduped.append(listing)
    return deduped
