"""Tier 2 REPLAY degradation test — forces timeout/429 on Tier 1, verifies fallback."""
import asyncio
import sys
import os
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.router import InferenceRouter, CircuitBreaker
from app.schemas import DisputeCase, CourierEvent


def _make_case():
    return DisputeCase(
        case_id="CASE-1001",
        order_id="ORD-9001",
        order_amount=250.00,
        unit_margin=46.00,
        dispute_fee=15.00,
        claim_date="2026-10-10",
        delivery_date="2026-09-27",
        return_window_days=14,
        claimed_reason="item_not_received",
        complaint_text="I never received my order.",
        courier_events=[
            CourierEvent(
                timestamp="2026-09-27T14:00:00",
                status="DELIVERED",
                note="Signed by resident",
                geo_match=True,
                signature_present=True,
            )
        ],
    )


async def test_tier2_replay():
    """Simulate Tier 1 as unreachable (bad URL) → expect REPLAY fallback."""
    print("=== TIER 2 REPLAY DEGRADATION TEST ===")
    print("Simulating: Tier 1 unreachable (bad URL, instant connection error)")

    router = InferenceRouter(
        mode="live",
        vllm_base_url="http://127.0.0.1:9999/v1",  # non-existent port → instant fail
        vllm_model="DeepSeek-V4-Flash",
        api_key="dummy-key-for-test",
        replay_dir=Path("data/replay"),
        timeout_seconds=2.0,
    )

    case = _make_case()
    # We need a decision stub; import margin engine for real decision
    from app.gate import PolicyGate
    from app.margin import MarginEngine
    import yaml

    with open("config/policy.yaml") as f:
        pcfg = yaml.safe_load(f)
    with open("config/margin.yaml") as f:
        mcfg = yaml.safe_load(f)

    gate = PolicyGate(pcfg)
    margin = MarginEngine(mcfg)
    gate_action, gate_reason, gate_status, rule_evals = gate.evaluate(case)
    decision = margin.compute_final_decision(
        case=case,
        gate_action=gate_action,
        gate_reason=gate_reason,
        gate_status=gate_status,
        rule_evaluations=rule_evals,
    )

    import time
    t0 = time.perf_counter()
    narrative = await router.generate_narrative(case, decision)
    elapsed_ms = (time.perf_counter() - t0) * 1000

    print(f"MODE       : {narrative.mode}")
    print(f"PROVIDER   : {narrative.llm_provider}")
    print(f"LATENCY_MS : {elapsed_ms:.1f}")
    print(f"TOKENS_OUT : {narrative.tokens_out}")
    print(f"SUMMARY    : {narrative.summary[:80]}")
    print(f"CB_STATE   : {router.circuit_breaker.state}")
    print(f"CB_FAILURES: {router.circuit_breaker.failure_count}")

    if narrative.mode in ("REPLAY", "TEMPLATE"):
        print("TIER2_RESULT: PASS — correctly fell back off Tier 1")
    else:
        print("TIER2_RESULT: FAIL — unexpected mode:", narrative.mode)


async def test_tier2_force_circuit_open():
    """Trip circuit breaker manually, verify it stays OPEN and routes to Tier 2."""
    print("\n=== CIRCUIT BREAKER OPEN -> REPLAY TEST ===")
    cb = CircuitBreaker(failure_threshold=2, recovery_timeout_seconds=60.0)
    cb.record_failure()
    cb.record_failure()
    print(f"CB_STATE after 2 failures: {cb.state}")

    router = InferenceRouter(
        mode="live",
        vllm_base_url="https://developer.amd.com.cn/radeon/api/v1",
        vllm_model="DeepSeek-V4-Flash",
        api_key="dummy",
        replay_dir=Path("data/replay"),
        circuit_breaker=cb,
    )
    case = _make_case()

    from app.gate import PolicyGate
    from app.margin import MarginEngine
    import yaml

    with open("config/policy.yaml") as f:
        pcfg = yaml.safe_load(f)
    with open("config/margin.yaml") as f:
        mcfg = yaml.safe_load(f)
    gate = PolicyGate(pcfg)
    margin = MarginEngine(mcfg)
    gate_action, gate_reason, gate_status, rule_evals = gate.evaluate(case)
    decision = margin.compute_final_decision(
        case=case,
        gate_action=gate_action,
        gate_reason=gate_reason,
        gate_status=gate_status,
        rule_evaluations=rule_evals,
    )

    narrative = await router.generate_narrative(case, decision)
    print(f"MODE       : {narrative.mode}")
    print(f"PROVIDER   : {narrative.llm_provider}")
    print(f"CB_STATE   : {router.circuit_breaker.state}")

    if narrative.mode in ("REPLAY", "TEMPLATE"):
        print("CIRCUIT_BREAKER_BYPASS: PASS — Tier 1 skipped correctly")
    else:
        print("CIRCUIT_BREAKER_BYPASS: FAIL — went to Tier 1 despite OPEN breaker")


asyncio.run(test_tier2_replay())
asyncio.run(test_tier2_force_circuit_open())
