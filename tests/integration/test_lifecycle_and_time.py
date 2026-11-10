"""Retention sweep (I-9, I-22), activity timer (I-13, server side), pilot report (I-15)."""

from __future__ import annotations

import uuid
from datetime import UTC, date, datetime, timedelta
from decimal import Decimal
from typing import Any

import pytest
from sqlalchemy import create_engine, select, text

from core import clock, config, retention, storage
from core.db import Actor, session_for
from core.devdata import World
from core.models import AudioAsset
from tests.helpers import Api, authorize, fake_wav, new_meeting, processed_meeting, sha, upload

pytestmark = pytest.mark.db


def owner_exec(sql: str, **params: Any) -> Any:
    eng = create_engine(config.settings().migration_database_url)
    with eng.begin() as c:
        out = c.execute(text(sql), params).all() if sql.lstrip().upper().startswith("SELECT") else \
            c.execute(text(sql), params)
    eng.dispose()
    return out


def test_i9_sweep_deletes_expired_audio_and_is_safe_twice(world: World, as_user: Any) -> None:
    api: Api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    authorize(api, m["id"])
    for i in range(10):
        upload(api, m["id"], fake_wav(bytes([i]) * 20))
    assets = owner_exec("SELECT id, storage_key FROM audio_assets")
    assert len(assets) == 10
    storage.store().delete(assets[0][1])  # one object already missing
    owner_exec("UPDATE audio_assets SET delete_after = now() - interval '1 hour'")
    first = retention.sweep()
    assert first == {"deleted": 10, "object_missing": 1, "abandoned_uploads": 0}
    assert not [k for k in storage.store().list_prefix("b/") if "/audio/" in k]
    events = owner_exec("SELECT count(*) FROM audio_assets WHERE deleted_at IS NOT NULL")
    assert events[0][0] == 10
    assert owner_exec("SELECT count(*) FROM audit_events WHERE action = 'audio.deleted'")[0][0] == 10
    second = retention.sweep()
    assert second == {"deleted": 0, "object_missing": 0, "abandoned_uploads": 0}
    assert owner_exec("SELECT count(*) FROM audit_events WHERE action = 'audio.deleted'")[0][0] == 10


def test_i22_abandoned_upload_parts_are_removed(world: World, as_user: Any) -> None:
    api: Api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    authorize(api, m["id"])
    data = fake_wav(b"x" * 500)
    a = api.post(f"/meetings/{m['id']}/uploads", {"sha256": sha(data), "byte_size": len(data),
                                                  "extension": "wav"}).json()
    api.patch(f"/uploads/{a['id']}", content=data[:200], params={"offset": 0})
    owner_exec("UPDATE audio_assets SET created_at = now() - interval '25 hours'")
    assert retention.sweep()["abandoned_uploads"] == 1
    assert storage.store().list_prefix("b/") == []
    state = owner_exec("SELECT upload_state FROM audio_assets")[0][0]
    assert state == "failed"


def test_audio_never_kept_past_hard_limit(world: World, as_user: Any) -> None:
    api: Api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    authorize(api, m["id"])
    upload(api, m["id"], fake_wav())
    with session_for(Actor.user(world.priya, world.harbourline, "strata_manager")) as s:
        a = s.scalar(select(AudioAsset))
        assert a is not None and a.delete_after is not None
        assert abs((a.delete_after - a.created_at).total_seconds() - 60 * 86400) < 10


def test_i13_server_side_activity_accounting(world: World, as_user: Any) -> None:
    """Scripted heartbeats for: 2 min setup, 3 min typing + 3 min listening (review), 2 min backgrounded.

    The client sends no heartbeat while hidden (client rule, web app not built), so the
    background minutes produce no requests. Expected: setup 120 s, review 360 s, within +/-15 s.
    """
    api: Api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)
    t0 = datetime(2026, 11, 2, 18, 0, tzinfo=UTC)
    current = {"t": t0}
    clock.set_clock(lambda: current["t"])

    def beat(activity: str, at_s: int) -> dict[str, Any]:
        current["t"] = t0 + timedelta(seconds=at_s)
        r = api.post(f"/meetings/{m['id']}/activity/heartbeat", {"activity": activity})
        assert r.status_code == 200, r.text
        return dict(r.json())

    for s in range(30, 121, 30):
        beat("setup", s)
    for s in range(150, 481, 30):  # 6 minutes of review: typing then listening
        beat("review", s)
    dup = beat("review", 490)  # a second tab 10 s later is ignored
    assert dup["accepted"] is False
    # 2 minutes in the background: no heartbeats; then one more review heartbeat after the gap
    after = beat("review", 480 + 150)
    clock.set_clock(None)
    rows = owner_exec("SELECT activity, sum(active_seconds) FROM review_sessions GROUP BY activity")
    got = dict(rows)
    assert abs(got["setup"] - 120) <= 15
    assert abs(got["review"] - 360 - 30) <= 15  # the post-gap heartbeat opens a new session worth 30 s
    assert after["active_seconds"] == 30


def test_i14_business_days_across_holiday() -> None:
    from core.timecal import business_days_after

    holidays = [date(2026, 12, 25)]  # test table only; the real BC list is T-5.1.2
    assert business_days_after(date(2026, 12, 24), date(2026, 12, 30), holidays) == 3
    assert business_days_after(date(2026, 12, 24), date(2026, 12, 31), holidays) == 4


def _approve(api: Api, world: World, mid: str, doc: dict[str, Any]) -> None:
    clause = next(c for c in doc["clauses"] if c["clause_number"] == "8(1)")
    assert authorize(api, mid, bylaw_clause_id=clause["id"]).status_code == 200
    for it in [i for i in api.get(f"/meetings/{mid}/draft").json()["items"] if i["item_type"] == "motion"]:
        api.patch(f"/minute-items/{it['id']}", {"outcome_method": "declared", "declared_outcome": "carried",
                                                 "reviewed": True}, headers={"If-Match": str(it["row_version"])})
    assert api.post(f"/meetings/{mid}/approve", {"attestation_text_version": "attest-2026.11.1"}).status_code == 200


