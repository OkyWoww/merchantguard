"""Tests for Deterministic Policy Gate rules (R-001 to R-006)."""

import pytest
from app.schemas import DisputeCase, CourierEvent, DecisionAction
from app.gate import PolicyGate


@pytest.fixture
def policy_gate():
    return PolicyGate({
        "policy_gate": {
            "return_window_days": 14,
            "high_value_cutoff": 250.0,
            "partial_damage_categories": ["DAMAGED", "PARTIAL_TRANSIT_DEFECT"],
        }
    })


def test_rule_r001_return_window_expired(policy_gate):
    """R-001: Claims filed beyond the 14-day window should trigger CONTEST."""
    case = DisputeCase(
        case_id="TEST-R001",
        order_id="ORD-101",
        claim_date="2026-10-30T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",  # 29 days elapsed
        order_amount=100.0,
        unit_margin=40.0,
        dispute_fee=15.0,
        claimed_reason="NOT_AS_DESCRIBED",
        complaint_text="Disputed after a month.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-01T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=True,
            )
        ],
    )
    action, reason, status, evals = policy_gate.evaluate(case)
    assert action == DecisionAction.CONTEST
    assert reason == "R001_WINDOW_EXPIRED"
    assert any(e.rule_id == "R-001" and not e.passed for e in evals)


def test_rule_r002_verified_signature_and_geo(policy_gate):
    """R-002: Deliveries with GPS match and signature must pass with CONTEST."""
    case = DisputeCase(
        case_id="TEST-R002",
        order_id="ORD-102",
        claim_date="2026-10-04T00:00:00Z",
        delivery_date="2026-10-02T00:00:00Z",  # 2 days elapsed
        order_amount=150.0,
        unit_margin=50.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="I did not receive this item.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-02T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=True,
            )
        ],
    )
    action, reason, status, evals = policy_gate.evaluate(case)
    assert action == DecisionAction.CONTEST
    assert reason == "R002_VERIFIED_SIGNATURE_GEO"
    assert status == "PASSED"


def test_rule_r003_high_value_escalation(policy_gate):
    """R-003: Orders above $250 without signature must escalate to NEEDS_HUMAN."""
    case = DisputeCase(
        case_id="TEST-R003",
        order_id="ORD-103",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=350.0,  # > 250
        unit_margin=120.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Missing luxury bag.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-01T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=False,  # No signature
            )
        ],
    )
    action, reason, status, evals = policy_gate.evaluate(case)
    assert action == DecisionAction.NEEDS_HUMAN
    assert reason == "R003_HIGH_VALUE_UNSIGNED"


def test_rule_r004_economic_fee_trap(policy_gate):
    """R-004: If dispute fee exceeds order value or margin is 0, auto-refund."""
    case = DisputeCase(
        case_id="TEST-R004",
        order_id="ORD-104",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=12.0,  # < dispute_fee of 15
        unit_margin=2.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Where is my phone adapter?",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-01T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=False,
            )
        ],
    )
    action, reason, status, evals = policy_gate.evaluate(case)
    assert action == DecisionAction.ACCEPT_REFUND
    assert reason == "R004_ECONOMIC_FEE_TRAP"


def test_rule_r005_partial_damage(policy_gate):
    """R-005: Damaged item categories should route to PARTIAL_REFUND offer."""
    case = DisputeCase(
        case_id="TEST-R005",
        order_id="ORD-105",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=80.0,
        unit_margin=30.0,
        dispute_fee=15.0,
        claimed_reason="DAMAGED",
        complaint_text="The corner was dented.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-01T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=True,
            )
        ],
    )
    action, reason, status, evals = policy_gate.evaluate(case)
    assert action == DecisionAction.PARTIAL_REFUND
    assert reason == "R005_PARTIAL_DEFECT_OFFER"


def test_rule_r006_missing_tracking_events(policy_gate):
    """R-006: Missing or unconfirmed tracking data routes to carrier investigation."""
    case = DisputeCase(
        case_id="TEST-R006",
        order_id="ORD-106",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=95.0,
        unit_margin=35.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Never got anything.",
        courier_events=[],  # No tracking events
    )
    action, reason, status, evals = policy_gate.evaluate(case)
    assert action == DecisionAction.NEEDS_HUMAN
    assert reason == "R006_COURIER_ANOMALY"
