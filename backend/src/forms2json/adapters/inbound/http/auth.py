"""JWT authentication for the HTTP API (FR-10).

Protect a router with `APIRouter(dependencies=[Depends(require_jwt)])`.
"""

from datetime import UTC, datetime, timedelta
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from forms2json.config import Settings, get_settings

_REQUIRED_CLAIMS = ["exp", "iat", "iss", "aud", "sub"]

# auto_error=False so a missing header gets the same 401 + WWW-Authenticate as a bad token.
_bearer = HTTPBearer(auto_error=False)


def issue_token(settings: Settings, subject: str) -> str:
    now = datetime.now(UTC)
    claims = {
        "sub": subject,
        "iss": settings.jwt_issuer,
        "aud": settings.jwt_audience,
        "iat": now,
        "exp": now + timedelta(seconds=settings.jwt_ttl_seconds),
    }
    return jwt.encode(
        claims, settings.jwt_secret.get_secret_value(), algorithm=settings.jwt_algorithm
    )


def require_jwt(
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer)],
    settings: Annotated[Settings, Depends(get_settings)],
) -> str:
    """Returns the token subject, or raises 401."""
    if credentials is None:
        raise _unauthorized("Missing bearer token")
    try:
        claims = jwt.decode(
            credentials.credentials,
            settings.jwt_secret.get_secret_value(),
            algorithms=[settings.jwt_algorithm],
            audience=settings.jwt_audience,
            issuer=settings.jwt_issuer,
            options={"require": _REQUIRED_CLAIMS},
        )
    except jwt.InvalidTokenError as error:
        raise _unauthorized("Invalid or expired token") from error
    subject: str = claims["sub"]
    return subject


def _unauthorized(detail: str) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"},
    )
