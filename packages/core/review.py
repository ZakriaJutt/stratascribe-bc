"""Review and correction of draft minutes (T-3.3.1, MH-05, MH-06, MH-07).

One item save = one transaction: check ``row_version`` (If-Match), write one
``corrections`` row per changed field with old value, new value, category and
author, re-evaluate the motion through ``packages/rules`` and set the review
status. Corrections feed M-1 and M-5. A declared outcome is only ever the
manager's own selection, attested with who and when; the model's reading is
kept in ``spoken_outcome`` / ``ai_suggestion`` as a suggestion.
"""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

import rules
from core import audit, authz, clock, jobs
from core.db import Actor
from core.errors import Conflict, Invalid, NotFound
from core.ids import uuid7
from core.meetings import get_meeting, strata_lot_count
from core.models import (
    BylawClause,
    BylawDocument,
    Correction,
    MinuteItem,
    MinuteItemCitation,
    MinutesVersion,
)

FIELD_CATEGORY = {
    "body_text": "motion_text",
    "mover": "mover_seconder",
    "seconder": "mover_seconder",
    "outcome_method": "outcome",
    "declared_outcome": "outcome",
    "casting_vote": "outcome",
    "discrepancy_resolution": "outcome",
    "discrepancy_note": "outcome",
    "threshold": "threshold",
    "votes_for": "vote_count",
    "votes_against": "vote_count",
    "votes_abstained": "vote_count",
    "eligible_votes": "vote_count",
    "members_present": "vote_count",
    "item_type": "other",
    "sensitive_flag": "other",
    "position": "other",
}
INT_FIELDS = {"votes_for", "votes_against", "votes_abstained", "eligible_votes", "members_present", "position"}
REVIEW_STATES = ("ready_for_review", "in_review")


def item_out(i: MinuteItem, citations: list[MinuteItemCitation] | None = None) -> dict[str, Any]:
    return {
        "id": str(i.id),
        "position": i.position,
        "item_type": i.item_type,
        "body_text": i.body_text,
        "mover": i.mover,
        "seconder": i.seconder,
        "outcome_method": i.outcome_method,
        "declared_outcome": i.declared_outcome,
        "outcome_attested_at": i.outcome_attested_at.isoformat() if i.outcome_attested_at else None,
        "threshold": i.threshold,
        "votes_for": i.votes_for,
        "votes_against": i.votes_against,
        "votes_abstained": i.votes_abstained,
        "eligible_votes": i.eligible_votes,
        "members_present": i.members_present,
        "casting_vote": i.casting_vote,
        "computed_result": i.computed_result,
        "computed_formula": i.computed_formula,
        "rules_version": i.rules_version,
        "discrepancy_resolution": i.discrepancy_resolution,
        "discrepancy_note": i.discrepancy_note,
        "final_outcome": i.final_outcome,
        "suggestion": {"spoken_outcome": i.spoken_outcome, "original": i.ai_suggestion},
        "source_segment_ids": [str(x) for x in i.source_segment_ids],
        "origin": i.origin,
        "review_status": i.review_status,
        "blocked_reason": i.blocked_reason,
        "sensitive_flag": i.sensitive_flag,
        "row_version": i.row_version,
        "citations": [
            {
                "id": str(c.id),
                "bylaw_clause_id": str(c.bylaw_clause_id) if c.bylaw_clause_id else None,
                "quoted_text": c.quoted_text,
                "origin": c.origin,
                "status": c.status,
            }
            for c in (citations or [])
            if c.status != "removed"
        ],
    }


def current_version(session: Session, meeting_id: uuid.UUID) -> MinutesVersion | None:
    return session.scalar(
        select(MinutesVersion).where(MinutesVersion.meeting_id == meeting_id).order_by(MinutesVersion.version.desc())
    )


