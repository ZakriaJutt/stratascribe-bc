"""Regression tests for the review round-3 residual (R6): the database approval path enforces the item rules.

Each case acts as the application role with an assigned manager's context and calls the database path
directly (`app_approve_version`, a hand-written approval row, a hand-written meeting transition), never
`core.approval`.
"""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from core.db import Actor, session_for
from core.devdata import World
from tests.helpers import processed_meeting, review_quorum
from tests.integration.test_pipeline import motions, patch, review_all

pytestmark = pytest.mark.db

ROW = ("INSERT INTO approvals (id, brokerage_id, strata_id, minutes_version_id, approved_by, content_hash, "
       "attestation_text_version) VALUES (gen_random_uuid(), :b, :s, :v, :u, :h, 'attest-2026.11.1')")


def _actor(world: World) -> Actor:
    return Actor.user(world.priya, world.harbourline, "strata_manager")


def _vid(world: World, meeting_id: str) -> Any:
    with session_for(_actor(world)) as s:
        return s.execute(text("SELECT id FROM minutes_versions WHERE meeting_id = :m"), {"m": meeting_id}).scalar()


def _status(world: World, vid: Any) -> str:
    with session_for(_actor(world)) as s:
        return str(s.execute(text("SELECT status FROM minutes_versions WHERE id = :v"), {"v": vid}).scalar())


def _raw_approve(world: World, meeting_id: str, vid: Any, version_hash: bytes, row_hash: bytes,
                 move_meeting: bool) -> None:
    p = {"b": world.harbourline, "s": world.zzs9001, "v": vid, "u": world.priya, "h": row_hash}
    with session_for(_actor(world)) as s:
        s.execute(text("SELECT app_approve_version(:v, :h)"), {"v": vid, "h": version_hash})
        s.execute(text(ROW), p)
        if move_meeting:
            s.execute(text("UPDATE meetings SET state = 'approved', state_version = state_version + 1 "
                           "WHERE id = :m"), {"m": meeting_id})


def test_r6_unreviewed_motions_refused_by_function(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    review_quorum(priya, m["id"])  # quorum reviewed, motions untouched
    vid = _vid(world, m["id"])
    for move in (False, True):
        with pytest.raises(DBAPIError, match="every motion reviewed"):
            _raw_approve(world, m["id"], vid, b"\x01", b"\x01", move)
    assert _status(world, vid) == "draft"


def test_r6_blocked_motion_with_unresolved_discrepancy_refused(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    review_all(priya, m["id"])
    it = motions(priya, m["id"])[1]
    it = patch(priya, it, outcome_method="counted", threshold="three_quarter", votes_for=8, votes_against=3,
               declared_outcome="carried", reviewed=True).json()
    assert it["review_status"] == "blocked"
    vid = _vid(world, m["id"])
    with pytest.raises(DBAPIError, match="every motion reviewed"):
        _raw_approve(world, m["id"], vid, b"\x01", b"\x01", True)
    # Marking it reviewed by hand does not get round it: the reviewed-motion CHECK refuses the row.
    with pytest.raises(DBAPIError), session_for(_actor(world)) as s:
        s.execute(text("UPDATE minute_items SET review_status = 'reviewed', blocked_reason = NULL WHERE id = :i"),
                  {"i": it["id"]})
    assert _status(world, vid) == "draft"


def test_r6_approval_row_hash_must_equal_version_hash(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    review_all(priya, m["id"])
    vid = _vid(world, m["id"])
    with pytest.raises(DBAPIError, match="hash must equal"):
        _raw_approve(world, m["id"], vid, b"\x02", b"\x01", True)
    assert _status(world, vid) == "draft"


def test_r6_meeting_must_be_approved_at_commit(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    review_all(priya, m["id"])
    vid = _vid(world, m["id"])
    with pytest.raises(DBAPIError, match="meeting approved"):
        _raw_approve(world, m["id"], vid, b"\x01", b"\x01", False)
    assert _status(world, vid) == "draft"


def test_r6_helpers_reveal_nothing_across_brokerages(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    vid = _vid(world, m["id"])
    with session_for(Actor.user(world.omar, world.tidewater, "strata_manager")) as s:
        assert s.execute(text("SELECT app_version_hash(:v)"), {"v": vid}).scalar() is None
        assert s.execute(text("SELECT app_meeting_state_of_version(:v)"), {"v": vid}).scalar() is None
