"""Activity timer and per-meeting time report (T-3.3.1 e, T-5.1.2, MH-07, PRD "How M-1 is captured").

The browser sends a heartbeat every 30 s only while the tab is visible and there
was input or audio playing in the last 60 s (client rule; the web app is not
built in B1). The server adds 30 s per accepted heartbeat, ignores heartbeats
closer than 25 s to the previous one (a second tab cannot double-count), and
closes a session after 2 minutes without a heartbeat.
"""

from __future__ import annotations

import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import clock
from core.db import Actor
from core.errors import Invalid
from core.ids import uuid7
from core.meetings import get_meeting
from core.models import MeetingTimeReport, ReviewSession

HEARTBEAT_SECONDS = 30
MIN_GAP_SECONDS = 25
SESSION_GAP_SECONDS = 120
ACTIVITIES = ("setup", "review", "lookup")


def heartbeat(session: Session, actor: Actor, meeting_id: uuid.UUID, activity: str) -> dict[str, Any]:
    m = get_meeting(session, actor, meeting_id)
    if activity not in ACTIVITIES:
        raise Invalid("activity must be setup, review or lookup.")
    now = clock.now()
    open_session = session.scalar(
        select(ReviewSession)
        .where(ReviewSession.meeting_id == m.id, ReviewSession.user_id == actor.user_id,
               ReviewSession.activity == activity,
               ReviewSession.last_heartbeat_at >= now - timedelta(seconds=SESSION_GAP_SECONDS))
        .order_by(ReviewSession.last_heartbeat_at.desc())
        .with_for_update()
    )
    accepted = True
    if open_session is None:
        open_session = ReviewSession(id=uuid7(), brokerage_id=m.brokerage_id, strata_id=m.strata_id,
                                     meeting_id=m.id, user_id=actor.user_id, activity=activity, started_at=now,
                                     last_heartbeat_at=now, active_seconds=HEARTBEAT_SECONDS)
        session.add(open_session)
    elif (now - open_session.last_heartbeat_at).total_seconds() >= MIN_GAP_SECONDS:
        open_session.active_seconds += HEARTBEAT_SECONDS
        open_session.last_heartbeat_at = now
    else:
        accepted = False
    session.flush()
    return {"accepted": accepted, "active_seconds": open_session.active_seconds}


def active_seconds(session: Session, meeting_id: uuid.UUID) -> dict[str, int]:
    out = dict.fromkeys(ACTIVITIES, 0)
    for r in session.scalars(select(ReviewSession).where(ReviewSession.meeting_id == meeting_id)):
        out[r.activity] += r.active_seconds
    return out


def put_time_report(session: Session, actor: Actor, meeting_id: uuid.UUID, body: dict[str, Any]) -> MeetingTimeReport:
    m = get_meeting(session, actor, meeting_id)
    fields = ("post_export_edit_minutes", "dictation_prep_minutes", "self_timed_total_minutes")
    for f in fields:
        v = body.get(f)
        if v is not None and (isinstance(v, bool) or not isinstance(v, int) or v < 0):
            raise Invalid(f"{f} must be a whole number of minutes.")
    sent = date.fromisoformat(body["marked_sent_on"]) if body.get("marked_sent_on") else None
    r = session.get(MeetingTimeReport, m.id, with_for_update=True)
    if r is None:
        r = MeetingTimeReport(meeting_id=m.id, brokerage_id=m.brokerage_id, strata_id=m.strata_id,
                              entered_by=actor.user_id, entered_at=clock.now())
        session.add(r)
    for f in fields:
        if f in body:
            setattr(r, f, body[f])
    if "marked_sent_on" in body:
        r.marked_sent_on = sent
    session.flush()
    return r
