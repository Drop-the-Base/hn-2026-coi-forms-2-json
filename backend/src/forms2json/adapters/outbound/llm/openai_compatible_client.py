import json
import time
from typing import Any

import httpx2
import openai
from openai import OpenAI
from opentelemetry import metrics, trace

from forms2json.application.ports.llm_client import LlmCallFailed, LlmClient, LlmResult, LlmUsage

MAX_ATTEMPTS = 3

_tracer = trace.get_tracer(__name__)
# GenAI semantic conventions: name, unit and buckets from the spec.
_token_usage = metrics.get_meter(__name__).create_histogram(
    "gen_ai.client.token.usage",
    unit="{token}",
    explicit_bucket_boundaries_advisory=[4**i for i in range(14)],
)


class OpenAiCompatibleLlmClient(LlmClient):
    """Any runtime with an OpenAI-compatible /v1/chat/completions (Ollama, vLLM, llama.cpp)."""

    def __init__(
        self,
        base_url: str,
        model: str,
        timeout_seconds: float,
        max_output_tokens: int,
        http_client: httpx2.Client | None = None,
    ) -> None:
        self._model = model
        self._max_output_tokens = max_output_tokens
        # Local runtimes ignore the key, but the SDK requires one. Retries are ours (below),
        # so one loop covers both network errors and invalid JSON.
        self._client = OpenAI(
            base_url=base_url,
            api_key="local",
            timeout=timeout_seconds,
            max_retries=0,
            http_client=http_client,
        )

    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> LlmResult:
        # GenAI semantic conventions; "openai" names the API flavor, not who hosts the model.
        attributes = {
            "gen_ai.operation.name": "chat",
            "gen_ai.provider.name": "openai",
            "gen_ai.request.model": self._model,
        }
        with _tracer.start_as_current_span(
            f"chat {self._model}", kind=trace.SpanKind.CLIENT, attributes=attributes
        ) as span:
            result = self._generate_json(system, user, schema)
            span.set_attributes(
                {
                    "gen_ai.usage.input_tokens": result.usage.prompt_tokens,
                    "gen_ai.usage.output_tokens": result.usage.completion_tokens,
                }
            )
            _token_usage.record(
                result.usage.prompt_tokens, {**attributes, "gen_ai.token.type": "input"}
            )
            _token_usage.record(
                result.usage.completion_tokens, {**attributes, "gen_ai.token.type": "output"}
            )
            return result

    def _generate_json(self, system: str, user: str, schema: dict[str, Any]) -> LlmResult:
        prompt_tokens = completion_tokens = 0
        started = time.perf_counter()
        last_error: Exception | None = None
        for _ in range(MAX_ATTEMPTS):
            try:
                response = self._client.chat.completions.create(
                    model=self._model,
                    messages=[
                        {"role": "system", "content": system},
                        {"role": "user", "content": user},
                    ],
                    response_format={
                        "type": "json_schema",
                        "json_schema": {"name": "output", "schema": schema, "strict": True},
                    },
                    temperature=0,
                    max_tokens=self._max_output_tokens,
                )
            except openai.APIConnectionError as error:  # includes APITimeoutError
                last_error = error
                continue
            except openai.APIError as error:
                raise LlmCallFailed(f"LLM runtime rejected the request: {error}") from error
            if response.usage:
                prompt_tokens += response.usage.prompt_tokens
                completion_tokens += response.usage.completion_tokens
            if response.choices[0].finish_reason == "length":
                # temperature=0 repeats the same cut-off answer, so a retry only wastes time.
                raise LlmCallFailed(
                    f"answer cut off at {self._max_output_tokens} tokens"
                    " (model looping, or input + output above the runtime context)"
                )
            try:
                data = json.loads(response.choices[0].message.content or "")
            except json.JSONDecodeError as error:
                last_error = error
                continue
            if isinstance(data, dict):
                usage = LlmUsage(prompt_tokens, completion_tokens, time.perf_counter() - started)
                return LlmResult(data, usage)
            last_error = ValueError(f"expected a JSON object, got {type(data).__name__}")
        raise LlmCallFailed(f"no valid answer after {MAX_ATTEMPTS} attempts") from last_error
