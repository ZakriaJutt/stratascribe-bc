"""SQLAlchemy models (schema.md "Data dictionary").

Indexes, unique and CHECK constraints are declared here AND in migrations; the
parity test (G-2) compares the migrated database with this metadata. Row-level
security policies and triggers live only in migrations and are covered by the
policy-listing test.

B1 covers the tables the core path needs. Not yet created: subscriptions,
exports, deletion_requests, backfill_progress. ``bylaw_clauses.embedding`` and
``statute_sections.embedding`` are absent because pgvector is not available on
this PostgreSQL; clause search sits behind ``ai.search.ClauseSearch``.
"""

from __future__ import annotations

import uuid
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    BigInteger,
    Boolean,
    CheckConstraint,
    Computed,
    Date,
    DateTime,
    ForeignKey,
    ForeignKeyConstraint,
    Index,
    Integer,
    LargeBinary,
    MetaData,
    SmallInteger,
    Text,
    UniqueConstraint,
    func,
    text,
)
from sqlalchemy.dialects.postgresql import ARRAY, CITEXT, JSONB, UUID
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

from core.ids import uuid7

NAMING = {
    "ix": "ix_%(table_name)s_%(column_0_N_name)s",
    "uq": "uq_%(table_name)s_%(column_0_N_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_N_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    metadata = MetaData(naming_convention=NAMING)


TS = DateTime(timezone=True)


def pk() -> Mapped[uuid.UUID]:
    return mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid7)


def created() -> Mapped[datetime]:
    return mapped_column(TS, nullable=False, server_default=func.now())


def updated() -> Mapped[datetime]:
    return mapped_column(TS, nullable=False, server_default=func.now(), onupdate=func.now())


def row_version() -> Mapped[int]:
    return mapped_column(Integer, nullable=False, server_default=text("1"))


def uid(nullable: bool = False) -> Mapped[Any]:
    return mapped_column(UUID(as_uuid=True), nullable=nullable)


def enum_check(column: str, values: tuple[str, ...], name: str | None = None) -> CheckConstraint:
    allowed = ", ".join(f"'{v}'" for v in values)
    return CheckConstraint(f"{column} IN ({allowed})", name=name or f"{column}_values")


def building_fk() -> ForeignKeyConstraint:
    return ForeignKeyConstraint(
        ["strata_id", "brokerage_id"],
        ["strata_corporations.id", "strata_corporations.brokerage_id"],
        name=None,
    )


MEETING_STATES = (
    "setup",
    "authorized",
    "not_recorded",
    "uploading",
    "uploaded",
    "transcribing",
    "failed_transcription",
    "drafting",
    "failed_drafting",
    "ready_for_review",
    "in_review",
    "approved",
)


class Brokerage(Base):
    __tablename__ = "brokerages"
    id: Mapped[uuid.UUID] = pk()
    legal_name: Mapped[str] = mapped_column(Text, nullable=False)
    licence_label: Mapped[str | None] = mapped_column(Text)
    privacy_contact_name: Mapped[str] = mapped_column(Text, nullable=False)
    privacy_contact_email: Mapped[str] = mapped_column(Text, nullable=False)
    allow_express_consent_basis: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    audio_retention_days_after_approval: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("14")
    )
    audio_max_days_after_upload: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("60"))
    transcript_retention_days_after_approval: Mapped[int] = mapped_column(
        Integer, nullable=False, server_default=text("90")
    )
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
    row_version: Mapped[int] = row_version()
    __table_args__ = (
        CheckConstraint("audio_retention_days_after_approval BETWEEN 1 AND 60", name="audio_retention_range"),
        CheckConstraint("audio_max_days_after_upload BETWEEN 7 AND 90", name="audio_max_range"),
        CheckConstraint("transcript_retention_days_after_approval BETWEEN 1 AND 365", name="transcript_range"),
        enum_check("status", ("active", "closing", "closed")),
    )


class User(Base):
    __tablename__ = "users"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brokerages.id"), nullable=False)
    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    role: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'invited'"))
    last_sign_in_at: Mapped[datetime | None] = mapped_column(TS)
    totp_secret_encrypted: Mapped[bytes | None] = mapped_column(LargeBinary)
    totp_enrolled_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
    row_version: Mapped[int] = row_version()
    __table_args__ = (
        UniqueConstraint("id", "brokerage_id"),
        enum_check("role", ("managing_broker", "strata_manager")),
        enum_check("status", ("invited", "active", "deactivated")),
    )


class Operator(Base):
    __tablename__ = "operators"
    id: Mapped[uuid.UUID] = pk()
    email: Mapped[str] = mapped_column(CITEXT, nullable=False, unique=True)
    full_name: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    totp_secret_encrypted: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    last_sign_in_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = created()
    __table_args__ = (enum_check("status", ("active", "deactivated")),)


