"""Approval and reopening (T-3.3.2, MH-08).

Approval locks the version, re-runs every rule server-side, and refuses while
any item is unreviewed or blocked, or while a bylaw recording basis is not
linked to a clause of the building's current confirmed bylaws (I-23). It writes
the content hash, the approval row, the meeting transition, new deletion dates
for audio and transcript, and the audit event, in one transaction. Approving
twice yields one approval (C-2). Approved versions are immutable (trigger, I-6);
reopening creates a new draft version.
"""

from __future__ import annotations

import hashlib
import json
import uuid
from datetime import timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

from core import audit, clock, jobs
from core.db import Actor
from core.errors import Conflict, Invalid
from core.ids import uuid7
from core.meetings import current_authorization, get_meeting, strata_lot_count
from core.models import (
    Approval,
    AudioAsset,
    Brokerage,
    BylawClause,
    BylawDocument,
    Meeting,
    MinuteItem,
    MinuteItemCitation,
    MinutesVersion,
    Transcript,
)
from core.review import evaluate

ATTESTATION_TEXT_VERSIONS = ("attest-2026.11.1",)
NOT_EVIDENCED = "recording authority not evidenced"


def _canonical(items: list[MinuteItem], cites: dict[uuid.UUID, list[str]]) -> bytes:
    rows = [
        {
            "position": i.position, "item_type": i.item_type, "body_text": i.body_text, "mover": i.mover,
            "seconder": i.seconder, "outcome_method": i.outcome_method, "declared_outcome": i.declared_outcome,
            "threshold": i.threshold, "votes_for": i.votes_for, "votes_against": i.votes_against,
            "votes_abstained": i.votes_abstained, "eligible_votes": i.eligible_votes,
            "members_present": i.members_present, "casting_vote": i.casting_vote,
            "final_outcome": i.final_outcome, "discrepancy_note": i.discrepancy_note,
            "citations": sorted(cites.get(i.id, [])),
        }
        for i in items
    ]
    return json.dumps(rows, sort_keys=True, ensure_ascii=False).encode()


def authority_evidenced(session: Session, meeting: Meeting) -> bool:
    auth = current_authorization(session, meeting.id)
    if auth is None:
        return False
    if auth.basis != "bylaw":
        return True
    if auth.bylaw_clause_id is None:
        return False
    clause = session.get(BylawClause, auth.bylaw_clause_id)
    doc = session.get(BylawDocument, clause.bylaw_document_id) if clause else None
    return doc is not None and doc.status == "current" and doc.strata_id == meeting.strata_id


def approve(session: Session, actor: Actor, meeting_id: uuid.UUID, body: dict[str, Any]) -> Approval:
    m = get_meeting(session, actor, meeting_id)
    if body.get("attestation_text_version") not in ATTESTATION_TEXT_VERSIONS:
        raise Invalid("Unknown attestation wording version.", code="attestation_version")
    session.execute(select(Meeting.id).where(Meeting.id == m.id).with_for_update())
    v = session.scalar(
        select(MinutesVersion).where(MinutesVersion.meeting_id == m.id)
        .order_by(MinutesVersion.version.desc()).with_for_update()
    )
    if v is None:
        raise Conflict("There is no draft to approve.", code="no_draft")
    if v.status == "approved":
        existing = session.scalar(select(Approval).where(Approval.minutes_version_id == v.id))
        if existing is not None:
            return existing  # approving twice creates one approval
    session.refresh(m)
    if m.state != "in_review":
        raise Conflict("The minutes are not in review.", code="not_in_review")
    if not authority_evidenced(session, m):
        raise Conflict(
            "Approval refused: recording authority not evidenced. Link the authorizing clause of the "
            "building's confirmed bylaws.",
            code="authority_not_evidenced",
        )
    items = list(session.scalars(
        select(MinuteItem).where(MinuteItem.minutes_version_id == v.id, MinuteItem.deleted_at.is_(None))
        .order_by(MinuteItem.position).with_for_update()
    ).all())
    lots = strata_lot_count(session, m.strata_id)
    problems: list[dict[str, Any]] = []
    for i in items:
        ev = evaluate(session, i, lots)  # every rule re-run server-side
        if ev is not None and ev.blocked:
            i.review_status, i.blocked_reason = "blocked", ev.blocked_reason
        if i.item_type == "motion" and i.review_status != "reviewed":
            problems.append({"item_id": str(i.id), "position": i.position, "review_status": i.review_status,
                             "blocked_reason": i.blocked_reason})
    session.flush()
    if problems:
        raise Conflict("Every motion must be reviewed and every blocker cleared.", code="items_not_ready",
                       extra={"items": problems})
    cites: dict[uuid.UUID, list[str]] = {}
    for c in session.scalars(select(MinuteItemCitation).where(
        MinuteItemCitation.minute_item_id.in_([i.id for i in items]), MinuteItemCitation.status == "confirmed"
    )):
        cites.setdefault(c.minute_item_id, []).append(str(c.bylaw_clause_id or c.statute_section_id))
    for i in items:
        session.refresh(i)  # read the generated final_outcome
    content_hash = hashlib.sha256(_canonical(items, cites)).digest()
    now = clock.now()
    if v.reopened_from is not None:
        session.execute(update(MinutesVersion).where(MinutesVersion.id == v.reopened_from)
                        .values(status="superseded"))
    v.status, v.content_hash = "approved", content_hash
    approval = Approval(id=uuid7(), brokerage_id=m.brokerage_id, strata_id=m.strata_id, minutes_version_id=v.id,
                        approved_by=actor.user_id, approved_at=now, content_hash=content_hash,
                        attestation_text_version=body["attestation_text_version"])
    session.add(approval)
    session.flush()
    if not jobs.transition(session, m.id, m.state_version, "approved"):
        raise Conflict("The meeting changed while approving; try again.", code="state_conflict")
    b = session.get(Brokerage, m.brokerage_id)
    keep_days = b.audio_retention_days_after_approval if b else 14
    for a in session.scalars(select(AudioAsset).where(AudioAsset.meeting_id == m.id,
                                                       AudioAsset.deleted_at.is_(None))):
        hard_limit = a.created_at + timedelta(days=b.audio_max_days_after_upload if b else 60)
        a.delete_after = min(now + timedelta(days=keep_days), hard_limit)
    t = session.scalar(select(Transcript).where(Transcript.meeting_id == m.id))
    if t is not None:
        t.delete_after = now + timedelta(days=b.transcript_retention_days_after_approval if b else 90)
    audit.record(session, actor, "minutes.approved", strata_id=m.strata_id, target_type="meeting", target_id=m.id,
                 details={"version": v.version})
    session.flush()
    return approval


