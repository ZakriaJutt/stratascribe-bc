"""How a motion gets its outcome (TRD.md "How a motion gets its outcome", "Discrepancy").

``evaluate_motion`` is the single function that turns manager-confirmed inputs
into the stored result columns. Callers persist ``MotionEvaluation.columns``
as given; they never name or assign the computed columns themselves (U-16).
"""

from __future__ import annotations

from dataclasses import dataclass, field

from rules.types import RULES_VERSION, RuleInputError, Threshold, VoteResult
from rules.votes import RuleResult, VoteInput, apply_casting_vote, compute_vote

DECLARED = "declared"
COUNTED = "counted"
OUTCOMES = ("carried", "defeated")
RESOLUTIONS = ("counts_corrected", "threshold_corrected", "recorded_as_declared")

BLOCK_METHOD = "Choose how the motion was decided: declared on a show of cards, or counted."
BLOCK_DECLARED = "Select carried or defeated as the chair declared it."
BLOCK_COUNTS = "Enter the threshold and the votes for and against."
BLOCK_NO_RESULT = "Enter the count, or switch to declared on a show of cards."
BLOCK_TIE = "Record whether the president used a casting vote."
BLOCK_NOTE = "A note is required when the minutes record both the declaration and the count."


def block_discrepancy(declared: str, counted: str) -> str:
    return (
        f"The chair declared {declared.upper()} but the count gives {counted.upper()}. "
        "Correct the count, correct the threshold, or record both as they happened."
    )


@dataclass(frozen=True)
class MotionInput:
    outcome_method: str | None
    declared_outcome: str | None = None
    outcome_attested: bool = False
    threshold: str | None = None
    votes_for: int | None = None
    votes_against: int | None = None
    votes_abstained: int | None = None
    eligible_votes: int | None = None
    members_present: int | None = None
    casting_vote: str | None = None
    discrepancy_resolution: str | None = None
    discrepancy_note: str | None = None
    strata_lot_count: int | None = None


@dataclass(frozen=True)
class MotionEvaluation:
    final_outcome: str | None
    blocked_reason: str | None
    computed: RuleResult | None
    columns: dict[str, str | None] = field(default_factory=dict)

    @property
    def blocked(self) -> bool:
        return self.blocked_reason is not None


def _columns(computed: RuleResult | None) -> dict[str, str | None]:
    # The only place in the code base that names the computed column (U-16).
    if computed is None:
        return {"computed_result": None, "computed_formula": None, "rules_version": None}
    return {
        "computed_result": computed.result.value,
        "computed_formula": computed.formula,
        "rules_version": RULES_VERSION,
    }


def evaluate_motion(m: MotionInput) -> MotionEvaluation:
    if m.declared_outcome is not None and m.declared_outcome not in OUTCOMES:
        raise RuleInputError("declared_outcome must be carried or defeated")
    if m.discrepancy_resolution is not None and m.discrepancy_resolution not in RESOLUTIONS:
        raise RuleInputError("unknown discrepancy_resolution")

    if m.outcome_method is None:
        return MotionEvaluation(None, BLOCK_METHOD, None, _columns(None))

    if m.outcome_method == DECLARED:
        # Show of cards: no counts are required, none are invented, nothing is computed.
        if m.declared_outcome is None or not m.outcome_attested:
            return MotionEvaluation(None, BLOCK_DECLARED, None, _columns(None))
        return MotionEvaluation(m.declared_outcome, None, None, _columns(None))

    if m.outcome_method != COUNTED:
        raise RuleInputError("outcome_method must be declared or counted")

    if m.threshold is None or m.votes_for is None or m.votes_against is None:
        return MotionEvaluation(None, BLOCK_COUNTS, None, _columns(None))

    computed = compute_vote(
        VoteInput(
            threshold=Threshold(m.threshold),
            votes_for=m.votes_for,
            votes_against=m.votes_against,
            votes_abstained=m.votes_abstained,
            eligible_votes=m.eligible_votes,
            members_present=m.members_present,
            strata_lot_count=m.strata_lot_count,
        )
    )
    cols = _columns(computed)
    if computed.result is VoteResult.NO_RESULT:
        return MotionEvaluation(None, BLOCK_NO_RESULT, computed, cols)
    if computed.result is not VoteResult.TIE and m.casting_vote is not None:
        raise RuleInputError("a casting vote is recorded only for a tie")

    counted = apply_casting_vote(computed.result, m.casting_vote)
    if counted is None:
        return MotionEvaluation(None, BLOCK_TIE, computed, cols)

    if m.declared_outcome is not None and m.declared_outcome != counted.value:
        if m.discrepancy_resolution == "recorded_as_declared":
            if not (m.discrepancy_note and m.discrepancy_note.strip()):
                return MotionEvaluation(None, BLOCK_NOTE, computed, cols)
            # The minutes state both the chair's declaration and the count as recorded;
            # the product does not rule on which is legally effective.
            return MotionEvaluation(m.declared_outcome, None, computed, cols)
        return MotionEvaluation(
            None, block_discrepancy(m.declared_outcome, counted.value), computed, cols
        )
    return MotionEvaluation(counted.value, None, computed, cols)
