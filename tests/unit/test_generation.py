"""End-to-end V0.3 slice test: generation grounded in verified evidence and
an existing job match, independently validated. Includes the scenario named
explicitly in the product vision — a generated cover letter claiming AWS
experience the candidate doesn't have must be caught, even if the
generation model itself claims to have grounded it.
"""
import pytest

from backend.models.evidence import EvidenceStatus
from backend.providers.llm.fake_provider import FakeLLMProvider
from backend.schemas.evidence import ExtractedEvidenceItem
from backend.schemas.generation import GeneratedApplication, GeneratedClaim
from backend.services.evidence.store import EvidenceStore
from backend.services.generation.service import generate_application_material, revalidate
from backend.services.generation.store import GenerationStore
from backend.services.jobs.analysis import analyze_and_match


def _approve_python_evidence(store: EvidenceStore, candidate_id: str) -> None:
    saved = store.save_pending_evidence(
        candidate_id,
        document_id=None,
        items=[
            ExtractedEvidenceItem(
                category="technology",
                concept="Python",
                description="Built data pipelines in Python.",
                source_text="Built data pipelines in Python.",
                organization=None,
                confidence="high",
            )
        ],
    )
    store.approve(saved[0].id)


def test_generation_requires_an_existing_job_match(session):
    store = EvidenceStore(session)
    candidate = store.get_or_create_candidate("No Match Yet")
    _approve_python_evidence(store, candidate.id)

    with pytest.raises(ValueError):
        generate_application_material(session, candidate.id, candidate.name, "nonexistent-job-id", FakeLLMProvider())


class _HallucinatingProvider(FakeLLMProvider):
    """Behaves like the fake provider for extraction/matching, but its
    generation claims one skill the candidate actually has (Python) and one
    it doesn't (AWS) — simulating a model that ignored its grounding
    instructions, so the validator must be the thing that actually catches it.
    """

    def generate_application(self, candidate_name, job_title, company, verified_evidence, requirement_matches):
        return GeneratedApplication(
            tailored_summary=f"{candidate_name} is a strong fit for {job_title}.",
            emphasized_experience=["Python", "AWS"],
            cv_suggestions=["Highlight your Python experience.", "Highlight your AWS experience."],
            cover_letter=(
                f"Dear Hiring Team,\n\nI have experience with Python and AWS, "
                f"making me a great fit for the {job_title} role.\n\nSincerely,\n{candidate_name}"
            ),
            claims=[
                GeneratedClaim(statement="experience with Python", concept="Python"),
                GeneratedClaim(statement="experience with AWS", concept="AWS"),
            ],
        )


def test_hallucinated_claim_is_caught_by_the_validator(session):
    store = EvidenceStore(session)
    candidate = store.get_or_create_candidate("Ada Example")
    _approve_python_evidence(store, candidate.id)

    description = "Data Scientist\nMust have strong Python and AWS experience.\n"
    job, job_match = analyze_and_match(session, candidate.id, FakeLLMProvider(), description)

    record, validations = generate_application_material(
        session, candidate.id, candidate.name, job.id, _HallucinatingProvider()
    )

    by_concept = {v.concept: v for v in validations}
    assert by_concept["Python"].supported is True
    assert by_concept["AWS"].supported is False
    assert by_concept["AWS"].matched_evidence_concept is None

    # persisted, and re-readable/re-validatable later
    latest = GenerationStore(session).get_latest(candidate.id, job.id)
    assert latest.id == record.id
    verified_evidence = store.list_evidence(candidate.id)
    replayed = revalidate(latest, [e for e in verified_evidence if e.status.value == "approved"])
    replayed_by_concept = {v.concept: v for v in replayed}
    assert replayed_by_concept["AWS"].supported is False


def test_revalidate_reflects_newly_approved_evidence(session):
    store = EvidenceStore(session)
    candidate = store.get_or_create_candidate("Grace Example")
    _approve_python_evidence(store, candidate.id)

    description = "Data Scientist\nMust have strong Python and AWS experience.\n"
    job, _ = analyze_and_match(session, candidate.id, FakeLLMProvider(), description)
    record, validations = generate_application_material(
        session, candidate.id, candidate.name, job.id, _HallucinatingProvider()
    )
    assert any(not v.supported for v in validations)

    # candidate later gets AWS evidence approved too
    saved = store.save_pending_evidence(
        candidate.id,
        document_id=None,
        items=[
            ExtractedEvidenceItem(
                category="technology",
                concept="AWS",
                description="Deployed services on AWS.",
                source_text="Deployed services on AWS.",
                organization=None,
                confidence="high",
            )
        ],
    )
    store.approve(saved[0].id)

    current_evidence = store.list_evidence(candidate.id, status=EvidenceStatus.APPROVED)
    replayed = revalidate(record, current_evidence)
    assert all(v.supported for v in replayed)
