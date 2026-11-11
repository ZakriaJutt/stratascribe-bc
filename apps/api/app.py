"""FastAPI application: the B1 core path under ``/api/v1`` (TRD "API contracts").

Thin routes: every decision lives in ``packages/core`` and ``packages/rules``.
Every request runs inside ``core.db.session_for(actor)``; there is no other
session. Mutating routes require the custom request header, a matching Origin
when one is sent, and accept ``Idempotency-Key``. Files are streamed by the API
under the session; responses carry ``Cache-Control: no-store``.
"""

from __future__ import annotations

import re
import time
import uuid
from collections.abc import Awaitable, Callable, Iterator
from datetime import date
from typing import Any

from fastapi import Depends, FastAPI, Query, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from ai.llm import FakeLlmClient, LlmClient
from core import (
    activity,
    approval,
    audit,
    authz,
    buildings,
    bylaws,
    config,
    idempotency,
    jobs,
    meetings,
    pilot,
    qa,
    review,
    sessions,
    storage,
)
from core import logging as clog
from core.db import Actor, session_for
from core.errors import Conflict, DomainError, Invalid, NotFound, Unauthenticated
from core.ids import uuid7
from core.models import AudioAsset, AuditEvent, BaselineMeasurement, Transcript, TranscriptSegment, User

Body = dict[str, Any]
COOKIE = "ss_session"
CSRF_HEADER = "x-stratascribe-request"
MUTATING = {"POST", "PUT", "PATCH", "DELETE"}
log = clog.get_logger("api")

llm_client: LlmClient = FakeLlmClient()


def set_llm(client: LlmClient) -> None:
    global llm_client
    llm_client = client


def _error(exc: DomainError, status: int | None = None) -> JSONResponse:
    body = {"error": {"code": exc.code, "message": exc.message, "correlation_id": clog.correlation_id(), **exc.extra}}
    return JSONResponse(body, status_code=status or exc.status)


# ---------------------------------------------------------------- dependencies


def current_actor(request: Request) -> Actor:
    token = request.cookies.get(COOKIE, "")
    ws = sessions.resolve(token)
    if ws is None:
        raise Unauthenticated("Sign in to continue.")
    probe = Actor.user(ws.user_id, ws.brokerage_id, ws.role)
    with session_for(probe) as s:
        u = s.get(User, ws.user_id)
        if u is None or u.status != "active" or u.role != ws.role or u.brokerage_id != ws.brokerage_id:
            sessions.end(token)
            raise Unauthenticated("Your session has ended.")
    return probe


def guard_request(request: Request) -> None:
    """Request-forgery defence (TRD): custom header on every mutating call, Origin must match."""
    if request.method not in MUTATING:
        return
    if request.headers.get(CSRF_HEADER) != "1":
        raise DomainError("Missing request header.", code="forbidden_request") from None
    # Origin (or, failing that, Referer) is required and must be our own origin (B1-010).
    base = config.settings().public_base_url
    origin = request.headers.get("origin")
    if origin is not None:
        if origin.rstrip("/") != base:
            raise DomainError("Cross-origin request refused.", code="forbidden_request")
        return
    referer = request.headers.get("referer", "")
    if not (referer == base or referer.startswith(base + "/")):
        raise DomainError("Request origin missing or not allowed.", code="forbidden_request")


async def json_body(request: Request) -> dict[str, Any]:
    if request.method not in MUTATING:
        return {}
    raw = await request.body()
    if not raw:
        return {}
    if not request.headers.get("content-type", "").startswith("application/json"):
        raise Invalid("Send a JSON body.", code="json_required")
    try:
        data = await request.json()
    except ValueError as exc:
        raise Invalid("Malformed JSON.") from exc
    if not isinstance(data, dict):
        raise Invalid("Send a JSON object.")
    return data


