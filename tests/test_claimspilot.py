from claimspilot import ClaimIntake, route_claim


def test_low_value_complete_claim_routes_straight_through():
    route = route_claim(
        ClaimIntake(
            claim_id="CLM-100",
            claim_type="auto",
            amount_usd=1200,
            policy_active=True,
            claimant_country="US",
        )
    )

    assert route.route == "straight_through"
    assert not route.requires_human_review


def test_injury_claim_routes_to_adjuster_review():
    route = route_claim(
        ClaimIntake(
            claim_id="CLM-101",
            claim_type="auto",
            amount_usd=2000,
            policy_active=True,
            claimant_country="US",
            has_injury=True,
        )
    )

    assert route.route == "adjuster_review"
    assert route.requires_human_review
    assert "injury_claim" in route.reasons


def test_high_fraud_claim_routes_to_siu():
    route = route_claim(
        ClaimIntake(
            claim_id="CLM-102",
            claim_type="home",
            amount_usd=3000,
            policy_active=True,
            claimant_country="US",
            fraud_score=0.91,
        )
    )

    assert route.route == "siu_review"
    assert route.sla_hours == 8

