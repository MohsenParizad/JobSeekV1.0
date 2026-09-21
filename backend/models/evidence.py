"""Evidence domain model: Candidate -> Documents -> Evidence, with provenance.

This intentionally matches the domain model in docs/architecture.md so the
later job/matching tables (V0.2+) can reference `Evidence` without changes
here.
"""
import enum
import uuid
from datetime import datetime, timezone

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.models.base import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class DocumentType(str, enum.Enum):
    CV = "cv"
    EMPLOYMENT_REFERENCE = "employment_reference"
    CERTIFICATE = "certificate"


class EvidenceCategory(str, enum.Enum):
    SKILL = "skill"
    EXPERIENCE = "experience"
    TECHNOLOGY = "technology"
    EDUCATION = "education"
    PROJECT = "project"


class Confidence(str, enum.Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class EvidenceStatus(str, enum.Enum):
    PENDING = "pending"
    APPROVED = "approved"
    REJECTED = "rejected"


class Candidate(Base):
    __tablename__ = "candidates"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    name: Mapped[str] = mapped_column(String(255))
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    documents: Mapped[list["Document"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="candidate", cascade="all, delete-orphan")


class Document(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"))
    document_type: Mapped[DocumentType] = mapped_column(Enum(DocumentType))
    original_filename: Mapped[str] = mapped_column(String(255))
    storage_path: Mapped[str] = mapped_column(String(500))
    raw_text: Mapped[str | None] = mapped_column(Text, nullable=True)
    uploaded_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)

    candidate: Mapped[Candidate] = relationship(back_populates="documents")
    evidence: Mapped[list["Evidence"]] = relationship(back_populates="document", cascade="all, delete-orphan")


class Evidence(Base):
    """One extracted, provenance-tracked claim about a candidate.

    `source_text` is the verbatim excerpt the claim was derived from, so the
    application can always answer "why do you believe this candidate has
    PostgreSQL experience?" instead of only reporting a score.
    """

    __tablename__ = "evidence"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    candidate_id: Mapped[str] = mapped_column(ForeignKey("candidates.id"))
    document_id: Mapped[str | None] = mapped_column(ForeignKey("documents.id"), nullable=True)

    category: Mapped[EvidenceCategory] = mapped_column(Enum(EvidenceCategory))
    concept: Mapped[str] = mapped_column(String(255))
    description: Mapped[str] = mapped_column(Text)
    source_text: Mapped[str] = mapped_column(Text)
    organization: Mapped[str | None] = mapped_column(String(255), nullable=True)
    confidence: Mapped[Confidence] = mapped_column(Enum(Confidence))
    status: Mapped[EvidenceStatus] = mapped_column(Enum(EvidenceStatus), default=EvidenceStatus.PENDING)

    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=_utcnow, onupdate=_utcnow)

    candidate: Mapped[Candidate] = relationship(back_populates="evidence")
    document: Mapped[Document | None] = relationship(back_populates="evidence")
