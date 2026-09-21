"""Job + requirement domain model (see docs/architecture.md).

V0.2 only supports manually-entered job descriptions (`source="manual"`);
V0.4 adds job providers that populate the same tables with
`source="arbeitnow"`/`"adzuna"` etc., without changing this schema.
"""
import enum
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base
from backend.models.util import new_id, utcnow


class RequirementCategory(str, enum.Enum):
    SKILL = "skill"
    TECHNOLOGY = "technology"
    LANGUAGE = "language"
    EDUCATION = "education"
    EXPERIENCE = "experience"


class RequirementImportance(str, enum.Enum):
    REQUIRED = "required"
    PREFERRED = "preferred"


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    title: Mapped[str] = mapped_column(String(255))
    company: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source: Mapped[str] = mapped_column(String(50), default="manual")
    seniority: Mapped[str | None] = mapped_column(String(50), nullable=True)
    work_model: Mapped[str | None] = mapped_column(String(50), nullable=True)
    raw_description: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)

    requirements: Mapped[list["JobRequirement"]] = relationship(back_populates="job", cascade="all, delete-orphan")


class JobRequirement(Base):
    """One requirement/qualification pulled from a job description, with the
    verbatim excerpt it was derived from (same provenance principle as
    `Evidence` — see backend/models/evidence.py).
    """

    __tablename__ = "job_requirements"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=new_id)
    job_id: Mapped[str] = mapped_column(ForeignKey("jobs.id"))

    category: Mapped[RequirementCategory] = mapped_column(Enum(RequirementCategory))
    concept: Mapped[str] = mapped_column(String(255))
    importance: Mapped[RequirementImportance] = mapped_column(Enum(RequirementImportance))
    language_level: Mapped[str | None] = mapped_column(String(10), nullable=True)
    source_text: Mapped[str] = mapped_column(Text)

    job: Mapped[Job] = relationship(back_populates="requirements")
