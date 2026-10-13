"""Tests for API endpoints, SSE streams, and 4 demo scenarios."""

import json
import pytest
from fastapi.testclient import TestClient
from app.api import app, cases_db


@pytest.fixture
def client():
    return TestClient(app)


def test_health_check(client):
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "healthy"
    assert "llm_mode" in data
    assert "audit_blocks_count" in data


def test_list_scenarios(client):
    res = client.get("/scenarios")
    assert res.status_code == 200
    scenarios = res.json()
    assert len(scenarios) == 4
    case_ids = [s["case_id"] for s in scenarios]
    assert "CASE-1001" in case_ids
    assert "CASE-1002" in case_ids
    assert "CASE-1003" in case_ids
    assert "CASE-1004" in case_ids


def test_sse_stream_case_1001(client):
    """Scenario 1: Clean Win (R-002) streamed via GET /cases/CASE-1001/stream."""
    res = client.get("/cases/CASE-1001/stream")
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]

    content = res.text
    assert "event: POLICY_GATE" in content
    assert "event: MARGIN_ENGINE" in content
    assert "event: NARRATION" in content
    assert "event: AUDIT_CHAIN" in content
    assert "event: COMPLETE" in content

    # Check stage payloads
    assert '"stage": "POLICY_GATE"' in content
    assert '"R002_DELIVERY_CONFIRMED"' in content
    assert '"CONTEST"' in content


def test_sse_stream_all_four_scenarios(client):
    """Validates expected decisions and reason codes across all 4 demo scenarios."""
    expected = {
        "CASE-1001": ("CONTEST", "R002_DELIVERY_CONFIRMED"),
        "CASE-1002": ("NEEDS_HUMAN", "R003_AMBIGUOUS_EVIDENCE"),
        "CASE-1003": ("CONTEST", "R001_WINDOW_EXPIRED"),
        "CASE-1004": ("ACCEPT_REFUND", "R005_ECONOMIC_FEE_TRAP"),
    }

    for case_id, (exp_action, exp_reason) in expected.items():
        res = client.get(f"/cases/{case_id}/stream")
        assert res.status_code == 200
        text = res.text
        assert exp_action in text, f"Expected {exp_action} in stream for {case_id}"
        assert exp_reason in text, f"Expected {exp_reason} in stream for {case_id}"


def test_post_case_evaluate_stream(client):
    """Validates dynamic case submission via POST /cases/evaluate/stream."""
    payload = {
        "case_id": "CASE-9999",
        "order_id": "ORD-99999",
        "claim_date": "2026-10-10T10:00:00Z",
        "delivery_date": "2026-10-09T10:00:00Z",
        "order_amount": 100.0,
        "unit_margin": 30.0,
        "dispute_fee": 15.0,
        "claimed_reason": "ITEM_NOT_RECEIVED",
        "complaint_text": "Did not receive item.",
        "courier_events": [
            {
                "timestamp": "2026-10-09T10:00:00Z",
                "status": "DELIVERED",
                "note": "Delivered with signature",
                "geo_match": True,
                "signature_present": True,
            }
        ],
    }

    res = client.post("/cases/evaluate/stream", json=payload)
    assert res.status_code == 200
    assert "text/event-stream" in res.headers["content-type"]
    text = res.text
    assert "event: POLICY_GATE" in text
    assert "event: MARGIN_ENGINE" in text
    assert "event: NARRATION" in text
    assert "event: AUDIT_CHAIN" in text
    assert "CASE-9999" in text
