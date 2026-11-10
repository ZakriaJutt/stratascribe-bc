"""``Idempotency-Key`` handling: a repeated key returns the first result (TRD "API contracts").

Stored in ``idempotency_keys`` in the same transaction as the mutation, so the
key and the effect commit together. Rows are visible only to their user (RLS).
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core.db import Actor
from core.errors import Invalid
from core.models import IdempotencyKey


def request_hash(body: Any) -> str:
    return hashlib.sha256(json.dumps(body, sort_keys=True, default=str).encode()).hexdigest()


def lookup(session: Session, actor: Actor, route: str, key: str | None, body: Any) -> tuple[int, Any] | None:
    if not key or actor.user_id is None:
        return None
    if len(key) > 200:
        raise Invalid("Idempotency-Key is too long.")
    row = session.scalar(
        select(IdempotencyKey).where(
            IdempotencyKey.user_id == actor.user_id, IdempotencyKey.route == route, IdempotencyKey.key == key
        )
    )
    if row is None:
        return None
    if row.request_hash != request_hash(body):
        raise Invalid("This Idempotency-Key was used with a different request.", code="idempotency_mismatch")
    return row.status_code, row.response_body


def store(session: Session, actor: Actor, route: str, key: str | None, body: Any, status: int, response: Any) -> None:
    if not key or actor.user_id is None:
        return
    session.add(
        IdempotencyKey(
            key=key,
            user_id=actor.user_id,
            route=route,
            request_hash=request_hash(body),
            status_code=status,
            response_body=json.loads(json.dumps(response, default=str)),
        )
    )
    session.flush()
