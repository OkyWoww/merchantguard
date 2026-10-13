# tech.md — Technical design

## 1. Stack
| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2, SSE streaming |
| Rules | Pure Python, YAML config |
| Margin model | scikit-learn (logistic regression or small gradient boosting), exported with joblib |
| LLM serving | Open-weights instruct model (e.g. Llama-3.1-8B-Instruct or Qwen2.5) via vLLM on AMD Developer Cloud (only LLM provider; Fireworks endpoint is retired for ACT III per AMD staff) |
| Frontend | Single-page dashboard (Tailwind + vanilla JS or minimal React) |
| Storage | SQLite (cases, audit log); tables are created automatically at FastAPI startup in the `lifespan` handler (`CREATE TABLE IF NOT EXISTS`), so no separate migration script is needed |
| Packaging | Docker + docker-compose (event rules require a containerized app) |
| Hosting | Public URL on a free host (confirm allowed platforms at kickoff) |

## 2. Pipeline
```
Inbound case → PII scrub → Policy Gate → Margin Engine → LLM Narrator → Validator → Human UI → Audit log
                               │ (rules resolve? skip LLM decision)               │
                               └────────── always works with LLM down ────────────┘
```

## 3. Repo layout
```
merchantguard/
  app/ (api.py, gate.py, margin.py, narrator.py, router.py, audit.py, schemas.py)
  config/ (policy.yaml, margin.yaml)
  data/ (generator.py, samples/, replay/)
  models/ (margin.joblib)
  web/ (index.html, app.js)
  tests/ (test_gate.py, test_margin.py, test_validator.py, test_router.py)
  docker-compose.yml  Dockerfile  .env.example  README.md  LICENSE
```

## 4. API
| Method | Path | Purpose |
|---|---|---|
| POST | /cases | submit a case |
| GET | /cases | queue with status/priority |
| GET | /cases/{id}/stream | SSE: gate → margin → narrative events |
| POST | /cases/{id}/review | approve / edit / reject (logged) |
| GET | /metrics | recovered-margin total, mode counts, latency stats |
| GET | /health | liveness + active LLM tier |

## 5. LLM router (demo ladder)
1. **Tier 1:** vLLM endpoint on AMD Developer Cloud (OpenAI-compatible API), timeout ~8 s.
2. **Tier 2 (REPLAY):** on timeout/error, return cached real outputs keyed by case hash (known demo cases only).
3. **Tier 3 (TEMPLATE):** no cache hit → deterministic template narrative built from facts. UI shows TEMPLATE banner. REPLAY and TEMPLATE both show a visible banner.
Router records `mode`, `model`, `latency_ms`, `tokens_out` on every call. Circuit breaker: 2 consecutive failures → skip tier for 60 s.

## 6. Narrator output contract (JSON)
```json
{ "summary": "string", "claims": [{"text": "string", "fact_ids": ["F3","F7"]}], "draft_reply": "string" }
```
Validator rejects: unknown fact IDs, claims with no fact IDs, any mention of an action word that contradicts the engine's action, output that fails schema. On rejection: one retry, then fall back to a template narrative built from facts (no LLM).

## 7. Environment variables (`.env.example`)
```
BASE_IMAGE=               # exact AMD base image name:tag from the event Discord (do not guess); passed as a build arg
LLM_MODE=live            # live | replay | template
VLLM_BASE_URL=
VLLM_MODEL=
DATABASE_URL=sqlite:///./mg.db
RATE_LIMIT_PER_MIN=20
```

## 8. AMD hardware evidence to capture
- `rocm-smi` screenshot/log while serving and during a benchmark run.
- Benchmark script output: p50/p95 latency, tokens/s, concurrent requests. Save to `docs/benchmarks/`.
- Exact serving command and model name recorded in README.
- Verify at kickoff: official ROCm/vLLM container image and any required setup from the event's AMD workshop materials. Do not guess versions.

## 9. Synthetic data
`data/generator.py` creates ≥200 cases with: class imbalance, missing logs, contradictory courier notes, high-value outliers, window edge cases (day 13/14/15), fee-vs-margin traps. Seeded RNG so results are reproducible. Labels derive from documented generative rules; document this in README as synthetic.

## 10. Container build and submission (per AMD staff in the event Discord)
- Do not build images inside notebooks.amd.com/hackathon (likely to fail). Build on your own machine or CI.
- Dockerfile: `ARG BASE_IMAGE` then `FROM ${BASE_IMAGE}` (value = the base image AMD named in Discord; record exact name/tag in docs/evidence/requirements.md; docker-compose passes it as `build.args.BASE_IMAGE`; never hard-code a guessed tag), clone the public repo inside the Dockerfile, install deps, set non-root user and entrypoint.
- Push to Docker Hub or another public registry (GHCR is an option; confirm it counts as "public registry"). Put the image name in the submission.
- **Open design question until the base image is known:** if judges run the image on their own AMD GPU, a container that depends on your private AMD Cloud endpoint will break once your credits end. Preferred design: the entrypoint starts the app and uses `VLLM_BASE_URL` if set; if the image is run with a GPU and the model is available it can start vLLM itself; otherwise it runs in REPLAY/TEMPLATE mode with a visible banner. Decide after reading the base image's contents.
