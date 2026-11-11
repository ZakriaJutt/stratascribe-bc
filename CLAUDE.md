# CLAUDE.md — StrataScribe BC

Read [AGENTS.md](AGENTS.md) first. It is canonical for reading order, sources of truth, conventions, tenant safety, migrations, tests, Git hygiene and completion reporting. This file adds only what is specific to this product.

**State:** build milestones B1 (foundation and deterministic core) and B2 (sign-in, Mailpit email, MinIO storage), authorised by the owner on 2026-11-11 before the Phase 0 gate. See the AGENTS.md state line and `verification-report-fixing.md` "B1 build record" and "B2 build record" for what ran.

## The buyer's workflow in six lines

1. A managing broker at a BC strata management brokerage pays; they assign strata managers to buildings (strata corporations).
2. A manager attends a council meeting, AGM or SGM for an assigned building.
3. Before any audio is accepted, the manager records why the meeting may be recorded (a filed recording bylaw, or the other bases in [App-flow.md](App-flow.md), screen S-08), or chooses dictated notes.
4. The system transcribes and drafts minutes in BC form; the manager checks every motion, mover, seconder, outcome and bylaw citation against the audio and corrects them. A motion's outcome is either what the chair declared on a show of cards, selected by the manager with no numbers, or calculated by fixed rules from a count the manager confirms.
5. The manager approves and exports Word or PDF, and sends it the way they always have. The recording is deleted on schedule.
6. For bylaw questions the manager gets the quoted clause with its number, or "No supporting clause found".

The pilot measures step 4: time saved **after** correction, across two authorized meetings. See [Decision.md](Decision.md) and [How M-1 is captured](PRD.md#how-m-1-is-captured). The first paid pilots are delivered by hand, before this application exists (Phase 0 in [execution-plan.md](execution-plan.md)).

## Highest-consequence errors

1. **Wrong motion or vote result in approved minutes.** The minutes are the strata corporation's record of its decisions. Never let a model's reading of "carried" become the outcome. Only `packages/rules` computes results, from counts the manager confirmed; a declared outcome is only ever the manager's own selection. Never require or invent counts for a motion decided on a show of cards.
2. **A manager sees another building's recording, minutes or bylaws,** even inside the same brokerage; or one brokerage sees another's. Treat any query, file link, job or cache that is not scoped by brokerage and building as a defect.
3. **A recording accepted without authority, or kept past its deletion date.**
4. **A bylaw answer shown without an exact, validated citation,** or from a superseded bylaw.

## Sensitive data

- Meeting audio and transcripts: owners' voices, names, unit numbers, arrears, bylaw complaints. Highest sensitivity. Never in logs, error messages, audit details, test fixtures, prompts sent to an unapproved endpoint, or this repository.
- Draft and approved minutes; questions and answers (they can name owners).
- The building-assignment table: it is the access rule.
- Processing and storage location is a product commitment (Canada). The language-model endpoint is an open decision (AD-5 in [TRD.md](TRD.md#9-architecture-decisions)); do not send real transcript text to any provider until that decision is recorded with the provider's own terms.

## Prohibited shortcuts

- Do not skip or default the recording-authority step, in code, seeds or demos.
- Do not write `computed_result` anywhere except `packages/rules`. Do not round vote fractions; use the integer inequalities in [TRD.md](TRD.md#deterministic-rules). Do not make vote counts mandatory, and do not prefill a declared outcome as final.
- Do not issue signed or expiring links to stored files; files are streamed by the API under the user's session. Do not give operators a database role that bypasses row-level security.
- In the hand-run phase, do not put any real recording, transcript or minutes text into a hosted model or chatbot; local models only (protocol under T-0.3.2 in [execution-plan.md](execution-plan.md)).
- Do not display model output as a bylaw answer unless the citation validator passed.
- Do not open a database session without tenant context, add a bypass role, or filter by tenant only in application code.
- Do not build storage keys by hand or expose internal hosts in links.
- Do not add a feature that sends anything to owners or councils.
- Do not use real recordings, real bylaws, real strata plan numbers or real people in fixtures. The examples (Harbourline, ZZS 9001, Priya Nair) are invented.
- Do not state a legal rule from memory. Cite the source ID in `Decision.md`, or open the primary source and add it there with the date.
- Do not change a price, pilot term or stop-rule threshold that came from the earlier discussion. Add a labelled proposal beside it.
- Do not mark anything verified that was only planned.

## First verification checks when implementation begins

Run these before any feature work is called complete. IDs refer to [execution-plan.md](execution-plan.md#planned-tests). B1 status per item is in `verification-report-fixing.md` "B1 build record"; in short: 1-6 ran and pass (I-9 audio only; U-7/I-8 against a fake model), 7 Not run (no containers, no link-building routes), 8 partly (I-13 server side only; I-15 ran).

1. **I-11** — with no session variables, the application database role reads zero rows from every tenant table.
2. **P-1, P-2, P-4 and P-6** — a manager assigned to ZZS 9001 gets 403 on every ZZS 9002 route including audio streams and downloads; a user of another brokerage gets 404 on everything; an operator reads nothing without a support grant; a managing broker can act in every building of their own brokerage and no other.
3. **I-1** — upload is refused for a meeting with no recording authority.
4. **U-1 to U-6 and U-10 to U-15** — counted-vote and quorum rules, including the 3/4 vote that fails by one, a motion declared on a show of cards with no numbers, a tie with a casting vote, and the small-strata and adjourned-meeting quorum.
5. **U-7 and I-8** — an answer with an inexact quote is rejected; all ten unanswerable questions are refused.
6. **I-9** — the retention sweep deletes expired audio and is safe to run twice.
7. **V-1 and V-3** — data survives container recreation; every generated link starts with the public base URL.
8. **I-13 and I-15** — the activity timer matches a scripted session, and the pilot report equals a hand calculation; without these the pilot's one number cannot be trusted.

## When unsure

- If a document and the code disagree, the document wins until it is changed deliberately, with the linked files updated as [AGENTS.md](AGENTS.md#what-to-update-when-something-changes) requires.
- If something is "not decided in chat" in `Decision.md`, do not decide it silently. Make a labelled proposal or ask.
