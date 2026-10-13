"""Tests for Statistical Margin Recovery Calculator and Expected Value (EV)."""

import pytest
from app.schemas import DisputeCase, CourierEvent, DecisionAction, GateRuleEvaluation
from app.margin import MarginEngine


@pytest.fixture
def margin_engine():
    return MarginEngine({
        "margin_engine": {
            "default_dispute_fee": 15.0,
            "min_ev_hurdle_usd": 0.0,
            "partial_refund_fraction": 0.35,
        }
    })


def test_ev_calculation_positive_recovery(margin_engine):
    """Verifies formula EV = P(Win) * (Margin + Fee) - (1 - P(Win)) * Fee."""
    case = DisputeCase(
        case_id="TEST-M01",
        order_id="ORD-201",
        claim_date="2026-10-04T00:00:00Z",
        delivery_date="2026-10-02T00:00:00Z",
        order_amount=200.0,
        unit_margin=70.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Dispute test",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-02T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=True,
            )
        ],
    )
    # p_win should be high with geo match + signature
    p_win = margin_engine.calculate_p_win(case, [])
    assert p_win >= 0.80

    ev = margin_engine.calculate_expected_margin_recovery(case, p_win)
    assert ev > 0.0


def test_negative_ev_override_to_accept_refund(margin_engine):
    """If EV is negative, contest recommendation must be overridden to ACCEPT_REFUND."""
    case = DisputeCase(
        case_id="TEST-M02",
        order_id="ORD-202",
        claim_date="2026-10-04T00:00:00Z",
        delivery_date="2026-10-02T00:00:00Z",
        order_amount=12.0,
        unit_margin=1.0,
        dispute_fee=25.0,  # Fee heavily outweighs margin
        claimed_reason="NOT_AS_DESCRIBED",
        complaint_text="Dispute test",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-02T00:00:00Z",
                status="DELIVERED",
                geo_match=False,
                signature_present=False,
            )
        ],
    )
    decision = margin_engine.compute_final_decision(
        case=case,
        gate_action=DecisionAction.CONTEST,
        gate_reason="STANDARD_GATE_PASS",
        gate_status="PASSED",
        rule_evaluations=[],
    )
    assert decision.action == DecisionAction.ACCEPT_REFUND
    assert decision.reason_code == "R004_NEGATIVE_EV_AVOIDANCE"
    assert decision.expected_margin_recovery < 0.0


def test_partial_refund_settlement_offer(margin_engine):
    """Verifies that PARTIAL_REFUND calculates standard 35% settlement fraction."""
    case = DisputeCase(
        case_id="TEST-M03",
        order_id="ORD-203",
        claim_date="2026-10-04T00:00:00Z",
        delivery_date="2026-10-02T00:00:00Z",
        order_amount=100.0,
        unit_margin=40.0,
        dispute_fee=15.0,
        claimed_reason="DAMAGED",
        complaint_text="Scratch on body",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-02T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=True,
            )
        ],
    )
    decision = margin_engine.compute_final_decision(
        case=case,
        gate_action=DecisionAction.PARTIAL_REFUND,
        gate_reason="R005_PARTIAL_DEFECT_OFFER",
        gate_status="TRIGGERED",
        rule_evaluations=[],
    )
    assert decision.action == DecisionAction.PARTIAL_REFUND
    assert decision.settlement_offer == 35.00