def draft_out(session: Session, actor: Actor, meeting_id: uuid.UUID) -> dict[str, Any]:
    m = get_meeting(session, actor, meeting_id)
    v = current_version(session, m.id)
    if v is None:
        return {"meeting_id": str(m.id), "state": m.state, "version": None, "items": []}
    items = session.scalars(
        select(MinuteItem)
        .where(MinuteItem.minutes_version_id == v.id, MinuteItem.deleted_at.is_(None))
        .order_by(MinuteItem.position)
    ).all()
    cites = session.scalars(
        select(MinuteItemCitation).where(MinuteItemCitation.minute_item_id.in_([i.id for i in items]))
    ).all()
    by_item: dict[uuid.UUID, list[MinuteItemCitation]] = {}
    for c in cites:
        by_item.setdefault(c.minute_item_id, []).append(c)
    return {
        "meeting_id": str(m.id),
        "state": m.state,
        "version": v.version,
        "version_id": str(v.id),
        "status": v.status,
        "rules_version": v.rules_version,
        "items": [item_out(i, by_item.get(i.id)) for i in items],
    }


def _motion_input(i: MinuteItem, lots: int | None) -> rules.MotionInput:
    return rules.MotionInput(
        outcome_method=i.outcome_method,
        declared_outcome=i.declared_outcome,
        outcome_attested=i.outcome_attested_at is not None,
        threshold=i.threshold,
        votes_for=i.votes_for,
        votes_against=i.votes_against,
        votes_abstained=i.votes_abstained,
        eligible_votes=i.eligible_votes,
        members_present=i.members_present,
        casting_vote=i.casting_vote,
        discrepancy_resolution=i.discrepancy_resolution,
        discrepancy_note=i.discrepancy_note,
        strata_lot_count=lots,
    )


def evaluate(session: Session, item: MinuteItem, lots: int | None) -> rules.MotionEvaluation | None:
    """Re-run the rules for a motion and store the rules package's columns as given."""
    if item.item_type != "motion":
        return None
    try:
        ev = rules.evaluate_motion(_motion_input(item, lots))
    except rules.RuleInputError as exc:
        raise Invalid(str(exc), code="rule_input") from exc
    for column, value in ev.columns.items():
        setattr(item, column, value)
    return ev


def _load_item(session: Session, actor: Actor, item_id: uuid.UUID) -> tuple[MinuteItem, MinutesVersion]:
    authz.locate(session, actor, "minute_item", item_id)
    item = session.get(MinuteItem, item_id, with_for_update=True)
    if item is None or item.deleted_at is not None:
        raise NotFound("Not found.")
    v = session.get(MinutesVersion, item.minutes_version_id)
    if v is None or v.status != "draft":
        raise Conflict("Approved minutes cannot be changed. Reopen them to make a new version.", code="approved")
    return item, v


def _start_review(session: Session, meeting_id: uuid.UUID) -> None:
    jobs.advance(session, meeting_id, ("ready_for_review",), "in_review")


def _set_status(item: MinuteItem, ev: rules.MotionEvaluation | None, mark_reviewed: bool | None) -> None:
    if ev is not None and ev.blocked and (mark_reviewed or item.review_status == "reviewed"
                                          or item.outcome_method is not None):
        item.review_status, item.blocked_reason = "blocked", ev.blocked_reason
        return
    item.blocked_reason = None
    if mark_reviewed is True:
        item.review_status = "reviewed"
    elif mark_reviewed is False or item.review_status == "blocked":
        item.review_status = "needs_review"


