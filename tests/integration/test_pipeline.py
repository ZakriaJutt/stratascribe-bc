"""Authority gate, upload, jobs, review, approval (I-1..I-6, I-23, C-1..C-3, U-10/U-11 via API, E-2/E-5 core)."""

from __future__ import annotations

import os
import threading
from typing import Any

import pytest
from sqlalchemy import create_engine, func, select, text
from sqlalchemy.exc import DBAPIError

from core import config, jobs, storage
from core.db import Actor, session_for
from core.devdata import World
from core.models import Approval, AudioAsset, Correction, Job, Meeting, MinuteItem
from tests.helpers import Api, authorize, drain_worker, fake_wav, new_meeting, processed_meeting, sha, upload

pytestmark = pytest.mark.db
ATTEST = {"attestation_text_version": "attest-2026.11.1"}


def owner_count(sql: str) -> int:
    eng = create_engine(config.settings().migration_database_url)
    with eng.connect() as c:
        n = int(c.execute(text(sql)).scalar() or 0)
    eng.dispose()
    return n


def motions(api: Api, meeting_id: str) -> list[dict[str, Any]]:
    d = api.get(f"/meetings/{meeting_id}/draft").json()
    return [i for i in d["items"] if i["item_type"] == "motion"]


def patch(api: Api, item: dict[str, Any], **changes: Any) -> Any:
    return api.patch(f"/minute-items/{item['id']}", changes, headers={"If-Match": str(item["row_version"])})


def review_all(api: Api, meeting_id: str) -> None:
    for it in motions(api, meeting_id):
        r = patch(api, it, outcome_method="declared", declared_outcome="carried", reviewed=True)
        assert r.status_code == 200, r.text


def link_confirmed_clause(api: Api, world: World, meeting_id: str) -> None:
    from tests.helpers import bylaw_text

    d = api.post(f"/buildings/{world.zzs9001}/bylaw-documents",
                 {"kind": "bylaws", "text": bylaw_text("bylaws_zzs9001.txt"), "filed_on": "2025-03-01"}).json()
    assert api.post(f"/bylaw-documents/{d['id']}/confirm").status_code == 200
    clause = next(c for c in d["clauses"] if c["clause_number"] == "8(1)")
    r = authorize(api, meeting_id, bylaw_clause_id=clause["id"])
    assert r.status_code == 200, r.text


# ---------------------------------------------------------------- authority gate and upload


