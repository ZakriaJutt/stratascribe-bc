"""Server-side web sessions in PostgreSQL (B2; TRD "Identity and tenancy").

The cookie carries 32 random bytes; the ``web_sessions`` row carries only their HMAC under
``SESSION_SECRET``, so a database dump yields no usable cookie. Idle expiry 60 minutes, absolute
lifetime 12 hours, both checked on every request against ``core.clock``. A session ends at sign-out,
on expiry, and for every session of a user at once on deactivation, a role change or an
authenticator reset (``end_all_for_user``, in the caller's transaction). Sessions are created only
by ``core.auth`` after the authenticator code is accepted; tests may call ``create`` directly.
"""

from __future__ import annotations

import hashlib
import hmac
import secrets
import uuid
from dataclasses import dataclass
from datetime import datetime, timedelta

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from core import clock, config
from core.db import Actor, session_for
from core.ids import uuid7
from core.models import User, WebSession

COOKIE = "ss_session"


def token_hash(token: str) -> bytes:
    return hmac.new(config.settings().session_secret.encode(), token.encode(), hashlib.sha256).digest()


@dataclass(frozen=True)
class Resolved:
    session_id: uuid.UUID
    user_id: uuid.UUID
    brokerage_id: uuid.UUID
    role: str
    idle_expires_at: datetime
    absolute_expires_at: datetime


def create_in(s: Session, user_id: uuid.UUID, brokerage_id: uuid.UUID, role: str) -> str:
    cfg = config.settings()
    token = secrets.token_urlsafe(32)
    now = clock.now()
    s.add(WebSession(id=uuid7(), token_hash=token_hash(token), brokerage_id=brokerage_id, user_id=user_id,
                     role=role, created_at=now, last_seen_at=now,
                     absolute_expires_at=now + timedelta(seconds=cfg.session_absolute_seconds)))
    s.flush()
    return token


def create(user_id: uuid.UUID, brokerage_id: uuid.UUID, role: str) -> str:
    with session_for(Actor.auth()) as s:
        return create_in(s, user_id, brokerage_id, role)


def resolve(token: str) -> Resolved | None:
    """The live session for this cookie, sliding the idle expiry; None when absent or ended."""
    if not token or len(token) > 200:
        return None
    cfg = config.settings()
    now = clock.now()
    with session_for(Actor.auth()) as s:
        ws = s.scalar(select(WebSession).where(WebSession.token_hash == token_hash(token)).with_for_update())
        if ws is None or ws.ended_at is not None:
            return None
        reason = None
        if now >= ws.absolute_expires_at:
            reason = "absolute"
        elif now - ws.last_seen_at >= timedelta(seconds=cfg.session_idle_seconds):
            reason = "idle"
        else:
            u = s.get(User, ws.user_id)
            if u is None or u.status != "active" or u.role != ws.role or u.brokerage_id != ws.brokerage_id:
                reason = "user_inactive"
        if reason is not None:
            ws.ended_at, ws.end_reason = now, reason
            return None
        ws.last_seen_at = now
        idle_at = now + timedelta(seconds=cfg.session_idle_seconds)
        return Resolved(ws.id, ws.user_id, ws.brokerage_id, ws.role, min(idle_at, ws.absolute_expires_at),
                        ws.absolute_expires_at)


def end(token: str, reason: str = "signed_out") -> None:
    with session_for(Actor.auth()) as s:
        s.execute(update(WebSession).where(WebSession.token_hash == token_hash(token), WebSession.ended_at.is_(None))
                  .values(ended_at=clock.now(), end_reason=reason))


def end_all_for_user(s: Session, user_id: uuid.UUID, reason: str) -> int:
    """End every live session of a user, inside the caller's (managing broker's) transaction."""
    res = s.execute(update(WebSession).where(WebSession.user_id == user_id, WebSession.ended_at.is_(None))
                    .values(ended_at=clock.now(), end_reason=reason))
    return int(getattr(res, "rowcount", 0) or 0)
