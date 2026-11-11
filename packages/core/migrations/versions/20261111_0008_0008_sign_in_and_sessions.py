"""B2 (T-2.2.2): emailed sign-in links, server-side web sessions in PostgreSQL, invitations.

- `sign_in_links`: HMACs of the link token and the requesting browser's nonce, 10-minute expiry,
  single use, at most 5 wrong authenticator codes.
- `web_sessions`: HMAC of the cookie token, idle and absolute expiry, ended_at and reason. Replaces
  the B1 Redis session store.
- `users`: `totp_last_used_step` (code replay guard), `invited_by`, `invited_at`.
- The sign-in context (`app.role = 'auth'`, no brokerage) may read and update `users`, and use
  `sign_in_links` and `web_sessions`; it sees no building table (`app_can_see_building` is false for it).
  Users read and end their own sessions; the managing broker ends a member's sessions.
- `app_email_in_use(email)`: true when any user or operator has the address (generic refusal of an
  invitation for an address of another brokerage, without disclosing which).
- Audit events may be appended from the sign-in context for the user's own brokerage.

Revision ID: 0008
Revises: 0007
Create Date: 2026-11-11
"""

from __future__ import annotations

from urllib.parse import urlparse

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

from core import config

revision = "0008"
down_revision = "0007"
branch_labels = None
depends_on = None

AUTH = "app_role() = 'auth'"
TENANT = "brokerage_id = app_brokerage()"
BROKER = "app_role() = 'managing_broker' AND app_user_id() IS NOT NULL"
END_REASONS = ("signed_out", "idle", "absolute", "deactivated", "role_changed", "authenticator_reset",
               "user_inactive")


def upgrade() -> None:
    role = urlparse(config.settings().database_url.replace("postgresql+psycopg", "postgresql")).username
    ts = sa.DateTime(timezone=True)
    op.add_column("users", sa.Column("totp_last_used_step", sa.BigInteger(), nullable=True))
    op.add_column("users", sa.Column("invited_by", postgresql.UUID(as_uuid=True), nullable=True))
    op.add_column("users", sa.Column("invited_at", ts, nullable=True))
    op.create_foreign_key(op.f("fk_users_invited_by_users"), "users", "users", ["invited_by"], ["id"])

    op.create_table(
        "sign_in_links",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("nonce_hash", sa.LargeBinary(), nullable=False),
        sa.Column("next_path", sa.Text(), nullable=True),
        sa.Column("created_at", ts, nullable=False),
        sa.Column("expires_at", ts, nullable=False),
        sa.Column("consumed_at", ts, nullable=True),
        sa.Column("failed_codes", sa.SmallInteger(), server_default=sa.text("0"), nullable=False),
        sa.CheckConstraint("failed_codes BETWEEN 0 AND 5", name=op.f("ck_sign_in_links_failed_codes_range")),
        sa.CheckConstraint("expires_at > created_at", name=op.f("ck_sign_in_links_expiry_after_creation")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], name=op.f("fk_sign_in_links_user_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_sign_in_links")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_sign_in_links_token_hash")),
    )
    op.create_index("ix_sign_in_links_user_id", "sign_in_links", ["user_id"])

    allowed = ", ".join(f"'{r}'" for r in END_REASONS)
    op.create_table(
        "web_sessions",
        sa.Column("id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("token_hash", sa.LargeBinary(), nullable=False),
        sa.Column("brokerage_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("user_id", postgresql.UUID(as_uuid=True), nullable=False),
        sa.Column("role", sa.Text(), nullable=False),
        sa.Column("created_at", ts, nullable=False),
        sa.Column("last_seen_at", ts, nullable=False),
        sa.Column("absolute_expires_at", ts, nullable=False),
        sa.Column("ended_at", ts, nullable=True),
        sa.Column("end_reason", sa.Text(), nullable=True),
        sa.CheckConstraint("role IN ('managing_broker', 'strata_manager')", name=op.f("ck_web_sessions_role_values")),
        sa.CheckConstraint(f"end_reason IN ({allowed})", name=op.f("ck_web_sessions_end_reason_values")),
        sa.ForeignKeyConstraint(["brokerage_id"], ["brokerages.id"],
                                name=op.f("fk_web_sessions_brokerage_id_brokerages")),
        sa.ForeignKeyConstraint(["user_id", "brokerage_id"], ["users.id", "users.brokerage_id"],
                                name=op.f("fk_web_sessions_user_id_brokerage_id_users")),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_web_sessions")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_web_sessions_token_hash")),
    )
    op.create_index("ix_web_sessions_user_id", "web_sessions", ["user_id"])

    for t in ("sign_in_links", "web_sessions"):
        op.execute(f"ALTER TABLE {t} ENABLE ROW LEVEL SECURITY")
        op.execute(f"ALTER TABLE {t} FORCE ROW LEVEL SECURITY")
        op.execute(f"GRANT SELECT, INSERT, UPDATE ON {t} TO {role}")
    op.execute(f"CREATE POLICY auth_flow ON sign_in_links FOR ALL USING ({AUTH}) WITH CHECK ({AUTH})")
    op.execute(f"CREATE POLICY auth_flow ON web_sessions FOR ALL USING ({AUTH}) WITH CHECK ({AUTH})")
    own = f"{TENANT} AND (user_id = app_user_id() OR {BROKER})"
    op.execute(f"CREATE POLICY own_or_broker ON web_sessions FOR SELECT USING ({own})")
    op.execute(f"CREATE POLICY end_own_or_broker ON web_sessions FOR UPDATE USING ({own}) WITH CHECK ({own})")
    op.execute(f"CREATE POLICY auth_read ON users FOR SELECT USING ({AUTH})")
    op.execute(f"CREATE POLICY auth_update ON users FOR UPDATE USING ({AUTH}) WITH CHECK ({AUTH})")
    op.execute("ALTER POLICY append ON audit_events WITH CHECK "
               f"({TENANT} OR app_role() = 'system' OR ({AUTH} AND actor_type = 'system'))")
    op.execute(r"""
CREATE OR REPLACE FUNCTION app_email_in_use(p_email citext) RETURNS boolean
LANGUAGE sql STABLE SECURITY DEFINER SET search_path = public, pg_temp AS $$
  SELECT EXISTS (SELECT 1 FROM users WHERE email = p_email)
      OR EXISTS (SELECT 1 FROM operators WHERE email = p_email) $$;
""")
    op.execute("REVOKE ALL ON FUNCTION app_email_in_use(citext) FROM PUBLIC")
    op.execute(f"GRANT EXECUTE ON FUNCTION app_email_in_use(citext) TO {role}")


def downgrade() -> None:
    raise SystemExit("restore the pre-deploy dump to go back (schema.md 'Migrations')")
