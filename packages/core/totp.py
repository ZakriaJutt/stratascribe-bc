"""Time-based authenticator codes (RFC 6238 over RFC 4226 HOTP; SHA-1, 6 digits, 30-second steps).

The secret is 20 random bytes, shown once at enrolment as base32 and as an ``otpauth://`` URI, and
stored only encrypted with AES-256-GCM under ``TOTP_ENCRYPTION_KEY`` (the user's id is the associated
data, so a ciphertext copied to another user's row does not decrypt). A code is accepted for the
current step or one step either side, and never for a step at or before the last accepted one
(replay guard).
"""

from __future__ import annotations

import base64
import hashlib
import hmac
import os
import struct
import uuid
from datetime import datetime
from urllib.parse import quote

from cryptography.hazmat.primitives.ciphers.aead import AESGCM

from core import config

STEP_SECONDS = 30
DIGITS = 6
WINDOW = 1
ISSUER = "StrataScribe BC"


def new_secret() -> bytes:
    return os.urandom(20)


def base32(secret: bytes) -> str:
    return base64.b32encode(secret).decode().rstrip("=")


def provisioning_uri(secret: bytes, account: str) -> str:
    label = quote(f"{ISSUER}:{account}")
    return f"otpauth://totp/{label}?secret={base32(secret)}&issuer={quote(ISSUER)}&digits={DIGITS}&period={STEP_SECONDS}"


def step_at(when: datetime) -> int:
    return int(when.timestamp()) // STEP_SECONDS


def code_for(secret: bytes, step: int) -> str:
    digest = hmac.new(secret, struct.pack(">Q", step), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    value = struct.unpack(">I", digest[offset:offset + 4])[0] & 0x7FFFFFFF
    return str(value % 10**DIGITS).zfill(DIGITS)


def accept(secret: bytes, code: str, when: datetime, last_used_step: int | None) -> int | None:
    """Return the matched step, or None. Constant-time comparison per candidate step."""
    if len(code) != DIGITS or not code.isdigit():
        return None
    now = step_at(when)
    matched: int | None = None
    for step in range(now - WINDOW, now + WINDOW + 1):
        if hmac.compare_digest(code_for(secret, step), code) and (last_used_step is None or step > last_used_step):
            matched = step
    return matched


def _key() -> bytes:
    return base64.b64decode(config.settings().totp_encryption_key)


def encrypt(secret: bytes, subject_id: uuid.UUID) -> bytes:
    nonce = os.urandom(12)
    return nonce + AESGCM(_key()).encrypt(nonce, secret, subject_id.bytes)


def decrypt(blob: bytes, subject_id: uuid.UUID) -> bytes:
    return AESGCM(_key()).decrypt(blob[:12], blob[12:], subject_id.bytes)
