"""End-to-end V0.2 slice test: manual job text in -> requirement extraction
-> matching against verified evidence -> persisted, explainable match out.
Uses the fake LLM provider so it needs no API key (see test conventions in
test_extraction.py / test_job_extraction_fake.py).
"""
from backend.models.evidence import EvidenceStatus
from backend.providers.llm.fake_provider import FakeLLMProvider
from backend.schemas.evidence import ExtractedEvidenceItem
from backend.services.evidence.store import EvidenceStore
from backend.services.jobs.analysis import analyze_and_match
from backend.services.matching.store import MatchStore


def test_analyze_and_match_distinguishes_supported_from_missing(session):
    store = EvidenceStore(session)
    candidate = store.get_or_create_candidate("Test Candidate")

    verified = store.save_pending_evidence(
        candidate.id,
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
    store.approve(verified[0].id)

    description = (
        "Data Scientist\n"
        "Must have strong Python experience.\n"
        "Kubernetes experience is required.\n"
    )
    job, job_match = analyze_and_match(session, candidate.id, FakeLLMProvider(), description)

    assert job.title == "Data Scientist"
    assert len(job.requirements) == 2

    match_types = {
        next(r for r in job.requirements if r.id == rm.requirement_id).concept: rm.match_type.value
        for rm in job_match.requirement_matches
    }
    assert match_types["Python"] == "direct"
    assert match_types["Kubernetes"] == "missing"
    assert 0 < job_match.score < 100  # one direct, one missing -> partial fit

    # persisted and retrievable as the latest match for this candidate/job
    latest = MatchStore(session).get_latest_match(candidate.id, job.id)
    assert latest.id == job_match.id
