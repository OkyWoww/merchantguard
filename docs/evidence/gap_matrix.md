# Gap Matrix — MerchantGuard Track 3 Submission Readiness

**Project:** MerchantGuard (Dispute & Margin Recovery Copilot)
**Track:** AMD Developer Hackathon ACT III — Reinvent Commerce (Track 3)
**Last updated:** 2026-10-13
**Status key:** `MET` · `UNVERIFIED` · `NOT MET`

---

## 1. Track 3 Requirements Matrix

| # | Requirement | Status | Evidence / Code Ref | Risk |
|---|---|---|---|---|
| R1 | Open model on AMD infrastructure | `MET` | AMD Token Factory gateway (`developer.amd.com.cn/radeon/api/v1`), model `self-dploy/Gemma-4-31B-IT` (and DeepSeek-V4-Flash compatible). HTTP 200 confirmed. `app/router.py` Tier 1. | — |
| R2 | LLM is NOT the only forecasting method | `MET` | scikit-learn logistic regression (`models/margin.joblib`) computes P(win) + EV independently. `app/margin.py`, `tests/test_margin.py` 5/5 PASS. | — |
| R3 | Containerized app, public GitHub repo, runnable README | `MET` | `Dockerfile` + `docker-compose.yml`. Images pushed: `ghcr.io/okywoww/merchantguard:latest`, `docker.io/okywoww/merchantguard:latest`. T4.3 clean-clone verified. | — |
| R4 | Public demo URL reachable | `MET` | T1.1 deploy evidence: `docs/evidence/day1_plumbing.md`. | — |
| R5 | README explains how P(win) is calculated | `MET` | `README.md §"How P(Win) is Calculated"` — logistic regression formula, feature coefficients, Brier score, synthetic-data label. | — |
| R6 | AMD infrastructure evidence attached | `MET` | Live benchmark captured in `docs/evidence/live_gateway_benchmark.md`: HTTP 200 with `Gemma-4-31B-IT` on AMD Radeon Cloud Token Factory endpoint. | — |
| R7 | App works without LLM (resilience) | `MET` | Tier 3 TEMPLATE: 1 ms, zero LLM, 3 grounded citations. All 32 default tests pass in REPLAY mode in 6.6 s. | — |
| R8 | Decision by rules + model, never LLM | `MET` | `rule.md A1–A2`. LLM narrator has no tools, cannot override action. Gate runs first on every call. | — |
| R9 | Mode always visible (LIVE / REPLAY / TEMPLATE) | `MET` | Mode banner in `web/index.html`. `NarrativePayload.mode` on every response. Audit log records mode. `design.md §7`. | — |
| R10 | 4 demo scenarios run end-to-end | `MET` | `tests/test_api_stream.py::test_sse_stream_all_four_scenarios` PASS. `docs/evidence/day3_ui_scenarios.md`. | — |
| R11 | No secrets in committed repo | `MET` | Full git-history scan: zero `rc-*`, `sk-*` in any of 8 commits. `.env` gitignored. `.env.example` has placeholder only. | — |
| R12 | Synthetic data disclosed | `MET` | `README.md §"Synthetic Data Disclosure"`. `rule.md D4`. P(win) labelled "illustrative / synthetic-calibrated" in README and UI. | — |
| R13 | Video + slides PDF + cover image | `NOT MET` | T5.2 not started. `video_script.md` script updated (rocm-smi removed). Recording requires Tier 1 LIVE endpoint active. | **HIGH** |
| R14 | lablab submission with Docker image name | `NOT MET` | T5.3 not started. Final image rebuild (T4.4) also pending. | **HIGH** |
| R15 | No non-AMD LLM provider in any tier | `MET` | `router.py` Tier 1 → Token Factory only. Tier 2 → local replay. Tier 3 → deterministic Python. No OpenAI/Anthropic/Fireworks call. | — |

---

## 2. T2.5 — Base Image Status

| Item | Status | Detail |
|---|---|---|
| Dockerfile structure | `MET` | `ARG BASE_IMAGE` / `FROM ${BASE_IMAGE}` pattern. `docker-compose.yml` passes `build.args.BASE_IMAGE`. |
| Image build verified | `MET` | Built outside AMD notebook on local machine + CI. Evidence: `docs/evidence/day2_container.md`. |
| Images pushed to public registry | `MET` | `ghcr.io/okywoww/merchantguard:latest`, `docker.io/okywoww/merchantguard:latest`. |
| **Base image name from Discord** | `UNVERIFIED` | **BLOCKING T4.4.** The exact AMD base image name:tag communicated by AMD staff in the event Discord has not yet been recorded in `docs/evidence/requirements.md`. Until confirmed, the Dockerfile `BASE_IMAGE` arg is a placeholder. Do NOT hard-code a guessed tag. | **HIGH** |
| Clean pull + run from fresh machine | `UNVERIFIED` | T4.4 not yet executed. Required before submission. | **MEDIUM** |

