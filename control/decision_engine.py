"""
PRIME-Factory Decision & Explainability Engine v4.2
Generates operational directives, urgency levels, and Decision Trace cards based on causal evidence (Section 8).
"""

import config

class DecisionEngine:
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
        """Evaluates causal evidence to generate actionable operational directives."""
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