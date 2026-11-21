import pytest

from forms2json.adapters.outbound.llm.openai_compatible_client import OpenAiCompatibleLlmClient
from forms2json.config import Settings

SCHEMA = {
    "type": "object",
    "properties": {"title": {"type": "string"}},
    "required": ["title"],
}


@pytest.mark.integration
def test_local_runtime_returns_json_matching_the_schema() -> None:
    settings = Settings()  # LLM_BASE_URL / LLM_MODEL point at a running Ollama
    client = OpenAiCompatibleLlmClient(
        settings.llm_base_url, settings.llm_model, settings.llm_timeout_seconds
    )

    result = client.generate_json(
        "Extract the form title as JSON.",
        "WNIOSEK O WYDANIE DOWODU OSOBISTEGO\nImię: ____",
        SCHEMA,
    )

    assert isinstance(result.data["title"], str)
    assert result.usage.prompt_tokens > 0
    assert result.usage.completion_tokens > 0
