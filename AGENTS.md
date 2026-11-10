# AGENTS.md — StrataScribe BC

Canonical instructions for any coding or documentation agent working in this repository. `CLAUDE.md` adds product-specific guidance and defers to this file.

**Current state: build milestone B1 (foundation and deterministic core) on branch `feat/b1-foundation`, authorised by the owner on 2026-11-11 before the Phase 0 sales gate.** Python packages, three Alembic migrations with row-level security, an API and a worker exist and run locally against synthetic data only; transcription and the language model are fakes behind interfaces. There is no web frontend, no deployment, no real provider and no sign-in flow (web sessions are created only by tests). What ran and what did not is recorded in `verification-report-fixing.md` section "B1 build record". Commands not marked as existing below are still **proposed**; do not report a proposed command as run.

## What this repository is for

One question: can a BC strata management brokerage save measurable time across two authorized meetings **after** a manager corrects motions, votes and bylaw citations? Work that does not help answer it is out of scope (risk R-21).

## Reading order

1. `Decision.md` — who pays, the economics, the stop rule, sources and assumptions.
2. `PRD.md` — outcomes, roles, must-haves `MH-01`–`MH-13`, metrics, non-goals.
3. `App-flow.md` — screens `S-01`–`S-17`, routes, states.
4. `design.md` — layout, microcopy, accessibility checks.
5. `TRD.md` — architecture (arc42 order), APIs, jobs, deterministic rules, AI boundaries, threat model.
6. `schema.md` — tables, permissions, retention, migrations.
7. `execution-plan.md` — phases, milestones, tasks `T-x.y.z`, planned tests.
8. `verification-report-fixing.md` — traceability, findings, and the only production risk register (`R-01`–`R-22`).

## Sources of truth

| Topic | File | Rule |
|---|---|---|
| Prices, offer, pilot terms, economics, stop rule, sources | `Decision.md` | Figures from the earlier discussion are quoted exactly and labelled. Do not change them; add a labelled proposal beside them. |
| Requirements and acceptance criteria | `PRD.md` | A feature without an MH ID does not get built. |
| Screens, routes, states | `App-flow.md` | — |
| Visual and content rules, accessibility checks | `design.md` | — |
| Architecture, API, jobs, rules, AI boundaries | `TRD.md` | — |
| Data, permissions, retention, migrations | `schema.md` | — |
| Sequence, tasks, tests | `execution-plan.md` | — |
| Risks, traceability, findings | `verification-report-fixing.md` | Other files cite risk IDs; they never restate a risk. |

Number labels (`[C]`, `[A-chat]`, `[A]`, `[S: …]`, `[D]`) are defined at the top of `Decision.md`. **Every number you add to any file must carry one.** Never present an assumption as a finding. If you cannot open a source, write "unverified, no source consulted".

## What to update when something changes

| If you change… | Also update… |
|---|---|
| A requirement or acceptance criterion | `PRD.md` (the MH row), the traceability table in `verification-report-fixing.md`, the linked task and test in `execution-plan.md`, the affected screen in `App-flow.md` |
| A screen, route or state | `App-flow.md` inventory, navigation diagram and screen section; `design.md` if layout or microcopy changes; the API table in `TRD.md`; traceability |
| A permission or role | `PRD.md` roles table; `schema.md` permissions table and policies; the abuse cases in `TRD.md`; permission tests `P-…` in `execution-plan.md`; `CLAUDE.md` if the highest-consequence error changes |
| A table, column, index or constraint | `schema.md` dictionary, index table and ER diagram; migration notes; the ORM-parity expectation; any API in `TRD.md` that exposes it |
| An operating assumption (price, cost, retention period, hosting location, model or provider, time target) | `Decision.md` (with its label and, if sourced, a row in Sources and assumptions); `TRD.md` constraints, decisions (AD-n) and quality table; `schema.md` retention table; `PRD.md` metrics |
| A legal reading | `Decision.md` Sources and assumptions first, with date and what was actually opened; then every file that cites that source ID |
| A risk's prevention or test | Only the register in `verification-report-fixing.md`, plus the task it names |
| The deterministic rules | `TRD.md` rules tables, the `minute_items` constraints in `schema.md`, S-10 in `App-flow.md`, unit tests U-1 to U-6 and U-10 to U-15, the source rows in `Decision.md`, and bump the rules version |
| How time is measured (any M-1 term) | `PRD.md` "How M-1 is captured", `review_sessions` and `meeting_time_reports` in `schema.md`, S-10, S-11, S-13 in `App-flow.md`, tests I-13 and I-15 |

