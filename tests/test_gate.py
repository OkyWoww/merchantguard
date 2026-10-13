"""Tests for Deterministic Policy Gate rules (R-001 through R-006).

Covers positive and negative test cases for every rule defined in docs/specs/rule_3.md §B:
- R-001: Return window compliance (claim_date - delivery_date > return_window_days)
- R-002: Delivery confirmed with signature and GPS geo match
- R-003: Courier note contradiction (e.g., left unattended / entry gate)
- R-004: High-value threshold ($250+) with weak evidence
- R-005: Dispute fee >= recoverable unit margin (economic fee trap)
- R-006: Missing required fields or tracking anomalies
"""

import pytest
from app.schemas import DisputeCase, CourierEvent, DecisionAction
from app.gate import PolicyGate


@pytest.fixture
def policy_gate():
    return PolicyGate({
        "policy_gate": {
            "return_window_days": 14,
            "high_value_threshold": 250.0,
            "high_value_cutoff": 250.0,
            "courier_contradiction_keywords": [
                "unattended", "porch", "gate", "outside", "driveway", "lobby", "left near", "no answer"
            ],
            "required_fields": ["order_id", "claim_date", "delivery_date", "order_amount"],
            "partial_damage_categories": ["DAMAGED", "PARTIAL_TRANSIT_DEFECT"],
            "escalate_on_missing_tracking": True,
            "require_carrier_geo_match": True,
        }
    })


# ----------------------------------------------------------------------
# Rule R-001: Return Window Expired vs Compliant
# ----------------------------------------------------------------------
def test_rule_r001_return_window_expired_negative(policy_gate):
    """R-001 Negative: Claims filed beyond the 14-day window trigger auto-contest."""
    case = DisputeCase(
        case_id="TEST-R001-FAIL",
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
    assert status == "TRIGGERED"
    assert any(e.rule_id == "R-001" and not e.passed for e in evals)


def test_rule_r001_return_window_valid_positive(policy_gate):
    """R-001 Positive: Claims within 14-day window pass R-001."""
    case = DisputeCase(
        case_id="TEST-R001-PASS",
        order_id="ORD-101-P",
        claim_date="2026-10-04T00:00:00Z",
        delivery_date="2026-10-02T00:00:00Z",  # 2 days elapsed
        order_amount=100.0,
        unit_margin=40.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Never received parcel.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-02T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=True,
            )
        ],
    )
    _, _, _, evals = policy_gate.evaluate(case)
    r001_eval = next(e for e in evals if e.rule_id == "R-001")
    assert r001_eval.passed is True


# ----------------------------------------------------------------------
# Rule R-002: Verified Delivery (Signature + Geo)
# ----------------------------------------------------------------------
def test_rule_r002_verified_signature_and_geo_positive(policy_gate):
    """R-002 Positive: Deliveries with GPS match and signature pass with CONTEST."""
    case = DisputeCase(
        case_id="TEST-R002-PASS",
        order_id="ORD-102",
        claim_date="2026-10-04T00:00:00Z",
        delivery_date="2026-10-02T00:00:00Z",
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
    assert reason in ("R002_DELIVERY_CONFIRMED", "R002_VERIFIED_SIGNATURE_GEO")
    assert status == "PASSED"
    assert any(e.rule_id == "R-002" and e.passed for e in evals)


def test_rule_r002_unverified_carrier_negative(policy_gate):
    """R-002 Negative: Missing signature & geo mismatch routes to investigation."""
    case = DisputeCase(
        case_id="TEST-R002-FAIL",
        order_id="ORD-102-F",
        claim_date="2026-10-04T00:00:00Z",
        delivery_date="2026-10-02T00:00:00Z",
        order_amount=80.0,
        unit_margin=30.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Missing order.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-02T00:00:00Z",
                status="DELIVERED",
                geo_match=False,
                signature_present=False,
            )
        ],
    )
    action, reason, status, evals = policy_gate.evaluate(case)
    assert action == DecisionAction.NEEDS_HUMAN
    assert any(e.rule_id == "R-002" and not e.passed for e in evals)


# ----------------------------------------------------------------------
# Rule R-003: Courier Contradiction
# ----------------------------------------------------------------------
def test_rule_r003_courier_contradiction_negative(policy_gate):
    """R-003 Negative: Courier note mentioning unattended/gate contradicts proof."""
    case = DisputeCase(
        case_id="TEST-R003-FAIL",
        order_id="ORD-103-F",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=120.0,
        unit_margin=40.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Item was stolen from outside.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-01T00:00:00Z",
                status="DELIVERED",
                note="Package left unattended near entry gate",
                geo_match=True,
                signature_present=False,
            )
        ],
    )
    action, reason, status, evals = policy_gate.evaluate(case)
    assert action == DecisionAction.NEEDS_HUMAN
    assert reason == "R003_AMBIGUOUS_EVIDENCE"
    assert status == "ESCALATED"
    assert any(e.rule_id == "R-003" and not e.passed for e in evals)


