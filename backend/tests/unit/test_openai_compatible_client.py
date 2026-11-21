import json
from collections.abc import Callable

import httpx2
import pytest

from forms2json.adapters.outbound.llm.openai_compatible_client import (
    MAX_ATTEMPTS,
    OpenAiCompatibleLlmClient,
)
from forms2json.application.ports.llm_client import LlmCallFailed

SCHEMA = {"type": "object", "properties": {"title": {"type": "string"}}}


def completion(content: str, finish_reason: str = "stop") -> httpx2.Response:
    return httpx2.Response(
        200,
        json={
            "id": "x",
            "object": "chat.completion",
            "created": 0,
            "model": "m",
            "choices": [
                {
                    "index": 0,
                    "finish_reason": finish_reason,
                    "message": {"role": "assistant", "content": content},
                }
            ],
            "usage": {"prompt_tokens": 10, "completion_tokens": 5, "total_tokens": 15},
        },
    )


def client_with(
    handler: Callable[[httpx2.Request], httpx2.Response],
) -> tuple[OpenAiCompatibleLlmClient, list[httpx2.Request]]:
    requests: list[httpx2.Request] = []

    def recording(request: httpx2.Request) -> httpx2.Response:
        requests.append(request)
        return handler(request)

    http_client = httpx2.Client(transport=httpx2.MockTransport(recording))
    return OpenAiCompatibleLlmClient("http://llm/v1", "m", 5.0, 100, http_client), requests


def test_returns_parsed_json_with_usage_and_sends_the_schema() -> None:
    client, requests = client_with(lambda _: completion('{"title": "Wniosek"}'))

    result = client.generate_json("system", "user", SCHEMA)

    assert result.data == {"title": "Wniosek"}
    assert (result.usage.prompt_tokens, result.usage.completion_tokens) == (10, 5)
    body = json.loads(requests[0].content)
    assert requests[0].url.path == "/v1/chat/completions"
    assert body["response_format"]["json_schema"]["schema"] == SCHEMA
    assert body["max_tokens"] == 100


def test_answer_cut_off_at_max_tokens_fails_without_retry() -> None:
    # A model that lost the document to a context shift loops until the token limit (#103).
    client, requests = client_with(lambda _: completion('{"title": "Wnio', "length"))

    with pytest.raises(LlmCallFailed, match="cut off at 100 tokens"):
        client.generate_json("system", "user", SCHEMA)
    assert len(requests) == 1


def test_invalid_json_is_retried_and_usage_summed() -> None:
    answers = iter(["not json", '{"title": "ok"}'])
    client, _ = client_with(lambda _: completion(next(answers)))

    result = client.generate_json("system", "user", SCHEMA)

    assert result.data == {"title": "ok"}
    assert result.usage.prompt_tokens == 20


@pytest.mark.parametrize("content", ["not json", "[1, 2]"])
def test_persistent_bad_output_raises_after_max_attempts(content: str) -> None:
    client, requests = client_with(lambda _: completion(content))

    with pytest.raises(LlmCallFailed):
        client.generate_json("system", "user", SCHEMA)
    assert len(requests) == MAX_ATTEMPTS


def test_timeout_is_retried_then_raises() -> None:
    def timeout(request: httpx2.Request) -> httpx2.Response:
        raise httpx2.ReadTimeout("slow model", request=request)

    client, requests = client_with(timeout)

    with pytest.raises(LlmCallFailed):
        client.generate_json("system", "user", SCHEMA)
    assert len(requests) == MAX_ATTEMPTS


def test_rejected_request_is_not_retried() -> None:
    client, requests = client_with(lambda _: httpx2.Response(404, json={"error": "no model"}))

    with pytest.raises(LlmCallFailed):
        client.generate_json("system", "user", SCHEMA)
    assert len(requests) == 1