class StrataCorporation(Base):
    __tablename__ = "strata_corporations"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brokerages.id"), nullable=False)
    name: Mapped[str] = mapped_column(Text, nullable=False)
    strata_plan_number: Mapped[str] = mapped_column(Text, nullable=False)
    strata_lot_count: Mapped[int | None] = mapped_column(Integer)
    owner_count: Mapped[int | None] = mapped_column(Integer)
    eligible_votes_total: Mapped[int | None] = mapped_column(Integer)
    council_size: Mapped[int | None] = mapped_column(Integer)
    general_quorum_rule: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("""'{"type": "act_default"}'::jsonb""")
    )
    council_quorum_rule: Mapped[dict[str, Any]] = mapped_column(
        JSONB, nullable=False, server_default=text("""'{"type": "standard_bylaw_16"}'::jsonb""")
    )
    standard_bylaws_declared_by: Mapped[uuid.UUID | None] = uid(True)
    standard_bylaws_declared_at: Mapped[datetime | None] = mapped_column(TS)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'active'"))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
    row_version: Mapped[int] = row_version()
    __table_args__ = (
        UniqueConstraint("id", "brokerage_id"),
        Index("uq_strata_plan_per_brokerage", "brokerage_id", text("upper(strata_plan_number)"), unique=True),
        CheckConstraint("strata_lot_count IS NULL OR strata_lot_count > 0", name="lots_positive"),
        CheckConstraint("owner_count IS NULL OR owner_count > 0", name="owners_positive"),
        CheckConstraint("council_size IS NULL OR council_size > 0", name="council_positive"),
        enum_check("status", ("active", "deleting", "deleted")),
    )


class BuildingAssignment(Base):
    __tablename__ = "building_assignments"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    user_id: Mapped[uuid.UUID] = uid()
    assigned_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    assigned_at: Mapped[datetime] = mapped_column(TS, nullable=False, server_default=func.now())
    revoked_at: Mapped[datetime | None] = mapped_column(TS)
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        building_fk(),
        # The assigned user must belong to the same brokerage (declarative, instead of a trigger).
        ForeignKeyConstraint(["user_id", "brokerage_id"], ["users.id", "users.brokerage_id"]),
        Index(
            "uq_assignment_active",
            "strata_id",
            "user_id",
            unique=True,
            postgresql_where=text("revoked_at IS NULL"),
        ),
        Index("ix_assignment_user_active", "user_id", postgresql_where=text("revoked_at IS NULL")),
    )


class Meeting(Base):
    __tablename__ = "meetings"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    meeting_type: Mapped[str] = mapped_column(Text, nullable=False)
    held_on: Mapped[date] = mapped_column(Date, nullable=False)
    format: Mapped[str] = mapped_column(Text, nullable=False)
    source_type: Mapped[str] = mapped_column(Text, nullable=False)
    state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'setup'"))
    state_version: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False, server_default=text("1"))
    length_minutes: Mapped[int | None] = mapped_column(Integer)
    reconvened_after_adjournment: Mapped[bool] = mapped_column(
        Boolean, nullable=False, server_default=text("false")
    )
    ended_at_local: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
    row_version: Mapped[int] = row_version()
    __table_args__ = (
        building_fk(),
        UniqueConstraint("id", "strata_id"),
        UniqueConstraint("strata_id", "meeting_type", "held_on", "sequence"),
        enum_check("meeting_type", ("council", "agm", "sgm")),
        enum_check("format", ("in_person", "electronic", "hybrid")),
        enum_check("source_type", ("recording", "dictated_notes", "not_recorded")),
        enum_check("state", MEETING_STATES),
        CheckConstraint("sequence IN (1, 2)", name="sequence_values"),
        Index("ix_meetings_strata_held", "strata_id", text("held_on DESC")),
        Index(
            "ix_meetings_review_queue",
            "brokerage_id",
            "state",
            postgresql_where=text("state IN ('ready_for_review', 'in_review')"),
        ),
    )


def meeting_fk() -> ForeignKeyConstraint:
    return ForeignKeyConstraint(["meeting_id", "strata_id"], ["meetings.id", "meetings.strata_id"])


class RecordingAuthorization(Base):
    __tablename__ = "recording_authorizations"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    meeting_id: Mapped[uuid.UUID] = uid()
    basis: Mapped[str] = mapped_column(Text, nullable=False)
    bylaw_clause_id: Mapped[uuid.UUID | None] = uid(True)
    bylaw_reference_text: Mapped[str | None] = mapped_column(Text)
    notice_text_version: Mapped[str] = mapped_column(Text, nullable=False)
    attested_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    attested_at: Mapped[datetime] = mapped_column(TS, nullable=False, server_default=func.now())
    superseded_by: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("recording_authorizations.id", deferrable=True, initially="DEFERRED")
    )
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        building_fk(),
        meeting_fk(),
        UniqueConstraint("id", "strata_id"),
        ForeignKeyConstraint(["bylaw_clause_id", "strata_id"], ["bylaw_clauses.id", "bylaw_clauses.strata_id"]),
        enum_check("basis", ("bylaw", "express_consent_all", "dictated_notes")),
        CheckConstraint(
            "basis <> 'bylaw' OR bylaw_clause_id IS NOT NULL OR bylaw_reference_text IS NOT NULL",
            name="bylaw_basis_reference",
        ),
        Index("uq_authorization_current", "meeting_id", unique=True, postgresql_where=text("superseded_by IS NULL")),
    )


