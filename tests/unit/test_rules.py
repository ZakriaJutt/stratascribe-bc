"""Unit tests U-1 to U-6 and U-10 to U-15 (execution-plan.md "Planned tests")."""

from __future__ import annotations

import pytest

from rules import (
    RULES_VERSION,
    MotionInput,
    RuleInputError,
    Threshold,
    VoteInput,
    VoteResult,
    compute_vote,
    council_quorum,
    declared_quorum,
    evaluate_motion,
    general_quorum,
)
from rules.motion import BLOCK_NO_RESULT, BLOCK_NOTE, BLOCK_TIE


def counted(**kw: object) -> MotionInput:
    return MotionInput(outcome_method="counted", **kw)  # type: ignore[arg-type]


def test_u1_three_quarter_carried() -> None:
    r = compute_vote(VoteInput(Threshold.THREE_QUARTER, 9, 3))
    assert r.result is VoteResult.CARRIED
    assert r.formula.startswith("9 × 4 ≥ 3 × 12")
    assert r.rules_version == RULES_VERSION


def test_u2_three_quarter_fails_by_one() -> None:
    r = compute_vote(VoteInput(Threshold.THREE_QUARTER, 8, 3))
    assert r.result is VoteResult.DEFEATED
    assert r.formula.endswith("32 < 33")


def test_u3_tie_blocks_until_casting_vote_recorded() -> None:
    e = evaluate_motion(counted(threshold="majority", votes_for=6, votes_against=6, strata_lot_count=40))
    assert e.computed is not None and e.computed.result is VoteResult.TIE
    assert e.blocked_reason == BLOCK_TIE and e.final_outcome is None
    e2 = evaluate_motion(
        counted(threshold="majority", votes_for=6, votes_against=6, casting_vote="not_used", strata_lot_count=40)
    )
    assert e2.final_outcome == "defeated" and not e2.blocked


def test_u4_eighty_percent() -> None:
    assert compute_vote(VoteInput(Threshold.EIGHTY_PERCENT, 40, 10, eligible_votes=50)).result is VoteResult.CARRIED
    r = compute_vote(VoteInput(Threshold.EIGHTY_PERCENT, 39, 11, eligible_votes=50))
    assert r.result is VoteResult.DEFEATED and r.formula.endswith("195 < 200")
    with pytest.raises(RuleInputError):
        compute_vote(VoteInput(Threshold.EIGHTY_PERCENT, 40, 10))


def test_u5_default_general_quorum() -> None:
    q = general_quorum(present_votes=17, eligible_votes=50, strata_lot_count=50, owner_count=48)
    assert q.met and q.formula.endswith("51 ≥ 50") and q.source == "[S: SPA] s. 48(2)(a)"
    q2 = general_quorum(present_votes=16, eligible_votes=50, strata_lot_count=50, owner_count=48)
    assert not q2.met and q2.formula.endswith("48 < 50")


def test_u6_zero_zero_is_no_result_and_blocks() -> None:
    e = evaluate_motion(counted(threshold="majority", votes_for=0, votes_against=0))
    assert e.computed is not None and e.computed.result is VoteResult.NO_RESULT
    assert e.blocked_reason == BLOCK_NO_RESULT
    assert "switch to declared" in BLOCK_NO_RESULT


def test_u10_declared_show_of_cards_needs_no_counts() -> None:
    e = evaluate_motion(MotionInput(outcome_method="declared", declared_outcome="carried", outcome_attested=True))
    assert not e.blocked and e.final_outcome == "carried"
    assert e.computed is None and e.columns["computed_result"] is None
    # Not attested yet: never prefilled as final.
    e2 = evaluate_motion(MotionInput(outcome_method="declared", declared_outcome="carried"))
    assert e2.blocked and e2.final_outcome is None


def test_u11_discrepancy_and_each_resolution() -> None:
    base = {"threshold": "three_quarter", "votes_for": 8, "votes_against": 3, "declared_outcome": "carried"}
    e = evaluate_motion(counted(**base))
    assert e.computed is not None and e.computed.result is VoteResult.DEFEATED
    assert e.blocked and "DECLARED CARRIED" in (e.blocked_reason or "").upper()
    # counts corrected: recomputes from the corrected count
    fixed = evaluate_motion(counted(**{**base, "votes_for": 9, "discrepancy_resolution": "counts_corrected"}))
    assert not fixed.blocked and fixed.final_outcome == "carried"
    # counts "corrected" but still disagree: still blocked
    still = evaluate_motion(counted(**{**base, "discrepancy_resolution": "counts_corrected"}))
    assert still.blocked
    # threshold corrected (it was a majority vote)
    thr = evaluate_motion(counted(**{**base, "threshold": "majority", "discrepancy_resolution": "threshold_corrected"}))
    assert not thr.blocked and thr.final_outcome == "carried"
    # recorded as declared needs a note, keeps both
    no_note = evaluate_motion(counted(**{**base, "discrepancy_resolution": "recorded_as_declared"}))
    assert no_note.blocked_reason == BLOCK_NOTE
    rec = evaluate_motion(
        counted(**{**base, "discrepancy_resolution": "recorded_as_declared", "discrepancy_note": "Chair declared"})
    )
    assert not rec.blocked and rec.final_outcome == "carried"
    assert rec.columns["computed_result"] == "defeated"


