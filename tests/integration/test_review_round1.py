"""Regression tests for review round 1 findings B1-001 to B1-011 (each reviewer case made permanent)."""

from __future__ import annotations

import threading
import uuid
from typing import Any

import pytest
from sqlalchemy import create_engine, select, text
from sqlalchemy.exc import DBAPIError

from ai.answer import answer
from ai.search import ClauseHit
from core import config, retention
from core.db import Actor, session_for
from core.devdata import World
from core.models import AudioAsset
from tests.helpers import Api, authorize, bylaw_text, drain_worker, fake_wav, new_meeting, processed_meeting, upload
from tests.integration.test_pipeline import ATTEST, link_confirmed_clause, motions, patch

pytestmark = pytest.mark.db


def owner_sql(sql: str, **p: Any) -> list[Any]:
    eng = create_engine(config.settings().migration_database_url)
    with eng.begin() as c:
        res = c.execute(text(sql), p)
        rows = list(res.all()) if res.returns_rows else []
    eng.dispose()
    return rows


def confirmed_doc(api: Api, strata: Any, fixture: str, filed: str) -> dict[str, Any]:
    d = api.post(f"/buildings/{strata}/bylaw-documents", {"kind": "bylaws", "text": bylaw_text(fixture),
                                                         "filed_on": filed}).json()
    assert api.post(f"/bylaw-documents/{d['id']}/confirm").status_code == 200
    return dict(d)


# ---------------------------------------------------------------- B1-001 idempotency replay


def test_b1_001_replay_after_unassignment_is_refused(world: World, as_user: Any) -> None:
    daniel, marta = as_user(world.daniel), as_user(world.marta)
    confirmed_doc(daniel, world.zzs9002, "bylaws_zzs9002.txt", "2024-06-01")
    body, key = {"question": "How many dogs may an owner keep?"}, {"Idempotency-Key": "k-dogs-1"}
    first = daniel.post(f"/buildings/{world.zzs9002}/questions", body, headers=key)
    assert first.status_code == 200 and first.json()["outcome"] == "answered"
    again = daniel.post(f"/buildings/{world.zzs9002}/questions", body, headers=key)
    assert again.json()["id"] == first.json()["id"]  # still assigned: the first result is returned
    m = processed_meeting(daniel, world.zzs9002)
    it = motions(daniel, m["id"])[0]
    assert daniel.patch(f"/minute-items/{it['id']}", {"mover": "Speaker 7"},
                        headers={"If-Match": str(it["row_version"]), "Idempotency-Key": "k-item-1"}).status_code == 200
    rows = owner_sql("SELECT brokerage_id, strata_id, expires_at > now() + interval '23 hours' FROM idempotency_keys")
    assert rows and all(r[0] == world.harbourline and r[1] == world.zzs9002 and r[2] for r in rows)
    assert marta.delete(f"/buildings/{world.zzs9002}/assignments/{world.daniel}").status_code == 200
    replay = daniel.post(f"/buildings/{world.zzs9002}/questions", body, headers=key)
    replay2 = daniel.patch(f"/minute-items/{it['id']}", {"mover": "Speaker 7"},
                           headers={"If-Match": "999", "Idempotency-Key": "k-item-1"})
    assert replay.status_code == 403 and "dogs" not in replay.text
    assert replay2.status_code == 403 and "Speaker" not in replay2.text


