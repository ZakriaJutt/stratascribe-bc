"""Permission matrix P-1 to P-6 (T-2.2.3, T-5.2.1 a-e) against real PostgreSQL row-level security.

Routes are enumerated from the application, so a new ``/api/v1`` route with an
ID in its path fails this suite until it has a row in ``ROUTE_BODIES``.
"""

from __future__ import annotations

import uuid
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from sqlalchemy import create_engine, select, text

from core import config, storage
from core.db import Actor, session_for
from core.devdata import World
from core.ids import uuid7
from core.models import AudioAsset, AuditEvent, Meeting, SupportGrant, TranscriptSegment
from tests.helpers import Api, authorize, bylaw_text, fake_wav, processed_meeting, review_quorum

pytestmark = pytest.mark.db

# Body sent with each templated route (method, path template) -> json body or bytes
ROUTE_BODIES: dict[tuple[str, str], Any] = {
    ("GET", "/api/v1/buildings/{strata_id}"): None,
    ("PUT", "/api/v1/buildings/{strata_id}/assignments/{user_id}"): {},
    ("DELETE", "/api/v1/buildings/{strata_id}/assignments/{user_id}"): None,
    ("GET", "/api/v1/buildings/{strata_id}/meetings"): None,
    ("POST", "/api/v1/buildings/{strata_id}/meetings"): {"meeting_type": "council", "held_on": "2026-01-05",
                                                         "format": "in_person", "source_type": "recording"},
    ("GET", "/api/v1/meetings/{meeting_id}"): None,
    ("PUT", "/api/v1/meetings/{meeting_id}/recording-authorization"): {
        "basis": "dictated_notes", "notice_text_version": "notice-2026.11.1"},
    ("POST", "/api/v1/meetings/{meeting_id}/uploads"): {"sha256": "ab" * 32, "byte_size": 10, "extension": "wav"},
    ("PATCH", "/api/v1/uploads/{asset_id}"): b"RIFF0000WAVE",
    ("POST", "/api/v1/uploads/{asset_id}/complete"): {},
    ("GET", "/api/v1/audio-assets/{asset_id}/stream"): None,
    ("POST", "/api/v1/meetings/{meeting_id}/process"): {},
    ("GET", "/api/v1/meetings/{meeting_id}/status"): None,
    ("GET", "/api/v1/meetings/{meeting_id}/transcript"): None,
    ("GET", "/api/v1/meetings/{meeting_id}/draft"): None,
    ("POST", "/api/v1/meetings/{meeting_id}/minute-items"): {"item_type": "motion", "body_text": "x"},
    ("PATCH", "/api/v1/minute-items/{item_id}"): {"mover": "x"},
    ("DELETE", "/api/v1/minute-items/{item_id}"): {"reason": "x"},
    ("POST", "/api/v1/minute-items/{item_id}/citations"): {"bylaw_clause_id": "{clause_id}"},
    ("DELETE", "/api/v1/minute-item-citations/{citation_id}"): None,
    ("POST", "/api/v1/meetings/{meeting_id}/activity/heartbeat"): {"activity": "review"},
    ("PUT", "/api/v1/meetings/{meeting_id}/time-report"): {"post_export_edit_minutes": 5},
    ("POST", "/api/v1/meetings/{meeting_id}/approve"): {"attestation_text_version": "attest-2026.11.1"},
    ("POST", "/api/v1/meetings/{meeting_id}/reopen"): {"reason": "x"},
    ("GET", "/api/v1/buildings/{strata_id}/bylaw-documents"): None,
    ("POST", "/api/v1/buildings/{strata_id}/bylaw-documents"): {"kind": "rules", "text": "1 Rule\n(1) Quiet."},
    ("GET", "/api/v1/bylaw-documents/{doc_id}"): None,
    ("POST", "/api/v1/bylaw-documents/{doc_id}/confirm"): {},
    ("POST", "/api/v1/buildings/{strata_id}/questions"): {"question": "How many dogs can I keep?"},
    ("GET", "/api/v1/buildings/{strata_id}/questions"): None,
}


def templated_routes() -> set[tuple[str, str]]:
    from api.app import create_app

    out = set()
    for r in create_app().routes:
        path = getattr(r, "path", "")
        if path.startswith("/api/v1") and "{" in path:
            for m in getattr(r, "methods", set()) - {"HEAD", "OPTIONS"}:
                out.add((m, path))
    return out


