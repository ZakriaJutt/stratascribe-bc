"""Lead ruling after review round 1: approved minutes always carry a reviewed quorum item.

Adds the explicit "not recorded" basis and statement, and a deferred constraint
trigger that refuses approving a minutes version without a reviewed quorum item.

Revision ID: 0005
Revises: 0004
Create Date: 2026-11-11
"""

from __future__ import annotations

from alembic import op

from core.models import QUORUM_BASIS_SQL, QUORUM_STATEMENT_SQL, REVIEWED_QUORUM_SQL

revision = "0005"
down_revision = "0004"
branch_labels = None
depends_on = None

FUNCTION = r"""
CREATE OR REPLACE FUNCTION app_version_has_reviewed_quorum(p_version uuid) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT EXISTS (SELECT 1 FROM minute_items i WHERE i.minutes_version_id = p_version
                   AND i.item_type = 'quorum' AND i.deleted_at IS NULL AND i.review_status = 'reviewed')
     AND NOT EXISTS (SELECT 1 FROM minute_items i WHERE i.minutes_version_id = p_version
                   AND i.item_type = 'quorum' AND i.deleted_at IS NULL AND i.review_status <> 'reviewed') $$;

CREATE OR REPLACE FUNCTION trg_approval_needs_quorum() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.status = 'approved' AND OLD.status = 'draft' AND NOT app_version_has_reviewed_quorum(NEW.id) THEN
    RAISE EXCEPTION 'approved minutes need a reviewed quorum item' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NULL;
END $$;
"""


def upgrade() -> None:
    for name, sql in (("quorum_basis", QUORUM_BASIS_SQL), ("quorum_statement", QUORUM_STATEMENT_SQL),
                      ("reviewed_quorum_complete", REVIEWED_QUORUM_SQL)):
        op.drop_constraint(op.f(f"ck_minute_items_{name}"), "minute_items", type_="check")
        op.create_check_constraint(op.f(f"ck_minute_items_{name}"), "minute_items", sql)
    op.execute(FUNCTION)
    op.execute("CREATE CONSTRAINT TRIGGER approval_needs_quorum AFTER UPDATE ON minutes_versions "
               "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION trg_approval_needs_quorum()")


def downgrade() -> None:
    raise SystemExit("restore the pre-deploy dump to go back (schema.md 'Migrations')")
