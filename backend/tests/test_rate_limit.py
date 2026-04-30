from pathlib import Path
import sys

import pytest

BACKEND_DIR = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(BACKEND_DIR))

from core.rate_limit import InMemoryRateLimiter


def test_limiter_allows_until_capacity_then_returns_retry_after():
    limiter = InMemoryRateLimiter()

    first = limiter.check("auth:192.0.2.1", limit=2, window_seconds=60, now=100.0)
    second = limiter.check("auth:192.0.2.1", limit=2, window_seconds=60, now=101.0)
    blocked = limiter.check("auth:192.0.2.1", limit=2, window_seconds=60, now=102.0)

    assert first.allowed and first.remaining == 1
    assert second.allowed and second.remaining == 0
    assert not blocked.allowed
    assert blocked.remaining == 0
    assert blocked.retry_after_seconds == 58


def test_limiter_can_preflight_without_consuming_capacity():
    limiter = InMemoryRateLimiter()

    preflight = limiter.check(
        "account:alice",
        limit=1,
        window_seconds=60,
        now=100.0,
        consume=False,
    )
    first_failure = limiter.check(
        "account:alice",
        limit=1,
        window_seconds=60,
        now=101.0,
    )
    blocked_preflight = limiter.check(
        "account:alice",
        limit=1,
        window_seconds=60,
        now=102.0,
        consume=False,
    )

    assert preflight.allowed and preflight.remaining == 1
    assert first_failure.allowed and first_failure.remaining == 0
    assert not blocked_preflight.allowed


def test_limiter_clear_removes_failure_history():
    limiter = InMemoryRateLimiter()
    limiter.check("account:alice", limit=1, window_seconds=60, now=1.0)
    assert not limiter.check(
        "account:alice",
        limit=1,
        window_seconds=60,
        now=2.0,
        consume=False,
    ).allowed

    limiter.clear("account:alice")

    assert limiter.check(
        "account:alice",
        limit=1,
        window_seconds=60,
        now=3.0,
        consume=False,
    ).allowed


def test_limiter_releases_capacity_after_window_expires():
    limiter = InMemoryRateLimiter()

    limiter.check("api:198.51.100.2", limit=1, window_seconds=10, now=5.0)
    assert not limiter.check(
        "api:198.51.100.2",
        limit=1,
        window_seconds=10,
        now=14.99,
    ).allowed

    released = limiter.check(
        "api:198.51.100.2",
        limit=1,
        window_seconds=10,
        now=15.0,
    )
    assert released.allowed
    assert released.remaining == 0


def test_limiter_isolated_by_policy_and_client_key():
    limiter = InMemoryRateLimiter()

    limiter.check("auth:203.0.113.3", limit=1, window_seconds=60, now=1.0)

    assert limiter.check(
        "api:203.0.113.3",
        limit=1,
        window_seconds=60,
        now=1.0,
    ).allowed
    assert limiter.check(
        "auth:203.0.113.4",
        limit=1,
        window_seconds=60,
        now=1.0,
    ).allowed


def test_limiter_rejects_invalid_configuration_and_key_window_reuse():
    limiter = InMemoryRateLimiter()

    with pytest.raises(ValueError, match="limit must be positive"):
        limiter.check("api:test", limit=0, window_seconds=60, now=1.0)
    with pytest.raises(ValueError, match="window_seconds must be positive"):
        limiter.check("api:test", limit=1, window_seconds=0, now=1.0)

    limiter.check("api:test", limit=1, window_seconds=60, now=1.0)
    with pytest.raises(ValueError, match="different window"):
        limiter.check("api:test", limit=1, window_seconds=30, now=2.0)