# Brokerage-level team routes (B2): no building, so the expected answers differ from P-1 (403 for a
# strata manager, 404 for another brokerage's managing broker). Covered row by row in
# tests/integration/test_b2_auth.py::test_b2_team_routes_broker_only_and_tenant_scoped.
TEAM_ROUTES = {("PATCH", "/api/v1/members/{user_id}"), ("POST", "/api/v1/invitations/{user_id}/resend")}


def test_every_route_with_an_id_has_a_matrix_row() -> None:
    missing = templated_routes() - set(ROUTE_BODIES) - TEAM_ROUTES
    assert not missing, f"add permission rows for: {sorted(missing)}"


def build_targets(world: World, as_user: Any) -> dict[str, str]:
    """Daniel (assigned to ZZS 9002) creates one of everything in ZZS 9002."""
    daniel: Api = as_user(world.daniel)
    d = daniel.post(f"/buildings/{world.zzs9002}/bylaw-documents",
                    {"kind": "bylaws", "text": bylaw_text("bylaws_zzs9002.txt"), "filed_on": "2024-06-01"}).json()
    assert daniel.post(f"/bylaw-documents/{d['id']}/confirm").status_code == 200
    m = processed_meeting(daniel, world.zzs9002)
    draft = daniel.get(f"/meetings/{m['id']}/draft").json()
    item = next(i for i in draft["items"] if i["item_type"] == "motion")
    cite = daniel.post(f"/minute-items/{item['id']}/citations", {"bylaw_clause_id": d["clauses"][0]["id"]}).json()
    with session_for(Actor.user(world.daniel, world.harbourline, "strata_manager")) as s:
        asset = s.scalar(select(AudioAsset).where(AudioAsset.strata_id == world.zzs9002))
        assert asset is not None
        asset_id = str(asset.id)
    stream = daniel.get(f"/audio-assets/{asset_id}/stream")
    assert stream.status_code == 200 and stream.content.startswith(b"RIFF")
    q = daniel.post(f"/buildings/{world.zzs9002}/questions", {"question": "How many dogs may an owner keep?"})
    assert q.status_code == 200
    return {"strata_id": str(world.zzs9002), "meeting_id": m["id"], "asset_id": asset_id, "item_id": item["id"],
            "citation_id": cite["id"], "doc_id": d["id"], "clause_id": d["clauses"][0]["id"],
            "user_id": str(world.priya)}


def call(api: Api, method: str, template: str, ids: dict[str, str]) -> Any:
    path = template.removeprefix("/api/v1")
    for k, v in ids.items():
        path = path.replace("{" + k + "}", v)
    body = ROUTE_BODIES[(method, template)]
    if isinstance(body, bytes):
        return api.send(method, path, content=body, params={"offset": 0},
                        headers={"content-type": "application/octet-stream", "If-Match": "1"})
    if isinstance(body, dict):
        body = {k: (ids["clause_id"] if v == "{clause_id}" else v) for k, v in body.items()}
    if method == "GET":
        return api.get(path)
    return api.send(method, path, json=body, headers={"If-Match": "1"})


def test_p1_unassigned_manager_gets_403_everywhere_including_files(world: World, as_user: Any) -> None:
    ids = build_targets(world, as_user)
    priya: Api = as_user(world.priya)
    leaks = [ids["meeting_id"], ids["asset_id"], ids["item_id"], ids["doc_id"], "Birch", "dogs"]
    results = {}
    for method, template in sorted(ROUTE_BODIES):
        r = call(priya, method, template, ids)
        results[(method, template)] = r.status_code
        assert not any(x in r.text for x in leaks), (method, template, r.text)
    assert set(results.values()) == {403}, {k: v for k, v in results.items() if v != 403}
    denied = owner_rows("SELECT count(*) FROM audit_events WHERE action = 'access.denied' AND actor_id = :a",
                        a=world.priya)
    assert denied == len(ROUTE_BODIES)
    # Building list shows only her assigned building
    names = [b["name"] for b in priya.get("/buildings").json()]
    assert names == ["Alder Court"]


