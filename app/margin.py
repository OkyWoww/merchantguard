"""Statistical Margin Recovery Engine: Win Probability & Expected Value (EV) Calculator."""

from __future__ import annotations
from typing import Dict, Any, Tuple
from app.schemas import DisputeCase, DecisionAction, DecisionResult, GateRuleEvaluation


class MarginEngine:
    def __init__(self, config: Dict[str, Any] | None = None):
        self.config = config or {}
        me_cfg = self.config.get("margin_engine", {})
        self.default_dispute_fee = float(me_cfg.get("default_dispute_fee", 15.0))
        self.min_ev_hurdle = float(me_cfg.get("min_ev_hurdle_usd", 0.0))
        self.partial_refund_fraction = float(me_cfg.get("partial_refund_fraction", 0.35))

        self.base_win_rates = me_cfg.get(
            "base_win_rates",
            {
                "ITEM_NOT_RECEIVED": 0.65,
                "DAMAGED": 0.40,
                "NOT_AS_DESCRIBED": 0.35,
                "UNAUTHORIZED_CHARGE": 0.50,
            },
        )
        self.evidence_weights = me_cfg.get(
            "evidence_weights",
            {
                "has_gps_geo_match": 0.25,
                "has_valid_signature": 0.20,
                "past_window_expired": 0.30,
                "zero_tracking_events": -0.45,
            },
        )

    def calculate_p_win(self, case: DisputeCase, rule_evaluations: list[GateRuleEvaluation]) -> float:
        """Computes statistical P(Win) using empirical baseline and carrier evidence features."""
        # Baseline probability from category
        reason_norm = case.claimed_reason.upper().replace(" ", "_")
        p_base = self.base_win_rates.get(reason_norm, 0.50)

        # Evidence adjustments
        has_geo = any(ev.geo_match for ev in case.courier_events)
        has_sig = any(ev.signature_present for ev in case.courier_events)
        has_events = len(case.courier_events) > 0

        # Check if R-001 (window expired) failed -> strong merchant advantage
        window_expired = any(r.rule_id == "R-001" and not r.passed for r in rule_evaluations)

        delta = 0.0
        if has_geo:
            delta += self.evidence_weights.get("has_gps_geo_match", 0.25)
        if has_sig:
            delta += self.evidence_weights.get("has_valid_signature", 0.20)
        if window_expired:
            delta += self.evidence_weights.get("past_window_expired", 0.30)
        if not has_events:
            delta += self.evidence_weights.get("zero_tracking_events", -0.45)

        p_win = max(0.05, min(0.98, p_base + delta))
        return round(p_win, 3)

    def calculate_expected_margin_recovery(
        self, case: DisputeCase, p_win: float
    ) -> float:
        """
        EV = P(Win) * (Unit Margin + Dispute Fee Saved) - (1 - P(Win)) * Dispute Fee
        This represents the net incremental margin relative to giving an immediate refund.
        """
        fee = case.dispute_fee if case.dispute_fee > 0 else self.default_dispute_fee
        margin = case.unit_margin

        # When winning: Merchant retains unit margin and does not pay/gets refund of dispute fee
        # When losing: Merchant loses unit margin AND loses dispute fee
        ev = (p_win * (margin + fee)) - ((1.0 - p_win) * fee)
        return round(ev, 2)

    def compute_final_decision(
        self,
        case: DisputeCase,
        gate_action: DecisionAction,
        gate_reason: str,
        gate_status: str,
        rule_evaluations: list[GateRuleEvaluation],
    ) -> DecisionResult:
        p_win = self.calculate_p_win(case, rule_evaluations)
        ev = self.calculate_expected_margin_recovery(case, p_win)

        settlement_offer = None
        action = gate_action
        reason_code = gate_reason

        # If gate recommended CONTEST, but expected value EV <= min_hurdle,
        # protect merchant against negative-EV arbitration trap
        if action == DecisionAction.CONTEST and ev <= self.min_ev_hurdle:
            action = DecisionAction.ACCEPT_REFUND
            reason_code = "R004_NEGATIVE_EV_AVOIDANCE"
            gate_status = "OVERRIDDEN_BY_MARGIN"

        if action == DecisionAction.PARTIAL_REFUND:
            settlement_offer = round(case.order_amount * self.partial_refund_fraction, 2)

        return DecisionResult(
            case_id=case.case_id,
            action=action,
            reason_code=reason_code,
            p_win=p_win,
            expected_margin_recovery=ev,
            gate_status=gate_status,
            rule_evaluations=rule_evaluations,
            settlement_offer=settlement_offer,
        )
