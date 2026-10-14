"""LLM Prompt Contract & Fact-Citation Validator.

INVARIANT: The LLM NEVER decides the outcome.
The outcome is already decided by Gate & Margin engines.
The LLM only compiles cited factual narratives based strictly on ground-truth case evidence.
"""

from __future__ import annotations
import json
import re
from typing import Dict, Any, List, Set, Tuple, Optional
from app.schemas import DisputeCase, DecisionResult, NarrativePayload, CitedClaim, DecisionAction


class FactKey(str):
    """String subclass representing fact key that also exposes .fact_id property."""
    @property
    def fact_id(self) -> str:
        return str(self)


class FactCitationValidator:
    @staticmethod
    def extract_ground_truth_facts(case: DisputeCase, decision: DecisionResult) -> Dict[FactKey, str]:
        """Extracts canonical verified facts from the case data."""
        facts: Dict[FactKey, str] = {
            FactKey("order_id"): case.order_id,
            FactKey("case_id"): case.case_id,
            FactKey("order_amount"): f"${case.order_amount:.2f}",
            FactKey("unit_margin"): f"${case.unit_margin:.2f}",
            FactKey("dispute_fee"): f"${case.dispute_fee:.2f}",
            FactKey("claim_date"): case.claim_date,
            FactKey("delivery_date"): case.delivery_date,
            FactKey("claimed_reason"): case.claimed_reason,
            FactKey("action_decision"): decision.action.value,
            FactKey("reason_code"): decision.reason_code,
            FactKey("F1"): f"Delivery registered on {case.delivery_date}",
            FactKey("F2"): f"Order {case.order_id} total amount ${case.order_amount:.2f}",
        }

        has_geo = any(ev.geo_match for ev in case.courier_events)
        has_sig = any(ev.signature_present for ev in case.courier_events)

        if has_geo:
            facts[FactKey("courier_geo")] = "Carrier GPS coordinates match delivery coordinates"
            facts[FactKey("F3")] = "Carrier GPS coordinates match delivery coordinates"
        if has_sig:
            facts[FactKey("signature")] = "Physical recipient signature verified"
            facts[FactKey("F4")] = "Physical recipient signature verified"
        if len(case.courier_events) > 0:
            facts[FactKey("courier_delivered")] = f"Delivered milestone registered on {case.delivery_date}"

        return facts

    @staticmethod
    def extract_cited_fact_ids(text: str) -> List[str]:
        """Extracts cited fact keys inside brackets, e.g. [F1], [FACT:courier_geo], [F99]."""
        matches = re.findall(r"\[(?:FACT:)?([A-Za-z0-9_]+)\]", text)
        return list(dict.fromkeys(matches))

    @staticmethod
    def check_action_alignment(text: str, expected_action: DecisionAction) -> bool:
        """Verifies that the narrative doesn't contradict the engine's locked decision action."""
        lower = text.lower()
        if expected_action == DecisionAction.CONTEST:
            if any(phrase in lower for phrase in ["agree to process a full refund", "accept full refund", "process a refund", "refund as requested"]):
                return False
        elif expected_action == DecisionAction.ACCEPT_REFUND:
            if any(phrase in lower for phrase in ["contest dispute", "deny claim", "reject refund"]):
                return False
        return True

    @staticmethod
    def safe_parse_llm_json(raw_text: str) -> Optional[Dict[str, Any]]:
        """Safely parses JSON output from LLM, returning None if malformed."""
        if not raw_text or not isinstance(raw_text, str):
            return None
        try:
            return json.loads(raw_text)
        except Exception:
            return None

    @staticmethod
    def validate_and_sanitize(
        raw_text: str,
        ground_facts: Dict[Any, str],
        decision: DecisionResult
    ) -> Tuple[bool, str, str]:
        """
        Validates narrative text for:
        1. Action alignment (does not contradict decision).
        2. Citation presence.
        3. Factual hallucination (rejects fact IDs not in ground truth).
        """
        if not FactCitationValidator.check_action_alignment(raw_text, decision.action):
            return False, raw_text, "Action mismatch: narrative contradicts locked engine action"

        cited_ids = FactCitationValidator.extract_cited_fact_ids(raw_text)
        if not cited_ids:
            return False, raw_text, "Missing citations: narrative contains no bracketed evidence citations"

        valid_ids = {str(k) for k in ground_facts.keys()}
        hallucinated = [fid for fid in cited_ids if fid not in valid_ids]

        sanitized = raw_text
        if hallucinated:
            for bad_id in hallucinated:
                sanitized = re.sub(rf"\[(?:FACT:)?{bad_id}\]", "", sanitized).strip()
            return False, sanitized, f"Hallucinated citations rejected: {hallucinated}"

        return True, sanitized, "Validation passed"

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
