"""The single access-decision point (T-2.2.3, MH-01, MH-02, R-05).

Row-level security is the first wall; this module is the second and decides
the response: another brokerage's ID -> 404 (the attempt is still audited for
the owning brokerage); a building of the caller's brokerage that a strata
manager is not assigned to -> 403 "not assigned". A managing broker has every
manager right in every building of their own brokerage.

Denials are written in their own transaction so a rolled-back request still
leaves an ``access.denied`` row.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import text
from sqlalchemy.orm import Session

from core import audit
from core import logging as clog
from core.db import Actor, session_for
from core.errors import Forbidden, NotFound

KINDS = (
    "building",
    "meeting",
    "audio_asset",
    "minute_item",
    "minute_item_citation",
    "bylaw_document",
    "bylaw_clause",
    "question",
)


@dataclass(frozen=True)
class Located:
    kind: str
    id: uuid.UUID
    strata_id: uuid.UUID


class AccessDenied(Forbidden):
    def __init__(self, kind: str, target_id: uuid.UUID, strata_id: uuid.UUID, reason: str) -> None:
        super().__init__("You are not assigned to this building. Ask your managing broker.", code="not_assigned")
        self.kind, self.target_id, self.strata_id, self.reason = kind, target_id, strata_id, reason


class ForeignOrMissing(NotFound):
    def __init__(self, kind: str, target_id: uuid.UUID) -> None:
        super().__init__("Not found.")
        self.kind, self.target_id = kind, target_id


def can_access_building(session: Session, actor: Actor, strata_id: uuid.UUID) -> bool:
    if actor.kind != "user":
        return False
    return bool(session.scalar(text("SELECT app_can_see_building(:s)"), {"s": strata_id}))


def locate(session: Session, actor: Actor, kind: str, target_id: uuid.UUID, *, broker_only: bool = False) -> Located:
    """Resolve a target to its building and check the actor may act on it."""
    if kind not in KINDS:
        raise ValueError("unknown kind")
    strata = session.scalar(text("SELECT app_locate(:k, :i)"), {"k": kind, "i": target_id})
    if strata is None:
        raise ForeignOrMissing(kind, target_id)
    if broker_only and not actor.is_broker:
        raise AccessDenied(kind, target_id, strata, "broker_only")
    if not can_access_building(session, actor, strata):
        raise AccessDenied(kind, target_id, strata, "not_assigned")
    return Located(kind, target_id, strata)


def require_broker(actor: Actor) -> None:
    if not actor.is_broker:
        raise Forbidden("Only the managing broker can do this.", code="broker_only")


def record_denial(actor: Actor, exc: Exception) -> None:
    """Persist the audit row for a denial in a fresh transaction."""
    if actor.kind != "user" or actor.brokerage_id is None:
        return
    with session_for(actor) as s:
        if isinstance(exc, AccessDenied):
            audit.record(
                s,
                actor,
                "access.denied",
                strata_id=exc.strata_id,
                target_type=exc.kind,
                target_id=exc.target_id,
                outcome="denied",
                details={"reason": exc.reason},
            )
        elif isinstance(exc, ForeignOrMissing):
            corr = uuid.UUID(clog.correlation_id() or clog.new_correlation_id())
            s.execute(
                text("SELECT app_record_foreign_denial(:k, :i, :a, :c)"),
                {"k": exc.kind, "i": exc.target_id, "a": actor.user_id, "c": corr},
            )
