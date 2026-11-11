"""The only way to open a database session (R-05, T-2.2.3).

``session_for(actor)`` opens a transaction as the non-superuser application role
and sets the row-level-security variables with ``set_config(..., true)``, so
they last for that transaction only and can never leak to the next user of a
pooled connection. Without these variables every policy evaluates to false.
"""

from __future__ import annotations

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from dataclasses import dataclass
from typing import Literal

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.orm import Session

from core import config

ActorKind = Literal["user", "service", "system", "operator", "auth"]


@dataclass(frozen=True)
class Actor:
    """Who is acting. Built from the session (users), the job row (service) or code (system)."""

    kind: ActorKind
    brokerage_id: uuid.UUID | None = None
    user_id: uuid.UUID | None = None
    role: str | None = None
    strata_id: uuid.UUID | None = None
    operator_id: uuid.UUID | None = None
    support_grant_id: uuid.UUID | None = None

    @classmethod
    def user(cls, user_id: uuid.UUID, brokerage_id: uuid.UUID, role: str) -> Actor:
        if role not in ("managing_broker", "strata_manager"):
            raise ValueError("unknown role")
        return cls("user", brokerage_id=brokerage_id, user_id=user_id, role=role)

    @classmethod
    def service(cls, brokerage_id: uuid.UUID, strata_id: uuid.UUID) -> Actor:
        """A worker acting for exactly one building, taken from the job row."""
        return cls("service", brokerage_id=brokerage_id, role="service", strata_id=strata_id)

    @classmethod
    def system(cls) -> Actor:
        """Lease jobs, heartbeats and the retention sweep only (policy-scoped, no content)."""
        return cls("system", role="system")

    @classmethod
    def auth(cls) -> Actor:
        """The sign-in context (B2): users, sign-in links and web sessions only; no building table.
        Used only by ``core.auth`` and ``core.sessions``."""
        return cls("auth", role="auth")

    @classmethod
    def operator(cls, operator_id: uuid.UUID, brokerage_id: uuid.UUID, support_grant_id: uuid.UUID) -> Actor:
        return cls(
            "operator",
            brokerage_id=brokerage_id,
            role="operator",
            operator_id=operator_id,
            support_grant_id=support_grant_id,
        )

    @property
    def is_broker(self) -> bool:
        return self.kind == "user" and self.role == "managing_broker"


_engines: dict[str, Engine] = {}


def engine() -> Engine:
    url = config.settings().database_url
    if url not in _engines:
        _engines[url] = create_engine(url, pool_pre_ping=True, pool_size=5, max_overflow=5)
    return _engines[url]


def dispose() -> None:
    for e in _engines.values():
        e.dispose()
    _engines.clear()


def _vars(actor: Actor) -> dict[str, str]:
    def s(v: object) -> str:
        return "" if v is None else str(v)

    return {
        "app.brokerage_id": s(actor.brokerage_id),
        "app.user_id": s(actor.user_id),
        "app.role": s(actor.role),
        "app.strata_id": s(actor.strata_id),
        "app.operator_id": s(actor.operator_id),
        "app.support_grant_id": s(actor.support_grant_id),
    }


@contextmanager
def session_for(actor: Actor) -> Iterator[Session]:
    """Open one transaction with tenant context; commit on success, roll back on error."""
    with Session(engine(), expire_on_commit=False) as session, session.begin():
        for name, value in _vars(actor).items():
            session.execute(text("SELECT set_config(:n, :v, true)"), {"n": name, "v": value})
        yield session