def mutate(actor: Actor, request: Request, body: Any, fn: Callable[[Session], tuple[int, Any]]) -> JSONResponse:
    route = request.scope.get("route")
    route_name = getattr(route, "path", request.url.path) + ":" + request.url.path
    key = request.headers.get("idempotency-key")
    try:
        with session_for(actor) as s:
            cached = idempotency.lookup(s, actor, route_name, key, body)
            if cached is not None:
                return JSONResponse(cached[1], status_code=cached[0])
            status, out = fn(s)
            idempotency.store(s, actor, route_name, key, body, status, out)
    except IntegrityError as exc:
        # A concurrent request won a uniqueness race; nothing of this one was committed (B1-011).
        raise Conflict("A conflicting change was saved at the same moment. Retry the request.",
                       code="concurrent_change") from exc
    return JSONResponse(out, status_code=status)


def read[T](actor: Actor, fn: Callable[[Session], T]) -> T:
    with session_for(actor) as s:
        return fn(s)


class BadRange(DomainError):
    status = 416
    code = "range_not_satisfiable"


def parse_range(header: str | None, size: int) -> tuple[int, int] | None:
    """Parse one ``bytes=`` range (RFC 9110). None means the whole file."""
    if header is None:
        return None
    m = re.fullmatch(r"bytes=(\d*)-(\d*)", header.strip())
    if m is None or (not m.group(1) and not m.group(2)):
        raise DomainError("Malformed Range header.", code="bad_range")
    lo, hi = m.group(1), m.group(2)
    if not lo:  # suffix range: the last N bytes
        n = int(hi)
        if n == 0:
            raise BadRange("Range not satisfiable.", extra={"size": size})
        return max(0, size - n), size - 1
    start = int(lo)
    end = min(int(hi), size - 1) if hi else size - 1
    if start >= size or (hi and int(hi) < start):
        raise BadRange("Range not satisfiable.", extra={"size": size})
    return start, end


CHUNK = 1024 * 1024


def read_chunks(key: str, start: int, end: int) -> Iterator[bytes]:
    pos = start
    st = storage.store()
    while pos <= end:
        part = st.read(key, pos, min(pos + CHUNK, end + 1) - 1)
        if not part:
            return
        yield part
        pos += len(part)


def uid(value: str) -> uuid.UUID:
    try:
        return uuid.UUID(value)
    except ValueError as exc:
        raise NotFound("Not found.") from exc


# ---------------------------------------------------------------- app


