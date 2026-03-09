from __future__ import annotations

from collections import deque
from dataclasses import dataclass
from threading import Lock
from time import monotonic


@dataclass(frozen=True, slots=True)
class RateLimitDecision:
    allowed: bool
    limit: int
    remaining: int
    retry_after_seconds: int


class InMemoryRateLimiter:
    """Process-local sliding-window limiter for API abuse protection."""

    def __init__(self) -> None:
        self._events: dict[str, deque[float]] = {}
        self._windows: dict[str, int] = {}
        self._lock = Lock()
        self._checks_since_cleanup = 0

    def check(
        self,
        key: str,
        *,
        limit: int,
        window_seconds: int,
        now: float | None = None,
    ) -> RateLimitDecision:
        if limit < 1:
            raise ValueError("limit must be positive")
        if window_seconds < 1:
            raise ValueError("window_seconds must be positive")

        timestamp = monotonic() if now is None else float(now)
        cutoff = timestamp - window_seconds

        with self._lock:
            configured_window = self._windows.setdefault(key, window_seconds)
            if configured_window != window_seconds:
                raise ValueError("rate-limit key reused with a different window")

            events = self._events.setdefault(key, deque())
            while events and events[0] <= cutoff:
                events.popleft()

            if len(events) >= limit:
                retry_after = max(1, int(events[0] + window_seconds - timestamp + 0.999))
                decision = RateLimitDecision(
                    allowed=False,
                    limit=limit,
                    remaining=0,
                    retry_after_seconds=retry_after,
                )
            else:
                events.append(timestamp)
                decision = RateLimitDecision(
                    allowed=True,
                    limit=limit,
                    remaining=max(0, limit - len(events)),
                    retry_after_seconds=0,
                )

            self._checks_since_cleanup += 1
            if self._checks_since_cleanup >= 1024:
                self._cleanup(timestamp)
                self._checks_since_cleanup = 0

            return decision

    def _cleanup(self, now: float) -> None:
        expired_keys: list[str] = []
        for key, events in self._events.items():
            window_seconds = self._windows[key]
            cutoff = now - window_seconds
            while events and events[0] <= cutoff:
                events.popleft()
            if not events:
                expired_keys.append(key)

        for key in expired_keys:
            self._events.pop(key, None)
            self._windows.pop(key, None)