class AudioAsset(Base):
    __tablename__ = "audio_assets"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    meeting_id: Mapped[uuid.UUID] = uid()
    part_number: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("1"))
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    byte_size: Mapped[int] = mapped_column(BigInteger, nullable=False)
    received_bytes: Mapped[int] = mapped_column(BigInteger, nullable=False, server_default=text("0"))
    duration_seconds: Mapped[int | None] = mapped_column(Integer)
    upload_state: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'receiving'"))
    authorization_id: Mapped[uuid.UUID] = uid()
    delete_after: Mapped[datetime | None] = mapped_column(TS)
    deleted_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
    row_version: Mapped[int] = row_version()
    __table_args__ = (
        building_fk(),
        meeting_fk(),
        UniqueConstraint("id", "strata_id"),
        ForeignKeyConstraint(
            ["authorization_id", "strata_id"], ["recording_authorizations.id", "recording_authorizations.strata_id"]
        ),
        UniqueConstraint("meeting_id", "sha256"),
        enum_check("upload_state", ("receiving", "complete", "failed")),
        CheckConstraint("byte_size > 0 AND received_bytes BETWEEN 0 AND byte_size", name="sizes"),
        CheckConstraint("part_number BETWEEN 1 AND 10", name="part_range"),
        Index("ix_audio_delete_after", "delete_after", postgresql_where=text("deleted_at IS NULL")),
    )


JOB_KINDS = ("transcribe", "draft_minutes", "index_bylaws", "export", "retention_sweep", "reconcile")


class Job(Base):
    __tablename__ = "jobs"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID | None] = uid(True)
    strata_id: Mapped[uuid.UUID | None] = uid(True)
    meeting_id: Mapped[uuid.UUID | None] = uid(True)
    bylaw_document_id: Mapped[uuid.UUID | None] = uid(True)
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    idempotency_key: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'queued'"))
    attempt: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    max_attempts: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("3"))
    run_after: Mapped[datetime] = mapped_column(TS, nullable=False, server_default=func.now())
    leased_until: Mapped[datetime | None] = mapped_column(TS)
    leased_by: Mapped[str | None] = mapped_column(Text)
    correlation_id: Mapped[uuid.UUID] = uid()
    error_code: Mapped[str | None] = mapped_column(Text)
    result_ref: Mapped[uuid.UUID | None] = uid(True)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
    __table_args__ = (
        building_fk(),
        meeting_fk(),
        # Scoped to tenant, building and meeting (B1-002); NULLs equal so system jobs stay unique.
        UniqueConstraint(
            "brokerage_id", "strata_id", "meeting_id", "kind", "idempotency_key",
            name="uq_jobs_scope_key", postgresql_nulls_not_distinct=True,
        ),
        enum_check("kind", JOB_KINDS),
        enum_check("status", ("queued", "leased", "succeeded", "failed")),
        CheckConstraint(
            "kind IN ('retention_sweep', 'reconcile') OR (brokerage_id IS NOT NULL AND strata_id IS NOT NULL)",
            name="tenant_scope",
        ),
        Index("ix_jobs_lease", "status", "leased_until", postgresql_where=text("status IN ('queued', 'leased')")),
    )


class Transcript(Base):
    __tablename__ = "transcripts"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    asr_model_id: Mapped[str] = mapped_column(Text, nullable=False)
    asr_params_hash: Mapped[str] = mapped_column(Text, nullable=False)
    language: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'en'"))
    delete_after: Mapped[datetime | None] = mapped_column(TS)
    deleted_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = created()
    __table_args__ = (building_fk(), meeting_fk(), UniqueConstraint("id", "strata_id"))


class TranscriptSegment(Base):
    __tablename__ = "transcript_segments"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    transcript_id: Mapped[uuid.UUID] = uid()
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    audio_asset_id: Mapped[uuid.UUID | None] = uid(True)
    start_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    end_ms: Mapped[int] = mapped_column(Integer, nullable=False)
    speaker_label: Mapped[str] = mapped_column(Text, nullable=False)
    speaker_name: Mapped[str | None] = mapped_column(Text)
    text: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        building_fk(),
        ForeignKeyConstraint(["transcript_id", "strata_id"], ["transcripts.id", "transcripts.strata_id"]),
        UniqueConstraint("transcript_id", "seq"),
        CheckConstraint("end_ms >= start_ms AND start_ms >= 0", name="times"),
    )


