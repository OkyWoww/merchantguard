"""Tests for Degradation Ladder Router & Circuit Breaker (Task T2.4).

Covers:
1. Happy path live inference on AMD ROCm vLLM endpoint (mode="LIVE").
2. Forced timeout on Tier 1 falling back to cached replay (mode="REPLAY").
3. Cache miss falling back to deterministic template (mode="TEMPLATE").
4. Circuit breaker tripping after 2 consecutive failures and skipping Tier 1.
5. Circuit breaker recovery to HALF_OPEN after timeout.
"""

import pytest
import time
from unittest.mock import AsyncMock, patch
import httpx

from app.schemas import DisputeCase, DecisionResult, DecisionAction, CourierEvent
from app.router import InferenceRouter, CircuitBreaker


@pytest.fixture
def sample_case_1001():
    return DisputeCase(
        case_id="CASE-1001",
        order_id="ORD-88219",
        claim_date="2026-10-04T14:30:00Z",
        delivery_date="2026-10-02T10:15:00Z",
        order_amount=185.00,
        unit_margin=62.00,
        dispute_fee=15.00,
        claimed_reason="ITEM_NOT_RECEIVED",
        complaint_text="I was home all day and nobody brought any package.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-02T10:15:00Z",
                status="DELIVERED",
                note="Handed directly to resident. Signed by M. Vance",
                geo_match=True,
                signature_present=True,
            )
        ],
    )


@pytest.fixture
def sample_decision():
    return DecisionResult(
        case_id="CASE-1001",
        action=DecisionAction.CONTEST,
        reason_code="R002_DELIVERY_CONFIRMED",
        p_win=0.98,
        expected_margin_recovery=226.57,
        gate_status="PASSED",
        rule_evaluations=[],
    )


