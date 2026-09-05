"""
PRIME-Factory Decision Engine v6.2 FINAL

Canonical decision engine - Single source of truth for all decisions.
FIXED: PdM Trigger now requires confirmed_anomaly + persistence + (HI/RUL/degradation).
"""

from __future__ import annotations

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field

import config


class DecisionCode:
    SCHEDULE_PDM = "SCHEDULE_PDM"
    MONITOR = "MONITOR"
    ELEVATE_INSPECTION = "ELEVATE_INSPECTION"
    CONTINUE_OPERATION = "CONTINUE_OPERATION"
    CONTROLLED_STOP = "CONTROLLED_STOP"
    EMERGENCY_MAINTENANCE = "EMERGENCY_MAINTENANCE"
    MAINTENANCE_IN_PROGRESS = "MAINTENANCE_IN_PROGRESS"
    RECOVERY_IN_PROGRESS = "RECOVERY_IN_PROGRESS"
    ENERGY_NOTICE = "ENERGY_NOTICE"


@dataclass
class Decision:
    """Complete decision record with evidence and recommendation."""
    decision_id: str
    timestamp: int
    machine_id: str
    current_state: str
    health_index: float
    rul_minutes: Optional[float]
    recommendation: str
    priority: str
    decision_code: str
    evidence_summary: Dict[str, Any]
    action_taken: Optional[str] = None
    action_timestamp: Optional[int] = None


