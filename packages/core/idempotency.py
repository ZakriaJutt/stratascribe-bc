"""``Idempotency-Key`` handling: a repeated key returns the first result (TRD "API contracts").

Stored in ``idempotency_keys`` in the same transaction as the mutation. Each row
carries the brokerage and the building the response concerns, and expires after
24 hours. Row-level security shows a row only to its user, in its brokerage,
before expiry, and only while that user may still see the building, so a replay
after unassignment finds nothing, the route runs again, and the access check
answers 403 (B1-001). Expired rows are purged by the retention sweep.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from core import clock
from core.db import Actor
from core.errors import Conflict, Invalid
from core.models import IdempotencyKey

TTL = timedelta(hours=24)


def request_hash(body: Any) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def lookup(session: Session, actor: Actor, route: str, key: str | None, body: Any) -> tuple[int, Any] | None:
    if not key or actor.user_id is None:
        return None
    if len(key) > 200:
        raise Invalid("Idempotency-Key is too long.")
    row = session.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.user_id == actor.user_id, IdempotencyKey.route == route, IdempotencyKey.key == key,
            IdempotencyKey.expires_at > clock.now(),
        )
    )
    if row is None:
        return None
    if row.request_hash != request_hash(body):
        raise Invalid("This Idempotency-Key was used with a different request.", code="idempotency_mismatch")
    return row.status_code, row.response_body


def store(session: Session, actor: Actor, route: str, key: str | None, body: Any, status: int, response: Any) -> None:
    if not key or actor.user_id is None or actor.brokerage_id is None:
        return
    strata: uuid.UUID | None = session.info.get("located_strata")
    now = clock.now()
    values = {
        "key": key, "user_id": actor.user_id, "route": route, "brokerage_id": actor.brokerage_id,
        "strata_id": strata, "request_hash": request_hash(body), "status_code": status,
        "response_body": json.loads(json.dumps(response, default=str)), "created_at": now, "expires_at": now + TTL,
    }
    for attempt in range(2):
        stmt = insert(IdempotencyKey).values(**values).on_conflict_do_nothing().returning(IdempotencyKey.key)
        if session.execute(stmt).scalar_one_or_none() is not None:
            return
        if attempt == 0:
            session.execute(text("SELECT app_purge_idempotency()"))  # an expired row may hold the key
    # Another request with this key committed first (or is in flight): this one's effects roll back.
    raise Conflict("A request with this Idempotency-Key was already processed. Retry to get its result.",
                   code="idempotency_in_progress")
