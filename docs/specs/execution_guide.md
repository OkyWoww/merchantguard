# execution_guide.md — How to run the 6-day sprint

## 1. Before kickoff
1. Read the lablab page, Hackathon Guidelines, Rule Book, and the AMD Developer Program signup requirement. The event page also mentions a free Evolus workspace (code shared at kickoff) and a containerized app with public GitHub repo and runnable README. Confirm exactly what each requires; do not assume.
2. Confirm: main agent must use an open model served on AMD infrastructure (your own vLLM on AMD Developer Cloud). AMD staff confirmed on Discord that the Fireworks API endpoint is retired for ACT III and cannot be used.
3. Confirm: LLM must not be the only forecasting method (satisfied by the statistical margin model).
4. Prepare repo, Docker base, generator, secret-scan hook.

## 2. Day-by-day gates
| Day | Gate to pass before moving on |
|---|---|
| 1 | Public URL live; gate tests green |
| 2 | AMD endpoint answers; router survives forced failures |
| 3 | 4 scenarios run end-to-end; replay works with LLM off; **scope freeze** |
| 4 | Benchmarks + rocm-smi evidence saved; clean-clone start works |
| 5 | Video, slides, README done; submitted |
| 6 | Buffer only |

## 3. Demo ladder (resilience)
Tier 1 AMD vLLM (LIVE) → Tier 2 replay of cached real model outputs for known demo cases (REPLAY) → Tier 3 deterministic template narrative for any other case (TEMPLATE). No non-AMD LLM provider is used. During the recorded video and live judging, prefer Tier 1 and show the mode banner. If Tier 1 is down, say so openly and show the fallback working: that is a strength, not something to hide.

## 4. Submission checklist (confirm against the live rules)
- [ ] Public GitHub repo with LICENSE and README that runs
- [ ] Containerized app, one-command start; Docker image built from the AMD base image named in Discord (repo cloned inside the Dockerfile), built outside the AMD notebook, pushed to Docker Hub or another public registry, and its image name entered in the submission (per AMD staff in the event Discord)
- [ ] Public demo URL reachable
- [ ] Video (MP4) and slide deck (PDF)
- [ ] Cover image 16:9 (PNG/JPG)
- [ ] Title, short and long description (≥100 words), tags/technologies, track = Reinvent Commerce
- [ ] AMD evidence (rocm-smi, benchmark) referenced in README and video
- [ ] Any event-specific requirement found in T0.1 (e.g. Evolus workspace)

## 5. Risk review (plan evaluation)
**Anti-survivorship bias — how similar projects fail:** chatbot wrappers with no real decision logic; LLM chains that add latency and failure points; polished demos on clean synthetic data that break on messy input; submissions with unreachable demo URLs or READMEs that don't run. Counter: decisions by rules + model, deliberately messy data, one-LLM-call design, clean-clone test.

**Single point of failure:** the LLM endpoint on AMD Developer Cloud (access, credits, cold start). Reinforce first: Day 0 access check, router with replay and template tiers, a pre-warmed endpoint before every demo/recording, and an app that works without any LLM.

**Pre-mortem — worst cases and mitigations:**
| Failure | Cause | Mitigation |
|---|---|---|
| No working demo at judging | URL down / container broken | Day-1 deploy, Day-4 clean-clone test, Day-6 monitoring |
| Disqualified / low score on rules | Model not on AMD infra; missing required step (e.g. workspace, program signup) | T0.1 verification; log mode per call; show AMD evidence |
| Misleading claims penalized | P(win) from synthetic data presented as real accuracy | Labels in UI/README (rule.md D7) |
| Scope creep | Too many features for 6 days | Scope freeze Day 3, cut-line in tasks.md |
| Key leak | Public repo | Pre-commit + CI scan, rotate on any exposure |
| Credit burn | Public traffic | Rate limits, replay default under low budget |
| GPU credits run out before judging ($100 free credit) | Instance left running, long benchmarks | Budget in T2.6, stop when idle, record benchmarks and video in planned windows, REPLAY/TEMPLATE keep the app alive |

## 6. If you fall behind
Follow the cut-line in tasks.md. Never cut: the gate, the margin engine, the audit log, the demo ladder, the README.