def test_i1_upload_refused_without_recording_authority(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    data = fake_wav()
    r = api.post(f"/meetings/{m['id']}/uploads", {"sha256": sha(data), "byte_size": len(data), "extension": "wav"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "no_recording_authority"
    assert owner_count("SELECT count(*) FROM audio_assets") == 0
    assert storage.store().list_prefix("b/") == []


def test_authority_cannot_be_edited_after_upload_only_superseded(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    assert authorize(api, m["id"]).status_code == 200
    # Before upload the basis can be superseded
    assert authorize(api, m["id"], bylaw_reference_text="Bylaw 8(1) as filed").status_code == 200
    upload(api, m["id"], fake_wav())
    r = authorize(api, m["id"], basis="dictated_notes")
    assert r.status_code == 409 and r.json()["error"]["code"] == "authority_locked"
    assert owner_count("SELECT count(*) FROM recording_authorizations") == 2
    assert owner_count("SELECT count(*) FROM recording_authorizations WHERE superseded_by IS NULL") == 1


def test_express_consent_requires_brokerage_setting(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    r = authorize(api, m["id"], basis="express_consent_all")
    assert r.status_code == 422 and r.json()["error"]["code"] == "basis_disabled"
    r = authorize(api, m["id"], basis="bylaw", bylaw_reference_text="")
    assert r.status_code == 422


def test_i2_resume_after_drop_does_not_resend_finished_bytes(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    authorize(api, m["id"])
    data = fake_wav(os.urandom(200_000))
    a = api.post(f"/meetings/{m['id']}/uploads",
                 {"sha256": sha(data), "byte_size": len(data), "extension": "wav"}).json()
    cut = int(len(data) * 0.6)
    assert api.patch(f"/uploads/{a['id']}", content=data[:cut], params={"offset": 0}).status_code == 200
    # "connection dropped": the client asks again and learns the stored offset
    again = api.post(f"/meetings/{m['id']}/uploads",
                     {"sha256": sha(data), "byte_size": len(data), "extension": "wav"}).json()
    assert again["id"] == a["id"] and again["received_bytes"] == cut
    wrong = api.patch(f"/uploads/{a['id']}", content=data[10:], params={"offset": 10})
    assert wrong.status_code == 409 and wrong.json()["error"]["received_bytes"] == cut
    assert api.patch(f"/uploads/{a['id']}", content=data[cut:], params={"offset": cut}).status_code == 200
    done = api.post(f"/uploads/{a['id']}/complete")
    assert done.status_code == 200 and done.json()["upload_state"] == "complete"
    with session_for(Actor.user(world.priya, world.harbourline, "strata_manager")) as s:
        asset = s.get(AudioAsset, __import__("uuid").UUID(a["id"]))
        assert asset is not None
        assert asset.storage_key == f"b/{world.harbourline}/s/{world.zzs9001}/audio/{asset.id}"
        assert storage.store().read(asset.storage_key) == data
        assert asset.delete_after is not None
    assert api.get(f"/meetings/{m['id']}").json()["state"] == "uploaded"


def test_i3_same_file_twice_is_one_asset(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    authorize(api, m["id"])
    data = fake_wav()
    first = upload(api, m["id"], data)
    second = api.post(f"/meetings/{m['id']}/uploads", {"sha256": sha(data), "byte_size": len(data),
                                                       "extension": "wav"})
    assert second.status_code == 200 and second.json()["id"] == first["id"]
    assert owner_count("SELECT count(*) FROM audio_assets") == 1


def test_i24_partial_type_and_checksum_refusals(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    authorize(api, m["id"])
    exe = b"MZ\x90\x00" + os.urandom(64)  # an executable renamed .m4a
    a = api.post(f"/meetings/{m['id']}/uploads", {"sha256": sha(exe), "byte_size": len(exe), "extension": "m4a"}).json()
    r = api.patch(f"/uploads/{a['id']}", content=exe, params={"offset": 0})
    assert r.status_code == 422 and r.json()["error"]["code"] == "type_not_accepted"
    big = api.post(f"/meetings/{m['id']}/uploads",
                   {"sha256": "ab" * 32, "byte_size": 2_600_000_000, "extension": "wav"})
    assert big.status_code == 422 and big.json()["error"]["code"] == "too_large"
    bad = api.post(f"/meetings/{m['id']}/uploads", {"sha256": "ab" * 32, "byte_size": 10, "extension": "exe"})
    assert bad.status_code == 422
    data = fake_wav()
    lie = api.post(f"/meetings/{m['id']}/uploads", {"sha256": "cd" * 32, "byte_size": len(data),
                                                    "extension": "wav"}).json()
    api.patch(f"/uploads/{lie['id']}", content=data, params={"offset": 0})
    r = api.post(f"/uploads/{lie['id']}/complete")
    assert r.status_code == 422 and r.json()["error"]["code"] == "checksum_mismatch"
    keys = storage.store().list_prefix("b/")
    assert not any("/audio/" in k for k in keys)


# ---------------------------------------------------------------- processing and jobs


def test_pipeline_produces_draft_with_suggestions_only(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)
    status = api.get(f"/meetings/{m['id']}/status").json()
    assert status["state"] == "ready_for_review", status
    ms = motions(api, m["id"])
    assert len(ms) == 2
    for it in ms:
        # The model's reading is a suggestion only: no method, outcome, count or computed result is stored.
        assert it["outcome_method"] is None and it["declared_outcome"] is None and it["votes_for"] is None
        assert it["computed_result"] is None and it["final_outcome"] is None
        assert it["suggestion"]["spoken_outcome"] == "carried"
        assert it["source_segment_ids"]
    assert ms[1]["suggestion"]["original"]["spoken_counts"] == {"for": 5, "against": 2}
    tr = api.get(f"/meetings/{m['id']}/transcript").json()["segments"]
    assert len(tr) == 8 and all(sid in {s["id"] for s in tr} for sid in ms[0]["source_segment_ids"])


def test_i5_process_twice_one_job_and_poll_shows_ready(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    authorize(api, m["id"])
    upload(api, m["id"], fake_wav())
    j1 = api.post(f"/meetings/{m['id']}/process").json()["job_id"]
    j2 = api.post(f"/meetings/{m['id']}/process").json()["job_id"]  # caller timed out and retried
    assert j1 == j2
    drain_worker()
    assert api.get(f"/meetings/{m['id']}/status").json()["state"] == "ready_for_review"
    assert owner_count("SELECT count(*) FROM jobs WHERE kind = 'transcribe'") == 1


def test_i4_late_completion_does_not_change_state(world: World, as_user: Any) -> None:
    from worker import handlers

    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    authorize(api, m["id"])
    upload(api, m["id"], fake_wav())
    api.post(f"/meetings/{m['id']}/process")
    first = jobs.lease("worker-a")
    assert first is not None
    drain_worker()  # nothing runnable: the job is leased by worker-a
    # worker-a's lease expires; the reconciler re-queues; worker-b finishes the whole pipeline
    with session_for(Actor.system()) as s:
        s.execute(text("UPDATE jobs SET leased_until = now() - interval '1 minute' WHERE id = :i"), {"i": first.id})
    assert jobs.reconcile() == 1
    drain_worker()
    before = api.get(f"/meetings/{m['id']}/status").json()
    assert before["state"] == "ready_for_review"
    # The stale worker-a now completes: result reused, state untouched
    from ai.transcription import FakeTranscriber

    handlers.transcribe(first, FakeTranscriber())
    after = api.get(f"/meetings/{m['id']}/status").json()
    assert (after["state"], after["state_version"]) == (before["state"], before["state_version"])
    assert owner_count("SELECT count(*) FROM transcripts") == 1
    assert owner_count("SELECT count(*) FROM jobs WHERE kind = 'draft_minutes'") == 1


def test_transition_compare_and_set(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    actor = Actor.user(world.priya, world.harbourline, "strata_manager")
    mid = __import__("uuid").UUID(m["id"])
    with session_for(actor) as s:
        assert jobs.transition(s, mid, 0, "authorized") is True
        assert jobs.transition(s, mid, 0, "authorized") is False  # stale version: no change
        with pytest.raises(jobs.IllegalTransition):
            jobs.transition(s, mid, 1, "approved")


def test_c3_two_workers_never_lease_the_same_job(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    authorize(api, m["id"])
    upload(api, m["id"], fake_wav())
    api.post(f"/meetings/{m['id']}/process")
    got: list[Any] = []
    barrier = threading.Barrier(2)

    def take(name: str) -> None:
        barrier.wait()
        got.append(jobs.lease(name))

    threads = [threading.Thread(target=take, args=(n,)) for n in ("w1", "w2")]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert sum(1 for g in got if g is not None) == 1


def test_transcription_failure_retries_then_failed_state(world: World, as_user: Any) -> None:
    from ai.llm import FakeLlmClient
    from ai.transcription import FakeTranscriber
    from core import clock
    from worker.main import run_one

    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    authorize(api, m["id"])
    upload(api, m["id"], fake_wav())
    api.post(f"/meetings/{m['id']}/process")
    asr = FakeTranscriber(fail_times=99)
    from datetime import UTC, datetime, timedelta

    base = datetime.now(UTC)
    for i in range(4):
        clock.set_clock(lambda i=i: base + timedelta(hours=i + 1))
        assert run_one("w", asr, FakeLlmClient())
    clock.set_clock(None)
    assert api.get(f"/meetings/{m['id']}/status").json()["state"] == "failed_transcription"
    with session_for(Actor.system()) as s:
        job = s.scalar(select(Job).where(Job.kind == "transcribe"))
        assert job is not None and job.status == "failed" and job.error_code == "RuntimeError"
    # Retry from the failed state succeeds
    assert api.post(f"/meetings/{m['id']}/process").status_code == 202
    drain_worker()
    assert api.get(f"/meetings/{m['id']}/status").json()["state"] == "ready_for_review"


def test_invalid_model_output_twice_gives_empty_template(world: World, as_user: Any) -> None:
    from ai.llm import InvalidJsonLlm
    from ai.transcription import FakeTranscriber
    from worker.main import run_one

    api = as_user(world.priya)
    m = new_meeting(api, world.zzs9001)
    authorize(api, m["id"])
    upload(api, m["id"], fake_wav())
    api.post(f"/meetings/{m['id']}/process")
    while run_one("w", FakeTranscriber(), InvalidJsonLlm()):
        pass
    d = api.get(f"/meetings/{m['id']}/draft").json()
    assert d["state"] == "ready_for_review" and d["items"] == []
    added = api.post(f"/meetings/{m['id']}/minute-items", {"item_type": "motion", "body_text": "Typed by hand"})
    assert added.status_code == 201


# ---------------------------------------------------------------- review, corrections, approval


def test_u10_declared_motion_approvable_with_no_counts(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)
    link_confirmed_clause(api, world, m["id"])
    review_all(api, m["id"])
    for it in motions(api, m["id"]):
        assert it["final_outcome"] == "carried" and it["computed_result"] is None and it["votes_for"] is None
    r = api.post(f"/meetings/{m['id']}/approve", ATTEST)
    assert r.status_code == 200, r.text
    assert api.get(f"/meetings/{m['id']}").json()["state"] == "approved"


def test_reviewing_a_motion_without_outcome_is_blocked(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)
    it = motions(api, m["id"])[0]
    r = patch(api, it, reviewed=True)
    assert r.status_code == 200 and r.json()["review_status"] == "blocked"
    it = r.json()
    r = patch(api, it, outcome_method="counted", threshold="majority", votes_for=0, votes_against=0, reviewed=True)
    body = r.json()
    assert body["computed_result"] == "no_result" and body["review_status"] == "blocked"
    assert "switch to declared" in body["blocked_reason"]


def test_u11_e2_three_quarter_fails_by_one_blocks_approval(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)
    link_confirmed_clause(api, world, m["id"])
    review_all(api, m["id"])
    it = motions(api, m["id"])[1]
    r = patch(api, it, outcome_method="counted", threshold="three_quarter", votes_for=8, votes_against=3,
              declared_outcome="carried", reviewed=True)
    it = r.json()
    assert it["computed_result"] == "defeated" and it["review_status"] == "blocked", it
    assert it["computed_formula"].endswith("32 < 33")
    r = api.post(f"/meetings/{m['id']}/approve", ATTEST)
    assert r.status_code == 409 and r.json()["error"]["code"] == "items_not_ready"
    # recorded as declared needs a note
    r = patch(api, it, discrepancy_resolution="recorded_as_declared", reviewed=True)
    assert r.status_code == 422 and r.json()["error"]["code"] == "discrepancy_note_required"
    r = patch(api, it, discrepancy_resolution="recorded_as_declared",
              discrepancy_note="Chair declared carried; count as recorded 8-3.", reviewed=True)
    it = r.json()
    assert it["review_status"] == "reviewed" and it["final_outcome"] == "carried"
    assert it["computed_result"] == "defeated"
    # counts corrected instead: recompute
    r = patch(api, it, discrepancy_resolution="counts_corrected", discrepancy_note=None, votes_for=9, reviewed=True)
    it = r.json()
    assert it["computed_result"] == "carried" and it["review_status"] == "reviewed", it
    assert api.post(f"/meetings/{m['id']}/approve", ATTEST).status_code == 200


def test_u14_tie_casting_vote_and_db_constraint(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)
    it = motions(api, m["id"])[0]
    it = patch(api, it, outcome_method="counted", threshold="majority", votes_for=6, votes_against=6,
               reviewed=True).json()
    assert it["computed_result"] == "tie" and it["review_status"] == "blocked"
    it = patch(api, it, casting_vote="used_for", reviewed=True).json()
    assert it["final_outcome"] == "carried" and it["review_status"] == "reviewed"
    # The database refuses a reviewed counted motion with no result, even bypassing the rules package.
    with pytest.raises(DBAPIError), session_for(Actor.user(world.priya, world.harbourline, "strata_manager")) as s:
        s.execute(text("UPDATE minute_items SET casting_vote = NULL WHERE id = :i"), {"i": it["id"]})


def test_two_lot_strata_tie_is_defeated(world: World, as_user: Any) -> None:
    api = as_user(world.daniel)
    m = processed_meeting(api, world.zzs9002)  # Birch Gardens has 3 lots; set 2 through the owner for the test
    eng = create_engine(config.settings().migration_database_url)
    with eng.begin() as c:
        c.execute(text("UPDATE strata_corporations SET strata_lot_count = 2 WHERE id = :i"), {"i": world.zzs9002})
    eng.dispose()
    it = motions(api, m["id"])[0]
    it = patch(api, it, outcome_method="counted", threshold="majority", votes_for=1, votes_against=1,
               reviewed=True).json()
    assert it["computed_result"] == "defeated" and it["review_status"] == "reviewed"
    r = patch(api, it, casting_vote="used_for")
    assert r.status_code == 422


def test_corrections_one_row_per_change_and_c1_conflict(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)
    it = motions(api, m["id"])[0]
    r = patch(api, it, body_text="the minutes of the September meeting be approved", mover="Speaker 4")
    assert r.status_code == 200
    stale = patch(api, it, body_text="other tab text")  # second tab with the old row_version
    assert stale.status_code == 409 and stale.json()["error"]["current"]["mover"] == "Speaker 4"
    assert patch(api, {"id": it["id"], "row_version": "x"}, mover="y").status_code in (409, 422)
    with session_for(Actor.user(world.priya, world.harbourline, "strata_manager")) as s:
        rows = s.scalars(select(Correction).order_by(Correction.made_at)).all()
        cats = sorted(c.category for c in rows)
        assert cats == ["motion_text", "mover_seconder"]
        assert all(c.made_by == world.priya for c in rows)
    assert api.get(f"/meetings/{m['id']}").json()["state"] == "in_review"
    no_if = api.patch(f"/minute-items/{it['id']}", {"mover": "z"})
    assert no_if.status_code == 422


def test_add_and_delete_items_are_corrections(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)
    new = api.post(f"/meetings/{m['id']}/minute-items", {"item_type": "motion", "body_text": "Missed motion"}).json()
    assert new["origin"] == "manager_added"
    victim = motions(api, m["id"])[0]
    assert api.delete(f"/minute-items/{victim['id']}", {"reason": "invented"}).status_code == 200
    assert owner_count("SELECT count(*) FROM corrections WHERE category IN ('item_added','item_deleted')") == 2
    assert owner_count("SELECT count(*) FROM minute_items WHERE deleted_at IS NOT NULL") == 1


def test_i23_bylaw_basis_needs_confirmed_clause_before_approval(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)  # basis bylaw with a typed reference only
    review_all(api, m["id"])
    r = api.post(f"/meetings/{m['id']}/approve", ATTEST)
    assert r.status_code == 409 and "recording authority not evidenced" in r.json()["error"]["message"]
    link_confirmed_clause(api, world, m["id"])  # supersedes the authority after upload: allowed for a clause link
    assert api.post(f"/meetings/{m['id']}/approve", ATTEST).status_code == 200


def test_i6_c2_approval_immutable_and_idempotent(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)
    link_confirmed_clause(api, world, m["id"])
    review_all(api, m["id"])
    a1 = api.post(f"/meetings/{m['id']}/approve", ATTEST)
    a2 = api.post(f"/meetings/{m['id']}/approve", ATTEST)
    assert a1.status_code == a2.status_code == 200
    assert a1.json()["approval_id"] == a2.json()["approval_id"]
    assert owner_count("SELECT count(*) FROM approvals") == 1
    priya = Actor.user(world.priya, world.harbourline, "strata_manager")
    with pytest.raises(DBAPIError), session_for(priya) as s:
        s.execute(text("UPDATE minute_items SET body_text = 'changed'"))
    with pytest.raises(DBAPIError), session_for(priya) as s:
        s.execute(text("UPDATE minutes_versions SET rules_version = 'x'"))
    it = motions(api, m["id"])[0]
    r = patch(api, it, mover="Speaker 9")
    assert r.status_code == 409 and r.json()["error"]["code"] == "approved"
    # Approval sets audio deletion to approval + 14 days (within the 60-day hard limit)
    with session_for(priya) as s:
        a = s.scalar(select(AudioAsset))
        appr = s.scalar(select(Approval))
        assert a is not None and appr is not None and a.delete_after is not None
        assert abs((a.delete_after - appr.approved_at).total_seconds() - 14 * 86400) < 5


def test_c2_concurrent_approvals_one_row(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)
    link_confirmed_clause(api, world, m["id"])
    review_all(api, m["id"])
    from core import approval

    priya = Actor.user(world.priya, world.harbourline, "strata_manager")
    results: list[Any] = []
    barrier = threading.Barrier(2)

    def go() -> None:
        barrier.wait()
        try:
            with session_for(priya) as s:
                results.append(approval.approve(s, priya, __import__("uuid").UUID(m["id"]), ATTEST).id)
        except Exception as exc:  # noqa: BLE001
            results.append(exc)

    ts = [threading.Thread(target=go) for _ in range(2)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()
    assert owner_count("SELECT count(*) FROM approvals") == 1
    ids = [r for r in results if not isinstance(r, Exception)]
    assert len(set(ids)) == 1


def test_reopen_creates_new_version_and_supersedes_on_approval(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    m = processed_meeting(api, world.zzs9001)
    link_confirmed_clause(api, world, m["id"])
    review_all(api, m["id"])
    api.post(f"/meetings/{m['id']}/approve", ATTEST)
    assert api.post(f"/meetings/{m['id']}/reopen", {"reason": ""}).status_code == 422
    r = api.post(f"/meetings/{m['id']}/reopen", {"reason": "Seconder name misspelled"})
    assert r.status_code == 200 and r.json()["version"] == 2
    it = motions(api, m["id"])[0]
    assert patch(api, it, seconder="Speaker 5").status_code == 200
    assert api.post(f"/meetings/{m['id']}/approve", ATTEST).status_code == 200
    assert owner_count("SELECT count(*) FROM minutes_versions WHERE status = 'superseded'") == 1
    assert owner_count("SELECT count(*) FROM minutes_versions WHERE status = 'approved'") == 1


def test_idempotency_key_returns_first_result(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    body = {"meeting_type": "agm", "held_on": "2026-09-01", "format": "hybrid", "source_type": "recording"}
    h = {"Idempotency-Key": "create-agm-1"}
    r1 = api.post(f"/buildings/{world.zzs9001}/meetings", body, headers=h)
    r2 = api.post(f"/buildings/{world.zzs9001}/meetings", body, headers=h)
    assert r1.status_code == r2.status_code == 201 and r1.json()["id"] == r2.json()["id"]
    r3 = api.post(f"/buildings/{world.zzs9001}/meetings", {**body, "format": "in_person"}, headers=h)
    assert r3.status_code == 422
    with session_for(Actor.user(world.priya, world.harbourline, "strata_manager")) as s:
        assert s.scalar(select(func.count()).select_from(Meeting)) == 1
    dup = api.post(f"/buildings/{world.zzs9001}/meetings", body)
    assert dup.status_code == 409
    second = api.post(f"/buildings/{world.zzs9001}/meetings", {**body, "confirm_second_meeting": True})
    assert second.status_code == 201 and second.json()["sequence"] == 2


def test_i19_forgery_defences(world: World, as_user: Any, client: Any) -> None:
    api = as_user(world.priya)
    body = {"meeting_type": "agm", "held_on": "2026-09-01", "format": "hybrid", "source_type": "recording"}
    client.cookies.clear()
    no_header = client.post(f"/api/v1/buildings/{world.zzs9001}/meetings", json=body,
                            cookies={"ss_session": api.token})
    assert no_header.status_code == 403
    cross = api.post(f"/buildings/{world.zzs9001}/meetings", body, headers={"Origin": "https://evil.example"})
    assert cross.status_code == 403
    form = api.send("POST", f"/buildings/{world.zzs9001}/meetings", content=b"meeting_type=agm",
                    headers={"content-type": "application/x-www-form-urlencoded"})
    assert form.status_code == 422
    assert owner_count("SELECT count(*) FROM meetings") == 0
    anon = client.get("/api/v1/buildings")
    assert anon.status_code == 401


def test_items_rows_scoped(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    processed_meeting(api, world.zzs9001)
    with session_for(Actor.user(world.priya, world.harbourline, "strata_manager")) as s:
        assert s.scalar(select(func.count()).select_from(MinuteItem)) >= 2
