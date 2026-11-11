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
from dataclasses import dataclass
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.orm import Session

import rules
from ai.answer import MIN_QUOTE_WORDS, quote_ok
from core import audit, authz, clock, jobs
from core.db import Actor
from core.errors import Conflict, Invalid, NotFound
from core.ids import uuid7
from core.meetings import get_meeting
from core.models import (
    BylawClause,
    BylawDocument,
    Correction,
    Meeting,
    MinuteItem,
    MinuteItemCitation,
    MinutesVersion,
    StrataCorporation,
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
    "quorum_basis": "attendance",
    "quorum_statement": "attendance",
    "present_count": "attendance",
    "eligible_count": "attendance",
}
INT_FIELDS = {"votes_for", "votes_against", "votes_abstained", "eligible_votes", "members_present", "position",
              "present_count", "eligible_count"}
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
        "quorum": None if i.item_type != "quorum" else {
            "basis": i.quorum_basis, "statement": i.quorum_statement, "present_count": i.present_count,
            "eligible_count": i.eligible_count, "required_count": i.required_count, "met": i.quorum_met,
            "rule": i.quorum_rule, "formula": i.quorum_formula,
            "attested_at": i.quorum_attested_at.isoformat() if i.quorum_attested_at else None,
            "statement_text": quorum_wording(i),
        },
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


COUNT_FIELDS = ("threshold", "votes_for", "votes_against", "votes_abstained", "eligible_votes", "members_present",
                "casting_vote", "discrepancy_resolution", "discrepancy_note")
QUORUM_INPUTS = ("quorum_basis", "quorum_statement", "present_count", "eligible_count")
MOTION_ONLY = ("outcome_method", "declared_outcome", *COUNT_FIELDS)

BLOCK_QUORUM_BASIS = ("Record how quorum was established: counted from attendance, declared by the chair, "
                      "or not recorded because attendance is unknown.")
BLOCK_QUORUM_NOT_RECORDED = "When attendance is unknown the minutes can only record 'quorum not recorded'."
BLOCK_QUORUM_COUNTED_STATEMENT = "With attendance figures the minutes record quorum established or not established."
QUORUM_NOT_RECORDED_WORDING = (
    "Quorum: not recorded. The number of votes present was not available to the manager who prepared "
    "these minutes."
)


def quorum_wording(i: MinuteItem) -> str | None:
    """The quorum sentence printed in the minutes, built only from stored fields (lead ruling)."""
    if i.item_type != "quorum" or i.quorum_statement is None:
        return None
    if i.quorum_statement == "not_recorded":
        return QUORUM_NOT_RECORDED_WORDING
    if i.quorum_basis == "declared":
        return "Quorum was declared established by the chair."
    said = "Quorum was established" if i.quorum_statement == "established" else "Quorum was not established"
    return (f"{said}: {i.present_count} present of {i.eligible_count} eligible; {i.required_count} required "
            f"({i.quorum_rule}, {i.rules_version}).")
BLOCK_QUORUM_NUMBERS = "Enter the votes (or council members) present and the number eligible."
BLOCK_QUORUM_STATEMENT = "Select what the minutes record: quorum established or not established."
BLOCK_QUORUM_DECLARED = "A quorum declared by the chair can only record that quorum was established."
BLOCK_QUORUM_LOTS = "Enter the building's strata lot and owner counts; they select the quorum rule."


@dataclass(frozen=True)
class Evaluation:
    blocked_reason: str | None

    @property
    def blocked(self) -> bool:
        return self.blocked_reason is not None


@dataclass(frozen=True)
class Context:
    meeting_type: str
    reconvened: bool
    lots: int | None
    owners: int | None
    general_rule: dict[str, Any] | None
    council_rule: dict[str, Any] | None


def context(session: Session, item: MinuteItem) -> Context:
    v = session.get(MinutesVersion, item.minutes_version_id)
    m = session.get(Meeting, v.meeting_id) if v else None
    b = session.get(StrataCorporation, item.strata_id)
    if m is None or b is None:  # pragma: no cover - FKs guarantee both
        raise NotFound("Not found.")
    return Context(m.meeting_type, m.reconvened_after_adjournment, b.strata_lot_count, b.owner_count,
                   b.general_quorum_rule, b.council_quorum_rule)


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


_QUORUM_COMPUTED = {"required_count": None, "quorum_met": None, "quorum_rule": None, "quorum_formula": None,
                    "rules_version": None}