## Product boundaries

- The product drafts; a licensed strata manager approves. Nothing is sent to owners by the product.
- Vote results from counts, quorum, access decisions, retention dates and job routing are deterministic code. A language model never decides them. A motion decided on a show of cards has a declared outcome selected by the manager; counts are optional and never invented.
- A bylaw answer is shown only with a validated, exact quotation from the building's current confirmed bylaws, rules or the statute set. Otherwise the product says no supporting clause was found.
- No audio is accepted without a recorded authority for that meeting.
- StrataScribe is not the system of record for a strata corporation's minutes and gives no legal advice.
- Non-goals are listed in `PRD.md`. Do not build them.

## Architecture conventions (proposed)

- Layout: `apps/web` (Next.js), `apps/api` (FastAPI), `apps/worker`, `packages/core`, `packages/rules`, `packages/ai`, `packages/docs`.
- `apps/*` never import each other. The web app talks to the API over HTTP only.
- `packages/core` imports no web framework; workers must start without one installed.
- All mutating endpoints accept an idempotency key. All state transitions go through `core.jobs.transition` with compare-and-set.
- Every log line and job carries a correlation ID. Never log transcript, minutes, question, answer, names or emails.
- URLs shown to users are built from `PUBLIC_BASE_URL` only. File bytes are streamed by the API under the user's session; there are no signed or expiring links to the object store.

## Reuse before writing

One owner per concern. Extend the owner; do not write a second one.

| Concern | Owner | B1 module |
|---|---|---|
| Configuration | `core.config` | `packages/core/config.py` (`settings()`, `fingerprint()`) |
| Logging and redaction | `core.logging` | `packages/core/logging.py` (JSON, correlation ID, allow-list redactor) |
| Access decisions | `core.authz` | `packages/core/authz.py` (`locate()`, 403/404, denial audit) |
| Database sessions with tenant context | `core.db.session_for` | `packages/core/db.py` (`Actor`, `session_for()`) |
| Storage keys and download links | `core.storage` | `packages/core/storage.py` (`key()`, `ScopedStore`, local store; S3 adapter not built) |
| Job states and transitions | `core.jobs` | `packages/core/jobs.py` (`transition()`, `enqueue()`, `lease()`, `reconcile()`) |
| Audit events | `core.audit` | `packages/core/audit.py` (`record()`) |
| Web sessions (identity only) | `core.sessions` | `packages/core/sessions.py` (Redis db 5; sign-in flow not built) |
| Idempotency keys | `core.idempotency` | `packages/core/idempotency.py` |
| Meetings, recording authority, uploads | `core.meetings` | `packages/core/meetings.py` |
| Review, corrections, item citations | `core.review` | `packages/core/review.py` |
| Approval and reopening | `core.approval` | `packages/core/approval.py` |
| Activity timer and time reports | `core.activity` | `packages/core/activity.py` |
| Pilot report (M-1 terms) | `core.pilot` | `packages/core/pilot.py` |
| Business days | `core.timecal` | `packages/core/timecal.py` (holiday table not built in) |
| Retention sweep | `core.retention` | `packages/core/retention.py` (audio and abandoned uploads only) |
| Synthetic fixtures | `core.devdata` | `packages/core/devdata.py` (refuses outside local/test) |
| Quorum and vote results | `packages/rules` | `packages/rules/` (`evaluate_motion`, `compute_vote`, `general_quorum`, `council_quorum`) |
| Model calls, prompts, citation validation, evaluation | `packages/ai` | `packages/ai/` (`Transcriber`, `LlmClient`, `ClauseSearch` with fakes; `answer.validate_citations`) |
| Bylaw parsing and minutes export | `packages/docs` | `packages/docs/` (plain-text clause splitter, audio magic bytes; export not built) |

