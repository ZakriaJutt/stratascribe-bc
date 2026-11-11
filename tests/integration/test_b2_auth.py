"""B2 sign-in end to end against the local Mailpit inbox (T-2.2.2; I-17, I-18, I-19, I-20; S-01, S-05).

Every address used here is created by the test (``b2-<random>@harbourline.example``) or is a seeded
synthetic user, and every message sent to it is deleted from Mailpit at teardown. Authenticator codes
are computed from the setup key returned at enrolment.
"""

from __future__ import annotations

import base64
import re
import time
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime, timedelta
from typing import Any

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, text
from sqlalchemy.exc import DBAPIError

from core import clock, config, sessions, totp
from core.db import Actor, session_for
from core.devdata import World
from core.ids import uuid7
from tests.helpers import CSRF, Api, mailpit_delete, mailpit_find, mailpit_text, processed_meeting

pytestmark = pytest.mark.db
V1 = "/api/v1"


# ---------------------------------------------------------------- helpers


class Clock:
    """A movable clock for expiry tests; starts at the real time."""

    def __init__(self) -> None:
        self.t = datetime.now(UTC)
        clock.set_clock(lambda: self.t)

    def advance(self, **kw: float) -> None:
        self.t += timedelta(**kw)


@pytest.fixture
def mailbox() -> Iterator[list[str]]:
    used: list[str] = []
    yield used
    for to in used:
        mailpit_delete(to)


def fresh_email(mailbox: list[str]) -> str:
    e = f"b2-{uuid.uuid4().hex[:12]}@harbourline.example"
    mailbox.append(e)
    return e


def wait_for_mail(to: str, count: int = 1) -> list[dict[str, Any]]:
    for _ in range(50):
        msgs = mailpit_find(to)
        if len(msgs) >= count:
            return msgs
        time.sleep(0.1)
    raise AssertionError(f"expected {count} message(s) in Mailpit")


def latest_token(to: str, count: int = 1) -> str:
    msgs = wait_for_mail(to, count)
    newest = max(msgs, key=lambda m: str(m["Created"]))
    m = re.search(r"/sign-in\?token=([A-Za-z0-9_\-]+)", mailpit_text(str(newest["ID"])))
    assert m, "no sign-in link in the message"
    return m.group(1)


def set_cookies(r: Any) -> dict[str, str]:
    """Raw Set-Cookie headers by cookie name."""
    out = {}
    for h in r.headers.get_list("set-cookie"):
        out[h.split("=", 1)[0]] = h
    return out


def cookie_value(header: str) -> str:
    return header.split("=", 1)[1].split(";", 1)[0].strip('"')


def ask_link(client: TestClient, email: str, nonce: str | None = None, **extra: Any) -> Any:
    client.cookies.clear()
    cookies = {"ss_signin": nonce} if nonce else {}
    return client.post(V1 + "/auth/magic-link", json={"email": email, **extra}, headers=CSRF, cookies=cookies)


def auth_post(client: TestClient, path: str, body: dict[str, Any], nonce: str | None) -> Any:
    client.cookies.clear()
    return client.post(V1 + path, json=body, headers=CSRF, cookies={"ss_signin": nonce} if nonce else {})


def code_now(setup_key: str, offset_steps: int = 0) -> str:
    secret = base64.b32decode(setup_key + "=" * (-len(setup_key) % 8))
    return totp.code_for(secret, totp.step_at(clock.now()) + offset_steps)


def invite(marta: Api, email: str, role: str = "strata_manager") -> dict[str, Any]:
    r = marta.post("/invitations", {"email": email, "full_name": "Test Member", "role": role})
    assert r.status_code == 201, r.text
    return dict(r.json())


def sign_in(client: TestClient, email: str, mail_count: int = 1) -> tuple[str, str]:
    """Full first sign-in: link from Mailpit, enrol, code. Returns (session token, setup key)."""
    r = ask_link(client, email)
    nonce = cookie_value(set_cookies(r)["ss_signin"])
    token = latest_token(email, mail_count)
    client.cookies.clear()
    assert client.get(V1 + "/auth/callback", params={"token": token},
                      cookies={"ss_signin": nonce}).json() == {"next_step": "enrol"}
    key = auth_post(client, "/auth/totp/enrol", {"token": token}, nonce).json()["setup_key"]
    r = auth_post(client, "/auth/totp/verify", {"token": token, "code": code_now(key)}, nonce)
    assert r.status_code == 200, r.text
    return cookie_value(set_cookies(r)["ss_session"]), key


