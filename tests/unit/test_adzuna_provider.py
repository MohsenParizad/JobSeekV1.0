from datetime import date
from unittest.mock import patch

import pytest
import requests

from backend.providers.jobs.adzuna import AdzunaProvider
from backend.providers.jobs.base import JobSearchError


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


ADZUNA_PAYLOAD = {
    "results": [
        {
            "id": "123456",
            "title": "Data Scientist",
            "company": {"display_name": "Data Corp"},
            "location": {"display_name": "London, UK"},
            "description": "We need a data scientist. Remote work available.",
            "redirect_url": "https://www.adzuna.co.uk/jobs/details/123456",
            "created": "2024-05-01T12:00:00Z",
            "salary_min": 40000.0,
            "salary_max": 60000.0,
            "contract_type": "permanent",
        },
        {
            "id": "654321",
            "title": "Onsite Analyst",
            "company": {"display_name": "Office Co"},
            "location": {"display_name": "Manchester, UK"},
            "description": "Fully onsite role, no remote option.",
            "redirect_url": "https://www.adzuna.co.uk/jobs/details/654321",
            "created": "2024-04-15T09:00:00Z",
        },
    ]
}


def test_normalizes_entries():
    with patch("backend.providers.jobs.adzuna.requests.get", return_value=_FakeResponse(ADZUNA_PAYLOAD)):
        results = AdzunaProvider("id", "key").search_jobs("data scientist")

    assert len(results) == 2
    first = next(r for r in results if r.external_id == "123456")
    assert first.source == "adzuna"
    assert first.title == "Data Scientist"
    assert first.company == "Data Corp"
    assert first.location == "London, UK"
    assert first.salary_min == 40000.0
    assert first.salary_max == 60000.0
    assert first.publication_date == date(2024, 5, 1)
    assert first.remote_type == "remote"


def test_work_model_filter():
    with patch("backend.providers.jobs.adzuna.requests.get", return_value=_FakeResponse(ADZUNA_PAYLOAD)):
        results = AdzunaProvider("id", "key").search_jobs("data scientist", work_model="remote")

    assert {r.external_id for r in results} == {"123456"}


def test_malformed_entry_is_skipped_not_fatal():
    payload = {"results": [{"title": "No id here"}, ADZUNA_PAYLOAD["results"][0]]}
    with patch("backend.providers.jobs.adzuna.requests.get", return_value=_FakeResponse(payload)):
        results = AdzunaProvider("id", "key").search_jobs("data scientist")

    assert len(results) == 1
    assert results[0].external_id == "123456"


def test_request_error_raises_job_search_error():
    with patch("backend.providers.jobs.adzuna.requests.get", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(JobSearchError):
            AdzunaProvider("id", "key").search_jobs("data scientist")
