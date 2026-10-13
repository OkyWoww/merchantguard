"""Deterministic Policy Gate: Authoritative Rule Engine (Rules R-001 to R-006).

INVARIANT: The LLM is NEVER the sole decider. Pure Python rules handle gate validations.
No hallucinations or external prompts can bypass these deterministic rules.

Rule Specification (docs/specs/rule_3.md §B):
- R-001: claim_date - delivery_date > return_window_days -> EXPIRED_WINDOW (auto-reject / contest)
- R-002: delivery confirmed with signature/photo AND geo match -> DELIVERY_CONFIRMED (contest)
- R-003: delivered but courier note contradicts proof (e.g., unattended) -> NEEDS_HUMAN / AMBIGUOUS_EVIDENCE
- R-004: amount >= high_value_threshold AND evidence weak -> NEEDS_HUMAN / HIGH_VALUE_WEAK_EVIDENCE
- R-005: dispute_fee >= recoverable margin -> route to margin engine, bias ACCEPT_REFUND
- R-006: missing required fields or tracking data -> NEEDS_HUMAN / INCOMPLETE_CASE
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
        self.high_value_threshold = float(
            pg_cfg.get("high_value_threshold", pg_cfg.get("high_value_cutoff", 250.0))
        )
        self.high_value_cutoff = self.high_value_threshold
        self.minimum_order_value_to_contest = float(
            pg_cfg.get("minimum_order_value_to_contest", 10.0)
        )
        self.contradiction_keywords = [
            kw.lower()
            for kw in pg_cfg.get(
                "courier_contradiction_keywords",
                ["unattended", "porch", "gate", "outside", "driveway", "lobby", "left near", "no answer"],
            )
        ]
        self.required_fields = list(
            pg_cfg.get(
                "required_fields",
                ["order_id", "claim_date", "delivery_date", "order_amount"],
            )
        )
        self.partial_damage_categories = set(
            pg_cfg.get(
                "partial_damage_categories",
                ["DAMAGED", "PARTIAL_TRANSIT_DEFECT", "MINOR_COSMETIC_DAMAGE"],
            )
        )
        self.escalate_on_missing_tracking = bool(
            pg_cfg.get("escalate_on_missing_tracking", True)
        )
        self.require_carrier_geo_match = bool(
            pg_cfg.get("require_carrier_geo_match", True)
        )

    def _calculate_days_elapsed(self, delivery_date_str: str, claim_date_str: str) -> float:
        try:
            d_deliv = datetime.fromisoformat(delivery_date_str.replace("Z", "+00:00"))
            d_claim = datetime.fromisoformat(claim_date_str.replace("Z", "+00:00"))
            return (d_claim - d_deliv).total_seconds() / 86400.0
        except Exception:
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

        # ------------------------------------------------------------------
        # Rule R-006: Missing required fields or carrier tracking milestones
        # ------------------------------------------------------------------
        missing_fields: List[str] = []
        for field in self.required_fields:
            val = getattr(case, field, None)
            if val is None or (isinstance(val, str) and not val.strip()):
                missing_fields.append(field)

        has_events = len(case.courier_events) > 0
        has_delivered_event = any(
            "DELIVERED" in ev.status.upper() for ev in case.courier_events
        )

        r006_passed = (len(missing_fields) == 0) and (
            has_events and has_delivered_event if self.escalate_on_missing_tracking else True
        )
        evaluations.append(
            GateRuleEvaluation(
                rule_id="R-006",
                rule_name="Case Completeness & Required Fields",
                passed=r006_passed,
                details=(
                    "All required dispute fields and carrier milestones present."
                    if r006_passed
                    else (
                        f"Missing required fields: {', '.join(missing_fields)}"
                        if missing_fields
                        else "Missing tracking milestones or delivery confirmation."
                    )
                ),
                trigger_action=DecisionAction.NEEDS_HUMAN if not r006_passed else None,
            )
        )
        if not r006_passed:
            reason = "R006_INCOMPLETE_CASE" if missing_fields else "R006_COURIER_ANOMALY"
            return (DecisionAction.NEEDS_HUMAN, reason, "ESCALATED", evaluations)

        # ------------------------------------------------------------------
        # Rule R-001: Return Window Expired (claim_date - delivery_date > return_window_days)
        # ------------------------------------------------------------------
        days_elapsed = self._calculate_days_elapsed(case.delivery_date, case.claim_date)
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

        # ------------------------------------------------------------------
        # Rule R-003: Courier note contradicts proof (e.g., left unattended)
        # ------------------------------------------------------------------
        contradiction_note: str | None = None
        for ev in case.courier_events:
            if ev.note:
                note_lower = ev.note.lower()
                for kw in self.contradiction_keywords:
                    if kw in note_lower:
                        contradiction_note = ev.note
                        break
            if contradiction_note:
                break

        r003_passed = contradiction_note is None
        evaluations.append(
            GateRuleEvaluation(
                rule_id="R-003",
                rule_name="Courier Proof Consistency",
                passed=r003_passed,
                details=(
                    "Courier notes consistent with confirmed delivery."
                    if r003_passed
                    else f"Courier note contradicts secure handover: '{contradiction_note}'."
                ),
                trigger_action=DecisionAction.NEEDS_HUMAN if not r003_passed else None,
            )
        )
        if not r003_passed:
            return (
                DecisionAction.NEEDS_HUMAN,
                "R003_AMBIGUOUS_EVIDENCE",
                "ESCALATED",
                evaluations,
            )

        # ------------------------------------------------------------------
        # Rule R-004: Amount >= high_value_threshold AND evidence weak
        # ------------------------------------------------------------------
        has_geo_match = any(ev.geo_match for ev in case.courier_events)
        has_signature = any(ev.signature_present for ev in case.courier_events)
        evidence_weak = (not has_signature) or (self.require_carrier_geo_match and not has_geo_match)

        r004_passed = not (case.order_amount >= self.high_value_threshold and evidence_weak)
        evaluations.append(
            GateRuleEvaluation(
                rule_id="R-004",
                rule_name="High-Value Custody Verification",
                passed=r004_passed,
                details=(
                    f"Order amount ${case.order_amount:.2f} satisfies custody risk threshold."
                    if r004_passed
                    else f"Order ${case.order_amount:.2f} >= ${self.high_value_threshold:.2f} threshold without physical signature."
                ),
                trigger_action=DecisionAction.NEEDS_HUMAN if not r004_passed else None,
            )
        )
        if not r004_passed:
            return (
                DecisionAction.NEEDS_HUMAN,
                "R004_HIGH_VALUE_WEAK_EVIDENCE",
                "ESCALATED",
                evaluations,
            )

        # ------------------------------------------------------------------
        # Rule R-005: Dispute fee >= recoverable margin (Economic fee trap)
        # ------------------------------------------------------------------
        r005_passed = not (
            case.dispute_fee >= case.unit_margin
            or case.order_amount <= case.dispute_fee
            or case.unit_margin <= 0.0
        )
        evaluations.append(
            GateRuleEvaluation(
                rule_id="R-005",
                rule_name="Economic Fee Trap Check",
                passed=r005_passed,
                details=(
                    f"Unit margin ${case.unit_margin:.2f} exceeds dispute fee ${case.dispute_fee:.2f}."
                    if r005_passed
                    else f"Dispute fee ${case.dispute_fee:.2f} >= unit margin ${case.unit_margin:.2f}. Biasing refund."
                ),
                trigger_action=DecisionAction.ACCEPT_REFUND if not r005_passed else None,
            )
        )
        if not r005_passed:
            return (
                DecisionAction.ACCEPT_REFUND,
                "R005_ECONOMIC_FEE_TRAP",
                "TRIGGERED",
                evaluations,
            )

        # ------------------------------------------------------------------
        # Partial Damage Category Settlement
        # ------------------------------------------------------------------
        is_partial_damage = case.claimed_reason.upper() in self.partial_damage_categories
        if is_partial_damage:
            evaluations.append(
                GateRuleEvaluation(
                    rule_id="PARTIAL_DAMAGE",
                    rule_name="Partial Defect Settlement Routing",
                    passed=False,
                    details=f"Claim category '{case.claimed_reason}' qualifies for deterministic partial settlement.",
                    trigger_action=DecisionAction.PARTIAL_REFUND,
                )
            )
            return (
                DecisionAction.PARTIAL_REFUND,
                "R005_PARTIAL_DEFECT_OFFER",
                "TRIGGERED",
                evaluations,
            )

        # ------------------------------------------------------------------
        # Rule R-002: Delivery confirmed with signature AND geo match
        # ------------------------------------------------------------------
        r002_passed = has_geo_match and has_signature
        evaluations.append(
            GateRuleEvaluation(
                rule_id="R-002",
                rule_name="Objective Carrier Proof (Signature + Geo)",
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
                "R002_DELIVERY_CONFIRMED",
                "PASSED",
                evaluations,
            )

        if has_geo_match:
            return (
                DecisionAction.CONTEST,
                "STANDARD_GEO_PROOF",
                "PASSED",
                evaluations,
            )

        return (
            DecisionAction.NEEDS_HUMAN,
            "AMBIGUOUS_EVIDENCE_ROUTE",
            "ESCALATED",
            evaluations,
        )
