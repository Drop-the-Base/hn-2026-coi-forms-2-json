import pytest


@pytest.fixture(autouse=True)
def _jwt_secret(monkeypatch: pytest.MonkeyPatch) -> None:
    # Settings requires JWT_SECRET (no default in code), so every test gets a throwaway one.
    monkeypatch.setenv("JWT_SECRET", "test-secret-test-secret-test-secret")