def test_rule_r003_courier_consistent_positive(policy_gate):
    """R-003 Positive: Courier note with secure handover passes R-003."""
    case = DisputeCase(
        case_id="TEST-R003-PASS",
        order_id="ORD-103-P",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=120.0,
        unit_margin=40.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Did not get item.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-01T00:00:00Z",
                status="DELIVERED",
                note="Handed directly to resident. Signed by M. Vance",
                geo_match=True,
                signature_present=True,
            )
        ],
    )
    _, _, _, evals = policy_gate.evaluate(case)
    r003_eval = next(e for e in evals if e.rule_id == "R-003")
    assert r003_eval.passed is True


# ----------------------------------------------------------------------
# Rule R-004: High-Value Item Custody
# ----------------------------------------------------------------------
def test_rule_r004_high_value_weak_evidence_negative(policy_gate):
    """R-004 Negative: Orders >= $250 without physical signature escalate to human."""
    case = DisputeCase(
        case_id="TEST-R004-FAIL",
        order_id="ORD-104-F",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=350.0,  # >= $250
        unit_margin=120.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Missing luxury bag.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-01T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=False,  # Weak evidence
            )
        ],
    )
    action, reason, status, evals = policy_gate.evaluate(case)
    assert action == DecisionAction.NEEDS_HUMAN
    assert reason in ("R004_HIGH_VALUE_WEAK_EVIDENCE", "R003_HIGH_VALUE_UNSIGNED")
    assert status == "ESCALATED"


def test_rule_r004_high_value_strong_evidence_positive(policy_gate):
    """R-004 Positive: Orders >= $250 WITH signature & geo match pass R-004."""
    case = DisputeCase(
        case_id="TEST-R004-PASS",
        order_id="ORD-104-P",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=500.0,
        unit_margin=180.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Item not received.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-01T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=True,
            )
        ],
    )
    _, _, _, evals = policy_gate.evaluate(case)
    r004_eval = next(e for e in evals if e.rule_id == "R-004")
    assert r004_eval.passed is True


# ----------------------------------------------------------------------
# Rule R-005: Economic Fee Trap Check
# ----------------------------------------------------------------------
def test_rule_r005_economic_fee_trap_negative(policy_gate):
    """R-005 Negative: Dispute fee >= recoverable margin triggers auto ACCEPT_REFUND."""
    case = DisputeCase(
        case_id="TEST-R005-FAIL",
        order_id="ORD-105-F",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=12.0,
        unit_margin=2.0,
        dispute_fee=15.0,  # Fee 15 > margin 2
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Small cord missing.",
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
    assert reason == "R005_ECONOMIC_FEE_TRAP"
    assert status == "TRIGGERED"
    assert any(e.rule_id == "R-005" and not e.passed for e in evals)


def test_rule_r005_healthy_margin_positive(policy_gate):
    """R-005 Positive: Unit margin > dispute fee passes R-005."""
    case = DisputeCase(
        case_id="TEST-R005-PASS",
        order_id="ORD-105-P",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=80.0,
        unit_margin=35.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Missing item.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-01T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=True,
            )
        ],
    )
    _, _, _, evals = policy_gate.evaluate(case)
    r005_eval = next(e for e in evals if e.rule_id == "R-005")
    assert r005_eval.passed is True


# ----------------------------------------------------------------------
# Rule R-006: Required Fields & Tracking Completeness
# ----------------------------------------------------------------------
def test_rule_r006_missing_required_fields_negative(policy_gate):
    """R-006 Negative: Missing order_id or dates escalates to human."""
    case = DisputeCase(
        case_id="TEST-R006-FAIL",
        order_id="",  # Missing required field
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=95.0,
        unit_margin=35.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="Incomplete case info.",
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
    assert action == DecisionAction.NEEDS_HUMAN
    assert reason == "R006_INCOMPLETE_CASE"
    assert status == "ESCALATED"
    assert any(e.rule_id == "R-006" and not e.passed for e in evals)


def test_rule_r006_missing_tracking_events_negative(policy_gate):
    """R-006 Negative: Empty courier events escalates to carrier investigation."""
    case = DisputeCase(
        case_id="TEST-R006-EVENTS",
        order_id="ORD-106",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=95.0,
        unit_margin=35.0,
        dispute_fee=15.0,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="No tracking anywhere.",
        courier_events=[],  # No tracking events
    )
    action, reason, status, evals = policy_gate.evaluate(case)
    assert action == DecisionAction.NEEDS_HUMAN
    assert reason == "R006_COURIER_ANOMALY"
    assert status == "ESCALATED"


def test_rule_partial_damage_routing(policy_gate):
    """Partial damage categories route to PARTIAL_REFUND offer."""
    case = DisputeCase(
        case_id="TEST-PARTIAL",
        order_id="ORD-107",
        claim_date="2026-10-03T00:00:00Z",
        delivery_date="2026-10-01T00:00:00Z",
        order_amount=80.0,
        unit_margin=30.0,
        dispute_fee=15.0,
        claimed_reason="DAMAGED",
        complaint_text="Dented side panel.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-01T00:00:00Z",
                status="DELIVERED",
                geo_match=True,
                signature_present=True,
            )
        ],
    )
    action, reason, status, _ = policy_gate.evaluate(case)
    assert action == DecisionAction.PARTIAL_REFUND
    assert reason == "R005_PARTIAL_DEFECT_OFFER"
    assert status == "TRIGGERED"
