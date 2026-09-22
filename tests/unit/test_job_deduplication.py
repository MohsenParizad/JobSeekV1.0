from backend.schemas.job_listing import JobListing
from backend.services.jobs.deduplication import deduplicate_listings


def _listing(source, external_id, title, company, location):
    return JobListing(
        source=source, external_id=external_id, title=title, company=company, location=location, description="desc"
    )


def test_collapses_same_vacancy_across_providers():
    listings = [
        _listing("arbeitnow", "a1", "Python Developer", "Acme GmbH", "Berlin"),
        _listing("adzuna", "z1", "python developer", "ACME GMBH", "berlin"),
    ]
    result = deduplicate_listings(listings)
    assert len(result) == 1
    assert result[0].source == "arbeitnow"  # first occurrence kept


def test_keeps_distinct_vacancies():
    listings = [
        _listing("arbeitnow", "a1", "Python Developer", "Acme", "Berlin"),
        _listing("arbeitnow", "a2", "Java Developer", "Acme", "Berlin"),
    ]
    result = deduplicate_listings(listings)
    assert len(result) == 2
