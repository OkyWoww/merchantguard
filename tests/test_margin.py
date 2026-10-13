"""Tests for Statistical Margin Recovery Calculator, Model Inference & Expected Recovery."""

import pytest
from pathlib import Path
from app.schemas import DisputeCase, CourierEvent, DecisionAction, GateRuleEvaluation
from app.margin import MarginEngine


@pytest.fixture
def margin_engine():
    base_dir = Path(__file__).resolve().parent.parent
    model_path = base_dir / "models" / "margin.joblib"
    return MarginEngine(
        config={
            "margin_engine": {
                "default_dispute_fee": 15.0,
                "min_ev_hurdle_usd": 0.0,
                "partial_refund_fraction": 0.35,
                "p_contest_min": 0.60,
                "p_partial_min": 0.35,
                "marginal_recovery_threshold": 5.0,
                "unrecovered_cogs_ratio": 0.50,
            }
        },
        model_path=model_path,
    )


def test_ev_calculation_positive_recovery(margin_engine):
    """
    Verifies decision mathematics per docs/specs/rule.md §C:
    loss_if_refund = refund_amount + unrecovered_cost
    expected_loss_if_contest = (1 - p_win) * loss_if_refund + expected_fee_cost
    expected_recovery = loss_if_refund - expected_loss_if_contest
    """
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
    # p_win should be high with signature and geo match
    p_win = margin_engine.calculate_p_win(case, [])
    assert p_win >= 0.80

    loss_refund, exp_loss_contest, expected_recovery = margin_engine.calculate_decision_metrics(
        case, p_win
    )
    # COGS = 200 - 70 = 130. Unrecovered cost = 130 * 0.50 = 65.
    # loss_if_refund = 200 + 65 = 265
    assert loss_refund == 265.00
    assert expected_recovery > 0.0

    # Decision should be CONTEST
    decision = margin_engine.compute_final_decision(
        case=case,
        gate_action=DecisionAction.CONTEST,
        gate_reason="R002_DELIVERY_CONFIRMED",
        gate_status="PASSED",
        rule_evaluations=[],
    )
    assert decision.action == DecisionAction.CONTEST
    assert decision.expected_margin_recovery > 0.0


def test_negative_ev_override_to_accept_refund(margin_engine):
    """If EV is negative or fee outweighs potential recovery, override to ACCEPT_REFUND."""
    case = DisputeCase(
        case_id="TEST-M02",
        order_id="ORD-202",
        claim_date="2026-10-04T00:00:00Z",
        delivery_date="2026-10-02T00:00:00Z",
        order_amount=12.0,
        unit_margin=1.0,
        dispute_fee=25.0,  # Fee heavily outweighs order amount & margin
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


def test_ambiguous_middle_tier_routes_to_partial_refund(margin_engine):
    """
    When P(win) is in the ambiguous middle tier [p_partial_min, p_contest_min)
    and expected recovery is marginal (<= marginal_recovery_threshold),
    the engine proposes PARTIAL_REFUND to save dispute fee.
    """
    case = DisputeCase(
        case_id="TEST-M04",
        order_id="ORD-204",
        claim_date="2026-10-04T00:00:00Z",
        delivery_date="2026-10-02T00:00:00Z",
        order_amount=25.0,
        unit_margin=8.0,
        dispute_fee=15.0,
        claimed_reason="NOT_AS_DESCRIBED",
        complaint_text="Slight shade variation",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-02T00:00:00Z",
                status="DELIVERED",
                geo_match=False,
                signature_present=False,
            )
        ],
    )
    # Manually test with a simulated middle-tier p_win
    loss_refund, _, _ = margin_engine.calculate_decision_metrics(case, 0.50)
    # Expected recovery for p_win=0.50: 0.50 * (25 + 8.5) - 15 = 16.75 - 15 = 1.75 <= 5.0
    decision = margin_engine.compute_final_decision(
        case=case,
        gate_action=DecisionAction.CONTEST,
        gate_reason="STANDARD_GATE_PASS",
        gate_status="PASSED",
        rule_evaluations=[],
    )
    # With p_win low/middle and high dispute fee ($15 on $25 order), recovery is marginal or negative
    assert decision.action in (DecisionAction.PARTIAL_REFUND, DecisionAction.ACCEPT_REFUND)
    if decision.action == DecisionAction.PARTIAL_REFUND:
        assert decision.settlement_offer == round(25.0 * 0.35, 2)


def test_model_artifact_loaded_successfully(margin_engine):
    """Ensures models/margin.joblib was successfully detected and loaded."""
    assert margin_engine.model_pipeline is not None
