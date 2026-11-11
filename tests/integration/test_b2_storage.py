"""B2 object storage through the S3 API against local MinIO (R-13, AD-11; I-9, P-1, P-2, P-5 on S3).

Each test writes under its own namespace (``tests/<random>/``) in the ``S3_BUCKET`` bucket and deletes
every object under it afterwards. Audio is synthetic (a RIFF header and random bytes); no real
recording is used. Skipped, with the reason, when the MinIO credentials are not in ``tools/.env``.
"""

from __future__ import annotations

import os
import uuid
from collections.abc import Iterator
from datetime import timedelta
from typing import Any

import pytest
from sqlalchemy import select

from core import clock, retention, storage
from core.db import Actor, session_for
from core.devdata import World
from core.models import AudioAsset
from tests.helpers import Api, authorize, drain_worker, fake_wav, new_meeting, sha

pytestmark = [
    pytest.mark.db,
    pytest.mark.skipif(not os.environ.get("S3_ACCESS_KEY_ID"), reason="MinIO credentials not in tools/.env"),
]


def make_store(namespace: str) -> storage.S3ObjectStore:
    return storage.S3ObjectStore(os.environ["S3_ENDPOINT_URL"], os.environ.get("S3_REGION", "us-east-1"),
                                 os.environ["S3_BUCKET"], os.environ["S3_ACCESS_KEY_ID"],
                                 os.environ["S3_SECRET_ACCESS_KEY"], namespace=namespace)


def raw_names(st: storage.S3ObjectStore) -> list[str]:
    return sorted(str(o["Key"]) for o in st._list(st.namespace))


def purge(st: storage.S3ObjectStore) -> None:
    for name in raw_names(st):
        st.s3.delete_object(Bucket=st.bucket, Key=name)


@pytest.fixture
def s3(world: World) -> Iterator[storage.S3ObjectStore]:
    st = make_store(f"tests/{uuid.uuid4().hex}/")
    storage.set_store(st)
    yield st
    storage.set_store(None)
    purge(st)
    assert raw_names(st) == []  # cleanup of test objects