def update_item(
    session: Session, actor: Actor, item_id: uuid.UUID, if_match: int | None, changes: dict[str, Any]
) -> MinuteItem:
    item, v = _load_item(session, actor, item_id)  # access first: 403/404 before any validation
    if if_match is None:
        raise Invalid("If-Match with the item's row_version is required.", code="if_match_required")
    if item.row_version != if_match:
        raise Conflict("This item was changed elsewhere.", code="version_conflict",
                       extra={"current": item_out(item)})
    mark_reviewed = changes.pop("reviewed", None)
    unknown = set(changes) - set(FIELD_CATEGORY)
    if unknown:
        raise Invalid(f"Fields cannot be edited: {sorted(unknown)}", code="field_not_editable")
    lots = strata_lot_count(session, item.strata_id)
    with session.no_autoflush:  # the row is written once, after the rules have run
        now = clock.now()
        for field, new in changes.items():
            if field in INT_FIELDS and new is not None and (isinstance(new, bool) or not isinstance(new, int)):
                raise Invalid(f"{field} must be a whole number.", code="rule_input")
            old = getattr(item, field)
            if old == new:
                continue
            setattr(item, field, new)
            session.add(
                Correction(
                    id=uuid7(), brokerage_id=item.brokerage_id, strata_id=item.strata_id, minute_item_id=item.id,
                    field=field, old_value=None if old is None else str(old),
                    new_value=None if new is None else str(new),
                    category=FIELD_CATEGORY[field], made_by=actor.user_id, made_at=now,
                )
            )
            if field == "declared_outcome":
                # The manager's own selection, attested now; never pre-filled by the model.
                item.outcome_attested_by = actor.user_id if new is not None else None
                item.outcome_attested_at = now if new is not None else None
            if field == "outcome_method" and new == "declared":
                item.casting_vote = None
        if item.discrepancy_resolution == "recorded_as_declared" and not (item.discrepancy_note or "").strip():
            raise Invalid(rules.motion.BLOCK_NOTE, code="discrepancy_note_required")
        ev = evaluate(session, item, lots)
        _set_status(item, ev, mark_reviewed)
    session.flush()
    session.refresh(item)
    _start_review(session, v.meeting_id)
    audit.record(session, actor, "item.corrected", strata_id=item.strata_id, target_type="minute_item",
                 target_id=item.id, details={"count": len(changes)})
    return item


def add_item(session: Session, actor: Actor, meeting_id: uuid.UUID, body: dict[str, Any]) -> MinuteItem:
    m = get_meeting(session, actor, meeting_id)
    v = current_version(session, m.id)
    if v is None or v.status != "draft":
        raise Conflict("There is no draft to add to.", code="no_draft")
    item_type = body.get("item_type", "motion")
    pos = body.get("position") or (session.scalar(
        select(func.coalesce(func.max(MinuteItem.position), 0)).where(MinuteItem.minutes_version_id == v.id)
    ) or 0) + 1
    item = MinuteItem(
        id=uuid7(), brokerage_id=m.brokerage_id, strata_id=m.strata_id, minutes_version_id=v.id, position=pos,
        item_type=item_type, body_text=str(body.get("body_text", "")), mover=body.get("mover"),
        seconder=body.get("seconder"), origin="manager_added",
    )
    session.add(item)
    session.flush()
    session.add(Correction(id=uuid7(), brokerage_id=m.brokerage_id, strata_id=m.strata_id, minute_item_id=item.id,
                           field="item", old_value=None, new_value=item_type, category="item_added",
                           made_by=actor.user_id, made_at=clock.now()))
    _start_review(session, m.id)
    session.flush()
    session.refresh(item)
    return item


def delete_item(session: Session, actor: Actor, item_id: uuid.UUID, reason: str | None) -> None:
    item, v = _load_item(session, actor, item_id)
    item.deleted_at = clock.now()
    item.delete_reason = (reason or "").strip() or "removed by manager"
    session.add(Correction(id=uuid7(), brokerage_id=item.brokerage_id, strata_id=item.strata_id,
                           minute_item_id=item.id, field="item", old_value=item.item_type, new_value=None,
                           category="item_deleted", made_by=actor.user_id, made_at=clock.now()))
    _start_review(session, v.meeting_id)
    session.flush()


# ---------------------------------------------------------------- citations on items (I-16)


