"""Domain errors, mapped to HTTP by the API: NotFound 404, Forbidden 403, Conflict 409, Invalid 422."""

from __future__ import annotations

from typing import Any


class DomainError(Exception):
    status = 400
    code = "error"

    def __init__(self, message: str, *, code: str | None = None, extra: dict[str, Any] | None = None) -> None:
        super().__init__(message)
        self.message = message
        if code:
            self.code = code
        self.extra = extra or {}


class NotFound(DomainError):
    status = 404
    code = "not_found"


class Forbidden(DomainError):
    status = 403
    code = "not_assigned"


class Conflict(DomainError):
    status = 409
    code = "conflict"


class Invalid(DomainError):
    status = 422
    code = "invalid"


class Unauthenticated(DomainError):
    status = 401
    code = "unauthenticated"
