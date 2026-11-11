"""Review round 1 fixes: B1-001 (idempotency scope and expiry), B1-002 (job key scope),
B1-003/B1-005 (NULL-safe and show-of-cards CHECKs), B1-004 (meaningful quotes), B1-006 (quorum
attendance), B1-008 (system context column limit), B1-009 (denial actor from the session)

Revision ID: 0004
Revises: 0003
Create Date: 2026-11-11
Generated: 2026-11-11 05:00:57.072679
"""

from __future__ import annotations

import sqlalchemy as sa
from alembic import op

from core.models import (
    DECLARED_NO_COUNTS_SQL,
    QUORUM_FIELDS_SQL,
    REVIEWED_MOTION_SQL,
    REVIEWED_QUORUM_SQL,
)

revision = '0004'
down_revision = '0003'
branch_labels = None
depends_on = None



SQL_FUNCTIONS = r"""
-- B1-009: the actor is the session's user, never a parameter.
DROP FUNCTION IF EXISTS app_record_foreign_denial(text, uuid, uuid, uuid);
CREATE OR REPLACE FUNCTION app_record_foreign_denial(p_kind text, p_id uuid, p_corr uuid)
RETURNS void LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE s uuid; b uuid;
BEGIN
  IF app_user_id() IS NULL OR app_brokerage() IS NULL THEN RETURN; END IF;
  IF p_kind = 'building' THEN SELECT id, brokerage_id INTO s, b FROM strata_corporations WHERE id = p_id;
  ELSIF p_kind = 'meeting' THEN SELECT strata_id, brokerage_id INTO s, b FROM meetings WHERE id = p_id;
  ELSIF p_kind = 'audio_asset' THEN SELECT strata_id, brokerage_id INTO s, b FROM audio_assets WHERE id = p_id;
  ELSIF p_kind = 'minute_item' THEN SELECT strata_id, brokerage_id INTO s, b FROM minute_items WHERE id = p_id;
  ELSIF p_kind = 'minute_item_citation' THEN
    SELECT strata_id, brokerage_id INTO s, b FROM minute_item_citations WHERE id = p_id;
  ELSIF p_kind = 'bylaw_document' THEN SELECT strata_id, brokerage_id INTO s, b FROM bylaw_documents WHERE id = p_id;
  ELSIF p_kind = 'bylaw_clause' THEN SELECT strata_id, brokerage_id INTO s, b FROM bylaw_clauses WHERE id = p_id;
  ELSIF p_kind = 'question' THEN SELECT strata_id, brokerage_id INTO s, b FROM qa_interactions WHERE id = p_id;
  ELSE RETURN;
  END IF;
  IF b IS NULL OR b = app_brokerage() THEN RETURN; END IF;
  INSERT INTO audit_events (id, brokerage_id, strata_id, actor_type, actor_id, action, target_type, target_id,
                            outcome, correlation_id, details, occurred_at)
  VALUES (gen_random_uuid(), b, s, 'user', app_user_id(), 'access.denied', p_kind, p_id, 'denied', p_corr,
          jsonb_build_object('reason', 'other_brokerage'), now());
END $$;

-- B1-001: expired stored responses are purged without giving any context read access to them.
CREATE OR REPLACE FUNCTION app_purge_idempotency() RETURNS bigint
LANGUAGE sql VOLATILE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  WITH d AS (DELETE FROM idempotency_keys WHERE expires_at <= now() RETURNING 1) SELECT count(*) FROM d $$;

-- B1-004: a citation quote must be a meaningful verbatim span: at least 20 characters and 4 words,
-- found in the clause text on word boundaries.
CREATE OR REPLACE FUNCTION app_quote_ok(p_body text, p_quote text) RETURNS boolean
LANGUAGE sql IMMUTABLE AS $$
  SELECT p_body IS NOT NULL AND p_quote IS NOT NULL
    AND length(btrim(p_quote)) >= 20
    AND coalesce(array_length(regexp_split_to_array(btrim(p_quote), '\s+'), 1), 0) >= 4
    AND p_body ~ ('(^|[^[:alnum:]])' || regexp_replace(p_quote, '([.^$*+?()\[\]{}|\\-])', '\\\1', 'g')
                  || '($|[^[:alnum:]])')
$$;

CREATE OR REPLACE FUNCTION trg_item_citation_check() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF app_item_version_status(NEW.minute_item_id) IS DISTINCT FROM 'draft' THEN
    RAISE EXCEPTION 'items of approved minutes are immutable' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF NEW.status <> 'removed' AND NEW.bylaw_clause_id IS NOT NULL
     AND app_clause_status(NEW.bylaw_clause_id) IS DISTINCT FROM 'current' THEN
    RAISE EXCEPTION 'citation must point to a clause of the current confirmed document'
      USING ERRCODE = 'check_violation';
  END IF;
  IF NEW.quoted_text IS NOT NULL AND NEW.bylaw_clause_id IS NOT NULL
     AND NOT app_quote_ok(app_clause_body(NEW.bylaw_clause_id), NEW.quoted_text) THEN
    RAISE EXCEPTION 'quoted text is not a meaningful verbatim span of the clause' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION trg_qa_citation_check() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.bylaw_clause_id IS NOT NULL THEN
    IF app_clause_status(NEW.bylaw_clause_id) IS DISTINCT FROM 'current' THEN
      RAISE EXCEPTION 'answer cites a clause that is not current' USING ERRCODE = 'check_violation';
    END IF;
    IF NOT app_quote_ok(app_clause_body(NEW.bylaw_clause_id), NEW.quoted_text) THEN
      RAISE EXCEPTION 'quoted text is not a meaningful verbatim span of the clause' USING ERRCODE = 'check_violation';
    END IF;
  END IF;
  RETURN NEW;
END $$;

-- B1-008: the system context may change only the retention and upload-state columns of audio rows.
CREATE OR REPLACE FUNCTION trg_audio_system_columns() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF app_role() = 'system' AND (to_jsonb(NEW) - 'delete_after' - 'deleted_at' - 'upload_state' - 'received_bytes'
      - 'updated_at' - 'row_version') <> (to_jsonb(OLD) - 'delete_after' - 'deleted_at' - 'upload_state'
      - 'received_bytes' - 'updated_at' - 'row_version') THEN
    RAISE EXCEPTION 'system context may change only retention and upload-state columns'
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN NEW;
END $$;
"""