def me(client: TestClient, token: str) -> Any:
    client.cookies.clear()
    return client.get(V1 + "/me", cookies={"ss_session": token})


def owner(sql: str, **p: Any) -> Any:
    eng = create_engine(config.settings().migration_database_url)
    with eng.begin() as c:
        v = c.execute(text(sql), p).all()
    eng.dispose()
    return v


# ---------------------------------------------------------------- end to end


def test_b2_invitation_link_enrolment_code_session(world: World, client: TestClient, as_user: Any,
                                                    mailbox: list[str]) -> None:
    marta = as_user(world.marta)
    email = fresh_email(mailbox)
    member = invite(marta, email)
    assert member["status"] == "invited"
    invitation = mailpit_text(str(wait_for_mail(email)[0]["ID"]))
    assert "http://localhost:3106/sign-in" in invitation and "token=" not in invitation

    r = ask_link(client, email, next="/buildings/abc")
    assert r.status_code == 202
    nonce_header = set_cookies(r)["ss_signin"]
    for attr in ("HttpOnly", "Secure", "SameSite=lax", "Path=/api/v1/auth", "Max-Age=600"):
        assert attr.lower() in nonce_header.lower(), (attr, nonce_header)
    nonce = cookie_value(nonce_header)
    token = latest_token(email, 2)
    assert len(base64.urlsafe_b64decode(token + "=" * (-len(token) % 4))) == 32  # 32 random bytes

    client.cookies.clear()
    assert client.get(V1 + "/auth/callback", params={"token": token},
                      cookies={"ss_signin": nonce}).json() == {"next_step": "enrol"}
    enrol = auth_post(client, "/auth/totp/enrol", {"token": token}, nonce).json()
    assert enrol["otpauth_uri"].startswith("otpauth://totp/") and len(enrol["setup_key"]) == 32
    bad = auth_post(client, "/auth/totp/verify", {"token": token, "code": "000000" if code_now(enrol["setup_key"])
                                                  != "000000" else "111111"}, nonce)
    assert bad.status_code == 400 and bad.json()["error"]["code"] == "code_mismatch"
    assert "ss_session" not in set_cookies(bad)  # no session until the code is accepted
    ok = auth_post(client, "/auth/totp/verify", {"token": token, "code": code_now(enrol["setup_key"])}, nonce)
    assert ok.status_code == 200 and ok.json()["next"] == "/buildings/abc"
    session_header = set_cookies(ok)["ss_session"]
    for attr in ("HttpOnly", "Secure", "SameSite=lax", "Path=/"):
        assert attr.lower() in session_header.lower(), (attr, session_header)
    body = me(client, cookie_value(session_header)).json()
    assert body["user_id"] == member["id"] and body["role"] == "strata_manager"
    rows = owner("SELECT status, totp_enrolled_at IS NOT NULL, totp_secret_encrypted IS NOT NULL FROM users "
                 "WHERE id = :i", i=member["id"])
    assert tuple(rows[0]) == ("active", True, True)
    # The stored secret is encrypted: the setup key's bytes do not appear in it.
    blob = owner("SELECT totp_secret_encrypted FROM users WHERE id = :i", i=member["id"])[0][0]
    assert base64.b32decode(enrol["setup_key"] + "=" * (-len(enrol["setup_key"]) % 8)) not in bytes(blob)
    # The stored session holds only an HMAC of the cookie token.
    stored = owner("SELECT token_hash FROM web_sessions WHERE user_id = :i", i=member["id"])
    assert cookie_value(session_header).encode() not in bytes(stored[0][0])
    # Audit: link requested, code rejected, signed in.
    actions = [e["action"] for e in marta.get("/audit-events").json() if e["target_id"] == member["id"]]
    assert {"member.invited", "auth.link_requested", "auth.code_rejected", "auth.signed_in"} <= set(actions)