class MinutesVersion(Base):
    __tablename__ = "minutes_versions"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    meeting_id: Mapped[uuid.UUID] = uid()
    version: Mapped[int] = mapped_column(Integer, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'draft'"))
    transcript_id: Mapped[uuid.UUID | None] = uid(True)
    llm_model_id: Mapped[str | None] = mapped_column(Text)
    prompt_version: Mapped[str | None] = mapped_column(Text)
    rules_version: Mapped[str] = mapped_column(Text, nullable=False)
    template_version: Mapped[str | None] = mapped_column(Text)
    reopened_from: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("minutes_versions.id"))
    reopen_reason: Mapped[str | None] = mapped_column(Text)
    content_hash: Mapped[bytes | None] = mapped_column(LargeBinary)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
    row_version: Mapped[int] = row_version()
    __table_args__ = (
        building_fk(),
        meeting_fk(),
        UniqueConstraint("id", "strata_id"),
        UniqueConstraint("meeting_id", "version"),
        enum_check("status", ("draft", "approved", "superseded")),
        CheckConstraint("reopened_from IS NULL OR reopen_reason IS NOT NULL", name="reopen_reason"),
        Index("uq_minutes_one_draft", "meeting_id", unique=True, postgresql_where=text("status = 'draft'")),
    )


COUNTED_OUTCOME_SQL = (
    "CASE "
    "WHEN computed_result IN ('carried', 'defeated') THEN computed_result "
    "WHEN computed_result = 'tie' AND casting_vote = 'used_for' THEN 'carried' "
    "WHEN computed_result = 'tie' AND casting_vote IN ('used_against', 'not_used') THEN 'defeated' "
    "END"
)
FINAL_OUTCOME_SQL = (
    "CASE "
    "WHEN outcome_method = 'declared' AND outcome_attested_at IS NOT NULL THEN declared_outcome "
    "WHEN outcome_method = 'counted' AND discrepancy_resolution = 'recorded_as_declared' THEN declared_outcome "
    f"WHEN outcome_method = 'counted' THEN {COUNTED_OUTCOME_SQL} "
    "END"
)


# Every term NULL-safe (coalesce / IS NOT NULL): a CHECK passes on NULL, so no clause may yield NULL (B1-003).
_COUNTED = f"coalesce(({COUNTED_OUTCOME_SQL}), '')"
REVIEWED_MOTION_SQL = (
    "item_type <> 'motion' OR review_status <> 'reviewed' OR ("
    "final_outcome IS NOT NULL AND ("
    "(coalesce(outcome_method, '') = 'declared' AND declared_outcome IS NOT NULL "
    "AND outcome_attested_by IS NOT NULL AND outcome_attested_at IS NOT NULL) OR "
    "(coalesce(outcome_method, '') = 'counted' AND threshold IS NOT NULL AND votes_for IS NOT NULL "
    "AND votes_against IS NOT NULL AND (coalesce(computed_result, '') IN ('carried', 'defeated') "
    "OR (coalesce(computed_result, '') = 'tie' AND casting_vote IS NOT NULL)) "
    f"AND (declared_outcome IS NULL OR declared_outcome = {_COUNTED} "
    "OR coalesce(discrepancy_resolution, '') = 'recorded_as_declared'))))"
)
# A show-of-cards motion stores no counts or threshold; counts exist only for a counted vote (B1-005).
DECLARED_NO_COUNTS_SQL = (
    "coalesce(outcome_method, '') = 'counted' OR (threshold IS NULL AND votes_for IS NULL "
    "AND votes_against IS NULL AND votes_abstained IS NULL AND eligible_votes IS NULL "
    "AND members_present IS NULL AND casting_vote IS NULL AND discrepancy_resolution IS NULL)"
)
QUORUM_FIELDS_SQL = (
    "item_type = 'quorum' OR (quorum_basis IS NULL AND quorum_statement IS NULL AND present_count IS NULL "
    "AND eligible_count IS NULL AND required_count IS NULL AND quorum_met IS NULL AND quorum_rule IS NULL "
    "AND quorum_formula IS NULL AND quorum_attested_by IS NULL)"
)
# A reviewed quorum item is either attested as declared by the chair, or counted with the computed
# result stored and agreeing with the recorded statement (B1-006).
REVIEWED_QUORUM_SQL = (
    "item_type <> 'quorum' OR review_status <> 'reviewed' OR (quorum_statement IS NOT NULL AND ("
    "(coalesce(quorum_basis, '') = 'declared' AND quorum_statement = 'established' "
    "AND quorum_attested_by IS NOT NULL AND quorum_attested_at IS NOT NULL) OR "
    "(coalesce(quorum_basis, '') = 'counted' AND present_count IS NOT NULL AND eligible_count IS NOT NULL "
    "AND quorum_met IS NOT NULL AND rules_version IS NOT NULL AND quorum_formula IS NOT NULL "
    "AND quorum_met = (quorum_statement = 'established'))))"
)


