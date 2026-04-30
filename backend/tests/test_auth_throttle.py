from pathlib import Path
from types import SimpleNamespace
import sys

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.rate_limit import InMemoryRateLimiter
from routers import auth


def _configure(monkeypatch, *, limit: int = 2):
    monkeypatch.setattr(
        auth,
        "settings",
        SimpleNamespace(
            rate_limit_enabled=True,
            auth_account_failure_limit=limit,
            rate_limit_window_seconds=60,
        ),
    )
    monkeypatch.setattr(auth, "_account_failure_limiter", InMemoryRateLimiter())


def test_account_failure_limit_is_independent_of_username_case(monkeypatch):
    _configure(monkeypatch, limit=2)

    assert not auth._account_rate_limited("Alice")
    auth._record_login_failure("Alice")
    assert not auth._account_rate_limited("alice")
    auth._record_login_failure("ALICE")
    assert auth._account_rate_limited("alice")


def test_successful_login_can_clear_account_failure_bucket(monkeypatch):
    _configure(monkeypatch, limit=1)

    auth._record_login_failure("alice")
    assert auth._account_rate_limited("alice")

    auth._clear_login_failures("alice")

    assert not auth._account_rate_limited("alice")


def test_account_failure_limit_can_be_disabled(monkeypatch):
    _configure(monkeypatch, limit=1)
    auth._record_login_failure("alice")
    monkeypatch.setattr(
        auth,
        "settings",
        SimpleNamespace(
            rate_limit_enabled=False,
            auth_account_failure_limit=1,
            rate_limit_window_seconds=60,
        ),
    )

    assert not auth._account_rate_limited("alice")
