# Day 2 Evidence: Degradation Ladder Router, Circuit Breaker & Cloud Budget

> **Project:** MerchantGuard (Dispute & Margin Recovery Copilot)  
> **Event:** AMD Developer Hackathon: ACT III — Track: Reinvent Commerce  
> **Milestone:** Tasks T2.4 & T2.6 Verification  
> **Date:** October 13, 2026

---

## 1. Task T2.4: Multi-Tier Resilient Inference Router Architecture

Implemented in `app/router.py`:

```text
Incoming Inference Request (Case + Decision)
                    │
                    ▼
     [ Circuit Breaker Closed? ]
        │                  │
       YES                 NO (OPEN / >2 errors)
        │                  │
        ▼                  │
┌───────────────────────┐  │
│ Tier 1: AMD ROCm vLLM │  │
│  Timeout: 8.0s        │  │
└───────────────────────┘  │
        │                  │
     Success?              │
     ├── YES ──────────────┼──────────► Mode: LIVE (amd_rocm_vllm)
     └── NO / Timeout ─────┘
                    │
                    ▼
┌─────────────────────────────────┐
│ Tier 2: Pre-cached Replay Cache │
│  Lookup: data/replay/           │
└─────────────────────────────────┘
        │
     Found?
     ├── YES ─────────────────────────► Mode: REPLAY (replay_cache_rocm_fallback)
     └── NO
                    │
                    ▼
┌─────────────────────────────────┐
│ Tier 3: Deterministic Template  │
│  Fact Synthesizer (0% LLM)      │
└─────────────────────────────────┘
                    │
                    └─────────────────► Mode: TEMPLATE (deterministic_template)
```

---

## 2. Router Test Execution Results (`pytest tests/test_router.py`)

All 5 test cases verified:
```text
tests/test_router.py::test_live_vllm_happy_path PASSED                   [ 20%]
tests/test_router.py::test_forced_timeout_degrades_to_replay_cache PASSED [ 40%]
tests/test_router.py::test_cache_miss_degrades_to_deterministic_template PASSED [ 60%]
tests/test_router.py::test_circuit_breaker_tripping_and_skipping_tier1 PASSED [ 80%]
tests/test_router.py::test_circuit_breaker_half_open_recovery PASSED     [100%]
```

### Key Verifications:
1. **Live Tier 1:** Mocks AMD vLLM OpenAI-compatible endpoint, returns `mode="LIVE"`, `llm_provider="amd_rocm_vllm"`, and output tokens.
2. **Replay Tier 2:** On network failure/timeout, seamlessly falls back to cached replay payload with `mode="REPLAY"`.
3. **Template Tier 3:** On cache miss, falls back to deterministic template built directly from case facts with `mode="TEMPLATE"`.
4. **Circuit Breaker:** Exactly 2 consecutive network failures trip the breaker from `CLOSED` to `OPEN`. Subsequent requests skip Tier 1 entirely with 0 network calls.
5. **Recovery:** Transitions to `HALF_OPEN` after 60-second recovery timeout and resets upon success.

---

## 3. Task T2.6: Cloud Budget Plan Summary
- Documented in `docs/evidence/budget.md`.
- Total AMD Cloud credit grant: **$100.00 USD**.
- Operating capacity: ~40 to 50 hours on AMD Instinct MI210/MI300X instance (~$1.99 - $2.49/hr).
- Safe active schedule: 4 controlled windows totaling ~12.5 hours (~$28.00 target, leaving 72% reserve buffer).
- Strict shut-down when idle policy enforced.

---

## 4. Full Pytest Suite Run (All 25 Tests Passing)

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\ADMIN\Documents\merchantguard
plugins: anyio-4.15.1, asyncio-1.4.0
collected 25 items

tests/test_audit.py::test_audit_chain_append_and_linkage PASSED          [  4%]
tests/test_audit.py::test_audit_chain_integrity_verification PASSED      [  8%]
tests/test_gate.py::test_rule_r001_return_window_expired_negative PASSED [ 12%]
tests/test_gate.py::test_rule_r001_return_window_valid_positive PASSED   [ 16%]
tests/test_gate.py::test_rule_r002_verified_signature_and_geo_positive PASSED [ 20%]
tests/test_gate.py::test_rule_r002_unverified_carrier_negative PASSED    [ 24%]
tests/test_gate.py::test_rule_r003_courier_contradiction_negative PASSED [ 28%]
tests/test_gate.py::test_rule_r003_courier_consistent_positive PASSED    [ 32%]
tests/test_gate.py::test_rule_r004_high_value_weak_evidence_negative PASSED [ 36%]
tests/test_gate.py::test_rule_r004_high_value_strong_evidence_positive PASSED [ 40%]
tests/test_gate.py::test_rule_r005_economic_fee_trap_negative PASSED     [ 44%]
tests/test_gate.py::test_rule_r005_healthy_margin_positive PASSED        [ 48%]
tests/test_gate.py::test_rule_r006_missing_required_fields_negative PASSED [ 52%]
tests/test_gate.py::test_rule_r006_missing_tracking_events_negative PASSED [ 56%]
tests/test_gate.py::test_rule_partial_damage_routing PASSED              [ 60%]
tests/test_margin.py::test_ev_calculation_positive_recovery PASSED       [ 64%]
tests/test_margin.py::test_negative_ev_override_to_accept_refund PASSED  [ 68%]
tests/test_margin.py::test_partial_refund_settlement_offer PASSED        [ 72%]
tests/test_margin.py::test_ambiguous_middle_tier_routes_to_partial_refund PASSED [ 76%]
tests/test_margin.py::test_model_artifact_loaded_successfully PASSED     [ 80%]
tests/test_router.py::test_live_vllm_happy_path PASSED                   [ 84%]
tests/test_router.py::test_forced_timeout_degrades_to_replay_cache PASSED [ 88%]
tests/test_router.py::test_cache_miss_degrades_to_deterministic_template PASSED [ 92%]
tests/test_router.py::test_circuit_breaker_tripping_and_skipping_tier1 PASSED [ 96%]
tests/test_router.py::test_circuit_breaker_half_open_recovery PASSED     [100%]

============================= 25 passed in 2.21s ==============================
```
