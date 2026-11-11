"""Quorum rules (TRD.md "Quorum rules")."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from rules.types import RULES_VERSION, RuleInputError, require_count

SRC_48_2A = "[S: SPA] s. 48(2)(a)"
SRC_48_2B = "[S: SPA] s. 48(2)(b)"
SRC_48_3 = "[S: SPA] s. 48(3)"
SRC_SB_16 = "[S: SPA-SB] s. 16(1)-(2)"

# Standard Bylaws s. 16(1): council size -> members required for quorum.
COUNCIL_QUORUM = {1: 1, 2: 2, 3: 2, 4: 2, 5: 3, 6: 3, 7: 4}


@dataclass(frozen=True)
class QuorumResult:
    met: bool
    rule: str
    source: str
    formula: str
    rules_version: str = RULES_VERSION
    required: int | None = None  # smallest number present that meets the rule; None for declared/adjourned

    def columns(self) -> dict[str, object]:
        """Stored quorum columns; callers persist these as given (B1-006)."""
        return {"required_count": self.required, "quorum_met": self.met, "quorum_rule": self.rule,
                "quorum_formula": self.formula, "rules_version": self.rules_version}


def _ceil_div(a: int, b: int) -> int:
    return -(-a // b)


def _fraction(rule: dict[str, Any]) -> tuple[int, int, str]:
    try:
        num = int(rule["numerator"])
        den = int(rule["denominator"])
        clause = str(rule["source_clause"]).strip()
    except (KeyError, TypeError, ValueError) as exc:
        raise RuleInputError("a fraction override needs numerator, denominator and source_clause") from exc
    if num < 0 or den <= 0 or not clause:
        raise RuleInputError("invalid fraction override")
    return num, den, clause


def general_quorum(
    *,
    present_votes: int,
    eligible_votes: int,
    strata_lot_count: int,
    owner_count: int,
    reconvened_after_adjournment: bool = False,
    override: dict[str, Any] | None = None,
) -> QuorumResult:
    present = require_count("present_votes", present_votes)
    eligible = require_count("eligible_votes", eligible_votes)
    lots = require_count("strata_lot_count", strata_lot_count)
    owners = require_count("owner_count", owner_count)
    if eligible == 0 or lots == 0 or present > eligible:
        raise RuleInputError("eligible votes and lots must be positive; present cannot exceed eligible")
    rule = override or {"type": "act_default"}

    if reconvened_after_adjournment:
        adjourned = rule.get("adjourned_rule")
        if adjourned is None or adjourned.get("type") == "act_default":
            return QuorumResult(
                True,
                "adjourned_meeting",
                SRC_48_3,
                f"reconvened after adjournment for no quorum: the {present} votes present are a quorum",
            )
        if adjourned.get("type") != "fraction":
            raise RuleInputError("unknown adjourned_rule type")
        num, den, clause = _fraction(adjourned)
        lhs, rhs = present * den, num * eligible
        met = lhs >= rhs
        return QuorumResult(
            met,
            "building_override_adjourned",
            f"Building bylaw {clause}",
            f"{present} × {den} {'≥' if met else '<'} {num} × {eligible}: {lhs} {'≥' if met else '<'} {rhs}",
            required=_ceil_div(num * eligible, den),
        )

    kind = rule.get("type")
    if kind == "fraction":
        num, den, clause = _fraction(rule)
        lhs, rhs = present * den, num * eligible
        met = lhs >= rhs
        return QuorumResult(
            met,
            "building_override",
            f"Building bylaw {clause}",
            f"{present} × {den} {'≥' if met else '<'} {num} × {eligible}: {lhs} {'≥' if met else '<'} {rhs}",
            required=_ceil_div(num * eligible, den),
        )
    if kind != "act_default":
        raise RuleInputError("unknown general_quorum_rule type")

    if lots < 4 or owners < 4:
        lhs, rhs = present * 3, 2 * eligible
        met = lhs >= rhs
        return QuorumResult(
            met,
            "small_strata_two_thirds",
            SRC_48_2B,
            f"{present} × 3 {'≥' if met else '<'} 2 × {eligible}: {lhs} {'≥' if met else '<'} {rhs}",
            required=_ceil_div(2 * eligible, 3),
        )
    lhs, rhs = present * 3, eligible
    met = lhs >= rhs
    return QuorumResult(
        met,
        "one_third",
        SRC_48_2A,
        f"{present} × 3 {'≥' if met else '<'} {eligible}: {lhs} {'≥' if met else '<'} {rhs}",
        required=_ceil_div(eligible, 3),
    )


def council_quorum(
    *, members_present: int, council_size: int, override: dict[str, Any] | None = None
) -> QuorumResult:
    present = require_count("members_present", members_present)
    size = require_count("council_size", council_size)
    if present > size:
        raise RuleInputError("members_present cannot exceed council_size")
    rule = override or {"type": "standard_bylaw_16"}
    if rule.get("type") == "fixed":
        try:
            minimum = int(rule["minimum"])
            clause = str(rule["source_clause"]).strip()
        except (KeyError, TypeError, ValueError) as exc:
            raise RuleInputError("a fixed council override needs minimum and source_clause") from exc
        if minimum <= 0 or not clause:
            raise RuleInputError("invalid council override")
        met = present >= minimum
        return QuorumResult(
            met, "building_override", f"Building bylaw {clause}", f"{present} {'≥' if met else '<'} {minimum}",
            required=minimum,
        )
    if rule.get("type") != "standard_bylaw_16":
        raise RuleInputError("unknown council_quorum_rule type")
    if size not in COUNCIL_QUORUM:
        raise RuleInputError("Standard Bylaw 16 covers councils of 1 to 7 members")
    required = COUNCIL_QUORUM[size]
    met = present >= required
    return QuorumResult(
        met,
        "standard_bylaw_16",
        SRC_SB_16,
        f"{present} present {'≥' if met else '<'} {required} required for a council of {size}",
        required=required,
    )


def declared_quorum(*, attested: bool) -> QuorumResult:
    """The chair declared quorum and the manager attests it, with no numbers."""
    if not attested:
        raise RuleInputError("a declared quorum must be attested by the manager")
    return QuorumResult(True, "declared_by_chair", "Attested by the manager", "quorum declared by the chair")
