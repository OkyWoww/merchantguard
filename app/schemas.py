"""Pydantic v2 schemas for MerchantGuard cases, gate decisions, narratives, and telemetry."""

from __future__ import annotations
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, ConfigDict


class DecisionAction(str, Enum):
    CONTEST = "CONTEST"
    PARTIAL_REFUND = "PARTIAL_REFUND"
    ACCEPT_REFUND = "ACCEPT_REFUND"
    NEEDS_HUMAN = "NEEDS_HUMAN"


class CourierEvent(BaseModel):
    model_config = ConfigDict(extra="ignore")

    timestamp: str = Field(description="ISO 8601 timestamp of tracking event")
    status: str = Field(description="Status description such as 'DELIVERED', 'IN_TRANSIT'")
    note: Optional[str] = Field(default=None, description="Optional courier comment")
    geo_match: bool = Field(default=False, description="True if courier GPS coordinates matches delivery address")
    signature_present: bool = Field(default=False, description="True if recipient signature was captured")


class DisputeCase(BaseModel):
    model_config = ConfigDict(extra="ignore")

    case_id: str = Field(description="Unique dispute case identifier, e.g. CASE-1001")
    order_id: str = Field(description="Referenced e-commerce order ID")
    claim_date: str = Field(description="ISO 8601 date when customer filed dispute")
    delivery_date: str = Field(description="ISO 8601 date when courier delivered order")
    order_amount: float = Field(ge=0.0, description="Gross merchandise value in USD")
    unit_margin: float = Field(ge=0.0, description="Net merchant product margin in USD")
    dispute_fee: float = Field(default=15.0, ge=0.0, description="Payment processor arbitration fee in USD")
    claimed_reason: str = Field(description="Customer claim category e.g. 'ITEM_NOT_RECEIVED', 'DAMAGED'")
    complaint_text: str = Field(description="Raw message or dispute description from customer")
    courier_events: List[CourierEvent] = Field(default_factory=list, description="Carrier milestone tracking events")


class GateRuleEvaluation(BaseModel):
    rule_id: str
    rule_name: str
    passed: bool
    details: str
    trigger_action: Optional[DecisionAction] = None


class DecisionResult(BaseModel):
    model_config = ConfigDict(extra="ignore")

    case_id: str
    action: DecisionAction
    reason_code: str
    p_win: float = Field(ge=0.0, le=1.0, description="Statistical win probability [0, 1]")
    expected_margin_recovery: float = Field(description="Expected monetary recovery net of fees in USD")
    gate_status: str = Field(description="'PASSED', 'REJECTED', 'ESCALATED', or 'TRIGGERED'")
    rule_evaluations: List[GateRuleEvaluation] = Field(default_factory=list)
    settlement_offer: Optional[float] = Field(default=None, description="Settlement refund amount if PARTIAL_REFUND")


class CitedClaim(BaseModel):
    statement: str
    fact_ids: List[str] = Field(default_factory=list, description="Ground truth evidence IDs supporting statement")


class NarrativePayload(BaseModel):
    model_config = ConfigDict(extra="ignore")

    case_id: str
    summary: str
    claims: List[CitedClaim]
    draft_reply: str
    llm_provider: str = Field(default="amd_rocm_vllm", description="Inference engine used")
    verified_citations: bool = Field(default=True, description="True if all claims are verified against ground facts")
    generation_latency_ms: Optional[float] = None
    mode: str = Field(default="REPLAY", description="Degradation tier: LIVE | REPLAY | TEMPLATE")
    model: Optional[str] = Field(default=None, description="Model identifier used")
    latency_ms: Optional[float] = Field(default=None, description="Latency in milliseconds")
    tokens_out: Optional[int] = Field(default=None, description="Number of output tokens")


class AuditBlock(BaseModel):
    index: int
    timestamp: str
    case_id: str
    action: str
    payload_hash: str
    previous_hash: str
    block_hash: str


class AuditVerificationResult(BaseModel):
    valid: bool
    total_blocks: int
    message: str
    corrupted_index: Optional[int] = None
