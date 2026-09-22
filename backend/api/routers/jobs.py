from datetime import date, timedelta

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.api.deps import get_db
from backend.api.schemas import (
    AnalyzeJobRequest,
    JobMatchOut,
    JobOut,
    JobSearchResponse,
    MatchedEvidenceOut,
    RequirementMatchOut,
)
from backend.models.job import Job
from backend.models.matching import JobMatch
from backend.providers.jobs import get_job_providers
from backend.providers.llm import get_llm_provider
from backend.schemas.job_listing import JobListing
from backend.services.evidence.store import EvidenceStore
from backend.services.jobs.analysis import analyze_and_match
from backend.services.jobs.search import search_all_providers
from backend.services.jobs.store import JobStore
from backend.services.matching.store import MatchStore

router = APIRouter(prefix="/jobs", tags=["jobs"])


@router.get("/search", response_model=JobSearchResponse)
def search_jobs(
    keywords: str = "",
    country: str | None = None,
    location: str | None = None,
    days_back: int = 0,
    work_model: str | None = None,
) -> JobSearchResponse:
    published_after = date.today() - timedelta(days=days_back) if days_back else None
    result = search_all_providers(
        get_job_providers(),
        keywords,
        country=country,
        location=location,
        published_after=published_after,
        work_model=work_model,
    )
    return JobSearchResponse(listings=result.listings, provider_errors=result.provider_errors)


@router.post("/listing", response_model=JobOut)
def save_listing(listing: JobListing, db: Session = Depends(get_db)) -> JobOut:
    job = JobStore(db).save_job_listing(listing)
    return JobOut.model_validate(job)


@router.get("", response_model=list[JobOut])
def list_jobs(db: Session = Depends(get_db)) -> list[JobOut]:
    return [JobOut.model_validate(job) for job in JobStore(db).list_jobs()]


@router.get("/{job_id}", response_model=JobOut)
def get_job(job_id: str, db: Session = Depends(get_db)) -> JobOut:
    job = JobStore(db).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    return JobOut.model_validate(job)


@router.post("/analyze", response_model=JobMatchOut)
def analyze_job(payload: AnalyzeJobRequest, db: Session = Depends(get_db)) -> JobMatchOut:
    try:
        job, job_match = analyze_and_match(
            db,
            payload.candidate_id,
            get_llm_provider(),
            description_text=payload.description_text,
            job_id=payload.job_id,
        )
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return _build_job_match_out(db, job, job_match)


@router.get("/{job_id}/match", response_model=JobMatchOut)
def get_job_match(job_id: str, candidate_id: str, db: Session = Depends(get_db)) -> JobMatchOut:
    job = JobStore(db).get_job(job_id)
    if job is None:
        raise HTTPException(status_code=404, detail="Job not found")
    job_match = MatchStore(db).get_latest_match(candidate_id, job_id)
    if job_match is None:
        raise HTTPException(status_code=404, detail="No match yet — analyze this job first")
    return _build_job_match_out(db, job, job_match)


def _build_job_match_out(db: Session, job: Job, job_match: JobMatch) -> JobMatchOut:
    requirement_by_id = {r.id: r for r in job.requirements}
    evidence_by_id = {e.id: e for e in EvidenceStore(db).list_evidence(job_match.candidate_id)}
    rows = []
    for rm in job_match.requirement_matches:
        requirement = requirement_by_id.get(rm.requirement_id)
        if requirement is None:
            continue
        matched = [
            MatchedEvidenceOut(id=eid, concept=evidence_by_id[eid].concept)
            for eid in rm.matched_evidence_ids
            if eid in evidence_by_id
        ]
        rows.append(
            RequirementMatchOut(
                requirement_id=requirement.id,
                concept=requirement.concept,
                category=requirement.category.value,
                importance=requirement.importance.value,
                match_type=rm.match_type.value,
                explanation=rm.explanation,
                matched_evidence=matched,
            )
        )
    return JobMatchOut(
        id=job_match.id,
        job_id=job.id,
        candidate_id=job_match.candidate_id,
        score=job_match.score,
        requirement_matches=rows,
    )
