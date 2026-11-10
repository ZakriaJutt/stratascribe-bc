"""Default deny, roles, policies, append-only and immutability at the database (I-11, I-6, T-2.2.1, T-2.2.4)."""

from __future__ import annotations

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from core import config
from core.db import Actor, session_for
from core.devdata import World
from core.models import Base
from tests.helpers import Api, processed_meeting

pytestmark = pytest.mark.db

TENANT_TABLES = sorted(t.name for t in Base.metadata.sorted_tables if t.name != "worker_heartbeats")


def test_i11_no_session_variables_reads_zero_rows(world: World, as_user: object) -> None:
    api: Api = as_user(world.marta)  # type: ignore[operator]
    processed_meeting(api, world.zzs9001)  # put rows in most tables first
    eng = create_engine(config.settings().database_url)
    with eng.connect() as c:
        assert c.execute(text("SELECT current_user")).scalar() == "stratascribe_app"
        counts = {t: c.execute(text(f"SELECT count(*) FROM {t}")).scalar() for t in TENANT_TABLES  # noqa: S608
                  if t != "statute_sections"}
    eng.dispose()
    assert counts and all(v == 0 for v in counts.values()), counts
    owner = create_engine(config.settings().migration_database_url)
    with owner.connect() as c:
        assert c.execute(text("SELECT count(*) FROM meetings")).scalar() == 1
        assert c.execute(text("SELECT count(*) FROM transcript_segments")).scalar() > 0
    owner.dispose()


def test_application_role_cannot_bypass_rls(world: World) -> None:
    owner = create_engine(config.settings().migration_database_url)
    with owner.connect() as c:
        row = c.execute(text("SELECT rolsuper, rolbypassrls FROM pg_roles WHERE rolname = 'stratascribe_app'")).one()
        assert tuple(row) == (False, False)
        flags = dict(c.execute(text(
            "SELECT relname, relrowsecurity AND relforcerowsecurity FROM pg_class "
            "WHERE relnamespace = 'public'::regnamespace AND relkind = 'r'")).all())
        owned = c.execute(text("SELECT count(*) FROM pg_tables WHERE schemaname='public' "
                               "AND tableowner = 'stratascribe_app'")).scalar()
    owner.dispose()
    for t in TENANT_TABLES:
        assert flags[t] is True, f"{t} must have RLS enabled and forced"
    assert owned == 0


EXPECTED_POLICIES = {
    "meetings": {"building", "operator_grant"},
    "transcript_segments": {"building", "operator_grant"},
    "minute_items": {"building", "operator_grant"},
    "audio_assets": {"building", "system_retention", "system_retention_update"},
    "jobs": {"building", "system_jobs"},
    "audit_events": {"append", "broker_read"},
    "building_assignments": {"own_or_broker", "broker_insert", "broker_update"},
    "bylaw_clauses": {"building"},
    "qa_interactions": {"building"},
    "review_sessions": {"own_rows"},
    "statute_sections": {"global_read"},
}


def test_policy_listing(world: World) -> None:
    owner = create_engine(config.settings().migration_database_url)
    with owner.connect() as c:
        rows = c.execute(text("SELECT tablename, policyname FROM pg_policies WHERE schemaname='public'")).all()
    owner.dispose()
    got: dict[str, set[str]] = {}
    for t, p in rows:
        got.setdefault(t, set()).add(p)
    for t, expected in EXPECTED_POLICIES.items():
        assert got.get(t) == expected, (t, got.get(t))
    for t in TENANT_TABLES:
        assert got.get(t), f"{t} has no policy"


def test_wrong_session_variables_see_nothing(world: World, as_user: object) -> None:
    api: Api = as_user(world.marta)  # type: ignore[operator]
    processed_meeting(api, world.zzs9001)
    omar = Actor.user(world.omar, world.tidewater, "strata_manager")
    with session_for(omar) as s:
        assert s.execute(text("SELECT count(*) FROM meetings")).scalar() == 0
        assert s.execute(text("SELECT count(*) FROM transcript_segments")).scalar() == 0
    # Right brokerage, unassigned building: Priya sees ZZS 9001 rows only.
    daniel_api: Api = as_user(world.daniel)  # type: ignore[operator]
    processed_meeting(daniel_api, world.zzs9002)
    priya = Actor.user(world.priya, world.harbourline, "strata_manager")
    with session_for(priya) as s:
        strata = {r[0] for r in s.execute(text("SELECT DISTINCT strata_id FROM meetings"))}
        assert strata == {world.zzs9001}


def test_t224_audit_events_are_append_only(world: World, as_user: object) -> None:
    api: Api = as_user(world.marta)  # type: ignore[operator]
    processed_meeting(api, world.zzs9001)
    marta = Actor.user(world.marta, world.harbourline, "managing_broker")
    for stmt in ("UPDATE audit_events SET action = 'x'", "DELETE FROM audit_events"):
        with pytest.raises(DBAPIError), session_for(marta) as s:
            s.execute(text(stmt))


def test_recording_authorization_cannot_be_edited(world: World, as_user: object) -> None:
    api: Api = as_user(world.marta)  # type: ignore[operator]
    processed_meeting(api, world.zzs9001)
    marta = Actor.user(world.marta, world.harbourline, "managing_broker")
    with pytest.raises(DBAPIError), session_for(marta) as s:
        s.execute(text("UPDATE recording_authorizations SET basis = 'express_consent_all'"))
    with pytest.raises(DBAPIError), session_for(marta) as s:
        s.execute(text("DELETE FROM recording_authorizations"))
