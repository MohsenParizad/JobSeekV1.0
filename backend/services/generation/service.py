"""Orchestrates the full V0.3 slice: generate tailored application material
grounded in a candidate's verified evidence and an existing job match, then
independently validate every claim it makes.

Kept UI-agnostic, like analyze_and_match in services/jobs/analysis.py, so
it's directly unit-testable and reusable from the future FastAPI layer.
"""
from sqlalchemy.orm import Session

from backend.models.evidence import Evidence, EvidenceStatus
from backend.models.generation import GeneratedApplicationRecord
from backend.providers.llm.base import LLMProvider
from backend.schemas.generation import (
    ClaimValidation,
    EvidenceForGeneration,
    GeneratedClaim,
    RequirementMatchForGeneration,
)
from backend.services.evidence.store import EvidenceStore
from backend.services.generation.store import GenerationStore
from backend.services.generation.validator import validate_claims
from backend.services.jobs.store import JobStore
from backend.services.matching.store import MatchStore


def generate_application_material(
    session: Session,
    candidate_id: str,
    candidate_name: str,
    job_id: str,
    llm_provider: LLMProvider,
) -> tuple[GeneratedApplicationRecord, list[ClaimValidation]]:
    job = JobStore(session).get_job(job_id)
    if job is None:
        raise ValueError(f"Job {job_id} not found")

    job_match = MatchStore(session).get_latest_match(candidate_id, job_id)
    if job_match is None:
        raise ValueError("Run job analysis for this job before generating application material.")

    verified_evidence = EvidenceStore(session).list_evidence(candidate_id, status=EvidenceStatus.APPROVED)
    requirement_by_id = {r.id: r for r in job.requirements}

    generated = llm_provider.generate_application(
        candidate_name=candidate_name,
        job_title=job.title,
        company=job.company,
        verified_evidence=[
            EvidenceForGeneration(id=e.id, concept=e.concept, description=e.description, category=e.category.value)
            for e in verified_evidence
        ],
        requirement_matches=[
            RequirementMatchForGeneration(
                concept=requirement_by_id[rm.requirement_id].concept,
                importance=requirement_by_id[rm.requirement_id].importance.value,
                match_type=rm.match_type.value,
            )
            for rm in job_match.requirement_matches
            if rm.requirement_id in requirement_by_id
        ],
    )

    claim_validations = validate_claims(generated.claims, verified_evidence)
    record = GenerationStore(session).save(candidate_id, job_id, generated)
    return record, claim_validations


def revalidate(record: GeneratedApplicationRecord, verified_evidence: list[Evidence]) -> list[ClaimValidation]:
    """Re-runs claim validation for an already-persisted record against the
    candidate's *current* verified evidence, so a claim that was unsupported
    at generation time but has since been backed by newly-approved evidence
    (or vice versa) is judged correctly rather than showing a stale result.
    """
    claims = [GeneratedClaim(**claim) for claim in record.claims]
    return validate_claims(claims, verified_evidence)