def test_b2_second_sign_in_uses_code_and_refuses_replayed_code(world: World, client: TestClient, as_user: Any,
                                                              mailbox: list[str]) -> None:
    clk = Clock()
    email = fresh_email(mailbox)
    invite(as_user(world.marta), email)
    _, key = sign_in(client, email, mail_count=2)
    used = code_now(key)
    r = ask_link(client, email)
    nonce = cookie_value(set_cookies(r)["ss_signin"])
    token = latest_token(email, 3)
    client.cookies.clear()
    assert client.get(V1 + "/auth/callback", params={"token": token},
                      cookies={"ss_signin": nonce}).json() == {"next_step": "code"}
    assert auth_post(client, "/auth/totp/enrol", {"token": token}, nonce).json()["error"]["code"] == \
        "already_enrolled"
    replay = auth_post(client, "/auth/totp/verify", {"token": token, "code": used}, nonce)
    assert replay.status_code == 400 and replay.json()["error"]["code"] == "code_mismatch"
    clk.advance(seconds=60)
    ok = auth_post(client, "/auth/totp/verify", {"token": token, "code": code_now(key)}, nonce)
    assert ok.status_code == 200, ok.text


def test_b2_unknown_email_gets_identical_response(world: World, client: TestClient, mailbox: list[str]) -> None:
    known, unknown = "priya@harbourline.example", fresh_email(mailbox)
    mailbox.append(known)
    a, b = ask_link(client, known), ask_link(client, unknown)
    assert a.status_code == b.status_code == 202 and a.json() == b.json()
    ca, cb = set_cookies(a)["ss_signin"], set_cookies(b)["ss_signin"]
    assert ca.replace(cookie_value(ca), "") == cb.replace(cookie_value(cb), "")
    assert sorted(a.headers.keys()) == sorted(b.headers.keys())
    wait_for_mail(known)
    time.sleep(0.3)
    assert mailpit_find(unknown) == []
    # Deactivated users get the same answer and no email.
    with session_for(Actor.user(world.marta, world.harbourline, "managing_broker")) as s:
        s.execute(text("UPDATE users SET status = 'deactivated' WHERE id = :i"), {"i": world.daniel})
    mailbox.append("daniel@harbourline.example")
    c = ask_link(client, "daniel@harbourline.example")
    assert c.status_code == 202 and c.json() == a.json()
    time.sleep(0.3)
    assert mailpit_find("daniel@harbourline.example") == []
    bad = ask_link(client, "not-an-address")
    assert bad.status_code == 422 and bad.json()["error"]["code"] == "invalid_email"


def test_b2_i18_expired_reused_and_other_browser_links_refused(world: World, client: TestClient, as_user: Any,
                                                              mailbox: list[str]) -> None:
    clk = Clock()
    email = fresh_email(mailbox)
    invite(as_user(world.marta), email)
    r = ask_link(client, email)
    nonce = cookie_value(set_cookies(r)["ss_signin"])
    token = latest_token(email, 2)
    # Different browser: no nonce cookie, or another browser's nonce.
    client.cookies.clear()
    for other in (None, "another-browser-nonce-0123456789"):
        r = client.get(V1 + "/auth/callback", params={"token": token},
                       cookies={"ss_signin": other} if other else {})
        assert r.status_code == 400 and r.json()["error"]["code"] == "link_other_browser"
    key = auth_post(client, "/auth/totp/enrol", {"token": token}, nonce).json()["setup_key"]
    # Expired: 11 minutes later the same link and a correct code are refused.
    clk.advance(minutes=11)
    r = auth_post(client, "/auth/totp/verify", {"token": token, "code": code_now(key)}, nonce)
    assert r.status_code == 400 and r.json()["error"]["code"] == "link_expired"
    assert r.json()["error"]["message"] == "This link has expired. Send a new one."
    # A fresh link works once; the second use is refused.
    r = ask_link(client, email, nonce=nonce)
    token2 = latest_token(email, 3)
    assert cookie_value(set_cookies(r)["ss_signin"]) == nonce  # same browser keeps its nonce
    key = auth_post(client, "/auth/totp/enrol", {"token": token2}, nonce).json()["setup_key"]
    assert auth_post(client, "/auth/totp/verify", {"token": token2, "code": code_now(key)}, nonce).status_code == 200
    clk.advance(seconds=60)
    again = auth_post(client, "/auth/totp/verify", {"token": token2, "code": code_now(key)}, nonce)
    assert again.status_code == 400 and again.json()["error"]["code"] == "link_expired"
    client.cookies.clear()
    assert client.get(V1 + "/auth/callback", params={"token": token2},
                      cookies={"ss_signin": nonce}).json()["error"]["code"] == "link_expired"
    # A made-up token looks exactly like an expired one.
    assert client.get(V1 + "/auth/callback", params={"token": "x" * 43},
                      cookies={"ss_signin": nonce}).json()["error"]["code"] == "link_expired"


