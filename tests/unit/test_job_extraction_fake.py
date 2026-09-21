from backend.providers.llm.fake_provider import FakeLLMProvider


def test_fake_provider_extracts_requirements_and_importance():
    provider = FakeLLMProvider()
    description = (
        "Data Scientist\n"
        "Must have strong Python and PostgreSQL experience.\n"
        "AWS experience is a nice to have.\n"
    )
    extracted = provider.extract_job_requirements(description)

    assert extracted.title == "Data Scientist"
    by_concept = {item.concept: item for item in extracted.requirements}
    assert by_concept["Python"].importance == "required"
    assert by_concept["PostgreSQL"].importance == "required"
    assert by_concept["AWS"].importance == "preferred"


def test_fake_provider_extracts_language_level():
    provider = FakeLLMProvider()
    description = "Backend Engineer\nGerman C1 is required for this role.\n"
    extracted = provider.extract_job_requirements(description)

    language_reqs = [item for item in extracted.requirements if item.category == "language"]
    assert len(language_reqs) == 1
    assert language_reqs[0].concept == "German"
    assert language_reqs[0].language_level == "C1"


def test_fake_provider_handles_empty_description():
    provider = FakeLLMProvider()
    extracted = provider.extract_job_requirements("")
    assert extracted.title == "Untitled role"
    assert extracted.requirements == []
