# tasks.md — Task list with required evidence

Rule: tick a box only after attaching the evidence (diff, test output, or command output) in `docs/evidence/`.

## Day 0 — Pre-kickoff (now → 12 Oct)
- [ ] T0.1 Confirm event requirements on the lablab page and Discord (AMD AI Developer Program signup, allowed hosting). Record any AMD base image name/tag from the Discord message in docs/evidence/requirements.md. Re-ask AMD staff, one question per message: (a) is work done before kickoff (repo scaffold, Dockerfile, data generator) allowed? (b) must a project align with one of the four themes to compete for the main prize? *Evidence: screenshot or notes in docs/evidence/requirements.md*
- [ ] T0.2 Create the AMD account, enter the AMD Developer Program, and verify AMD Token Factory access at `developer.amd.com.cn`. Test one chat-completion call against `DeepSeek-V4-Flash`. *Evidence: portal screenshot + sanitized curl/httpx output with HTTP 200 and latency*
- [ ] T0.3 HOLD until the pre-kickoff scaffolding question (T0.1a) is answered; otherwise do after kickoff. Repo skeleton, Dockerfile, .env.example, pre-commit secret scan. *Evidence: `git log`, hook run output*
- [ ] T0.4 HOLD (same condition as T0.3). Synthetic data generator draft. *Evidence: generator run output (row counts, class balance)*

## Day 1 — 12–13 Oct: Plumbing
- [x] T1.1 Deploy empty FE+API to public URL. *Evidence: docs/evidence/day1_plumbing.md*
- [x] T1.2 Pydantic schemas + Policy Gate R-001..R-006 with fixtures. *Evidence: docs/evidence/day1_plumbing.md (`pytest tests/test_gate.py`)*
- [x] T1.3 Audit log with hash chain. *Evidence: docs/evidence/day1_plumbing.md (tests + `GET /audit/verify`)*

## Day 2 — 13–14 Oct: Model & AMD wiring
- [x] T2.1 Train/export margin model; calibration/sanity report. *Evidence: docs/evidence/margin_model_report.md & docs/evidence/day2_margin_engine.md (1,821 bytes joblib)*
- [x] T2.2 Margin engine + action logic from config. *Evidence: docs/evidence/day2_margin_engine.md (`pytest tests/test_margin.py`, 4 scenarios verified)*
- [ ] T2.3 Verify AMD Token Factory gateway connectivity: run one live inference call against `developer.amd.com.cn/radeon/api/v1` with model `DeepSeek-V4-Flash`. Record HTTP status, latency_ms, tokens_in/out. Capture Token Factory portal screenshot showing usage. *Evidence: sanitized terminal output + portal screenshot in docs/evidence/*
- [x] T2.4 LLM router (Token Factory → replay → template) + circuit breaker. *Evidence: docs/evidence/day2_router.md (`pytest tests/test_router.py`)*
- [ ] T2.6 AMD Token Factory quota check: verify rate-limit (RPM cap), per-request token limit, and monthly quota visible in the developer portal. Document the safe ops budget (requests per day / tokens per day) to avoid 429 throttling during the demo and judging window. *Evidence: portal screenshot + rate-limit test output (trigger a 429 or confirm limit from docs)*
- [x] T2.5 First image build + push (moved earlier to surface base-image problems). Dockerfile starts FROM the AMD base image named in Discord, clones the public repo inside the Dockerfile, is built on your own machine or CI (NOT in the notebooks.amd.com/hackathon notebook; AMD staff said that likely won't work), and is pushed to Docker Hub or another public registry. *Evidence: docs/evidence/day2_container.md (ghcr.io/okywoww/merchantguard:latest & docker.io/okywoww/merchantguard:latest)*

## Day 3 — 14–15 Oct: End-to-end + UI  (SCOPE FREEZE at end of day)
- [x] T3.1 Narrator + validator + template fallback. *Evidence: docs/evidence/day3_ui_scenarios.md (`pytest tests/test_api_stream.py` & `tests/test_router.py`)*
- [x] T3.2 SSE pipeline end-to-end. *Evidence: docs/evidence/day3_ui_scenarios.md (`GET /cases/{case_id}/stream`, `POST /cases/evaluate/stream`, 4 scenarios verified)*
- [x] T3.3 Dashboard UI (queue, compare, decision, narrative, action bar). *Evidence: docs/evidence/day3_ui_scenarios.md (`web/index.html` & `web/app.js` live tests)*
- [x] T3.4 Replay cache generated for all demo cases. *Evidence: docs/evidence/day3_ui_scenarios.md (`data/replay/scenario_[1..4]_replay.json` tested with LLM_MODE=replay)*

## Day 4 — 15–16 Oct: Benchmark & hardening
- [x] T4.1 Benchmark against AMD Token Factory (client-side latency p50/p95, tokens/s). *Evidence: docs/evidence/benchmark_report.md (`scripts/benchmark.py` 100 runs, zero-drift verified)*
- [ ] T4.2 Security checklist (security.md §3). *Evidence: scan outputs*
- [x] T4.3 Clean-clone test: one command start. *Evidence: README.md quickstart, single-command run & ghcr.io/okywoww/merchantguard:latest*
- [ ] T4.4 Final image: rebuild from the final commit, push, verify `docker pull` + run from a clean machine, and record the image name for the submission form. *Evidence: registry URL, pull/run output*

## Day 5 — 16–17 Oct: Package & submit (target: Sat 17 Oct 22:00 WIB)
- [ ] T5.1 README (run steps, architecture, synthetic-data disclosure, AMD evidence, and a section "How P(win) is calculated" required by the Track 3 note). 
- [ ] T5.2 Video (see video_script.md), slides PDF, 16:9 cover image.
- [ ] T5.3 Submit on lablab (include the Docker image name); verify the demo URL from a different network/device.

## Day 6 — 18 Oct: Buffer
- [ ] T6.1 Monitor demo URL and endpoints; fix only critical issues.

## Cut-line (if behind, drop in this order)
1. Edit-draft feature → 2. Metrics baseline chart → 3. Replay cache for non-demo cases (keep template tier) → 4. Extra dispute types (keep INR + window scenarios).

## Removed / Out of Scope
- **T3.5 (Evolus partner adapter):** Evolus is a separate Partner Track with its own prizes. Track 3 (Reinvent Commerce) is the only target track. Evolus is fully out of scope — do not build the adapter.
- **$100 VM credit budget (old T2.6):** Superseded by T2.6 Token Factory quota check above. No AMD Developer Cloud VM is provisioned.
