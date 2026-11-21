import pytest
from pydantic import ValidationError

from forms2json.config import Settings


def test_max_upload_bytes_comes_from_env(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "1024")
    assert Settings().max_upload_bytes == 1024


def test_non_positive_max_upload_bytes_is_rejected(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("MAX_UPLOAD_BYTES", "0")
    with pytest.raises(ValidationError):
        Settings()
