from functools import cache
from pathlib import Path
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration read from environment variables (NFR-08)."""

    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)  # FR-05
    file_store_dir: Path = Path("/tmp/forms2json")  # tmpfs volume in compose (ADR-0005)
    file_ttl_seconds: int = Field(default=15 * 60, gt=0)  # NFR-06
    result_ttl_seconds: int = Field(default=30 * 60, gt=0)  # NFR-06, results live in api memory
    # FR-06: how long POST /forms:convert waits before answering 202 with the job id.
    sync_timeout_seconds: float = Field(default=120.0, gt=0)
    llm_base_url: str = "http://llm-runtime:11434/v1"  # Ollama in compose (ADR-0007)
    llm_model: str = "qwen3:1.7b"  # placeholder until the eval-based model ADR
    llm_timeout_seconds: float = Field(default=120.0, gt=0)
    # Ollama ignores the key; a cloud endpoint needs a real one, only from env (ADR-0028).
    llm_api_key: SecretStr = SecretStr("local")
    # Not every OpenAI-compatible provider supports strict json_schema; json_object is the fallback.
    llm_response_format: Literal["json_schema", "json_object"] = "json_schema"
    # soffice can hang on a broken file; the worker (.doc) and the api (preview) kill it after this.
    doc_conversion_timeout_seconds: float = Field(default=60.0, gt=0)
    ocr_lang: str = "pol"  # Tesseract language pack installed in the worker image (ADR-0029)
    rabbitmq_url: str = "amqp://guest:guest@rabbitmq:5672/"  # compose service (ADR-0004)
    # Roughly 10k tokens of Polish text: fits the context of small local models with the prompt.
    llm_max_input_chars: int = Field(default=30_000, gt=0)
    # A looping model stops here instead of running until the timeout. Input + prompt + this
    # must fit the runtime context (Ollama: OLLAMA_CONTEXT_LENGTH, default 4096 is too small).
    llm_max_output_tokens: int = Field(default=4096, gt=0)
    # FR-T1: below this an element is not "high" in frontend/DESIGN.md and needs a human look.
    confidence_review_threshold: float = Field(default=0.85, ge=0, le=1)
    # NFR-13: provider prices per 1M tokens (or GPU time for a local model); 0 = not counted.
    cost_per_1m_input_tokens: float = Field(default=0.0, ge=0)
    cost_per_1m_output_tokens: float = Field(default=0.0, ge=0)
    cost_per_gpu_second: float = Field(default=0.0, ge=0)
    cost_currency: str = "USD"

    # FR-10. No default secret: the API must not start with a guessable key (NFR-07).
    # 32 bytes is the HS256 minimum from RFC 7518 §3.2.
    jwt_secret: SecretStr = Field(min_length=32)
    # Only HMAC: the key is a shared secret, so asymmetric algorithms and "none" are not allowed.
    jwt_algorithm: Literal["HS256", "HS384", "HS512"] = "HS256"
    jwt_issuer: str = "forms2json"
    jwt_audience: str = "forms2json-api"
    jwt_ttl_seconds: int = Field(default=3600, gt=0)


@cache
def get_settings() -> Settings:
    return Settings()
