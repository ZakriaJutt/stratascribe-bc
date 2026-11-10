"""Row-level security, append-only and immutability triggers, grants (schema.md steps 10-11).

Policies in words are in schema.md "Permissions and tenant boundaries". Every
tenant table has RLS ENABLED and FORCED. Without session variables every policy
is false (default deny, test I-11). The application role is a non-superuser
without BYPASSRLS; it owns nothing.

Revision ID: 0003
Revises: 0002
Create Date: 2026-11-11
"""

from __future__ import annotations

from urllib.parse import urlparse

from alembic import op

from core import config

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None

FUNCTIONS = r"""
CREATE OR REPLACE FUNCTION app_setting(name text) RETURNS text
LANGUAGE sql STABLE AS $$ SELECT nullif(current_setting(name, true), '') $$;

CREATE OR REPLACE FUNCTION app_brokerage() RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT app_setting('app.brokerage_id')::uuid $$;

CREATE OR REPLACE FUNCTION app_user_id() RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT app_setting('app.user_id')::uuid $$;

CREATE OR REPLACE FUNCTION app_role() RETURNS text
LANGUAGE sql STABLE AS $$ SELECT app_setting('app.role') $$;

CREATE OR REPLACE FUNCTION app_strata() RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT app_setting('app.strata_id')::uuid $$;

CREATE OR REPLACE FUNCTION app_operator() RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT app_setting('app.operator_id')::uuid $$;

CREATE OR REPLACE FUNCTION app_grant() RETURNS uuid
LANGUAGE sql STABLE AS $$ SELECT app_setting('app.support_grant_id')::uuid $$;

-- Building policy: managing broker of the brokerage, an assigned manager, or the
-- service actor of exactly this building. Runs with the caller's rights, so the
-- building_assignments rows it reads are themselves filtered by RLS.
CREATE OR REPLACE FUNCTION app_can_see_building(p_strata uuid) RETURNS boolean
LANGUAGE sql STABLE AS $$
  SELECT CASE app_role()
    WHEN 'managing_broker' THEN app_user_id() IS NOT NULL
    WHEN 'strata_manager' THEN EXISTS (
      SELECT 1 FROM building_assignments a
      WHERE a.strata_id = p_strata AND a.user_id = app_user_id() AND a.revoked_at IS NULL)
    WHEN 'service' THEN p_strata = app_strata()
    ELSE false
  END
$$;

-- The meeting an operator session may read: from an unexpired, unrevoked grant
-- of this brokerage, open to this operator. Null otherwise.
CREATE OR REPLACE FUNCTION app_grant_meeting() RETURNS uuid
LANGUAGE sql STABLE AS $$
  SELECT g.meeting_id FROM support_grants g
  WHERE app_role() = 'operator' AND g.id = app_grant() AND g.brokerage_id = app_brokerage()
    AND g.expires_at > now() AND g.revoked_at IS NULL
    AND (g.operator_id IS NULL OR g.operator_id = app_operator())
$$;

-- Locator for 403-versus-404 (TRD "Identity and tenancy"): returns the building of
-- a row only when the row belongs to the caller's brokerage. Reveals no content.
CREATE OR REPLACE FUNCTION app_locate(p_kind text, p_id uuid) RETURNS uuid
LANGUAGE plpgsql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE s uuid; b uuid;
BEGIN
  IF p_kind = 'building' THEN SELECT id, brokerage_id INTO s, b FROM strata_corporations WHERE id = p_id;
  ELSIF p_kind = 'meeting' THEN SELECT strata_id, brokerage_id INTO s, b FROM meetings WHERE id = p_id;
  ELSIF p_kind = 'audio_asset' THEN SELECT strata_id, brokerage_id INTO s, b FROM audio_assets WHERE id = p_id;
  ELSIF p_kind = 'minute_item' THEN SELECT strata_id, brokerage_id INTO s, b FROM minute_items WHERE id = p_id;
  ELSIF p_kind = 'minute_item_citation' THEN
    SELECT strata_id, brokerage_id INTO s, b FROM minute_item_citations WHERE id = p_id;
  ELSIF p_kind = 'bylaw_document' THEN SELECT strata_id, brokerage_id INTO s, b FROM bylaw_documents WHERE id = p_id;
  ELSIF p_kind = 'bylaw_clause' THEN SELECT strata_id, brokerage_id INTO s, b FROM bylaw_clauses WHERE id = p_id;
  ELSIF p_kind = 'question' THEN SELECT strata_id, brokerage_id INTO s, b FROM qa_interactions WHERE id = p_id;
  ELSE RAISE EXCEPTION 'unknown kind %', p_kind;
  END IF;
  IF b IS NULL OR app_brokerage() IS NULL OR b <> app_brokerage() THEN RETURN NULL; END IF;
  RETURN s;
END $$;

-- A cross-brokerage attempt is answered 404 but recorded in the OWNING brokerage's
-- audit log so its managing broker sees it (P-2). Returns nothing to the caller.
CREATE OR REPLACE FUNCTION app_record_foreign_denial(p_kind text, p_id uuid, p_actor uuid, p_corr uuid)
RETURNS void LANGUAGE plpgsql VOLATILE SECURITY DEFINER SET search_path = public, pg_temp AS $$
DECLARE s uuid; b uuid;
BEGIN
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
  VALUES (gen_random_uuid(), b, s, 'user', p_actor, 'access.denied', p_kind, p_id, 'denied', p_corr,
          jsonb_build_object('reason', 'other_brokerage'), now());
END $$;

-- Mutable rows: row_version increments on every update (If-Match, C-1).
CREATE OR REPLACE FUNCTION trg_row_version() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN NEW.row_version := OLD.row_version + 1; NEW.updated_at := now(); RETURN NEW; END $$;

CREATE OR REPLACE FUNCTION trg_append_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN RAISE EXCEPTION 'append-only table %', TG_TABLE_NAME USING ERRCODE = 'insufficient_privilege'; END $$;

CREATE OR REPLACE FUNCTION trg_authorization_supersede_only() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN RAISE EXCEPTION 'recording authorizations are never deleted'
    USING ERRCODE = 'insufficient_privilege'; END IF;
  IF OLD.superseded_by IS NOT NULL OR NEW.superseded_by IS NULL
     OR (to_jsonb(NEW) - 'superseded_by') <> (to_jsonb(OLD) - 'superseded_by') THEN
    RAISE EXCEPTION 'a recording authorization can only be superseded' USING ERRCODE = 'insufficient_privilege';
  END IF;
  RETURN NEW;
END $$;

-- Approved minutes are immutable; only approved -> superseded is allowed (I-6).
CREATE OR REPLACE FUNCTION trg_minutes_version_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP = 'DELETE' THEN
    IF OLD.status <> 'draft' THEN RAISE EXCEPTION 'approved minutes are immutable'
      USING ERRCODE = 'insufficient_privilege'; END IF;
    RETURN OLD;
  END IF;
  IF OLD.status = 'superseded' THEN
    RAISE EXCEPTION 'approved minutes are immutable' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF OLD.status = 'approved' THEN
    IF NEW.status <> 'superseded' OR (to_jsonb(NEW) - 'status' - 'row_version' - 'updated_at')
       <> (to_jsonb(OLD) - 'status' - 'row_version' - 'updated_at') THEN
      RAISE EXCEPTION 'approved minutes are immutable' USING ERRCODE = 'insufficient_privilege';
    END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION app_version_status(p_version uuid) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT status FROM minutes_versions WHERE id = p_version $$;

CREATE OR REPLACE FUNCTION trg_minute_item_immutable() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF TG_OP IN ('UPDATE', 'DELETE') AND app_version_status(OLD.minutes_version_id) IS DISTINCT FROM 'draft' THEN
    RAISE EXCEPTION 'items of approved minutes are immutable' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF TG_OP IN ('INSERT', 'UPDATE') AND app_version_status(NEW.minutes_version_id) IS DISTINCT FROM 'draft' THEN
    RAISE EXCEPTION 'items of approved minutes are immutable' USING ERRCODE = 'insufficient_privilege';
  END IF;
  IF TG_OP = 'DELETE' THEN RETURN OLD; END IF;
  RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION app_item_version_status(p_item uuid) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT v.status FROM minute_items i JOIN minutes_versions v ON v.id = i.minutes_version_id WHERE i.id = p_item $$;

CREATE OR REPLACE FUNCTION app_clause_status(p_clause uuid) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT d.status FROM bylaw_clauses c JOIN bylaw_documents d ON d.id = c.bylaw_document_id WHERE c.id = p_clause $$;

CREATE OR REPLACE FUNCTION app_clause_body(p_clause uuid) RETURNS text
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT body_text FROM bylaw_clauses WHERE id = p_clause $$;

-- Item citations: same building (composite FK) and a CURRENT confirmed document.
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
     AND strpos(app_clause_body(NEW.bylaw_clause_id), NEW.quoted_text) = 0 THEN
    RAISE EXCEPTION 'quoted text is not an exact substring of the clause' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;

-- Answer citations: exact substring of a current clause (MH-10, defence in depth for U-7).
CREATE OR REPLACE FUNCTION trg_qa_citation_check() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.bylaw_clause_id IS NOT NULL THEN
    IF app_clause_status(NEW.bylaw_clause_id) IS DISTINCT FROM 'current' THEN
      RAISE EXCEPTION 'answer cites a clause that is not current' USING ERRCODE = 'check_violation';
    END IF;
    IF strpos(app_clause_body(NEW.bylaw_clause_id), NEW.quoted_text) = 0 THEN
      RAISE EXCEPTION 'quoted text is not an exact substring of the clause' USING ERRCODE = 'check_violation';
    END IF;
  END IF;
  RETURN NEW;
END $$;

CREATE OR REPLACE FUNCTION trg_qa_answer_has_citation() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF NEW.outcome = 'answered' AND NOT EXISTS (
       SELECT 1 FROM qa_citations c WHERE c.qa_interaction_id = NEW.id AND c.validated) THEN
    RAISE EXCEPTION 'an answered question needs at least one validated citation' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NULL;
END $$;

CREATE OR REPLACE FUNCTION app_other_active_brokers(p_brokerage uuid, p_user uuid) RETURNS bigint
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT count(*) FROM users WHERE brokerage_id = p_brokerage AND id <> p_user
    AND role = 'managing_broker' AND status = 'active' $$;

CREATE OR REPLACE FUNCTION trg_last_broker() RETURNS trigger LANGUAGE plpgsql AS $$
BEGIN
  IF OLD.role = 'managing_broker' AND OLD.status = 'active'
     AND (NEW.role <> 'managing_broker' OR NEW.status <> 'active')
     AND app_other_active_brokers(OLD.brokerage_id, OLD.id) = 0 THEN
    RAISE EXCEPTION 'cannot deactivate or demote the last active managing broker' USING ERRCODE = 'check_violation';
  END IF;
  RETURN NEW;
END $$;
"""