Before adding a helper, search these packages. If something close exists, change it there.

## Tenant and building safety

- Two boundaries: brokerage (tenant) and building (strata corporation). Both are enforced in PostgreSQL row-level security and again in `core.authz`.
- Never open a database session except through `core.db.session_for(actor)`. Never use a role that bypasses row-level security in application code.
- Every building-owned table carries `brokerage_id` and `strata_id`. A new table without them needs a written reason in `schema.md`.
- Workers take tenant context from the job row, scoped to one building.
- Never build an object key by hand. Never use an uploaded file name in a key.
- No cache may hold tenant data unless its key includes brokerage and building and `schema.md` and risk R-05 are updated first.
- Every new route needs rows in the permission test matrix before it merges.
- Use only synthetic data in local, CI and staging. Never copy production data out of production.

## Migrations

- One linear Alembic history. More than one head fails CI. Rebase; do not add merge migrations.
- Declare indexes and constraints in the ORM models as well as migrations. Row-level security policies and triggers live in migrations and are checked by the policy-listing test.
- Create indexes on existing tables concurrently, in their own migration. Set a 5-second lock timeout.
- Backfills are resumable jobs with a progress row, not migration bodies.
- Expand, then contract: a release never drops something the previous release still reads.

## Tests

- Commands that exist (B1, root `Makefile`): `make venv`, `make db-role`, `make reset-test-db`, `make migrate-dev`, `make seed`, `make dev` (API on 8106 and worker run directly, waits for `/readyz`), `make stop`, `make test` (drops and re-migrates the test schema, then runs every test), `make test-unit`, `make lint` (ruff), `make typecheck` (mypy strict), `make check-migrations`. Still proposed: `make eval`, `make deploy TAG=…`, `make rollback TAG=…`, the Compose stack.
- Integration and permission tests run against a real PostgreSQL with row-level security on. Do not mock the database for access tests.
- Any change to prompts, model IDs or retrieval must re-run the AI fixtures; citation validity and refusal must stay at 100%.
- Any change to `packages/rules` must keep U-1 to U-6 and U-10 to U-15 passing and bump the rules version.
- Mark a test as passed only if you ran it and saw it pass. Otherwise write **Not run**.

## Git hygiene

- Default branch `main`, protected. Branch names: `feat/<short>`, `fix/<short>`, `docs/<short>`. Delete branches on merge.
- Small commits with a message that names the task ID (for example "T-3.2.3: 3/4 vote rule").
- Never commit credentials, tokens, environment files, recordings, transcripts, real bylaws, or real names. Synthetic examples only.
- Do not rewrite history on `main`. Do not delete someone else's unmerged branch.
- The repository root holds the ten planning files plus `.gitignore` and `Makefile`; code lives in `apps/`, `packages/`, `tests/` and `tools/` (virtual environment, tool configuration, synthetic environment files). Scratch files and checkers stay outside the repository.

## Accurate completion reporting

When you finish a piece of work, report:

1. What you changed, by file.
2. What you verified, and how (command and result), separately from what you did not verify.
3. Which numbers or legal statements you added and their labels and sources.
4. Which other files you updated per the table above, or why none was needed.
5. Anything you could not reconcile.

Do not write "done", "verified" or "compliant" for anything that was only planned. A planned control is not evidence of compliance.
