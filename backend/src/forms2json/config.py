from functools import cache
from typing import Literal

from pydantic import Field, SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Runtime configuration read from environment variables (NFR-08)."""

    max_upload_bytes: int = Field(default=20 * 1024 * 1024, gt=0)  # FR-05

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
