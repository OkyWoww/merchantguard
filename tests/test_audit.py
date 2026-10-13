"""Tests for cryptographic hash-chain audit log system."""

import pytest
import tempfile
from pathlib import Path
from app.schemas import DecisionResult, DecisionAction
from app.audit import AuditChain, GENESIS_PREVIOUS_HASH


@pytest.fixture
def temp_audit_chain():
    with tempfile.TemporaryDirectory() as tmpdir:
        log_file = Path(tmpdir) / "audit_test.json"
        chain = AuditChain(storage_path=str(log_file))
        yield chain


def test_audit_chain_append_and_linkage(temp_audit_chain):
    """Verifies that block hashes link to predecessor block hashes consecutively."""
    d1 = DecisionResult(
        case_id="CASE-1",
        action=DecisionAction.CONTEST,
        reason_code="R002_PASSED",
        p_win=0.88,
        expected_margin_recovery=55.0,
        gate_status="PASSED",
    )
    b1 = temp_audit_chain.append_decision(d1)
    assert b1.index == 0
    assert b1.previous_hash == GENESIS_PREVIOUS_HASH
    assert len(b1.block_hash) == 64

    d2 = DecisionResult(
        case_id="CASE-2",
        action=DecisionAction.ACCEPT_REFUND,
        reason_code="R004_ECONOMIC_FEE_TRAP",
        p_win=0.15,
        expected_margin_recovery=-8.5,
        gate_status="TRIGGERED",
    )
    b2 = temp_audit_chain.append_decision(d2)
    assert b2.index == 1
    assert b2.previous_hash == b1.block_hash


def test_audit_chain_integrity_verification(temp_audit_chain):
    """Verifies valid chain reports valid, and modified block hash fails verification."""
    d = DecisionResult(
        case_id="CASE-1",
        action=DecisionAction.CONTEST,
        reason_code="R002_PASSED",
        p_win=0.88,
        expected_margin_recovery=55.0,
        gate_status="PASSED",
    )
    temp_audit_chain.append_decision(d)

    result = temp_audit_chain.verify_integrity()
    assert result.valid is True
    assert result.total_blocks == 1

    # Simulate malicious database tampering
    temp_audit_chain.chain[0].action = "ACCEPT_REFUND"  # Mutated action
    tampered_result = temp_audit_chain.verify_integrity()
    assert tampered_result.valid is False
    assert tampered_result.corrupted_index == 0
