"""Counted-vote rules (TRD.md "Counted-vote rules")."""

from __future__ import annotations

from dataclasses import dataclass

from rules.types import (
    RULES_VERSION,
    CastingVote,
    RuleInputError,
    Threshold,
    VoteResult,
    require_count,
)

SRC_SPA_S1 = "[S: SPA] s. 1"
SRC_SB_27 = "[S: SPA-SB] s. 27(5)-(6)"
SRC_SB_18 = "[S: SPA-SB] s. 18(1)-(2)"


@dataclass(frozen=True)
class VoteInput:
    threshold: Threshold
    votes_for: int | None
    votes_against: int | None
    votes_abstained: int | None = None
    eligible_votes: int | None = None
    members_present: int | None = None
    strata_lot_count: int | None = None


@dataclass(frozen=True)
class RuleResult:
    result: VoteResult
    rule: str
    source: str
    formula: str
    rules_version: str = RULES_VERSION
    casting_vote_offered: bool = False


def _cmp(holds: bool, lhs: int, rhs: int, ge: bool) -> str:
    if ge:
        return f"{lhs} ≥ {rhs}" if holds else f"{lhs} < {rhs}"
    return f"{lhs} > {rhs}" if holds else f"{lhs} ≤ {rhs}"


def _tie(rule: str, source: str, f: int, lots: int | None) -> RuleResult:
    if lots == 2:
        # No casting vote where the strata plan has only 2 strata lots: a tie is defeated.
        return RuleResult(
            VoteResult.DEFEATED,
            rule,
            source,
            f"{f} for = {f} against; tie; no casting vote with 2 strata lots",
        )
    return RuleResult(
        VoteResult.TIE,
        rule,
        source,
        f"{f} for = {f} against; tie",
        casting_vote_offered=True,
    )


def compute_vote(v: VoteInput) -> RuleResult:
    """Compute the result of a counted vote. Abstentions never count."""
    f = require_count("votes_for", v.votes_for)
    a = require_count("votes_against", v.votes_against)
    if v.votes_abstained is not None:
        require_count("votes_abstained", v.votes_abstained)
    if v.strata_lot_count is not None and v.strata_lot_count <= 0:
        raise RuleInputError("strata_lot_count must be positive")
    threshold = Threshold(v.threshold)

    if f == 0 and a == 0:
        return RuleResult(
            VoteResult.NO_RESULT,
            threshold.value,
            SRC_SPA_S1,
            "0 for and 0 against: no result",
        )

    total = f + a
    if threshold is Threshold.MAJORITY:
        if f == a:
            return _tie("majority", SRC_SB_27, f, v.strata_lot_count)
        holds = f * 2 > total
        res = VoteResult.CARRIED if holds else VoteResult.DEFEATED
        sym = ">" if holds else "≤"
        return RuleResult(
            res, "majority", SRC_SPA_S1, f"{f} × 2 {sym} {total}: " + _cmp(holds, f * 2, total, False)
        )

    if threshold is Threshold.THREE_QUARTER:
        lhs, rhs = f * 4, 3 * total
        holds = lhs >= rhs
        sym = "≥" if holds else "<"
        return RuleResult(
            VoteResult.CARRIED if holds else VoteResult.DEFEATED,
            "three_quarter",
            SRC_SPA_S1,
            f"{f} × 4 {sym} 3 × {total}: " + _cmp(holds, lhs, rhs, True),
        )

    if threshold is Threshold.EIGHTY_PERCENT:
        eligible = require_count("eligible_votes", v.eligible_votes)
        if eligible == 0 or f > eligible:
            raise RuleInputError("eligible_votes must be positive and not below votes_for")
        lhs, rhs = f * 5, 4 * eligible
        holds = lhs >= rhs
        sym = "≥" if holds else "<"
        return RuleResult(
            VoteResult.CARRIED if holds else VoteResult.DEFEATED,
            "eighty_percent",
            SRC_SPA_S1,
            f"{f} × 5 {sym} 4 × {eligible}: " + _cmp(holds, lhs, rhs, True),
        )

    if threshold is Threshold.UNANIMOUS:
        eligible = require_count("eligible_votes", v.eligible_votes)
        if eligible == 0 or f > eligible:
            raise RuleInputError("eligible_votes must be positive and not below votes_for")
        holds = f == eligible
        return RuleResult(
            VoteResult.CARRIED if holds else VoteResult.DEFEATED,
            "unanimous",
            SRC_SPA_S1,
            f"{f} {'=' if holds else '≠'} {eligible}",
        )

    if threshold is Threshold.COUNCIL_MAJORITY:
        present = require_count("members_present", v.members_present)
        abstained = v.votes_abstained or 0
        if present == 0 or f + a + abstained > present:
            raise RuleInputError("members_present must cover every vote cast or abstained")
        if f == a:
            return _tie("council_majority", SRC_SB_18, f, v.strata_lot_count)
        holds = f * 2 > present
        sym = ">" if holds else "≤"
        return RuleResult(
            VoteResult.CARRIED if holds else VoteResult.DEFEATED,
            "council_majority",
            SRC_SB_18,
            f"{f} × 2 {sym} {present} present: " + _cmp(holds, f * 2, present, False),
        )

    raise RuleInputError(f"unknown threshold {threshold}")  # pragma: no cover


def apply_casting_vote(result: VoteResult, casting_vote: str | None) -> VoteResult | None:
    """Outcome of a counted vote after the president's casting vote.

    Returns None while a tie has no casting-vote record (the item stays blocked).
    """
    if result is not VoteResult.TIE:
        if casting_vote is not None:
            raise RuleInputError("a casting vote is recorded only for a tie")
        return result
    if casting_vote is None:
        return None
    cv = CastingVote(casting_vote)
    return VoteResult.CARRIED if cv is CastingVote.USED_FOR else VoteResult.DEFEATED
