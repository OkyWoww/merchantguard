# Day 2 Evidence: Margin Model Training & Decision Engine Wiring

> **Project:** MerchantGuard (Dispute & Margin Recovery Copilot)  
> **Event:** AMD Developer Hackathon: ACT III — Track: Reinvent Commerce  
> **Date:** October 13, 2026  
> **Milestone:** Tasks T2.1 & T2.2 Completed

---

## 1. Task T2.1: Model Training & Calibrated Artifact

### 1.1 Training Pipeline Overview
- **Synthetic Data Generator:** `data/generator.py` generated $N=500$ dispute profiles with a fixed random seed (`seed=42`).
- **Features Extracted:**
  1. `delivery_days_gap`: Elapsed days between delivery and dispute claim
  2. `has_signature`: Recipient physical signature present (0 or 1)
  3. `geo_distance_meters`: Courier GPS coordinate distance from delivery destination (meters)
  4. `buyer_history_score`: Account trust & historical dispute ratio ($[0.0, 1.0]$)
  5. `dispute_amount`: Order gross merchandise value (GMV) in USD
  6. `courier_reliability_score`: Carrier historical telematic delivery fidelity ($[0.0, 1.0]$)
- **Classifier:** `scikit-learn` `Pipeline(StandardScaler(), LogisticRegression(C=1.0, random_state=42))`
- **Model Artifact:** Exported to `models/margin.joblib` (Size: **1,821 bytes / 1.78 KB**).
- **Model Card:** Documented in `docs/evidence/margin_model_report.md`.

### 1.2 Evaluation Metrics (20% Holdout Test Set)

| Metric | Score | Note |
|---|---|---|
| **Accuracy** | **97.00%** | High prediction accuracy |
| **ROC-AUC** | **0.9996** | Near-perfect separation of recoverable cases |
| **Log-Loss** | **0.0649** | Very low cross-entropy penalty |
| **Brier Calibration** | **0.0184** | Calibrated probabilities for EV calculus |
| **Artifact Size** | **1,821 bytes** | Lightweight, instant CPU/edge evaluation |

---

## 2. Task T2.2: Statistical Margin Recovery Engine (`app/margin.py`)

### 2.1 Decision Mathematics Implementation (docs/specs/rule.md §C)
Implemented directly in `app/margin.py`:

$$\text{loss\_if\_refund} = \text{refund\_amount} + \text{unrecovered\_cost}$$
$$\text{expected\_loss\_if\_contest} = (1 - P(\text{win})) \times \text{loss\_if\_refund} + \text{expected\_fee\_cost}$$
$$\text{expected\_recovery} = \text{loss\_if\_refund} - \text{expected\_loss\_if\_contest}$$

All thresholds are parameter-driven and loaded from `config/margin.yaml`:
- `p_contest_min`: `0.60`
- `p_partial_min`: `0.35`
- `min_ev_hurdle_usd`: `0.0`
- `marginal_recovery_threshold`: `5.0`
- `partial_refund_fraction`: `0.35`
- `unrecovered_cogs_ratio`: `0.50`

### 2.2 End-to-End Evaluation on the 4 Core Hackathon Scenarios

```text
CASE-1001 -> action: CONTEST        reason: R002_DELIVERY_CONFIRMED  p_win: 0.980  recovery: $226.57
CASE-1002 -> action: NEEDS_HUMAN    reason: R003_AMBIGUOUS_EVIDENCE  p_win: 0.050  recovery: $ 13.00
CASE-1003 -> action: CONTEST        reason: R001_WINDOW_EXPIRED      p_win: 0.920  recovery: $143.70
CASE-1004 -> action: ACCEPT_REFUND  reason: R005_ECONOMIC_FEE_TRAP  p_win: 0.917  recovery: $  5.95
```

---

## 3. Test Suite Verification (`pytest tests/`)

```text
============================= test session starts =============================
platform win32 -- Python 3.11.9, pytest-9.1.1, pluggy-1.6.0
rootdir: C:\Users\ADMIN\Documents\merchantguard
plugins: anyio-4.15.1, asyncio-1.4.0
collected 20 items

tests/test_audit.py::test_audit_chain_append_and_linkage PASSED          [  5%]
tests/test_audit.py::test_audit_chain_integrity_verification PASSED      [ 10%]
tests/test_gate.py::test_rule_r001_return_window_expired_negative PASSED [ 15%]
tests/test_gate.py::test_rule_r001_return_window_valid_positive PASSED   [ 20%]
tests/test_gate.py::test_rule_r002_verified_signature_and_geo_positive PASSED [ 25%]
tests/test_gate.py::test_rule_r002_unverified_carrier_negative PASSED    [ 30%]
tests/test_gate.py::test_rule_r003_courier_contradiction_negative PASSED [ 35%]
tests/test_gate.py::test_rule_r003_courier_consistent_positive PASSED    [ 40%]
tests/test_gate.py::test_rule_r004_high_value_weak_evidence_negative PASSED [ 45%]
tests/test_gate.py::test_rule_r004_high_value_strong_evidence_positive PASSED [ 50%]
tests/test_gate.py::test_rule_r005_economic_fee_trap_negative PASSED     [ 55%]
tests/test_gate.py::test_rule_r005_healthy_margin_positive PASSED        [ 60%]
tests/test_gate.py::test_rule_r006_missing_required_fields_negative PASSED [ 65%]
tests/test_gate.py::test_rule_r006_missing_tracking_events_negative PASSED [ 70%]
tests/test_gate.py::test_rule_partial_damage_routing PASSED              [ 75%]
tests/test_margin.py::test_ev_calculation_positive_recovery PASSED       [ 80%]
tests/test_margin.py::test_negative_ev_override_to_accept_refund PASSED  [ 85%]
tests/test_margin.py::test_partial_refund_settlement_offer PASSED        [ 90%]
tests/test_margin.py::test_ambiguous_middle_tier_routes_to_partial_refund PASSED [ 95%]
tests/test_margin.py::test_model_artifact_loaded_successfully PASSED     [100%]

============================= 20 passed in 1.50s ==============================
```
