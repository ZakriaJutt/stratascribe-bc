"""Job states and meeting-state transitions (T-3.1.3, R-01, R-02).

Every meeting state change goes through ``transition`` with compare-and-set on
``state_version``: a late or duplicate completion cannot overwrite a newer
state. Jobs are rows leased with ``FOR UPDATE SKIP LOCKED``; a duplicate request
finds the existing row by ``(kind, idempotency_key)``.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select, text, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from core import clock
from core import logging as clog
from core.db import Actor, session_for
from core.ids import uuid7
from core.models import Job, Meeting

TRANSITIONS: frozenset[tuple[str, str]] = frozenset(
    {
        ("setup", "authorized"),
        ("setup", "not_recorded"),
        ("authorized", "uploading"),
        ("uploading", "uploaded"),
        ("uploading", "authorized"),
        ("uploaded", "uploading"),
        ("uploaded", "transcribing"),
        ("transcribing", "drafting"),
        ("transcribing", "failed_transcription"),
        ("drafting", "ready_for_review"),
        ("drafting", "failed_drafting"),
        ("failed_transcription", "transcribing"),
        ("failed_drafting", "drafting"),
        ("ready_for_review", "in_review"),
        ("in_review", "approved"),
        ("approved", "in_review"),
    }
)

# TRD "Jobs, retries, timeouts, idempotency": retries and backoff per kind.
BACKOFF_MINUTES = {"transcribe": (1, 5, 15), "draft_minutes": (1, 5, 15), "index_bylaws": (1, 5, 15)}
MAX_ATTEMPTS = {"transcribe": 4, "draft_minutes": 4, "index_bylaws": 4, "export": 3}
LEASE_SECONDS = {"transcribe": 30 * 60, "draft_minutes": 15 * 60, "index_bylaws": 10 * 60}


class IllegalTransition(ValueError):
    pass


def transition(session: Session, meeting_id: uuid.UUID, expected_version: int, new_state: str) -> bool:
    """Compare-and-set. Returns False (and changes nothing) if the version moved on."""
    current = session.execute(
        select(Meeting.state, Meeting.state_version).where(Meeting.id == meeting_id)
    ).one_or_none()
    if current is None:
        return False
    state, version = current
    if version != expected_version:
        return False
    if (state, new_state) not in TRANSITIONS:
        raise IllegalTransition(f"{state} -> {new_state}")
    res = session.execute(
        update(Meeting)
        .where(Meeting.id == meeting_id, Meeting.state_version == expected_version, Meeting.state == state)
        .values(state=new_state, state_version=Meeting.state_version + 1)
        .returning(Meeting.id)
    )
    return res.scalar_one_or_none() is not None


def advance(session: Session, meeting_id: uuid.UUID, from_states: tuple[str, ...], new_state: str) -> bool:
    """Transition from the current state if it is one of ``from_states``; CAS on the version read."""
    row = session.execute(
        select(Meeting.state, Meeting.state_version).where(Meeting.id == meeting_id).with_for_update()
    ).one_or_none()
    if row is None or row[0] not in from_states:
        return False
    return transition(session, meeting_id, row[1], new_state)


def enqueue(
    session: Session,
    *,
    kind: str,
    idempotency_key: str,
    brokerage_id: uuid.UUID | None,
    strata_id: uuid.UUID | None,
    meeting_id: uuid.UUID | None = None,
    bylaw_document_id: uuid.UUID | None = None,
) -> tuple[uuid.UUID, bool]:
    """Insert a job unless one with the same key exists. Returns (job_id, created)."""
    corr = clog.correlation_id() or clog.new_correlation_id()
    job_id = uuid7()
    stmt = (
        insert(Job)
        .values(
            id=job_id,
            kind=kind,
            idempotency_key=idempotency_key,
            brokerage_id=brokerage_id,
            strata_id=strata_id,
            meeting_id=meeting_id,
            bylaw_document_id=bylaw_document_id,
            correlation_id=uuid.UUID(corr),
            max_attempts=MAX_ATTEMPTS.get(kind, 1),
        )
        .on_conflict_do_nothing(index_elements=["kind", "idempotency_key"])
        .returning(Job.id)
    )
    created = session.execute(stmt).scalar_one_or_none()
    if created is not None:
        return created, True
    existing = session.scalar(
        select(Job.id).where(Job.kind == kind, Job.idempotency_key == idempotency_key)
    )
    if existing is None:  # pragma: no cover - the row is invisible: different building
        raise LookupError("job exists outside the caller's scope")
    return existing, False


@dataclass(frozen=True)
class LeasedJob:
    id: uuid.UUID
    kind: str
    brokerage_id: uuid.UUID | None
    strata_id: uuid.UUID | None
    meeting_id: uuid.UUID | None
    bylaw_document_id: uuid.UUID | None
    attempt: int
    correlation_id: uuid.UUID


def lease(worker_id: str, kinds: tuple[str, ...] | None = None) -> LeasedJob | None:
    """Lease the oldest runnable job. Two workers never get the same job (C-3)."""
    now = clock.now()
    with session_for(Actor.system()) as s:
        q = (
            select(Job)
            .where(Job.status == "queued", Job.run_after <= now)
            .order_by(Job.created_at)
            .limit(1)
            .with_for_update(skip_locked=True)
        )
        if kinds:
            q = q.where(Job.kind.in_(kinds))
        job = s.scalars(q).first()
        if job is None:
            return None
        job.status = "leased"
        job.attempt += 1
        job.leased_by = worker_id
        job.leased_until = now + timedelta(seconds=LEASE_SECONDS.get(job.kind, 120))
        s.flush()
        return LeasedJob(
            job.id, job.kind, job.brokerage_id, job.strata_id, job.meeting_id, job.bylaw_document_id,
            job.attempt, job.correlation_id,
        )


def complete(session: Session, job_id: uuid.UUID, result_ref: uuid.UUID | None) -> None:
    """Mark succeeded inside the worker's result transaction (service actor of the job's building)."""
    session.execute(
        update(Job)
        .where(Job.id == job_id)
        .values(status="succeeded", result_ref=result_ref, leased_until=None, error_code=None)
    )


def fail(job_id: uuid.UUID, error_code: str) -> str:
    """Retry with backoff, or fail after the last attempt. Returns the new status."""
    with session_for(Actor.system()) as s:
        job = s.get(Job, job_id, with_for_update=True)
        if job is None or job.status == "succeeded":
            return job.status if job else "missing"
        job.error_code = error_code
        job.leased_until = None
        job.leased_by = None
        if job.attempt >= job.max_attempts:
            job.status = "failed"
        else:
            delays = BACKOFF_MINUTES.get(job.kind, (1,))
            delay = delays[min(job.attempt - 1, len(delays) - 1)]
            job.status = "queued"
            job.run_after = clock.now() + timedelta(minutes=delay)
        s.flush()
        return job.status


def reconcile() -> int:
    """Re-queue (or fail) jobs whose lease expired. Returns the number touched."""
    now = clock.now()
    touched = 0
    with session_for(Actor.system()) as s:
        jobs = s.scalars(
            select(Job).where(Job.status == "leased", Job.leased_until < now).with_for_update(skip_locked=True)
        ).all()
        for job in jobs:
            job.leased_until = None
            job.leased_by = None
            job.error_code = "lease_expired"
            job.status = "failed" if job.attempt >= job.max_attempts else "queued"
            touched += 1
    return touched


def heartbeat(worker_id: str, fingerprint: str) -> None:
    with session_for(Actor.system()) as s:
        s.execute(
            text(
                "INSERT INTO worker_heartbeats (worker_id, config_fingerprint, last_seen_at) VALUES (:w, :f, :t) "
                "ON CONFLICT (worker_id) DO UPDATE SET config_fingerprint = :f, last_seen_at = :t"
            ),
            {"w": worker_id, "f": fingerprint, "t": clock.now()},
        )


def config_mismatch(session: Session, fingerprint: str) -> bool:
    """True if a live worker runs with a different validated configuration (I-21)."""
    rows = session.execute(text(
        "SELECT config_fingerprint FROM worker_heartbeats WHERE last_seen_at > now() - interval '2 minutes'"
    )).scalars().all()
    return any(r != fingerprint for r in rows)