def upload_in_parts(api: Api, meeting_id: str, data: bytes, parts: int) -> dict[str, Any]:
    r = api.post(f"/meetings/{meeting_id}/uploads", {"sha256": sha(data), "byte_size": len(data), "extension": "wav"})
    assert r.status_code == 201, r.text
    a = r.json()
    step = -(-len(data) // parts)
    for off in range(0, len(data), step):
        r = api.patch(f"/uploads/{a['id']}", content=data[off:off + step], params={"offset": off},
                      headers={"content-type": "application/octet-stream"})
        assert r.status_code == 200, r.text
    r = api.post(f"/uploads/{a['id']}/complete")
    assert r.status_code == 200, r.text
    return dict(r.json())


def test_b2_s3_upload_and_stream_for_one_tenant_refused_for_others(world: World, as_user: Any,
                                                                  s3: storage.S3ObjectStore) -> None:
    daniel = as_user(world.daniel)
    m = new_meeting(daniel, world.zzs9002)
    assert authorize(daniel, m["id"]).status_code == 200
    data = fake_wav(os.urandom(6 * 1024 * 1024))  # above the 5 MB multipart minimum: composed from parts
    asset = upload_in_parts(daniel, m["id"], data, parts=3)
    names = raw_names(s3)
    prefix = f"{s3.namespace}b/{world.harbourline}/s/{world.zzs9002}/audio/"
    assert names == [prefix + asset["id"]], names  # one object, building-scoped key, no chunks left
    assert all("wav" not in n for n in names)  # no file name or extension in the key
    whole = daniel.get(f"/audio-assets/{asset['id']}/stream")
    assert whole.status_code == 200 and whole.content == data
    assert whole.headers["cache-control"] == "no-store"
    part = daniel.get(f"/audio-assets/{asset['id']}/stream", headers={"Range": "bytes=100-199"})
    assert part.status_code == 206 and part.content == data[100:200]
    # Same brokerage, unassigned building: 403. Other brokerage: 404. No bytes either way.
    priya = as_user(world.priya)
    r = priya.get(f"/audio-assets/{asset['id']}/stream")
    assert r.status_code == 403 and b"RIFF" not in r.content
    omar = as_user(world.omar)
    r = omar.get(f"/audio-assets/{asset['id']}/stream")
    assert r.status_code == 404 and b"RIFF" not in r.content
    # The worker reads it through its building-scoped view and transcribes.
    assert daniel.post(f"/meetings/{m['id']}/process").status_code == 202
    drain_worker()
    assert daniel.get(f"/meetings/{m['id']}/status").json()["state"] == "ready_for_review"


def test_b2_s3_worker_scope_and_key_rules(world: World, s3: storage.S3ObjectStore) -> None:
    k9002 = storage.key(world.harbourline, world.zzs9002, "audio", uuid.uuid4())
    s3.put(k9002, b"synthetic")
    scoped = storage.ScopedStore(s3, world.harbourline, world.zzs9001)
    with pytest.raises(storage.StorageScopeError):
        scoped.read(k9002)
    with pytest.raises(storage.StorageScopeError):
        scoped.list_prefix(storage.building_prefix(world.harbourline, world.zzs9002))
    for bad in ("../../etc/passwd", "b/x/s/y/audio/z", k9002 + "/.chunks/0000000000000000"):
        with pytest.raises(storage.InvalidKey):
            s3.read(bad)
    assert storage.ScopedStore(s3, world.harbourline, world.zzs9002).read(k9002) == b"synthetic"


def test_b2_s3_resumable_chunks_ranges_and_delete(world: World, s3: storage.S3ObjectStore) -> None:
    tmp = storage.key(world.harbourline, world.zzs9001, "tmp", uuid.uuid4())
    final = storage.key(world.harbourline, world.zzs9001, "audio", uuid.uuid4())
    data = os.urandom(300_000)
    assert s3.size(tmp) is None
    assert s3.write_at(tmp, 0, data[:100_000]) == 100_000
    with pytest.raises(ValueError):
        s3.write_at(tmp, 50, data[50:60])  # a resumed client must send from the stored offset
    assert s3.write_at(tmp, 100_000, data[100_000:]) == 300_000
    assert s3.size(tmp) == 300_000
    assert s3.read(tmp, 99_990, 100_009) == data[99_990:100_010]  # across the chunk boundary
    assert s3.list_prefix(storage.building_prefix(world.harbourline, world.zzs9001)) == [tmp]
    s3.move(tmp, final)
    assert s3.size(tmp) is None and s3.read(final) == data
    assert s3.read(final, 299_990) == data[299_990:]
    assert s3.delete(final) is True and s3.delete(final) is False
    assert raw_names(s3) == []


def test_b2_s3_retention_sweep_deletes_expired_audio(world: World, as_user: Any, s3: storage.S3ObjectStore) -> None:
    priya = as_user(world.priya)
    m = new_meeting(priya, world.zzs9001)
    assert authorize(priya, m["id"]).status_code == 200
    asset = upload_in_parts(priya, m["id"], fake_wav(os.urandom(1000)), parts=2)
    with session_for(Actor.user(world.priya, world.harbourline, "strata_manager")) as s:
        a = s.scalar(select(AudioAsset).where(AudioAsset.id == uuid.UUID(asset["id"])))
        assert a is not None and a.delete_after is not None
        due = a.delete_after
    clock.set_clock(lambda: due + timedelta(minutes=1))
    retention.sweep()
    retention.sweep()  # safe to run twice
    assert raw_names(s3) == []
    assert priya.get("/me").status_code == 401  # 60 days later the old session has expired too
    assert as_user(world.priya).get(f"/audio-assets/{asset['id']}/stream").status_code == 404


def test_b2_s3_bylaw_original_stored_under_building_key(world: World, as_user: Any,
                                                       s3: storage.S3ObjectStore) -> None:
    from tests.helpers import bylaw_text

    priya = as_user(world.priya)
    d = priya.post(f"/buildings/{world.zzs9001}/bylaw-documents",
                   {"kind": "bylaws", "text": bylaw_text("bylaws_zzs9001.txt"), "filed_on": "2025-03-01"}).json()
    assert raw_names(s3) == [f"{s3.namespace}b/{world.harbourline}/s/{world.zzs9001}/bylaw/{d['id']}"]