BUILDING_TABLES_ALL = (
    "meetings",
    "recording_authorizations",
    "audio_assets",
    "transcripts",
    "transcript_segments",
    "minutes_versions",
    "minute_items",
    "minute_item_citations",
    "corrections",
    "meeting_time_reports",
    "approvals",
    "bylaw_documents",
    "bylaw_clauses",
    "qa_interactions",
    "qa_citations",
    "jobs",
)
ROW_VERSION_TABLES = (
    "brokerages",
    "users",
    "strata_corporations",
    "meetings",
    "audio_assets",
    "minutes_versions",
    "minute_items",
    "minute_item_citations",
    "meeting_time_reports",
    "bylaw_documents",
    "bylaw_clauses",
)
RLS_TABLES = (
    "brokerages",
    "users",
    "operators",
    "strata_corporations",
    "building_assignments",
    *BUILDING_TABLES_ALL,
    "review_sessions",
    "baseline_measurements",
    "audit_events",
    "support_grants",
    "idempotency_keys",
    "statute_sections",
)

TENANT = "brokerage_id = app_brokerage()"
BUILDING = f"{TENANT} AND app_can_see_building(strata_id)"
BROKER = "app_role() = 'managing_broker' AND app_user_id() IS NOT NULL"


def _policies() -> list[str]:
    p: list[str] = []
    add = p.append
    # Tenancy tables
    add("CREATE POLICY tenant_read ON brokerages FOR SELECT USING (id = app_brokerage())")
    add(f"CREATE POLICY broker_update ON brokerages FOR UPDATE USING (id = app_brokerage() AND {BROKER})")
    add(f"CREATE POLICY tenant_read ON users FOR SELECT USING ({TENANT} AND app_role() IN "
        "('managing_broker', 'strata_manager'))")
    add(f"CREATE POLICY broker_write ON users FOR INSERT WITH CHECK ({TENANT} AND {BROKER})")
    add(f"CREATE POLICY broker_update ON users FOR UPDATE USING ({TENANT} AND {BROKER})")
    add("CREATE POLICY operator_self ON operators FOR SELECT USING (app_role() = 'operator' AND id = app_operator())")
    add(f"CREATE POLICY tenant_read ON strata_corporations FOR SELECT USING ({TENANT} AND "
        "(app_role() IN ('managing_broker', 'strata_manager') OR (app_role() = 'service' AND id = app_strata())))")
    add(f"CREATE POLICY broker_insert ON strata_corporations FOR INSERT WITH CHECK ({TENANT} AND {BROKER})")
    add(f"CREATE POLICY broker_update ON strata_corporations FOR UPDATE USING ({TENANT} AND {BROKER})")
    add(f"CREATE POLICY own_or_broker ON building_assignments FOR SELECT USING ({TENANT} AND ({BROKER} "
        "OR (app_role() = 'strata_manager' AND user_id = app_user_id()) "
        "OR (app_role() = 'service' AND strata_id = app_strata())))")
    add(f"CREATE POLICY broker_insert ON building_assignments FOR INSERT WITH CHECK ({TENANT} AND {BROKER})")
    add(f"CREATE POLICY broker_update ON building_assignments FOR UPDATE USING ({TENANT} AND {BROKER})")
    # Building-owned tables
    for t in BUILDING_TABLES_ALL:
        add(f"CREATE POLICY building ON {t} FOR ALL USING ({BUILDING}) WITH CHECK ({BUILDING})")
    # Operator read under a support grant: only rows of the granted meeting (P-4)
    add(f"CREATE POLICY operator_grant ON meetings FOR SELECT USING ({TENANT} AND id = app_grant_meeting())")
    for t in ("transcripts", "minutes_versions"):
        add(f"CREATE POLICY operator_grant ON {t} FOR SELECT USING ({TENANT} AND meeting_id = app_grant_meeting())")
    add(f"CREATE POLICY operator_grant ON transcript_segments FOR SELECT USING ({TENANT} AND transcript_id IN "
        "(SELECT t.id FROM transcripts t WHERE t.meeting_id = app_grant_meeting()))")
    add(f"CREATE POLICY operator_grant ON minute_items FOR SELECT USING ({TENANT} AND minutes_version_id IN "
        "(SELECT v.id FROM minutes_versions v WHERE v.meeting_id = app_grant_meeting()))")
    # System context: job leasing and the retention sweep only (no content tables)
    add("CREATE POLICY system_jobs ON jobs FOR ALL USING (app_role() = 'system') WITH CHECK (app_role() = 'system')")
    add("CREATE POLICY system_retention ON audio_assets FOR SELECT USING (app_role() = 'system')")
    add("CREATE POLICY system_retention_update ON audio_assets FOR UPDATE USING (app_role() = 'system') "
        "WITH CHECK (app_role() = 'system')")
    # Own rows
    own = f"{TENANT} AND (user_id = app_user_id() OR {BROKER})"
    add(f"CREATE POLICY own_rows ON review_sessions FOR ALL USING ({own} AND app_can_see_building(strata_id)) "
        f"WITH CHECK ({TENANT} AND user_id = app_user_id() AND app_can_see_building(strata_id))")
    add(f"CREATE POLICY own_rows ON baseline_measurements FOR ALL USING ({own}) "
        f"WITH CHECK ({TENANT} AND user_id = app_user_id() AND (strata_id IS NULL OR app_can_see_building(strata_id)))")
    # Audit: anyone in the tenant (or the system) appends; only the managing broker reads
    add(f"CREATE POLICY append ON audit_events FOR INSERT WITH CHECK ({TENANT} OR app_role() = 'system')")
    add(f"CREATE POLICY broker_read ON audit_events FOR SELECT USING ({TENANT} AND {BROKER})")
    # Support grants: the managing broker manages them; an operator sees only its grant
    add(f"CREATE POLICY broker ON support_grants FOR ALL USING ({TENANT} AND {BROKER}) "
        f"WITH CHECK ({TENANT} AND {BROKER})")
    add(f"CREATE POLICY operator_own ON support_grants FOR SELECT USING ({TENANT} AND app_role() = 'operator' "
        "AND id = app_grant())")
    add("CREATE POLICY own_keys ON idempotency_keys FOR ALL USING (user_id = app_user_id()) "
        "WITH CHECK (user_id = app_user_id())")
    add("CREATE POLICY global_read ON statute_sections FOR SELECT USING (true)")
    return p