def test_u12_adjourned_meeting_quorum() -> None:
    q = general_quorum(
        present_votes=5, eligible_votes=50, strata_lot_count=50, owner_count=50, reconvened_after_adjournment=True
    )
    assert q.met and q.source == "[S: SPA] s. 48(3)"
    override = {"adjourned_rule": {"type": "fraction", "numerator": 1, "denominator": 4, "source_clause": "12(3)"}}
    q2 = general_quorum(
        present_votes=5,
        eligible_votes=50,
        strata_lot_count=50,
        owner_count=50,
        reconvened_after_adjournment=True,
        override=override,
    )
    assert not q2.met and "12(3)" in q2.source


def test_u13_small_strata_two_thirds() -> None:
    q1 = general_quorum(present_votes=1, eligible_votes=3, strata_lot_count=3, owner_count=3)
    assert not q1.met and q1.formula.endswith("3 < 6") and q1.source == "[S: SPA] s. 48(2)(b)"
    q2 = general_quorum(present_votes=2, eligible_votes=3, strata_lot_count=3, owner_count=3)
    assert q2.met and q2.formula.endswith("6 ≥ 6")
    # fewer than 4 owners also selects the 2/3 rule
    q3 = general_quorum(present_votes=10, eligible_votes=50, strata_lot_count=50, owner_count=3)
    assert q3.rule == "small_strata_two_thirds" and not q3.met


def test_u14_casting_vote_and_two_lot_strata() -> None:
    e = evaluate_motion(
        counted(threshold="majority", votes_for=6, votes_against=6, casting_vote="used_for", strata_lot_count=40)
    )
    assert e.final_outcome == "carried" and not e.blocked
    two = evaluate_motion(counted(threshold="majority", votes_for=6, votes_against=6, strata_lot_count=2))
    assert two.computed is not None and not two.computed.casting_vote_offered
    assert two.final_outcome == "defeated" and not two.blocked
    with pytest.raises(RuleInputError):
        evaluate_motion(
            counted(threshold="majority", votes_for=6, votes_against=6, casting_vote="used_for", strata_lot_count=2)
        )


@pytest.mark.parametrize(
    ("size", "present", "met"),
    [(1, 1, True), (3, 1, False), (4, 2, True), (5, 2, False), (6, 3, True), (7, 4, True)],
)
def test_u15_council_quorum(size: int, present: int, met: bool) -> None:
    assert council_quorum(members_present=present, council_size=size).met is met


def test_u15_council_votes() -> None:
    c = compute_vote(VoteInput(Threshold.COUNCIL_MAJORITY, 3, 1, members_present=4))
    assert c.result is VoteResult.CARRIED and "6 > 4" in c.formula
    t = compute_vote(VoteInput(Threshold.COUNCIL_MAJORITY, 2, 2, members_present=4, strata_lot_count=30))
    assert t.result is VoteResult.TIE and t.casting_vote_offered
    d = compute_vote(VoteInput(Threshold.COUNCIL_MAJORITY, 2, 1, votes_abstained=1, members_present=4))
    assert d.result is VoteResult.DEFEATED and "4 ≤ 4" in d.formula


def test_unanimous_and_inputs() -> None:
    assert compute_vote(VoteInput(Threshold.UNANIMOUS, 50, 0, eligible_votes=50)).result is VoteResult.CARRIED
    assert compute_vote(VoteInput(Threshold.UNANIMOUS, 49, 0, eligible_votes=50)).result is VoteResult.DEFEATED
    with pytest.raises(RuleInputError):
        compute_vote(VoteInput(Threshold.MAJORITY, -1, 2))
    with pytest.raises(RuleInputError):
        council_quorum(members_present=3, council_size=9)
    assert declared_quorum(attested=True).met
    with pytest.raises(RuleInputError):
        general_quorum(present_votes=5, eligible_votes=50, strata_lot_count=50, owner_count=50, override={"type": "x"})