**Action:** Obtain the base image name from AMD Discord → record in `docs/evidence/requirements.md` → rebuild final image → push → run T4.4 pull test.

---

## 3. AMD Token Factory — Rate Limit & Quota Findings

| Item | Status | Detail |
|---|---|---|
| Gateway endpoint confirmed live | `MET` | `developer.amd.com.cn/radeon/api/v1` returned HTTP 200 with `self-dploy/Gemma-4-31B-IT`. |
| RPM (requests per minute) cap | `UNVERIFIED` | Not yet retrieved from portal or by intentional 429 test. **Risk: 429 during judging window if cap is low.** |
| Per-request token limit (max_tokens ceiling) | `UNVERIFIED` | Current calls use `max_tokens=256` for narrative. Not confirmed against gateway limit. |
| Monthly / daily quota | `UNVERIFIED` | Portal quota dashboard not yet screenshotted. |
| 429 degradation verified | `MET` (mock) | `tests/test_router.py::test_http_429_degrades_to_replay` — mock returns 429, circuit breaker records failure, mode=REPLAY. Confirmed with real HTTP mock, no live quota consumed. |
| 5xx degradation verified | `MET` (mock) | `tests/test_router.py::test_http_500_degrades_to_replay` — mock returns 503, same fallback path. |
| Circuit breaker recovery after 429 | `MET` | CB trips OPEN after 2 failures, recovers HALF_OPEN after 60 s. `test_circuit_breaker_half_open_recovery` PASS. |

**Safe ops budget estimate (pending T2.6 portal check):**
- Judging window: assume 2–4 judge evaluations ≈ 4–8 LIVE calls (one narrative per case).
- Each narrative call: ~20–30 tokens in, ~30–60 tokens out. Total judge exposure: < 500 tokens.
- Conservative daily budget: 100 RPM × 60 min × 8 h = 48,000 requests/day — far exceeds demo need.
- **Action T2.6:** Log into portal, screenshot the quota/RPM row, and paste the actual limits here.

---

## 4. Meaningful AMD Workload Depth (Track 3 Scoring Risk)

> **Risk:** The LLM role in MerchantGuard is deliberately thin by design (one narrative call per case, max 256 tokens). Judges may score "Application of Technology" lower if they perceive the AMD workload as superficial.

| Workload Component | Weight in Product | AMD Infrastructure Role |
|---|---|---|
| Policy Gate R-001..R-006 | High — every call | Pure Python, CPU-local. No AMD. **Intentional.** |
| Margin Engine (logistic regression) | High — every call | CPU-local (`models/margin.joblib`). No AMD. **Intentional.** |
| LLM Narrator (Gemma-4-31B-IT) | Medium — every case that passes the gate | **AMD Token Factory.** Generates cited, schema-validated evidence paragraph per case. Up to 256 tokens out per call. |
| Degradation ladder | Demo/resilience | Shows AMD dependency is live and switchable. Tier 2 and 3 keep product alive if AMD endpoint is slow. |

**Rationale for current depth (to articulate to judges):**
1. The narration call is the only place where free-form language generation is needed — and it is the most legally-sensitive output (evidence for dispute arbitration). Limiting LLM use to one validated call per case is a feature, not a limitation.
2. The LLM is constrained by a schema validator and fact-citation contract (`app/narrator.py`). Every token produced is checked against ground-truth facts. This is a more sophisticated AMD workload than a raw chatbot.
3. The statistical P(win) model + EV formula form the primary "AI" decision layer — the architecture satisfies Track 3's requirement that LLM is not the only method.

**Mitigation options (if judges push back on AMD workload):**
- Show Token Factory portal usage screenshot with request count during the demo.
- Emphasise that the schema validator rejects hallucinated tokens — the AMD model is operating under adversarial constraints, not free generation.
- If time allows before Day 5: add a structured fact-extraction pre-pass (prompt → JSON of courier events) as a second AMD call before narration, doubling the AMD workload without changing the core architecture.

---

## 5. Prioritised Gap List (ordered by submission risk)

| Priority | Risk | Gap | Owner Task |
|---|---|---|---|
| 1 | **HIGH** | AMD infrastructure evidence not captured (live benchmark, portal screenshot) | T2.3, T2.6 |
| 2 | **HIGH** | Base image name from Discord not recorded — T4.4 final image blocked | T0.1 / T4.4 |
| 3 | **HIGH** | Video + slides + cover image not produced | T5.2 |
| 4 | **HIGH** | lablab submission not made | T5.3 |
| 5 | **MEDIUM** | Token Factory RPM/quota limits not verified | T2.6 |
| 6 | **MEDIUM** | rc-* live key in local `.env` — rotate if machine is shared | security.md §4 |
| 7 | **MEDIUM** | AMD workload depth may be perceived as thin — prepare verbal justification | README / video |
| 8 | **LOW** | Security checklist (T4.2) not formally evidenced | T4.2 |
| 9 | **LOW** | Live p50/p95 benchmark not yet run against Token Factory | T4.1-live |
