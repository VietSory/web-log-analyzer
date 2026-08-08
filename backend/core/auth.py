from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Annotated

import jwt
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jwt.exceptions import InvalidTokenError

from config import get_settings
from database import get_user_by_id


class AccessTokenError(ValueError):
    pass


_bearer_scheme = HTTPBearer(auto_error=False)


def create_access_token(user_id: str) -> str:
    settings = get_settings()
    now = datetime.now(timezone.utc)
    payload = {
        "sub": user_id,
        "type": "access",
        "iat": now,
        "exp": now + timedelta(minutes=settings.access_token_expire_minutes),
    }
    return jwt.encode(
        payload,
        settings.auth_secret_key.get_secret_value(),
        algorithm=settings.auth_algorithm,
    )


def decode_access_token(token: str) -> str:
    settings = get_settings()
    try:
        payload = jwt.decode(
            token,
            settings.auth_secret_key.get_secret_value(),
            algorithms=[settings.auth_algorithm],
            options={"require": ["sub", "type", "iat", "exp"]},
        )
    except InvalidTokenError as exc:
        raise AccessTokenError("Invalid or expired access token") from exc

    if payload.get("type") != "access":
        raise AccessTokenError("Invalid access token type")

    subject = payload.get("sub")
    if not isinstance(subject, str) or not subject:
        raise AccessTokenError("Invalid access token subject")

    return subject


def _credentials_error() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )


def get_current_user(
    credentials: Annotated[
        HTTPAuthorizationCredentials | None,
        Depends(_bearer_scheme),
    ],
) -> dict:
    if credentials is None or credentials.scheme.lower() != "bearer":
        raise _credentials_error()

    try:
        user_id = decode_access_token(credentials.credentials)
    except AccessTokenError as exc:
        raise _credentials_error() from exc

    user = get_user_by_id(user_id)
    if user is None:
        raise _credentials_error()

    return user
