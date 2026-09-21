from backend.providers.llm.fake_provider import FakeLLMProvider
from backend.services.documents.extraction import EvidenceExtractionService


def test_extract_returns_empty_list_for_blank_text():
    service = EvidenceExtractionService(FakeLLMProvider())
    assert service.extract("   ") == []


def test_extract_finds_known_concepts_with_source_text():
    service = EvidenceExtractionService(FakeLLMProvider())
    text = "Built data pipelines in Python.\nManaged a PostgreSQL database."
    items = service.extract(text)

    concepts = {item.concept for item in items}
    assert concepts == {"Python", "PostgreSQL"}

    python_item = next(item for item in items if item.concept == "Python")
    assert python_item.source_text == "Built data pipelines in Python."


def test_extract_does_not_confuse_java_and_javascript():
    service = EvidenceExtractionService(FakeLLMProvider())
    items = service.extract("Wrote frontend code in JavaScript.")
    concepts = {item.concept for item in items}
    assert concepts == {"JavaScript"}
