"""Bylaw questions (T-4.2.1, MH-10): retrieval -> model -> exact-quote validator -> answer or refusal."""

from __future__ import annotations

import uuid
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ai.answer import DISCLAIMER, PROMPT_VERSION, REFUSAL, answer
from ai.llm import LlmClient
from ai.search import ClauseSearch, PostgresKeywordSearch
from core import audit, authz
from core.db import Actor
from core.errors import Invalid
from core.ids import uuid7
from core.models import QaCitation, QaInteraction


def ask(
    session: Session,
    actor: Actor,
    strata_id: uuid.UUID,
    question: str,
    llm: LlmClient,
    search: ClauseSearch | None = None,
) -> dict[str, Any]:
    authz.locate(session, actor, "building", strata_id)
    q = (question or "").strip()
    if not q or len(q) > 2000:
        raise Invalid("Ask a question of up to 2,000 characters.")
    searcher = search or PostgresKeywordSearch(session)
    hits = searcher.search(strata_id, q, limit=8)
    result = answer(q, hits, llm)
    qa = QaInteraction(
        id=uuid7(), brokerage_id=actor.brokerage_id, strata_id=strata_id, asked_by=actor.user_id, question_text=q,
        outcome=result.outcome, answer_text=result.answer_text, llm_model_id=llm.model_id,
        prompt_version=PROMPT_VERSION, retrieval_params_hash=searcher.params_hash,
    )
    session.add(qa)
    session.flush()
    for c in result.citations:
        session.add(QaCitation(id=uuid7(), brokerage_id=actor.brokerage_id, strata_id=strata_id,
                               qa_interaction_id=qa.id, bylaw_clause_id=c.clause.clause_id,
                               quoted_text=c.quote, validated=True))
    session.flush()
    audit.record(session, actor, "qa.asked", strata_id=strata_id, target_type="question", target_id=qa.id,
                 details={"outcome": result.outcome})
    if result.outcome == "answered":
        return {
            "id": str(qa.id), "outcome": "answered", "answer": result.answer_text, "disclaimer": DISCLAIMER,
            "citations": [
                {"bylaw_clause_id": str(c.clause.clause_id), "clause_number": c.clause.clause_number,
                 "quoted_text": c.quote, "document_id": str(c.clause.document_id),
                 "filed_on": c.clause.filed_on.isoformat() if c.clause.filed_on else None,
                 "filing_reference": c.clause.filing_reference}
                for c in result.citations
            ],
        }
    return {
        "id": str(qa.id), "outcome": "refused", "message": REFUSAL, "disclaimer": DISCLAIMER,
        "search_results_label": "Closest passages (search results, not an answer)",
        "search_results": [
            {"bylaw_clause_id": str(h.clause_id), "clause_number": h.clause_number, "body_text": h.body_text}
            for h in result.closest
        ],
    }


def history(session: Session, actor: Actor, strata_id: uuid.UUID) -> list[dict[str, Any]]:
    authz.locate(session, actor, "building", strata_id)
    rows = session.scalars(select(QaInteraction).where(QaInteraction.strata_id == strata_id)
                           .order_by(QaInteraction.created_at.desc()).limit(50)).all()
    return [{"id": str(r.id), "question": r.question_text, "outcome": r.outcome, "answer": r.answer_text}
            for r in rows]
