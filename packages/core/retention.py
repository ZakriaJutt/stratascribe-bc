"""Retention sweep for audio (T-5.1.1 partial, MH-12, R-14). Safe to run twice (I-9).

Runs in the system context, which row-level security limits to job rows and the
audio deletion columns; it never reads transcript or minutes content.
"""

from __future__ import annotations

from datetime import timedelta

from sqlalchemy import select

from core import audit, clock, storage
from core import logging as clog
from core.db import Actor, session_for
from core.models import AudioAsset

log = clog.get_logger("retention")
INCOMPLETE_UPLOAD_HOURS = 24


def sweep() -> dict[str, int]:
    now = clock.now()
    actor = Actor.system()
    st = storage.store()
    deleted = missing = abandoned = 0
    with session_for(actor) as s:
        due = s.scalars(
            select(AudioAsset)
            .where(AudioAsset.deleted_at.is_(None), AudioAsset.delete_after <= now)
            .with_for_update(skip_locked=True)
        ).all()
        for a in due:
            removed = st.delete(a.storage_key)
            st.delete(storage.key(a.brokerage_id, a.strata_id, "tmp", a.id))
            missing += 0 if removed else 1
            a.deleted_at = now
            deleted += 1
            audit.record(s, actor, "audio.deleted", brokerage_id=a.brokerage_id, strata_id=a.strata_id,
                         target_type="audio_asset", target_id=a.id,
                         details={"reason": "retention" if removed else "retention_object_missing"})
        stale = s.scalars(
            select(AudioAsset)
            .where(AudioAsset.upload_state == "receiving",
                   AudioAsset.created_at <= now - timedelta(hours=INCOMPLETE_UPLOAD_HOURS))
            .with_for_update(skip_locked=True)
        ).all()
        for a in stale:
            st.delete(storage.key(a.brokerage_id, a.strata_id, "tmp", a.id))
            a.upload_state, a.received_bytes = "failed", 0
            abandoned += 1
            audit.record(s, actor, "audio.deleted", brokerage_id=a.brokerage_id, strata_id=a.strata_id,
                         target_type="audio_asset", target_id=a.id, details={"reason": "incomplete_upload"})
    log.info("retention sweep finished", extra={"count": deleted})
    return {"deleted": deleted, "object_missing": missing, "abandoned_uploads": abandoned}