def test_p2_other_brokerage_gets_404_and_owner_sees_the_attempt(world: World, as_user: Any) -> None:
    ids = build_targets(world, as_user)
    omar: Api = as_user(world.omar)
    for method, template in sorted(ROUTE_BODIES):
        r = call(omar, method, template, ids)
        assert r.status_code == 404, (method, template, r.status_code, r.text)
        assert "Birch" not in r.text and ids["meeting_id"] not in r.text
    marta: Api = as_user(world.marta)
    events = [e for e in marta.get("/audit-events").json() if e["action"] == "access.denied"]
    assert len(events) == len(ROUTE_BODIES)
    assert all(e["actor_id"] == str(world.omar) and e["details"] == {"reason": "other_brokerage"} for e in events)
    # Random IDs that exist nowhere are also 404 and log nothing
    assert omar.get(f"/meetings/{uuid.uuid4()}").status_code == 404
    assert omar.get("/meetings/not-a-uuid").status_code == 404


def test_p3_unassigned_while_editing(world: World, as_user: Any) -> None:
    priya: Api = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    item = next(i for i in priya.get(f"/meetings/{m['id']}/draft").json()["items"] if i["item_type"] == "motion")
    marta: Api = as_user(world.marta)
    assert marta.delete(f"/buildings/{world.zzs9001}/assignments/{world.priya}").status_code == 200
    r = priya.patch(f"/minute-items/{item['id']}", {"mover": "x"}, headers={"If-Match": str(item["row_version"])})
    assert r.status_code == 403 and "Speaker" not in r.text
    assert priya.get(f"/meetings/{m['id']}/draft").status_code == 403
    assert priya.get("/buildings").json() == []
    assert any(e["action"] == "assignment.revoked" for e in marta.get("/audit-events").json())


def test_p4_operator_reads_only_granted_meeting_while_grant_is_live(world: World, as_user: Any) -> None:
    priya: Api = as_user(world.priya)
    m1 = processed_meeting(priya, world.zzs9001)
    m2 = processed_meeting(priya, world.zzs9001, held_on="2026-10-20")
    op_id = uuid7()
    eng = create_engine(config.settings().migration_database_url)
    with eng.begin() as c:
        c.execute(text("INSERT INTO operators (id, email, full_name, totp_secret_encrypted) "
                       "VALUES (:i, 'ops@stratascribe.example', 'Support Person', '\\x00')"), {"i": op_id})
    eng.dispose()
    marta = Actor.user(world.marta, world.harbourline, "managing_broker")
    grant_id = uuid7()
    with session_for(marta) as s:
        s.add(SupportGrant(id=grant_id, brokerage_id=world.harbourline, strata_id=world.zzs9001,
                           meeting_id=uuid.UUID(m1["id"]), operator_id=op_id, granted_by=world.marta,
                           reason="Transcript shows wrong speaker", expires_at=datetime.now(UTC) + timedelta(hours=24)))

    def segments(actor: Actor, meeting_id: str) -> int:
        with session_for(actor) as s:
            return len(s.execute(text(
                "SELECT g.id FROM transcript_segments g JOIN transcripts t ON t.id = g.transcript_id "
                "WHERE t.meeting_id = :m"), {"m": meeting_id}).all())

    no_grant = Actor.operator(op_id, world.harbourline, uuid7())
    assert segments(no_grant, m1["id"]) == 0
    with_grant = Actor.operator(op_id, world.harbourline, grant_id)
    assert segments(with_grant, m1["id"]) == 8
    assert segments(with_grant, m2["id"]) == 0
    with session_for(with_grant) as s:  # read-only: an operator cannot write under a grant
        assert s.execute(text("UPDATE transcript_segments SET text = 'x' RETURNING id")).all() == []
        assert s.execute(text("SELECT count(*) FROM bylaw_documents")).scalar() == 0
    other_brokerage = Actor.operator(op_id, world.tidewater, grant_id)
    assert segments(other_brokerage, m1["id"]) == 0
    with session_for(marta) as s:
        s.execute(text("UPDATE support_grants SET expires_at = now() - interval '1 second' WHERE id = :g"),
                  {"g": grant_id})
    assert segments(with_grant, m1["id"]) == 0
    with session_for(Actor.user(world.marta, world.harbourline, "managing_broker")) as s:
        assert s.execute(text("SELECT current_user")).scalar() == "stratascribe_app"


def test_p5_worker_is_scoped_to_its_building(world: World, as_user: Any) -> None:
    processed_meeting(as_user(world.daniel), world.zzs9002)
    worker_9001 = Actor.service(world.harbourline, world.zzs9001)
    with session_for(worker_9001) as s:
        assert s.scalar(select(Meeting)) is None
        assert s.scalar(select(TranscriptSegment)) is None
    with session_for(Actor.service(world.harbourline, world.zzs9002)) as s:
        asset = s.scalar(select(AudioAsset))
        assert asset is not None
        key = asset.storage_key
    scoped = storage.ScopedStore(storage.store(), world.harbourline, world.zzs9001)
    with pytest.raises(storage.StorageScopeError):
        scoped.read(key)
    with pytest.raises(storage.InvalidKey):
        scoped.read("../../etc/passwd")