def _evaluate_quorum(item: MinuteItem, ctx: Context) -> Evaluation:
    """Quorum from the numbers the manager confirmed (B1-006), computed by packages/rules."""
    cols: dict[str, object] = dict(_QUORUM_COMPUTED)
    reason: str | None = None
    if item.quorum_basis is None:
        reason = BLOCK_QUORUM_BASIS
    elif item.quorum_basis == "not_recorded":
        if item.quorum_statement != "not_recorded" or item.present_count is not None:
            reason = BLOCK_QUORUM_NOT_RECORDED
    elif item.quorum_basis == "declared":
        if item.quorum_statement is None:
            reason = BLOCK_QUORUM_STATEMENT
        elif item.quorum_statement != "established":
            reason = BLOCK_QUORUM_DECLARED
    elif item.present_count is None or item.eligible_count is None:
        reason = BLOCK_QUORUM_NUMBERS
    else:
        try:
            if ctx.meeting_type == "council":
                res = rules.council_quorum(members_present=item.present_count, council_size=item.eligible_count,
                                           override=ctx.council_rule)
            elif ctx.lots is None or ctx.owners is None:
                res = None
                reason = BLOCK_QUORUM_LOTS
            else:
                res = rules.general_quorum(present_votes=item.present_count, eligible_votes=item.eligible_count,
                                           strata_lot_count=ctx.lots, owner_count=ctx.owners,
                                           reconvened_after_adjournment=ctx.reconvened, override=ctx.general_rule)
        except rules.RuleInputError as exc:
            raise Invalid(str(exc), code="rule_input") from exc
        if res is not None:
            cols = res.columns()
            if item.quorum_statement is None:
                reason = BLOCK_QUORUM_STATEMENT
            elif item.quorum_statement == "not_recorded":
                reason = BLOCK_QUORUM_COUNTED_STATEMENT
            elif (item.quorum_statement == "established") != res.met:
                said = "established" if item.quorum_statement == "established" else "not established"
                got = "met" if res.met else "not met"
                reason = f"The minutes record quorum {said}, but the numbers give quorum {got} ({res.formula})."
    for column, value in cols.items():
        setattr(item, column, value)
    return Evaluation(reason)


def evaluate(session: Session, item: MinuteItem, ctx: Context | None = None) -> Evaluation | None:
    """Re-run the rules for a motion or quorum item and store the rules package's columns as given."""
    if item.item_type not in ("motion", "quorum"):
        return None
    ctx = ctx or context(session, item)
    if item.item_type == "quorum":
        return _evaluate_quorum(item, ctx)
    try:
        ev = rules.evaluate_motion(_motion_input(item, ctx.lots))
    except rules.RuleInputError as exc:
        raise Invalid(str(exc), code="rule_input") from exc
    for column, value in ev.columns.items():
        setattr(item, column, value)
    return Evaluation(ev.blocked_reason)


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


def _set_status(item: MinuteItem, ev: Evaluation | None, mark_reviewed: bool | None) -> None:
    started = item.outcome_method is not None or item.quorum_basis is not None
    if ev is not None and ev.blocked and (mark_reviewed or item.review_status == "reviewed" or started):
        item.review_status, item.blocked_reason = "blocked", ev.blocked_reason
        return
    item.blocked_reason = None
    if mark_reviewed is True:
        item.review_status = "reviewed"
    elif mark_reviewed is False or item.review_status == "blocked":
        item.review_status = "needs_review"


def _correct(session: Session, actor: Actor, item: MinuteItem, field: str, old: Any, new: Any, now: Any) -> None:
    session.add(
        Correction(
            id=uuid7(), brokerage_id=item.brokerage_id, strata_id=item.strata_id, minute_item_id=item.id,
            field=field, old_value=None if old is None else str(old), new_value=None if new is None else str(new),
            category=FIELD_CATEGORY[field], made_by=actor.user_id, made_at=now,
        )
    )


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
    item_type = changes.get("item_type", item.item_type)
    if item_type != "quorum" and any(changes.get(f) is not None for f in QUORUM_INPUTS):
        raise Invalid("Attendance figures belong on the quorum item.", code="quorum_fields_on_other_item")
    if item_type != "motion" and any(changes.get(f) is not None for f in MOTION_ONLY):
        raise Invalid("Outcome and vote fields belong on a motion.", code="motion_fields_on_other_item")
    method = changes.get("outcome_method", item.outcome_method)
    if method != "counted" and any(changes.get(f) is not None for f in COUNT_FIELDS):
        # A show-of-cards motion stores no counts or threshold (B1-005).
        raise Invalid("Counts and a threshold are recorded only when a precise count was taken. Choose "
                      "'counted' to enter them.", code="counts_on_declared")
    ctx = context(session, item)
    with session.no_autoflush:  # the row is written once, after the rules have run
        now = clock.now()
        for field, new in changes.items():
            if field in INT_FIELDS and new is not None and (isinstance(new, bool) or not isinstance(new, int)):
                raise Invalid(f"{field} must be a whole number.", code="rule_input")
            old = getattr(item, field)
            if old == new:
                continue
            setattr(item, field, new)
            _correct(session, actor, item, field, old, new, now)
            if field == "declared_outcome":
                # The manager's own selection, attested now; never pre-filled by the model.
                item.outcome_attested_by = actor.user_id if new is not None else None
                item.outcome_attested_at = now if new is not None else None
            if field in ("quorum_basis", "quorum_statement"):
                declared = item.quorum_basis in ("declared", "not_recorded")  # the manager attests either
                item.quorum_attested_by = actor.user_id if declared else None
                item.quorum_attested_at = now if declared else None
        if item.outcome_method != "counted":
            for field in COUNT_FIELDS:  # stale counts from an earlier "counted" choice are cleared, as corrections
                old = getattr(item, field)
                if old is not None:
                    setattr(item, field, None)
                    _correct(session, actor, item, field, old, None, now)
        if item.discrepancy_resolution == "recorded_as_declared" and not (item.discrepancy_note or "").strip():
            raise Invalid(rules.motion.BLOCK_NOTE, code="discrepancy_note_required")
        ev = evaluate(session, item, ctx)
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
    if quote is not None and (not isinstance(quote, str) or not quote_ok(clause.body_text, quote)):
        raise Invalid(f"The quotation must be at least {MIN_QUOTE_WORDS} words copied exactly from the clause.",
                      code="quote_not_exact")
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
