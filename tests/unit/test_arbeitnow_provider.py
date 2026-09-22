from datetime import date
from unittest.mock import patch

import pytest
import requests

from backend.providers.jobs.arbeitnow import ArbeitnowProvider
from backend.providers.jobs.base import JobSearchError


class _FakeResponse:
    def __init__(self, payload):
        self._payload = payload

    def raise_for_status(self):
        pass

    def json(self):
        return self._payload


ARBEITNOW_PAGE = {
    "data": [
        {
            "slug": "python-dev-berlin",
            "company_name": "Acme GmbH",
            "title": "Python Developer",
            "description": "We need a Python developer with PostgreSQL experience.",
            "remote": True,
            "url": "https://www.arbeitnow.com/jobs/python-dev-berlin",
            "tags": ["python", "postgresql"],
            "job_types": ["Full time"],
            "location": "Berlin, Germany",
            "created_at": 1700000000,
        },
        {
            "slug": "java-dev-munich",
            "company_name": "Beta AG",
            "title": "Java Developer",
            "description": "Java and Spring experience required.",
            "remote": False,
            "url": "https://www.arbeitnow.com/jobs/java-dev-munich",
            "tags": ["java"],
            "job_types": ["Full time"],
            "location": "Munich, Germany",
            "created_at": 1690000000,
        },
    ],
    "links": {"next": None},
}


def test_search_filters_by_keyword():
    with patch("backend.providers.jobs.arbeitnow.requests.get", return_value=_FakeResponse(ARBEITNOW_PAGE)):
        results = ArbeitnowProvider().search_jobs("Python")

    assert len(results) == 1
    assert results[0].title == "Python Developer"
    assert results[0].source == "arbeitnow"
    assert results[0].external_id == "python-dev-berlin"
    assert results[0].remote_type == "remote"
    assert results[0].publication_date == date(2023, 11, 14)


def test_search_filters_by_work_model():
    with patch("backend.providers.jobs.arbeitnow.requests.get", return_value=_FakeResponse(ARBEITNOW_PAGE)):
        results = ArbeitnowProvider().search_jobs("", work_model="remote")

    assert {r.external_id for r in results} == {"python-dev-berlin"}


def test_search_filters_by_published_after():
    with patch("backend.providers.jobs.arbeitnow.requests.get", return_value=_FakeResponse(ARBEITNOW_PAGE)):
        results = ArbeitnowProvider().search_jobs("", published_after=date(2023, 11, 1))

    assert {r.external_id for r in results} == {"python-dev-berlin"}


def test_malformed_entry_is_skipped_not_fatal():
    payload = {"data": [{"title": "No slug here"}, ARBEITNOW_PAGE["data"][0]], "links": {"next": None}}
    with patch("backend.providers.jobs.arbeitnow.requests.get", return_value=_FakeResponse(payload)):
        results = ArbeitnowProvider().search_jobs("")

    assert len(results) == 1
    assert results[0].external_id == "python-dev-berlin"


def test_request_error_raises_job_search_error():
    with patch("backend.providers.jobs.arbeitnow.requests.get", side_effect=requests.ConnectionError("boom")):
        with pytest.raises(JobSearchError):
            ArbeitnowProvider().search_jobs("python")
