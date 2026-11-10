"""Test harness. Loads tools/env.test BEFORE importing application code.

Integration and permission tests run against the real PostgreSQL test database
as the non-superuser role ``stratascribe_app`` with row-level security on, and
against Redis database 5 (keys prefixed ``stratascribe:test:``).
"""

from __future__ import annotations

import os
import shutil
from collections.abc import Iterator
from pathlib import Path
from typing import Any

import pytest

ROOT = Path(__file__).resolve().parents[1]
for line in (ROOT / "tools" / "env.test").read_text().splitlines():
    if line.strip() and not line.startswith("#"):
        k, _, v = line.partition("=")
        os.environ[k.strip()] = v.strip()

from fastapi.testclient import TestClient  # noqa: E402

from core import clock, config, devdata, sessions, storage  # noqa: E402
from core.devdata import World  # noqa: E402
from tests.helpers import Api  # noqa: E402


@pytest.fixture
def world() -> Iterator[World]:
    config.reset()
    clock.set_clock(None)
    devdata.reset_all()
    r = sessions.client()
    for k in r.scan_iter("stratascribe:test:*"):
        r.delete(k)
    root = ROOT / config.settings().object_store_root
    shutil.rmtree(root, ignore_errors=True)
    storage.set_store(None)
    w = devdata.seed_world()
    yield w
    clock.set_clock(None)


@pytest.fixture
def client(world: World) -> TestClient:
    from api.app import create_app

    return TestClient(create_app())


@pytest.fixture
def as_user(client: TestClient, world: World) -> Any:
    roles = {world.marta: (world.harbourline, "managing_broker"), world.priya: (world.harbourline, "strata_manager"),
             world.daniel: (world.harbourline, "strata_manager"), world.omar: (world.tidewater, "strata_manager")}

    def make(user_id: Any) -> Api:
        b, role = roles[user_id]
        return Api(client, sessions.create(user_id, b, role))

    return make