def _app_role() -> str:
    user = urlparse(config.settings().database_url.replace("postgresql+psycopg", "postgresql")).username
    if not user:
        raise SystemExit("DATABASE_URL must name the application role")
    return user


def upgrade() -> None:
    role = _app_role()
    op.execute(
        f"DO $$ BEGIN IF NOT EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}') THEN "
        f"RAISE EXCEPTION 'create role {role} first (make db-role)'; END IF; END $$"
    )
    op.execute(
        f"DO $$ BEGIN IF EXISTS (SELECT 1 FROM pg_roles WHERE rolname = '{role}' AND (rolsuper OR rolbypassrls)) "
        f"THEN RAISE EXCEPTION 'application role must not bypass row-level security'; END IF; END $$"
    )
    op.execute(FUNCTIONS)
    for t in RLS_TABLES:
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
    for stmt in _policies():
        op.execute(stmt)

    for t in ROW_VERSION_TABLES:
        op.execute(f"CREATE TRIGGER row_version BEFORE UPDATE ON {t} FOR EACH ROW EXECUTE FUNCTION trg_row_version()")
    for t in ("audit_events", "corrections", "approvals"):
        op.execute(
            f"CREATE TRIGGER append_only BEFORE UPDATE OR DELETE ON {t} FOR EACH ROW EXECUTE FUNCTION trg_append_only()"
        )
    op.execute("CREATE TRIGGER supersede_only BEFORE UPDATE OR DELETE ON recording_authorizations "
               "FOR EACH ROW EXECUTE FUNCTION trg_authorization_supersede_only()")
    op.execute("CREATE TRIGGER immutable BEFORE UPDATE OR DELETE ON minutes_versions "
               "FOR EACH ROW EXECUTE FUNCTION trg_minutes_version_immutable()")
    op.execute("CREATE TRIGGER immutable BEFORE INSERT OR UPDATE OR DELETE ON minute_items "
               "FOR EACH ROW EXECUTE FUNCTION trg_minute_item_immutable()")
    op.execute("CREATE TRIGGER citation_check BEFORE INSERT OR UPDATE ON minute_item_citations "
               "FOR EACH ROW EXECUTE FUNCTION trg_item_citation_check()")
    op.execute("CREATE TRIGGER citation_check BEFORE INSERT OR UPDATE ON qa_citations "
               "FOR EACH ROW EXECUTE FUNCTION trg_qa_citation_check()")
    op.execute("CREATE CONSTRAINT TRIGGER answer_has_citation AFTER INSERT OR UPDATE ON qa_interactions "
               "DEFERRABLE INITIALLY DEFERRED FOR EACH ROW EXECUTE FUNCTION trg_qa_answer_has_citation()")
    op.execute("CREATE TRIGGER last_broker BEFORE UPDATE ON users FOR EACH ROW EXECUTE FUNCTION trg_last_broker()")

    # Grants: no DDL, not the owner. Append-only tables get INSERT and SELECT only.
    op.execute(f"GRANT USAGE ON SCHEMA public TO {role}")
    op.execute(f"REVOKE ALL ON ALL TABLES IN SCHEMA public FROM {role}")
    dml = (
        "brokerages", "users", "strata_corporations", "building_assignments", "meetings", "audio_assets",
        "jobs", "transcripts", "transcript_segments", "minutes_versions", "minute_items", "minute_item_citations",
        "review_sessions", "meeting_time_reports", "bylaw_documents", "bylaw_clauses", "qa_interactions",
        "baseline_measurements", "support_grants",
    )
    for t in dml:
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON {t} TO {role}")
    op.execute(f"GRANT DELETE ON idempotency_keys, worker_heartbeats TO {role}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON recording_authorizations TO {role}")
    for t in ("audit_events", "corrections", "approvals", "qa_citations"):
        op.execute(f"GRANT SELECT, INSERT ON {t} TO {role}")
    op.execute(f"GRANT SELECT ON operators, statute_sections TO {role}")
    op.execute(f"GRANT SELECT, INSERT, UPDATE ON idempotency_keys, worker_heartbeats TO {role}")
    op.execute(f"GRANT SELECT ON alembic_version TO {role}")
    op.execute(f"GRANT EXECUTE ON ALL FUNCTIONS IN SCHEMA public TO {role}")


def downgrade() -> None:
    raise SystemExit("restore the pre-deploy dump to go back (schema.md 'Migrations')")
