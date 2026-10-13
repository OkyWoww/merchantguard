# tech.md — Technical design

## 1. Stack
| Layer | Choice |
|---|---|
| Backend | Python 3.11+, FastAPI, Pydantic v2, SSE streaming |
| Rules | Pure Python, YAML config |
| Margin model | scikit-learn (logistic regression or small gradient boosting), exported with joblib |
| LLM serving | **AMD Token Factory gateway** — OpenAI-compatible chat completions at `developer.amd.com.cn/radeon/api/v1`, model `DeepSeek-V4-Flash`. Configured entirely via env vars (`VLLM_BASE_URL`, `MODEL_NAME`, `OPENAI_API_KEY`). No self-hosted vLLM instance or AMD Developer Cloud VM is required for Track 3. |
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
1. **Tier 1 (LIVE):** AMD Token Factory gateway (`developer.amd.com.cn/radeon/api/v1`, model `DeepSeek-V4-Flash`). OpenAI-compatible chat completions. Timeout configurable via `VLLM_TIMEOUT` (default 35 s). Bearer API key from `OPENAI_API_KEY` env var — never hard-coded.
2. **Tier 2 (REPLAY):** on timeout / HTTP error / circuit-breaker OPEN, return cached real outputs keyed by case hash (known demo cases only).
3. **Tier 3 (TEMPLATE):** no cache hit → deterministic template narrative built from facts. UI shows TEMPLATE banner. REPLAY and TEMPLATE both show a visible banner.
Router records `mode`, `model`, `latency_ms`, `tokens_out` on every call. Circuit breaker: 2 consecutive failures → skip tier for 60 s.

## 6. Narrator output contract (JSON)
```json
{ "summary": "string", "claims": [{"text": "string", "fact_ids": ["F3","F7"]}], "draft_reply": "string" }
```
Validator rejects: unknown fact IDs, claims with no fact IDs, any mention of an action word that contradicts the engine's action, output that fails schema. On rejection: one retry, then fall back to a template narrative built from facts (no LLM).

## 7. Environment variables (`.env.example`)
```
PORT=8000
LLM_MODE=live               # live | replay | template
VLLM_BASE_URL=https://developer.amd.com.cn/radeon/api/v1   # AMD Token Factory base URL
MODEL_NAME=DeepSeek-V4-Flash                               # AMD Token Factory model
VLLM_MODEL=DeepSeek-V4-Flash                               # alias used by router
OPENAI_API_KEY=<your-amd-token-factory-bearer-key>         # obtain from developer.amd.com.cn portal
VLLM_TIMEOUT=35.0
RATE_LIMIT_PER_MIN=20
AUDIT_LOG_PATH=data/audit_log.json
POLICY_CONFIG_PATH=config/policy.yaml
MARGIN_CONFIG_PATH=config/margin.yaml
```
**Security:** `OPENAI_API_KEY` must be set in `.env` (gitignored) or as a runtime secret. ZERO raw keys in any committed file.

## 8. AMD infrastructure evidence to capture
- **Client-side latency benchmark:** p50/p95/p99 request latency and tokens-per-second measured against the AMD Token Factory endpoint. Save output to `docs/benchmarks/`.
- **Token Factory portal screenshot:** shows the project/application name and usage dashboard confirming AMD infrastructure consumption.
- **Sanitized request logs:** router logs with timestamp, model ID, HTTP status, latency_ms, tokens_out — API key redacted.
- **No `rocm-smi` required:** Track 3 uses the managed Token Factory gateway; GPU-level telemetry is not accessible client-side.

## 9. Synthetic data
`data/generator.py` creates ≥200 cases with: class imbalance, missing logs, contradictory courier notes, high-value outliers, window edge cases (day 13/14/15), fee-vs-margin traps. Seeded RNG so results are reproducible. Labels derive from documented generative rules; document this in README as synthetic.

## 10. Container build and submission (per AMD staff in the event Discord)
- Do not build images inside notebooks.amd.com/hackathon (likely to fail). Build on your own machine or CI.
- Dockerfile: `ARG BASE_IMAGE` then `FROM ${BASE_IMAGE}` (value = the base image AMD named in Discord; record exact name/tag in docs/evidence/requirements.md; docker-compose passes it as `build.args.BASE_IMAGE`; never hard-code a guessed tag), clone the public repo inside the Dockerfile, install deps, set non-root user and entrypoint.
- Push to Docker Hub or another public registry (GHCR is an option; confirm it counts as "public registry"). Put the image name in the submission.
- **Tier 1 availability in container:** the container reads `VLLM_BASE_URL` and `OPENAI_API_KEY` from environment. If those vars are absent or the endpoint is unreachable, the router degrades to REPLAY/TEMPLATE automatically with a visible banner. No private AMD Cloud VM endpoint is baked into the image.
