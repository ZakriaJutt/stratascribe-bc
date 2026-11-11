"""Sign-in: emailed single-use link plus authenticator code (B2, T-2.2.2; TRD AD-10, App-flow S-01).

1. ``request_link``: rate limited per IP address and per email; the same answer, and the same work
   before answering, whether or not the address exists. After the response, ``issue_link`` stores a
   link for an invited or active user (HMAC of 32 random bytes, 10 minutes) bound to the requesting
   browser's nonce cookie and sends the email.
2. ``check_link``: read-only; says whether the browser must enrol an authenticator or enter a code.
   Mail scanners that prefetch the link therefore cannot use it up.
3. ``enrol``: first sign-in only; returns a new secret once (stored encrypted, not yet active).
4. ``verify``: the 6-digit code; at most 5 wrong codes per link. On success the link is used up, the
   user becomes active, and only now is a session created.

Errors carry the App-flow S-01 wording. No address, token or code is logged.
"""

from __future__ import annotations

import hashlib
import hmac
import re
import secrets
import uuid
from dataclasses import dataclass
from datetime import timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from core import audit, clock, config, mail, ratelimit, sessions, totp
from core import logging as clog
from core.db import Actor, session_for
from core.errors import Conflict, DomainError, Invalid
from core.ids import uuid7
from core.mail import Message
from core.models import SignInLink, User

log = clog.get_logger("auth")
NONCE_COOKIE = "ss_signin"
MAX_FAILED_CODES = 5
EMAIL_RE = re.compile(r"^[^@\s]{1,64}@[A-Za-z0-9.-]{1,253}\.[A-Za-z]{2,63}$")
NEXT_RE = re.compile(r"^/(?![/\\])[A-Za-z0-9/_\-.~%?=&]{0,300}$")
DEFAULT_NEXT = "/buildings"


class RateLimited(DomainError):
    status = 429
    code = "rate_limited"


class LinkError(DomainError):
    status = 400
    code = "link_expired"


EXPIRED = "This link has expired. Send a new one."
OTHER_BROWSER = "Open the link in the browser where you asked for it, or send a new one."
CODE_MISMATCH = "That code did not match. Codes change every 30 seconds."
EXHAUSTED = "Too many codes tried. Send a new sign-in link."


def _hash(value: str) -> bytes:
    return hmac.new(config.settings().session_secret.encode(), value.encode(), hashlib.sha256).digest()


def new_nonce() -> str:
    return secrets.token_urlsafe(32)


def safe_next(value: object) -> str | None:
    """Only same-site paths (App-flow S-01): no scheme, no host, no ``//`` or backslash."""
    if not isinstance(value, str) or not value:
        return None
    return value if NEXT_RE.match(value) else None


def normalise_email(value: object) -> str:
    email = value.strip() if isinstance(value, str) else ""
    if not EMAIL_RE.match(email):
        raise Invalid("Enter a valid work email address.", code="invalid_email", extra={"fields": ["email"]})
    return email.lower()


