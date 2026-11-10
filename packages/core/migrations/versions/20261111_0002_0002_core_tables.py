"""core tables

Revision ID: 0002
Revises: 0001
Create Date: 2026-11-11
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = '0002'
down_revision = '0001'
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table('brokerages',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('legal_name', sa.Text(), nullable=False),
    sa.Column('licence_label', sa.Text(), nullable=True),
    sa.Column('privacy_contact_name', sa.Text(), nullable=False),
    sa.Column('privacy_contact_email', sa.Text(), nullable=False),
    sa.Column('allow_express_consent_basis', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('audio_retention_days_after_approval', sa.Integer(), server_default=sa.text('14'), nullable=False),
    sa.Column('audio_max_days_after_upload', sa.Integer(), server_default=sa.text('60'), nullable=False),
    sa.Column('transcript_retention_days_after_approval', sa.Integer(), server_default=sa.text('90'), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'active'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint("status IN ('active', 'closing', 'closed')", name=op.f('ck_brokerages_status_values')),
    sa.CheckConstraint('audio_max_days_after_upload BETWEEN 7 AND 90', name=op.f('ck_brokerages_audio_max_range')),
    sa.CheckConstraint('audio_retention_days_after_approval BETWEEN 1 AND 60', name=op.f('ck_brokerages_audio_retention_range')),
    sa.CheckConstraint('transcript_retention_days_after_approval BETWEEN 1 AND 365', name=op.f('ck_brokerages_transcript_range')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_brokerages'))
    )
    op.create_table('idempotency_keys',
    sa.Column('key', sa.Text(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('route', sa.Text(), nullable=False),
    sa.Column('request_hash', sa.Text(), nullable=False),
    sa.Column('status_code', sa.Integer(), nullable=False),
    sa.Column('response_body', postgresql.JSONB(astext_type=sa.Text()), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.PrimaryKeyConstraint('key', 'user_id', 'route', name=op.f('pk_idempotency_keys'))
    )
    op.create_table('operators',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('email', postgresql.CITEXT(), nullable=False),
    sa.Column('full_name', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'active'"), nullable=False),
    sa.Column('totp_secret_encrypted', sa.LargeBinary(), nullable=False),
    sa.Column('last_sign_in_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("status IN ('active', 'deactivated')", name=op.f('ck_operators_status_values')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_operators')),
    sa.UniqueConstraint('email', name=op.f('uq_operators_email'))
    )
    op.create_table('statute_sections',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('instrument', sa.Text(), nullable=False),
    sa.Column('section_number', sa.Text(), nullable=False),
    sa.Column('heading', sa.Text(), nullable=True),
    sa.Column('body_text', sa.Text(), nullable=False),
    sa.Column('source_url', sa.Text(), nullable=False),
    sa.Column('current_to', sa.Date(), nullable=False),
    sa.Column('version_label', sa.Text(), nullable=False),
    sa.Column('superseded_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("instrument IN ('spa', 'regulation', 'standard_bylaws')", name=op.f('ck_statute_sections_instrument_values')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_statute_sections')),
    sa.UniqueConstraint('instrument', 'section_number', 'version_label', name=op.f('uq_statute_sections_instrument_section_number_version_label'))
    )
    op.create_table('worker_heartbeats',
    sa.Column('worker_id', sa.Text(), nullable=False),
    sa.Column('config_fingerprint', sa.Text(), nullable=False),
    sa.Column('last_seen_at', sa.DateTime(timezone=True), nullable=False),
    sa.PrimaryKeyConstraint('worker_id', name=op.f('pk_worker_heartbeats'))
    )
    op.create_table('audit_events',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=True),
    sa.Column('actor_type', sa.Text(), nullable=False),
    sa.Column('actor_id', sa.UUID(), nullable=True),
    sa.Column('action', sa.Text(), nullable=False),
    sa.Column('target_type', sa.Text(), nullable=True),
    sa.Column('target_id', sa.UUID(), nullable=True),
    sa.Column('outcome', sa.Text(), nullable=False),
    sa.Column('correlation_id', sa.UUID(), nullable=False),
    sa.Column('details', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text("'{}'::jsonb"), nullable=False),
    sa.Column('occurred_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("actor_type IN ('user', 'operator', 'system')", name=op.f('ck_audit_events_actor_type_values')),
    sa.CheckConstraint("outcome IN ('ok', 'denied', 'failed')", name=op.f('ck_audit_events_outcome_values')),
    sa.ForeignKeyConstraint(['brokerage_id'], ['brokerages.id'], name=op.f('fk_audit_events_brokerage_id_brokerages')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audit_events'))
    )
    op.create_index('ix_audit_brokerage_strata_time', 'audit_events', ['brokerage_id', 'strata_id', sa.literal_column('occurred_at DESC')], unique=False)
    op.create_index('ix_audit_brokerage_time', 'audit_events', ['brokerage_id', sa.literal_column('occurred_at DESC')], unique=False)
    op.create_index('ix_audit_denied', 'audit_events', ['actor_id', 'occurred_at'], unique=False, postgresql_where=sa.text("outcome = 'denied'"))
    op.create_table('strata_corporations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('name', sa.Text(), nullable=False),
    sa.Column('strata_plan_number', sa.Text(), nullable=False),
    sa.Column('strata_lot_count', sa.Integer(), nullable=True),
    sa.Column('owner_count', sa.Integer(), nullable=True),
    sa.Column('eligible_votes_total', sa.Integer(), nullable=True),
    sa.Column('council_size', sa.Integer(), nullable=True),
    sa.Column('general_quorum_rule', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text('\'{"type": "act_default"}\'::jsonb'), nullable=False),
    sa.Column('council_quorum_rule', postgresql.JSONB(astext_type=sa.Text()), server_default=sa.text('\'{"type": "standard_bylaw_16"}\'::jsonb'), nullable=False),
    sa.Column('standard_bylaws_declared_by', sa.UUID(), nullable=True),
    sa.Column('standard_bylaws_declared_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('status', sa.Text(), server_default=sa.text("'active'"), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint("status IN ('active', 'deleting', 'deleted')", name=op.f('ck_strata_corporations_status_values')),
    sa.CheckConstraint('council_size IS NULL OR council_size > 0', name=op.f('ck_strata_corporations_council_positive')),
    sa.CheckConstraint('owner_count IS NULL OR owner_count > 0', name=op.f('ck_strata_corporations_owners_positive')),
    sa.CheckConstraint('strata_lot_count IS NULL OR strata_lot_count > 0', name=op.f('ck_strata_corporations_lots_positive')),
    sa.ForeignKeyConstraint(['brokerage_id'], ['brokerages.id'], name=op.f('fk_strata_corporations_brokerage_id_brokerages')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_strata_corporations')),
    sa.UniqueConstraint('id', 'brokerage_id', name=op.f('uq_strata_corporations_id_brokerage_id'))
    )
    op.create_index('uq_strata_plan_per_brokerage', 'strata_corporations', ['brokerage_id', sa.literal_column('upper(strata_plan_number)')], unique=True)
    op.create_table('users',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('email', postgresql.CITEXT(), nullable=False),
    sa.Column('full_name', sa.Text(), nullable=False),
    sa.Column('role', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'invited'"), nullable=False),
    sa.Column('last_sign_in_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('totp_secret_encrypted', sa.LargeBinary(), nullable=True),
    sa.Column('totp_enrolled_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint("role IN ('managing_broker', 'strata_manager')", name=op.f('ck_users_role_values')),
    sa.CheckConstraint("status IN ('invited', 'active', 'deactivated')", name=op.f('ck_users_status_values')),
    sa.ForeignKeyConstraint(['brokerage_id'], ['brokerages.id'], name=op.f('fk_users_brokerage_id_brokerages')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_users')),
    sa.UniqueConstraint('email', name=op.f('uq_users_email')),
    sa.UniqueConstraint('id', 'brokerage_id', name=op.f('uq_users_id_brokerage_id'))
    )
    op.create_table('baseline_measurements',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=True),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('meeting_type', sa.Text(), nullable=False),
    sa.Column('meeting_length_minutes', sa.Integer(), nullable=False),
    sa.Column('drafting_minutes', sa.Integer(), nullable=False),
    sa.Column('method', sa.Text(), nullable=False),
    sa.Column('noted_on', sa.Date(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("meeting_type IN ('council', 'general')", name=op.f('ck_baseline_measurements_meeting_type_values')),
    sa.CheckConstraint("method IN ('stopwatch', 'estimate')", name=op.f('ck_baseline_measurements_method_values')),
    sa.CheckConstraint('meeting_length_minutes > 0 AND drafting_minutes > 0', name=op.f('ck_baseline_measurements_positive')),
    sa.ForeignKeyConstraint(['brokerage_id'], ['brokerages.id'], name=op.f('fk_baseline_measurements_brokerage_id_brokerages')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_baseline_measurements_strata_id_brokerage_id_strata_corporations')),
    sa.ForeignKeyConstraint(['user_id', 'brokerage_id'], ['users.id', 'users.brokerage_id'], name=op.f('fk_baseline_measurements_user_id_brokerage_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_baseline_measurements'))
    )
    op.create_table('building_assignments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('assigned_by', sa.UUID(), nullable=False),
    sa.Column('assigned_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['assigned_by'], ['users.id'], name=op.f('fk_building_assignments_assigned_by_users')),
    sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], name=op.f('fk_building_assignments_revoked_by_users')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_building_assignments_strata_id_brokerage_id_strata_corporations')),
    sa.ForeignKeyConstraint(['user_id', 'brokerage_id'], ['users.id', 'users.brokerage_id'], name=op.f('fk_building_assignments_user_id_brokerage_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_building_assignments'))
    )
    op.create_index('ix_assignment_user_active', 'building_assignments', ['user_id'], unique=False, postgresql_where=sa.text('revoked_at IS NULL'))
    op.create_index('uq_assignment_active', 'building_assignments', ['strata_id', 'user_id'], unique=True, postgresql_where=sa.text('revoked_at IS NULL'))
    op.create_table('bylaw_documents',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('filing_reference', sa.Text(), nullable=True),
    sa.Column('filed_on', sa.Date(), nullable=True),
    sa.Column('storage_key', sa.Text(), nullable=False),
    sa.Column('sha256', sa.LargeBinary(), nullable=False),
    sa.Column('parser_version', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'processing'"), nullable=False),
    sa.Column('confirmed_by', sa.UUID(), nullable=True),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint("kind <> 'bylaws' OR status NOT IN ('current', 'superseded') OR filed_on IS NOT NULL", name=op.f('ck_bylaw_documents_bylaws_filed_on')),
    sa.CheckConstraint("kind IN ('bylaws', 'rules')", name=op.f('ck_bylaw_documents_kind_values')),
    sa.CheckConstraint("status IN ('processing', 'needs_confirmation', 'current', 'superseded', 'failed')", name=op.f('ck_bylaw_documents_status_values')),
    sa.CheckConstraint("status NOT IN ('current', 'superseded') OR (confirmed_by IS NOT NULL AND confirmed_at IS NOT NULL)", name=op.f('ck_bylaw_documents_confirmed')),
    sa.ForeignKeyConstraint(['confirmed_by'], ['users.id'], name=op.f('fk_bylaw_documents_confirmed_by_users')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_bylaw_documents_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bylaw_documents')),
    sa.UniqueConstraint('id', 'strata_id', name=op.f('uq_bylaw_documents_id_strata_id')),
    sa.UniqueConstraint('storage_key', name=op.f('uq_bylaw_documents_storage_key')),
    sa.UniqueConstraint('strata_id', 'sha256', name=op.f('uq_bylaw_documents_strata_id_sha256'))
    )
    op.create_index('uq_bylaw_current', 'bylaw_documents', ['strata_id', 'kind'], unique=True, postgresql_where=sa.text("status = 'current'"))
    op.create_table('meetings',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('meeting_type', sa.Text(), nullable=False),
    sa.Column('held_on', sa.Date(), nullable=False),
    sa.Column('format', sa.Text(), nullable=False),
    sa.Column('source_type', sa.Text(), nullable=False),
    sa.Column('state', sa.Text(), server_default=sa.text("'setup'"), nullable=False),
    sa.Column('state_version', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_by', sa.UUID(), nullable=False),
    sa.Column('sequence', sa.SmallInteger(), server_default=sa.text('1'), nullable=False),
    sa.Column('length_minutes', sa.Integer(), nullable=True),
    sa.Column('reconvened_after_adjournment', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('ended_at_local', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint("format IN ('in_person', 'electronic', 'hybrid')", name=op.f('ck_meetings_format_values')),
    sa.CheckConstraint("meeting_type IN ('council', 'agm', 'sgm')", name=op.f('ck_meetings_meeting_type_values')),
    sa.CheckConstraint("source_type IN ('recording', 'dictated_notes', 'not_recorded')", name=op.f('ck_meetings_source_type_values')),
    sa.CheckConstraint("state IN ('setup', 'authorized', 'not_recorded', 'uploading', 'uploaded', 'transcribing', 'failed_transcription', 'drafting', 'failed_drafting', 'ready_for_review', 'in_review', 'approved')", name=op.f('ck_meetings_state_values')),
    sa.CheckConstraint('sequence IN (1, 2)', name=op.f('ck_meetings_sequence_values')),
    sa.ForeignKeyConstraint(['created_by'], ['users.id'], name=op.f('fk_meetings_created_by_users')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_meetings_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_meetings')),
    sa.UniqueConstraint('id', 'strata_id', name=op.f('uq_meetings_id_strata_id')),
    sa.UniqueConstraint('strata_id', 'meeting_type', 'held_on', 'sequence', name=op.f('uq_meetings_strata_id_meeting_type_held_on_sequence'))
    )
    op.create_index('ix_meetings_review_queue', 'meetings', ['brokerage_id', 'state'], unique=False, postgresql_where=sa.text("state IN ('ready_for_review', 'in_review')"))
    op.create_index('ix_meetings_strata_held', 'meetings', ['strata_id', sa.literal_column('held_on DESC')], unique=False)
    op.create_table('qa_interactions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('asked_by', sa.UUID(), nullable=False),
    sa.Column('question_text', sa.Text(), nullable=False),
    sa.Column('outcome', sa.Text(), nullable=False),
    sa.Column('answer_text', sa.Text(), nullable=True),
    sa.Column('llm_model_id', sa.Text(), nullable=False),
    sa.Column('prompt_version', sa.Text(), nullable=False),
    sa.Column('retrieval_params_hash', sa.Text(), nullable=False),
    sa.Column('flagged_wrong', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("outcome <> 'answered' OR answer_text IS NOT NULL", name=op.f('ck_qa_interactions_answer_text')),
    sa.CheckConstraint("outcome IN ('answered', 'refused', 'unavailable')", name=op.f('ck_qa_interactions_outcome_values')),
    sa.ForeignKeyConstraint(['asked_by'], ['users.id'], name=op.f('fk_qa_interactions_asked_by_users')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_qa_interactions_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_qa_interactions')),
    sa.UniqueConstraint('id', 'strata_id', name=op.f('uq_qa_interactions_id_strata_id'))
    )
    op.create_index('ix_qa_strata_created', 'qa_interactions', ['strata_id', sa.literal_column('created_at DESC')], unique=False)
    op.create_table('bylaw_clauses',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('bylaw_document_id', sa.UUID(), nullable=False),
    sa.Column('clause_number', sa.Text(), nullable=False),
    sa.Column('heading', sa.Text(), nullable=True),
    sa.Column('body_text', sa.Text(), nullable=False),
    sa.Column('page_from', sa.Integer(), nullable=True),
    sa.Column('page_to', sa.Integer(), nullable=True),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('embedding_model_id', sa.Text(), nullable=True),
    sa.Column('edited_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.ForeignKeyConstraint(['bylaw_document_id', 'strata_id'], ['bylaw_documents.id', 'bylaw_documents.strata_id'], name=op.f('fk_bylaw_clauses_bylaw_document_id_strata_id_bylaw_documents')),
    sa.ForeignKeyConstraint(['edited_by'], ['users.id'], name=op.f('fk_bylaw_clauses_edited_by_users')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_bylaw_clauses_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_bylaw_clauses')),
    sa.UniqueConstraint('bylaw_document_id', 'position', name=op.f('uq_bylaw_clauses_bylaw_document_id_position')),
    sa.UniqueConstraint('id', 'strata_id', name=op.f('uq_bylaw_clauses_id_strata_id'))
    )
    op.create_index('ix_bylaw_clauses_fts', 'bylaw_clauses', [sa.literal_column("to_tsvector('english'::regconfig, body_text)")], unique=False, postgresql_using='gin')
    op.create_index('ix_bylaw_clauses_strata_document', 'bylaw_clauses', ['strata_id', 'bylaw_document_id'], unique=False)
    op.create_table('jobs',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=True),
    sa.Column('strata_id', sa.UUID(), nullable=True),
    sa.Column('meeting_id', sa.UUID(), nullable=True),
    sa.Column('bylaw_document_id', sa.UUID(), nullable=True),
    sa.Column('kind', sa.Text(), nullable=False),
    sa.Column('idempotency_key', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'queued'"), nullable=False),
    sa.Column('attempt', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('max_attempts', sa.Integer(), server_default=sa.text('3'), nullable=False),
    sa.Column('run_after', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('leased_until', sa.DateTime(timezone=True), nullable=True),
    sa.Column('leased_by', sa.Text(), nullable=True),
    sa.Column('correlation_id', sa.UUID(), nullable=False),
    sa.Column('error_code', sa.Text(), nullable=True),
    sa.Column('result_ref', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("kind IN ('retention_sweep', 'reconcile') OR (brokerage_id IS NOT NULL AND strata_id IS NOT NULL)", name=op.f('ck_jobs_tenant_scope')),
    sa.CheckConstraint("kind IN ('transcribe', 'draft_minutes', 'index_bylaws', 'export', 'retention_sweep', 'reconcile')", name=op.f('ck_jobs_kind_values')),
    sa.CheckConstraint("status IN ('queued', 'leased', 'succeeded', 'failed')", name=op.f('ck_jobs_status_values')),
    sa.ForeignKeyConstraint(['meeting_id', 'strata_id'], ['meetings.id', 'meetings.strata_id'], name=op.f('fk_jobs_meeting_id_strata_id_meetings')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_jobs_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_jobs')),
    sa.UniqueConstraint('kind', 'idempotency_key', name=op.f('uq_jobs_kind_idempotency_key'))
    )
    op.create_index('ix_jobs_lease', 'jobs', ['status', 'leased_until'], unique=False, postgresql_where=sa.text("status IN ('queued', 'leased')"))
    op.create_table('meeting_time_reports',
    sa.Column('meeting_id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('post_export_edit_minutes', sa.Integer(), nullable=True),
    sa.Column('dictation_prep_minutes', sa.Integer(), nullable=True),
    sa.Column('self_timed_total_minutes', sa.Integer(), nullable=True),
    sa.Column('marked_sent_on', sa.Date(), nullable=True),
    sa.Column('entered_by', sa.UUID(), nullable=False),
    sa.Column('entered_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint('coalesce(post_export_edit_minutes, 0) >= 0 AND coalesce(dictation_prep_minutes, 0) >= 0 AND coalesce(self_timed_total_minutes, 0) >= 0', name=op.f('ck_meeting_time_reports_minutes_non_negative')),
    sa.ForeignKeyConstraint(['entered_by'], ['users.id'], name=op.f('fk_meeting_time_reports_entered_by_users')),
    sa.ForeignKeyConstraint(['meeting_id', 'strata_id'], ['meetings.id', 'meetings.strata_id'], name=op.f('fk_meeting_time_reports_meeting_id_strata_id_meetings')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_meeting_time_reports_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('meeting_id', name=op.f('pk_meeting_time_reports'))
    )
    op.create_table('minutes_versions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('meeting_id', sa.UUID(), nullable=False),
    sa.Column('version', sa.Integer(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'draft'"), nullable=False),
    sa.Column('transcript_id', sa.UUID(), nullable=True),
    sa.Column('llm_model_id', sa.Text(), nullable=True),
    sa.Column('prompt_version', sa.Text(), nullable=True),
    sa.Column('rules_version', sa.Text(), nullable=False),
    sa.Column('template_version', sa.Text(), nullable=True),
    sa.Column('reopened_from', sa.UUID(), nullable=True),
    sa.Column('reopen_reason', sa.Text(), nullable=True),
    sa.Column('content_hash', sa.LargeBinary(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint("status IN ('draft', 'approved', 'superseded')", name=op.f('ck_minutes_versions_status_values')),
    sa.CheckConstraint('reopened_from IS NULL OR reopen_reason IS NOT NULL', name=op.f('ck_minutes_versions_reopen_reason')),
    sa.ForeignKeyConstraint(['meeting_id', 'strata_id'], ['meetings.id', 'meetings.strata_id'], name=op.f('fk_minutes_versions_meeting_id_strata_id_meetings')),
    sa.ForeignKeyConstraint(['reopened_from'], ['minutes_versions.id'], name=op.f('fk_minutes_versions_reopened_from_minutes_versions')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_minutes_versions_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_minutes_versions')),
    sa.UniqueConstraint('id', 'strata_id', name=op.f('uq_minutes_versions_id_strata_id')),
    sa.UniqueConstraint('meeting_id', 'version', name=op.f('uq_minutes_versions_meeting_id_version'))
    )
    op.create_index('uq_minutes_one_draft', 'minutes_versions', ['meeting_id'], unique=True, postgresql_where=sa.text("status = 'draft'"))
    op.create_table('review_sessions',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('meeting_id', sa.UUID(), nullable=False),
    sa.Column('user_id', sa.UUID(), nullable=False),
    sa.Column('activity', sa.Text(), nullable=False),
    sa.Column('started_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('last_heartbeat_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('active_seconds', sa.Integer(), server_default=sa.text('0'), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("activity IN ('setup', 'review', 'lookup')", name=op.f('ck_review_sessions_activity_values')),
    sa.CheckConstraint('active_seconds >= 0', name=op.f('ck_review_sessions_active_non_negative')),
    sa.ForeignKeyConstraint(['meeting_id', 'strata_id'], ['meetings.id', 'meetings.strata_id'], name=op.f('fk_review_sessions_meeting_id_strata_id_meetings')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_review_sessions_strata_id_brokerage_id_strata_corporations')),
    sa.ForeignKeyConstraint(['user_id'], ['users.id'], name=op.f('fk_review_sessions_user_id_users')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_review_sessions'))
    )
    op.create_index('ix_review_sessions_meeting_user', 'review_sessions', ['meeting_id', 'user_id', 'activity', 'last_heartbeat_at'], unique=False)
    op.create_table('support_grants',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('meeting_id', sa.UUID(), nullable=False),
    sa.Column('operator_id', sa.UUID(), nullable=True),
    sa.Column('granted_by', sa.UUID(), nullable=False),
    sa.Column('reason', sa.Text(), nullable=False),
    sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False),
    sa.Column('revoked_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('revoked_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('length(btrim(reason)) > 0', name=op.f('ck_support_grants_reason')),
    sa.ForeignKeyConstraint(['granted_by'], ['users.id'], name=op.f('fk_support_grants_granted_by_users')),
    sa.ForeignKeyConstraint(['meeting_id', 'strata_id'], ['meetings.id', 'meetings.strata_id'], name=op.f('fk_support_grants_meeting_id_strata_id_meetings')),
    sa.ForeignKeyConstraint(['operator_id'], ['operators.id'], name=op.f('fk_support_grants_operator_id_operators')),
    sa.ForeignKeyConstraint(['revoked_by'], ['users.id'], name=op.f('fk_support_grants_revoked_by_users')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_support_grants_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_support_grants'))
    )
    op.create_table('transcripts',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('meeting_id', sa.UUID(), nullable=False),
    sa.Column('asr_model_id', sa.Text(), nullable=False),
    sa.Column('asr_params_hash', sa.Text(), nullable=False),
    sa.Column('language', sa.Text(), server_default=sa.text("'en'"), nullable=False),
    sa.Column('delete_after', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['meeting_id', 'strata_id'], ['meetings.id', 'meetings.strata_id'], name=op.f('fk_transcripts_meeting_id_strata_id_meetings')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_transcripts_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_transcripts')),
    sa.UniqueConstraint('id', 'strata_id', name=op.f('uq_transcripts_id_strata_id')),
    sa.UniqueConstraint('meeting_id', name=op.f('uq_transcripts_meeting_id'))
    )
    op.create_table('approvals',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('minutes_version_id', sa.UUID(), nullable=False),
    sa.Column('approved_by', sa.UUID(), nullable=False),
    sa.Column('approved_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('content_hash', sa.LargeBinary(), nullable=False),
    sa.Column('attestation_text_version', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.ForeignKeyConstraint(['approved_by'], ['users.id'], name=op.f('fk_approvals_approved_by_users')),
    sa.ForeignKeyConstraint(['minutes_version_id', 'strata_id'], ['minutes_versions.id', 'minutes_versions.strata_id'], name=op.f('fk_approvals_minutes_version_id_strata_id_minutes_versions')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_approvals_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_approvals')),
    sa.UniqueConstraint('minutes_version_id', name=op.f('uq_approvals_minutes_version_id'))
    )
    op.create_table('minute_items',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('minutes_version_id', sa.UUID(), nullable=False),
    sa.Column('position', sa.Integer(), nullable=False),
    sa.Column('item_type', sa.Text(), nullable=False),
    sa.Column('body_text', sa.Text(), server_default=sa.text("''"), nullable=False),
    sa.Column('mover', sa.Text(), nullable=True),
    sa.Column('seconder', sa.Text(), nullable=True),
    sa.Column('outcome_method', sa.Text(), nullable=True),
    sa.Column('declared_outcome', sa.Text(), nullable=True),
    sa.Column('outcome_attested_by', sa.UUID(), nullable=True),
    sa.Column('outcome_attested_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('threshold', sa.Text(), nullable=True),
    sa.Column('votes_for', sa.Integer(), nullable=True),
    sa.Column('votes_against', sa.Integer(), nullable=True),
    sa.Column('votes_abstained', sa.Integer(), nullable=True),
    sa.Column('eligible_votes', sa.Integer(), nullable=True),
    sa.Column('members_present', sa.Integer(), nullable=True),
    sa.Column('casting_vote', sa.Text(), nullable=True),
    sa.Column('computed_result', sa.Text(), nullable=True),
    sa.Column('computed_formula', sa.Text(), nullable=True),
    sa.Column('rules_version', sa.Text(), nullable=True),
    sa.Column('discrepancy_resolution', sa.Text(), nullable=True),
    sa.Column('discrepancy_note', sa.Text(), nullable=True),
    sa.Column('final_outcome', sa.Text(), sa.Computed("CASE WHEN outcome_method = 'declared' AND outcome_attested_at IS NOT NULL THEN declared_outcome WHEN outcome_method = 'counted' AND discrepancy_resolution = 'recorded_as_declared' THEN declared_outcome WHEN outcome_method = 'counted' THEN CASE WHEN computed_result IN ('carried', 'defeated') THEN computed_result WHEN computed_result = 'tie' AND casting_vote = 'used_for' THEN 'carried' WHEN computed_result = 'tie' AND casting_vote IN ('used_against', 'not_used') THEN 'defeated' END END", persisted=True), nullable=True),
    sa.Column('spoken_outcome', sa.Text(), nullable=True),
    sa.Column('ai_suggestion', postgresql.JSONB(astext_type=sa.Text()), nullable=True),
    sa.Column('source_segment_ids', postgresql.ARRAY(sa.UUID()), server_default=sa.text("'{}'"), nullable=False),
    sa.Column('origin', sa.Text(), nullable=False),
    sa.Column('review_status', sa.Text(), server_default=sa.text("'needs_review'"), nullable=False),
    sa.Column('blocked_reason', sa.Text(), nullable=True),
    sa.Column('sensitive_flag', sa.Boolean(), server_default=sa.text('false'), nullable=False),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('delete_reason', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint("casting_vote IS NULL OR (casting_vote IN ('not_used', 'used_for', 'used_against') AND computed_result = 'tie')", name=op.f('ck_minute_items_casting_vote')),
    sa.CheckConstraint("computed_result IS NULL OR computed_result IN ('carried', 'defeated', 'tie', 'no_result')", name=op.f('ck_minute_items_computed')),
    sa.CheckConstraint("declared_outcome IS NULL OR declared_outcome IN ('carried', 'defeated')", name=op.f('ck_minute_items_declared')),
    sa.CheckConstraint("discrepancy_resolution IS DISTINCT FROM 'recorded_as_declared' OR (discrepancy_note IS NOT NULL AND length(btrim(discrepancy_note)) > 0)", name=op.f('ck_minute_items_resolution_note')),
    sa.CheckConstraint("discrepancy_resolution IS NULL OR discrepancy_resolution IN ('counts_corrected', 'threshold_corrected', 'recorded_as_declared')", name=op.f('ck_minute_items_resolution')),
    sa.CheckConstraint("item_type <> 'motion' OR review_status <> 'reviewed' OR (final_outcome IS NOT NULL AND ((outcome_method = 'declared' AND declared_outcome IS NOT NULL AND outcome_attested_by IS NOT NULL AND outcome_attested_at IS NOT NULL) OR (outcome_method = 'counted' AND threshold IS NOT NULL AND votes_for IS NOT NULL AND votes_against IS NOT NULL AND (computed_result IN ('carried', 'defeated') OR (computed_result = 'tie' AND casting_vote IS NOT NULL)) AND (declared_outcome IS NULL OR declared_outcome = (CASE WHEN computed_result IN ('carried', 'defeated') THEN computed_result WHEN computed_result = 'tie' AND casting_vote = 'used_for' THEN 'carried' WHEN computed_result = 'tie' AND casting_vote IN ('used_against', 'not_used') THEN 'defeated' END) OR discrepancy_resolution = 'recorded_as_declared'))))", name=op.f('ck_minute_items_reviewed_motion_complete')),
    sa.CheckConstraint("item_type IN ('attendance', 'quorum', 'call_to_order', 'motion', 'discussion', 'adjournment', 'other')", name=op.f('ck_minute_items_item_type_values')),
    sa.CheckConstraint("origin IN ('ai', 'manager_added')", name=op.f('ck_minute_items_origin_values')),
    sa.CheckConstraint("outcome_method = 'counted' OR computed_result IS NULL", name=op.f('ck_minute_items_declared_has_no_computed')),
    sa.CheckConstraint("outcome_method IS NULL OR outcome_method IN ('declared', 'counted')", name=op.f('ck_minute_items_method')),
    sa.CheckConstraint("review_status IN ('needs_review', 'reviewed', 'blocked')", name=op.f('ck_minute_items_review_status_values')),
    sa.CheckConstraint("threshold IS NULL OR threshold IN ('majority', 'three_quarter', 'eighty_percent', 'unanimous', 'council_majority')", name=op.f('ck_minute_items_threshold')),
    sa.CheckConstraint('coalesce(votes_for, 0) >= 0 AND coalesce(votes_against, 0) >= 0 AND coalesce(votes_abstained, 0) >= 0 AND coalesce(eligible_votes, 0) >= 0 AND coalesce(members_present, 0) >= 0', name=op.f('ck_minute_items_counts_non_negative')),
    sa.ForeignKeyConstraint(['minutes_version_id', 'strata_id'], ['minutes_versions.id', 'minutes_versions.strata_id'], name=op.f('fk_minute_items_minutes_version_id_strata_id_minutes_versions')),
    sa.ForeignKeyConstraint(['outcome_attested_by'], ['users.id'], name=op.f('fk_minute_items_outcome_attested_by_users')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_minute_items_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_minute_items')),
    sa.UniqueConstraint('id', 'strata_id', name=op.f('uq_minute_items_id_strata_id'))
    )
    op.create_index('ix_minute_items_version_position', 'minute_items', ['minutes_version_id', 'position'], unique=False)
    op.create_table('qa_citations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('qa_interaction_id', sa.UUID(), nullable=False),
    sa.Column('bylaw_clause_id', sa.UUID(), nullable=True),
    sa.Column('statute_section_id', sa.UUID(), nullable=True),
    sa.Column('quoted_text', sa.Text(), nullable=False),
    sa.Column('validated', sa.Boolean(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('length(quoted_text) > 0', name=op.f('ck_qa_citations_quote_present')),
    sa.CheckConstraint('num_nonnulls(bylaw_clause_id, statute_section_id) = 1', name=op.f('ck_qa_citations_one_reference')),
    sa.CheckConstraint('validated', name=op.f('ck_qa_citations_validated')),
    sa.ForeignKeyConstraint(['bylaw_clause_id', 'strata_id'], ['bylaw_clauses.id', 'bylaw_clauses.strata_id'], name=op.f('fk_qa_citations_bylaw_clause_id_strata_id_bylaw_clauses')),
    sa.ForeignKeyConstraint(['qa_interaction_id', 'strata_id'], ['qa_interactions.id', 'qa_interactions.strata_id'], name=op.f('fk_qa_citations_qa_interaction_id_strata_id_qa_interactions')),
    sa.ForeignKeyConstraint(['statute_section_id'], ['statute_sections.id'], name=op.f('fk_qa_citations_statute_section_id_statute_sections')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_qa_citations_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_qa_citations'))
    )
    op.create_table('recording_authorizations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('meeting_id', sa.UUID(), nullable=False),
    sa.Column('basis', sa.Text(), nullable=False),
    sa.Column('bylaw_clause_id', sa.UUID(), nullable=True),
    sa.Column('bylaw_reference_text', sa.Text(), nullable=True),
    sa.Column('notice_text_version', sa.Text(), nullable=False),
    sa.Column('attested_by', sa.UUID(), nullable=False),
    sa.Column('attested_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('superseded_by', sa.UUID(), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("basis <> 'bylaw' OR bylaw_clause_id IS NOT NULL OR bylaw_reference_text IS NOT NULL", name=op.f('ck_recording_authorizations_bylaw_basis_reference')),
    sa.CheckConstraint("basis IN ('bylaw', 'express_consent_all', 'dictated_notes')", name=op.f('ck_recording_authorizations_basis_values')),
    sa.ForeignKeyConstraint(['attested_by'], ['users.id'], name=op.f('fk_recording_authorizations_attested_by_users')),
    sa.ForeignKeyConstraint(['bylaw_clause_id', 'strata_id'], ['bylaw_clauses.id', 'bylaw_clauses.strata_id'], name=op.f('fk_recording_authorizations_bylaw_clause_id_strata_id_bylaw_clauses')),
    sa.ForeignKeyConstraint(['meeting_id', 'strata_id'], ['meetings.id', 'meetings.strata_id'], name=op.f('fk_recording_authorizations_meeting_id_strata_id_meetings')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_recording_authorizations_strata_id_brokerage_id_strata_corporations')),
    sa.ForeignKeyConstraint(['superseded_by'], ['recording_authorizations.id'], name=op.f('fk_recording_authorizations_superseded_by_recording_authorizations'), initially='DEFERRED', deferrable=True),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_recording_authorizations')),
    sa.UniqueConstraint('id', 'strata_id', name=op.f('uq_recording_authorizations_id_strata_id'))
    )
    op.create_index('uq_authorization_current', 'recording_authorizations', ['meeting_id'], unique=True, postgresql_where=sa.text('superseded_by IS NULL'))
    op.create_table('transcript_segments',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('transcript_id', sa.UUID(), nullable=False),
    sa.Column('seq', sa.Integer(), nullable=False),
    sa.Column('audio_asset_id', sa.UUID(), nullable=True),
    sa.Column('start_ms', sa.Integer(), nullable=False),
    sa.Column('end_ms', sa.Integer(), nullable=False),
    sa.Column('speaker_label', sa.Text(), nullable=False),
    sa.Column('speaker_name', sa.Text(), nullable=True),
    sa.Column('text', sa.Text(), nullable=False),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint('end_ms >= start_ms AND start_ms >= 0', name=op.f('ck_transcript_segments_times')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_transcript_segments_strata_id_brokerage_id_strata_corporations')),
    sa.ForeignKeyConstraint(['transcript_id', 'strata_id'], ['transcripts.id', 'transcripts.strata_id'], name=op.f('fk_transcript_segments_transcript_id_strata_id_transcripts')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_transcript_segments')),
    sa.UniqueConstraint('transcript_id', 'seq', name=op.f('uq_transcript_segments_transcript_id_seq'))
    )
    op.create_table('audio_assets',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('meeting_id', sa.UUID(), nullable=False),
    sa.Column('part_number', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.Column('storage_key', sa.Text(), nullable=False),
    sa.Column('sha256', sa.LargeBinary(), nullable=False),
    sa.Column('byte_size', sa.BigInteger(), nullable=False),
    sa.Column('received_bytes', sa.BigInteger(), server_default=sa.text('0'), nullable=False),
    sa.Column('duration_seconds', sa.Integer(), nullable=True),
    sa.Column('upload_state', sa.Text(), server_default=sa.text("'receiving'"), nullable=False),
    sa.Column('authorization_id', sa.UUID(), nullable=False),
    sa.Column('delete_after', sa.DateTime(timezone=True), nullable=True),
    sa.Column('deleted_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint("upload_state IN ('receiving', 'complete', 'failed')", name=op.f('ck_audio_assets_upload_state_values')),
    sa.CheckConstraint('byte_size > 0 AND received_bytes BETWEEN 0 AND byte_size', name=op.f('ck_audio_assets_sizes')),
    sa.CheckConstraint('part_number BETWEEN 1 AND 10', name=op.f('ck_audio_assets_part_range')),
    sa.ForeignKeyConstraint(['authorization_id', 'strata_id'], ['recording_authorizations.id', 'recording_authorizations.strata_id'], name=op.f('fk_audio_assets_authorization_id_strata_id_recording_authorizations')),
    sa.ForeignKeyConstraint(['meeting_id', 'strata_id'], ['meetings.id', 'meetings.strata_id'], name=op.f('fk_audio_assets_meeting_id_strata_id_meetings')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_audio_assets_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_audio_assets')),
    sa.UniqueConstraint('id', 'strata_id', name=op.f('uq_audio_assets_id_strata_id')),
    sa.UniqueConstraint('meeting_id', 'sha256', name=op.f('uq_audio_assets_meeting_id_sha256')),
    sa.UniqueConstraint('storage_key', name=op.f('uq_audio_assets_storage_key'))
    )
    op.create_index('ix_audio_delete_after', 'audio_assets', ['delete_after'], unique=False, postgresql_where=sa.text('deleted_at IS NULL'))
    op.create_table('corrections',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('minute_item_id', sa.UUID(), nullable=False),
    sa.Column('field', sa.Text(), nullable=False),
    sa.Column('old_value', sa.Text(), nullable=True),
    sa.Column('new_value', sa.Text(), nullable=True),
    sa.Column('category', sa.Text(), nullable=False),
    sa.Column('made_by', sa.UUID(), nullable=False),
    sa.Column('made_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.CheckConstraint("category IN ('motion_text', 'mover_seconder', 'outcome', 'vote_count', 'threshold', 'citation', 'attendance', 'other', 'item_added', 'item_deleted')", name=op.f('ck_corrections_category_values')),
    sa.ForeignKeyConstraint(['made_by'], ['users.id'], name=op.f('fk_corrections_made_by_users')),
    sa.ForeignKeyConstraint(['minute_item_id', 'strata_id'], ['minute_items.id', 'minute_items.strata_id'], name=op.f('fk_corrections_minute_item_id_strata_id_minute_items')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_corrections_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_corrections'))
    )
    op.create_index('ix_corrections_item_made', 'corrections', ['minute_item_id', 'made_at'], unique=False)
    op.create_table('minute_item_citations',
    sa.Column('id', sa.UUID(), nullable=False),
    sa.Column('brokerage_id', sa.UUID(), nullable=False),
    sa.Column('strata_id', sa.UUID(), nullable=False),
    sa.Column('minute_item_id', sa.UUID(), nullable=False),
    sa.Column('bylaw_clause_id', sa.UUID(), nullable=True),
    sa.Column('statute_section_id', sa.UUID(), nullable=True),
    sa.Column('quoted_text', sa.Text(), nullable=True),
    sa.Column('origin', sa.Text(), nullable=False),
    sa.Column('status', sa.Text(), server_default=sa.text("'suggested'"), nullable=False),
    sa.Column('confirmed_by', sa.UUID(), nullable=True),
    sa.Column('confirmed_at', sa.DateTime(timezone=True), nullable=True),
    sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
    sa.Column('row_version', sa.Integer(), server_default=sa.text('1'), nullable=False),
    sa.CheckConstraint("origin IN ('ai_suggested', 'manager_added')", name=op.f('ck_minute_item_citations_origin_values')),
    sa.CheckConstraint("status IN ('suggested', 'confirmed', 'removed')", name=op.f('ck_minute_item_citations_status_values')),
    sa.CheckConstraint('num_nonnulls(bylaw_clause_id, statute_section_id) = 1', name=op.f('ck_minute_item_citations_one_reference')),
    sa.ForeignKeyConstraint(['bylaw_clause_id', 'strata_id'], ['bylaw_clauses.id', 'bylaw_clauses.strata_id'], name=op.f('fk_minute_item_citations_bylaw_clause_id_strata_id_bylaw_clauses')),
    sa.ForeignKeyConstraint(['confirmed_by'], ['users.id'], name=op.f('fk_minute_item_citations_confirmed_by_users')),
    sa.ForeignKeyConstraint(['minute_item_id', 'strata_id'], ['minute_items.id', 'minute_items.strata_id'], name=op.f('fk_minute_item_citations_minute_item_id_strata_id_minute_items')),
    sa.ForeignKeyConstraint(['statute_section_id'], ['statute_sections.id'], name=op.f('fk_minute_item_citations_statute_section_id_statute_sections')),
    sa.ForeignKeyConstraint(['strata_id', 'brokerage_id'], ['strata_corporations.id', 'strata_corporations.brokerage_id'], name=op.f('fk_minute_item_citations_strata_id_brokerage_id_strata_corporations')),
    sa.PrimaryKeyConstraint('id', name=op.f('pk_minute_item_citations'))
    )


def downgrade() -> None:
    op.drop_table('minute_item_citations')
    op.drop_index('ix_corrections_item_made', table_name='corrections')
    op.drop_table('corrections')
    op.drop_index('ix_audio_delete_after', table_name='audio_assets', postgresql_where=sa.text('deleted_at IS NULL'))
    op.drop_table('audio_assets')
    op.drop_table('transcript_segments')
    op.drop_index('uq_authorization_current', table_name='recording_authorizations', postgresql_where=sa.text('superseded_by IS NULL'))
    op.drop_table('recording_authorizations')
    op.drop_table('qa_citations')
    op.drop_index('ix_minute_items_version_position', table_name='minute_items')
    op.drop_table('minute_items')
    op.drop_table('approvals')
    op.drop_table('transcripts')
    op.drop_table('support_grants')
    op.drop_index('ix_review_sessions_meeting_user', table_name='review_sessions')
    op.drop_table('review_sessions')
    op.drop_index('uq_minutes_one_draft', table_name='minutes_versions', postgresql_where=sa.text("status = 'draft'"))
    op.drop_table('minutes_versions')
    op.drop_table('meeting_time_reports')
    op.drop_index('ix_jobs_lease', table_name='jobs', postgresql_where=sa.text("status IN ('queued', 'leased')"))
    op.drop_table('jobs')
    op.drop_index('ix_bylaw_clauses_strata_document', table_name='bylaw_clauses')
    op.drop_index('ix_bylaw_clauses_fts', table_name='bylaw_clauses', postgresql_using='gin')
    op.drop_table('bylaw_clauses')
    op.drop_index('ix_qa_strata_created', table_name='qa_interactions')
    op.drop_table('qa_interactions')
    op.drop_index('ix_meetings_strata_held', table_name='meetings')
    op.drop_index('ix_meetings_review_queue', table_name='meetings', postgresql_where=sa.text("state IN ('ready_for_review', 'in_review')"))
    op.drop_table('meetings')
    op.drop_index('uq_bylaw_current', table_name='bylaw_documents', postgresql_where=sa.text("status = 'current'"))
    op.drop_table('bylaw_documents')
    op.drop_index('uq_assignment_active', table_name='building_assignments', postgresql_where=sa.text('revoked_at IS NULL'))
    op.drop_index('ix_assignment_user_active', table_name='building_assignments', postgresql_where=sa.text('revoked_at IS NULL'))
    op.drop_table('building_assignments')
    op.drop_table('baseline_measurements')
    op.drop_table('users')
    op.drop_index('uq_strata_plan_per_brokerage', table_name='strata_corporations')
    op.drop_table('strata_corporations')
    op.drop_index('ix_audit_denied', table_name='audit_events', postgresql_where=sa.text("outcome = 'denied'"))
    op.drop_index('ix_audit_brokerage_time', table_name='audit_events')
    op.drop_index('ix_audit_brokerage_strata_time', table_name='audit_events')
    op.drop_table('audit_events')
    op.drop_table('worker_heartbeats')
    op.drop_table('statute_sections')
    op.drop_table('operators')
    op.drop_table('idempotency_keys')
    op.drop_table('brokerages')
