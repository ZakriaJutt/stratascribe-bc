"""Outbound email (B2). One interface; SMTP is the only transport.

Locally SMTP goes to Mailpit (127.0.0.1:1025, no authentication); production points the same
settings (``SMTP_*``, ``EMAIL_FROM``) at a real provider. Messages carry sign-in links and invitations
only, never meeting content (TRD context table). Addresses and bodies are never logged.
"""

from __future__ import annotations

import smtplib
import ssl
from dataclasses import dataclass
from email.message import EmailMessage
from typing import Protocol

from core import config
from core import logging as clog

log = clog.get_logger("mail")


@dataclass(frozen=True)
class Message:
    to: str
    subject: str
    body: str


class Mailer(Protocol):
    def send(self, message: Message) -> None: ...


class SmtpMailer:
    def __init__(self, host: str, port: int, username: str = "", password: str = "", starttls: bool = False,
                 sender: str = "") -> None:
        self.host, self.port, self.username, self.password = host, port, username, password
        self.starttls, self.sender = starttls, sender

    def send(self, message: Message) -> None:
        msg = EmailMessage()
        msg["From"] = self.sender
        msg["To"] = message.to
        msg["Subject"] = message.subject
        msg.set_content(message.body)
        with smtplib.SMTP(self.host, self.port, timeout=10) as smtp:
            if self.starttls:
                smtp.starttls(context=ssl.create_default_context())
            if self.username:
                smtp.login(self.username, self.password)
            smtp.send_message(msg)


_mailer: Mailer | None = None


def mailer() -> Mailer:
    global _mailer
    if _mailer is None:
        s = config.settings()
        _mailer = SmtpMailer(s.smtp_host, s.smtp_port, s.smtp_username, s.smtp_password, s.smtp_starttls,
                             s.email_from)
    return _mailer


def set_mailer(m: Mailer | None) -> None:
    global _mailer
    _mailer = m


def send(message: Message, kind: str) -> bool:
    """Send; on failure log the kind only (no address) and return False. The caller's response does
    not change, so a failed send never reveals whether an address exists."""
    try:
        mailer().send(message)
        return True
    except (OSError, smtplib.SMTPException):
        log.error("email not sent", extra={"kind": kind, "error_code": "smtp_failed"})
        return False
