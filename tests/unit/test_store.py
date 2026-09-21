from backend.models.evidence import DocumentType, EvidenceStatus
from backend.schemas.evidence import ExtractedEvidenceItem
from backend.services.evidence.store import EvidenceStore


def test_get_or_create_candidate_is_idempotent(session):
    store = EvidenceStore(session)
    first = store.get_or_create_candidate("Ada Lovelace", email="ada@example.com")
    second = store.get_or_create_candidate("Ada Lovelace")
    assert first.id == second.id


def test_save_pending_evidence_then_approve(session):
    store = EvidenceStore(session)
    candidate = store.get_or_create_candidate("Grace Hopper")

    item = ExtractedEvidenceItem(
        category="technology",
        concept="COBOL",
        description="Worked with COBOL.",
        source_text="Developed programs in COBOL.",
        organization="Navy",
        confidence="high",
    )
    saved = store.save_pending_evidence(candidate.id, document_id=None, items=[item])
    assert len(saved) == 1
    assert saved[0].status == EvidenceStatus.PENDING

    pending = store.list_evidence(candidate.id, status=EvidenceStatus.PENDING)
    assert len(pending) == 1

    approved = store.approve(saved[0].id, concept="COBOL (edited)")
    assert approved.status == EvidenceStatus.APPROVED
    assert approved.concept == "COBOL (edited)"

    verified = store.list_evidence(candidate.id, status=EvidenceStatus.APPROVED)
    assert len(verified) == 1
    assert verified[0].concept == "COBOL (edited)"


def test_reject_evidence(session):
    store = EvidenceStore(session)
    candidate = store.get_or_create_candidate("Katherine Johnson")
    item = ExtractedEvidenceItem(
        category="skill",
        concept="Orbital mechanics",
        description="Calculated trajectories.",
        source_text="Performed trajectory calculations.",
        organization=None,
        confidence="high",
    )
    saved = store.save_pending_evidence(candidate.id, document_id=None, items=[item])
    rejected = store.reject(saved[0].id)
    assert rejected.status == EvidenceStatus.REJECTED


def test_delete_document_removes_file_and_cascades_evidence(session, tmp_path):
    store = EvidenceStore(session)
    candidate = store.get_or_create_candidate("Margaret Hamilton")

    file_path = tmp_path / "cv.pdf"
    file_path.write_bytes(b"%PDF-1.4 fake")

    document = store.save_document(
        candidate_id=candidate.id,
        document_type=DocumentType.CV,
        original_filename="cv.pdf",
        storage_path=file_path,
        raw_text="Software engineer.",
    )
    item = ExtractedEvidenceItem(
        category="experience",
        concept="Software engineering",
        description="Worked as a software engineer.",
        source_text="Software engineer.",
        organization=None,
        confidence="medium",
    )
    store.save_pending_evidence(candidate.id, document.id, [item])

    assert file_path.exists()
    store.delete_document(document.id)
    assert not file_path.exists()
    assert store.list_evidence(candidate.id) == []
