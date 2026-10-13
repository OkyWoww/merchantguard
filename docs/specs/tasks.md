# tasks.md — Task list with required evidence

Rule: tick a box only after attaching the evidence (diff, test output, or command output) in `docs/evidence/`.

## Day 0 — Pre-kickoff (now → 12 Oct)
- [ ] T0.1 Confirm event requirements on the lablab page and Discord (Evolus workspace/event code, AMD AI Developer Program signup, allowed hosting). Record the exact AMD base image name/tag from the Discord message in docs/evidence/requirements.md. Re-ask AMD staff, one question per message: (a) is work done before kickoff (repo scaffold, Dockerfile, data generator) allowed? (b) must a project align with one of the four themes to compete for the main prize? *Evidence: screenshot or notes in docs/evidence/requirements.md*
- [ ] T0.2 Create the AMD account (use a different email if signup says "invalid or already used"), enter the AMD Developer Program, and verify AMD Developer Cloud access. *Evidence: screenshot of access + chat-completion output from your own vLLM endpoint*
- [ ] T0.3 HOLD until the pre-kickoff scaffolding question (T0.1a) is answered; otherwise do after kickoff. Repo skeleton, Dockerfile, .env.example, pre-commit secret scan. *Evidence: `git log`, hook run output*
- [ ] T0.4 HOLD (same condition as T0.3). Synthetic data generator draft. *Evidence: generator run output (row counts, class balance)*

## Day 1 — 12–13 Oct: Plumbing
- [x] T1.1 Deploy empty FE+API to public URL. *Evidence: docs/evidence/day1_plumbing.md*
- [x] T1.2 Pydantic schemas + Policy Gate R-001..R-006 with fixtures. *Evidence: docs/evidence/day1_plumbing.md (`pytest tests/test_gate.py`)*
- [x] T1.3 Audit log with hash chain. *Evidence: docs/evidence/day1_plumbing.md (tests + `GET /audit/verify`)*

## Day 2 — 13–14 Oct: Model & AMD wiring
- [x] T2.1 Train/export margin model; calibration/sanity report. *Evidence: docs/evidence/margin_model_report.md & docs/evidence/day2_margin_engine.md (1,821 bytes joblib)*
- [x] T2.2 Margin engine + action logic from config. *Evidence: docs/evidence/day2_margin_engine.md (`pytest tests/test_margin.py`, 4 scenarios verified)*
- [ ] T2.3 vLLM serving on AMD Developer Cloud. *Evidence: serve command, `/v1/models` response, `rocm-smi` capture*
- [x] T2.4 LLM router (vLLM → replay → template) + circuit breaker. *Evidence: docs/evidence/day2_router.md (`pytest tests/test_router.py`)*
- [x] T2.6 Credit budget: new AMD AI Developer Program members get $100 cloud credit (per kickoff slides). Find the instance hourly price, compute usable hours, and schedule GPU windows (dev, benchmark, recording); stop the instance when idle. *Evidence: docs/evidence/budget.md & docs/evidence/day2_router.md*
- [x] T2.5 First image build + push (moved earlier to surface base-image problems). Dockerfile starts FROM the AMD base image named in Discord, clones the public repo inside the Dockerfile, is built on your own machine or CI (NOT in the notebooks.amd.com/hackathon notebook; AMD staff said that likely won't work), and is pushed to Docker Hub or another public registry. *Evidence: docs/evidence/day2_container.md (ghcr.io/okywoww/merchantguard:latest & docker.io/okywoww/merchantguard:latest)*

## Day 3 — 14–15 Oct: End-to-end + UI  (SCOPE FREEZE at end of day)
- [x] T3.1 Narrator + validator + template fallback. *Evidence: docs/evidence/day3_ui_scenarios.md (`pytest tests/test_api_stream.py` & `tests/test_router.py`)*
- [x] T3.2 SSE pipeline end-to-end. *Evidence: docs/evidence/day3_ui_scenarios.md (`GET /cases/{case_id}/stream`, `POST /cases/evaluate/stream`, 4 scenarios verified)*
- [x] T3.3 Dashboard UI (queue, compare, decision, narrative, action bar). *Evidence: docs/evidence/day3_ui_scenarios.md (`web/index.html` & `web/app.js` live tests)*
- [x] T3.4 Replay cache generated for all demo cases. *Evidence: docs/evidence/day3_ui_scenarios.md (`data/replay/scenario_[1..4]_replay.json` tested with LLM_MODE=replay)*

## Day 4 — 15–16 Oct: Benchmark & hardening
- [ ] T4.1 Benchmark on AMD instance (latency p50/p95, tokens/s, concurrency). *Evidence: docs/benchmarks/*
- [ ] T4.2 Security checklist (security.md §3). *Evidence: scan outputs*
- [ ] T4.3 Clean-clone test: one command start. *Evidence: terminal log on a fresh clone*
- [ ] T4.4 Final image: rebuild from the final commit, push, verify `docker pull` + run from a clean machine, and record the image name for the submission form. *Evidence: registry URL, pull/run output*

## Day 5 — 16–17 Oct: Package & submit (target: Sat 17 Oct 22:00 WIB)
- [ ] T5.1 README (run steps, architecture, synthetic-data disclosure, AMD evidence, and a section "How P(win) is calculated" required by the Track 3 note). 
- [ ] T5.2 Video (see video_script.md), slides PDF, 16:9 cover image.
- [ ] T5.3 Submit on lablab (include the Docker image name); verify the demo URL from a different network/device.

## Day 6 — 18 Oct: Buffer
- [ ] T6.1 Monitor demo URL and endpoints; fix only critical issues.

## Cut-line (if behind, drop in this order)
1. Edit-draft feature → 2. Metrics baseline chart → 3. Replay cache for non-demo cases (keep template tier) → 4. Extra dispute types (keep INR + window scenarios).

## Optional stretch — Evolus intake adapter (decide at kickoff, timebox 2 hours)
- [ ] T3.5 Only if Evolus workspace setup works within the timebox: expose case intake (order history, courier log, complaint) as an input adapter that outputs the existing `Case` schema. Core gate/margin/narrator code must not change. *Evidence: adapter test output + diff showing no changes under app/gate.py and app/margin.py*
- If setup is not quick or the event rules say Evolus is required, follow the rules from T0.1 instead of this stretch rule.
- Evolus is a separate Partner Track (own prizes) per the kickoff slides. Before building on it, ask AMD staff whether Evolus-hosted open models count as AMD infrastructure for Track 3, and whether using Evolus is required or optional. Do not use any Evolus-hosted model as an LLM tier until that is answered in writing.
- If the timebox is exceeded, drop it and note why in docs/evidence/requirements.md.
