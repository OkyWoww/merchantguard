# Day 3 Evidence: UI Dashboard, SSE Stream & 4 Demo Scenarios

**Project:** MerchantGuard (Dispute & Margin Recovery Copilot)  
**Track:** AMD Developer Hackathon: ACT III — Track: Reinvent Commerce  
**Tasks:** T3.1 (SSE Stream Endpoint), T3.2 (4 Interactive Demo Scenarios), T3.3 (Frontend Dashboard), T3.4 (Replay Cache Verification)  
**Date:** 2026-10-13  
**Status:** COMPLETE & VERIFIED (30/30 Pytest Passing)

---

## 1. Executive Summary

Day 3 establishes the complete end-to-end user-facing surface and live execution telemetry for **MerchantGuard**:
1. **Robust SSE Streaming Pipeline (T3.1):** Sequential 4-stage telemetry (`POLICY_GATE` → `MARGIN_ENGINE` → `NARRATION` → `AUDIT_CHAIN` → `COMPLETE`) with standard `data: {"stage": "...", "payload": {...}}\n\n` packaging exposed at both `GET /cases/{case_id}/stream` and `POST /cases/evaluate/stream`.
2. **Interactive 4 Demo Scenarios (T3.2):** Pre-configured, 1-click executable demo cases matching `docs/specs/product_3.md` and `docs/specs/video_script_3.md` across `data/scenarios/`, `data/samples/`, and `GET /scenarios`.
3. **Refined Merchant Copilot Dashboard (T3.3):** Modern dark-mode interface in `web/index.html` and `web/app.js` featuring real-time stage progress steppers, glowing decision badges, financial margin recovery analytics, ground-truth citation chips, and cryptographic ledger inspectors.
4. **Replay Cache & Zero-Cost Offline Reliability (T3.4):** 100% test pass rate with `LLM_MODE=replay`, guaranteeing offline-safe operation and instant demo execution.

---

## 2. Server-Sent Events (SSE) Stream Architecture (T3.1)

### 2.1 Sequential Execution Stages
The SSE stream emits 5 events sequentially with artificial non-blocking pacing (`asyncio.sleep`) to produce a smooth streaming telemetry feel on the UI:

| Stage # | SSE Event Name | Standard JSON Payload Shape | Description |
|---|---|---|---|
| **1** | `POLICY_GATE` | `{"stage": "POLICY_GATE", "payload": {"action": ..., "reason": ..., "status": ..., "rules": [...]}}` | Deterministic evaluation of rules R-001 through R-006 |
| **2** | `MARGIN_ENGINE` | `{"stage": "MARGIN_ENGINE", "payload": {"p_win": ..., "expected_margin_recovery": ..., "action": ...}}` | Statistical $P(\text{Win})$ model and EV margin formula |
| **3** | `NARRATION` | `{"stage": "NARRATION", "payload": {"summary": ..., "claims": [...], "draft_reply": ..., "mode": ...}}` | Fact-cited dispute draft from vLLM, Replay, or Template synthesizer |
| **4** | `AUDIT_CHAIN` | `{"stage": "AUDIT_CHAIN", "payload": {"block": {...}, "integrity_valid": true, "chain_head_hash": ...}}` | Chained SHA-256 block creation linked to genesis block |
| **5** | `COMPLETE` | `{"stage": "COMPLETE", "payload": {"status": "completed", "case_id": ...}}` | Stream termination signal |

### 2.2 Wire Format Example (`GET /cases/CASE-1001/stream`)
```http
HTTP/1.1 200 OK
Content-Type: text/event-stream; charset=utf-8
Cache-Control: no-cache
Connection: keep-alive

event: POLICY_GATE
data: {"stage": "POLICY_GATE", "payload": {"case_id": "CASE-1001", "action": "CONTEST", "reason": "R002_DELIVERY_CONFIRMED", "status": "GATE_APPROVED", "rules": [...]}}

event: MARGIN_ENGINE
data: {"stage": "MARGIN_ENGINE", "payload": {"case_id": "CASE-1001", "action": "CONTEST", "p_win": 0.98, "expected_margin_recovery": 226.57, "reason_code": "R002_DELIVERY_CONFIRMED"}}

event: NARRATION
data: {"stage": "NARRATION", "payload": {"case_id": "CASE-1001", "summary": "Carrier GPS coordinates and physical signature verify legitimate doorstep handover on 2026-10-02.", "claims": [...], "draft_reply": "Dear Dispute Arbitration Team...", "mode": "REPLAY"}}

event: AUDIT_CHAIN
data: {"stage": "AUDIT_CHAIN", "payload": {"block": {"index": 1, "case_id": "CASE-1001", "action": "CONTEST", "block_hash": "f3a8b9409..."}, "integrity_valid": true, "total_blocks": 2}}

event: COMPLETE
data: {"stage": "COMPLETE", "payload": {"status": "completed", "case_id": "CASE-1001", "action": "CONTEST"}}
```