class DecisionEngine:
    """
    Canonical Decision Engine.

    All decisions must go through this engine.
    Dashboard wrapper must call this, not duplicate logic.
    """

    def __init__(self):
        self.decision_history: List[Decision] = []
        self._decision_counter = 0

    def evaluate(
        self,
        machine_id: str,
        timestamp: int,
        current_state: str,
        health_index: float,
        rul_minutes: Optional[float],
        eci: float,
        is_confirmed_anomaly: bool,
        persistence_ratio: float = 0.0,
        production_units: int = 0,
        context: Optional[Dict[str, Any]] = None
    ) -> Decision:
        """
        Evaluate machine condition and generate a decision recommendation.
        This is the CANONICAL decision logic.
        """
        self._decision_counter += 1
        decision_id = f"DEC_{self._decision_counter:04d}"

        # Build evidence summary
        evidence_summary = {
            "state": current_state,
            "health_index": round(health_index, 1),
            "rul_minutes": rul_minutes if rul_minutes is not None else "N/A",
            "eci": round(eci, 4),
            "confirmed_anomaly": is_confirmed_anomaly,
            "persistence_ratio": round(persistence_ratio, 3),
            "production_units": production_units,
            "context": context or {}
        }

        # Determine recommendation, priority, and decision_code
        recommendation, priority, decision_code = self._make_decision(
            current_state=current_state,
            health_index=health_index,
            rul_minutes=rul_minutes,
            eci=eci,
            is_confirmed_anomaly=is_confirmed_anomaly,
            persistence_ratio=persistence_ratio,
            context=context
        )

        decision = Decision(
            decision_id=decision_id,
            timestamp=timestamp,
            machine_id=machine_id,
            current_state=current_state,
            health_index=health_index,
            rul_minutes=rul_minutes,
            recommendation=recommendation,
            priority=priority,
            decision_code=decision_code,
            evidence_summary=evidence_summary
        )

        self.decision_history.append(decision)
        return decision

    def _make_decision(
        self,
        current_state: str,
        health_index: float,
        rul_minutes: Optional[float],
        eci: float,
        is_confirmed_anomaly: bool,
        persistence_ratio: float = 0.0,
        context: Optional[Dict] = None
    ) -> tuple:
        """
        Core decision logic.

        Returns: (recommendation, priority, decision_code)
        """
        # ===== FAILED =====
        if current_state == config.STATE_FAILED:
            return (
                "EMERGENCY: Corrective maintenance required immediately. Machine has failed.",
                "CRITICAL",
                DecisionCode.EMERGENCY_MAINTENANCE
            )

        # ===== CRITICAL =====
        if current_state == config.STATE_CRITICAL:
            if rul_minutes is not None and rul_minutes <= 10:
                return (
                    f"URGENT: Controlled stop required. RUL = {rul_minutes:.0f} minutes. "
                    "Schedule corrective maintenance immediately.",
                    "CRITICAL",
                    DecisionCode.CONTROLLED_STOP
                )
            return (
                "CRITICAL: Condition is severe. Consider controlled stop or derating. "
                "Prepare for maintenance intervention.",
                "HIGH",
                DecisionCode.CONTROLLED_STOP
            )

        # ===== PREDICTIVE ALERT - PdM TRIGGER LOGIC =====
        # ===== FIXED: Requires confirmed_anomaly + persistence + (HI/RUL/degradation) =====
        if current_state == config.STATE_PREDICTIVE_ALERT:
            # Check if PdM should be triggered
            should_trigger = self._should_trigger_pdm(
                health_index=health_index,
                rul_minutes=rul_minutes,
                is_confirmed_anomaly=is_confirmed_anomaly,
                persistence_ratio=persistence_ratio,
                context=context
            )

            if should_trigger:
                rul_display = f"{rul_minutes:.0f}min" if rul_minutes is not None else "N/A"
                return (
                    f"PREDICTIVE: Execute PdM now. HI={health_index:.1f}, RUL={rul_display}. "
                    "Schedule 15-minute intervention.",
                    "HIGH",
                    DecisionCode.SCHEDULE_PDM
                )

            # ===== FIXED: If confirmed anomaly but not triggering, elevate inspection =====
            if is_confirmed_anomaly:
                rul_display = f"{rul_minutes:.0f}min" if rul_minutes is not None else "N/A"
                return (
                    f"PREDICTIVE ALERT: Anomaly confirmed (HI={health_index:.1f}, RUL={rul_display}). "
                    "Risk not yet critical. Elevate inspection frequency.",
                    "MEDIUM",
                    DecisionCode.ELEVATE_INSPECTION
                )

            # If not confirmed but in PREDICTIVE_ALERT state (shouldn't happen, but safe)
            rul_display = f"{rul_minutes:.0f}min" if rul_minutes is not None else "N/A"
            return (
                f"PREDICTIVE ALERT: Anomaly detected but not confirmed. HI={health_index:.1f}, RUL={rul_display}. "
                "Continue monitoring, await confirmation.",
                "MEDIUM",
                DecisionCode.MONITOR
            )

        # ===== WARNING =====
        if current_state == config.STATE_WARNING:
            return (
                "WARNING: Condition is degrading. Increase monitoring frequency. "
                "Inspect machine at next opportunity.",
                "MEDIUM",
                DecisionCode.ELEVATE_INSPECTION
            )

        # ===== DEGRADING =====
        if current_state == config.STATE_DEGRADING:
            return (
                "DEGRADING: Early signs of wear detected. Continue routine monitoring. "
                "Consider increasing inspection frequency.",
                "LOW",
                DecisionCode.MONITOR
            )

        # ===== MAINTENANCE / RECOVERY =====
        if current_state == config.STATE_MAINTENANCE:
            return (
                "MAINTENANCE: Machine is under service. Await recovery.",
                "MEDIUM",
                DecisionCode.MAINTENANCE_IN_PROGRESS
            )

        if current_state == config.STATE_RECOVERY:
            return (
                "RECOVERY: Post-maintenance stabilization in progress. "
                "Validate before returning to service.",
                "LOW",
                DecisionCode.RECOVERY_IN_PROGRESS
            )

        # ===== NORMAL =====
        if abs(eci) > config.DECISION_CONFIG.get("eci_deviation_threshold", 0.15):
            return (
                f"ENERGY NOTICE: ECI deviation detected ({eci:.3f}). "
                "Check for energy inefficiency or context change.",
                "LOW",
                DecisionCode.ENERGY_NOTICE
            )

        return (
            "NORMAL: All systems operating within nominal parameters. "
            "Continue standard operation.",
            "LOW",
            DecisionCode.CONTINUE_OPERATION
        )

    def _should_trigger_pdm(
        self,
        health_index: float,
        rul_minutes: Optional[float],
        is_confirmed_anomaly: bool,
        persistence_ratio: float = 0.0,
        context: Optional[Dict] = None
    ) -> bool:
        """
        PdM trigger condition.

        ===== FIXED: Now requires ALL of the following =====
        1. Confirmed anomaly
        2. Persistence >= threshold
        3. (HI <= threshold OR RUL <= threshold OR degradation >= threshold)

        This implements the full PRIME logic: 
        Anomaly → Persistence → Confirmation → Risk → Action
        """
        # ===== FIXED: Require confirmed anomaly =====
        if not is_confirmed_anomaly:
            return False

        # ===== FIXED: Require persistence =====
        if config.PDM_REQUIRE_PERSISTENCE:
            if persistence_ratio < config.PERSISTENCE_THRESHOLD:
                return False

        # ===== Check risk thresholds =====
        # HI trigger
        if health_index <= config.PDM_TRIGGER_HI:
            return True

        # RUL trigger
        if rul_minutes is not None and rul_minutes <= config.PDM_TRIGGER_RUL:
            return True

        # Degradation trigger (context-based)
        if context and context.get("degradation", 0.0) >= config.PDM_TRIGGER_DEGRADATION:
            return True

        # No trigger condition met
        return False

    # ---- Helper methods ----
    def get_decision_history(self) -> List[Decision]:
        return self.decision_history

    def get_recent_decisions(self, count: int = 10) -> List[Decision]:
        return self.decision_history[-count:] if self.decision_history else []

    def get_decisions_by_priority(self, priority: str) -> List[Decision]:
        return [d for d in self.decision_history if d.priority == priority.upper()]

    def get_decisions_by_machine(self, machine_id: str) -> List[Decision]:
        return [d for d in self.decision_history if d.machine_id == machine_id]

    def record_action(self, decision_id: str, action: str, timestamp: int):
        for decision in self.decision_history:
            if decision.decision_id == decision_id:
                decision.action_taken = action
                decision.action_timestamp = timestamp
                break

    def reset(self):
        self.decision_history = []
        self._decision_counter = 0


