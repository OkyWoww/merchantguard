# MerchantGuard (Dispute & Margin Recovery Copilot)

> **AMD Developer Hackathon: ACT III — Track: Reinvent Commerce**  
> An autonomous e-commerce dispute decision engine where a **Deterministic Policy Gate** and **Statistical Margin Engine** make authoritative decisions, while an open-weights LLM running via **vLLM on AMD ROCm** (with pre-cached Replay Mode fallback) only produces cited factual narratives.

---

## 🛡️ Core Architectural Invariants

1. **The LLM is NEVER the sole decider**: Pure Python rules enforce deterministic validation (`R-001` through `R-006`). No prompt injection or hallucination can flip a dispute decision.
2. **Zero Secrets Commited**: Only `.env.example` is committed. No API keys or credentials in source control.
3. **Strict Citation Contract**: The narrator only generates statements bound to verified evidence IDs (`[FACT:courier_geo]`, `[FACT:signature]`, `[FACT:claim_date]`). Ungrounded assertions are purged.
4. **Degradation Ladder**: Primary inference queries AMD ROCm vLLM; if unreachable, gracefully falls back to pre-cached deterministic Replay Mode fixtures.
5. **Cryptographic Audit Chain**: Every evaluation is appended to a tamper-evident SHA-256 hash-chain with instant mathematical verification.

---

## 📁 Repository Structure

```text
merchantguard/
├── app/
│   ├── __init__.py
│   ├── api.py           # FastAPI endpoints (/health, /cases, /cases/{id}/stream, /audit/verify)
│   ├── schemas.py       # Pydantic v2 schemas for Cases, Facts, Decisions, and Telemetry
│   ├── gate.py          # Deterministic Policy Gate (Rules R-001 to R-006)
│   ├── margin.py        # Statistical Margin Recovery Calculator & P(Win) formula
│   ├── narrator.py      # LLM Prompt Contract & Fact-Citation Validator
│   ├── router.py        # Degradation Ladder (AMD vLLM -> Replay Mode Cache)
│   └── audit.py         # Cryptographic hash-chain audit log system
├── config/
│   ├── policy.yaml      # Configurable thresholds (return_window_days, high_value_cutoff)
│   └── margin.yaml      # Tunable recovery formulas and dispute fee parameters
├── data/
│   ├── samples/         # Static fixtures for the 4 core demo scenarios
│   │   ├── scenario_1_clean_win.json
│   │   ├── scenario_2_ambiguous.json
│   │   ├── scenario_3_window_bypass.json
│   │   └── scenario_4_economic_trap.json
│   ├── replay/          # Pre-cached narrative responses for Replay Mode
│   └── generator.py     # Reproducible synthetic dataset generator draft
├── models/
│   └── .gitkeep         # Storage for trained lightweight margin model (joblib)
├── web/
│   ├── index.html       # Single-screen dashboard UI (Tailwind CSS CDN)
│   └── app.js           # Lightweight SSE stream consumer and dispute queue interaction
├── tests/
│   ├── __init__.py
│   ├── test_gate.py     # Fixture tests for Policy Gate rules (R-001 to R-006)
│   ├── test_margin.py   # Margin calculation sanity & recovery edge cases
│   └── test_audit.py    # Hash-chain integrity verification tests
├── docs/
│   └── evidence/        # Folder for benchmark logs and rocm-smi captures
├── .env.example
├── .gitignore
├── Dockerfile           # Non-root user container configuration
├── docker-compose.yml
├── requirements.txt
├── LICENSE              # MIT License
└── README.md            # Hackathon project overview & reproduction guide
```

---

## ⚡ Quickstart

### 1. Local Python Setup
```bash
python -m venv .venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env

# Run FastAPI Dev Server
uvicorn app.api:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Docker Deployment
```bash
docker compose up --build -d
curl http://localhost:8000/health
```

### 3. Running Pytest Suite
```bash
pytest tests/ -v
```

---

## 🔬 Policy Gate Rules (R-001 to R-006)

| Code | Rule Name | Condition | Action / Flag |
|---|---|---|---|
| `R-001` | **Return Window Expired** | Claim Date - Delivery Date > `return_window_days` | Reject claim immediately (`CONTEST`) |
| `R-002` | **Verified Signature + Geo Match** | Signature present AND Courier GPS confirms delivery coords | Auto-contest evidence valid (`CONTEST`) |
| `R-003` | **High-Value Item Escalate** | Order Amount > `high_value_cutoff` without signature | Flag for Senior Adjuster (`NEEDS_HUMAN`) |
| `R-004` | **Economic Fee Trap** | Dispute fee > Expected Margin Recovery ($EV < 0$) | Auto-refund to protect merchant margin (`ACCEPT_REFUND`) |
| `R-005` | **Partial Damage Claim** | Claimed reason matches partial transit defect | Offer settlement formula (`PARTIAL_REFUND`) |
| `R-006` | **Courier Anomaly Missing Data** | No tracking event or courier GPS mismatch | Route to carrier investigation (`NEEDS_HUMAN`) |

---

## 📊 Statistical Margin Recovery Formula

Expected Value ($EV$) of contesting a dispute:

$$EV = P(\text{Win}) \times (\text{Unit Margin} + \text{Dispute Fee}) - (1 - P(\text{Win})) \times \text{Dispute Fee}$$

- If $EV \le 0$: System chooses `ACCEPT_REFUND` (contesting loses more money than granting refund).
- If $EV > 0$ and Policy Gate passes: System chooses `CONTEST`.
- If claim is partial defect: System computes optimal `PARTIAL_REFUND`.

---

## 🚀 AMD ROCm vLLM Integration

MerchantGuard routes narrative generation through local AMD ROCm instances:
- **Target Hardware**: AMD Instinct™ MI300X / Radeon™ RX 7900 XTX
- **Inference Server**: `vLLM` container with ROCm 6.x execution backend
- **Model**: `meta-llama/Llama-3.1-8B-Instruct`
- **Fallback**: Zero-latency offline Replay Cache for demonstrations and network air-gaps.
