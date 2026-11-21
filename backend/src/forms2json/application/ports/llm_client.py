from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class LlmUsage:
    """Summed over every attempt: retries cost tokens and time too (NFR-13)."""

    prompt_tokens: int
    completion_tokens: int
    duration_seconds: float


@dataclass(frozen=True)
class LlmResult:
    data: dict[str, Any]  # parsed JSON object; the caller validates it with its pydantic model
    usage: LlmUsage


class LlmCallFailed(RuntimeError):
    """The model was unreachable or kept returning output that is not a JSON object."""


class LlmRequestTooLarge(LlmCallFailed):
    """The provider refused the prompt as too large (HTTP 413, e.g. a tokens-per-minute cap)."""


class LlmRateLimited(LlmCallFailed):
    """The provider's rate limit is used up (HTTP 429)."""


class LlmClient(ABC):
    """Talks to a local model and returns JSON shaped by the given JSON Schema (ADR-0007)."""

    @abstractmethod
    def generate_json(self, system: str, user: str, schema: dict[str, Any]) -> LlmResult: ...
