# AMD Developer Cloud: $100 Credit Budget Allocation & Scheduling Plan

> **Project:** MerchantGuard (Dispute & Margin Recovery Copilot)  
> **Event:** AMD Developer Hackathon: ACT III — Track: Reinvent Commerce  
> **Milestone:** Task T2.6 Cloud Budget Management  
> **Date:** October 13, 2026

---

## 1. Credit Envelope & Instance Pricing

| Resource | Specification | Hourly Rate (USD) | Max Usable Hours ($100 Cap) |
|---|---|---|---|
| **AMD Developer Cloud Instance** | 1x AMD Instinct™ MI210 / MI300X (vLLM Serving) | ~$1.99 – $2.49 / hr | **40.1 – 50.2 hours** |
| **Total Credit Balance** | AMD AI Developer Program Grant | **$100.00** | — |
| **Planned Operational Target** | Scheduled Windows Only | **~$28.00** (~12.5 hrs) | **72% Reserve Buffer** |

---

## 2. Planned Execution Windows (3-Phase Schedule)

To avoid accidental credit exhaustion, GPU instances are strictly stopped during local development, coding, UI layout, and documentation. The app runs 100% reliably in **REPLAY mode** on CPU during all intermediate tasks.

```
Total $100 Budget
├── [Phase 1: 2.0h] Dev & Smoke-Test ($4.98)
├── [Phase 2: 3.0h] Benchmark & ROCm Telemetry ($7.47)
├── [Phase 3: 2.5h] Demo Recording & Submission ($6.23)
├── [Phase 4: 5.0h] Judge Evaluation Buffer ($12.45)
└── [RESERVE BUFFER: ~$68.87 remaining]
```

### Phase Breakdown

### Phase 1: Environment Provisioning & Smoke-Test (Target: Day 2)
- **Duration:** 2.0 hours
- **Estimated Cost:** $3.98 – $4.98
- **Objectives:**
  1. Boot AMD Cloud instance with ROCm / vLLM runtime.
  2. Deploy `meta-llama/Llama-3.1-8B-Instruct` or `Qwen2.5-7B-Instruct`.
  3. Validate `/v1/models` and `/v1/chat/completions` OpenAI-compatible API response.
  4. Perform initial health check against `app/router.py` in `LLM_MODE=live`.
  5. **Immediate stop instance** upon test completion.

### Phase 2: Telemetry Capture & Latency Benchmarks (Target: Day 4)
- **Duration:** 3.0 hours
- **Estimated Cost:** $5.97 – $7.47
- **Objectives:**
  1. Capture baseline `rocm-smi` GPU compute & VRAM utilization.
  2. Execute benchmark script: p50/p95 latency, tokens/sec, and concurrency.
  3. Capture peak `rocm-smi` load logs during SSE dispute streaming.
  4. Save benchmark logs to `docs/benchmarks/`.
  5. **Immediate stop instance**.

### Phase 3: Video Recording & Final Submission Walkthrough (Target: Day 5)
- **Duration:** 2.5 hours
- **Estimated Cost:** $4.98 – $6.23
- **Objectives:**
  1. Spin up endpoint for high-resolution video capture per `docs/specs/video_script.md`.
  2. Record live side-by-side demonstration (Policy Gate -> ROCm vLLM Narrative -> SSE Stream).
  3. Capture high-fidelity screenshots for submission gallery.
  4. Stop instance.

### Phase 4: Judge Verification Buffer (Target: Day 6 / Evaluation)
- **Duration:** 5.0 hours
- **Estimated Cost:** ~$9.95 – $12.45
- **Objectives:** Keep instance running during live judging / demo evaluation slot.

---

## 3. Strict Operating Invariants & Anti-Waste Policies

1. **Local-First / REPLAY First:**
   All unit tests, UI styling, and gate logic development run locally using `LLM_MODE=replay`. Zero cloud credits are consumed while writing Python or React code.
2. **Hard Stop Policy:**
   Instances MUST be turned off immediately after evidence collection. An alarm timer is set for each active window (max 90 minutes per session).
3. **Graceful Fallback:**
   Even if the instance is stopped, `app/router.py` immediately falls back to Tier 2 (Replay Cache) and Tier 3 (Deterministic Template), ensuring the public demo URL never fails or errors.
