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


def _filter_grounded(items: list[ExtractedEvidenceItem], document_text: str) -> list[ExtractedEvidenceItem]:
    normalized_doc = " ".join(document_text.split()).lower()
    grounded = []
    for item in items:
        normalized_source = " ".join(item.source_text.split()).lower()
        if normalized_source and normalized_source in normalized_doc:
            grounded.append(item)
    return grounded
