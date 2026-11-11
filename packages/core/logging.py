"""Structured JSON logging with correlation IDs and an allow-list redactor (T-2.1.4, R-12).

Only allow-listed extra fields are written; every other field is replaced by
"[redacted]". Message strings must be fixed text: never format transcript,
minutes, question, answer, names or emails into them.
"""

from __future__ import annotations

import contextvars
import json
import logging
import sys
import uuid
from datetime import UTC, datetime
from typing import Any

_correlation_id: contextvars.ContextVar[str | None] = contextvars.ContextVar("correlation_id", default=None)

ALLOWED_FIELDS = frozenset(
    {
        "correlation_id",
        "job_id",
        "job_kind",
        "attempt",
        "meeting_id",
        "strata_id",
        "brokerage_id",
        "user_id",
        "actor_type",
        "status",
        "state",
        "error_code",
        "route",
        "method",
        "status_code",
        "duration_ms",
        "worker_id",
        "count",
        "fingerprint",
        "kind",
        "port",
        "target_type",
        "target_id",
        "outcome",
    }
)
REDACTED = "[redacted]"
_RESERVED = frozenset(vars(logging.makeLogRecord({})).keys()) | {"message", "asctime"}


def new_correlation_id() -> str:
    return str(uuid.uuid4())


def set_correlation_id(value: str | None) -> contextvars.Token[str | None]:
    return _correlation_id.set(value)


def reset_correlation_id(token: contextvars.Token[str | None]) -> None:
    _correlation_id.reset(token)


def correlation_id() -> str | None:
    return _correlation_id.get()


def redact(fields: dict[str, Any]) -> dict[str, Any]:
    return {k: (v if k in ALLOWED_FIELDS else REDACTED) for k, v in fields.items()}


class JsonFormatter(logging.Formatter):
    def format(self, record: logging.LogRecord) -> str:
        extras = {k: v for k, v in vars(record).items() if k not in _RESERVED}
        out: dict[str, Any] = {
            "ts": datetime.fromtimestamp(record.created, UTC).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "msg": record.msg if isinstance(record.msg, str) else REDACTED,
            "correlation_id": extras.pop("correlation_id", None) or correlation_id(),
        }
        out.update(redact(extras))
        if record.exc_info and record.exc_info[0] is not None:
            # Exception type only: messages can carry content.
            out["exc_type"] = record.exc_info[0].__name__
        return json.dumps(out, default=str)


def configure(level: int = logging.INFO) -> None:
    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(JsonFormatter())
    root = logging.getLogger()
    root.handlers[:] = [handler]
    root.setLevel(level)


def get_logger(name: str) -> logging.Logger:
    return logging.getLogger(name)