def create_app() -> FastAPI:
    cfg = config.settings()
    app = FastAPI(title="StrataScribe BC API", version="b1", docs_url=None, redoc_url=None, openapi_url=None)

    @app.middleware("http")
    async def correlation(request: Request, call_next: Callable[[Request], Awaitable[Response]]) -> Response:
        incoming = request.headers.get("x-correlation-id")
        try:
            corr = str(uuid.UUID(incoming)) if incoming else clog.new_correlation_id()
        except ValueError:
            corr = clog.new_correlation_id()
        token = clog.set_correlation_id(corr)
        start = time.monotonic()
        try:
            response = await call_next(request)
        finally:
            clog.reset_correlation_id(token)
        response.headers["X-Correlation-ID"] = corr
        response.headers["Cache-Control"] = "no-store"
        response.headers["X-Content-Type-Options"] = "nosniff"
        log.info("request", extra={"method": request.method, "route": request.url.path,
                                   "status_code": response.status_code, "correlation_id": corr,
                                   "duration_ms": int((time.monotonic() - start) * 1000)})
        return response

    @app.exception_handler(DomainError)
    async def domain_error(request: Request, exc: DomainError) -> JSONResponse:
        if isinstance(exc, (authz.AccessDenied, authz.ForeignOrMissing)):
            actor = getattr(request.state, "actor", None)
            if actor is not None:
                authz.record_denial(actor, exc)
        if exc.code == "forbidden_request":
            exc.status = 403
        return _error(exc)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request: Request, exc: RequestValidationError) -> JSONResponse:
        fields = [".".join(str(p) for p in e.get("loc", ())) for e in exc.errors()]
        return _error(Invalid("Invalid request parameters.", code="invalid_request", extra={"fields": fields}))

    @app.exception_handler(Exception)
    async def unexpected_error(request: Request, exc: Exception) -> JSONResponse:
        # No exception text in the response or the log: it can carry content (B1-011).
        log.error("unhandled error", extra={"route": request.url.path, "error_code": type(exc).__name__})
        return _error(DomainError("Something went wrong. Quote the reference to support.", code="internal_error"),
                      status=500)

    def actor_dep(request: Request) -> Actor:
        guard_request(request)
        a = current_actor(request)
        request.state.actor = a
        return a

    A = Depends(actor_dep)
    B = Depends(json_body)
    v1 = "/api/v1"

    # ---- health
    @app.get("/healthz")
    def healthz() -> dict[str, str]:
        return {"status": "ok"}

    @app.get("/readyz")
    def readyz() -> JSONResponse:
        checks: dict[str, str] = {}
        try:
            with session_for(Actor.system()) as s:
                s.execute(text("SELECT 1"))
                checks["database"] = "ok"
                mismatch = jobs.config_mismatch(s, cfg.fingerprint())
                checks["configuration"] = "configuration mismatch" if mismatch else "ok"
        except Exception:  # noqa: BLE001
            checks["database"] = "unavailable"
        try:
            sessions.client().ping()
            checks["redis"] = "ok"
        except Exception:  # noqa: BLE001
            checks["redis"] = "unavailable"
        try:
            st = storage.store()
            ok = not isinstance(st, storage.LocalObjectStore) or st.root.is_dir()
            checks["storage"] = "ok" if ok else "unavailable"
        except Exception:  # noqa: BLE001
            checks["storage"] = "unavailable"
        ready = all(v == "ok" for v in checks.values())
        return JSONResponse({"ready": ready, "checks": checks, "fingerprint": cfg.fingerprint()},
                            status_code=200 if ready else 503)

    @app.get(v1 + "/me")
    def me(actor: Actor = A) -> dict[str, Any]:
        return {"user_id": str(actor.user_id), "brokerage_id": str(actor.brokerage_id), "role": actor.role}

    # ---- buildings
    @app.get(v1 + "/buildings")
    def list_buildings(actor: Actor = A) -> list[dict[str, Any]]:
        return read(actor, lambda s: [buildings.building_out(b) for b in buildings.list_buildings(s, actor)])

    @app.get(v1 + "/buildings/{strata_id}")
    def get_building(strata_id: str, actor: Actor = A) -> dict[str, Any]:
        return read(actor, lambda s: buildings.building_out(buildings.get_building(s, actor, uid(strata_id))))

    @app.put(v1 + "/buildings/{strata_id}/assignments/{user_id}")
    def assign(strata_id: str, user_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            buildings.assign(s, actor, uid(strata_id), uid(user_id))
            return 200, {"assigned": True}
        return mutate(actor, request, body, fn)

    @app.delete(v1 + "/buildings/{strata_id}/assignments/{user_id}")
    def unassign(strata_id: str, user_id: str, request: Request, actor: Actor = A) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            buildings.unassign(s, actor, uid(strata_id), uid(user_id))
            return 200, {"assigned": False}
        return mutate(actor, request, {}, fn)

    # ---- meetings
    @app.get(v1 + "/buildings/{strata_id}/meetings")
    def list_meetings(strata_id: str, actor: Actor = A) -> list[dict[str, Any]]:
        from core.models import Meeting

        def fn(s: Session) -> list[dict[str, Any]]:
            sid = uid(strata_id)
            authz.locate(s, actor, "building", sid)
            rows = s.scalars(select(Meeting).where(Meeting.strata_id == sid).order_by(Meeting.held_on.desc()))
            return [meetings.meeting_out(m) for m in rows]
        return read(actor, fn)

    @app.post(v1 + "/buildings/{strata_id}/meetings")
    def create_meeting(strata_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        return mutate(actor, request, body,
                      lambda s: (201, meetings.meeting_out(meetings.create_meeting(s, actor, uid(strata_id), body))))

    @app.get(v1 + "/meetings/{meeting_id}")
    def get_meeting(meeting_id: str, actor: Actor = A) -> dict[str, Any]:
        def fn(s: Session) -> dict[str, Any]:
            m = meetings.get_meeting(s, actor, uid(meeting_id))
            audit.record(s, actor, "meeting.opened", strata_id=m.strata_id, target_type="meeting", target_id=m.id)
            auth = meetings.current_authorization(s, m.id)
            out = meetings.meeting_out(m)
            out["recording_authorization"] = None if auth is None else {
                "id": str(auth.id), "basis": auth.basis, "bylaw_clause_id": str(auth.bylaw_clause_id)
                if auth.bylaw_clause_id else None, "attested_by": str(auth.attested_by),
                "attested_at": auth.attested_at.isoformat(), "notice_text_version": auth.notice_text_version}
            return out
        return read(actor, fn)

    @app.put(v1 + "/meetings/{meeting_id}/recording-authorization")
    def put_authorization(meeting_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            a = meetings.record_authorization(s, actor, uid(meeting_id), body)
            return 200, {"id": str(a.id), "basis": a.basis}
        return mutate(actor, request, body, fn)

    # ---- uploads and audio
    @app.post(v1 + "/meetings/{meeting_id}/uploads")
    def init_upload(meeting_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            a, created = meetings.init_upload(s, actor, uid(meeting_id), body)
            return (201 if created else 200), meetings.upload_out(a)
        return mutate(actor, request, body, fn)

    @app.patch(v1 + "/uploads/{asset_id}")
    async def append(asset_id: str, request: Request, offset: int, actor: Actor = A) -> JSONResponse:
        data = await request.body()
        with session_for(actor) as s:
            a = meetings.append_part(s, actor, uid(asset_id), offset, data)
            return JSONResponse(meetings.upload_out(a))

    @app.post(v1 + "/uploads/{asset_id}/complete")
    def complete(asset_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            a = meetings.complete_upload(s, actor, uid(asset_id))
            if a.upload_state == "failed":
                return 422, {"error": {"code": "checksum_mismatch", "message": "Checksum mismatch: upload the file "
                                       "again.", "correlation_id": clog.correlation_id()}}
            return 200, meetings.upload_out(a)
        return mutate(actor, request, body, fn)

    @app.get(v1 + "/audio-assets/{asset_id}/stream")
    def stream(asset_id: str, request: Request, actor: Actor = A) -> Response:
        with session_for(actor) as s:
            loc = authz.locate(s, actor, "audio_asset", uid(asset_id))  # checked on every range request
            a = s.get(AudioAsset, loc.id)
            if a is None or a.upload_state != "complete" or a.deleted_at is not None:
                raise NotFound("Not found.")
            size = a.byte_size
            rng = request.headers.get("range")
            span = parse_range(rng, size)  # 400 / 416 before any byte is read (B1-007)
            start, end = span if span is not None else (0, size - 1)
            if start == 0:
                audit.record(s, actor, "audio.streamed", strata_id=a.strata_id, target_type="audio_asset",
                             target_id=a.id)
            key = a.storage_key
        headers = {"Accept-Ranges": "bytes", "Content-Length": str(end - start + 1)}
        if span is not None:
            headers["Content-Range"] = f"bytes {start}-{end}/{size}"
        return StreamingResponse(read_chunks(key, start, end), status_code=206 if span is not None else 200,
                                 media_type="application/octet-stream", headers=headers)

    @app.post(v1 + "/meetings/{meeting_id}/process")
    def process(meeting_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            job_id = meetings.request_processing(s, actor, uid(meeting_id), cfg.asr_model_id)
            return 202, {"job_id": str(job_id)}
        return mutate(actor, request, body, fn)

    @app.get(v1 + "/meetings/{meeting_id}/status")
    def status(meeting_id: str, actor: Actor = A) -> dict[str, Any]:
        return read(actor, lambda s: meetings.status_out(s, actor, uid(meeting_id)))

    @app.get(v1 + "/meetings/{meeting_id}/transcript")
    def transcript(meeting_id: str, offset: int = Query(0, ge=0), limit: int = Query(200, ge=1, le=500),
                   actor: Actor = A) -> dict[str, Any]:
        def fn(s: Session) -> dict[str, Any]:
            m = meetings.get_meeting(s, actor, uid(meeting_id))
            t = s.scalar(select(Transcript).where(Transcript.meeting_id == m.id))
            if t is None:
                return {"segments": []}
            if offset == 0:
                audit.record(s, actor, "transcript.read", strata_id=m.strata_id, target_type="meeting",
                             target_id=m.id)
            segs = s.scalars(select(TranscriptSegment).where(TranscriptSegment.transcript_id == t.id)
                             .order_by(TranscriptSegment.seq).offset(offset).limit(min(limit, 500)))
            return {"segments": [{"id": str(g.id), "seq": g.seq, "start_ms": g.start_ms, "end_ms": g.end_ms,
                                  "speaker_label": g.speaker_label, "speaker_name": g.speaker_name,
                                  "text": g.text} for g in segs]}
        return read(actor, fn)

    # ---- review
    @app.get(v1 + "/meetings/{meeting_id}/draft")
    def draft(meeting_id: str, actor: Actor = A) -> dict[str, Any]:
        return read(actor, lambda s: review.draft_out(s, actor, uid(meeting_id)))

    @app.post(v1 + "/meetings/{meeting_id}/minute-items")
    def add_item(meeting_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        return mutate(actor, request, body,
                      lambda s: (201, review.item_out(review.add_item(s, actor, uid(meeting_id), body))))

    @app.patch(v1 + "/minute-items/{item_id}")
    def patch_item(item_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        raw = request.headers.get("if-match")
        try:
            if_match = int(raw.strip('"')) if raw else None
        except ValueError as exc:
            raise Invalid("If-Match must be the item's row_version.") from exc
        return mutate(actor, request, body,
                      lambda s: (200, review.item_out(review.update_item(s, actor, uid(item_id), if_match,
                                                                          dict(body)))))

    @app.delete(v1 + "/minute-items/{item_id}")
    def delete_item(item_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            review.delete_item(s, actor, uid(item_id), body.get("reason"))
            return 200, {"deleted": True}
        return mutate(actor, request, body, fn)

    @app.post(v1 + "/minute-items/{item_id}/citations")
    def add_citation(item_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            c = review.add_citation(s, actor, uid(item_id), body)
            return 201, {"id": str(c.id), "status": c.status}
        return mutate(actor, request, body, fn)

    @app.delete(v1 + "/minute-item-citations/{citation_id}")
    def remove_citation(citation_id: str, request: Request, actor: Actor = A) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            review.remove_citation(s, actor, uid(citation_id))
            return 200, {"removed": True}
        return mutate(actor, request, {}, fn)

    @app.post(v1 + "/meetings/{meeting_id}/activity/heartbeat")
    def heartbeat(meeting_id: str, actor: Actor = A, body: Body = B) -> dict[str, Any]:
        with session_for(actor) as s:
            return activity.heartbeat(s, actor, uid(meeting_id), str(body.get("activity")))

    @app.put(v1 + "/meetings/{meeting_id}/time-report")
    def time_report(meeting_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            r = activity.put_time_report(s, actor, uid(meeting_id), body)
            return 200, {"meeting_id": str(r.meeting_id), "row_version": r.row_version}
        return mutate(actor, request, body, fn)

    @app.post(v1 + "/meetings/{meeting_id}/approve")
    def approve(meeting_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            a = approval.approve(s, actor, uid(meeting_id), body)
            return 200, {"approval_id": str(a.id), "content_hash": a.content_hash.hex()}
        return mutate(actor, request, body, fn)

    @app.post(v1 + "/meetings/{meeting_id}/reopen")
    def reopen(meeting_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            v = approval.reopen(s, actor, uid(meeting_id), body)
            return 200, {"version": v.version, "version_id": str(v.id)}
        return mutate(actor, request, body, fn)

    # ---- bylaws and questions
    @app.get(v1 + "/buildings/{strata_id}/bylaw-documents")
    def list_docs(strata_id: str, actor: Actor = A) -> list[dict[str, Any]]:
        return read(actor, lambda s: [bylaws.document_out(d) for d in bylaws.list_documents(s, actor, uid(strata_id))])

    @app.post(v1 + "/buildings/{strata_id}/bylaw-documents")
    def create_doc(strata_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            d = bylaws.create_document(s, actor, uid(strata_id), body)
            return 201, bylaws.document_out(*bylaws.get_document(s, actor, d.id))
        return mutate(actor, request, body, fn)

    @app.get(v1 + "/bylaw-documents/{doc_id}")
    def get_doc(doc_id: str, actor: Actor = A) -> dict[str, Any]:
        return read(actor, lambda s: bylaws.document_out(*bylaws.get_document(s, actor, uid(doc_id))))

    @app.post(v1 + "/bylaw-documents/{doc_id}/confirm")
    def confirm_doc(doc_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        return mutate(actor, request, body,
                      lambda s: (200, bylaws.document_out(bylaws.confirm(s, actor, uid(doc_id)))))

    @app.post(v1 + "/buildings/{strata_id}/questions")
    def ask(strata_id: str, request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        return mutate(actor, request, body,
                      lambda s: (200, qa.ask(s, actor, uid(strata_id), str(body.get("question", "")), llm_client)))

    @app.get(v1 + "/buildings/{strata_id}/questions")
    def questions(strata_id: str, actor: Actor = A) -> list[dict[str, Any]]:
        return read(actor, lambda s: qa.history(s, actor, uid(strata_id)))

    # ---- pilot measurement
    @app.post(v1 + "/pilot/baselines")
    def add_baseline(request: Request, actor: Actor = A, body: Body = B) -> JSONResponse:
        def fn(s: Session) -> tuple[int, Any]:
            strata = uid(body["strata_id"]) if body.get("strata_id") else None
            if strata is not None:
                authz.locate(s, actor, "building", strata)
            try:
                row = BaselineMeasurement(
                    id=uuid7(), brokerage_id=actor.brokerage_id, strata_id=strata, user_id=actor.user_id,
                    meeting_type=body["meeting_type"], meeting_length_minutes=int(body["meeting_length_minutes"]),
                    drafting_minutes=int(body["drafting_minutes"]), method=body["method"],
                    noted_on=date.fromisoformat(body["noted_on"]))
            except (KeyError, ValueError) as exc:
                raise Invalid("meeting_type, meeting_length_minutes, drafting_minutes, method, noted_on.") from exc
            s.add(row)
            s.flush()
            return 201, {"id": str(row.id)}
        return mutate(actor, request, body, fn)

    @app.get(v1 + "/pilot/report")
    def report(actor: Actor = A) -> dict[str, Any]:
        def fn(s: Session) -> dict[str, Any]:
            facts, bases = pilot.collect(s, actor)
            return pilot.report_out(pilot.build_report(facts, bases))
        return read(actor, fn)

    @app.get(v1 + "/audit-events")
    def audit_events(actor: Actor = A) -> list[dict[str, Any]]:
        def fn(s: Session) -> list[dict[str, Any]]:
            authz.require_broker(actor)
            rows = s.scalars(select(AuditEvent).order_by(AuditEvent.occurred_at.desc()).limit(500))
            return [{"action": r.action, "outcome": r.outcome, "actor_id": str(r.actor_id) if r.actor_id else None,
                     "strata_id": str(r.strata_id) if r.strata_id else None, "target_type": r.target_type,
                     "target_id": str(r.target_id) if r.target_id else None, "details": r.details,
                     "occurred_at": r.occurred_at.isoformat()} for r in rows]
        return read(actor, fn)

    return app
