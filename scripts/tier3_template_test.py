"""Tier 3 TEMPLATE offline test — cache-miss + LLM down → deterministic synthesizer."""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.router import InferenceRouter
from app.schemas import DisputeCase, CourierEvent


def _make_case_no_replay():
    """Use a case ID that has no replay file, guaranteeing a cache miss."""
    return DisputeCase(
        case_id="CASE-OFFLN-999",
        order_id="ORD-OFFLINE-999",
        order_amount=75.00,
        unit_margin=12.00,
        dispute_fee=8.00,
        claim_date="2026-10-12",
        delivery_date="2026-10-01",
        return_window_days=14,
        claimed_reason="item_not_received",
        complaint_text="Package never showed up.",
        courier_events=[
            CourierEvent(
                timestamp="2026-10-01T10:00:00",
                status="DELIVERED",
                note="Left at door",
                geo_match=False,
                signature_present=False,
            )
        ],
    )


async def test_tier3_template():
    """With mode=template and a case ID with no replay file → must produce TEMPLATE."""
    print("=== TIER 3 TEMPLATE OFFLINE TEST ===")
    print("Simulating: LLM fully down (mode=template) + cache miss (unknown case ID)")

    router = InferenceRouter(
        mode="template",  # Force template — simulates full offline
        vllm_base_url="http://127.0.0.1:9999/v1",  # unreachable
        vllm_model="template-synthesizer",
        api_key=None,
        replay_dir=Path("data/replay"),
    )

    case = _make_case_no_replay()

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

    print(f"MODE         : {narrative.mode}")
    print(f"PROVIDER     : {narrative.llm_provider}")
    print(f"MODEL        : {narrative.model}")
    print(f"LATENCY_MS   : {elapsed_ms:.2f}")
    print(f"TOKENS_OUT   : {narrative.tokens_out}")
    print(f"CLAIMS       : {len(narrative.claims)} cited claims")
    print(f"CITATIONS_OK : {narrative.verified_citations}")
    print(f"SUMMARY      : {narrative.summary[:80]}")
    print(f"DRAFT_REPLY  : {narrative.draft_reply[:120]}...")

    # Validate fact citations are grounded (no hallucinated IDs)
    from app.narrator import FactCitationValidator
    facts = FactCitationValidator.extract_ground_truth_facts(case, decision)
    valid_keys = set(facts.keys())
    all_cited_valid = all(
        fid in valid_keys for claim in narrative.claims for fid in claim.fact_ids
    )
    print(f"ALL_CITATIONS_GROUNDED: {all_cited_valid}")

    if narrative.mode == "TEMPLATE" and narrative.llm_provider == "deterministic_template" and all_cited_valid:
        print("TIER3_RESULT: PASS — deterministic template, zero LLM, all citations grounded")
    else:
        print("TIER3_RESULT: FAIL")

asyncio.run(test_tier3_template())