def test_b2_five_wrong_codes_end_the_link(world: World, client: TestClient, as_user: Any,
                                         mailbox: list[str]) -> None:
    email = fresh_email(mailbox)
    invite(as_user(world.marta), email)
    r = ask_link(client, email)
    nonce = cookie_value(set_cookies(r)["ss_signin"])
    token = latest_token(email, 2)
    key = auth_post(client, "/auth/totp/enrol", {"token": token}, nonce).json()["setup_key"]
    good = code_now(key)
    wrong = [c for c in ("000000", "111111", "222222", "333333", "444444", "555555") if c != good][:5]
    codes = [auth_post(client, "/auth/totp/verify", {"token": token, "code": c}, nonce) for c in wrong]
    assert [c.status_code for c in codes] == [400, 400, 400, 400, 429]
    assert codes[-1].json()["error"]["code"] == "attempts_exhausted"
    r = auth_post(client, "/auth/totp/verify", {"token": token, "code": good}, nonce)
    assert r.status_code == 429 and "ss_session" not in set_cookies(r)


def test_b2_i17_sign_in_requests_rate_limited_per_email_and_ip(world: World, client: TestClient,
                                                              mailbox: list[str]) -> None:
    email = "priya@harbourline.example"
    mailbox.append(email)
    codes = [ask_link(client, email).status_code for _ in range(6)]
    assert codes == [202] * 5 + [429]
    r = ask_link(client, email)
    assert r.json()["error"]["code"] == "rate_limited" and int(r.headers["Retry-After"]) > 0
    assert "Too many sign-in requests" in r.json()["error"]["message"]
    assert len(wait_for_mail(email, 5)) == 5
    # Per IP address: 20 per hour across any addresses (7 already counted above from this client).
    others = [fresh_email(mailbox) for _ in range(14)]
    results = [ask_link(client, e).status_code for e in others]
    assert results == [202] * 13 + [429]


def test_b2_next_accepts_only_same_site_paths(world: World, client: TestClient, as_user: Any,
                                             mailbox: list[str]) -> None:
    from core.auth import safe_next

    assert safe_next("/meetings/1?tab=review") == "/meetings/1?tab=review"
    for bad in ("//evil.example/x", "https://evil.example", "/\\evil.example", "javascript:alert(1)", "", None):
        assert safe_next(bad) is None
    email = fresh_email(mailbox)
    invite(as_user(world.marta), email)
    r = ask_link(client, email, next="//evil.example/")
    nonce = cookie_value(set_cookies(r)["ss_signin"])
    token = latest_token(email, 2)
    key = auth_post(client, "/auth/totp/enrol", {"token": token}, nonce).json()["setup_key"]
    ok = auth_post(client, "/auth/totp/verify", {"token": token, "code": code_now(key)}, nonce)
    assert ok.json()["next"] == "/buildings"


def test_b2_i19_sign_in_routes_need_the_request_header_and_origin(world: World, client: TestClient) -> None:
    client.cookies.clear()
    r = client.post(V1 + "/auth/magic-link", json={"email": "priya@harbourline.example"})
    assert r.status_code == 403
    r = client.post(V1 + "/auth/magic-link", json={"email": "priya@harbourline.example"},
                    headers={"X-StrataScribe-Request": "1", "Origin": "https://evil.example"})
    assert r.status_code == 403
    assert owner("SELECT count(*) FROM sign_in_links")[0][0] == 0


# ---------------------------------------------------------------- sessions


def test_b2_sign_out_ends_the_session(world: World, client: TestClient, as_user: Any, mailbox: list[str]) -> None:
    email = fresh_email(mailbox)
    invite(as_user(world.marta), email)
    token, _ = sign_in(client, email, mail_count=2)
    assert me(client, token).status_code == 200
    client.cookies.clear()
    assert client.post(V1 + "/auth/sign-out", cookies={"ss_session": token}).status_code == 403  # header needed
    r = client.post(V1 + "/auth/sign-out", headers=CSRF, cookies={"ss_session": token})
    assert r.status_code == 200 and 'ss_session=""' in r.headers["set-cookie"]
    assert me(client, token).status_code == 401
    assert owner("SELECT end_reason FROM web_sessions WHERE token_hash IS NOT NULL AND ended_at IS NOT NULL "
                 "AND user_id = (SELECT id FROM users WHERE email = :e)", e=email)[0][0] == "signed_out"


