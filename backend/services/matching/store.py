"""Persistence boundary for job-matching runs."""
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.matching import JobMatch, RequirementMatch
from backend.services.matching.engine import MatchResult


class MatchStore:
    def __init__(self, session: Session):
        self._session = session

    def save_match(
        self,
        candidate_id: str,
        job_id: str,
        results_by_requirement_id: dict[str, MatchResult],
        score: float,
    ) -> JobMatch:
        job_match = JobMatch(candidate_id=candidate_id, job_id=job_id, score=score)
        self._session.add(job_match)
        self._session.flush()

        rows = [
            RequirementMatch(
                job_match_id=job_match.id,
                requirement_id=requirement_id,
                match_type=result.match_type,
                matched_evidence_ids=result.matched_evidence_ids,
                explanation=result.explanation,
            )
            for requirement_id, result in results_by_requirement_id.items()
        ]
        self._session.add_all(rows)
        self._session.commit()
        self._session.refresh(job_match)
        return job_match

    def get_latest_match(self, candidate_id: str, job_id: str) -> JobMatch | None:
        stmt = (
            select(JobMatch)
            .where(JobMatch.candidate_id == candidate_id, JobMatch.job_id == job_id)
            .order_by(JobMatch.created_at.desc())
        )
        return self._session.scalars(stmt).first()
