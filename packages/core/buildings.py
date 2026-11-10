"""Buildings and assignments (T-5.1.3 partial, MH-02). The assignment table is the access rule."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.orm import Session

from core import audit, authz, clock
from core.db import Actor
from core.errors import Invalid, NotFound
from core.ids import uuid7
from core.models import BuildingAssignment, StrataCorporation, User


def building_out(b: StrataCorporation) -> dict[str, Any]:
    return {"id": str(b.id), "name": b.name, "strata_plan_number": b.strata_plan_number,
            "strata_lot_count": b.strata_lot_count, "owner_count": b.owner_count,
            "council_size": b.council_size, "general_quorum_rule": b.general_quorum_rule,
            "council_quorum_rule": b.council_quorum_rule, "row_version": b.row_version}


def list_buildings(session: Session, actor: Actor) -> list[StrataCorporation]:
    """A strata manager sees assigned buildings only; the managing broker sees all."""
    q = select(StrataCorporation).where(StrataCorporation.status == "active").order_by(StrataCorporation.name)
    rows = session.scalars(q).all()
    return [b for b in rows if authz.can_access_building(session, actor, b.id)]


def get_building(session: Session, actor: Actor, strata_id: uuid.UUID) -> StrataCorporation:
    authz.locate(session, actor, "building", strata_id)
    b = session.get(StrataCorporation, strata_id)
    if b is None:  # pragma: no cover
        raise NotFound("Not found.")
    return b


def assign(session: Session, actor: Actor, strata_id: uuid.UUID, user_id: uuid.UUID) -> None:
    authz.locate(session, actor, "building", strata_id, broker_only=True)
    u = session.get(User, user_id)
    if u is None:
        raise NotFound("Not found.")
    if u.role != "strata_manager" or u.status != "active":
        raise Invalid("Only an active strata manager can be assigned.")
    exists = session.scalar(select(BuildingAssignment.id).where(
        BuildingAssignment.strata_id == strata_id, BuildingAssignment.user_id == user_id,
        BuildingAssignment.revoked_at.is_(None)))
    if exists:
        return
    session.add(BuildingAssignment(id=uuid7(), brokerage_id=actor.brokerage_id, strata_id=strata_id,
                                   user_id=user_id, assigned_by=actor.user_id))
    session.flush()
    audit.record(session, actor, "assignment.created", strata_id=strata_id, target_type="user", target_id=user_id)


def unassign(session: Session, actor: Actor, strata_id: uuid.UUID, user_id: uuid.UUID) -> None:
    authz.locate(session, actor, "building", strata_id, broker_only=True)
    res = session.execute(
        update(BuildingAssignment)
        .where(BuildingAssignment.strata_id == strata_id, BuildingAssignment.user_id == user_id,
               BuildingAssignment.revoked_at.is_(None))
        .values(revoked_at=clock.now(), revoked_by=actor.user_id)
        .returning(BuildingAssignment.id)
    )
    if res.scalar_one_or_none() is None:
        raise NotFound("Not found.")
    audit.record(session, actor, "assignment.revoked", strata_id=strata_id, target_type="user", target_id=user_id)