def test_i15_pilot_report_equals_hand_calculation(world: World, as_user: Any) -> None:
    from tests.helpers import bylaw_text

    priya: Api = as_user(world.priya)
    doc = priya.post(f"/buildings/{world.zzs9001}/bylaw-documents",
                     {"kind": "bylaws", "text": bylaw_text("bylaws_zzs9001.txt"), "filed_on": "2025-03-01"}).json()
    priya.post(f"/bylaw-documents/{doc['id']}/confirm")
    # Baselines (Priya's own stopwatch entries): council 120 min meeting took 240 min; council 60 took 90.
    # Mean ratio council = (2.0 + 1.5) / 2 = 1.75. General: 180 min meeting took 270 -> 1.5. One estimate (ignored).
    for mt, length, drafting, method in [("council", 120, 240, "stopwatch"), ("council", 60, 90, "stopwatch"),
                                         ("general", 180, 270, "stopwatch"), ("council", 60, 600, "estimate")]:
        r = priya.post("/pilot/baselines", {"meeting_type": mt, "meeting_length_minutes": length,
                                            "drafting_minutes": drafting, "method": method,
                                            "noted_on": "2026-09-01"})
        assert r.status_code == 201
    ms = []
    for held, mtype, length in [("2026-10-01", "council", 90), ("2026-10-08", "agm", 120),
                                ("2026-10-15", "council", 100)]:
        m = processed_meeting(priya, world.zzs9001, held_on=held, meeting_type=mtype, length_minutes=length)
        _approve(priya, world, m["id"], doc)
        ms.append(m)
    # Timers and time reports set directly (I-13 covers how timers accrue)
    timers = [(600, 1800, 300), (900, 2400, 600), (300, 1200, 0)]  # setup, review, lookup seconds
    reports = [(10, 75), (15, 100), (5, 30)]  # post-export edit minutes, stopwatch total
    for m, (su, rv, lk), (pe, sw) in zip(ms, timers, reports, strict=True):
        for act, secs in (("setup", su), ("review", rv), ("lookup", lk)):
            if secs:
                owner_exec("INSERT INTO review_sessions (id, brokerage_id, strata_id, meeting_id, user_id, activity, "
                           "started_at, last_heartbeat_at, active_seconds) VALUES (:i, :b, :s, :m, :u, :a, now(), "
                           "now(), :n)", i=uuid.uuid4(), b=world.harbourline, s=world.zzs9001, m=m["id"],
                           u=world.priya, a=act, n=secs)
        assert priya.put(f"/meetings/{m['id']}/time-report", {"post_export_edit_minutes": pe,
                                                              "self_timed_total_minutes": sw}).status_code == 200
    assert priya.get("/pilot/report").status_code == 403  # broker only
    rep = as_user(world.marta).get("/pilot/report").json()
    rows = {r["meeting_id"]: r for r in rep["meetings"]}
    r1, r2, r3 = (rows[m["id"]] for m in ms)
    # Meeting 1 (first authorized): stopwatch 75 is used. Baseline council 1.75 x 90 = 157.5. Net 82.5.
    assert r1["figure_source"] == "stopwatch" and r1["after_correction_minutes"] == "75.0"
    assert r1["baseline_minutes"] == "157.5" and r1["net_saving_minutes"] == "82.5"
    assert r1["timer_total_minutes"] == "55.0"  # 10 + 30 + 5 + 10
    # Meeting 2 (second authorized, AGM): stopwatch 100. Baseline general 1.5 x 120 = 180. Net 80.
    assert r2["figure_source"] == "stopwatch" and r2["baseline_minutes"] == "180.0"
    assert r2["net_saving_minutes"] == "80.0"
    # Meeting 3: timer sum = 5 + 20 + 0 + 5 = 30; stopwatch 30 agrees. Baseline 1.75 x 100 = 175. Net 145.
    assert r3["figure_source"] == "timer" and r3["after_correction_minutes"] == "30.0"
    assert r3["net_saving_minutes"] == "145.0" and r3["flags"] == []
    assert rep["used_count"] == 3 and rep["net_saving_total_minutes"] == str(Decimal("307.5"))


def test_pilot_report_estimates_listed_apart_and_cross_type() -> None:
    from core.pilot import BaselineFact, MeetingFact, build_report

    u, other = uuid.uuid4(), uuid.uuid4()
    facts = [MeetingFact(uuid.uuid4(), date(2026, 10, d), "council", "recording", u, 60,
                         self_timed_total_minutes=40) for d in (1, 2)]
    facts.append(MeetingFact(uuid.uuid4(), date(2026, 10, 3), "council", "recording", u, 60, review_seconds=3600,
                             self_timed_total_minutes=30))
    rep = build_report(facts, [BaselineFact(u, "general", 100, 200, "stopwatch"),
                               BaselineFact(other, "council", 60, 600, "stopwatch")])
    rows = rep["meetings"]
    assert all(r.baseline_note == "cross-type" for r in rows)  # another manager's baseline is never used
    assert rows[0].baseline == Decimal(120) and rows[0].net_saving == Decimal(80)
    assert "timer_stopwatch_differ_over_20pct" in rows[2].flags  # timer 60 vs stopwatch 30
    only_est = build_report(facts[:1], [BaselineFact(u, "council", 60, 90, "estimate")])
    assert only_est["listed_apart_count"] == 1 and "estimate_only" in only_est["meetings"][0].flags
