from backend.config import settings
from backend.providers.llm.base import LLMProvider


def get_llm_provider() -> LLMProvider:
    """Returns the real Anthropic-backed provider if a key is configured,
    otherwise falls back to the deterministic fake so the app still runs."""
    if settings.anthropic_api_key:
        from backend.providers.llm.anthropic_provider import AnthropicProvider

        return AnthropicProvider()
    from backend.providers.llm.fake_provider import FakeLLMProvider

    return FakeLLMProvider()