class MinuteItem(Base):
    __tablename__ = "minute_items"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    minutes_version_id: Mapped[uuid.UUID] = uid()
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    item_type: Mapped[str] = mapped_column(Text, nullable=False)
    body_text: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("''"))
    mover: Mapped[str | None] = mapped_column(Text)
    seconder: Mapped[str | None] = mapped_column(Text)
    outcome_method: Mapped[str | None] = mapped_column(Text)
    declared_outcome: Mapped[str | None] = mapped_column(Text)
    outcome_attested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    outcome_attested_at: Mapped[datetime | None] = mapped_column(TS)
    threshold: Mapped[str | None] = mapped_column(Text)
    votes_for: Mapped[int | None] = mapped_column(Integer)
    votes_against: Mapped[int | None] = mapped_column(Integer)
    votes_abstained: Mapped[int | None] = mapped_column(Integer)
    eligible_votes: Mapped[int | None] = mapped_column(Integer)
    members_present: Mapped[int | None] = mapped_column(Integer)
    casting_vote: Mapped[str | None] = mapped_column(Text)
    computed_result: Mapped[str | None] = mapped_column(Text)
    computed_formula: Mapped[str | None] = mapped_column(Text)
    rules_version: Mapped[str | None] = mapped_column(Text)
    discrepancy_resolution: Mapped[str | None] = mapped_column(Text)
    discrepancy_note: Mapped[str | None] = mapped_column(Text)
    # Quorum attendance (item_type = 'quorum' only; B1-006)
    quorum_basis: Mapped[str | None] = mapped_column(Text)
    quorum_statement: Mapped[str | None] = mapped_column(Text)
    present_count: Mapped[int | None] = mapped_column(Integer)
    eligible_count: Mapped[int | None] = mapped_column(Integer)
    required_count: Mapped[int | None] = mapped_column(Integer)
    quorum_met: Mapped[bool | None] = mapped_column(Boolean)
    quorum_rule: Mapped[str | None] = mapped_column(Text)
    quorum_formula: Mapped[str | None] = mapped_column(Text)
    quorum_attested_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    quorum_attested_at: Mapped[datetime | None] = mapped_column(TS)
    final_outcome: Mapped[str | None] = mapped_column(Text, Computed(FINAL_OUTCOME_SQL, persisted=True))
    spoken_outcome: Mapped[str | None] = mapped_column(Text)
    ai_suggestion: Mapped[dict[str, Any] | None] = mapped_column(JSONB)
    source_segment_ids: Mapped[list[uuid.UUID]] = mapped_column(
        ARRAY(UUID(as_uuid=True)), nullable=False, server_default=text("'{}'")
    )
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    review_status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'needs_review'"))
    blocked_reason: Mapped[str | None] = mapped_column(Text)
    sensitive_flag: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    deleted_at: Mapped[datetime | None] = mapped_column(TS)
    delete_reason: Mapped[str | None] = mapped_column(Text)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
    row_version: Mapped[int] = row_version()
    __table_args__ = (
        building_fk(),
        ForeignKeyConstraint(
            ["minutes_version_id", "strata_id"], ["minutes_versions.id", "minutes_versions.strata_id"]
        ),
        UniqueConstraint("id", "strata_id"),
        enum_check(
            "item_type", ("attendance", "quorum", "call_to_order", "motion", "discussion", "adjournment", "other")
        ),
        CheckConstraint("outcome_method IS NULL OR outcome_method IN ('declared', 'counted')", name="method"),
        CheckConstraint("declared_outcome IS NULL OR declared_outcome IN ('carried', 'defeated')", name="declared"),
        CheckConstraint(
            "threshold IS NULL OR threshold IN "
            "('majority', 'three_quarter', 'eighty_percent', 'unanimous', 'council_majority')",
            name="threshold",
        ),
        CheckConstraint(
            "coalesce(votes_for, 0) >= 0 AND coalesce(votes_against, 0) >= 0 AND coalesce(votes_abstained, 0) >= 0 "
            "AND coalesce(eligible_votes, 0) >= 0 AND coalesce(members_present, 0) >= 0",
            name="counts_non_negative",
        ),
        CheckConstraint(
            "casting_vote IS NULL OR (casting_vote IN ('not_used', 'used_for', 'used_against') "
            "AND coalesce(computed_result, '') = 'tie')",
            name="casting_vote",
        ),
        CheckConstraint(
            "computed_result IS NULL OR computed_result IN ('carried', 'defeated', 'tie', 'no_result')",
            name="computed",
        ),
        CheckConstraint(
            "coalesce(outcome_method, '') = 'counted' OR computed_result IS NULL", name="declared_has_no_computed"
        ),
        CheckConstraint(
            "discrepancy_resolution IS NULL OR discrepancy_resolution IN "
            "('counts_corrected', 'threshold_corrected', 'recorded_as_declared')",
            name="resolution",
        ),
        CheckConstraint(
            "discrepancy_resolution IS DISTINCT FROM 'recorded_as_declared' "
            "OR (discrepancy_note IS NOT NULL AND length(btrim(discrepancy_note)) > 0)",
            name="resolution_note",
        ),
        CheckConstraint(REVIEWED_MOTION_SQL, name="reviewed_motion_complete"),
        CheckConstraint(DECLARED_NO_COUNTS_SQL, name="declared_no_counts"),
        CheckConstraint(QUORUM_FIELDS_SQL, name="quorum_fields_only_on_quorum"),
        CheckConstraint(REVIEWED_QUORUM_SQL, name="reviewed_quorum_complete"),
        CheckConstraint(
            "quorum_basis IS NULL OR quorum_basis IN ('counted', 'declared')", name="quorum_basis"
        ),
        CheckConstraint(
            "quorum_statement IS NULL OR quorum_statement IN ('established', 'not_established')",
            name="quorum_statement",
        ),
        CheckConstraint(
            "coalesce(present_count, 0) >= 0 AND coalesce(eligible_count, 0) >= 0 AND coalesce(required_count, 0) >= 0",
            name="quorum_counts_non_negative",
        ),
        enum_check("origin", ("ai", "manager_added")),
        enum_check("review_status", ("needs_review", "reviewed", "blocked")),
        Index("ix_minute_items_version_position", "minutes_version_id", "position"),
    )


