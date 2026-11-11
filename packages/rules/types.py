from __future__ import annotations

from enum import StrEnum

# Bump on any change to this package (AGENTS.md "What to update when").
RULES_VERSION = "rules-2026.11.2"  # .2: QuorumResult.required and stored quorum columns (B1-006)


class RuleInputError(ValueError):
    """Raised when an input required by the selected rule is missing or invalid."""


class Threshold(StrEnum):
    MAJORITY = "majority"
    THREE_QUARTER = "three_quarter"
    EIGHTY_PERCENT = "eighty_percent"
    UNANIMOUS = "unanimous"
    COUNCIL_MAJORITY = "council_majority"


class VoteResult(StrEnum):
    CARRIED = "carried"
    DEFEATED = "defeated"
    TIE = "tie"
    NO_RESULT = "no_result"


class CastingVote(StrEnum):
    NOT_USED = "not_used"
    USED_FOR = "used_for"
    USED_AGAINST = "used_against"


def require_count(name: str, value: int | None) -> int:
    if value is None:
        raise RuleInputError(f"{name} is required for this rule")
    if isinstance(value, bool) or not isinstance(value, int):
        raise RuleInputError(f"{name} must be an integer")
    if value < 0:
        raise RuleInputError(f"{name} must not be negative")
    return value
