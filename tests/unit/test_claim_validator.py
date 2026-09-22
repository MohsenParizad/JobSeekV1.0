from backend.models.evidence import Confidence, Evidence, EvidenceCategory, EvidenceStatus
from backend.schemas.generation import GeneratedClaim
from backend.services.generation.validator import validate_claims


def _evidence(id_, concept, description="") -> Evidence:
    return Evidence(
        id=id_,
        candidate_id="c1",
        category=EvidenceCategory.TECHNOLOGY,
        concept=concept,
        description=description,
        source_text=description or concept,
        confidence=Confidence.HIGH,
        status=EvidenceStatus.APPROVED,
    )


def test_supported_claim_is_flagged_supported():
    evidence = [_evidence("e1", "PostgreSQL", "Administered a PostgreSQL database.")]
    claims = [GeneratedClaim(statement="extensive experience with PostgreSQL", concept="PostgreSQL")]
    results = validate_claims(claims, evidence)
    assert results[0].supported is True
    assert results[0].matched_evidence_concept == "PostgreSQL"


def test_unsupported_claim_is_flagged_unsupported():
    # The exact AWS/Snowflake/SAP scenario from the product vision: the
    # candidate's evidence has nothing to do with AWS, so a generated claim
    # of AWS experience must be caught.
    evidence = [_evidence("e1", "Python", "Built data pipelines in Python.")]
    claims = [GeneratedClaim(statement="experience with AWS", concept="AWS")]
    results = validate_claims(claims, evidence)
    assert results[0].supported is False
    assert results[0].matched_evidence_concept is None


def test_synonym_claim_is_still_supported():
    evidence = [_evidence("e1", "PostgreSQL", "Administered a PostgreSQL database.")]
    claims = [GeneratedClaim(statement="worked with Postgres", concept="Postgres")]
    results = validate_claims(claims, evidence)
    assert results[0].supported is True


def test_no_evidence_means_every_claim_is_unsupported():
    claims = [GeneratedClaim(statement="experience with Python", concept="Python")]
    results = validate_claims(claims, [])
    assert results[0].supported is False


def test_empty_claims_returns_empty_list():
    assert validate_claims([], []) == []
