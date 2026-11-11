"""Job handlers. Tenant context comes from the job row only, scoped to one building (P-5)."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select

from ai.extraction import extract_items
from ai.llm import LlmClient
from ai.transcription import Transcriber
from core import config, jobs, storage
from core.db import Actor, session_for
from core.ids import uuid7
from core.jobs import LeasedJob
from core.models import AudioAsset, Meeting, MinuteItem, MinutesVersion, Transcript, TranscriptSegment
from rules import RULES_VERSION

TEMPLATE_VERSION = "template-2026.11.1"


class PermanentError(Exception):
    def __init__(self, code: str) -> None:
        super().__init__(code)
        self.code = code


def _actor(job: LeasedJob) -> Actor:
    if job.brokerage_id is None or job.strata_id is None:
        raise PermanentError("job_without_building")
    return Actor.service(job.brokerage_id, job.strata_id)


def transcribe(job: LeasedJob, asr: Transcriber) -> uuid.UUID:
    actor = _actor(job)
    assert job.brokerage_id and job.strata_id
    scoped = storage.ScopedStore(storage.store(), job.brokerage_id, job.strata_id)
    with session_for(actor) as s:
        m = s.get(Meeting, job.meeting_id)
        if m is None:
            raise PermanentError("meeting_not_found")
        existing = s.scalar(select(Transcript.id).where(Transcript.meeting_id == m.id))
        if existing is None:
            jobs.advance(s, m.id, ("uploaded", "failed_transcription"), "transcribing")
        assets = [(a.id, a.storage_key) for a in s.scalars(
            select(AudioAsset).where(AudioAsset.meeting_id == m.id, AudioAsset.upload_state == "complete",
                                     AudioAsset.deleted_at.is_(None)).order_by(AudioAsset.part_number))]
    if existing is not None:
        return _finish_transcribe(job, actor, existing)
    segments: list[tuple[uuid.UUID, Any]] = []
    for asset_id, key in assets:
        audio = scoped.read(key)
        segments.extend((asset_id, seg) for seg in asr.transcribe(audio))
    with session_for(actor) as s:
        existing = s.scalar(select(Transcript.id).where(Transcript.meeting_id == job.meeting_id))
        if existing is None:  # a late duplicate never overwrites a stored transcript (I-4)
            t = Transcript(id=uuid7(), brokerage_id=job.brokerage_id, strata_id=job.strata_id,
                           meeting_id=job.meeting_id, asr_model_id=asr.model_id, asr_params_hash=asr.params_hash)
            s.add(t)
            s.flush()
            for seq, (asset_id, seg) in enumerate(segments, start=1):
                s.add(TranscriptSegment(id=uuid7(), brokerage_id=job.brokerage_id, strata_id=job.strata_id,
                                        transcript_id=t.id, seq=seq, audio_asset_id=asset_id,
                                        start_ms=seg.start_ms, end_ms=seg.end_ms, speaker_label=seg.speaker_label,
                                        text=seg.text))
            existing = t.id
    return _finish_transcribe(job, actor, existing)


def _finish_transcribe(job: LeasedJob, actor: Actor, transcript_id: uuid.UUID) -> uuid.UUID:
    cfg = config.settings()
    with session_for(actor) as s:
        jobs.complete(s, job.id, transcript_id)
        # Compare-and-set: if the meeting moved on, the result is stored but the state is left alone.
        if jobs.advance(s, job.meeting_id, ("transcribing",), "drafting") or s.scalar(  # type: ignore[arg-type]
            select(Meeting.state).where(Meeting.id == job.meeting_id)
        ) == "drafting":
            jobs.enqueue(s, kind="draft_minutes",
                         idempotency_key=f"{transcript_id}|{cfg.prompt_version}|{cfg.llm_model_id}",
                         brokerage_id=job.brokerage_id, strata_id=job.strata_id, meeting_id=job.meeting_id)
    return transcript_id


def draft_minutes(job: LeasedJob, llm: LlmClient) -> uuid.UUID:
    actor = _actor(job)
    cfg = config.settings()
    with session_for(actor) as s:
        existing = s.scalar(select(MinutesVersion.id).where(MinutesVersion.meeting_id == job.meeting_id))
        t = s.scalar(select(Transcript).where(Transcript.meeting_id == job.meeting_id))
        if t is None:
            raise PermanentError("transcript_missing")
        jobs.advance(s, t.meeting_id, ("failed_drafting",), "drafting")
        segs = [{"id": str(g.id), "speaker_label": g.speaker_label, "text": g.text}
                for g in s.scalars(select(TranscriptSegment).where(TranscriptSegment.transcript_id == t.id)
                                   .order_by(TranscriptSegment.seq))]
        transcript_id = t.id
    if existing is None:
        items = extract_items(segs, llm)  # None after two invalid outputs: empty-template fallback
        with session_for(actor) as s:
            existing = s.scalar(select(MinutesVersion.id).where(MinutesVersion.meeting_id == job.meeting_id))
            if existing is None:
                v = MinutesVersion(id=uuid7(), brokerage_id=job.brokerage_id, strata_id=job.strata_id,
                                   meeting_id=job.meeting_id, version=1, transcript_id=transcript_id,
                                   llm_model_id=llm.model_id, prompt_version=cfg.prompt_version,
                                   rules_version=RULES_VERSION,
                                   template_version="empty-template" if items is None else TEMPLATE_VERSION)
                s.add(v)
                s.flush()
                # Every draft carries a quorum item for the manager to complete (lead ruling): from the model's
                # text if it proposed one, otherwise empty. Only the manager's confirmed figures decide it.
                if not any(it.item_type == "quorum" for it in items or []):
                    s.add(MinuteItem(id=uuid7(), brokerage_id=job.brokerage_id, strata_id=job.strata_id,
                                     minutes_version_id=v.id, position=0, item_type="quorum", body_text="",
                                     origin="ai", ai_suggestion={"template": "quorum"}))
                for pos, it in enumerate(items or [], start=1):
                    suggestion = it.model_dump()
                    if it.item_type == "motion":
                        suggestion["suggested_method"] = "counted" if it.spoken_counts else "declared"
                    s.add(MinuteItem(
                        id=uuid7(), brokerage_id=job.brokerage_id, strata_id=job.strata_id,
                        minutes_version_id=v.id, position=pos, item_type=it.item_type, body_text=it.text,
                        mover=it.mover, seconder=it.seconder, spoken_outcome=it.spoken_outcome,
                        ai_suggestion=suggestion, source_segment_ids=[uuid.UUID(x) for x in it.segment_ids],
                        origin="ai", sensitive_flag=it.sensitive,
                    ))
                existing = v.id
    with session_for(actor) as s:
        jobs.complete(s, job.id, existing)
        jobs.advance(s, job.meeting_id, ("drafting",), "ready_for_review")  # type: ignore[arg-type]
    return existing


def mark_failed(job: LeasedJob) -> None:
    """After the last attempt, move the meeting to the matching failed state."""
    if job.meeting_id is None or job.brokerage_id is None or job.strata_id is None:
        return
    target = {"transcribe": ("transcribing", "failed_transcription"),
              "draft_minutes": ("drafting", "failed_drafting")}.get(job.kind)
    if target is None:
        return
    with session_for(_actor(job)) as s:
        jobs.advance(s, job.meeting_id, (target[0],), target[1])
