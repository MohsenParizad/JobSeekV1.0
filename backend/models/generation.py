"""Persisted generated application material for a candidate x job pair.

`claims` stores the generation model's own self-reported list of checkable
claims (see schemas/generation.py's GeneratedClaim) — kept as raw JSON so
the claim validator can be re-run against the candidate's *current* verified
evidence whenever this record is viewed, rather than freezing a stale
validation result from generation time.
"""
from datetime import datetime

from sqlalchemy import JSON, DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base
from backend.models.util import new_id, utcnow


class GeneratedApplicationRecord(Base):
    __tablename__ = "generated_applications"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"))
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))

    tailored_summary: Mapped[str] = mapped_column(Text)
    emphasized_experience: Mapped[list[str]] = mapped_column(JSON, default=list)
    cv_suggestions: Mapped[list[str]] = mapped_column(JSON, default=list)
    cover_letter: Mapped[str] = mapped_column(Text)
    claims: Mapped[list[dict]] = mapped_column(JSON, default=list)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    job = relationship("Job")