# ===== Helper Functions =====
def get_recommendation_from_state(state: str) -> str:
    """Quick lookup for state-based recommendations."""
    recommendations = {
        config.STATE_NORMAL: "Continue standard operation.",
        config.STATE_DEGRADING: "Increase monitoring frequency.",
        config.STATE_WARNING: "Schedule inspection at next opportunity.",
        config.STATE_PREDICTIVE_ALERT: "Plan maintenance intervention.",
        config.STATE_CRITICAL: "Prepare for controlled stop.",
        config.STATE_FAILED: "Emergency corrective maintenance required.",
        config.STATE_MAINTENANCE: "Await recovery from maintenance.",
        config.STATE_RECOVERY: "Validate before returning to service."
    }
    return recommendations.get(state, "Monitor condition.")


# ===== Dashboard Compatibility =====
def evaluate_decision_for_dashboard(
    machine_id: str,
    current_state: str,
    health_index: float,
    rul_minutes: int,
    is_confirmed_anomaly: bool,
    eci: float,
    penalty_contributions: dict,
    product_key: str,
    persistence_ratio: float = 0.0
) -> dict:
    """
    Dashboard compatibility function.
    Maps DecisionEngine output to dashboard expected format.
    """
    engine = DecisionEngine()
    rul = float(rul_minutes) if rul_minutes > 0 else None

    decision = engine.evaluate(
        machine_id=machine_id,
        timestamp=0,
        current_state=current_state,
        health_index=health_index,
        rul_minutes=rul,
        eci=eci,
        is_confirmed_anomaly=is_confirmed_anomaly,
        persistence_ratio=persistence_ratio
    )

    urgency_map = {
        "LOW": "NONE",
        "MEDIUM": "MEDIUM",
        "HIGH": "HIGH",
        "CRITICAL": "IMMEDIATE"
    }

    code_map = {
        DecisionCode.SCHEDULE_PDM: "SCHEDULE_PREDICTIVE_MAINTENANCE",
        DecisionCode.MONITOR: "MONITOR",
        DecisionCode.ELEVATE_INSPECTION: "ELEVATE_INSPECTION",
        DecisionCode.CONTINUE_OPERATION: "CONTINUE_OPERATION",
        DecisionCode.CONTROLLED_STOP: "CONTROLLED_STOP",
        DecisionCode.EMERGENCY_MAINTENANCE: "EMERGENCY_MAINTENANCE",
        DecisionCode.ENERGY_NOTICE: "ENERGY_NOTICE"
    }

    code = code_map.get(decision.decision_code, "CONTINUE_OPERATION")
    urgency = urgency_map.get(decision.priority, "LOW")

    return {
        "decision_code": code,
        "title": decision.recommendation.split(".")[0] if "." in decision.recommendation else decision.recommendation[:60],
        "urgency": urgency,
        "machine_id": machine_id,
        "current_state": current_state,
        "health_index": health_index,
        "rul_display": f"{rul_minutes} min" if rul_minutes > 0 else "RUL Nominal / Stable",
        "recommended_action": decision.recommendation,
        "consequence_of_inaction": "Monitor condition" if decision.priority == "LOW" else "Possible failure if not addressed",
        "operating_context": {
            "product": product_key,
            "eci_deviation_pct": f"{eci * 100:+.1f}%",
            "persistence_confirmed": "YES" if is_confirmed_anomaly else "NO"
        },
        "penalty_contributions": penalty_contributions or {}
    }


# ===== Static method for Phase 3 test =====
@staticmethod
def evaluate_decision(
    machine_id: str,
    current_state: str,
    health_index: float,
    rul_minutes: int,
    is_confirmed_anomaly: bool,
    eci: float,
    penalty_contributions: dict,
    product_key: str,
    persistence_ratio: float = 0.0
) -> dict:
    return evaluate_decision_for_dashboard(
        machine_id=machine_id,
        current_state=current_state,
        health_index=health_index,
        rul_minutes=rul_minutes,
        is_confirmed_anomaly=is_confirmed_anomaly,
        eci=eci,
        penalty_contributions=penalty_contributions,
        product_key=product_key,
        persistence_ratio=persistence_ratio
    )

DecisionEngine.evaluate_decision = evaluate_decision