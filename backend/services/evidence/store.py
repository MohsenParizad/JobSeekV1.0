"""The only component that touches the database for candidates, documents,
and evidence directly. Later services (matching, generation) must read
verified evidence through this, not via ad hoc queries elsewhere.
"""
from pathlib import Path

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.models.evidence import Candidate, Document, DocumentType, Evidence, EvidenceStatus
from backend.schemas.evidence import ExtractedEvidenceItem


class EvidenceStore:
    def __init__(self, session: Session):
        self._session = session

    # --- candidates ---

    def get_or_create_candidate(self, name: str, email: str | None = None) -> Candidate:
        candidate = self._session.scalar(select(Candidate).where(Candidate.name == name))
        if candidate:
            return candidate
        candidate = Candidate(name=name, email=email)
        self._session.add(candidate)
        self._session.commit()
        self._session.refresh(candidate)
        return candidate

    # --- documents ---

    def save_document(
        self,
        candidate_id: str,
        document_type: DocumentType,
        original_filename: str,
        storage_path: Path,
        raw_text: str,
    ) -> Document:
        document = Document(
            candidate_id=candidate_id,
            document_type=document_type,
            original_filename=original_filename,
            storage_path=str(storage_path),
            raw_text=raw_text,
        )
        self._session.add(document)
        self._session.commit()
        self._session.refresh(document)
        return document

    def delete_document(self, document_id: str) -> None:
        """Removes the stored file and cascades to delete its evidence rows."""
        document = self._session.get(Document, document_id)
        if document is None:
            return
        storage_path = Path(document.storage_path)
        if storage_path.exists():
            storage_path.unlink()
        self._session.delete(document)
        self._session.commit()

    # --- evidence ---

    def save_pending_evidence(
        self,
        candidate_id: str,
        document_id: str | None,
        items: list[ExtractedEvidenceItem],
    ) -> list[Evidence]:
        rows = [
            Evidence(
                candidate_id=candidate_id,
                document_id=document_id,
                category=item.category,
                concept=item.concept,
                description=item.description,
                source_text=item.source_text,
                organization=item.organization,
                confidence=item.confidence,
                status=EvidenceStatus.PENDING,
            )
            for item in items
        ]
        self._session.add_all(rows)
        self._session.commit()
        for row in rows:
            self._session.refresh(row)
        return rows

    def list_evidence(self, candidate_id: str, status: EvidenceStatus | None = None) -> list[Evidence]:
        stmt = select(Evidence).where(Evidence.candidate_id == candidate_id)
        if status is not None:
            stmt = stmt.where(Evidence.status == status)
        return list(self._session.scalars(stmt))

    def approve(self, evidence_id: str, concept: str | None = None, description: str | None = None) -> Evidence:
        evidence = self._get_evidence(evidence_id)
        if concept is not None:
            evidence.concept = concept
        if description is not None:
            evidence.description = description
        evidence.status = EvidenceStatus.APPROVED
        self._session.commit()
        self._session.refresh(evidence)
        return evidence

    def reject(self, evidence_id: str) -> Evidence:
        evidence = self._get_evidence(evidence_id)
        evidence.status = EvidenceStatus.REJECTED
        self._session.commit()
        self._session.refresh(evidence)
        return evidence

    def _get_evidence(self, evidence_id: str) -> Evidence:
        evidence = self._session.get(Evidence, evidence_id)
        if evidence is None:
            raise ValueError(f"Evidence {evidence_id} not found")
        return evidence
