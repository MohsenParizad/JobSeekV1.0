"""End-to-end API test: candidate -> upload -> approve -> analyze -> generate,
mirroring the full Streamlit workflow but through the HTTP layer. Uses the
fake LLM provider automatically (no ANTHROPIC_API_KEY in the test env).
"""
import io
from unittest.mock import patch

import docx

from backend.providers.jobs.base import JobProvider
from backend.schemas.job_listing import JobListing


def _make_docx_bytes(text: str) -> bytes:
    document = docx.Document()
    document.add_paragraph(text)
    buffer = io.BytesIO()
    document.save(buffer)
    return buffer.getvalue()


def test_full_workflow(client):
    assert client.get("/health").json() == {"status": "ok"}

    resp = client.post("/candidates", json={"name": "Ada Example"})
    assert resp.status_code == 200
    candidate_id = resp.json()["id"]

    resp = client.get(f"/candidates/{candidate_id}")
    assert resp.status_code == 200
    assert resp.json()["name"] == "Ada Example"

    cv_bytes = _make_docx_bytes("Built data pipelines in Python.")
    resp = client.post(
        f"/candidates/{candidate_id}/documents",
        data={"document_type": "cv"},
        files={
            "file": (
                "cv.docx",
                cv_bytes,
                "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
            )
        },
    )
    assert resp.status_code == 200
    pending = resp.json()
    assert len(pending) == 1
    assert pending[0]["concept"] == "Python"
    assert pending[0]["status"] == "pending"
    evidence_id = pending[0]["id"]

    resp = client.patch(f"/evidence/{evidence_id}", json={"action": "approve"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "approved"

    resp = client.get(f"/candidates/{candidate_id}/evidence", params={"status": "approved"})
    assert resp.status_code == 200
    assert len(resp.json()) == 1

    resp = client.post(
        "/jobs/analyze",
        json={
            "candidate_id": candidate_id,
            "description_text": (
                "Data Scientist\nMust have strong Python experience.\nKubernetes experience is required.\n"
            ),
        },
    )
    assert resp.status_code == 200
    match = resp.json()
    job_id = match["job_id"]
    match_types = {rm["concept"]: rm["match_type"] for rm in match["requirement_matches"]}
    assert match_types["Python"] == "direct"
    assert match_types["Kubernetes"] == "missing"

    resp = client.get(f"/jobs/{job_id}/match", params={"candidate_id": candidate_id})
    assert resp.status_code == 200
    assert resp.json()["id"] == match["id"]

    resp = client.post(
        "/applications/generate",
        json={"candidate_id": candidate_id, "candidate_name": "Ada Example", "job_id": job_id},
    )
    assert resp.status_code == 200
    generated = resp.json()
    assert generated["job_id"] == job_id
    assert any(v["concept"] == "Python" and v["supported"] for v in generated["validations"])

    resp = client.get(f"/applications/{job_id}", params={"candidate_id": candidate_id})
    assert resp.status_code == 200
    assert resp.json()["id"] == generated["id"]


def test_get_unknown_candidate_returns_404(client):
    resp = client.get("/candidates/does-not-exist")
    assert resp.status_code == 404


def test_analyze_without_description_or_job_id_returns_400(client):
    resp = client.post("/candidates", json={"name": "No Input"})
    candidate_id = resp.json()["id"]
    resp = client.post("/jobs/analyze", json={"candidate_id": candidate_id})
    assert resp.status_code == 400


def test_get_match_before_analysis_returns_404(client):
    resp = client.post("/candidates", json={"name": "No Match"})
    candidate_id = resp.json()["id"]
    resp = client.post(
        "/jobs/listing",
        json={"source": "manual", "external_id": "x1", "title": "Some Job", "description": "desc"},
    )
    job_id = resp.json()["id"]
    resp = client.get(f"/jobs/{job_id}/match", params={"candidate_id": candidate_id})
    assert resp.status_code == 404


def test_job_search_endpoint_returns_shape(client):
    resp = client.get("/jobs/search", params={"keywords": "python"})
    assert resp.status_code == 200
    body = resp.json()
    assert "listings" in body
    assert "provider_errors" in body


class _FakeProviderWithResults(JobProvider):
    name = "fake"

    def search_jobs(self, keywords, country=None, location=None, published_after=None, work_model=None):
        return [
            JobListing(
                source=self.name,
                external_id="fake-1",
                title="Python Developer",
                company="Acme",
                location="Berlin",
                description="Build things in Python.",
                remote_type="remote",
            )
        ]


def test_job_search_endpoint_serializes_real_listings(client):
    # Regression test: JobListing (backend/schemas/job_listing.py) and
    # JobListingOut (backend/api/schemas.py) are separate Pydantic models
    # with identical fields — Pydantic does NOT auto-convert one into the
    # other, so the endpoint must explicitly build JobListingOut instances.
    # An empty listings list passes validation trivially, so this needs at
    # least one real result to actually catch the bug.
    with patch("backend.api.routers.jobs.get_job_providers", return_value=[_FakeProviderWithResults()]):
        resp = client.get("/jobs/search", params={"keywords": "python"})
    assert resp.status_code == 200
    body = resp.json()
    assert len(body["listings"]) == 1
    assert body["listings"][0]["external_id"] == "fake-1"
    assert body["listings"][0]["title"] == "Python Developer"
