"""Round-3 residual (hardening after B1-012): the database approval path enforces the item rules too.

Before this migration only `core.approval` refused approval while a motion was unreviewed, so raw SQL as
the application role inside a manager's own building could approve a version with unreviewed motions,
a different hash on the approval row, and no meeting transition. Now:

- `app_version_items_ready(version)`: every live motion and quorum item is `reviewed`, none is `blocked`,
  and no counted motion has an unresolved discrepancy (a declared outcome that differs from the final
  outcome without `recorded_as_declared`, or no final outcome at all).
- `app_approve_version` refuses immediately when the quorum item is not reviewed or the items are not ready.
- The deferred trigger on `minutes_versions` refuses the approved transition at commit when the items
  are not ready or the meeting is not `approved`.
- The deferred trigger on `approvals` refuses an approval row whose content hash differs from its
  version's content hash.

Revision ID: 0007
Revises: 0006
Create Date: 2026-11-11
"""

from __future__ import annotations

from urllib.parse import urlparse

from alembic import op

from core import config

revision = "0007"
down_revision = "0006"
branch_labels = None
depends_on = None

SQL = r"""
CREATE OR REPLACE FUNCTION app_version_items_ready(p_version uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT NOT EXISTS (
    SELECT 1 FROM minute_items i
     WHERE i.minutes_version_id = p_version AND i.deleted_at IS NULL AND i.item_type IN ('motion', 'quorum')
       AND (i.review_status <> 'reviewed'
            OR (i.item_type = 'motion' AND i.final_outcome IS NULL)
            OR (i.item_type = 'motion' AND i.outcome_method = 'counted' AND i.declared_outcome IS NOT NULL
                AND i.declared_outcome IS DISTINCT FROM i.final_outcome))) $$;

CREATE OR REPLACE FUNCTION app_version_hash(p_version uuid) RETURNS bytea
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT content_hash FROM minutes_versions WHERE id = p_version AND brokerage_id = app_brokerage() $$;

CREATE OR REPLACE FUNCTION app_meeting_state_of_version(p_version uuid) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT m.state FROM minutes_versions v JOIN meetings m ON m.id = v.meeting_id
   WHERE v.id = p_version AND v.brokerage_id = app_brokerage() $$;

CREATE OR REPLACE FUNCTION trg_approval_needs_quorum() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status = 'approved' AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'approved') THEN
    IF NOT app_version_has_reviewed_quorum(NEW.id) THEN
      RAISE EXCEPTION 'approved minutes need a reviewed quorum item' USING ERRCODE = 'check_violation';
    END IF;
    IF NOT app_version_items_ready(NEW.id) THEN
      RAISE EXCEPTION 'approved minutes need every motion reviewed and every discrepancy resolved'
        USING ERRCODE = 'check_violation';
    END IF;
    IF NOT app_version_has_approval(NEW.id) OR NEW.content_hash IS NULL THEN
      RAISE EXCEPTION 'approved minutes need an approval row and a content hash' USING ERRCODE = 'check_violation';
    END IF;
    IF app_meeting_state_of_version(NEW.id) IS DISTINCT FROM 'approved' THEN
      RAISE EXCEPTION 'approved minutes need their meeting approved' USING ERRCODE = 'check_violation';
    END IF;
  END IF;
  RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION trg_approval_row_check() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF app_version_status(NEW.minutes_version_id) IS DISTINCT FROM 'approved' THEN
    RAISE EXCEPTION 'an approval row needs its minutes version approved' USING ERRCODE = 'check_violation';
  END IF;
  IF NOT app_version_has_reviewed_quorum(NEW.minutes_version_id) THEN
    RAISE EXCEPTION 'approved minutes need a reviewed quorum item' USING ERRCODE = 'check_violation';
  END IF;
  IF NOT app_version_items_ready(NEW.minutes_version_id) THEN
    RAISE EXCEPTION 'approved minutes need every motion reviewed and every discrepancy resolved'
      USING ERRCODE = 'check_violation';
  END IF;
  IF app_version_hash(NEW.minutes_version_id) IS DISTINCT FROM NEW.content_hash THEN
    RAISE EXCEPTION 'the approval row hash must equal the approved version hash' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION app_approve_version(p_version uuid, p_hash bytea) RETURNS void
LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE v minutes_versions%ROWTYPE;
BEGIN
  SELECT * INTO v FROM minutes_versions WHERE id = p_version FOR UPDATE;
  IF v.id IS NULL OR app_brokerage() IS NULL OR v.brokerage_id <> app_brokerage()
     OR app_role() NOT IN ('managing_broker', 'strata_manager') OR NOT app_can_see_building(v.strata_id) THEN
    RAISE EXCEPTION 'not found' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF v.status <> 'draft' OR p_hash IS NULL THEN
    RAISE EXCEPTION 'only a draft can be approved' USING ERRCODE = 'check_violation';
  END IF;
  IF NOT app_version_has_reviewed_quorum(p_version) THEN
    RAISE EXCEPTION 'approved minutes need a reviewed quorum item' USING ERRCODE = 'check_violation';
  END IF;
  IF NOT app_version_items_ready(p_version) THEN
    RAISE EXCEPTION 'approved minutes need every motion reviewed and every discrepancy resolved'
      USING ERRCODE = 'check_violation';
  END IF;
  IF v.reopened_from IS NOT NULL THEN
    UPDATE minutes_versions SET status = 'superseded' WHERE id = v.reopened_from AND status = 'approved';
  END IF;
  UPDATE minutes_versions SET status = 'approved', content_hash = p_hash WHERE id = p_version;
END $$;
"""


def upgrade() -> None:
    role = urlparse(config.settings().database_url.replace("postgresql+psycopg", "postgresql")).username
    op.execute(SQL)
    # The trigger functions run with the caller's rights, so the application role keeps EXECUTE; nobody else.
    for fn in ("app_version_items_ready(uuid)", "app_version_hash(uuid)", "app_meeting_state_of_version(uuid)"):
        op.execute(f"REVOKE ALL ON FUNCTION {fn} FROM PUBLIC")
        op.execute(f"GRANT EXECUTE ON FUNCTION {fn} TO {role}")


def downgrade() -> None:
    raise SystemExit("restore the pre-deploy dump to go back (schema.md 'Migrations')")
