"""Worker starts without a web framework (R-07), configuration fingerprint (I-21), migrations (G-1, G-2)."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

import pytest
from alembic.autogenerate import compare_metadata
from alembic.config import Config
from alembic.migration import MigrationContext
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text

from core import config, jobs
from core.db import Actor, session_for
from core.devdata import World
from core.models import Base

pytestmark = pytest.mark.db
ROOT = Path(__file__).resolve().parents[2]

BLOCK_WEB = """
import sys, importlib.abc
sys.path[:0] = sys.argv[1:3]
class Block(importlib.abc.MetaPathFinder):
    def find_spec(self, name, path, target=None):
        if name.split('.')[0] in ('fastapi', 'starlette', 'uvicorn'):
            raise ImportError('web framework blocked: ' + name)
sys.meta_path.insert(0, Block())
import worker.main, worker.handlers
from worker.main import main
sys.exit(main(['worker', 'heartbeat']))
"""


def test_worker_starts_with_web_framework_absent(world: World) -> None:
    args = [sys.executable, "-I", "-c", BLOCK_WEB, str(ROOT / "packages"), str(ROOT / "apps")]
    r = subprocess.run(args, env=dict(os.environ), capture_output=True, text=True, timeout=60, check=False)  # noqa: S603
    assert r.returncode == 0, r.stderr[-2000:]


def test_i21_config_fingerprint_matches_and_mismatch_is_not_ready(world: World, client: object) -> None:
    from fastapi.testclient import TestClient

    c: TestClient = client  # type: ignore[assignment]
    jobs.heartbeat("w-same", config.settings().fingerprint())
    r = c.get("/readyz")
    assert r.status_code == 200 and r.json()["checks"]["configuration"] == "ok"
    other = config.load({**os.environ, "RETENTION_AUDIO_DAYS_AFTER_APPROVAL_DEFAULT": "21"})
    jobs.heartbeat("w-other", other.fingerprint())
    r = c.get("/readyz")
    assert r.status_code == 503 and r.json()["checks"]["configuration"] == "configuration mismatch"
    with session_for(Actor.system()) as s:
        s.execute(text("DELETE FROM worker_heartbeats"))


def test_g1_single_migration_head() -> None:
    cfg = Config(str(ROOT / "tools" / "alembic.ini"))
    heads = ScriptDirectory.from_config(cfg).get_heads()
    assert heads == ["0004"]


def test_g2_migrated_schema_matches_orm_metadata(world: World) -> None:
    eng = create_engine(config.settings().migration_database_url)
    with eng.connect() as c:
        diff = compare_metadata(MigrationContext.configure(c, opts={"compare_type": True}), Base.metadata)
    eng.dispose()
    assert diff == [], diff
