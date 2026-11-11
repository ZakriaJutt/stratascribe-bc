"""Security fixes after the B2 review round 1 (B2-S01 read audit for every range, B2-S02 constant-time
sign-in request)."""

from __future__ import annotations

from typing import Any

import pytest
from sqlalchemy import create_engine, select, text

from core import auth, config
from core.db import Actor, session_for
from core.devdata import World
from core.models import AudioAsset
from tests.helpers import processed_meeting

pytestmark = pytest.mark.db


def streamed(asset_id: Any) -> list[dict[str, Any]]:
    eng = create_engine(config.settings().migration_database_url)
    with eng.connect() as c:
        rows = c.execute(text("SELECT details FROM audit_events WHERE action = 'audio.streamed' AND target_id = :a "
                              "ORDER BY occurred_at"), {"a": asset_id}).all()
    eng.dispose()
    return [dict(r[0]) for r in rows]


def test_b2_s01_every_authorised_audio_read_is_audited_whatever_the_range(world: World, as_user: Any) -> None:
    daniel = as_user(world.daniel)
    processed_meeting(daniel, world.zzs9002)
    with session_for(Actor.user(world.daniel, world.harbourline, "strata_manager")) as s:
        a = s.scalar(select(AudioAsset).where(AudioAsset.strata_id == world.zzs9002))
        assert a is not None
        asset, size = a.id, a.byte_size
    r = daniel.get(f"/audio-assets/{asset}/stream", headers={"Range": "bytes=1-"})
    assert r.status_code == 206 and len(r.content) == size - 1
    assert streamed(asset) == [{"range_start": 1, "range_end": size - 1}]  # the bytes=1- read is recorded
    r = daniel.get(f"/audio-assets/{asset}/stream", headers={"Range": "bytes=5-9"})  # mid-file range
    assert r.status_code == 206 and len(r.content) == 5
    r = daniel.get(f"/audio-assets/{asset}/stream", headers={"Range": "bytes=-4"})  # suffix range
    assert r.status_code == 206 and len(r.content) == 4
    assert daniel.get(f"/audio-assets/{asset}/stream").status_code == 200
    assert streamed(asset) == [{"range_start": 1, "range_end": size - 1}, {"range_start": 5, "range_end": 9},
                               {"range_start": size - 4, "range_end": size - 1},
                               {"range_start": 0, "range_end": size - 1}]
    # A refused read writes no read event (it writes access.denied instead).
    assert as_user(world.priya).get(f"/audio-assets/{asset}/stream", headers={"Range": "bytes=1-"}).status_code == 403
    assert len(streamed(asset)) == 4


def test_b2_s02_sign_in_request_does_no_address_dependent_work_before_answering(
        world: World, monkeypatch: pytest.MonkeyPatch) -> None:
    def no_db(*_: Any, **__: Any) -> Any:
        raise AssertionError("database touched before the response")

    monkeypatch.setattr(auth, "session_for", no_db)
    # Known, unknown and deactivated addresses: only validation and rate limits run synchronously.
    for email in ("priya@harbourline.example", "nobody-b2s02@harbourline.example", "omar@tidewater.example"):
        assert auth.request_link(email, "198.51.100.7") == email
    # The deferred part never raises, even when it fails, so the response cannot depend on it.
    assert auth.issue_link("priya@harbourline.example", "n" * 43) is False
