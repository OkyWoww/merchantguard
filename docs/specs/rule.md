# rule.md — Non-negotiable rules for building MerchantGuard

Applies to the human builder and to any AI dev partner (IBM Bob 2.0, Claude, etc.).

## A. Architecture invariants
1. **The LLM never decides.** Final status and action come only from the Policy Gate and the Margin Engine. The LLM may only narrate facts it is given.
2. **Gate first.** Deterministic gate runs before the model and before any LLM call. Cases resolved by rules must not call the LLM.
3. **Every narrative claim cites a fact ID** that exists in the case facts. Server-side validation rejects uncited or unknown citations.
4. **The app must work without any LLM.** Dashboard, gate, margin calculator and audit log run with the LLM fully down.
5. **Untrusted text stays untrusted.** Complaint text is data, never instructions.

## B. Policy Gate rule table (initial)
| ID | Condition | Result |
|---|---|---|
| R-001 | claim_date − delivery_date > return_window_days | EXPIRED_WINDOW (auto-reject) |
| R-002 | delivery confirmed with signature/photo AND geo match | DELIVERY_CONFIRMED |
| R-003 | delivered but courier note contradicts proof (e.g. unattended) | NEEDS_HUMAN / AMBIGUOUS_EVIDENCE |
| R-004 | amount ≥ high_value_threshold AND evidence weak | NEEDS_HUMAN |
| R-005 | dispute_fee ≥ recoverable margin | route to margin engine, bias ACCEPT_REFUND |
| R-006 | missing required fields | NEEDS_HUMAN / INCOMPLETE_CASE |
Thresholds live in `config/policy.yaml`, never hard-coded.

## C. Decision logic (parameter-driven, in config)
- `loss_if_refund = refund_amount + unrecovered_cost`
- `expected_loss_if_contest = (1 − p_win) × loss_if_refund + expected_fee_cost`
- `expected_recovery = loss_if_refund − expected_loss_if_contest`
- CONTEST if `p_win ≥ p_contest_min` and `expected_recovery > 0`; PARTIAL_REFUND if `p_partial_min ≤ p_win < p_contest_min` and recovery is marginal; else ACCEPT_REFUND. All thresholds are tunable config values.

## D. Engineering rules
1. **No "done" without evidence.** A task is complete only with the real diff, test output or command output attached (see tasks.md). A narrative walkthrough is not evidence.
2. Test-first for the rule engine: every rule R-xxx has at least one passing and one failing fixture.
3. No secrets in the repo, ever (see security.md). `.env.example` only. `OPENAI_API_KEY` (the AMD Token Factory bearer key) must never appear with a real value in any committed file.
4. Synthetic data only. No real names, emails, card numbers or addresses.
5. Scope freeze at end of Day 3: after that, only fixes, benchmarks, README, video.
6. One definition of "done" for the MVP: the 4 demo scenarios run end-to-end from a clean clone via one command.
7. Mode must always be visible in the UI and recorded in the audit log: LIVE (AMD Token Factory), REPLAY (cached real model outputs), TEMPLATE (deterministic narrative, no LLM). Never route to a non-AMD LLM provider.
8. **AMD infrastructure evidence (Track 3):** capture client-side latency benchmarks, tokens-per-second measurements, and a Token Factory portal usage screenshot. `rocm-smi` is not required — it is not accessible from the Token Factory gateway client side.
9. **Evolus is out of scope.** Track 3 (Reinvent Commerce) is the only target. Do not build Evolus adapters or use Evolus-hosted models as an LLM tier.