class MinuteItemCitation(Base):
    __tablename__ = "minute_item_citations"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    minute_item_id: Mapped[uuid.UUID] = uid()
    bylaw_clause_id: Mapped[uuid.UUID | None] = uid(True)
    statute_section_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("statute_sections.id"))
    quoted_text: Mapped[str | None] = mapped_column(Text)
    origin: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'suggested'"))
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
    row_version: Mapped[int] = row_version()
    __table_args__ = (
        building_fk(),
        ForeignKeyConstraint(["minute_item_id", "strata_id"], ["minute_items.id", "minute_items.strata_id"]),
        ForeignKeyConstraint(["bylaw_clause_id", "strata_id"], ["bylaw_clauses.id", "bylaw_clauses.strata_id"]),
        CheckConstraint("num_nonnulls(bylaw_clause_id, statute_section_id) = 1", name="one_reference"),
        enum_check("origin", ("ai_suggested", "manager_added")),
        enum_check("status", ("suggested", "confirmed", "removed")),
    )


CORRECTION_CATEGORIES = (
    "motion_text",
    "mover_seconder",
    "outcome",
    "vote_count",
    "threshold",
    "citation",
    "attendance",
    "other",
    "item_added",
    "item_deleted",
)


class Correction(Base):
    __tablename__ = "corrections"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    minute_item_id: Mapped[uuid.UUID] = uid()
    field: Mapped[str] = mapped_column(Text, nullable=False)
    old_value: Mapped[str | None] = mapped_column(Text)
    new_value: Mapped[str | None] = mapped_column(Text)
    category: Mapped[str] = mapped_column(Text, nullable=False)
    made_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    made_at: Mapped[datetime] = mapped_column(TS, nullable=False, server_default=func.now())
    __table_args__ = (
        building_fk(),
        ForeignKeyConstraint(["minute_item_id", "strata_id"], ["minute_items.id", "minute_items.strata_id"]),
        enum_check("category", CORRECTION_CATEGORIES),
        Index("ix_corrections_item_made", "minute_item_id", "made_at"),
    )


class ReviewSession(Base):
    __tablename__ = "review_sessions"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    meeting_id: Mapped[uuid.UUID] = uid()
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    activity: Mapped[str] = mapped_column(Text, nullable=False)
    started_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    last_heartbeat_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    active_seconds: Mapped[int] = mapped_column(Integer, nullable=False, server_default=text("0"))
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        building_fk(),
        meeting_fk(),
        enum_check("activity", ("setup", "review", "lookup")),
        CheckConstraint("active_seconds >= 0", name="active_non_negative"),
        Index("ix_review_sessions_meeting_user", "meeting_id", "user_id", "activity", "last_heartbeat_at"),
    )


class MeetingTimeReport(Base):
    __tablename__ = "meeting_time_reports"
    meeting_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    post_export_edit_minutes: Mapped[int | None] = mapped_column(Integer)
    dictation_prep_minutes: Mapped[int | None] = mapped_column(Integer)
    self_timed_total_minutes: Mapped[int | None] = mapped_column(Integer)
    marked_sent_on: Mapped[date | None] = mapped_column(Date)
    entered_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    entered_at: Mapped[datetime] = mapped_column(TS, nullable=False, server_default=func.now())
    updated_at: Mapped[datetime] = updated()
    row_version: Mapped[int] = row_version()
    __table_args__ = (
        building_fk(),
        meeting_fk(),
        CheckConstraint(
            "coalesce(post_export_edit_minutes, 0) >= 0 AND coalesce(dictation_prep_minutes, 0) >= 0 "
            "AND coalesce(self_timed_total_minutes, 0) >= 0",
            name="minutes_non_negative",
        ),
    )


class Approval(Base):
    __tablename__ = "approvals"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    minutes_version_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), nullable=False, unique=True)
    approved_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    approved_at: Mapped[datetime] = mapped_column(TS, nullable=False, server_default=func.now())
    content_hash: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    attestation_text_version: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        building_fk(),
        ForeignKeyConstraint(
            ["minutes_version_id", "strata_id"], ["minutes_versions.id", "minutes_versions.strata_id"]
        ),
    )


