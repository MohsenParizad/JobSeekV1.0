from backend.services.text_matching import concept_matches, concepts_related


def test_exact_match():
    assert concept_matches("Python", "Python")


def test_synonym_match():
    assert concept_matches("Postgres", "PostgreSQL")
    assert concept_matches("PostgreSQL", "Postgres")


def test_concept_found_in_context_text():
    assert concept_matches("Docker", "Containerization", "Used Docker to containerize services.")


def test_no_match():
    assert not concept_matches("Snowflake", "Python", "Built data pipelines in Python.")


def test_empty_concept_never_matches():
    assert not concept_matches("", "Python", "Built data pipelines in Python.")


def test_related_via_shared_token():
    assert concepts_related("AWS Lambda", "AWS", "Deployed services on AWS.")


def test_unrelated_concepts():
    assert not concepts_related("Snowflake", "Python", "Built data pipelines in Python.")