OWN_KEYS = (
    "user_id = app_user_id() AND brokerage_id = app_brokerage() AND expires_at > now() "
    "AND (strata_id IS NULL OR app_can_see_building(strata_id))"
)


def _role() -> str:
    from urllib.parse import urlparse

    from core import config

    user = urlparse(config.settings().database_url.replace("postgresql+psycopg", "postgresql")).username
    if not user:
        raise SystemExit("DATABASE_URL must name the application role")
    return user


def upgrade() -> None:
    # Stored responses are a 24-hour cache; existing rows lack the new scope columns.
    op.execute("DELETE FROM idempotency_keys")
    op.add_column('idempotency_keys', sa.Column('brokerage_id', sa.UUID(), nullable=False))
    op.add_column('idempotency_keys', sa.Column('strata_id', sa.UUID(), nullable=True))
    op.add_column('idempotency_keys', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=False))
    op.create_index('ix_idempotency_expires', 'idempotency_keys', ['expires_at'], unique=False)
    op.create_foreign_key(op.f('fk_idempotency_keys_brokerage_id_brokerages'), 'idempotency_keys', 'brokerages', ['brokerage_id'], ['id'])
    op.create_foreign_key(op.f('fk_idempotency_keys_strata_id_brokerage_id_strata_corporations'), 'idempotency_keys', 'strata_corporations', ['strata_id', 'brokerage_id'], ['id', 'brokerage_id'])
    op.drop_constraint(op.f('uq_jobs_kind_idempotency_key'), 'jobs', type_='unique')
    op.create_unique_constraint('uq_jobs_scope_key', 'jobs', ['brokerage_id', 'strata_id', 'meeting_id', 'kind', 'idempotency_key'], postgresql_nulls_not_distinct=True)
    op.add_column('minute_items', sa.Column('quorum_basis', sa.Text(), nullable=True))
    op.add_column('minute_items', sa.Column('quorum_statement', sa.Text(), nullable=True))
    op.add_column('minute_items', sa.Column('present_count', sa.Integer(), nullable=True))
    op.add_column('minute_items', sa.Column('eligible_count', sa.Integer(), nullable=True))
    op.add_column('minute_items', sa.Column('required_count', sa.Integer(), nullable=True))
    op.add_column('minute_items', sa.Column('quorum_met', sa.Boolean(), nullable=True))
    op.add_column('minute_items', sa.Column('quorum_rule', sa.Text(), nullable=True))
    op.add_column('minute_items', sa.Column('quorum_formula', sa.Text(), nullable=True))
    op.add_column('minute_items', sa.Column('quorum_attested_by', sa.UUID(), nullable=True))
    op.add_column('minute_items', sa.Column('quorum_attested_at', sa.DateTime(timezone=True), nullable=True))
    op.create_foreign_key(op.f('fk_minute_items_quorum_attested_by_users'), 'minute_items', 'users', ['quorum_attested_by'], ['id'])


    for name in ("reviewed_motion_complete", "declared_has_no_computed", "casting_vote"):
        op.drop_constraint(op.f(f"ck_minute_items_{name}"), "minute_items", type_="check")
    op.create_check_constraint(op.f("ck_minute_items_reviewed_motion_complete"), "minute_items", REVIEWED_MOTION_SQL)
    op.create_check_constraint(
        op.f("ck_minute_items_declared_has_no_computed"), "minute_items",
        "coalesce(outcome_method, '') = 'counted' OR computed_result IS NULL",
    )
    op.create_check_constraint(
        op.f("ck_minute_items_casting_vote"), "minute_items",
        "casting_vote IS NULL OR (casting_vote IN ('not_used', 'used_for', 'used_against') "
        "AND coalesce(computed_result, '') = 'tie')",
    )
    # Existing declared motions must not keep counts (B1-005): clear before the CHECK is added.
    op.execute(
        "UPDATE minute_items SET threshold = NULL, votes_for = NULL, votes_against = NULL, votes_abstained = NULL, "
        "eligible_votes = NULL, members_present = NULL, casting_vote = NULL, discrepancy_resolution = NULL "
        "WHERE coalesce(outcome_method, '') <> 'counted' AND app_version_status(minutes_version_id) = 'draft'"
    )
    op.create_check_constraint(op.f("ck_minute_items_declared_no_counts"), "minute_items", DECLARED_NO_COUNTS_SQL)
    op.create_check_constraint(op.f("ck_minute_items_quorum_fields_only_on_quorum"), "minute_items",
                               QUORUM_FIELDS_SQL)
    op.create_check_constraint(op.f("ck_minute_items_reviewed_quorum_complete"), "minute_items",
                               REVIEWED_QUORUM_SQL)
    op.create_check_constraint(op.f("ck_minute_items_quorum_basis"), "minute_items",
                               "quorum_basis IS NULL OR quorum_basis IN ('counted', 'declared')")
    op.create_check_constraint(
        op.f("ck_minute_items_quorum_statement"), "minute_items",
        "quorum_statement IS NULL OR quorum_statement IN ('established', 'not_established')",
    )
    op.create_check_constraint(
        op.f("ck_minute_items_quorum_counts_non_negative"), "minute_items",
        "coalesce(present_count, 0) >= 0 AND coalesce(eligible_count, 0) >= 0 AND coalesce(required_count, 0) >= 0",
    )

    role = _role()
    op.execute(SQL_FUNCTIONS)
    op.execute("DROP POLICY own_keys ON idempotency_keys")
    op.execute(f"CREATE POLICY own_keys ON idempotency_keys FOR ALL USING ({OWN_KEYS}) WITH CHECK ({OWN_KEYS})")
    op.execute("CREATE TRIGGER system_columns BEFORE UPDATE ON audio_assets "
               "FOR EACH ROW EXECUTE FUNCTION trg_audio_system_columns()")
    op.execute("REVOKE ALL ON FUNCTION app_purge_idempotency() FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {role}")


def downgrade() -> None:
    raise SystemExit("restore the pre-deploy dump to go back (schema.md 'Migrations')")
