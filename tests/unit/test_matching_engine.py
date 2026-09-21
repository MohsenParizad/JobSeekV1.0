from backend.models.evidence import Confidence, Evidence, EvidenceCategory, EvidenceStatus
from backend.models.job import JobRequirement, RequirementCategory, RequirementImportance
from backend.schemas.matching import TransferableClassification
from backend.services.matching.engine import MatchingEngine, MatchResult, score_matches


def _evidence(id_, concept, description="", category=EvidenceCategory.TECHNOLOGY) -> Evidence:
    return Evidence(
        id=id_,
        candidate_id="c1",
        category=category,
        concept=concept,
        description=description,
        source_text=description or concept,
        confidence=Confidence.HIGH,
        status=EvidenceStatus.APPROVED,
    )


def _requirement(concept, category=RequirementCategory.TECHNOLOGY, importance=RequirementImportance.REQUIRED):
    return JobRequirement(
        id="r1",
        job_id="j1",
        category=category,
        concept=concept,
        importance=importance,
        source_text=concept,
    )


def test_exact_concept_match_is_direct():
    engine = MatchingEngine()
    result = engine.match(_requirement("Python"), [_evidence("e1", "Python", "Built services in Python.")])
    assert result.match_type == "direct"
    assert result.matched_evidence_ids == ["e1"]


def test_synonym_match_is_direct():
    engine = MatchingEngine()
    result = engine.match(
        _requirement("Postgres"), [_evidence("e1", "PostgreSQL", "Administered a PostgreSQL database.")]
    )
    assert result.match_type == "direct"


def test_concept_mentioned_in_description_is_direct():
    engine = MatchingEngine()
    result = engine.match(
        _requirement("Docker"), [_evidence("e1", "Containerization", "Used Docker to containerize services.")]
    )
    assert result.match_type == "direct"


def test_partial_token_overlap_is_related():
    engine = MatchingEngine()
    result = engine.match(_requirement("AWS Lambda"), [_evidence("e1", "AWS", "Deployed services on AWS.")])
    assert result.match_type == "related"


def test_no_overlap_is_missing_without_llm_provider():
    engine = MatchingEngine()
    result = engine.match(_requirement("Snowflake"), [_evidence("e1", "Python", "Built services in Python.")])
    assert result.match_type == "missing"
    assert result.matched_evidence_ids == []


def test_missing_with_no_evidence_at_all():
    engine = MatchingEngine()
    result = engine.match(_requirement("Python"), [])
    assert result.match_type == "missing"


class _AlwaysTransferableProvider:
    def classify_transferable(self, requirement, candidate_evidence):
        return TransferableClassification(is_transferable=True, evidence_indices=[0], explanation="Plausible transfer.")


class _NeverTransferableProvider:
    def classify_transferable(self, requirement, candidate_evidence):
        return TransferableClassification(is_transferable=False)


def test_llm_can_upgrade_missing_to_transferable():
    engine = MatchingEngine(llm_provider=_AlwaysTransferableProvider())
    requirement = _requirement("Predictive Maintenance", category=RequirementCategory.SKILL)
    evidence = [
        _evidence(
            "e1", "Machine Learning", "Built ML models for industrial equipment.", category=EvidenceCategory.SKILL
        )
    ]
    result = engine.match(requirement, evidence)
    assert result.match_type == "transferable"
    assert result.matched_evidence_ids == ["e1"]
    assert result.explanation == "Plausible transfer."


def test_llm_never_consulted_or_overrides_a_direct_match():
    engine = MatchingEngine(llm_provider=_AlwaysTransferableProvider())
    result = engine.match(_requirement("Python"), [_evidence("e1", "Python", "Built services in Python.")])
    assert result.match_type == "direct"


def test_llm_declining_leaves_requirement_missing():
    engine = MatchingEngine(llm_provider=_NeverTransferableProvider())
    result = engine.match(_requirement("Snowflake"), [_evidence("e1", "Python", "Built services in Python.")])
    assert result.match_type == "missing"


def test_score_matches_is_deterministic_and_bounded():
    required = _requirement("Python", importance=RequirementImportance.REQUIRED)
    preferred = _requirement("AWS", importance=RequirementImportance.PREFERRED)
    pairs = [
        (required, MatchResult("direct", ["e1"], "matched")),
        (preferred, MatchResult("missing", [], "no evidence")),
    ]
    score = score_matches(pairs)
    assert 0 <= score <= 100
    assert score == round(100 * (3 * 1.0) / (3 * 1.0 + 3 * 0.5), 1)


def test_score_matches_handles_empty_requirement_list():
    assert score_matches([]) == 0.0
