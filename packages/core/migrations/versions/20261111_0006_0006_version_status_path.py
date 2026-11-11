"""Review round 2, B1-012: a minutes version is born a draft and becomes approved only one way.

- BEFORE INSERT trigger: a version can only be created with status 'draft' and no content hash.
- The application role loses UPDATE on `minutes_versions` and INSERT on its `status` column (a non-null
  `content_hash` on INSERT is refused by the trigger; the ORM sends the column as NULL); the only path to 'approved' (and to 'superseded') is the SECURITY DEFINER
  function `app_approve_version`, which checks brokerage and building access itself.
- Deferred constraint triggers, on INSERT as well as UPDATE: an approved version needs a reviewed
  quorum item and an approval row; an approval row needs its version approved, with a reviewed
  quorum item, at commit.

Revision ID: 0006
Revises: 0005
Create Date: 2026-11-11
"""

from __future__ import annotations

from urllib.parse import urlparse

from alembic import op

from core import config

revision = "0006"
down_revision = "0005"
branch_labels = None
depends_on = None

SQL = r"""
CREATE OR REPLACE FUNCTION trg_version_born_draft() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status IS DISTINCT FROM 'draft' OR NEW.content_hash IS NOT NULL THEN
    RAISE EXCEPTION 'a minutes version is created as a draft; approval goes through app_approve_version'
      USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION app_version_has_approval(p_version uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT EXISTS (SELECT 1 FROM approvals a WHERE a.minutes_version_id = p_version) $$;

CREATE OR REPLACE FUNCTION trg_approval_needs_quorum() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status = 'approved' AND (TG_OP = 'INSERT' OR OLD.status IS DISTINCT FROM 'approved') THEN
    IF NOT app_version_has_reviewed_quorum(NEW.id) THEN
      RAISE EXCEPTION 'approved minutes need a reviewed quorum item' USING ERRCODE = 'check_violation';
    END IF;
    IF NOT app_version_has_approval(NEW.id) OR NEW.content_hash IS NULL THEN
      RAISE EXCEPTION 'approved minutes need an approval row and a content hash' USING ERRCODE = 'check_violation';
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
  RETURN NULL;
END $$;

-- The only path to 'approved'. Checks access itself because it runs with the owner's rights.
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
  IF v.reopened_from IS NOT NULL THEN
    UPDATE minutes_versions SET status = 'superseded' WHERE id = v.reopened_from AND status = 'approved';
  END IF;
  UPDATE minutes_versions SET status = 'approved', content_hash = p_hash WHERE id = p_version;
END $$;
"""

INSERT_COLUMNS = (
    "id, brokerage_id, strata_id, meeting_id, version, transcript_id, llm_model_id, prompt_version, "
    "rules_version, template_version, reopened_from, reopen_reason, content_hash, created_at, updated_at, row_version"
)


def upgrade() -> None:
    role = urlparse(config.settings().database_url.replace("postgresql+psycopg", "postgresql")).username
    op.execute(SQL)
    op.execute("CREATE TRIGGER born_draft BEFORE INSERT ON minutes_versions "
               "FOR EACH ROW EXECUTE FUNCTION trg_version_born_draft()")
    op.execute("DROP TRIGGER approval_needs_quorum ON minutes_versions")
    op.execute("CREATE CONSTRAINT TRIGGER approval_needs_quorum AFTER INSERT OR UPDATE ON minutes_versions "
               "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION trg_approval_needs_quorum()")
    op.execute("CREATE CONSTRAINT TRIGGER approval_row_check AFTER INSERT ON approvals "
               "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION trg_approval_row_check()")
    op.execute(f"REVOKE INSERT, UPDATE ON minutes_versions FROM {role}")
    op.execute(f"GRANT INSERT ({INSERT_COLUMNS}) ON minutes_versions TO {role}")
    op.execute("REVOKE ALL ON FUNCTION app_approve_version(uuid, bytea) FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION app_approve_version(uuid, bytea) TO {role}")


def downgrade() -> None:
    raise SystemExit("restore the pre-deploy dump to go back (schema.md 'Migrations')")
