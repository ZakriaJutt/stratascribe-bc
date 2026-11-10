"""Bylaw library (T-4.1.1 partial, MH-09).

B1 accepts plain text and splits it synchronously with ``docs.clauses``; PDF and
DOCX extraction, scanned-file detection and the ``index_bylaws`` job are not
built. Confirming a document makes it citable and supersedes the previous
current document of the same kind for that building.
"""

from __future__ import annotations

import hashlib
import uuid
from datetime import date
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from core import audit, authz, clock, storage
from core.db import Actor
from core.errors import Conflict, Invalid, NotFound
from core.ids import uuid7
from core.models import BylawClause, BylawDocument
from docs.clauses import PARSER_VERSION, split_clauses


def document_out(d: BylawDocument, clauses: list[BylawClause] | None = None) -> dict[str, Any]:
    out: dict[str, Any] = {
        "id": str(d.id), "strata_id": str(d.strata_id), "kind": d.kind, "status": d.status,
        "filing_reference": d.filing_reference, "filed_on": d.filed_on.isoformat() if d.filed_on else None,
        "parser_version": d.parser_version,
    }
    if clauses is not None:
        out["clauses"] = [
            {"id": str(c.id), "clause_number": c.clause_number, "heading": c.heading, "body_text": c.body_text,
             "position": c.position}
            for c in clauses
        ]
    return out


def create_document(session: Session, actor: Actor, strata_id: uuid.UUID, body: dict[str, Any]) -> BylawDocument:
    authz.locate(session, actor, "building", strata_id)
    kind = body.get("kind", "bylaws")
    text_body = body.get("text")
    if kind not in ("bylaws", "rules") or not isinstance(text_body, str) or not text_body.strip():
        raise Invalid("kind and text are required (B1 accepts plain text only).")
    filed_on = date.fromisoformat(body["filed_on"]) if body.get("filed_on") else None
    raw = text_body.encode()
    sha = hashlib.sha256(raw).digest()
    doc_id = uuid7()
    key = storage.key(actor.brokerage_id, strata_id, "bylaw", doc_id)  # type: ignore[arg-type]
    clauses = split_clauses(text_body)
    if not clauses:
        raise Invalid("No numbered clauses were found in this text.", code="no_clauses")
    doc = BylawDocument(
        id=doc_id, brokerage_id=actor.brokerage_id, strata_id=strata_id, kind=kind,
        filing_reference=body.get("filing_reference"), filed_on=filed_on, storage_key=key, sha256=sha,
        parser_version=PARSER_VERSION, status="needs_confirmation",
    )
    session.add(doc)
    try:
        session.flush()
    except IntegrityError as exc:
        raise Conflict("This document is already in the building's library.", code="duplicate_document") from exc
    for c in clauses:
        session.add(BylawClause(
            id=uuid7(), brokerage_id=actor.brokerage_id, strata_id=strata_id, bylaw_document_id=doc.id,
            clause_number=c.clause_number, heading=c.heading, body_text=c.body_text, position=c.position,
        ))
    session.flush()
    storage.store().put(key, raw)
    return doc


def get_document(session: Session, actor: Actor, doc_id: uuid.UUID) -> tuple[BylawDocument, list[BylawClause]]:
    authz.locate(session, actor, "bylaw_document", doc_id)
    d = session.get(BylawDocument, doc_id)
    if d is None:
        raise NotFound("Not found.")
    clauses = list(session.scalars(
        select(BylawClause).where(BylawClause.bylaw_document_id == d.id).order_by(BylawClause.position)
    ).all())
    return d, clauses


def list_documents(session: Session, actor: Actor, strata_id: uuid.UUID) -> list[BylawDocument]:
    authz.locate(session, actor, "building", strata_id)
    return list(session.scalars(
        select(BylawDocument).where(BylawDocument.strata_id == strata_id).order_by(BylawDocument.created_at)
    ).all())


def confirm(session: Session, actor: Actor, doc_id: uuid.UUID) -> BylawDocument:
    d, _ = get_document(session, actor, doc_id)
    if d.status != "needs_confirmation":
        raise Conflict("Only a document waiting for confirmation can be confirmed.", code="not_confirmable")
    if d.kind == "bylaws" and d.filed_on is None:
        raise Invalid("Enter the filing date before confirming bylaws.", code="filed_on_required")
    session.execute(
        update(BylawDocument)
        .where(BylawDocument.strata_id == d.strata_id, BylawDocument.kind == d.kind, BylawDocument.status == "current")
        .values(status="superseded")
    )
    d.status, d.confirmed_by, d.confirmed_at = "current", actor.user_id, clock.now()
    session.flush()
    audit.record(session, actor, "bylaws.confirmed", strata_id=d.strata_id, target_type="bylaw_document",
                 target_id=d.id, details={"kind": d.kind})
    return d