class BylawDocument(Base):
    __tablename__ = "bylaw_documents"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    kind: Mapped[str] = mapped_column(Text, nullable=False)
    filing_reference: Mapped[str | None] = mapped_column(Text)
    filed_on: Mapped[date | None] = mapped_column(Date)
    storage_key: Mapped[str] = mapped_column(Text, nullable=False, unique=True)
    sha256: Mapped[bytes] = mapped_column(LargeBinary, nullable=False)
    parser_version: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default=text("'processing'"))
    confirmed_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    confirmed_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
    row_version: Mapped[int] = row_version()
    __table_args__ = (
        building_fk(),
        UniqueConstraint("id", "strata_id"),
        UniqueConstraint("strata_id", "sha256"),
        enum_check("kind", ("bylaws", "rules")),
        enum_check("status", ("processing", "needs_confirmation", "current", "superseded", "failed")),
        CheckConstraint(
            "kind <> 'bylaws' OR status NOT IN ('current', 'superseded') OR filed_on IS NOT NULL",
            name="bylaws_filed_on",
        ),
        CheckConstraint(
            "status NOT IN ('current', 'superseded') OR (confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL)",
            name="confirmed",
        ),
        Index("uq_bylaw_current", "strata_id", "kind", unique=True, postgresql_where=text("status = 'current'")),
    )


class BylawClause(Base):
    __tablename__ = "bylaw_clauses"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    bylaw_document_id: Mapped[uuid.UUID] = uid()
    clause_number: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    page_from: Mapped[int | None] = mapped_column(Integer)
    page_to: Mapped[int | None] = mapped_column(Integer)
    position: Mapped[int] = mapped_column(Integer, nullable=False)
    embedding_model_id: Mapped[str | None] = mapped_column(Text)
    edited_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = created()
    updated_at: Mapped[datetime] = updated()
    row_version: Mapped[int] = row_version()
    __table_args__ = (
        building_fk(),
        ForeignKeyConstraint(
            ["bylaw_document_id", "strata_id"], ["bylaw_documents.id", "bylaw_documents.strata_id"]
        ),
        UniqueConstraint("id", "strata_id"),
        UniqueConstraint("bylaw_document_id", "position"),
        Index("ix_bylaw_clauses_strata_document", "strata_id", "bylaw_document_id"),
        Index(
            "ix_bylaw_clauses_fts",
            text("to_tsvector('english'::regconfig, body_text)"),
            postgresql_using="gin",
        ),
    )


class StatuteSection(Base):
    __tablename__ = "statute_sections"
    id: Mapped[uuid.UUID] = pk()
    instrument: Mapped[str] = mapped_column(Text, nullable=False)
    section_number: Mapped[str] = mapped_column(Text, nullable=False)
    heading: Mapped[str | None] = mapped_column(Text)
    body_text: Mapped[str] = mapped_column(Text, nullable=False)
    source_url: Mapped[str] = mapped_column(Text, nullable=False)
    current_to: Mapped[date] = mapped_column(Date, nullable=False)
    version_label: Mapped[str] = mapped_column(Text, nullable=False)
    superseded_at: Mapped[datetime | None] = mapped_column(TS)
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        UniqueConstraint("instrument", "section_number", "version_label"),
        enum_check("instrument", ("spa", "regulation", "standard_bylaws")),
    )


class QaInteraction(Base):
    __tablename__ = "qa_interactions"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    asked_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    question_text: Mapped[str] = mapped_column(Text, nullable=False)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    answer_text: Mapped[str | None] = mapped_column(Text)
    llm_model_id: Mapped[str] = mapped_column(Text, nullable=False)
    prompt_version: Mapped[str] = mapped_column(Text, nullable=False)
    retrieval_params_hash: Mapped[str] = mapped_column(Text, nullable=False)
    flagged_wrong: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default=text("false"))
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        building_fk(),
        UniqueConstraint("id", "strata_id"),
        enum_check("outcome", ("answered", "refused", "unavailable")),
        CheckConstraint("outcome <> 'answered' OR answer_text IS NOT NULL", name="answer_text"),
        Index("ix_qa_strata_created", "strata_id", text("created_at DESC")),
    )


class QaCitation(Base):
    __tablename__ = "qa_citations"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    qa_interaction_id: Mapped[uuid.UUID] = uid()
    bylaw_clause_id: Mapped[uuid.UUID | None] = uid(True)
    statute_section_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("statute_sections.id"))
    quoted_text: Mapped[str] = mapped_column(Text, nullable=False)
    validated: Mapped[bool] = mapped_column(Boolean, nullable=False)
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        building_fk(),
        ForeignKeyConstraint(["qa_interaction_id", "strata_id"], ["qa_interactions.id", "qa_interactions.strata_id"]),
        ForeignKeyConstraint(["bylaw_clause_id", "strata_id"], ["bylaw_clauses.id", "bylaw_clauses.strata_id"]),
        CheckConstraint("num_nonnulls(bylaw_clause_id, statute_section_id) = 1", name="one_reference"),
        CheckConstraint("validated", name="validated"),
        CheckConstraint("length(quoted_text) > 0", name="quote_present"),
    )


