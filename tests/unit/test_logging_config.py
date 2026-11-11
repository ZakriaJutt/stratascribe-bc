"""U-9 redaction, correlation IDs (T-2.1.4) and configuration validation (T-2.1.1)."""

from __future__ import annotations

import json
import logging

import pytest

from core import config
from core import logging as clog


def test_u9_text_and_email_are_redacted(capsys: pytest.CaptureFixture[str]) -> None:
    clog.configure()
    token = clog.set_correlation_id("11111111-2222-3333-4444-555555555555")
    try:
        logging.getLogger("t").info("item saved", extra={"text": "Owner of unit 12 is in arrears",
                                                          "email": "x@example.com", "meeting_id": "m-1"})
    finally:
        clog.reset_correlation_id(token)
    line = json.loads(capsys.readouterr().out.strip().splitlines()[-1])
    assert line["text"] == "[redacted]" and line["email"] == "[redacted]"
    assert line["meeting_id"] == "m-1"
    assert line["correlation_id"] == "11111111-2222-3333-4444-555555555555"
    assert "arrears" not in json.dumps(line)


def test_exception_messages_are_not_logged(capsys: pytest.CaptureFixture[str]) -> None:
    clog.configure()
    try:
        raise ValueError("transcript says Priya owes money")
    except ValueError:
        logging.getLogger("t").exception("failed")
    out = capsys.readouterr().out
    assert "Priya" not in out and "ValueError" in out


BASE = {
    "STRATASCRIBE_ENV": "test",
    "DATABASE_URL": "postgresql+psycopg://stratascribe_app@localhost/stratascribe_test",
    "MIGRATION_DATABASE_URL": "postgresql+psycopg://zakria@localhost/stratascribe_test",
    "REDIS_URL": "redis://localhost:6379/5",
    "PUBLIC_BASE_URL": "http://localhost:3106",
    "OBJECT_STORE_ROOT": "var/x",
    "SESSION_SECRET": "s" * 40,
    "TOTP_ENCRYPTION_KEY": "dGVzdC1vbmx5LXRvdHAta2V5LW5vdC1mb3ItdXNlISE=",
}


def test_config_validation_names_the_bad_variable() -> None:
    with pytest.raises(config.ConfigError) as e:
        config.load({**BASE, "PUBLIC_BASE_URL": "https://app.example.ca/some/path"})
    assert "PUBLIC_BASE_URL" in str(e.value)
    with pytest.raises(config.ConfigError) as e:
        config.load({k: v for k, v in BASE.items() if k != "SESSION_SECRET"})
    assert "SESSION_SECRET" in str(e.value)


def test_fingerprint_excludes_secrets_and_tracks_retention() -> None:
    a = config.load(BASE)
    b = config.load({**BASE, "SESSION_SECRET": "t" * 40})
    c = config.load({**BASE, "RETENTION_AUDIO_DAYS_AFTER_APPROVAL_DEFAULT": "20"})
    assert a.fingerprint() == b.fingerprint() != c.fingerprint()