def test_p6_managing_broker_acts_in_every_building_of_own_brokerage_only(world: World, as_user: Any) -> None:
    marta: Api = as_user(world.marta)
    d = marta.post(f"/buildings/{world.zzs9002}/bylaw-documents",
                   {"kind": "bylaws", "text": bylaw_text("bylaws_zzs9002.txt"), "filed_on": "2024-06-01"}).json()
    marta.post(f"/bylaw-documents/{d['id']}/confirm")
    m = processed_meeting(marta, world.zzs9002)
    assert authorize(marta, m["id"], bylaw_clause_id=d["clauses"][0]["id"]).status_code == 200
    for it in [i for i in marta.get(f"/meetings/{m['id']}/draft").json()["items"] if i["item_type"] == "motion"]:
        r = marta.patch(f"/minute-items/{it['id']}", {"outcome_method": "declared", "declared_outcome": "carried",
                                                       "reviewed": True}, headers={"If-Match": str(it["row_version"])})
        assert r.status_code == 200
    review_quorum(marta, m["id"])
    assert marta.post(f"/meetings/{m['id']}/approve", {"attestation_text_version": "attest-2026.11.1"}).status_code \
        == 200
    actions = {e["action"] for e in marta.get("/audit-events").json() if e["actor_id"] == str(world.marta)}
    assert {"authorization.recorded", "audio.uploaded", "item.corrected", "minutes.approved"} <= actions
    assert {b["name"] for b in marta.get("/buildings").json()} == {"Alder Court", "Birch Gardens"}
    omar: Api = as_user(world.omar)
    t = processed_meeting(omar, world.zzs9101)
    assert marta.get(f"/meetings/{t['id']}").status_code == 404
    assert marta.get(f"/buildings/{world.zzs9101}").status_code == 404


def test_i25_read_events_have_no_content(world: World, as_user: Any) -> None:
    priya: Api = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    priya.get(f"/meetings/{m['id']}")
    priya.get(f"/meetings/{m['id']}/transcript")
    with session_for(Actor.user(world.priya, world.harbourline, "strata_manager")) as s:
        asset = s.scalar(select(AudioAsset))
        assert asset is not None
    priya.get(f"/audio-assets/{asset.id}/stream")
    with session_for(Actor.user(world.marta, world.harbourline, "managing_broker")) as s:
        rows = s.scalars(select(AuditEvent).where(AuditEvent.actor_id == world.priya)).all()
    actions = {r.action for r in rows}
    assert {"meeting.opened", "transcript.read", "audio.streamed"} <= actions
    for r in rows:
        assert r.strata_id == world.zzs9001 and r.target_id is not None
        assert set(r.details) <= {"basis", "count", "part_number", "reason", "outcome", "version",
                                  "range_start", "range_end"}  # byte offsets, no content (B2-S01)
    # export.downloaded: exports are not built in B1


def owner_rows(sql: str, **params: Any) -> int:
    eng = create_engine(config.settings().migration_database_url)
    with eng.connect() as c:
        n = int(c.execute(text(sql), params).scalar() or 0)
    eng.dispose()
    return n


def test_audio_stream_range_requests_are_checked_each_time(world: World, as_user: Any) -> None:
    daniel: Api = as_user(world.daniel)
    m = processed_meeting(daniel, world.zzs9002)
    with session_for(Actor.service(world.harbourline, world.zzs9002)) as s:
        asset = s.scalar(select(AudioAsset).where(AudioAsset.meeting_id == uuid.UUID(m["id"])))
        assert asset is not None
    r = daniel.get(f"/audio-assets/{asset.id}/stream", headers={"Range": "bytes=0-3"})
    assert r.status_code == 206 and r.content == b"RIFF" and r.headers["cache-control"] == "no-store"
    marta: Api = as_user(world.marta)
    marta.delete(f"/buildings/{world.zzs9002}/assignments/{world.daniel}")
    assert daniel.get(f"/audio-assets/{asset.id}/stream", headers={"Range": "bytes=4-7"}).status_code == 403
    assert fake_wav  # imported helper used by processed_meeting
