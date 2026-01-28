from pathlib import Path
import sys
from datetime import datetime, timedelta, timezone

import jwt
import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from config import get_settings
from core.auth import AccessTokenError, create_access_token, decode_access_token


@pytest.fixture(autouse=True)
def auth_settings(monkeypatch):
    monkeypatch.setenv("APP_ENV", "test")
    monkeypatch.setenv("AUTH_SECRET_KEY", "test-secret-key-with-at-least-thirty-two-bytes")
    monkeypatch.setenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30")
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


def test_access_token_round_trip():
    token = create_access_token("user-123")
    assert decode_access_token(token) == "user-123"


def test_tampered_access_token_is_rejected():
    token = create_access_token("user-123")
    with pytest.raises(AccessTokenError):
        decode_access_token(token + "tampered")


def test_expired_access_token_is_rejected():
    settings = get_settings()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "user-123",
            "type": "access",
            "iat": now - timedelta(hours=2),
            "exp": now - timedelta(hours=1),
        },
        settings.auth_secret_key.get_secret_value(),
        algorithm=settings.auth_algorithm,
    )
    with pytest.raises(AccessTokenError):
        decode_access_token(token)


def test_wrong_token_type_is_rejected():
    settings = get_settings()
    now = datetime.now(timezone.utc)
    token = jwt.encode(
        {
            "sub": "user-123",
            "type": "refresh",
            "iat": now,
            "exp": now + timedelta(minutes=5),
        },
        settings.auth_secret_key.get_secret_value(),
        algorithm=settings.auth_algorithm,
    )
    with pytest.raises(AccessTokenError):
        decode_access_token(token)


def test_production_rejects_default_auth_secret(monkeypatch):
    monkeypatch.setenv("APP_ENV", "production")
    monkeypatch.setenv(
        "AUTH_SECRET_KEY",
        "dev-only-change-this-secret-at-least-32-bytes",
    )
    get_settings.cache_clear()
    with pytest.raises(ValueError):
        get_settings()
