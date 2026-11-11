"""Fixed-window rate limits in Redis (TRD "Identity and tenancy", rate-limit table; test I-17).

Identifiers (email addresses, IP addresses) are stored only as HMACs, so Redis holds no personal
data. Windows follow ``core.clock`` so tests can move time. Built in B2: sign-in requests per email
and per IP address. Authenticator attempts are limited per link in ``sign_in_links.failed_codes``.
"""

from __future__ import annotations

import hashlib
import hmac

import redis

from core import clock, config

SIGN_IN_PER_EMAIL = (5, 3600)
SIGN_IN_PER_IP = (20, 3600)

_client: redis.Redis[str] | None = None


def client() -> redis.Redis[str]:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(config.settings().redis_url, decode_responses=True)
    return _client


def prefix() -> str:
    return f"stratascribe:{config.settings().env}:rl:"


def _ident(value: str) -> str:
    secret = config.settings().session_secret.encode()
    return hmac.new(secret, value.encode(), hashlib.sha256).hexdigest()[:32]


def hit(bucket: str, ident: str, limit: int, window: int) -> int | None:
    """Count one event. Return None when allowed, else the seconds until the window resets."""
    now = int(clock.now().timestamp())
    start = now - now % window
    key = f"{prefix()}{bucket}:{_ident(ident)}:{start}"
    r = client()
    count = int(r.incr(key))
    if count == 1:
        r.expire(key, window + 60)
    if count > limit:
        return start + window - now
    return None