def test_b2_i20_idle_and_absolute_expiry(world: World, client: TestClient, as_user: Any) -> None:
    clk = Clock()
    idle = as_user(world.priya)
    clk.advance(minutes=59)
    assert idle.get("/me").status_code == 200  # activity slides the idle limit
    clk.advance(minutes=61)
    assert idle.get("/me").status_code == 401
    busy = as_user(world.daniel)
    for _ in range(14):  # active every 50 minutes for 11 h 40 min
        clk.advance(minutes=50)
        assert busy.get("/me").status_code == 200
    clk.advance(minutes=21)  # 12 h 1 min after creation
    assert busy.get("/me").status_code == 401
    reasons = sorted(r[0] for r in owner("SELECT end_reason FROM web_sessions WHERE ended_at IS NOT NULL"))
    assert reasons == ["absolute", "idle"]


def test_b2_cross_tenant_session_refused(world: World, client: TestClient, as_user: Any) -> None:
    priya = as_user(world.priya)
    m = processed_meeting(priya, world.zzs9001)
    omar = as_user(world.omar)
    assert omar.get(f"/meetings/{m['id']}").status_code == 404
    assert omar.get("/members").status_code == 403
    # A session cannot be carried into another brokerage by editing its row from a tenant context.
    with pytest.raises(DBAPIError), session_for(Actor.user(world.omar, world.tidewater, "strata_manager")) as s:
        s.execute(text("UPDATE web_sessions SET brokerage_id = :b"), {"b": world.harbourline})
    with session_for(Actor.user(world.omar, world.tidewater, "strata_manager")) as s:
        assert s.execute(text("SELECT count(*) FROM web_sessions WHERE brokerage_id = :b"),
                         {"b": world.harbourline}).scalar() == 0
        assert s.execute(text("SELECT count(*) FROM sign_in_links")).scalar() == 0
    # The sign-in context sees no building content.
    with session_for(Actor.auth()) as s:
        assert s.execute(text("SELECT count(*) FROM meetings")).scalar() == 0
        assert s.execute(text("SELECT count(*) FROM transcript_segments")).scalar() == 0
    # A tampered or random cookie is refused.
    assert Api(client, omar.token + "x").get("/me").status_code == 401
    assert Api(client, "random-token").get("/me").status_code == 401
    assert Api(client, None).get("/buildings").status_code == 401


def test_b2_omar_cross_brokerage_rows_after_real_sign_in(world: World, client: TestClient,
                                                        mailbox: list[str]) -> None:
    mailbox.append("omar@tidewater.example")
    token, _ = sign_in(client, "omar@tidewater.example")
    api = Api(client, token)
    assert api.get("/me").json()["brokerage_id"] == str(world.tidewater)
    assert [b["name"] for b in api.get("/buildings").json()] == ["Cedar Quay"]
    assert api.get(f"/buildings/{world.zzs9001}").status_code == 404


# ---------------------------------------------------------------- team: invitations and member changes


def test_b2_deactivation_role_change_and_reset_end_sessions(world: World, client: TestClient, as_user: Any,
                                                           mailbox: list[str]) -> None:
    marta = as_user(world.marta)
    priya_tabs = [as_user(world.priya), as_user(world.priya)]
    r = marta.patch(f"/members/{world.priya}", {"status": "deactivated"})
    assert r.status_code == 200 and r.json()["status"] == "deactivated"
    assert all(t.get("/buildings").status_code == 401 for t in priya_tabs)
    assert marta.patch(f"/members/{world.priya}", {"status": "active"}).status_code == 422  # never signed in
    daniel = as_user(world.daniel)
    assert marta.patch(f"/members/{world.daniel}", {"role": "managing_broker"}).status_code == 200
    assert daniel.get("/me").status_code == 401  # a role change ends sessions
    # Last-broker guard: Marta can now be demoted (Daniel is a broker), but Daniel then cannot be.
    assert marta.patch(f"/members/{world.marta}", {"role": "strata_manager"}).status_code == 200
    daniel_broker = Api(client, sessions.create(world.daniel, world.harbourline, "managing_broker"))
    r = daniel_broker.patch(f"/members/{world.daniel}", {"status": "deactivated"})
    assert r.status_code == 409 and r.json()["error"]["code"] == "last_broker"
    # Authenticator reset: the member enrols again at the next sign-in.
    email = fresh_email(mailbox)
    member = invite(daniel_broker, email)
    token, _ = sign_in(client, email, mail_count=2)
    assert daniel_broker.patch(f"/members/{member['id']}", {"reset_authenticator": True}).status_code == 200
    assert me(client, token).status_code == 401
    r = ask_link(client, email)
    nonce = cookie_value(set_cookies(r)["ss_signin"])
    link = latest_token(email, 3)
    client.cookies.clear()
    assert client.get(V1 + "/auth/callback", params={"token": link},
                      cookies={"ss_signin": nonce}).json() == {"next_step": "enrol"}
    reasons = {r[0] for r in owner("SELECT end_reason FROM web_sessions WHERE ended_at IS NOT NULL")}
    assert {"deactivated", "role_changed", "authenticator_reset"} <= reasons


