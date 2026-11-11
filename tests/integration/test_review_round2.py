"""Regression tests for review round 2, B1-012: no way to an approved minutes version except approval."""

from __future__ import annotations

import os
from typing import Any

import pytest
from sqlalchemy import text
from sqlalchemy.exc import DBAPIError

from core.db import Actor, session_for
from core.devdata import World
from tests.helpers import new_meeting, processed_meeting
from tests.integration.test_pipeline import ATTEST, link_confirmed_clause, review_all

pytestmark = pytest.mark.db


def _actor(world: World) -> Actor:
    return Actor.user(world.priya, world.harbourline, "strata_manager")


def _version(world: World, meeting_id: str) -> Any:
    with session_for(_actor(world)) as s:
        return s.execute(text("SELECT id, version FROM minutes_versions WHERE meeting_id = :m"),
                         {"m": meeting_id}).one()


INSERT = ("INSERT INTO minutes_versions (id, brokerage_id, strata_id, meeting_id, version, rules_version{extra}) "
          "VALUES (gen_random_uuid(), :b, :s, :m, 9, 'rules-2026.11.2'{vals}) RETURNING id")


def test_b1_012_direct_insert_as_approved_is_refused(world: World, as_user: Any) -> None:
    m = processed_meeting(as_user(world.priya), world.zzs9001)
    p = {"b": world.harbourline, "s": world.zzs9001, "m": m["id"]}
    for extra, vals in ((", status", ", 'approved'"), (", status, content_hash", ", 'approved', '\\x00'"),
                        (", status", ", 'superseded'"), (", content_hash", ", '\\x00'")):
        with pytest.raises(DBAPIError), session_for(_actor(world)) as s:
            s.execute(text(INSERT.format(extra=extra, vals=vals)), p)


def test_b1_012_insert_draft_then_update_to_approved_is_refused(world: World, as_user: Any) -> None:
    m = new_meeting(as_user(world.priya), world.zzs9001)  # no draft yet: one draft per meeting
    p = {"b": world.harbourline, "s": world.zzs9001, "m": m["id"]}
    with session_for(_actor(world)) as s:  # a draft may be inserted
        vid = s.execute(text(INSERT.format(extra="", vals="")), p).scalar()
    with pytest.raises(DBAPIError, match="permission denied"), session_for(_actor(world)) as s:
        s.execute(text("UPDATE minutes_versions SET status = 'approved' WHERE id = :v"), {"v": vid})
    # Through the approval function but with no approval row and no reviewed quorum: refused at commit.
    with pytest.raises(DBAPIError, match="reviewed quorum item"), session_for(_actor(world)) as s:
        s.execute(text("SELECT app_approve_version(:v, '\\x01')"), {"v": vid})
    # Another building's version cannot be approved through the function either.
    v2 = _version(world, m["id"])[0]
    with pytest.raises(DBAPIError, match="not found"), session_for(
            Actor.user(world.omar, world.tidewater, "strata_manager")) as s:
        s.execute(text("SELECT app_approve_version(:v, '\\x01')"), {"v": v2})


def test_b1_012_approval_row_without_quorum_is_refused(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    vid = _version(world, m["id"])[0]
    row = ("INSERT INTO approvals (id, brokerage_id, strata_id, minutes_version_id, approved_by, content_hash, "
           "attestation_text_version) VALUES (gen_random_uuid(), :b, :s, :v, :u, '\\x01', 'attest-2026.11.1')")
    p = {"b": world.harbourline, "s": world.zzs9001, "v": vid, "u": world.priya}
    with pytest.raises(DBAPIError, match="needs its minutes version approved"), session_for(_actor(world)) as s:
        s.execute(text(row), p)  # approval row for a draft
    with pytest.raises(DBAPIError, match="reviewed quorum item"), session_for(_actor(world)) as s:
        s.execute(text("SELECT app_approve_version(:v, '\\x01')"), {"v": vid})
        s.execute(text(row), p)  # approval row plus status, but the quorum item is unreviewed


def test_b1_012_normal_approval_and_reopen_still_work(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    link_confirmed_clause(priya, world, m["id"])
    review_all(priya, m["id"])
    assert priya.post(f"/meetings/{m['id']}/approve", ATTEST).status_code == 200
    assert priya.post(f"/meetings/{m['id']}/reopen", {"reason": "typo"}).status_code == 200
    assert priya.post(f"/meetings/{m['id']}/approve", ATTEST).status_code == 200
    with session_for(_actor(world)) as s:
        rows = s.execute(text("SELECT version, status, content_hash IS NOT NULL FROM minutes_versions "
                              "WHERE meeting_id = :m ORDER BY version"), {"m": m["id"]}).all()
    assert [tuple(r) for r in rows] == [(1, "superseded", True), (2, "approved", True)]
    assert os.environ["STRATASCRIBE_ENV"] == "test"
