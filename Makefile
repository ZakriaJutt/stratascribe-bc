# StrataScribe BC — local commands (B1). Services run directly; the TRD's Compose setup stays proposed.
# Python 3.12 venv at tools/.venv. PostgreSQL 16 on localhost:5432, Redis db 5, API port 8106.

SHELL := /bin/bash
PY := tools/.venv/bin/python
VENV := tools/.venv
PYTHONPATH := $(CURDIR)/packages:$(CURDIR)/apps
TEST_ENV := set -a && . tools/env.test && set +a
DEV_ENV := set -a && . $(if $(wildcard tools/env.local),tools/env.local,tools/env.example.local) && set +a
APP_ROLE := stratascribe_app

.PHONY: venv db-role migrate-test reset-test-db migrate-dev seed dev api worker test test-unit lint typecheck check-migrations check

venv:
	/opt/homebrew/bin/python3.12 -m venv $(VENV)
	$(VENV)/bin/pip install -q -r tools/requirements-dev.txt

# Non-superuser application role without BYPASSRLS (idempotent).
db-role:
	psql -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='$(APP_ROLE)'" | grep -q 1 || \
	  psql -d postgres -c "CREATE ROLE $(APP_ROLE) LOGIN NOSUPERUSER NOBYPASSRLS NOCREATEDB NOCREATEROLE"

# Drop and re-create the test schema, then migrate from zero (clean-database run).
reset-test-db: db-role
	psql -q -d stratascribe_test -c "DROP SCHEMA IF EXISTS public CASCADE; CREATE SCHEMA public;" 2>/dev/null
	cd tools && $(TEST_ENV:tools/%=%) && ../$(VENV)/bin/alembic -c alembic.ini upgrade head

migrate-test: db-role
	cd tools && $(TEST_ENV:tools/%=%) && ../$(VENV)/bin/alembic -c alembic.ini upgrade head

migrate-dev: db-role
	$(DEV_ENV) && cd tools && ../$(VENV)/bin/alembic -c alembic.ini upgrade head

seed: migrate-dev
	$(DEV_ENV) && PYTHONPATH=$(PYTHONPATH) $(PY) -c "from core import devdata; devdata.reset_all(); print(devdata.seed_world())"

api:
	$(DEV_ENV) && PYTHONPATH=$(PYTHONPATH) $(PY) -m api

worker:
	$(DEV_ENV) && PYTHONPATH=$(PYTHONPATH) $(PY) -m worker run

# One command: migrate, start API and worker, wait for /readyz.
dev: migrate-dev
	@$(DEV_ENV) && mkdir -p var && \
	  (PYTHONPATH=$(PYTHONPATH) $(PY) -m worker run > var/worker.log 2>&1 & echo $$! > var/worker.pid) && \
	  (PYTHONPATH=$(PYTHONPATH) $(PY) -m api > var/api.log 2>&1 & echo $$! > var/api.pid) && \
	  for i in $$(seq 1 30); do curl -sf http://127.0.0.1:8106/readyz >/dev/null && break; sleep 1; done; \
	  curl -s http://127.0.0.1:8106/readyz; echo; echo "API pid $$(cat var/api.pid), worker pid $$(cat var/worker.pid); stop with: make stop"

stop:
	-@kill $$(cat var/api.pid) $$(cat var/worker.pid) 2>/dev/null; rm -f var/api.pid var/worker.pid

test-unit:
	cd tools && .venv/bin/pytest -c pytest.ini --rootdir=.. ../tests/unit

test: reset-test-db
	cd tools && .venv/bin/pytest -c pytest.ini --rootdir=.. ../tests

lint:
	cd tools && .venv/bin/ruff check --config ruff.toml ../packages ../apps ../tests

typecheck:
	cd tools && .venv/bin/mypy --config-file mypy.ini ../packages ../apps

# One migration head; migrated schema equals the ORM metadata (G-1, G-2 checks run in the test suite).
check-migrations:
	cd tools && $(TEST_ENV:tools/%=%) && ../$(VENV)/bin/alembic -c alembic.ini heads | tee /dev/stderr | wc -l | grep -qx ' *1'

check: lint typecheck test
