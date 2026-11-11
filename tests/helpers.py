"""Helpers shared by tests: a signed-in API client and the common meeting flow."""

from __future__ import annotations

import hashlib
import os
from pathlib import Path
from typing import Any

from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parents[1]
FIXTURES = ROOT / "tests" / "fixtures"
CSRF = {"X-StrataScribe-Request": "1", "Origin": "http://localhost:3106"}


class Api:
    """A signed-in user's HTTP client."""

    def __init__(self, client: TestClient, token: str | None) -> None:
        self.c = client
        self.token = token

    def _h(self, extra: dict[str, str] | None = None, mutating: bool = True) -> dict[str, str]:
        h = dict(CSRF) if mutating else {}
        if extra:
            h.update(extra)
        return h

    def _cookies(self) -> dict[str, str]:
        return {"ss_session": self.token} if self.token else {}

    def get(self, path: str, **kw: Any) -> Any:
        self.c.cookies.clear()
        return self.c.get("/api/v1" + path, cookies=self._cookies(), headers=kw.pop("headers", None), **kw)

    def send(self, method: str, path: str, json: Any = None, headers: dict[str, str] | None = None,
             content: bytes | None = None, params: dict[str, Any] | None = None) -> Any:
        self.c.cookies.clear()
        return self.c.request(method, "/api/v1" + path, json=json, content=content, params=params,
                              headers=self._h(headers), cookies=self._cookies())

    def post(self, path: str, json: Any = None, **kw: Any) -> Any:
        return self.send("POST", path, json if json is not None else {}, **kw)

    def put(self, path: str, json: Any = None, **kw: Any) -> Any:
        return self.send("PUT", path, json if json is not None else {}, **kw)

    def patch(self, path: str, json: Any = None, **kw: Any) -> Any:
        return self.send("PATCH", path, json, **kw)

    def delete(self, path: str, json: Any = None, **kw: Any) -> Any:
        return self.send("DELETE", path, json, **kw)


def fake_wav(payload: bytes = b"synthetic-audio") -> bytes:
    body = b"WAVEfmt " + payload
    return b"RIFF" + len(body).to_bytes(4, "little") + body


def sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def bylaw_text(name: str) -> str:
    return (FIXTURES / name).read_text()


# ---------------------------------------------------------------- flows reused by several tests


def new_meeting(api: Api, strata_id: Any, **kw: Any) -> dict[str, Any]:
    body = {"meeting_type": "council", "held_on": "2026-10-15", "format": "in_person", "source_type": "recording",
            "length_minutes": 90}
    body.update(kw)
    r = api.post(f"/buildings/{strata_id}/meetings", body)
    assert r.status_code == 201, r.text
    return dict(r.json())


def authorize(api: Api, meeting_id: str, **kw: Any) -> Any:
    body = {"basis": "bylaw", "bylaw_reference_text": "Bylaw 8(1)", "notice_text_version": "notice-2026.11.1"}
    body.update(kw)
    return api.put(f"/meetings/{meeting_id}/recording-authorization", body)


def upload(api: Api, meeting_id: str, data: bytes, ext: str = "wav") -> dict[str, Any]:
    r = api.post(f"/meetings/{meeting_id}/uploads", {"sha256": sha(data), "byte_size": len(data), "extension": ext})
    assert r.status_code in (200, 201), r.text
    a = r.json()
    if a["upload_state"] == "receiving":
        r = api.patch(f"/uploads/{a['id']}", content=data, params={"offset": a["received_bytes"]},
                      headers={"content-type": "application/octet-stream"})
        assert r.status_code == 200, r.text
        r = api.post(f"/uploads/{a['id']}/complete")
        assert r.status_code == 200, r.text
    return dict(r.json())


def drain_worker() -> int:
    from worker.main import drain

    return drain("test-worker")


def processed_meeting(api: Api, strata_id: Any, **kw: Any) -> dict[str, Any]:
    """Create -> authorize -> upload -> process -> drain the worker -> ready_for_review."""
    m = new_meeting(api, strata_id, **kw)
    assert authorize(api, m["id"]).status_code == 200
    upload(api, m["id"], fake_wav(os.urandom(8)))
    assert api.post(f"/meetings/{m['id']}/process").status_code == 202
    drain_worker()
    return m


def review_quorum(api: Api, meeting_id: str, **fields: Any) -> dict[str, Any]:
    """Complete the draft's quorum item (default: declared established by the chair, attested)."""
    d = api.get(f"/meetings/{meeting_id}/draft").json()
    q = next(i for i in d["items"] if i["item_type"] == "quorum")
    body = fields or {"quorum_basis": "declared", "quorum_statement": "established"}
    r = api.patch(f"/minute-items/{q['id']}", {**body, "reviewed": True}, headers={"If-Match": str(q["row_version"])})
    assert r.status_code == 200, r.text
    return dict(r.json())
