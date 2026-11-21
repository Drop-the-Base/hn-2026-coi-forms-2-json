from pathlib import Path

from pydantic import Field
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration read from environment variables (NFR-08)."""

    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)  # FR-05
    file_store_dir: Path = Path("/tmp/forms2json")  # tmpfs volume in compose (ADR-0005)
    file_ttl_seconds: int = Field(default=15 * 60, gt=0)  # NFR-06
