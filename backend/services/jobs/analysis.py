"""Orchestrates a full job-analysis run: extract requirements from a job
description, persist the job, match each requirement against the
candidate's verified evidence, and persist the match.

Kept UI-agnostic — the Streamlit app calls this one function, and it's
directly unit-testable and reusable from the future FastAPI layer without
touching business logic (see docs/architecture.md).
"""
from sqlalchemy.orm import Session

from backend.models.evidence import EvidenceStatus
from backend.models.job import Job
from backend.models.matching import JobMatch
from backend.providers.llm.base import LLMProvider
from backend.services.evidence.store import EvidenceStore
from backend.services.jobs.store import JobStore
from backend.services.matching.engine import MatchingEngine, score_matches
from backend.services.matching.store import MatchStore


def analyze_and_match(
    session: Session,
    candidate_id: str,
    llm_provider: LLMProvider,
    description_text: str,
) -> tuple[Job, JobMatch]:
    extracted = llm_provider.extract_job_requirements(description_text)
    job = JobStore(session).save_job(extracted, raw_description=description_text)

    verified_evidence = EvidenceStore(session).list_evidence(candidate_id, status=EvidenceStatus.APPROVED)

    engine = MatchingEngine(llm_provider)
    results_by_requirement_id = {}
    pairs = []
    for requirement in job.requirements:
        result = engine.match(requirement, verified_evidence)
        results_by_requirement_id[requirement.id] = result
        pairs.append((requirement, result))

    score = score_matches(pairs)
    job_match = MatchStore(session).save_match(candidate_id, job.id, results_by_requirement_id, score)
    return job, job_match
