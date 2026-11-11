"""Audit events (T-2.2.4, MH-11). Append-only: the application role has INSERT and SELECT only.

``details`` accepts allow-listed keys only and never transcript, minutes,
question or answer text.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy.orm import Session

from core import clock
from core import logging as clog
from core.db import Actor
from core.ids import uuid7
from core.models import AuditEvent

ALLOWED_DETAIL_KEYS = frozenset(
    {"reason", "role", "basis", "state", "from_state", "to_state", "version", "count", "format", "field",
     "category", "kind", "route", "error_code", "outcome", "part_number", "days", "range_start", "range_end"}
)


def _details(details: dict[str, Any] | None) -> dict[str, Any]:
    if not details:
        return {}
    bad = set(details) - ALLOWED_DETAIL_KEYS
    if bad:
        raise ValueError(f"audit details keys not allowed: {sorted(bad)}")
    return details


def record(
    session: Session,
    actor: Actor,
    action: str,
    *,
    strata_id: uuid.UUID | None = None,
    target_type: str | None = None,
    target_id: uuid.UUID | None = None,
    outcome: str = "ok",
    details: dict[str, Any] | None = None,
    brokerage_id: uuid.UUID | None = None,
) -> None:
    b = brokerage_id or actor.brokerage_id
    if b is None:
        raise ValueError("audit event needs a brokerage")
    actor_type = {"user": "user", "operator": "operator"}.get(actor.kind, "system")
    actor_id = actor.user_id if actor.kind == "user" else actor.operator_id
    session.add(
        AuditEvent(
            id=uuid7(),
            brokerage_id=b,
            strata_id=strata_id,
            actor_type=actor_type,
            actor_id=actor_id,
            action=action,
            target_type=target_type,
            target_id=target_id,
            outcome=outcome,
            correlation_id=uuid.UUID(clog.correlation_id() or clog.new_correlation_id()),
            details=_details(details),
            # Set here so the INSERT needs no RETURNING: only the managing broker may SELECT audit rows.
            occurred_at=clock.now(),
        )
    )
    session.flush()
