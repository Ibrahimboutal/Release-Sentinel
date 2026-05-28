from __future__ import annotations

from dataclasses import dataclass
from typing import Literal

ClaimType = Literal["auto", "home", "health", "travel"]
ClaimRouteName = Literal["straight_through", "adjuster_review", "siu_review", "manual_exception"]


@dataclass(frozen=True)
class ClaimIntake:
    claim_id: str
    claim_type: ClaimType
    amount_usd: float
    policy_active: bool
    claimant_country: str
    has_injury: bool = False
    prior_claims_12m: int = 0
    missing_documents: int = 0
    fraud_score: float = 0.0


@dataclass(frozen=True)
class ClaimRoute:
    route: ClaimRouteName
    reasons: list[str]
    sla_hours: int
    requires_human_review: bool


def route_claim(claim: ClaimIntake) -> ClaimRoute:
    """Small deterministic workflow for tests and demo screenshots.

    The hackathon entry is about testing governance, not insurance. This
    function creates a realistic enough business surface for risk analysis,
    targeted regression, and human-review examples.
    """

    reasons: list[str] = []

    if not claim.policy_active:
        return ClaimRoute(
            route="manual_exception",
            reasons=["inactive_policy"],
            sla_hours=4,
            requires_human_review=True,
        )

    if claim.missing_documents > 0:
        reasons.append("missing_documents")

    if claim.fraud_score >= 0.82 or claim.prior_claims_12m >= 4:
        reasons.append("fraud_or_repeat_claim_pattern")
        return ClaimRoute(
            route="siu_review",
            reasons=reasons,
            sla_hours=8,
            requires_human_review=True,
        )

    if claim.amount_usd >= 7500 or claim.has_injury or reasons:
        if claim.amount_usd >= 7500:
            reasons.append("high_value_claim")
        if claim.has_injury:
            reasons.append("injury_claim")
        return ClaimRoute(
            route="adjuster_review",
            reasons=reasons,
            sla_hours=24,
            requires_human_review=True,
        )

    return ClaimRoute(
        route="straight_through",
        reasons=["low_value_complete_claim"],
        sla_hours=2,
        requires_human_review=False,
    )

