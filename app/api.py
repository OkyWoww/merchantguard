"""FastAPI application endpoints for MerchantGuard.

Provides REST and Server-Sent Events (SSE) streaming for dispute evaluations,
policy gate checks, statistical margin calculations, and cryptographic audit logs.
"""

from __future__ import annotations
import os
import json
import asyncio
from pathlib import Path
from typing import List, Dict, Any, Optional
import yaml

from fastapi import FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse, FileResponse
from fastapi.staticfiles import StaticFiles

from app.schemas import (
    DisputeCase,
    DecisionResult,
    NarrativePayload,
    AuditVerificationResult,
    AuditBlock,
)
from app.gate import PolicyGate
from app.margin import MarginEngine
from app.router import InferenceRouter
from app.audit import AuditChain

app = FastAPI(
    title="MerchantGuard - Dispute & Margin Recovery Copilot",
    description="Deterministic Policy Gate and Statistical Margin Engine with AMD ROCm vLLM Narratives",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load YAML configs
BASE_DIR = Path(__file__).resolve().parent.parent
POLICY_CFG_PATH = BASE_DIR / "config" / "policy.yaml"
MARGIN_CFG_PATH = BASE_DIR / "config" / "margin.yaml"

policy_cfg: Dict[str, Any] = {}
margin_cfg: Dict[str, Any] = {}

if POLICY_CFG_PATH.exists():
    with open(POLICY_CFG_PATH, "r", encoding="utf-8") as f:
        policy_cfg = yaml.safe_load(f) or {}

if MARGIN_CFG_PATH.exists():
    with open(MARGIN_CFG_PATH, "r", encoding="utf-8") as f:
        margin_cfg = yaml.safe_load(f) or {}

gate_engine = PolicyGate(policy_cfg)
margin_engine = MarginEngine(margin_cfg)
router_engine = InferenceRouter()
audit_chain = AuditChain()

# In-memory store for active cases
cases_db: Dict[str, DisputeCase] = {}
evaluations_db: Dict[str, Dict[str, Any]] = {}


def _load_sample_fixtures():
    samples_dir = BASE_DIR / "data" / "samples"
    if samples_dir.exists():
        for file in samples_dir.glob("*.json"):
            try:
                with open(file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    case = DisputeCase(**data)
                    cases_db[case.case_id] = case
            except Exception:
                pass


_load_sample_fixtures()

WEB_DIR = BASE_DIR / "web"


@app.get("/")
async def root():
    """Serves the frontend dashboard or fallback service info."""
    index_file = WEB_DIR / "index.html"
    if index_file.exists():
        return FileResponse(index_file)
    return {
        "status": "online",
        "service": "MerchantGuard",
        "version": "1.0.0",
        "docs": "/docs",
    }


@app.get("/app.js")
async def get_app_js():
    """Serves the frontend dashboard JavaScript controller."""
    js_file = WEB_DIR / "app.js"
    if js_file.exists():
        return FileResponse(js_file, media_type="application/javascript")
    raise HTTPException(status_code=404, detail="app.js not found")


@app.get("/health")
async def health_check():
    """Healthcheck endpoint for container orchestration and uptime probes."""
    return {
        "status": "healthy",
        "service": "MerchantGuard",
        "version": "1.0.0",
        "llm_mode": os.getenv("LLM_MODE", "replay"),
        "vllm_base_url": os.getenv("VLLM_BASE_URL", "http://localhost:8000/v1"),
        "audit_blocks_count": len(audit_chain.chain),
    }


@app.get("/cases", response_model=List[DisputeCase])
async def list_cases():
    """List all registered dispute cases."""
    return list(cases_db.values())


@app.get("/cases/{case_id}", response_model=DisputeCase)
async def get_case(case_id: str):
    """Retrieve details for a specific dispute case."""
    if case_id not in cases_db:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")
    return cases_db[case_id]


@app.post("/cases", response_model=Dict[str, Any])
async def create_or_evaluate_case(case: DisputeCase):
    """Registers and runs end-to-end evaluation on a dispute case."""
    cases_db[case.case_id] = case

    # 1. Deterministic Policy Gate
    gate_action, gate_reason, gate_status, rule_evals = gate_engine.evaluate(case)

    # 2. Statistical Margin Recovery Engine
    decision = margin_engine.compute_final_decision(
        case=case,
        gate_action=gate_action,
        gate_reason=gate_reason,
        gate_status=gate_status,
        rule_evaluations=rule_evals,
    )

    # 3. Cited Narrative Generation via Router
    narrative = await router_engine.generate_narrative(case, decision)

    # 4. Cryptographic Audit Chain
    block = audit_chain.append_decision(
        decision=decision,
        extra_payload={
            "narrative_summary": narrative.summary,
            "provider": narrative.llm_provider,
        },
    )

    result = {
        "case": case.model_dump(),
        "decision": decision.model_dump(),
        "narrative": narrative.model_dump(),
        "audit_block": block.model_dump(),
    }
    evaluations_db[case.case_id] = result
    return result


@app.get("/cases/{case_id}/stream")
async def stream_case_evaluation(case_id: str):
    """
    Server-Sent Events (SSE) endpoint providing streaming execution telemetry:
    Emits stage-by-stage progression (Gate -> Margin -> Narrator -> Audit).
    """
    if case_id not in cases_db:
        raise HTTPException(status_code=404, detail=f"Case {case_id} not found")

    case = cases_db[case_id]

    async def event_generator():
        # Step 1: Policy Gate
        await asyncio.sleep(0.15)
        gate_action, gate_reason, gate_status, rule_evals = gate_engine.evaluate(case)
        yield f"event: gate_evaluated\ndata: {json.dumps({'action': gate_action.value, 'reason': gate_reason, 'rules': [r.model_dump() for r in rule_evals]})}\n\n"

        # Step 2: Margin Engine
        await asyncio.sleep(0.20)
        decision = margin_engine.compute_final_decision(
            case, gate_action, gate_reason, gate_status, rule_evals
        )
        yield f"event: margin_computed\ndata: {json.dumps(decision.model_dump())}\n\n"

        # Step 3: LLM Narrator (AMD ROCm / Replay)
        await asyncio.sleep(0.25)
        narrative = await router_engine.generate_narrative(case, decision)
        yield f"event: narrative_generated\ndata: {json.dumps(narrative.model_dump())}\n\n"

        # Step 4: Cryptographic Audit
        await asyncio.sleep(0.10)
        block = audit_chain.append_decision(
            decision, extra_payload={"streamed": True, "provider": narrative.llm_provider}
        )
        yield f"event: audit_committed\ndata: {json.dumps(block.model_dump())}\n\n"
        yield "event: complete\ndata: {\"status\": \"completed\"}\n\n"

    return StreamingResponse(
        event_generator(),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/audit/verify", response_model=AuditVerificationResult)
async def verify_audit_chain():
    """Validates entire SHA-256 hash-chain integrity."""
    return audit_chain.verify_integrity()


@app.get("/audit/blocks", response_model=List[AuditBlock])
async def get_audit_blocks():
    """Returns all blocks in the immutable audit ledger."""
    return audit_chain.chain


@app.get("/metrics")
async def get_system_metrics():
    """Aggregated financial and operational metrics for the merchant."""
    total_evaluated = len(audit_chain.chain)
    return {
        "total_disputes_processed": total_evaluated,
        "active_cases_in_queue": len(cases_db),
        "chain_integrity_valid": audit_chain.verify_integrity().valid,
        "llm_mode": os.getenv("LLM_MODE", "replay"),
    }


if WEB_DIR.exists():
    app.mount("/web", StaticFiles(directory=str(WEB_DIR)), name="web_assets")

if __name__ == "__main__":
    import uvicorn

    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)

