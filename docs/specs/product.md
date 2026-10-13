# product.md — MerchantGuard (Dispute & Margin Recovery Copilot)

**Event:** AMD Developer Hackathon: ACT III (lablab.ai, online 12–18 Oct 2026)
**Track:** Reinvent Commerce (Track 3 only — Evolus Partner Track is out of scope)
**One-liner:** Stop leaking e-commerce margin on bad dispute decisions: deterministic policy guardrails + a statistical margin model decide; an open LLM on AMD infrastructure only writes the evidence narrative.

## 1. Problem
E-commerce ops teams handle returns, "item not received" claims and chargebacks by hand. Two costly errors: (a) refunding disputes that were winnable, (b) fighting disputes where the dispute fee exceeds what can be recovered.

## 2. Target user
E-commerce Ops / CS Lead at a small-to-mid merchant who approves the final response on each case.

## 3. Scope
**In scope (MVP)**
- Case intake (API + sample loader) for 4 dispute types: item-not-received, return-window claim, damaged item, unauthorized-charge claim.
- Deterministic Policy Gate (window, delivery proof, signature/geo flags, PII scrub).
- Margin model: P(win), cost of dispute vs refund, recommended action.
- LLM narrator: cited evidence paragraph + draft response (via AMD Token Factory gateway, model DeepSeek-V4-Flash).
- Human approve/edit/reject UI with audit log.
- Synthetic dataset generator and replay mode.

**Out of scope** — real payment-processor integrations, real customer data, multi-tenant auth, model training/fine-tuning, mobile UI, Evolus partner integration.

## 4. Inputs
| Input | Fields |
|---|---|
| Order | order_id, order_date, items, amount, unit_margin, fulfillment_status |
| Courier log | events[] (timestamp, status, note), delivery_proof (photo/signature flags, geo match) |
| Complaint | free text, claimed reason code, claim_date |
| Store policy | return_window_days, accepted proofs, dispute_fee, fee_refundable_on_win |

## 5. Outputs
1. **Policy Gate status:** `IN_POLICY` | `EXPIRED_WINDOW` | `DELIVERY_CONFIRMED` | `NEEDS_HUMAN` (with reason code).
2. **Margin metric:** P(win), expected loss per option, expected margin recovery, recommended action `CONTEST` | `PARTIAL_REFUND` | `ACCEPT_REFUND`.
3. **Evidence narrative:** one paragraph, every claim cited to a fact ID, plus draft reply to bank/buyer.
4. **Audit record:** inputs hash, decision, mode (LIVE/REPLAY/TEMPLATE), reviewer action, timestamp.

## 6. Demo scenarios (must all work)
1. Clean win — delivered with signature 3 days ago, buyer claims non-receipt → CONTEST.
2. Ambiguous evidence — "Delivered" but courier note says left unattended, high value → NEEDS_HUMAN (AMBIGUOUS_EVIDENCE).
3. Window bypass — return requested day 35, policy 14 days → auto-reject by rules, no LLM call for the decision.
4. Economic trap — dispute fee exceeds recoverable margin → ACCEPT_REFUND.

## 7. Success metrics (for the pitch)
- Total Recovered Margin counter across the synthetic case set vs a "refund everything" baseline.
- Decision-time per case (target: seconds, measured and logged).
- 100% of decisions reproducible from the audit log.
- Inference latency / tokens-per-second measured via AMD Token Factory gateway (client-side benchmark).

## 8. Honesty constraints (do not violate in demo or README)
- P(win) is trained on **synthetic** data. Label it "illustrative / synthetic-calibrated" in the UI and README. Never present it as real-world accuracy.
- Replay mode must show a visible REPLAY banner. It is a resilience fallback, not the live path.
- All dollar figures in the demo are illustrative.

## 9. Judging criteria mapping (from the kickoff livestream slides, relayed by Oky; verify against the lablab page)
| Criterion | How MerchantGuard answers it | Where to show it |
|---|---|---|
| Application of Technology | Open model (DeepSeek-V4-Flash) via AMD Token Factory gateway, statistical margin model, schema/citation validator, degradation ladder | architecture slide, Token Factory portal screenshot + latency benchmark, engine status indicator |
| Business Value | Measured recovered margin vs a "refund everything" baseline (synthetic, labeled), decision time per case | metrics strip, final video segment |
| Originality | Decision/narration split (LLM cannot decide), economic-trap case, visible fault tolerance | scenarios 2 and 4, kill-the-endpoint moment |
| Presentation | Four scripted scenarios in about 4 minutes | video_script.md |

**Track 3 participant note:** because MerchantGuard predicts P(win), the README must explain how it is calculated (features, model, training data, how it is combined with the rules) and state that the LLM is not the forecasting method.

**Vibe Generation special prize (optional):** keep `docs/ai-workflow.md` logging how AI tools were used during the build (spec-first, evidence-backed tasks).
