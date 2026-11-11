"""Team: invitations and member changes by the managing broker (B2, T-2.2.2 (d); App-flow S-05).

An invitation creates an ``invited`` user in the broker's own brokerage and emails a pointer to the
sign-in page (no token: the invitee requests a link like anyone else). An address already used in
another brokerage or by an operator gets the generic "This address cannot be invited". Deactivation,
a role change and an authenticator reset end every session of that member at once; the last active
managing broker cannot be deactivated or demoted (database trigger).
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select, text
from sqlalchemy.exc import DBAPIError
from sqlalchemy.orm import Session

from core import audit, authz, clock, config, sessions
from core.auth import normalise_email
from core.db import Actor
from core.errors import Conflict, Invalid, NotFound
from core.ids import uuid7
from core.mail import Message
from core.models import Brokerage, BuildingAssignment, User

ROLES = ("managing_broker", "strata_manager")


def member_out(u: User, buildings: list[uuid.UUID] | None = None) -> dict[str, Any]:
    return {"id": str(u.id), "email": u.email, "full_name": u.full_name, "role": u.role, "status": u.status,
            "invited_at": u.invited_at.isoformat() if u.invited_at else None,
            "authenticator_enrolled": u.totp_enrolled_at is not None,
            "buildings": [str(b) for b in (buildings or [])]}


def list_members(s: Session, actor: Actor) -> list[dict[str, Any]]:
    authz.require_broker(actor)
    assigned: dict[uuid.UUID, list[uuid.UUID]] = {}
    for a in s.scalars(select(BuildingAssignment).where(BuildingAssignment.revoked_at.is_(None))):
        assigned.setdefault(a.user_id, []).append(a.strata_id)
    users = s.scalars(select(User).order_by(User.full_name))
    return [member_out(u, assigned.get(u.id)) for u in users]


def _invitation(s: Session, u: User) -> Message:
    b = s.get(Brokerage, u.brokerage_id)
    base = config.settings().public_base_url
    name = b.legal_name if b else "Your brokerage"
    return Message(to=u.email, subject="You are invited to StrataScribe",
                   body=f"{name} has invited you to StrataScribe.\n\nSign in at {base}/sign-in with this email "
                        "address. You will set up an authenticator app the first time.")


def invite(s: Session, actor: Actor, body: dict[str, Any]) -> tuple[User, Message]:
    authz.require_broker(actor)
    email = normalise_email(body.get("email"))
    full_name = (body.get("full_name") or "").strip() if isinstance(body.get("full_name"), str) else ""
    role = body.get("role", "strata_manager")
    if not full_name or len(full_name) > 200:
        raise Invalid("Enter the member's name.", code="invalid_name", extra={"fields": ["full_name"]})
    if role not in ROLES:
        raise Invalid("Unknown role.", code="invalid_role", extra={"fields": ["role"]})
    own = s.scalar(select(User).where(User.email == email))
    if own is not None:
        if own.status == "invited":
            raise Conflict(f"Already invited on {own.invited_at:%d %b %Y}. Resend?" if own.invited_at
                           else "Already invited. Resend?", code="already_invited", extra={"member_id": str(own.id)})
        raise Conflict("This person is already a member.", code="already_member", extra={"member_id": str(own.id)})
    if s.execute(text("SELECT app_email_in_use(:e)"), {"e": email}).scalar():
        raise Conflict("This address cannot be invited.", code="cannot_invite")
    u = User(id=uuid7(), brokerage_id=actor.brokerage_id, email=email, full_name=full_name, role=role,
             status="invited", invited_by=actor.user_id, invited_at=clock.now())
    s.add(u)
    s.flush()
    audit.record(s, actor, "member.invited", target_type="user", target_id=u.id, details={"role": role})
    return u, _invitation(s, u)


def _member(s: Session, actor: Actor, user_id: uuid.UUID) -> User:
    authz.require_broker(actor)
    u = s.get(User, user_id, with_for_update=True)
    if u is None:
        raise NotFound("Not found.")
    return u


def resend(s: Session, actor: Actor, user_id: uuid.UUID) -> tuple[User, Message]:
    u = _member(s, actor, user_id)
    if u.status != "invited":
        raise Conflict("Only a pending invitation can be resent.", code="not_invited")
    u.invited_at = clock.now()
    audit.record(s, actor, "member.invitation_resent", target_type="user", target_id=u.id)
    return u, _invitation(s, u)


def update_member(s: Session, actor: Actor, user_id: uuid.UUID, body: dict[str, Any]) -> User:
    u = _member(s, actor, user_id)
    unknown = set(body) - {"role", "status", "reset_authenticator"}
    if unknown:
        raise Invalid("Only role, status and reset_authenticator can be changed.", extra={"fields": sorted(unknown)})
    end_reason: str | None = None
    try:
        with s.begin_nested():
            if "role" in body and body["role"] != u.role:
                if body["role"] not in ROLES:
                    raise Invalid("Unknown role.", code="invalid_role", extra={"fields": ["role"]})
                u.role, end_reason = body["role"], "role_changed"
                s.flush()
            if "status" in body and body["status"] != u.status:
                if body["status"] not in ("active", "deactivated") or (
                        body["status"] == "active" and u.last_sign_in_at is None):
                    raise Invalid("Status can be 'active' (for a member who has signed in) or 'deactivated'.",
                                  code="invalid_status", extra={"fields": ["status"]})
                u.status = body["status"]
                end_reason = "deactivated" if u.status == "deactivated" else end_reason
                s.flush()
            if body.get("reset_authenticator") is True:
                u.totp_secret_encrypted, u.totp_enrolled_at, u.totp_last_used_step = None, None, None
                end_reason = end_reason or "authenticator_reset"
                s.flush()
    except DBAPIError as exc:
        if "last active managing broker" in str(exc.orig):
            raise Conflict("The last active managing broker cannot be deactivated or demoted.",
                           code="last_broker") from None
        raise
    if end_reason is not None:
        n = sessions.end_all_for_user(s, u.id, end_reason)
        audit.record(s, actor, "member.updated", target_type="user", target_id=u.id,
                     details={"role": u.role, "state": u.status, "reason": end_reason, "count": n})
    return u
