from backend.schemas.job_listing import JobListing
from backend.services.jobs.store import JobStore


def _listing(external_id="ext-1"):
    return JobListing(
        source="arbeitnow",
        external_id=external_id,
        title="Python Developer",
        company="Acme",
        location="Berlin, Germany",
        description="We need a Python developer.",
        remote_type="remote",
    )


def test_save_job_listing_is_idempotent(session):
    store = JobStore(session)
    first = store.save_job_listing(_listing())
    second = store.save_job_listing(_listing())
    assert first.id == second.id
    assert first.requirements == []


def test_save_job_listing_persists_canonical_fields(session):
    job = JobStore(session).save_job_listing(_listing())
    assert job.source == "arbeitnow"
    assert job.external_id == "ext-1"
    assert job.location == "Berlin, Germany"
    assert job.remote_type == "remote"
    assert job.raw_description == "We need a Python developer."
    assert job.retrieved_at is not None


def test_different_external_ids_are_not_deduplicated(session):
    store = JobStore(session)
    first = store.save_job_listing(_listing(external_id="ext-1"))
    second = store.save_job_listing(_listing(external_id="ext-2"))
    assert first.id != second.id
