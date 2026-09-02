"""
PRIME-Factory Decision Engine v6.0
Converts confirmed evidence/state into explainable recommendations (Section 15).
"""

import config
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field


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
    priority: str  # LOW, MEDIUM, HIGH, CRITICAL
    evidence_summary: Dict[str, Any]
    action_taken: Optional[str] = None
    action_timestamp: Optional[int] = None


class DecisionEngine:
    """
    Decision engine that consumes confirmed state + HI/RUL + evidence + production constraints.
    Implements the decision logic from Section 15 of the constitution.
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
        production_units: int = 0,
        context: Dict[str, Any] = None
    ) -> Decision:
        """
        Evaluate machine condition and generate a decision recommendation.
        Follows the decision hierarchy from Section 15.
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
            "production_units": production_units,
            "context": context or {}
        }
        
        # Determine recommendation based on state and evidence
        recommendation, priority = self._make_decision(
            current_state=current_state,
            health_index=health_index,
            rul_minutes=rul_minutes,
            eci=eci,
            is_confirmed_anomaly=is_confirmed_anomaly,
            production_units=production_units
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
        production_units: int
    ) -> tuple:
        """
        Core decision logic based on state and evidence.
        Returns (recommendation, priority).
        """
        
        # ===== Critical / Failure States (Highest Priority) =====
        if current_state == config.STATE_FAILED:
            return (
                "EMERGENCY: Corrective maintenance required immediately. Machine has failed.",
                "CRITICAL"
            )
        
        if current_state == config.STATE_CRITICAL:
            if rul_minutes is not None and rul_minutes <= 10:
                return (
                    f"URGENT: Controlled stop required. RUL = {rul_minutes:.0f} minutes. "
                    "Schedule corrective maintenance immediately.",
                    "CRITICAL"
                )
            return (
                "CRITICAL: Condition is severe. Consider controlled stop or derating. "
                "Prepare for maintenance intervention.",
                "HIGH"
            )
        
        # ===== Predictive Alert (Actionable) =====
        if current_state == config.STATE_PREDICTIVE_ALERT:
            if rul_minutes is not None and rul_minutes <= 30:
                return (
                    f"PREDICTIVE: Maintenance should be planned. RUL = {rul_minutes:.0f} minutes. "
                    "Schedule 15-minute intervention.",
                    "HIGH"
                )
            return (
                "PREDICTIVE ALERT: Actionable anomaly detected. "
                "Schedule maintenance within the next shift.",
                "MEDIUM"
            )
        
        # ===== Warning =====
        if current_state == config.STATE_WARNING:
            return (
                "WARNING: Condition is degrading. Increase monitoring frequency. "
                "Inspect machine at next opportunity.",
                "MEDIUM"
            )
        
        # ===== Degrading =====
        if current_state == config.STATE_DEGRADING:
            return (
                "DEGRADING: Early signs of wear detected. Continue routine monitoring. "
                "Consider increasing inspection frequency.",
                "LOW"
            )
        
        # ===== Maintenance / Recovery =====
        if current_state == config.STATE_MAINTENANCE:
            return (
                "MAINTENANCE: Machine is under service. Await recovery.",
                "MEDIUM"
            )
        
        if current_state == config.STATE_RECOVERY:
            return (
                "RECOVERY: Post-maintenance stabilization in progress. "
                "Validate before returning to service.",
                "LOW"
            )
        
        # ===== Normal =====
        # Check for energy concerns even in normal state
        if abs(eci) > config.DECISION_CONFIG.get("eci_deviation_threshold", 0.15):
            return (
                f"ENERGY NOTICE: ECI deviation detected ({eci:.3f}). "
                "Check for energy inefficiency or context change.",
                "LOW"
            )
        
        return (
            "NORMAL: All systems operating within nominal parameters. Continue standard operation.",
            "LOW"
        )
    
    # ===== NEW: Static method for dashboard compatibility =====
    @staticmethod
    def evaluate_decision(
        machine_id: str,
        current_state: str,
        health_index: float,
        rul_minutes: int,
        is_confirmed_anomaly: bool,
        eci: float,
        penalty_contributions: dict,
        product_key: str
    ) -> dict:
        """
        Static method for dashboard compatibility.
        Mirrors the interface of control.decision_engine.DecisionEngine.
        """
        # Map state to decision
        if current_state in [config.STATE_MAINTENANCE, config.STATE_RECOVERY]:
            decision_code = "IN_SERVICE"
            title = "Maintenance / Post-Repair Stabilization"
            urgency = "LOW"
            recommended_action = "Allow machine to complete stabilization cycle"
            consequence_of_inaction = "N/A — Asset currently being serviced/recovering"
        elif health_index <= config.HI_THRESHOLDS["CRITICAL"] or current_state == config.STATE_CRITICAL:
            decision_code = "CONTROLLED_STOP"
            title = "CRITICAL: Immediate Controlled Shutdown Required"
            urgency = "IMMEDIATE"
            recommended_action = "Execute Controlled Stop to prevent catastrophic bearing failure"
            consequence_of_inaction = "Impending line breakdown within ~15 min (75-min downtime, $350/hr penalty)"
        elif current_state == config.STATE_PREDICTIVE_ALERT or (health_index <= config.HI_THRESHOLDS["MONITOR"] and is_confirmed_anomaly):
            decision_code = "SCHEDULE_PREDICTIVE_MAINTENANCE"
            title = "PREDICTIVE ACTION: Schedule 15-min Targeted Intervention"
            urgency = "HIGH"
            recommended_action = "Execute 15-min Planned Predictive Maintenance now"
            consequence_of_inaction = "Bearing wear will progress to critical failure, causing 5x downtime and scrap losses"
        elif current_state == config.STATE_WARNING or abs(eci) > 0.08:
            decision_code = "ELEVATE_INSPECTION"
            title = "WARNING: Elevated Energy / Mechanical Drift"
            urgency = "MEDIUM"
            recommended_action = "Inspect lubrication and thermal dissipation on next scheduled stop"
            consequence_of_inaction = "Gradual efficiency loss and accelerated mechanical degradation"
        else:
            decision_code = "CONTINUE_OPERATION"
            title = "NORMAL: Healthy Baseline Operation"
            urgency = "NONE"
            recommended_action = "Continue standard production plan"
            consequence_of_inaction = "None — Asset operating within optimal nominal bounds"

        return {
            "decision_code": decision_code,
            "title": title,
            "urgency": urgency,
            "machine_id": machine_id,
            "current_state": current_state,
            "health_index": health_index,
            "rul_display": f"{rul_minutes} min" if (rul_minutes is not None and rul_minutes > 0) else "RUL Nominal / Stable",
            "recommended_action": recommended_action,
            "consequence_of_inaction": consequence_of_inaction,
            "operating_context": {
                "product": product_key,
                "eci_deviation_pct": f"{eci * 100:+.1f}%",
                "persistence_confirmed": "YES (5/5 Samples)" if is_confirmed_anomaly else "NO (Transient / Normal)"
            },
            "penalty_contributions": penalty_contributions
        }
    
    def get_decision_history(self) -> List[Decision]:
        """Return all decisions made."""
        return self.decision_history
    
    def get_recent_decisions(self, count: int = 10) -> List[Decision]:
        """Return the most recent N decisions."""
        return self.decision_history[-count:] if self.decision_history else []
    
    def get_decisions_by_priority(self, priority: str) -> List[Decision]:
        """Filter decisions by priority level."""
        return [d for d in self.decision_history if d.priority == priority.upper()]
    
    def get_decisions_by_machine(self, machine_id: str) -> List[Decision]:
        """Filter decisions by machine ID."""
        return [d for d in self.decision_history if d.machine_id == machine_id]
    
    def record_action(self, decision_id: str, action: str, timestamp: int):
        """Record the action taken for a decision."""
        for decision in self.decision_history:
            if decision.decision_id == decision_id:
                decision.action_taken = action
                decision.action_timestamp = timestamp
                break
    
    def reset(self):
        """Clear all decision history."""
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