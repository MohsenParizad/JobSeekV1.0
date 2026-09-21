"""Persisted result of matching one job's requirements against a candidate's
verified evidence — the JobMatch/RequirementMatch entities from
docs/architecture.md.
"""
import enum
from datetime import datetime

from sqlalchemy import JSON, DateTime, Enum, Float, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base
from backend.models.util import new_id, utcnow


class MatchType(str, enum.Enum):
    DIRECT = "direct"
    RELATED = "related"
    TRANSFERABLE = "transferable"
    MISSING = "missing"


class JobMatch(Base):
    """One matching run of a candidate against a job. A new run is created
    each time analysis is re-triggered rather than overwriting the last one,
    so history is kept; callers read the latest one via
    `MatchStore.get_latest_match`.
    """

    __tablename__ = "job_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))
    score: Mapped[float] = mapped_column(Float)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    requirement_matches: Mapped[list["RequirementMatch"]] = relationship(
        back_populates="job_match", cascade="all, delete-orphan"
    )


class RequirementMatch(Base):
    """Classification of a single job requirement against the candidate's
    verified evidence. `matched_evidence_ids` cites the specific evidence
    rows the classification relies on, and `explanation` is always
    grounded in that evidence — never a bare score (see
    docs/requirements.md's AI safety / explainability NFRs).
    """

    __tablename__ = "requirement_matches"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_match_id: Mapped[str] = mapped_column(ForeignKey("job_matches.id"))
    requirement_id: Mapped[str] = mapped_column(ForeignKey("job_requirements.id"))
    match_type: Mapped[MatchType] = mapped_column(Enum(MatchType))
    matched_evidence_ids: Mapped[list[str]] = mapped_column(JSON, default=list)
    explanation: Mapped[str] = mapped_column(Text)

    job_match: Mapped[JobMatch] = relationship(back_populates="requirement_matches")
