"""Bylaw library, cited answers and refusals, citations on items (I-7, I-8, I-16, U-7 through the API).

The model here is the deterministic fake (a word-overlap heuristic). These
tests prove the pipeline: building-filtered retrieval, the exact-quote
validator, refusal and storage. They say nothing about a real model's quality.
"""

from __future__ import annotations

import json
from typing import Any

import pytest
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from ai.llm import AlteringQuoteLlm, FakeLlmClient
from api import app as api_app
from core import config
from core.db import Actor, session_for
from core.devdata import World
from tests.helpers import FIXTURES, Api, bylaw_text, processed_meeting

pytestmark = pytest.mark.db
QUESTIONS = json.loads((FIXTURES / "questions.json").read_text())


def load_bylaws(api: Api, strata_id: Any, name: str, confirm: bool = True) -> dict[str, Any]:
    r = api.post(f"/buildings/{strata_id}/bylaw-documents", {"kind": "bylaws", "text": bylaw_text(name),
                                                            "filed_on": "2025-03-01", "filing_reference": "ZZ1234"})
    assert r.status_code == 201, r.text
    d = r.json()
    if confirm:
        assert api.post(f"/bylaw-documents/{d['id']}/confirm").status_code == 200
    return dict(d)


def test_clause_split_and_confirm_rules(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    d = load_bylaws(api, world.zzs9001, "bylaws_zzs9001.txt", confirm=False)
    numbers = [c["clause_number"] for c in d["clauses"]]
    assert numbers[:3] == ["1(1)", "1(2)", "2(1)"] and "11(1)" in numbers and len(numbers) == 23
    r = api.post(f"/buildings/{world.zzs9001}/bylaw-documents", {"kind": "bylaws", "text": "1 A\n(1) B."})
    no_date = r.json()
    assert api.post(f"/bylaw-documents/{no_date['id']}/confirm").status_code == 422
    dup = api.post(f"/buildings/{world.zzs9001}/bylaw-documents",
                   {"kind": "bylaws", "text": bylaw_text("bylaws_zzs9001.txt")})
    assert dup.status_code == 409
    assert api.post(f"/bylaw-documents/{d['id']}/confirm").json()["status"] == "current"


def test_i7_answerable_questions_have_validated_citations(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    doc = load_bylaws(api, world.zzs9001, "bylaws_zzs9001.txt")
    load_bylaws(as_user(world.daniel), world.zzs9002, "bylaws_zzs9002.txt")
    by_id = {c["id"]: c for c in doc["clauses"]}
    for question, expected in QUESTIONS["answerable"]:
        r = api.post(f"/buildings/{world.zzs9001}/questions", {"question": question}).json()
        assert r["outcome"] == "answered", (question, r)
        assert r["disclaimer"] == "Information, not legal advice."
        assert r["citations"], question
        for c in r["citations"]:
            clause = by_id[c["bylaw_clause_id"]]  # always a clause of ZZS 9001's current document
            assert c["quoted_text"] in clause["body_text"]
            assert c["filed_on"] == "2025-03-01" and c["document_id"] == doc["id"]
        assert r["citations"][0]["clause_number"] == expected, (question, r["citations"][0])
        assert "Birch" not in json.dumps(r)


def test_i8_unanswerable_questions_are_refused(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    load_bylaws(api, world.zzs9001, "bylaws_zzs9001.txt")  # includes an injected instruction in clause 10(1)
    for question in QUESTIONS["unanswerable"]:
        r = api.post(f"/buildings/{world.zzs9001}/questions", {"question": question}).json()
        assert r["outcome"] == "refused", (question, r)
        assert r["message"] == "No supporting clause found"
        assert r["search_results_label"].startswith("Closest passages")
        assert "answer" not in r
    hist = api.get(f"/buildings/{world.zzs9001}/questions").json()
    assert len(hist) == 10 and {h["outcome"] for h in hist} == {"refused"}


def test_u7_altered_quote_is_never_returned(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    load_bylaws(api, world.zzs9001, "bylaws_zzs9001.txt")
    api_app.set_llm(AlteringQuoteLlm())
    try:
        r = api.post(f"/buildings/{world.zzs9001}/questions", {"question": "How many dogs can I keep?"}).json()
    finally:
        api_app.set_llm(FakeLlmClient())
    assert r["outcome"] == "refused" and "citations" not in r


def test_superseded_and_unconfirmed_bylaws_are_not_cited(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    load_bylaws(api, world.zzs9001, "bylaws_zzs9001.txt", confirm=False)
    r = api.post(f"/buildings/{world.zzs9001}/questions", {"question": "How many dogs can I keep?"}).json()
    assert r["outcome"] == "refused"  # unconfirmed documents are not citable
    new = "2 Pets\n(1) An owner may keep at most one of their dogs in a strata lot.\n"
    d2 = api.post(f"/buildings/{world.zzs9001}/bylaw-documents", {"kind": "bylaws", "text": new,
                                                                 "filed_on": "2026-01-10"}).json()
    api.post(f"/bylaw-documents/{d2['id']}/confirm")
    r = api.post(f"/buildings/{world.zzs9001}/questions", {"question": "How many dogs can I keep?"}).json()
    assert r["outcome"] == "answered" and "one of their dogs" in r["citations"][0]["quoted_text"]


def test_db_refuses_an_answer_without_a_valid_citation(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    d = load_bylaws(api, world.zzs9001, "bylaws_zzs9001.txt")
    priya = Actor.user(world.priya, world.harbourline, "strata_manager")
    with pytest.raises(DBAPIError), session_for(priya) as s:
        s.execute(text(
            "INSERT INTO qa_interactions (id, brokerage_id, strata_id, asked_by, question_text, outcome, answer_text,"
            " llm_model_id, prompt_version, retrieval_params_hash) VALUES (gen_random_uuid(), :b, :s, :u, 'q',"
            " 'answered', 'a', 'm', 'p', 'h')"), {"b": world.harbourline, "s": world.zzs9001, "u": world.priya})
    with pytest.raises(DBAPIError), session_for(priya) as s:
        qid = s.execute(text(
            "INSERT INTO qa_interactions (id, brokerage_id, strata_id, asked_by, question_text, outcome,"
            " llm_model_id, prompt_version, retrieval_params_hash) VALUES (gen_random_uuid(), :b, :s, :u, 'q',"
            " 'refused', 'm', 'p', 'h') RETURNING id"), {"b": world.harbourline, "s": world.zzs9001,
                                                       "u": world.priya}).scalar()
        s.execute(text("INSERT INTO qa_citations (id, brokerage_id, strata_id, qa_interaction_id, bylaw_clause_id,"
                       " quoted_text, validated) VALUES (gen_random_uuid(), :b, :s, :q, :c, 'not in clause', true)"),
                  {"b": world.harbourline, "s": world.zzs9001, "q": qid, "c": d["clauses"][0]["id"]})


def test_i16_citation_corrections_on_items(world: World, as_user: Any) -> None:
    api = as_user(world.priya)
    doc = load_bylaws(api, world.zzs9001, "bylaws_zzs9001.txt")
    other = load_bylaws(as_user(world.daniel), world.zzs9002, "bylaws_zzs9002.txt")
    c = {x["clause_number"]: x["id"] for x in doc["clauses"]}
    m = processed_meeting(api, world.zzs9001)
    items = [i for i in api.get(f"/meetings/{m['id']}/draft").json()["items"] if i["item_type"] == "motion"]
    a, b = items[0], items[1]
    # An AI-suggested citation to 3(1) on motion a (inserted as the worker would)
    eng = create_engine(config.settings().migration_database_url)
    with eng.begin() as conn:
        sug = conn.execute(text(
            "INSERT INTO minute_item_citations (id, brokerage_id, strata_id, minute_item_id, bylaw_clause_id,"
            " origin, status) VALUES (gen_random_uuid(), :b, :s, :i, :c, 'ai_suggested', 'suggested') RETURNING id"),
            {"b": world.harbourline, "s": world.zzs9001, "i": a["id"], "c": c["3(1)"]}).scalar()
    eng.dispose()
    # replace 3(1) with 3(2); add one on b, then remove it; add one from the lookup panel
    r = api.post(f"/minute-items/{a['id']}/citations", {"bylaw_clause_id": c["3(2)"],
                                                         "replaces_citation_id": str(sug)})
    assert r.status_code == 201
    extra = api.post(f"/minute-items/{b['id']}/citations", {"bylaw_clause_id": c["4(1)"]}).json()
    assert api.delete(f"/minute-item-citations/{extra['id']}").status_code == 200
    r = api.post(f"/minute-items/{b['id']}/citations", {"bylaw_clause_id": c["8(1)"],
                                                         "quoted_text": "may be audio recorded"})
    assert r.status_code == 201
    bad = api.post(f"/minute-items/{b['id']}/citations", {"bylaw_clause_id": c["8(1)"], "quoted_text": "may be filmed"})
    assert bad.status_code == 422
    foreign = api.post(f"/minute-items/{b['id']}/citations", {"bylaw_clause_id": other["clauses"][0]["id"]})
    assert foreign.status_code == 403  # a ZZS 9002 clause is refused (Priya cannot even see it)
    marta_try = as_user(world.marta).post(f"/minute-items/{b['id']}/citations",
                                          {"bylaw_clause_id": other["clauses"][0]["id"]})
    assert marta_try.status_code == 422 and marta_try.json()["error"]["code"] == "clause_other_building"
    eng = create_engine(config.settings().migration_database_url)
    with eng.connect() as conn:
        cats = conn.execute(text("SELECT count(*) FROM corrections WHERE category = 'citation'")).scalar()
        live = conn.execute(text(
            "SELECT DISTINCT d.strata_id, d.status FROM minute_item_citations mc JOIN bylaw_clauses bc"
            " ON bc.id = mc.bylaw_clause_id JOIN bylaw_documents d ON d.id = bc.bylaw_document_id"
            " WHERE mc.status <> 'removed'")).all()
    eng.dispose()
    assert cats == 4  # replace, add, remove, add from lookup
    assert live == [(world.zzs9001, "current")]