@pytest.mark.asyncio
async def test_live_vllm_happy_path(sample_case_1001, sample_decision):
    """Tier 1: Successful response from AMD vLLM OpenAI-compatible endpoint."""
    router = InferenceRouter(mode="live", vllm_base_url="http://mock-vllm:8000/v1")

    mock_resp = httpx.Response(
        status_code=200,
        json={
            "choices": [
                {
                    "message": {
                        "content": "Official response generated on AMD ROCm: Order was delivered with signature."
                    }
                }
            ],
            "usage": {"completion_tokens": 28},
        },
        request=httpx.Request("POST", "http://mock-vllm:8000/v1/chat/completions"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        payload = await router.generate_narrative(sample_case_1001, sample_decision)

        assert payload.mode == "LIVE"
        assert payload.llm_provider == "amd_rocm_vllm"
        assert "Official response generated on AMD ROCm" in payload.draft_reply
        assert payload.tokens_out == 28
        assert payload.generation_latency_ms is not None
        assert router.circuit_breaker.state == "CLOSED"
        assert router.circuit_breaker.failure_count == 0


@pytest.mark.asyncio
async def test_forced_timeout_degrades_to_replay_cache(sample_case_1001, sample_decision):
    """Tier 1 failure (timeout) degrades to Tier 2 (Replay Cache)."""
    router = InferenceRouter(mode="live", timeout_seconds=35.0)

    with patch.object(httpx.AsyncClient, "post", side_effect=httpx.TimeoutException("Read timeout after 8s")):
        payload = await router.generate_narrative(sample_case_1001, sample_decision)

        assert payload.mode == "REPLAY"
        assert payload.llm_provider == "replay_cache_rocm_fallback"
        assert payload.verified_citations is True
        assert len(payload.claims) > 0
        assert router.circuit_breaker.failure_count == 1
        assert router.circuit_breaker.state == "CLOSED"


@pytest.mark.asyncio
async def test_cache_miss_degrades_to_deterministic_template(sample_decision):
    """Tier 2 cache miss degrades to Tier 3 (Deterministic Template Synthesizer)."""
    # Case with no replay file in data/replay/
    unknown_case = DisputeCase(
        case_id="CASE-9999",
        order_id="ORD-99999",
        claim_date="2026-10-04T00:00:00Z",
        delivery_date="2026-10-02T00:00:00Z",
        order_amount=99.00,
        unit_margin=30.00,
        dispute_fee=15.00,
        claimed_reason="NOT_AS_DESCRIBED",
        complaint_text="Unknown scenario testing template fallback.",
        courier_events=[],
    )

    router = InferenceRouter(mode="replay")
    payload = await router.generate_narrative(unknown_case, sample_decision)

    assert payload.mode == "TEMPLATE"
    assert payload.llm_provider == "deterministic_template"
    assert payload.model == "template-synthesizer"
    assert "Deterministic Template" in payload.draft_reply
    assert payload.verified_citations is True
    assert payload.tokens_out is not None


@pytest.mark.asyncio
async def test_circuit_breaker_tripping_and_skipping_tier1(sample_case_1001, sample_decision):
    """Circuit breaker trips OPEN after 2 failures and skips Tier 1 on subsequent calls."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60.0)
    router = InferenceRouter(mode="live", circuit_breaker=cb)

    with patch.object(httpx.AsyncClient, "post", side_effect=httpx.ConnectError("Connection refused")) as mock_post:
        # Failure 1
        p1 = await router.generate_narrative(sample_case_1001, sample_decision)
        assert p1.mode == "REPLAY"
        assert cb.failure_count == 1
        assert cb.state == "CLOSED"
        assert mock_post.call_count == 1

        # Failure 2 -> Circuit trips to OPEN
        p2 = await router.generate_narrative(sample_case_1001, sample_decision)
        assert p2.mode == "REPLAY"
        assert cb.failure_count == 2
        assert cb.state == "OPEN"
        assert mock_post.call_count == 2

        # Call 3: Circuit is OPEN -> Tier 1 is skipped immediately without network call!
        p3 = await router.generate_narrative(sample_case_1001, sample_decision)
        assert p3.mode == "REPLAY"
        # mock_post should still be 2, NOT 3!
        assert mock_post.call_count == 2


@pytest.mark.asyncio
async def test_http_429_degrades_to_replay(sample_case_1001, sample_decision):
    """HTTP 429 from gateway is treated as a failure and falls back to REPLAY."""
    router = InferenceRouter(mode="live", timeout_seconds=35.0)

    mock_resp = httpx.Response(
        status_code=429,
        json={"error": "rate limit exceeded"},
        request=httpx.Request("POST", "http://mock-vllm:8000/v1/chat/completions"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        payload = await router.generate_narrative(sample_case_1001, sample_decision)

        assert payload.mode in ("REPLAY", "TEMPLATE")
        assert router.circuit_breaker.failure_count >= 1


@pytest.mark.asyncio
async def test_http_500_degrades_to_replay(sample_case_1001, sample_decision):
    """HTTP 5xx from gateway is treated as a failure and falls back to REPLAY."""
    router = InferenceRouter(mode="live", timeout_seconds=35.0)

    mock_resp = httpx.Response(
        status_code=503,
        json={"error": "service unavailable"},
        request=httpx.Request("POST", "http://mock-vllm:8000/v1/chat/completions"),
    )

    with patch.object(httpx.AsyncClient, "post", new_callable=AsyncMock) as mock_post:
        mock_post.return_value = mock_resp
        payload = await router.generate_narrative(sample_case_1001, sample_decision)

        assert payload.mode in ("REPLAY", "TEMPLATE")
        assert router.circuit_breaker.failure_count >= 1


@pytest.mark.asyncio
async def test_circuit_breaker_half_open_recovery():
    """Circuit breaker transitions to HALF_OPEN after recovery timeout expires."""
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60.0)
    cb.record_failure()
    cb.record_failure()
    assert cb.state == "OPEN"

    # Immediately: cannot attempt
    assert cb.can_attempt() is False

    # Simulate elapsed 65 seconds
    cb.last_failure_time = time.time() - 65.0
    assert cb.can_attempt() is True
    assert cb.state == "HALF_OPEN"

    # Upon success: transitions back to CLOSED
    cb.record_success()
    assert cb.state == "CLOSED"
    assert cb.failure_count == 0
