"""Business-day arithmetic for M-2 ("3 business days"), test I-14.

The BC statutory-holiday table is NOT built in: it must be taken from the BC
government list in T-5.1.2 (not looked up). Callers pass the holidays.
"""

from __future__ import annotations

from collections.abc import Iterable
from datetime import date, timedelta


def business_days_after(held_on: date, sent_on: date, holidays: Iterable[date]) -> int:
    """Business days after the meeting day up to and including the sent day."""
    if sent_on < held_on:
        raise ValueError("sent before the meeting")
    off = set(holidays)
    days, d = 0, held_on
    while d < sent_on:
        d += timedelta(days=1)
        if d.weekday() < 5 and d not in off:
            days += 1
    return days