class BaselineMeasurement(Base):
    __tablename__ = "baseline_measurements"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brokerages.id"), nullable=False)
    strata_id: Mapped[uuid.UUID | None] = uid(True)
    user_id: Mapped[uuid.UUID] = uid()
    meeting_type: Mapped[str] = mapped_column(Text, nullable=False)
    meeting_length_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    drafting_minutes: Mapped[int] = mapped_column(Integer, nullable=False)
    method: Mapped[str] = mapped_column(Text, nullable=False)
    noted_on: Mapped[date] = mapped_column(Date, nullable=False)
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        ForeignKeyConstraint(["user_id", "brokerage_id"], ["users.id", "users.brokerage_id"]),
        building_fk(),
        enum_check("meeting_type", ("council", "general")),
        enum_check("method", ("stopwatch", "estimate")),
        CheckConstraint("meeting_length_minutes > 0 AND drafting_minutes > 0", name="positive"),
    )


class AuditEvent(Base):
    __tablename__ = "audit_events"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brokerages.id"), nullable=False)
    strata_id: Mapped[uuid.UUID | None] = uid(True)
    actor_type: Mapped[str] = mapped_column(Text, nullable=False)
    actor_id: Mapped[uuid.UUID | None] = uid(True)
    action: Mapped[str] = mapped_column(Text, nullable=False)
    target_type: Mapped[str | None] = mapped_column(Text)
    target_id: Mapped[uuid.UUID | None] = uid(True)
    outcome: Mapped[str] = mapped_column(Text, nullable=False)
    correlation_id: Mapped[uuid.UUID] = uid()
    details: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False, server_default=text("'{}'::jsonb"))
    occurred_at: Mapped[datetime] = mapped_column(TS, nullable=False, server_default=func.now())
    __table_args__ = (
        enum_check("actor_type", ("user", "operator", "system")),
        enum_check("outcome", ("ok", "denied", "failed")),
        Index("ix_audit_brokerage_time", "brokerage_id", text("occurred_at DESC")),
        Index("ix_audit_brokerage_strata_time", "brokerage_id", "strata_id", text("occurred_at DESC")),
        Index("ix_audit_denied", "actor_id", "occurred_at", postgresql_where=text("outcome = 'denied'")),
    )


class SupportGrant(Base):
    __tablename__ = "support_grants"
    id: Mapped[uuid.UUID] = pk()
    brokerage_id: Mapped[uuid.UUID] = uid()
    strata_id: Mapped[uuid.UUID] = uid()
    meeting_id: Mapped[uuid.UUID] = uid()
    operator_id: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("operators.id"))
    granted_by: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id"), nullable=False)
    reason: Mapped[str] = mapped_column(Text, nullable=False)
    expires_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    revoked_at: Mapped[datetime | None] = mapped_column(TS)
    revoked_by: Mapped[uuid.UUID | None] = mapped_column(ForeignKey("users.id"))
    created_at: Mapped[datetime] = created()
    __table_args__ = (
        building_fk(),
        meeting_fk(),
        CheckConstraint("length(btrim(reason)) > 0", name="reason"),
    )


class IdempotencyKey(Base):
    """Stored first responses. Scoped by brokerage, building and user; visible only while the
    user may still see that building, and only until ``expires_at`` (B1-001)."""

    __tablename__ = "idempotency_keys"
    key: Mapped[str] = mapped_column(Text, primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True)
    route: Mapped[str] = mapped_column(Text, primary_key=True)
    brokerage_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("brokerages.id"), nullable=False)
    strata_id: Mapped[uuid.UUID | None] = uid(True)
    request_hash: Mapped[str] = mapped_column(Text, nullable=False)
    status_code: Mapped[int] = mapped_column(Integer, nullable=False)
    response_body: Mapped[dict[str, Any]] = mapped_column(JSONB, nullable=False)
    created_at: Mapped[datetime] = created()
    expires_at: Mapped[datetime] = mapped_column(TS, nullable=False)
    __table_args__ = (
        building_fk(),
        Index("ix_idempotency_expires", "expires_at"),
    )


class WorkerHeartbeat(Base):
    __tablename__ = "worker_heartbeats"
    worker_id: Mapped[str] = mapped_column(Text, primary_key=True)
    config_fingerprint: Mapped[str] = mapped_column(Text, nullable=False)
    last_seen_at: Mapped[datetime] = mapped_column(TS, nullable=False)


TENANT_TABLES = tuple(
    t.name
    for t in Base.metadata.sorted_tables
    if "brokerage_id" in t.c or t.name in ("brokerages", "idempotency_keys", "operators")
)
BUILDING_TABLES = tuple(t.name for t in Base.metadata.sorted_tables if "strata_id" in t.c)