---

## 3. Four Core Demo Scenarios Verification (T3.2)

All 4 demo scenarios are defined in `data/scenarios/` and `data/samples/`, and verified on the live server:

| Scenario | Case ID | Order / Margin / Fee | Key Carrier Fact | Rule Triggered | Action Output | EV Outcome |
|---|---|---|---|---|---|---|
| **Scenario 1: Clean Win** | `CASE-1001` | $185.00 / $62.00 / $15.00 | Signed by resident M. Vance + Geo Match | `R-002` (Delivery Confirmed) | `CONTEST` | **+$226.57** ($P(\text{Win})=98\%$) |
| **Scenario 2: Ambiguous Evidence** | `CASE-1002` | $420.00 / $140.00 / $15.00 | "Package left by fence / unattended" | `R-003` (Ambiguous Evidence) | `NEEDS_HUMAN` | Escalated to Adjuster ($P(\text{Win})=5\%$) |
| **Scenario 3: Window Bypass** | `CASE-1003` | $130.00 / $45.00 / $15.00 | Claim filed 21 days post-delivery (limit 14) | `R-001` (Window Expired) | `CONTEST` | Instant ($0$ LLM tokens spent) |
| **Scenario 4: Economic Fee Trap** | `CASE-1004` | $16.50 / $3.80 / $15.00 | Dispute fee ($15) > Unit margin ($3.80) | `R-005` (Economic Fee Trap) | `ACCEPT_REFUND` | Auto-Refund (Prevent Net Loss) |

### 3.1 Live Terminal Evaluation Output
```
--- 2. Core Scenarios Endpoint ---
Total scenarios: 4
  scenario_1: Scenario 1: Clean Win -> CONTEST [R-002]
  scenario_2: Scenario 2: Ambiguous Evidence -> NEEDS_HUMAN [R-003]
  scenario_3: Scenario 3: Window Bypass -> CONTEST [R-001]
  scenario_4: Scenario 4: Economic Fee Trap -> ACCEPT_REFUND [R-005]

--- 3. SSE Stream Case 1001 (Clean Win - R-002) ---
Stream bytes received: 9243
Events emitted: ['event: POLICY_GATE', 'event: gate_evaluated', 'event: MARGIN_ENGINE', 'event: margin_computed', 'event: NARRATION', 'event: narrative_generated', 'event: AUDIT_CHAIN', 'event: audit_committed', 'event: COMPLETE', 'event: complete']

--- 4. SSE Stream Case 1002 (Ambiguous Evidence - R-003) ---
Verified: Case 1002 -> NEEDS_HUMAN (R003_AMBIGUOUS_EVIDENCE)

--- 5. SSE Stream Case 1003 (Window Bypass - R-001) ---
Verified: Case 1003 -> CONTEST (R001_WINDOW_EXPIRED)

--- 6. SSE Stream Case 1004 (Economic Fee Trap - R-005) ---
Verified: Case 1004 -> ACCEPT_REFUND (R005_ECONOMIC_FEE_TRAP)

--- 7. Cryptographic Audit Verification ---
AUDIT VERIFY: {'valid': True, 'total_blocks': 60, 'message': 'All 60 blocks cryptographically verified. Zero tampering detected.', 'corrupted_index': None}
```

---

## 4. Frontend Dashboard Integration (T3.3)

### 4.1 UI Component Architecture
The single-screen dashboard (`web/index.html` + `web/app.js`) is constructed using semantic HTML5, modern Tailwind utilities, and Google Fonts (`Plus Jakarta Sans` + `JetBrains Mono`):

1. **Header & Status Strip:**
   - Active Inference Tier Pill: `REPLAY (Zero-Cost / Offline)` | `AMD ROCm vLLM (LIVE)` | `TEMPLATE`
   - AMD Cloud Credit Badge: `$100 Active (~38.5h GPU)`
   - Track 3 Disclosure: *"Win probability P(win) modeled via calibrated Logistic Regression. LLM acts strictly as factual evidence synthesizer."*
   - Ledger Status Button: *"Verify Ledger"*
2. **1-Click Demo Scenario Selector:**
   - 4 prominent, responsive cards for each hackathon scenario with direct `onclick="triggerScenario(id, num)"` bindings.