def _limit(bucket: str, ident: str, rule: tuple[int, int]) -> None:
    retry = ratelimit.hit(bucket, ident, *rule)
    if retry is not None:
        minutes = max(1, -(-retry // 60))
        raise RateLimited(f"Too many sign-in requests. Try again in {minutes} minutes.",
                          extra={"retry_after_seconds": retry})


def request_link(email_value: object, ip: str) -> str:
    """The synchronous part of a sign-in request: validate the address and apply the rate limits.
    It does the same work whether or not the address exists; everything that depends on that
    (lookup, link row, audit, email) runs in ``issue_link`` after the response is sent (B2-S02)."""
    email = normalise_email(email_value)
    _limit("signin-ip", ip, ratelimit.SIGN_IN_PER_IP)
    _limit("signin-email", email, ratelimit.SIGN_IN_PER_EMAIL)
    return email


def issue_link(email: str, nonce: str, next_value: object = None) -> bool:
    """Run after the response: store a link for a known, usable address and email it. Returns whether
    an email was sent. Never raises (it runs as a background task); failures are logged by kind."""
    try:
        message = _store_link(email, nonce, next_value)
    except Exception:  # noqa: BLE001
        log.error("sign-in link not issued", extra={"kind": "sign_in_link", "error_code": "issue_failed"})
        return False
    return message is not None and mail.send(message, "sign_in_link")


def _store_link(email: str, nonce: str, next_value: object) -> Message | None:
    cfg = config.settings()
    now = clock.now()
    with session_for(Actor.auth()) as s:
        u = s.scalar(select(User).where(User.email == email))
        if u is None or u.status not in ("invited", "active"):
            return None
        token = secrets.token_urlsafe(32)
        s.add(SignInLink(id=uuid7(), user_id=u.id, token_hash=_hash(token), nonce_hash=_hash(nonce),
                         next_path=safe_next(next_value), created_at=now,
                         expires_at=now + timedelta(seconds=cfg.sign_in_link_seconds)))
        audit.record(s, Actor.auth(), "auth.link_requested", brokerage_id=u.brokerage_id, target_type="user",
                     target_id=u.id)
    minutes = cfg.sign_in_link_seconds // 60
    body = (f"Use this link to sign in to StrataScribe. It works once, for {minutes} minutes, in the browser "
            f"where you asked for it:\n\n{cfg.public_base_url}/sign-in?token={token}\n\n"
            "If you did not ask to sign in, ignore this email.")
    return Message(to=u.email, subject="Your StrataScribe sign-in link", body=body)


def _load(s: Session, token: object, nonce: str | None) -> tuple[SignInLink, User]:
    if not isinstance(token, str) or not token or len(token) > 200:
        raise LinkError(EXPIRED)
    link = s.scalar(select(SignInLink).where(SignInLink.token_hash == _hash(token)).with_for_update())
    if link is None or link.consumed_at is not None or clock.now() >= link.expires_at:
        raise LinkError(EXPIRED)
    if not nonce or not hmac.compare_digest(link.nonce_hash, _hash(nonce)):
        raise LinkError(OTHER_BROWSER, code="link_other_browser")
    if link.failed_codes >= MAX_FAILED_CODES:
        raise RateLimited(EXHAUSTED, code="attempts_exhausted")
    u = s.get(User, link.user_id, with_for_update=True)
    if u is None or u.status not in ("invited", "active"):
        raise LinkError(EXPIRED)
    return link, u


def check_link(token: object, nonce: str | None) -> dict[str, str]:
    with session_for(Actor.auth()) as s:
        _, u = _load(s, token, nonce)
        return {"next_step": "code" if u.totp_enrolled_at is not None else "enrol"}


def enrol(token: object, nonce: str | None) -> dict[str, str]:
    with session_for(Actor.auth()) as s:
        _, u = _load(s, token, nonce)
        if u.totp_enrolled_at is not None:
            raise Conflict("An authenticator is already set up. Enter its code.", code="already_enrolled")
        secret = totp.new_secret()
        u.totp_secret_encrypted = totp.encrypt(secret, u.id)
        u.totp_last_used_step = None
        return {"setup_key": totp.base32(secret), "otpauth_uri": totp.provisioning_uri(secret, u.email)}


@dataclass(frozen=True)
class SignedIn:
    token: str
    next_path: str
    user_id: uuid.UUID
    brokerage_id: uuid.UUID
    role: str


def verify(token: object, nonce: str | None, code: object) -> SignedIn:
    code_str = code.strip() if isinstance(code, str) else ""
    failure: DomainError | None = None
    result: SignedIn | None = None
    now = clock.now()
    with session_for(Actor.auth()) as s:
        link, u = _load(s, token, nonce)
        if u.totp_secret_encrypted is None:
            raise Conflict("Set up your authenticator first.", code="enrolment_required")
        step = totp.accept(totp.decrypt(u.totp_secret_encrypted, u.id), code_str, now, u.totp_last_used_step)
        if step is None:
            link.failed_codes += 1
            audit.record(s, Actor.auth(), "auth.code_rejected", brokerage_id=u.brokerage_id, target_type="user",
                         target_id=u.id, outcome="denied", details={"count": link.failed_codes})
            failure = (RateLimited(EXHAUSTED, code="attempts_exhausted") if link.failed_codes >= MAX_FAILED_CODES
                       else LinkError(CODE_MISMATCH, code="code_mismatch",
                                      extra={"attempts_left": MAX_FAILED_CODES - link.failed_codes}))
        else:
            enrolled_now = u.totp_enrolled_at is None
            link.consumed_at = now
            u.totp_last_used_step = step
            if enrolled_now:
                u.totp_enrolled_at = now
            if u.status == "invited":
                u.status = "active"
            u.last_sign_in_at = now
            s.flush()
            session_token = sessions.create_in(s, u.id, u.brokerage_id, u.role)
            result = SignedIn(session_token, link.next_path or DEFAULT_NEXT, u.id, u.brokerage_id, u.role)
            kind = "enrolled" if enrolled_now else "code"
    if failure is not None:
        raise failure  # the failed-attempt count above is committed first
    assert result is not None
    actor = Actor.user(result.user_id, result.brokerage_id, result.role)
    with session_for(actor) as s:
        audit.record(s, actor, "auth.signed_in", target_type="user", target_id=result.user_id,
                     details={"kind": kind})
    return result


def sign_out(token: str, actor: Actor) -> None:
    sessions.end(token, "signed_out")
    with session_for(actor) as s:
        audit.record(s, actor, "auth.signed_out", target_type="user", target_id=actor.user_id)
