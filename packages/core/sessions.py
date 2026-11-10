"""Server-side web sessions in Redis (TRD "Identity and tenancy").

Redis holds only the session identity (user, brokerage, role, times), never
tenant content, so R-05's no-cache rule is respected. Keys are HMACs of the
cookie token, so a Redis dump does not yield usable cookies. Idle expiry 60
minutes, absolute lifetime 12 hours; deactivation or a role change ends all of
a user's sessions. Sign-in (magic link plus authenticator code, T-2.2.2) is not
built in B1: sessions are created by ``create`` from tests and the seed only.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass

import redis

from core import clock, config

_client: redis.Redis[str] | None = None


def client() -> redis.Redis[str]:
    global _client
    if _client is None:
        _client = redis.Redis.from_url(config.settings().redis_url, decode_responses=True)
    return _client


def _prefix() -> str:
    return f"stratascribe:{config.settings().env}:"


def _hash(token: str) -> str:
    secret = config.settings().session_secret.encode()
    return hmac.new(secret, token.encode(), hashlib.sha256).hexdigest()


@dataclass(frozen=True)
class WebSession:
    user_id: uuid.UUID
    brokerage_id: uuid.UUID
    role: str
    created_at: float


def create(user_id: uuid.UUID, brokerage_id: uuid.UUID, role: str) -> str:
    s = config.settings()
    token = secrets.token_urlsafe(32)
    h = _hash(token)
    r = client()
    key = _prefix() + "sess:" + h
    r.hset(key, mapping={"user_id": str(user_id), "brokerage_id": str(brokerage_id), "role": role,
                         "created_at": str(clock.now().timestamp())})
    r.expire(key, s.session_idle_seconds)
    r.sadd(_prefix() + "user:" + str(user_id), h)
    r.expire(_prefix() + "user:" + str(user_id), s.session_absolute_seconds)
    return token


def resolve(token: str) -> WebSession | None:
    if not token:
        return None
    s = config.settings()
    r = client()
    key = _prefix() + "sess:" + _hash(token)
    data = r.hgetall(key)
    if not data:
        return None
    created_at = float(data["created_at"])
    if clock.now().timestamp() - created_at > s.session_absolute_seconds:
        r.delete(key)
        return None
    r.expire(key, s.session_idle_seconds)  # sliding idle expiry
    return WebSession(uuid.UUID(data["user_id"]), uuid.UUID(data["brokerage_id"]), data["role"], created_at)


def end(token: str) -> None:
    client().delete(_prefix() + "sess:" + _hash(token))


def end_all_for_user(user_id: uuid.UUID) -> None:
    r = client()
    members = r.smembers(_prefix() + "user:" + str(user_id))
    for h in members:
        r.delete(_prefix() + "sess:" + h)
    r.delete(_prefix() + "user:" + str(user_id))
