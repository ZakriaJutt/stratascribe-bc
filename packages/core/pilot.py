"""Pilot report: every M-1 term per meeting (T-5.1.2 partial, MH-13, PRD "How M-1 is captured").

After-correction minutes = setup + review and correction + lookup + post-export
editing + dictation. For the first two authorized (recorded) meetings per
brokerage the stopwatch total is the figure used; after that the timer sum is
used and any meeting where timer and stopwatch differ by more than 20% is
flagged. The matched baseline is (mean of drafting minutes / meeting length
over the same manager's stopwatch baselines of the same type) x the pilot
meeting's length; the other type is used only when none exists ("cross-type").
Estimates are never used; such meetings are listed apart. All terms are
proposals [A] in the PRD. Arithmetic is exact (Decimal), rounded only for display.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from datetime import date
from decimal import Decimal
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import authz
from core.activity import active_seconds
from core.db import Actor
from core.models import Approval, AudioAsset, BaselineMeasurement, Meeting, MeetingTimeReport, MinutesVersion

SIXTY = Decimal(60)
DISCREPANCY = Decimal("0.20")


@dataclass(frozen=True)
class BaselineFact:
    user_id: uuid.UUID
    meeting_type: str  # council | general
    meeting_length_minutes: int
    drafting_minutes: int
    method: str  # stopwatch | estimate


@dataclass(frozen=True)
class MeetingFact:
    meeting_id: uuid.UUID
    held_on: date
    meeting_type: str  # council | agm | sgm
    source_type: str
    manager_id: uuid.UUID
    length_minutes: int | None
    setup_seconds: int = 0
    review_seconds: int = 0
    lookup_seconds: int = 0
    post_export_edit_minutes: int | None = None
    dictation_seconds: int = 0
    dictation_prep_minutes: int | None = None
    self_timed_total_minutes: int | None = None


@dataclass
class MeetingRow:
    meeting_id: uuid.UUID
    terms: dict[str, Decimal]
    timer_total: Decimal
    stopwatch_total: Decimal | None
    figure_source: str | None
    after_correction: Decimal | None
    baseline: Decimal | None
    baseline_note: str | None
    net_saving: Decimal | None
    flags: list[str] = field(default_factory=list)


def _type(meeting_type: str) -> str:
    return "council" if meeting_type == "council" else "general"


def matched_baseline(fact: MeetingFact, baselines: list[BaselineFact]) -> tuple[Decimal | None, str | None]:
    own = [b for b in baselines if b.user_id == fact.manager_id]  # never another manager's baseline
    stop = [b for b in own if b.method == "stopwatch"]
    if fact.length_minutes is None:
        return None, "meeting_length_missing"
    same = [b for b in stop if b.meeting_type == _type(fact.meeting_type)]
    note = None
    pool = same
    if not same:
        pool = [b for b in stop if b.meeting_type != _type(fact.meeting_type)]
        note = "cross-type"
    if not pool:
        return None, "estimate_only" if own else "no_baseline"
    ratio = sum((Decimal(b.drafting_minutes) / Decimal(b.meeting_length_minutes) for b in pool), Decimal(0))
    ratio /= Decimal(len(pool))
    return ratio * Decimal(fact.length_minutes), note


def build_report(meetings: list[MeetingFact], baselines: list[BaselineFact]) -> dict[str, Any]:
    ordered = sorted(meetings, key=lambda f: (f.held_on, str(f.meeting_id)))
    recorded_seen = 0
    rows: list[MeetingRow] = []
    for f in ordered:
        terms = {
            "setup": Decimal(f.setup_seconds) / SIXTY,
            "review": Decimal(f.review_seconds) / SIXTY,
            "lookup": Decimal(f.lookup_seconds) / SIXTY,
            "post_export_edit": Decimal(f.post_export_edit_minutes or 0),
            "dictation": Decimal(f.dictation_seconds) / SIXTY + Decimal(f.dictation_prep_minutes or 0),
        }
        timer_total = sum(terms.values(), Decimal(0))
        stopwatch = Decimal(f.self_timed_total_minutes) if f.self_timed_total_minutes is not None else None
        flags: list[str] = []
        first_two = False
        if f.source_type == "recording":
            recorded_seen += 1
            first_two = recorded_seen <= 2
        if first_two:
            figure_source, after = ("stopwatch", stopwatch) if stopwatch is not None else (None, None)
            if stopwatch is None:
                flags.append("stopwatch_required")
        else:
            figure_source, after = "timer", timer_total
            if stopwatch is not None and stopwatch > 0 and abs(timer_total - stopwatch) > DISCREPANCY * stopwatch:
                flags.append("timer_stopwatch_differ_over_20pct")
        baseline, note = matched_baseline(f, baselines)
        if note in ("estimate_only", "no_baseline", "meeting_length_missing"):
            flags.append(note)
        net = baseline - after if baseline is not None and after is not None else None
        rows.append(MeetingRow(f.meeting_id, terms, timer_total, stopwatch, figure_source, after, baseline,
                               note, net, flags))
    used = [r for r in rows if r.net_saving is not None]
    apart = [r for r in rows if r.net_saving is None]
    return {
        "meetings": rows,
        "used_count": len(used),
        "listed_apart_count": len(apart),
        "net_saving_total": sum((r.net_saving for r in used if r.net_saving is not None), Decimal(0)),
    }


def _fmt(d: Decimal | None) -> str | None:
    return None if d is None else str(d.quantize(Decimal("0.1")))


def report_out(report: dict[str, Any]) -> dict[str, Any]:
    return {
        "used_count": report["used_count"],
        "listed_apart_count": report["listed_apart_count"],
        "net_saving_total_minutes": _fmt(report["net_saving_total"]),
        "sample_note": "Two meetings cannot show a median or variance (PRD 'How M-1 is captured').",
        "meetings": [
            {
                "meeting_id": str(r.meeting_id),
                "terms_minutes": {k: _fmt(v) for k, v in r.terms.items()},
                "timer_total_minutes": _fmt(r.timer_total),
                "stopwatch_total_minutes": _fmt(r.stopwatch_total),
                "figure_source": r.figure_source,
                "after_correction_minutes": _fmt(r.after_correction),
                "baseline_minutes": _fmt(r.baseline),
                "baseline_note": r.baseline_note,
                "net_saving_minutes": _fmt(r.net_saving),
                "flags": r.flags,
            }
            for r in report["meetings"]
        ],
    }


def collect(session: Session, actor: Actor) -> tuple[list[MeetingFact], list[BaselineFact]]:
    authz.require_broker(actor)
    facts: list[MeetingFact] = []
    rows = session.execute(
        select(Meeting, Approval.approved_by)
        .join(MinutesVersion, MinutesVersion.meeting_id == Meeting.id)
        .join(Approval, Approval.minutes_version_id == MinutesVersion.id)
        .where(MinutesVersion.version == 1)
    ).all()
    for m, approved_by in rows:
        secs = active_seconds(session, m.id)
        tr = session.get(MeetingTimeReport, m.id)
        dictation = 0
        if m.source_type == "dictated_notes":
            dictation = sum(a.duration_seconds or 0 for a in session.scalars(
                select(AudioAsset).where(AudioAsset.meeting_id == m.id)))
        facts.append(MeetingFact(
            meeting_id=m.id, held_on=m.held_on, meeting_type=m.meeting_type, source_type=m.source_type,
            manager_id=approved_by, length_minutes=m.length_minutes, setup_seconds=secs["setup"],
            review_seconds=secs["review"], lookup_seconds=secs["lookup"],
            post_export_edit_minutes=tr.post_export_edit_minutes if tr else None, dictation_seconds=dictation,
            dictation_prep_minutes=tr.dictation_prep_minutes if tr else None,
            self_timed_total_minutes=tr.self_timed_total_minutes if tr else None,
        ))
    baselines = [
        BaselineFact(b.user_id, b.meeting_type, b.meeting_length_minutes, b.drafting_minutes, b.method)
        for b in session.scalars(select(BaselineMeasurement))
    ]
    return facts, baselines
