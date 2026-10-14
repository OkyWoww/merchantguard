"""Live-gateway integration tests — marked `live`, excluded from default pytest run.

Run with:  pytest -v -m live tests/test_live_gateway.py
Requires:  OPENAI_API_KEY set in .env (real AMD Token Factory bearer key).
These tests consume API quota; never run in CI without explicit opt-in.
"""

import os
import time
import pytest
import httpx
import asyncio
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

from app.router import InferenceRouter
from app.schemas import DisputeCase, CourierEvent
from app.gate import PolicyGate
from app.margin import MarginEngine
import yaml


def _load_engines():
    base = Path(__file__).resolve().parent.parent
    with open(base / "config" / "policy.yaml") as f:
        pcfg = yaml.safe_load(f)
    with open(base / "config" / "margin.yaml") as f:
        mcfg = yaml.safe_load(f)
    return PolicyGate(pcfg), MarginEngine(mcfg)


def _case_1001():
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


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_tier1_http200_and_latency():
    """LIVE: AMD Token Factory returns HTTP 200; latency < 35s; mode=LIVE."""
    case = _case_1001()
    gate, margin = _load_engines()
    gate_action, gate_reason, gate_status, rule_evals = gate.evaluate(case)
    decision = margin.compute_final_decision(
        case=case,
        gate_action=gate_action,
        gate_reason=gate_reason,
        gate_status=gate_status,
        rule_evaluations=rule_evals,
    )

    router = InferenceRouter(mode="live")
    t0 = time.perf_counter()
    narrative = await router.generate_narrative(case, decision)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    assert narrative.mode == "LIVE", f"Expected LIVE, got {narrative.mode}"
    assert narrative.llm_provider == "amd_rocm_vllm"
    assert elapsed_ms < 35_000, f"Latency {elapsed_ms:.0f}ms exceeds 35s timeout"
    assert narrative.tokens_out > 0
    assert len(narrative.draft_reply) > 10
    print(f"\n[LIVE] latency={elapsed_ms:.0f}ms tokens_out={narrative.tokens_out} model={narrative.model}")


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_tier1_http429_degrades_to_replay():
    """LIVE: Simulate HTTP 429 from gateway — circuit breaker records failure, falls back to REPLAY."""
    import unittest.mock as mock

    case = _case_1001()
    gate, margin = _load_engines()
    gate_action, gate_reason, gate_status, rule_evals = gate.evaluate(case)
    decision = margin.compute_final_decision(
        case=case,
        gate_action=gate_action,
        gate_reason=gate_reason,
        gate_status=gate_status,
        rule_evaluations=rule_evals,
    )

    mock_resp = httpx.Response(
        status_code=429,
        json={"error": "rate limit exceeded"},
        request=httpx.Request("POST", "https://developer.amd.com.cn/radeon/api/v1/chat/completions"),
    )

    router = InferenceRouter(mode="live")
    with mock.patch.object(httpx.AsyncClient, "post", new_callable=mock.AsyncMock) as mp:
        mp.return_value = mock_resp
        narrative = await router.generate_narrative(case, decision)

    assert narrative.mode in ("REPLAY", "TEMPLATE"), f"Expected REPLAY/TEMPLATE after 429, got {narrative.mode}"
    assert router.circuit_breaker.failure_count >= 1
    print(f"\n[429->FALLBACK] mode={narrative.mode} cb_failures={router.circuit_breaker.failure_count}")


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_tier1_http500_degrades_to_replay():
    """LIVE: Simulate HTTP 500 from gateway — records failure, falls back to REPLAY/TEMPLATE."""
    import unittest.mock as mock

    case = _case_1001()
    gate, margin = _load_engines()
    gate_action, gate_reason, gate_status, rule_evals = gate.evaluate(case)
    decision = margin.compute_final_decision(
        case=case,
        gate_action=gate_action,
        gate_reason=gate_reason,
        gate_status=gate_status,
        rule_evaluations=rule_evals,
    )

    mock_resp = httpx.Response(
        status_code=500,
        json={"error": "internal server error"},
        request=httpx.Request("POST", "https://developer.amd.com.cn/radeon/api/v1/chat/completions"),
    )

    router = InferenceRouter(mode="live")
    with mock.patch.object(httpx.AsyncClient, "post", new_callable=mock.AsyncMock) as mp:
        mp.return_value = mock_resp
        narrative = await router.generate_narrative(case, decision)

    assert narrative.mode in ("REPLAY", "TEMPLATE"), f"Expected REPLAY/TEMPLATE after 500, got {narrative.mode}"
    assert router.circuit_breaker.failure_count >= 1
    print(f"\n[500->FALLBACK] mode={narrative.mode} cb_failures={router.circuit_breaker.failure_count}")


@pytest.mark.live
@pytest.mark.asyncio
async def test_live_p50_p95_latency_benchmark():
    """LIVE: 5 sequential calls to AMD Token Factory; reports p50/p95 latency and tokens/s."""
    api_key = os.getenv("OPENAI_API_KEY", "")
    base_url = os.getenv("VLLM_BASE_URL", "https://developer.amd.com.cn/radeon/api/v1")
    model = os.getenv("MODEL_NAME", "Gemma-4-31B-IT")
    timeout = float(os.getenv("VLLM_TIMEOUT", "60.0"))

    latencies = []
    tokens_list = []

    for i in range(5):
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": "You are a concise assistant."},
                {"role": "user", "content": f"Say OK_{i} and nothing else."},
            ],
            "temperature": 0.0,
            "max_tokens": 10,
        }
        t0 = time.perf_counter()
        async with httpx.AsyncClient(timeout=timeout) as client:
            resp = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000

        assert resp.status_code == 200, f"Call {i} returned {resp.status_code}"
        data = resp.json()
        tokens = data.get("usage", {}).get("completion_tokens", 0)
        latencies.append(elapsed_ms)
        tokens_list.append(tokens)

    latencies.sort()
    n = len(latencies)
    p50 = latencies[n // 2]
    p95 = latencies[int(n * 0.95)]
    avg_tokens = sum(tokens_list) / n
    avg_tps = avg_tokens / (sum(latencies) / n / 1000) if sum(latencies) > 0 else 0

    print(f"\n[LIVE BENCHMARK] n={n} p50={p50:.0f}ms p95={p95:.0f}ms avg_tokens={avg_tokens:.1f} avg_tps={avg_tps:.2f}")
    assert p50 < 35_000, f"p50 {p50:.0f}ms exceeds 35s timeout"
