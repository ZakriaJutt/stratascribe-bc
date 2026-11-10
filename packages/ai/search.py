"""Clause search behind an interface (pgvector is not available on this PostgreSQL 16).

B1 implementation: PostgreSQL full-text search over the question's words (OR), always
filtered by building and ``status = 'current'`` in the query itself and run
under row-level security, so another building's clause can never be returned.
A vector implementation can replace it later without touching callers.
"""

from __future__ import annotations

import re
import uuid
from dataclasses import dataclass
from datetime import date
from typing import Protocol

from sqlalchemy import text
from sqlalchemy.orm import Session


@dataclass(frozen=True)
class ClauseHit:
    clause_id: uuid.UUID
    document_id: uuid.UUID
    clause_number: str
    body_text: str
    filed_on: date | None
    filing_reference: str | None
    score: float


class ClauseSearch(Protocol):
    params_hash: str

    def search(self, strata_id: uuid.UUID, query: str, limit: int = 5) -> list[ClauseHit]: ...


_SQL = text(
    """
    SELECT c.id, c.bylaw_document_id, c.clause_number, c.body_text, d.filed_on, d.filing_reference,
           ts_rank(to_tsvector('english'::regconfig, c.body_text), to_tsquery('english', :q)) AS score
    FROM bylaw_clauses c
    JOIN bylaw_documents d ON d.id = c.bylaw_document_id AND d.strata_id = c.strata_id
    WHERE c.strata_id = :s AND d.status = 'current'
      AND to_tsvector('english'::regconfig, c.body_text) @@ to_tsquery('english', :q)
    ORDER BY score DESC, c.position
    LIMIT :n
    """
)


class PostgresKeywordSearch:
    params_hash = "pg-fts-0.1"

    def __init__(self, session: Session) -> None:
        self.session = session

    def search(self, strata_id: uuid.UUID, query: str, limit: int = 5) -> list[ClauseHit]:
        terms = re.findall(r"[a-z0-9]+", query.lower())
        if not terms:
            return []
        # Only [a-z0-9] terms joined by "|": no user text reaches tsquery syntax.
        rows = self.session.execute(_SQL, {"q": " | ".join(terms), "s": strata_id, "n": limit}).all()
        return [ClauseHit(r[0], r[1], r[2], r[3], r[4], r[5], float(r[6])) for r in rows]