def test_b2_invitation_rules(world: World, as_user: Any, mailbox: list[str]) -> None:
    marta = as_user(world.marta)
    email = fresh_email(mailbox)
    member = invite(marta, email)
    again = marta.post("/invitations", {"email": email.upper(), "full_name": "Test Member"})
    assert again.status_code == 409 and again.json()["error"]["code"] == "already_invited"
    assert "Already invited on" in again.json()["error"]["message"]
    assert marta.post(f"/invitations/{member['id']}/resend").status_code == 200
    assert len(wait_for_mail(email, 2)) == 2
    assert marta.post(f"/invitations/{world.priya}/resend").json()["error"]["code"] == "not_invited"
    same = marta.post("/invitations", {"email": "priya@harbourline.example", "full_name": "P"})
    assert same.json()["error"]["code"] == "already_member"
    # Another brokerage's address, and an operator's address: the same generic refusal.
    owner("INSERT INTO operators (id, email, full_name, totp_secret_encrypted) "
          "VALUES (:i, 'ops@stratascribe.example', 'Support Person', '\\x00') RETURNING id", i=uuid7())
    for addr in ("omar@tidewater.example", "ops@stratascribe.example"):
        r = marta.post("/invitations", {"email": addr, "full_name": "X"})
        assert r.status_code == 409 and r.json()["error"] == {
            "code": "cannot_invite", "message": "This address cannot be invited.",
            "correlation_id": r.json()["error"]["correlation_id"]}
    assert marta.post("/invitations", {"email": fresh_email(mailbox), "full_name": "X", "role": "admin"}
                      ).status_code == 422
    listed = {m["email"]: m for m in marta.get("/members").json()}
    assert listed[email]["status"] == "invited" and "omar@tidewater.example" not in listed
    assert listed["priya@harbourline.example"]["buildings"] == [str(world.zzs9001)]
    # Idempotent replay of an invitation sends no second email.
    e2 = fresh_email(mailbox)
    first = marta.post("/invitations", {"email": e2, "full_name": "Y"}, headers={"Idempotency-Key": "inv-1"})
    second = marta.post("/invitations", {"email": e2, "full_name": "Y"}, headers={"Idempotency-Key": "inv-1"})
    assert first.status_code == second.status_code == 201 and first.json() == second.json()
    time.sleep(0.3)
    assert len(wait_for_mail(e2)) == 1


TEAM_ROUTES: list[tuple[str, str, dict[str, Any] | None]] = [
    ("PATCH", "/members/{user_id}", {"status": "deactivated"}),
    ("POST", "/invitations/{user_id}/resend", {}),
]


def test_b2_team_routes_broker_only_and_tenant_scoped(world: World, client: TestClient, as_user: Any,
                                                     mailbox: list[str]) -> None:
    marta = as_user(world.marta)
    email = fresh_email(mailbox)
    target = invite(marta, email)["id"]
    priya = as_user(world.priya)
    assert priya.get("/members").status_code == 403
    assert priya.post("/invitations", {"email": fresh_email(mailbox), "full_name": "X"}).status_code == 403
    tide_broker = uuid7()
    owner("INSERT INTO users (id, brokerage_id, email, full_name, role, status) VALUES "
          "(:i, :b, 'broker@tidewater.example', 'Tide Broker', 'managing_broker', 'active') RETURNING id",
          i=tide_broker, b=world.tidewater)
    tide = Api(client, sessions.create(tide_broker, world.tidewater, "managing_broker"))
    for method, path, body in TEAM_ROUTES:
        p = path.replace("{user_id}", target)
        assert priya.send(method, p, body).status_code == 403
        r = tide.send(method, p, body)
        assert r.status_code == 404 and email not in r.text
    assert email not in tide.get("/members").text
    assert owner("SELECT status FROM users WHERE id = :i", i=target)[0][0] == "invited"
