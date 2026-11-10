"""Deterministic quorum and vote rules (T-3.2.3, MH-06).

Pure code: no model, no network, no database, integer arithmetic only. Every
result carries the rule name, the source reference and the inequality that was
evaluated. Sources are the IDs in Decision.md ("Sources and assumptions"); the
rules were written from TRD.md "Deterministic rules" and must be checked
against the statute text by a second person in T-4.1.2 before real use.

This package is the only place allowed to produce ``computed_result``
(test U-16 enforces it).
"""

from rules.motion import (
    MotionEvaluation,
    MotionInput,
    evaluate_motion,
)
from rules.quorum import (
    QuorumResult,
    council_quorum,
    declared_quorum,
    general_quorum,
)
from rules.types import RULES_VERSION, RuleInputError, Threshold, VoteResult
from rules.votes import RuleResult, VoteInput, apply_casting_vote, compute_vote

__all__ = [
    "RULES_VERSION",
    "MotionEvaluation",
    "MotionInput",
    "QuorumResult",
    "RuleInputError",
    "RuleResult",
    "Threshold",
    "VoteInput",
    "VoteResult",
    "apply_casting_vote",
    "compute_vote",
    "council_quorum",
    "declared_quorum",
    "evaluate_motion",
    "general_quorum",
]
