"""LLM Prompt Contract & Fact-Citation Validator.

INVARIANT: The LLM NEVER decides the outcome.
The outcome is already decided by Gate & Margin engines.
The LLM only compiles cited factual narratives based strictly on ground-truth case evidence.
"""

from __future__ import annotations
import re
from typing import Dict, Any, List, Set
from app.schemas import DisputeCase, DecisionResult, NarrativePayload, CitedClaim


class FactCitationValidator:
    @staticmethod
    def extract_ground_truth_facts(case: DisputeCase, decision: DecisionResult) -> Dict[str, str]:
        """Extracts canonical verified facts from the case data."""
        facts: Dict[str, str] = {
            "order_id": case.order_id,
            "case_id": case.case_id,
            "order_amount": f"${case.order_amount:.2f}",
            "unit_margin": f"${case.unit_margin:.2f}",
            "dispute_fee": f"${case.dispute_fee:.2f}",
            "claim_date": case.claim_date,
            "delivery_date": case.delivery_date,
            "claimed_reason": case.claimed_reason,
            "action_decision": decision.action.value,
            "reason_code": decision.reason_code,
        }

        has_geo = any(ev.geo_match for ev in case.courier_events)
        has_sig = any(ev.signature_present for ev in case.courier_events)

        if has_geo:
            facts["courier_geo"] = "Carrier GPS coordinates match delivery coordinates"
        if has_sig:
            facts["signature"] = "Physical recipient signature verified"
        if len(case.courier_events) > 0:
            facts["courier_delivered"] = f"Delivered milestone registered on {case.delivery_date}"

        return facts

    @staticmethod
    def validate_claims(
        claims: List[CitedClaim], valid_facts: Set[str]
    ) -> Tuple[List[CitedClaim], bool]:
        """Validates that cited claims only reference valid factual evidence IDs."""
        verified = True
        sanitized_claims: List[CitedClaim] = []

        for claim in claims:
            # Check if all cited fact_ids exist in ground truth
            invalid_ids = [fid for fid in claim.fact_ids if fid not in valid_facts]
            if invalid_ids:
                verified = False
                # Remove ungrounded fact IDs to protect against hallucinations
                valid_ids_only = [fid for fid in claim.fact_ids if fid in valid_facts]
                sanitized_claims.append(
                    CitedClaim(
                        statement=claim.statement,
                        fact_ids=valid_ids_only,
                    )
                )
            else:
                sanitized_claims.append(claim)

        return sanitized_claims, verified

    @staticmethod
    def construct_system_prompt() -> str:
        return (
            "You are MerchantGuard Fact Narrator running on AMD ROCm. "
            "You write cited factual narratives for e-commerce dispute responses.\n"
            "RULES:\n"
            "1. You DO NOT decide the action; the action is already locked by the Deterministic Policy Gate.\n"
            "2. Every factual assertion MUST cite its evidence ID using format [FACT:evidence_id].\n"
            "3. Do not invent or hallucinate carrier timestamps, tracking numbers, or promises.\n"
            "4. Keep the tone professional, objective, and legally precise."
        )

    @staticmethod
    def construct_user_prompt(case: DisputeCase, decision: DecisionResult, ground_facts: Dict[str, str]) -> str:
        facts_list = "\n".join([f"- {k}: {v}" for k, v in ground_facts.items()])
        return (
            f"CASE SUMMARY:\n"
            f"Case ID: {case.case_id}\n"
            f"Customer Complaint: \"{case.complaint_text}\"\n"
            f"LOCKED ACTION: {decision.action.value} ({decision.reason_code})\n"
            f"Statistical P(Win): {decision.p_win * 100:.1f}%\n"
            f"Expected Net Margin Recovery: ${decision.expected_margin_recovery:.2f}\n\n"
            f"VERIFIED EVIDENCE GROUND TRUTH:\n{facts_list}\n\n"
            f"Generate a structured summary, a list of cited factual claims, and a professional dispute reply."
        )
