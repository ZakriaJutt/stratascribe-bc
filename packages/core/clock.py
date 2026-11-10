"""One clock for the application so tests can fix time (I-13, I-14, retention)."""

from __future__ import annotations

from collections.abc import Callable
from datetime import UTC, datetime

_now: Callable[[], datetime] = lambda: datetime.now(UTC)  # noqa: E731


def now() -> datetime:
    return _now()


def set_clock(fn: Callable[[], datetime] | None) -> None:
    global _now
    _now = fn if fn is not None else (lambda: datetime.now(UTC))