def test_b1_001_expired_responses_are_purged(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    body = {"meeting_type": "agm", "held_on": "2026-09-01", "format": "hybrid", "source_type": "recording"}
    assert priya.post(f"/buildings/{world.zzs9001}/meetings", body, headers={"Idempotency-Key": "x"}).status_code \
        == 201
    owner_sql("UPDATE idempotency_keys SET expires_at = now() - interval '1 minute'")
    assert retention.sweep()["idempotency_purged"] == 1
    assert owner_sql("SELECT count(*) FROM idempotency_keys")[0][0] == 0


def test_b1_011_concurrent_same_key_creates_one_meeting(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    body = {"meeting_type": "agm", "held_on": "2026-09-02", "format": "hybrid", "source_type": "recording"}
    codes: list[int] = []
    barrier = threading.Barrier(2)

    def go() -> None:
        barrier.wait()
        codes.append(priya.post(f"/buildings/{world.zzs9001}/meetings", body,
                                headers={"Idempotency-Key": "same"}).status_code)

    ts = [threading.Thread(target=go) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert owner_sql("SELECT count(*) FROM meetings")[0][0] == 1
    assert len(codes) == 2 and 500 not in codes and 201 in codes, codes
    assert set(codes) <= {201, 409}, codes


# ---------------------------------------------------------------- B1-002 job key scope


def test_b1_002_same_audio_in_two_brokerages(world: World, as_user: Any) -> None:
    omar, priya = as_user(world.omar), as_user(world.priya)
    data = fake_wav(b"identical-bytes-in-two-tenants")
    mo = new_meeting(omar, world.zzs9101)
    authorize(omar, mo["id"])
    upload(omar, mo["id"], data)
    assert omar.post(f"/meetings/{mo['id']}/process").status_code == 202
    mp = new_meeting(priya, world.zzs9001)
    authorize(priya, mp["id"])
    upload(priya, mp["id"], data)
    r = priya.post(f"/meetings/{mp['id']}/process")
    assert r.status_code == 202
    drain_worker()
    assert priya.get(f"/meetings/{mp['id']}/status").json()["state"] == "ready_for_review"
    assert omar.get(f"/meetings/{mo['id']}/status").json()["state"] == "ready_for_review"


def test_b1_002_same_audio_in_two_meetings_of_one_building(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    data = fake_wav(b"same-file-two-meetings")
    ids = []
    for day in ("2026-10-01", "2026-10-02"):
        m = new_meeting(priya, world.zzs9001, held_on=day)
        authorize(priya, m["id"])
        upload(priya, m["id"], data)
        r = priya.post(f"/meetings/{m['id']}/process")
        assert r.status_code == 202
        ids.append((m["id"], r.json()["job_id"]))
    drain_worker()
    assert ids[0][1] != ids[1][1]
    assert [priya.get(f"/meetings/{mid}/status").json()["state"] for mid, _ in ids] == ["ready_for_review"] * 2


# ---------------------------------------------------------------- B1-003 NULL-safe CHECK


def test_b1_003_db_refuses_reviewed_declared_carried_counted_defeated(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    it = patch(priya, motions(priya, m["id"])[0], outcome_method="counted", threshold="three_quarter",
               votes_for=8, votes_against=3, declared_outcome="carried", reviewed=True).json()
    assert it["review_status"] == "blocked"
    actor = Actor.user(world.priya, world.harbourline, "strata_manager")
    with pytest.raises(DBAPIError, match="reviewed_motion_complete"), session_for(actor) as s:
        s.execute(text("UPDATE minute_items SET review_status='reviewed', blocked_reason=NULL WHERE id=:i"),
                  {"i": it["id"]})
    # With the note-backed resolution the same row is storable as reviewed.
    with session_for(actor) as s:
        s.execute(text("UPDATE minute_items SET review_status='reviewed', blocked_reason=NULL, "
                       "discrepancy_resolution='recorded_as_declared', discrepancy_note='as declared' "
                       "WHERE id=:i"), {"i": it["id"]})


# ---------------------------------------------------------------- B1-004 meaningful quotes


def _hit(body: str) -> ClauseHit:
    return ClauseHit(uuid.uuid4(), uuid.uuid4(), "3(4)", body, None, None, 1.0)


class QuoteLlm:
    model_id = "fake-quote"

    def __init__(self, quote: str) -> None:
        self.quote = quote

    def complete_json(self, task: str, payload: dict[str, Any]) -> str:
        import json

        cid = payload["clauses"][0]["id"]
        return json.dumps({"answer": "Owners may keep up to five dogs.",
                           "citations": [{"clause_id": cid, "quote": self.quote}]})


@pytest.mark.parametrize("quote", ["a", "two dogs", "o more than two dogs", "than two dogs.", " no more than two dogs"])
def test_b1_004_trivial_or_partial_word_quotes_are_refused(quote: str) -> None:
    res = answer("How many dogs?", [_hit("An owner may keep no more than two dogs.")], QuoteLlm(quote))
    assert res.outcome == "refused", quote


def test_b1_004_meaningful_quote_is_accepted_and_db_agrees(world: World, as_user: Any) -> None:
    res = answer("How many dogs?", [_hit("An owner may keep no more than two dogs.")],
                 QuoteLlm("may keep no more than two dogs"))
    assert res.outcome == "answered"
    priya = as_user(world.priya)
    d = confirmed_doc(priya, world.zzs9001, "bylaws_zzs9001.txt", "2025-03-01")
    clause = next(c for c in d["clauses"] if c["clause_number"] == "2(1)")
    actor = Actor.user(world.priya, world.harbourline, "strata_manager")
    with pytest.raises(DBAPIError, match="meaningful verbatim"), session_for(actor) as s:
        qid = s.execute(text(
            "INSERT INTO qa_interactions (id, brokerage_id, strata_id, asked_by, question_text, outcome,"
            " llm_model_id, prompt_version, retrieval_params_hash) VALUES (gen_random_uuid(), :b, :s, :u, 'q',"
            " 'refused', 'm', 'p', 'h') RETURNING id"), {"b": world.harbourline, "s": world.zzs9001,
                                                       "u": world.priya}).scalar()
        s.execute(text("INSERT INTO qa_citations (id, brokerage_id, strata_id, qa_interaction_id, bylaw_clause_id,"
                       " quoted_text, validated) VALUES (gen_random_uuid(), :b, :s, :q, :c, 'a', true)"),
                  {"b": world.harbourline, "s": world.zzs9001, "q": qid, "c": clause["id"]})


# ---------------------------------------------------------------- B1-005 show of cards


def test_b1_005_declared_motion_stores_no_counts(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    it = patch(priya, motions(priya, m["id"])[0], outcome_method="counted", threshold="three_quarter",
               votes_for=5, votes_against=2).json()
    out = patch(priya, it, outcome_method="declared", declared_outcome="carried", reviewed=True).json()
    assert out["votes_for"] is None and out["threshold"] is None and out["review_status"] == "reviewed"
    cleared = owner_sql("SELECT field FROM corrections WHERE minute_item_id = :i AND new_value IS NULL",
                        i=out["id"])
    assert {r[0] for r in cleared} >= {"threshold", "votes_for", "votes_against"}
    r2 = patch(priya, motions(priya, m["id"])[1], outcome_method="declared", declared_outcome="carried",
               votes_for=12, threshold="unanimous", reviewed=True)
    assert r2.status_code == 422 and r2.json()["error"]["code"] == "counts_on_declared"
    actor = Actor.user(world.priya, world.harbourline, "strata_manager")
    with pytest.raises(DBAPIError, match="declared_no_counts"), session_for(actor) as s:
        s.execute(text("UPDATE minute_items SET votes_for = 12 WHERE id = :i"), {"i": out["id"]})


# ---------------------------------------------------------------- B1-006 quorum


def _quorum_item(api: Api, meeting_id: str) -> dict[str, Any]:
    r = api.post(f"/meetings/{meeting_id}/minute-items",
                 {"item_type": "quorum", "body_text": "Quorum was established.", "position": 1})
    assert r.status_code == 201
    return dict(r.json())


def _review_motions(api: Api, meeting_id: str) -> None:
    for it in motions(api, meeting_id):
        assert patch(api, it, outcome_method="declared", declared_outcome="carried", reviewed=True).status_code == 200


def test_b1_006_unreviewed_quorum_statement_blocks_approval(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    _quorum_item(priya, m["id"])
    _review_motions(priya, m["id"])
    link_confirmed_clause(priya, world, m["id"])
    r = priya.post(f"/meetings/{m['id']}/approve", ATTEST)
    assert r.status_code == 409 and r.json()["error"]["items"][0]["position"] == 1


def test_b1_006_statement_contradicting_numbers_is_refused(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001, meeting_type="agm")  # Alder Court: 40 lots, 38 owners
    q = _quorum_item(priya, m["id"])
    q = patch(priya, q, quorum_basis="counted", present_count=2, eligible_count=40, quorum_statement="established",
              reviewed=True).json()
    assert q["review_status"] == "blocked" and "not met" in q["blocked_reason"]
    assert q["quorum"]["required_count"] == 14 and q["quorum"]["met"] is False
    assert q["quorum"]["formula"].endswith("6 < 40")
    _review_motions(priya, m["id"])
    link_confirmed_clause(priya, world, m["id"])
    assert priya.post(f"/meetings/{m['id']}/approve", ATTEST).status_code == 409
    actor = Actor.user(world.priya, world.harbourline, "strata_manager")
    with pytest.raises(DBAPIError, match="reviewed_quorum_complete"), session_for(actor) as s:
        s.execute(text("UPDATE minute_items SET review_status='reviewed', blocked_reason=NULL WHERE id=:i"),
                  {"i": q["id"]})
    q = patch(priya, q, present_count=14, reviewed=True).json()
    assert q["review_status"] == "reviewed" and q["quorum"]["met"] is True
    assert priya.post(f"/meetings/{m['id']}/approve", ATTEST).status_code == 200
    stored = owner_sql("SELECT present_count, eligible_count, required_count, quorum_met, rules_version "
                       "FROM minute_items WHERE id = :i", i=q["id"])
    assert stored == [(14, 40, 14, True, "rules-2026.11.2")]


def test_b1_006_council_and_declared_quorum(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)  # council meeting
    q = _quorum_item(priya, m["id"])
    q = patch(priya, q, quorum_basis="counted", present_count=2, eligible_count=5,
              quorum_statement="not_established", reviewed=True).json()
    assert q["review_status"] == "reviewed" and q["quorum"]["required_count"] == 3
    q = patch(priya, q, quorum_basis="declared", present_count=None, eligible_count=None,
              quorum_statement="established", reviewed=True).json()
    assert q["review_status"] == "reviewed" and q["quorum"]["attested_at"] is not None
    bad = patch(priya, motions(priya, m["id"])[0], present_count=3)
    assert bad.status_code == 422


# ---------------------------------------------------------------- B1-007, B1-010, B1-011


def test_b1_007_bad_ranges_and_paging(world: World, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    with session_for(Actor.user(world.priya, world.harbourline, "strata_manager")) as s:
        a = s.scalar(select(AudioAsset))
        assert a is not None
    url = f"/audio-assets/{a.id}/stream"
    assert priya.get(url, headers={"Range": "bytes=abc-"}).status_code == 400
    assert priya.get(url, headers={"Range": "bytes=10-2"}).status_code == 416
    assert priya.get(url, headers={"Range": "bytes=99999-"}).status_code == 416
    tail = priya.get(url, headers={"Range": "bytes=-4"})
    assert tail.status_code == 206 and tail.headers["content-range"] == f"bytes {a.byte_size - 4}-{a.byte_size - 1}/" \
        f"{a.byte_size}" and len(tail.content) == 4
    full = priya.get(url)
    assert full.status_code == 200 and len(full.content) == a.byte_size
    r = priya.get(f"/meetings/{m['id']}/transcript", params={"limit": -1})
    assert r.status_code == 422 and r.json()["error"]["code"] == "invalid_request"


def test_b1_010_mutation_without_origin_or_referer_is_refused(world: World, as_user: Any, client: Any) -> None:
    priya = as_user(world.priya)
    body = {"meeting_type": "agm", "held_on": "2026-09-01", "format": "hybrid", "source_type": "recording"}
    client.cookies.clear()
    no_origin = client.post(f"/api/v1/buildings/{world.zzs9001}/meetings", json=body,
                            headers={"X-StrataScribe-Request": "1"}, cookies={"ss_session": priya.token})
    assert no_origin.status_code == 403
    client.cookies.clear()
    referer = client.post(f"/api/v1/buildings/{world.zzs9001}/meetings", json=body,
                          headers={"X-StrataScribe-Request": "1", "Referer": "http://localhost:3106/meetings"},
                          cookies={"ss_session": priya.token})
    assert referer.status_code == 201


def test_b1_011_unexpected_error_is_json_without_detail(world: World) -> None:
    from fastapi.testclient import TestClient

    from api.app import create_app

    app = create_app()

    @app.get("/boom")
    def boom() -> None:
        raise RuntimeError("transcript says Priya owes money")

    r = TestClient(app, raise_server_exceptions=False).get("/boom")
    assert r.status_code == 500 and r.json()["error"]["code"] == "internal_error"
    assert "Priya" not in r.text


# ---------------------------------------------------------------- B1-008, B1-009


def test_b1_008_system_context_limited_to_retention_columns(world: World, as_user: Any) -> None:
    processed_meeting(as_user(world.priya), world.zzs9001)
    with pytest.raises(DBAPIError, match="system context"), session_for(Actor.system()) as s:
        s.execute(text("UPDATE audio_assets SET storage_key = storage_key || '-x'"))
    with session_for(Actor.system()) as s:
        n = s.execute(text("UPDATE audio_assets SET delete_after = now() RETURNING id")).all()
    assert len(n) == 1


def test_b1_009_foreign_denial_takes_actor_from_session(world: World, as_user: Any) -> None:
    mo = new_meeting(as_user(world.omar), world.zzs9101)
    with pytest.raises(DBAPIError), session_for(Actor.user(world.priya, world.harbourline, "strata_manager")) as s:
        s.execute(text("SELECT app_record_foreign_denial('meeting', :m, :fake, gen_random_uuid())"),
                  {"m": mo["id"], "fake": str(uuid.uuid4())})
    with session_for(Actor.user(world.priya, world.harbourline, "strata_manager")) as s:
        s.execute(text("SELECT app_record_foreign_denial('meeting', :m, gen_random_uuid())"), {"m": mo["id"]})
    rows = owner_sql("SELECT brokerage_id, actor_id FROM audit_events WHERE target_id = :m", m=mo["id"])
    assert rows == [(world.tidewater, world.priya)]
