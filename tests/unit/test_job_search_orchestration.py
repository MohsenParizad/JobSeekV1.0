from backend.providers.jobs.base import JobProvider, JobSearchError
from backend.schemas.job_listing import JobListing
from backend.services.jobs.search import search_all_providers


class _WorkingProvider(JobProvider):
    name = "working"

    def search_jobs(self, keywords, country=None, location=None, published_after=None, work_model=None):
        return [
            JobListing(
                source=self.name, external_id="1", title="Python Developer", company="Acme", location="Berlin",
                description="desc",
            )
        ]


class _FailingProvider(JobProvider):
    name = "failing"

    def search_jobs(self, keywords, country=None, location=None, published_after=None, work_model=None):
        raise JobSearchError("provider is down")


class _DuplicateProvider(JobProvider):
    name = "duplicate"

    def search_jobs(self, keywords, country=None, location=None, published_after=None, work_model=None):
        return [
            JobListing(
                source=self.name, external_id="2", title="Python Developer", company="Acme", location="Berlin",
                description="desc",
            )
        ]


def test_one_provider_failing_does_not_break_the_others():
    result = search_all_providers([_WorkingProvider(), _FailingProvider()], "python")
    assert len(result.listings) == 1
    assert result.provider_errors == {"failing": "provider is down"}


def test_results_from_multiple_providers_are_deduplicated():
    result = search_all_providers([_WorkingProvider(), _DuplicateProvider()], "python")
    assert len(result.listings) == 1


def test_all_providers_succeeding_reports_no_errors():
    result = search_all_providers([_WorkingProvider()], "python")
    assert result.provider_errors == {}
