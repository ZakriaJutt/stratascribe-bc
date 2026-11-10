"""Meetings, the recording-authority gate and resumable audio upload (T-3.1.1, T-3.1.2, MH-03, MH-04).

No audio is accepted for a meeting without a current recording authorization
(409 ``no_recording_authority``, test I-1). The authority cannot be edited after
the first upload; it can only be superseded, and after upload only to link the
confirmed bylaw clause for the same basis (I-23).
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date, timedelta
from typing import Any

from sqlalchemy import func, select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core import audit, authz, clock, jobs, storage
from core.db import Actor
from core.errors import Conflict, Invalid, NotFound
from core.ids import uuid7
from core.models import AudioAsset, Brokerage, Meeting, RecordingAuthorization, StrataCorporation
from docs.filetypes import AUDIO_EXTENSIONS, MAX_MEETING_AUDIO_BYTES, MAX_PARTS, sniff_audio

NOTICE_TEXT_VERSIONS = ("notice-2026.11.1",)
UPLOAD_OPEN_STATES = ("authorized", "uploading", "uploaded")


def meeting_out(m: Meeting) -> dict[str, Any]:
    return {
        "id": str(m.id),
        "strata_id": str(m.strata_id),
        "meeting_type": m.meeting_type,
        "held_on": m.held_on.isoformat(),
        "format": m.format,
        "source_type": m.source_type,
        "state": m.state,
        "state_version": m.state_version,
        "sequence": m.sequence,
        "row_version": m.row_version,
    }


def get_meeting(session: Session, actor: Actor, meeting_id: uuid.UUID) -> Meeting:
    authz.locate(session, actor, "meeting", meeting_id)
    m = session.get(Meeting, meeting_id)
    if m is None:  # pragma: no cover - locate found it, RLS hid it: treat as not found
        raise NotFound("Not found.")
    return m


def create_meeting(session: Session, actor: Actor, strata_id: uuid.UUID, body: dict[str, Any]) -> Meeting:
    authz.locate(session, actor, "building", strata_id)
    try:
        held_on = date.fromisoformat(str(body["held_on"]))
        meeting_type, fmt, source = body["meeting_type"], body["format"], body["source_type"]
    except (KeyError, ValueError) as exc:
        raise Invalid("meeting_type, held_on, format and source_type are required.") from exc
    if meeting_type not in ("council", "agm", "sgm") or fmt not in ("in_person", "electronic", "hybrid"):
        raise Invalid("Unknown meeting type or format.")
    if source not in ("recording", "dictated_notes", "not_recorded"):
        raise Invalid("Unknown source type.")
    existing = session.scalar(
        select(func.max(Meeting.sequence)).where(
            Meeting.strata_id == strata_id, Meeting.meeting_type == meeting_type, Meeting.held_on == held_on
        )
    )
    sequence = 1
    if existing is not None:
        if not body.get("confirm_second_meeting") or existing >= 2:
            raise Conflict(
                "A meeting of this type already exists on this date. Confirm to create a second one.",
                code="duplicate_meeting",
            )
        sequence = 2
    m = Meeting(
        id=uuid7(),
        brokerage_id=actor.brokerage_id,
        strata_id=strata_id,
        meeting_type=meeting_type,
        held_on=held_on,
        format=fmt,
        source_type=source,
        created_by=actor.user_id,
        sequence=sequence,
        length_minutes=body.get("length_minutes"),
        reconvened_after_adjournment=bool(body.get("reconvened_after_adjournment", False)),
    )
    session.add(m)
    session.flush()
    if source == "not_recorded":
        jobs.transition(session, m.id, 0, "not_recorded")
    session.refresh(m)
    return m


def current_authorization(session: Session, meeting_id: uuid.UUID) -> RecordingAuthorization | None:
    return session.scalar(
        select(RecordingAuthorization).where(
            RecordingAuthorization.meeting_id == meeting_id, RecordingAuthorization.superseded_by.is_(None)
        )
    )


def _has_audio(session: Session, meeting_id: uuid.UUID) -> bool:
    return (
        session.scalar(select(func.count()).select_from(AudioAsset).where(AudioAsset.meeting_id == meeting_id)) or 0
    ) > 0


def record_authorization(
    session: Session, actor: Actor, meeting_id: uuid.UUID, body: dict[str, Any]
) -> RecordingAuthorization:
    m = get_meeting(session, actor, meeting_id)
    basis = body.get("basis")
    if basis not in ("bylaw", "express_consent_all", "dictated_notes"):
        raise Invalid("Choose why this meeting may be recorded.", code="basis_required")
    notice = body.get("notice_text_version")
    if notice not in NOTICE_TEXT_VERSIONS:
        raise Invalid("Unknown notice wording version.", code="notice_version")
    clause_id = uuid.UUID(body["bylaw_clause_id"]) if body.get("bylaw_clause_id") else None
    ref = (body.get("bylaw_reference_text") or "").strip() or None
    if basis == "bylaw" and clause_id is None and ref is None:
        raise Invalid("Give the bylaw clause that authorizes recording.", code="bylaw_reference_required")
    if basis == "express_consent_all":
        b = session.get(Brokerage, m.brokerage_id)
        if b is None or not b.allow_express_consent_basis:
            raise Invalid("Your brokerage has not enabled the express-consent basis.", code="basis_disabled")
    if clause_id is not None:
        loc = authz.locate(session, actor, "bylaw_clause", clause_id)
        if loc.strata_id != m.strata_id:
            raise Invalid("The clause must be one of this building's bylaws.", code="clause_other_building")
    if m.state in ("approved", "not_recorded"):
        raise Conflict("The recording authority can no longer be changed.", code="authority_locked")

    prev = current_authorization(session, meeting_id)
    if prev is not None and _has_audio(session, meeting_id):
        # After upload: supersede only to link a clause for the same bylaw basis.
        same = prev.basis == "bylaw" and basis == "bylaw" and clause_id is not None and prev.bylaw_clause_id is None
        if not same:
            raise Conflict(
                "Audio has been uploaded; the recording authority cannot be edited, only superseded "
                "by linking the bylaw clause.",
                code="authority_locked",
            )
    elif prev is None and m.state != "setup":
        raise Conflict("This meeting cannot take a recording authority.", code="authority_locked")

    new_id = uuid7()
    if prev is not None:
        # superseded_by's foreign key is deferred, so the old row is pointed at the new one first;
        # this keeps "one current authorization per meeting" (partial unique index) true at every step.
        session.execute(
            update(RecordingAuthorization)
            .where(RecordingAuthorization.id == prev.id, RecordingAuthorization.superseded_by.is_(None))
            .values(superseded_by=new_id)
        )
    new = RecordingAuthorization(
        id=new_id,
        brokerage_id=m.brokerage_id,
        strata_id=m.strata_id,
        meeting_id=m.id,
        basis=basis,
        bylaw_clause_id=clause_id,
        bylaw_reference_text=ref if ref else (prev.bylaw_reference_text if prev else None),
        notice_text_version=notice,
        attested_by=actor.user_id,
        attested_at=clock.now(),
    )
    session.add(new)
    try:
        session.flush()
    except IntegrityError as exc:  # pragma: no cover - concurrent supersede
        raise Conflict("Recording authority changed concurrently.") from exc
    if m.state == "setup":
        jobs.transition(session, m.id, m.state_version, "authorized")
    audit.record(
        session, actor, "authorization.recorded", strata_id=m.strata_id, target_type="meeting", target_id=m.id,
        details={"basis": basis},
    )
    return new


# ---------------------------------------------------------------- uploads (T-3.1.2)


def upload_out(a: AudioAsset) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "meeting_id": str(a.meeting_id),
        "part_number": a.part_number,
        "byte_size": a.byte_size,
        "received_bytes": a.received_bytes,
        "upload_state": a.upload_state,
    }


def init_upload(session: Session, actor: Actor, meeting_id: uuid.UUID, body: dict[str, Any]) -> tuple[AudioAsset, bool]:
    """Start (or find) an upload. Returns (asset, created). 409 without a recording authority (I-1)."""
    m = get_meeting(session, actor, meeting_id)
    session.execute(select(Meeting.id).where(Meeting.id == m.id).with_for_update())
    auth = current_authorization(session, m.id)
    if auth is None:
        raise Conflict(
            "Record why this meeting may be recorded before uploading audio.", code="no_recording_authority"
        )
    if m.state not in UPLOAD_OPEN_STATES:
        raise Conflict("Audio can no longer be changed for this meeting.", code="upload_closed")
    try:
        sha = bytes.fromhex(str(body["sha256"]))
        size = int(body["byte_size"])
        ext = "." + str(body["extension"]).lower().lstrip(".")
        part = int(body.get("part_number", 1))
    except (KeyError, ValueError) as exc:
        raise Invalid("sha256, byte_size and extension are required.") from exc
    if len(sha) != 32 or size <= 0:
        raise Invalid("Invalid checksum or size.")
    if ext not in AUDIO_EXTENSIONS:
        raise Invalid("This file type is not accepted.", code="type_not_accepted")
    existing = session.scalar(select(AudioAsset).where(AudioAsset.meeting_id == m.id, AudioAsset.sha256 == sha))
    if existing is not None and existing.upload_state != "failed":
        return existing, False  # I-3: the same file twice is one asset
    live = session.execute(
        select(func.count(), func.coalesce(func.sum(AudioAsset.byte_size), 0)).where(
            AudioAsset.meeting_id == m.id, AudioAsset.upload_state != "failed", AudioAsset.deleted_at.is_(None)
        )
    ).one()
    if live[0] >= MAX_PARTS or not 1 <= part <= MAX_PARTS:
        raise Invalid("A meeting takes at most 10 audio parts.", code="too_many_parts")
    if int(live[1]) + size > MAX_MEETING_AUDIO_BYTES:
        raise Invalid("A meeting takes at most 2.5 GB of audio.", code="too_large")
    if existing is not None:  # a failed earlier attempt of the same file: reset it
        existing.upload_state, existing.received_bytes = "receiving", 0
        existing.authorization_id = auth.id
        session.flush()
        return existing, True
    asset_id = uuid7()
    a = AudioAsset(
        id=asset_id,
        brokerage_id=m.brokerage_id,
        strata_id=m.strata_id,
        meeting_id=m.id,
        part_number=part,
        storage_key=storage.key(m.brokerage_id, m.strata_id, "audio", asset_id),
        sha256=sha,
        byte_size=size,
        authorization_id=auth.id,
    )
    session.add(a)
    session.flush()
    if m.state in ("authorized", "uploaded"):
        jobs.transition(session, m.id, m.state_version, "uploading")
    return a, True


def _asset(session: Session, actor: Actor, asset_id: uuid.UUID) -> AudioAsset:
    authz.locate(session, actor, "audio_asset", asset_id)
    a = session.get(AudioAsset, asset_id, with_for_update=True)
    if a is None:  # pragma: no cover
        raise NotFound("Not found.")
    return a


def tmp_key(a: AudioAsset) -> str:
    return storage.key(a.brokerage_id, a.strata_id, "tmp", a.id)


def append_part(session: Session, actor: Actor, asset_id: uuid.UUID, offset: int, data: bytes) -> AudioAsset:
    """Append bytes at ``offset``. A resumed client first reads ``received_bytes`` (I-2)."""
    a = _asset(session, actor, asset_id)
    if a.upload_state != "receiving":
        raise Conflict("This upload is not receiving data.", code="upload_closed")
    if offset != a.received_bytes:
        raise Conflict("Resume from the stored offset.", code="offset_mismatch",
                       extra={"received_bytes": a.received_bytes})
    if a.received_bytes + len(data) > a.byte_size:
        raise Invalid("More data than the declared size.", code="too_large")
    if offset == 0 and sniff_audio(data[:16]) is None:
        raise Invalid("The file content is not an accepted audio type.", code="type_not_accepted")
    a.received_bytes = storage.store().write_at(tmp_key(a), offset, data)
    session.flush()
    return a


def complete_upload(session: Session, actor: Actor, asset_id: uuid.UUID) -> AudioAsset:
    a = _asset(session, actor, asset_id)
    if a.upload_state == "complete":
        return a
    st = storage.store()
    if a.upload_state != "receiving" or a.received_bytes != a.byte_size:
        raise Conflict("The upload is not finished.", code="upload_incomplete",
                       extra={"received_bytes": a.received_bytes})
    digest = hashlib.sha256()
    pos, chunk = 0, 8 * 1024 * 1024
    while pos < a.byte_size:
        part = st.read(tmp_key(a), pos, min(pos + chunk, a.byte_size) - 1)
        digest.update(part)
        pos += len(part)
        if not part:
            break
    if digest.digest() != a.sha256:
        # Committed as failed (the caller reports 422); the client starts this part again.
        st.delete(tmp_key(a))
        a.upload_state, a.received_bytes = "failed", 0
        session.flush()
        return a
    # Malware scanning (ClamAV) is not built in B1; see verification report.
    st.move(tmp_key(a), a.storage_key)
    b = session.get(Brokerage, a.brokerage_id)
    max_days = b.audio_max_days_after_upload if b else 60
    a.upload_state = "complete"
    a.delete_after = clock.now() + timedelta(days=max_days)
    session.flush()
    pending = session.scalar(
        select(func.count()).select_from(AudioAsset).where(
            AudioAsset.meeting_id == a.meeting_id, AudioAsset.upload_state == "receiving"
        )
    )
    if not pending:
        jobs.advance(session, a.meeting_id, ("uploading",), "uploaded")
    audit.record(session, actor, "audio.uploaded", strata_id=a.strata_id, target_type="audio_asset",
                 target_id=a.id, details={"part_number": a.part_number})
    return a


def request_processing(session: Session, actor: Actor, meeting_id: uuid.UUID, asr_model_id: str) -> uuid.UUID:
    """Queue transcription. Idempotent: the job key is the audio checksums plus the model ID."""
    m = get_meeting(session, actor, meeting_id)
    if current_authorization(session, m.id) is None:
        raise Conflict("No recording authority for this meeting.", code="no_recording_authority")
    assets = session.scalars(
        select(AudioAsset).where(
            AudioAsset.meeting_id == m.id, AudioAsset.upload_state == "complete", AudioAsset.deleted_at.is_(None)
        ).order_by(AudioAsset.part_number)
    ).all()
    if not assets:
        raise Conflict("Upload the audio first.", code="no_audio")
    key = ":".join(a.sha256.hex() for a in assets) + "|" + asr_model_id
    job_id, created = jobs.enqueue(session, kind="transcribe", idempotency_key=key, brokerage_id=m.brokerage_id,
                                   strata_id=m.strata_id, meeting_id=m.id)
    if m.state == "failed_transcription" and not created:
        from core.models import Job  # local import keeps the public surface small

        job = session.get(Job, job_id, with_for_update=True)
        if job is not None and job.status == "failed":
            job.status, job.attempt, job.error_code, job.run_after = "queued", 0, None, clock.now()
    elif m.state == "failed_drafting":
        from core.models import Job

        job = session.scalar(select(Job).where(Job.meeting_id == m.id, Job.kind == "draft_minutes"))
        if job is not None and job.status == "failed":
            job.status, job.attempt, job.error_code, job.run_after = "queued", 0, None, clock.now()
            job_id = job.id
    session.flush()
    return job_id


def status_out(session: Session, actor: Actor, meeting_id: uuid.UUID) -> dict[str, Any]:
    from core.models import Job

    m = get_meeting(session, actor, meeting_id)
    last = session.scalar(select(Job).where(Job.meeting_id == m.id).order_by(Job.created_at.desc()).limit(1))
    return {
        "state": m.state,
        "state_version": m.state_version,
        "step": last.kind if last else None,
        "job_status": last.status if last else None,
        "error_code": last.error_code if last else None,
    }


def strata_lot_count(session: Session, strata_id: uuid.UUID) -> int | None:
    s = session.get(StrataCorporation, strata_id)
    return s.strata_lot_count if s else None
