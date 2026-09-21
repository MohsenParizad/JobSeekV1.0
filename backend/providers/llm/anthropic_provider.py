"""Real LLM-backed extraction via the Anthropic API.

Uses forced tool-use so the model's output is schema-validated rather than
parsed out of free text, then applies a grounding check: any item whose
`source_text` doesn't actually appear in the input document is dropped. This
is a first line of defence against invented evidence; the full evidence
validator (checking generated application text against verified evidence)
lands in V0.3.
"""
import anthropic

from backend.config import settings
from backend.providers.llm.base import LLMProvider
from backend.schemas.evidence import ExtractedEvidenceBatch, ExtractedEvidenceItem
from backend.schemas.job import ExtractedJobRequirements
from backend.schemas.matching import EvidenceForMatching, RequirementForMatching, TransferableClassification

EXTRACTION_TOOL = {
    "name": "record_evidence",
    "description": "Record structured, evidence-backed claims extracted from a candidate document.",
    "input_schema": ExtractedEvidenceBatch.model_json_schema(),
}

EXTRACTION_SYSTEM_PROMPT = """\
You extract verifiable professional evidence from a candidate's CV or employment reference.

Rules:
- Only extract claims that are explicitly stated or very strongly implied by the text.
- `source_text` must be a verbatim or near-verbatim excerpt from the document that supports the \
claim. Never write a source_text that does not appear in the input.
- Do not infer skills the document does not mention. If a technology is only tangentially related \
to something mentioned, do not include it.
- Use "high" confidence only for explicit statements, "medium" for reasonable and closely-tied \
inferences, "low" for weak inferences. When in doubt, omit the item rather than guess.
- Extract skills, technologies, experience (roles/responsibilities), education, and projects as \
separate items.
"""

JOB_EXTRACTION_TOOL = {
    "name": "record_job_requirements",
    "description": "Record structured requirements extracted from a job vacancy description.",
    "input_schema": ExtractedJobRequirements.model_json_schema(),
}

JOB_EXTRACTION_SYSTEM_PROMPT = """\
You extract structured requirements from a job vacancy description.

Rules:
- `source_text` for each requirement must be a verbatim or near-verbatim excerpt from the job \
description that states it. Never write a source_text that does not appear in the input.
- importance is "required" when the text presents it as mandatory (e.g. "must have", "required", \
listed under required qualifications) and "preferred" when it is presented as a bonus/nice-to-have.
- category is "language" for spoken/written language requirements (set language_level to the \
stated proficiency, e.g. "B2", "C1", "fluent"), and skill/technology/education/experience otherwise.
- Infer seniority and work_model only when the text states or clearly implies them; otherwise omit them.
- List each distinct requirement as its own item, even if several appear in one sentence.
"""

TRANSFERABLE_TOOL = {
    "name": "classify_transferable_evidence",
    "description": (
        "Decide whether any of the candidate's verified evidence transfers to a job requirement "
        "that a deterministic matcher already found no direct or related evidence for."
    ),
    "input_schema": TransferableClassification.model_json_schema(),
}

TRANSFERABLE_SYSTEM_PROMPT = """\
A deterministic matcher already checked for direct and related evidence for this job requirement \
and found none. Your only job is to decide whether any of the candidate's OTHER verified evidence \
plausibly transfers to it — meaning related background that doesn't literally state the \
requirement but would reasonably help.

Rules:
- Only cite evidence from the numbered list given to you, by its index. Never invent evidence.
- If nothing plausibly transfers, set is_transferable to false and leave evidence_indices empty.
- Be conservative: a generally strong candidate is not itself transferable evidence — the cited \
evidence must have a concrete, explainable link to the requirement.
- explanation must justify the link concretely, referencing what the cited evidence actually says.
"""


class AnthropicProvider(LLMProvider):
    def __init__(self, api_key: str | None = None, model: str | None = None):
        key = api_key or settings.anthropic_api_key
        if not key:
            raise ValueError("ANTHROPIC_API_KEY is not configured")
        self._client = anthropic.Anthropic(api_key=key)
        self._model = model or settings.anthropic_model

    def extract_evidence(self, document_text: str) -> list[ExtractedEvidenceItem]:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=EXTRACTION_SYSTEM_PROMPT,
            tools=[EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "record_evidence"},
            messages=[{"role": "user", "content": f"Document text:\n\n{document_text}"}],
        )
        tool_use = next(block for block in response.content if block.type == "tool_use")
        batch = ExtractedEvidenceBatch.model_validate(tool_use.input)
        return _filter_grounded(batch.items, document_text)

    def extract_job_requirements(self, description_text: str) -> ExtractedJobRequirements:
        response = self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            system=JOB_EXTRACTION_SYSTEM_PROMPT,
            tools=[JOB_EXTRACTION_TOOL],
            tool_choice={"type": "tool", "name": "record_job_requirements"},
            messages=[{"role": "user", "content": f"Job description:\n\n{description_text}"}],
        )
        tool_use = next(block for block in response.content if block.type == "tool_use")
        parsed = ExtractedJobRequirements.model_validate(tool_use.input)
        parsed.requirements = _filter_grounded(parsed.requirements, description_text)
        return parsed

    def classify_transferable(
        self,
        requirement: RequirementForMatching,
        candidate_evidence: list[EvidenceForMatching],
    ) -> TransferableClassification:
        if not candidate_evidence:
            return TransferableClassification(is_transferable=False)

        evidence_listing = "\n".join(
            f"{i}. [{e.category}] {e.concept} — {e.description}" for i, e in enumerate(candidate_evidence)
        )
        prompt = (
            f"Job requirement ({requirement.importance}, category={requirement.category}): {requirement.concept}\n"
            f'Requirement context: "{requirement.source_text}"\n\n'
            f"Candidate's verified evidence:\n{evidence_listing}"
        )
        response = self._client.messages.create(
            model=self._model,
            max_tokens=1024,
            system=TRANSFERABLE_SYSTEM_PROMPT,
            tools=[TRANSFERABLE_TOOL],
            tool_choice={"type": "tool", "name": "classify_transferable_evidence"},
            messages=[{"role": "user", "content": prompt}],
        )
        tool_use = next(block for block in response.content if block.type == "tool_use")
        result = TransferableClassification.model_validate(tool_use.input)
        valid_indices = [i for i in result.evidence_indices if 0 <= i < len(candidate_evidence)]
        if not valid_indices:
            return TransferableClassification(is_transferable=False)
        return TransferableClassification(is_transferable=True, evidence_indices=valid_indices, explanation=result.explanation)


def _filter_grounded(items: list, source_document_text: str) -> list:
    """Drops any item whose `source_text` doesn't actually appear in the
    source document — a defence-in-depth check against the model inventing
    evidence or requirements. Works for both ExtractedEvidenceItem and
    ExtractedRequirementItem since both carry a `source_text` field.
    """
    normalized_doc = " ".join(source_document_text.split()).lower()
    grounded = []
    for item in items:
        normalized_source = " ".join(item.source_text.split()).lower()
        if normalized_source and normalized_source in normalized_doc:
            grounded.append(item)
    return grounded