def _check_clause(session: Session, actor: Actor, clause_id: uuid.UUID, strata_id: uuid.UUID) -> BylawClause:
    loc = authz.locate(session, actor, "bylaw_clause", clause_id)
    if loc.strata_id != strata_id:
        raise Invalid("The clause must be from this building's bylaws.", code="clause_other_building")
    clause = session.get(BylawClause, clause_id)
    doc = session.get(BylawDocument, clause.bylaw_document_id) if clause else None
    if clause is None or doc is None or doc.status != "current":
        raise Invalid("The clause must be from the building's current confirmed bylaws.", code="clause_not_current")
    return clause


def _citation_correction(session: Session, actor: Actor, item: MinuteItem, old: str | None, new: str | None) -> None:
    session.add(Correction(id=uuid7(), brokerage_id=item.brokerage_id, strata_id=item.strata_id,
                           minute_item_id=item.id, field="citation", old_value=old, new_value=new,
                           category="citation", made_by=actor.user_id, made_at=clock.now()))


def add_citation(session: Session, actor: Actor, item_id: uuid.UUID, body: dict[str, Any]) -> MinuteItemCitation:
    """Attach (``bylaw_clause_id``), replace (plus ``replaces_citation_id``) or confirm a suggestion."""
    item, v = _load_item(session, actor, item_id)
    now = clock.now()
    if body.get("confirm_citation_id"):
        c = session.get(MinuteItemCitation, uuid.UUID(body["confirm_citation_id"]), with_for_update=True)
        if c is None or c.minute_item_id != item.id or c.status != "suggested":
            raise NotFound("Not found.")
        if c.bylaw_clause_id:
            _check_clause(session, actor, c.bylaw_clause_id, item.strata_id)
        c.status, c.confirmed_by, c.confirmed_at = "confirmed", actor.user_id, now
        _citation_correction(session, actor, item, "suggested", str(c.bylaw_clause_id))
        session.flush()
        _start_review(session, v.meeting_id)
        return c
    try:
        clause_id = uuid.UUID(str(body["bylaw_clause_id"]))
    except (KeyError, ValueError) as exc:
        raise Invalid("bylaw_clause_id is required.") from exc
    clause = _check_clause(session, actor, clause_id, item.strata_id)
    quote = body.get("quoted_text")
    if quote is not None and quote not in clause.body_text:
        raise Invalid("The quotation must match the clause text exactly.", code="quote_not_exact")
    old_value = None
    if body.get("replaces_citation_id"):
        old = session.get(MinuteItemCitation, uuid.UUID(body["replaces_citation_id"]), with_for_update=True)
        if old is None or old.minute_item_id != item.id or old.status == "removed":
            raise NotFound("Not found.")
        old.status = "removed"
        old_value = str(old.bylaw_clause_id)
    c = MinuteItemCitation(
        id=uuid7(), brokerage_id=item.brokerage_id, strata_id=item.strata_id, minute_item_id=item.id,
        bylaw_clause_id=clause.id, quoted_text=quote, origin="manager_added", status="confirmed",
        confirmed_by=actor.user_id, confirmed_at=now,
    )
    session.add(c)
    _citation_correction(session, actor, item, old_value, str(clause.id))
    session.flush()
    _start_review(session, v.meeting_id)
    return c


def remove_citation(session: Session, actor: Actor, citation_id: uuid.UUID) -> None:
    authz.locate(session, actor, "minute_item_citation", citation_id)
    c = session.get(MinuteItemCitation, citation_id, with_for_update=True)
    if c is None or c.status == "removed":
        raise NotFound("Not found.")
    item, _v = _load_item(session, actor, c.minute_item_id)
    session.execute(update(MinuteItemCitation).where(MinuteItemCitation.id == c.id).values(status="removed"))
    _citation_correction(session, actor, item, str(c.bylaw_clause_id), None)
    session.flush()
