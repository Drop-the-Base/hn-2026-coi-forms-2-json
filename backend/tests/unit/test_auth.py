from datetime import UTC, datetime, timedelta
from typing import Annotated, Any

import jwt
import pytest
from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from forms2json.adapters.inbound.http.auth import issue_token, require_jwt
from forms2json.config import Settings, get_settings

SECRET = "test-secret-test-secret-test-secret"


@pytest.fixture
def settings() -> Settings:
    return Settings(jwt_secret=SECRET, jwt_issuer="iss-test", jwt_audience="aud-test")


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = FastAPI()

    @app.get("/protected")
    def protected(subject: Annotated[str, Depends(require_jwt)]) -> dict[str, str]:
        return {"subject": subject}

    app.dependency_overrides[get_settings] = lambda: settings
    return TestClient(app)


def _claims(settings: Settings, **overrides: Any) -> dict[str, Any]:
    now = datetime.now(UTC)
    claims = {
        "sub": "demo",
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(minutes=5),
    }
    return claims | overrides


def _status(client: TestClient, token: str, scheme: str = "Bearer") -> int:
    return client.get("/protected", headers={"Authorization": f"{scheme} {token}"}).status_code


def test_issued_token_is_accepted(client: TestClient, settings: Settings) -> None:
    token = issue_token(settings, "alice")
    response = client.get("/protected", headers={"Authorization": f"Bearer {token}"})
    assert response.status_code == 200
    assert response.json() == {"subject": "alice"}


def test_missing_token_is_401(client: TestClient) -> None:
    response = client.get("/protected")
    assert response.status_code == 401
    assert response.headers["WWW-Authenticate"] == "Bearer"


def test_non_bearer_scheme_is_401(client: TestClient, settings: Settings) -> None:
    assert _status(client, issue_token(settings, "demo"), scheme="Basic") == 401


def test_garbage_token_is_401(client: TestClient) -> None:
    assert _status(client, "not-a-jwt") == 401


def test_wrong_signature_is_401(client: TestClient, settings: Settings) -> None:
    token = jwt.encode(_claims(settings), "other-secret-other-secret-other-sec", algorithm="HS256")
    assert _status(client, token) == 401


def test_expired_token_is_401(client: TestClient, settings: Settings) -> None:
    past = datetime.now(UTC) - timedelta(hours=1)
    token = jwt.encode(_claims(settings, iat=past, exp=past + timedelta(minutes=5)), SECRET)
    assert _status(client, token) == 401


def test_wrong_audience_is_401(client: TestClient, settings: Settings) -> None:
    assert _status(client, jwt.encode(_claims(settings, aud="someone-else"), SECRET)) == 401


def test_wrong_issuer_is_401(client: TestClient, settings: Settings) -> None:
    assert _status(client, jwt.encode(_claims(settings, iss="someone-else"), SECRET)) == 401


def test_default_ttl_issues_token_without_exp(client: TestClient, settings: Settings) -> None:
    token = issue_token(settings, "urzednik")  # JWT_TTL_SECONDS=0 by default (ADR-0032)
    assert "exp" not in jwt.decode(token, options={"verify_signature": False})
    assert _status(client, token) == 200


def test_positive_ttl_issues_token_with_exp(client: TestClient, settings: Settings) -> None:
    token = issue_token(settings.model_copy(update={"jwt_ttl_seconds": 600}), "urzednik")
    claims = jwt.decode(token, options={"verify_signature": False})
    assert claims["exp"] - claims["iat"] == 600
    assert _status(client, token) == 200  # once past exp, test_expired_token_is_401 applies


def test_token_without_iat_is_401(client: TestClient, settings: Settings) -> None:
    claims = _claims(settings)
    del claims["iat"]
    assert _status(client, jwt.encode(claims, SECRET)) == 401


def test_unsigned_token_is_401(client: TestClient, settings: Settings) -> None:
    assert _status(client, jwt.encode(_claims(settings), "", algorithm="none")) == 401
