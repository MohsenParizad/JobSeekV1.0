"""The evidence-grounded generation safeguard: checks every claim the
generation model says it made against the candidate's *verified* evidence.

Deliberately deterministic and independent of the model that generated the
text — reuses the exact same keyword/synonym grounding logic as the
MatchingEngine (backend/services/text_matching.py) rather than asking the
same LLM to grade its own homework. This is what turns "the model was told
not to hallucinate" into an actual, checkable guarantee (see the AI-safety
NFR in docs/requirements.md and the "Evidence-Grounded Generation" concept
in the product vision).
"""
from backend.models.evidence import Evidence
from backend.schemas.generation import ClaimValidation, GeneratedClaim
from backend.services.text_matching import concept_matches


def validate_claims(claims: list[GeneratedClaim], verified_evidence: list[Evidence]) -> list[ClaimValidation]:
    results = []
    for claim in claims:
        matched = next(
            (e for e in verified_evidence if concept_matches(claim.concept, e.concept, e.description)),
            None,
        )
        results.append(
            ClaimValidation(
                statement=claim.statement,
                concept=claim.concept,
                supported=matched is not None,
                matched_evidence_concept=matched.concept if matched else None,
            )
        )
    return results