3. **SSE Telemetry Progress Stepper:**
   - 4 sequential indicator boxes: `1. POLICY GATE` → `2. MARGIN ENGINE` → `3. FACT NARRATION` → `4. AUDIT CHAIN`.
   - Real-time animated pulsing when active, glowing green `DONE ✓` upon stage resolution.
4. **Dispute Queue & Evidence Compare Panel:**
   - Buyer dispute claim (reason, complaint statement, amount).
   - Carrier telematic trail (timestamps, notes, GPS geo-match badge, signature presence badge).
   - Dynamic conflict badge: `Verified Consistent ✓` or `Carrier Ambiguity Detected ⚠️`.
5. **Decision Banner & Financial Margin Recovery Breakdown:**
   - High-contrast decision badge: `CONTEST` (emerald glow), `NEEDS_HUMAN` (amber glow), `ACCEPT_REFUND` (rose glow).
   - Financial breakdown grid: Loss if Refunded, Win Probability $P(\text{Win})$ with visual bar, Dispute Fee Risk, Net Expected Recovery ($EV$).
   - Interactive formula breakdown drawer displaying exact numeric substitution.
6. **Fact-Cited Arbitration Narrative Box:**
   - Ground-truth citation chips: `[F1: ORD-88219]`, `[F2: Signed 'M. Vance']`, `[F3: Geo-Match ✓]`.
   - Full processor defense draft with a 1-click *"Copy Response"* clipboard button.
7. **Cryptographic Audit Chain Inspector:**
   - Current block index (`#1`), SHA-256 block hash, parent hash (linked to genesis block).
   - Interactive modal displaying hash integrity verification status (`VALID - UNBROKEN`).

---

## 5. Test Suite Verification (`pytest tests/`)

Running `pytest -v tests/` confirms 30 passing unit and integration tests with zero regression:

```
tests/test_api_stream.py::test_health_check PASSED                       [  3%]
tests/test_api_stream.py::test_list_scenarios PASSED                     [  6%]
tests/test_api_stream.py::test_sse_stream_case_1001 PASSED               [ 10%]
tests/test_api_stream.py::test_sse_stream_all_four_scenarios PASSED      [ 13%]
tests/test_api_stream.py::test_post_case_evaluate_stream PASSED          [ 16%]
tests/test_audit.py::test_audit_chain_append_and_linkage PASSED          [ 20%]
tests/test_audit.py::test_audit_chain_integrity_verification PASSED      [ 23%]
tests/test_gate.py::test_rule_r001_return_window_expired_negative PASSED [ 26%]
tests/test_gate.py::test_rule_r001_return_window_valid_positive PASSED   [ 30%]
tests/test_gate.py::test_rule_r002_verified_signature_and_geo_positive PASSED [ 33%]
tests/test_gate.py::test_rule_r002_unverified_carrier_negative PASSED    [ 36%]
tests/test_gate.py::test_rule_r003_courier_contradiction_negative PASSED [ 40%]
tests/test_gate.py::test_rule_r003_courier_consistent_positive PASSED    [ 43%]
tests/test_gate.py::test_rule_r004_high_value_weak_evidence_negative PASSED [ 46%]
tests/test_gate.py::test_rule_r004_high_value_strong_evidence_positive PASSED [ 50%]
tests/test_gate.py::test_rule_r005_economic_fee_trap_negative PASSED     [ 53%]
tests/test_gate.py::test_rule_r005_healthy_margin_positive PASSED        [ 56%]
tests/test_gate.py::test_rule_r006_missing_required_fields_negative PASSED [ 60%]
tests/test_gate.py::test_rule_r006_missing_tracking_events_negative PASSED [ 63%]
tests/test_gate.py::test_rule_partial_damage_routing PASSED              [ 66%]
tests/test_margin.py::test_ev_calculation_positive_recovery PASSED       [ 70%]
tests/test_margin.py::test_negative_ev_override_to_accept_refund PASSED  [ 73%]
tests/test_margin.py::test_partial_refund_settlement_offer PASSED        [ 76%]
tests/test_margin.py::test_ambiguous_middle_tier_routes_to_partial_refund PASSED [ 80%]
tests/test_margin.py::test_model_artifact_loaded_successfully PASSED     [ 83%]
tests/test_router.py::test_live_vllm_happy_path PASSED                   [ 86%]
tests/test_router.py::test_forced_timeout_degrades_to_replay_cache PASSED [ 90%]
tests/test_router.py::test_cache_miss_degrades_to_deterministic_template PASSED [ 93%]
tests/test_router.py::test_circuit_breaker_tripping_and_skipping_tier1 PASSED [ 96%]
tests/test_router.py::test_circuit_breaker_half_open_recovery PASSED     [100%]

======================== 30 passed in 7.43s =========================
```
