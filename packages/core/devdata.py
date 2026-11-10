"""Synthetic fixtures for local and test databases only (``make seed``; execution-plan "Planned tests").

Two brokerages, three buildings, four users, all invented: Priya (ZZS 9001
only), Daniel (ZZS 9001 and ZZS 9002), Marta (managing broker of Harbourline),
Omar (manager at Tidewater). Written through the migration (owner) connection
because onboarding rows have no application-role INSERT policy. Refuses to run
outside local or test.
"""

from __future__ import annotations

import uuid
from dataclasses import dataclass

from sqlalchemy import create_engine, text
from sqlalchemy.orm import Session

from core import config
from core.ids import uuid7
from core.models import Base, Brokerage, BuildingAssignment, StrataCorporation, User


@dataclass(frozen=True)
class World:
    harbourline: uuid.UUID
    tidewater: uuid.UUID
    zzs9001: uuid.UUID
    zzs9002: uuid.UUID
    zzs9101: uuid.UUID
    priya: uuid.UUID
    daniel: uuid.UUID
    marta: uuid.UUID
    omar: uuid.UUID


def _guard() -> config.Settings:
    s = config.settings()
    if s.env not in ("local", "test"):
        raise SystemExit("devdata refuses to run outside local or test")
    return s


def reset_all() -> None:
    s = _guard()
    eng = create_engine(s.migration_database_url)
    names = ", ".join(t.name for t in Base.metadata.sorted_tables)
    with eng.begin() as c:
        c.execute(text(f"TRUNCATE {names} CASCADE"))
    eng.dispose()


def seed_world() -> World:
    s = _guard()
    eng = create_engine(s.migration_database_url)
    hb, tw = uuid7(), uuid7()
    s1, s2, s3 = uuid7(), uuid7(), uuid7()
    priya, daniel, marta, omar = uuid7(), uuid7(), uuid7(), uuid7()
    with Session(eng) as db, db.begin():
        db.add_all([
            Brokerage(id=hb, legal_name="Harbourline Strata Management Ltd.", privacy_contact_name="Marta Ruiz",
                      privacy_contact_email="privacy@harbourline.example"),
            Brokerage(id=tw, legal_name="Tidewater Strata Management Inc.", privacy_contact_name="Omar Haddad",
                      privacy_contact_email="privacy@tidewater.example"),
        ])
        db.flush()
        db.add_all([
            User(id=marta, brokerage_id=hb, email="marta@harbourline.example", full_name="Marta Ruiz",
                 role="managing_broker", status="active"),
            User(id=priya, brokerage_id=hb, email="priya@harbourline.example", full_name="Priya Nair",
                 role="strata_manager", status="active"),
            User(id=daniel, brokerage_id=hb, email="daniel@harbourline.example", full_name="Daniel Okafor",
                 role="strata_manager", status="active"),
            User(id=omar, brokerage_id=tw, email="omar@tidewater.example", full_name="Omar Haddad",
                 role="strata_manager", status="active"),
        ])
        db.flush()
        db.add_all([
            StrataCorporation(id=s1, brokerage_id=hb, name="Alder Court", strata_plan_number="ZZS 9001",
                              strata_lot_count=40, owner_count=38, eligible_votes_total=40, council_size=5),
            StrataCorporation(id=s2, brokerage_id=hb, name="Birch Gardens", strata_plan_number="ZZS 9002",
                              strata_lot_count=3, owner_count=3, eligible_votes_total=3, council_size=3),
            StrataCorporation(id=s3, brokerage_id=tw, name="Cedar Quay", strata_plan_number="ZZS 9101",
                              strata_lot_count=24, owner_count=24, eligible_votes_total=24, council_size=5),
        ])
        db.flush()
        db.add_all([
            BuildingAssignment(id=uuid7(), brokerage_id=hb, strata_id=s1, user_id=priya, assigned_by=marta),
            BuildingAssignment(id=uuid7(), brokerage_id=hb, strata_id=s1, user_id=daniel, assigned_by=marta),
            BuildingAssignment(id=uuid7(), brokerage_id=hb, strata_id=s2, user_id=daniel, assigned_by=marta),
            BuildingAssignment(id=uuid7(), brokerage_id=tw, strata_id=s3, user_id=omar, assigned_by=omar),
        ])
    eng.dispose()
    return World(hb, tw, s1, s2, s3, priya, daniel, marta, omar)
