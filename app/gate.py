"""Deterministic Policy Gate: Authoritative Rule Engine (Rules R-001 to R-006).

INVARIANT: The LLM is NEVER the sole decider. Pure Python rules handle gate validations.
No hallucinations or external prompts can bypass these deterministic rules.
"""

from __future__ import annotations
from datetime import datetime
from typing import Dict, Any, List, Tuple
from app.schemas import DisputeCase, DecisionAction, GateRuleEvaluation


class PolicyGate:
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        pg_cfg = self.config.get("policy_gate", {})
        self.return_window_days = float(pg_cfg.get("return_window_days", 14))
        self.high_value_cutoff = float(pg_cfg.get("high_value_cutoff", 250.0))
        self.partial_damage_categories = set(
            pg_cfg.get(
                "partial_damage_categories",
                ["DAMAGED", "PARTIAL_TRANSIT_DEFECT", "MINOR_COSMETIC_DAMAGE"],
            )
        )

    def _calculate_days_elapsed(self, delivery_date_str: str, claim_date_str: str) -> float:
        try:
            d_deliv = datetime.fromisoformat(delivery_date_str.replace("Z", "+00:00"))
            d_claim = datetime.fromisoformat(claim_date_str.replace("Z", "+00:00"))
            return (d_claim - d_deliv).total_seconds() / 86400.0
        except Exception:
            # Fallback for plain YYYY-MM-DD
            try:
                d_deliv = datetime.strptime(delivery_date_str[:10], "%Y-%m-%d")
                d_claim = datetime.strptime(claim_date_str[:10], "%Y-%m-%d")
                return float((d_claim - d_deliv).days)
            except Exception:
                return 0.0

    def evaluate(self, case: DisputeCase) -> Tuple[DecisionAction, str, str, List[GateRuleEvaluation]]:
        """
        Evaluates the dispute against rules R-001 through R-006.
        Returns: (DecisionAction, reason_code, gate_status, List[GateRuleEvaluation])
        """
        evaluations: List[GateRuleEvaluation] = []
        days_elapsed = self._calculate_days_elapsed(case.delivery_date, case.claim_date)

        has_geo_match = any(ev.geo_match for ev in case.courier_events)
        has_signature = any(ev.signature_present for ev in case.courier_events)
        has_delivered_event = any(
            "DELIVERED" in ev.status.upper() for ev in case.courier_events
        )

        # Rule R-001: Return Window Bypass / Expired
        r001_passed = days_elapsed <= self.return_window_days
        evaluations.append(
            GateRuleEvaluation(
                rule_id="R-001",
                rule_name="Return Window Compliance",
                passed=r001_passed,
                details=f"{days_elapsed:.1f} days elapsed (Allowed threshold: {self.return_window_days} days).",
                trigger_action=DecisionAction.CONTEST if not r001_passed else None,
            )
        )
        if not r001_passed:
            return (
                DecisionAction.CONTEST,
                "R001_WINDOW_EXPIRED",
                "TRIGGERED",
                evaluations,
            )

        # Rule R-006: Courier Anomaly / Missing Carrier Data
        r006_passed = len(case.courier_events) > 0 and has_delivered_event
        evaluations.append(
            GateRuleEvaluation(
                rule_id="R-006",
                rule_name="Courier Milestone Completeness",
                passed=r006_passed,
                details=(
                    "Carrier tracking complete and delivered status confirmed."
                    if r006_passed
                    else "Missing tracking milestones or delivery confirmation."
                ),
                trigger_action=DecisionAction.NEEDS_HUMAN if not r006_passed else None,
            )
        )
        if not r006_passed:
            return (
                DecisionAction.NEEDS_HUMAN,
                "R006_COURIER_ANOMALY",
                "ESCALATED",
                evaluations,
            )

        # Rule R-003: High-Value Item Escalate (Value > Cutoff without signature)
        r003_passed = not (case.order_amount > self.high_value_cutoff and not has_signature)
        evaluations.append(
            GateRuleEvaluation(
                rule_id="R-003",
                rule_name="High-Value Custody Verification",
                passed=r003_passed,
                details=(
                    f"Order amount ${case.order_amount:.2f} satisfies signature protocol."
                    if r003_passed
                    else f"Order ${case.order_amount:.2f} exceeds ${self.high_value_cutoff:.2f} threshold without physical signature."
                ),
                trigger_action=DecisionAction.NEEDS_HUMAN if not r003_passed else None,
            )
        )
        if not r003_passed:
            return (
                DecisionAction.NEEDS_HUMAN,
                "R003_HIGH_VALUE_UNSIGNED",
                "ESCALATED",
                evaluations,
            )

        # Rule R-004: Economic Fee Trap Check
        # If the dispute fee alone exceeds the order margin or order amount, contesting is economically irrational
        r004_passed = case.order_amount > case.dispute_fee and case.unit_margin > 0.0
        evaluations.append(
            GateRuleEvaluation(
                rule_id="R-004",
                rule_name="Economic Fee Trap Check",
                passed=r004_passed,
                details=(
                    f"Unit margin ${case.unit_margin:.2f} exceeds dispute fee ${case.dispute_fee:.2f}."
                    if r004_passed
                    else f"Dispute fee ${case.dispute_fee:.2f} exceeds recovery potential (${case.unit_margin:.2f})."
                ),
                trigger_action=DecisionAction.ACCEPT_REFUND if not r004_passed else None,
            )
        )
        if not r004_passed:
            return (
                DecisionAction.ACCEPT_REFUND,
                "R004_ECONOMIC_FEE_TRAP",
                "TRIGGERED",
                evaluations,
            )

        # Rule R-005: Partial Damage Settlement
        is_partial_damage = case.claimed_reason.upper() in self.partial_damage_categories
        evaluations.append(
            GateRuleEvaluation(
                rule_id="R-005",
                rule_name="Partial Defect Settlement Routing",
                passed=not is_partial_damage,
                details=(
                    "Full custody or non-damage dispute claim."
                    if not is_partial_damage
                    else f"Claim category '{case.claimed_reason}' qualifies for deterministic partial settlement."
                ),
                trigger_action=DecisionAction.PARTIAL_REFUND if is_partial_damage else None,
            )
        )
        if is_partial_damage:
            return (
                DecisionAction.PARTIAL_REFUND,
                "R005_PARTIAL_DEFECT_OFFER",
                "TRIGGERED",
                evaluations,
            )

        # Rule R-002: Verified Signature + Geo Match
        r002_passed = has_geo_match and has_signature
        evaluations.append(
            GateRuleEvaluation(
                rule_id="R-002",
                rule_name="Objective Carrier Proof (Signature + GPS)",
                passed=r002_passed,
                details=(
                    "Both GPS coordinates match delivery address AND physical signature present."
                    if r002_passed
                    else f"Carrier evidence: GPS match={has_geo_match}, Signature={has_signature}."
                ),
                trigger_action=DecisionAction.CONTEST if r002_passed else None,
            )
        )
        if r002_passed:
            return (
                DecisionAction.CONTEST,
                "R002_VERIFIED_SIGNATURE_GEO",
                "PASSED",
                evaluations,
            )

        # If carrier data is partially present (e.g., GPS match but no signature under threshold)
        if has_geo_match:
            return (
                DecisionAction.CONTEST,
                "STANDARD_GEO_PROOF",
                "PASSED",
                evaluations,
            )

        # Default ambiguity escalation
        return (
            DecisionAction.NEEDS_HUMAN,
            "AMBIGUOUS_EVIDENCE_ROUTE",
            "ESCALATED",
            evaluations,
        )