def reopen(session: Session, actor: Actor, meeting_id: uuid.UUID, body: dict[str, Any]) -> MinutesVersion:
    m = get_meeting(session, actor, meeting_id)
    reason = (body.get("reason") or "").strip()
    if not reason:
        raise Invalid("A reason is required to reopen approved minutes.", code="reason_required")
    session.execute(select(Meeting.id).where(Meeting.id == m.id).with_for_update())
    v = session.scalar(select(MinutesVersion).where(MinutesVersion.meeting_id == m.id)
                       .order_by(MinutesVersion.version.desc()))
    session.refresh(m)
    if v is None or v.status != "approved" or m.state != "approved":
        raise Conflict("Only approved minutes can be reopened.", code="not_approved")
    new = MinutesVersion(
        id=uuid7(), brokerage_id=m.brokerage_id, strata_id=m.strata_id, meeting_id=m.id,
        version=(session.scalar(select(func.max(MinutesVersion.version)).where(MinutesVersion.meeting_id == m.id))
                 or 0) + 1,
        transcript_id=v.transcript_id, llm_model_id=v.llm_model_id, prompt_version=v.prompt_version,
        rules_version=v.rules_version, template_version=v.template_version, reopened_from=v.id,
        reopen_reason=reason,
    )
    session.add(new)
    session.flush()
    skip = {"id", "minutes_version_id", "final_outcome", "created_at", "updated_at", "row_version"}
    for old in session.scalars(select(MinuteItem).where(MinuteItem.minutes_version_id == v.id,
                                                        MinuteItem.deleted_at.is_(None))):
        data = {c.key: getattr(old, c.key) for c in MinuteItem.__mapper__.column_attrs if c.key not in skip}
        copy = MinuteItem(id=uuid7(), minutes_version_id=new.id, **data)
        session.add(copy)
        session.flush()
        for c in session.scalars(select(MinuteItemCitation).where(MinuteItemCitation.minute_item_id == old.id,
                                                                  MinuteItemCitation.status == "confirmed")):
            session.add(MinuteItemCitation(
                id=uuid7(), brokerage_id=c.brokerage_id, strata_id=c.strata_id, minute_item_id=copy.id,
                bylaw_clause_id=c.bylaw_clause_id, statute_section_id=c.statute_section_id,
                quoted_text=c.quoted_text, origin=c.origin, status="confirmed", confirmed_by=c.confirmed_by,
                confirmed_at=c.confirmed_at,
            ))
    session.flush()
    if not jobs.transition(session, m.id, m.state_version, "in_review"):
        raise Conflict("The meeting changed while reopening; try again.", code="state_conflict")
    audit.record(session, actor, "minutes.reopened", strata_id=m.strata_id, target_type="meeting", target_id=m.id,
                 details={"version": new.version})
    return new
