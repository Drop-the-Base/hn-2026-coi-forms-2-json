from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration read from environment variables (NFR-08)."""

    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)  # FR-05
    file_store_dir: Path = Path("/tmp/forms2json")  # tmpfs volume in compose (ADR-0005)
    file_ttl_seconds: int = Field(default=15 * 60, gt=0)  # NFR-06
    llm_base_url: str = "http://llm-runtime:11434/v1"  # Ollama in compose (ADR-0007)
    llm_model: str = "qwen3:1.7b"  # placeholder until the eval-based model ADR
    llm_timeout_seconds: float = Field(default=120.0, gt=0)
