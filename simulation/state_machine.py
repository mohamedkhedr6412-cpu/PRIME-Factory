"""
PRIME-Factory Canonical 8-State Asset State Machine Engine v6.0
Governs asset operational transitions, predictive alert hysteresis, maintenance duration,
and post-repair stabilization lifecycles (Section 6).
"""

import config

class AssetStateMachine:
    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        self.current_state = config.STATE_NORMAL
        self.state_history = []
        self.recovery_timer = 0
        self.repair_timer = 0

    def update_state(
        self,
        degradation: float,
        health_index: float,
        is_confirmed_anomaly: bool,
        in_maintenance: bool = False,
        maintenance_duration: int = 15
    ) -> str:
        """
        Updates machine operational state along the canonical causal chain:
        NORMAL -> DEGRADING -> WARNING -> PREDICTIVE_ALERT -> CRITICAL -> FAILED -> MAINTENANCE -> RECOVERY -> NORMAL
        """
        if in_maintenance:
            self.current_state = config.STATE_MAINTENANCE
            self.repair_timer = maintenance_duration
            self.state_history.append(self.current_state)
            return self.current_state

        if self.current_state == config.STATE_MAINTENANCE:
            self.current_state = config.STATE_RECOVERY
            self.recovery_timer = 15  # 15-minute physical stabilization phase
            self.state_history.append(self.current_state)
            return self.current_state

        if self.current_state == config.STATE_RECOVERY:
            self.recovery_timer -= 1
            if self.recovery_timer <= 0:
                self.current_state = config.STATE_NORMAL
            self.state_history.append(self.current_state)
            return self.current_state

        # Continuous Dynamic Condition Evaluation
        if degradation >= 0.75:
            self.current_state = config.STATE_FAILED
        elif health_index <= config.HI_THRESHOLDS["CRITICAL"] or degradation >= 0.50:
            self.current_state = config.STATE_CRITICAL
        elif health_index <= config.HI_THRESHOLDS["MONITOR"] and is_confirmed_anomaly:
            self.current_state = config.STATE_PREDICTIVE_ALERT
        elif health_index <= config.HI_THRESHOLDS["HEALTHY"] or degradation >= 0.15:
            self.current_state = config.STATE_WARNING
        elif degradation > 0.0:
            self.current_state = config.STATE_DEGRADING
        else:
            self.current_state = config.STATE_NORMAL

        self.state_history.append(self.current_state)
        return self.current_state

    @staticmethod
    def get_state_badge(state: str) -> dict:
        """Returns color badges and direct operational directives for dashboard rendering."""
        badges = {
            "NORMAL": {
                "color": "#28a745", 
                "label": "NORMAL (Healthy)", 
                "action": "Continue Standard Operation"
            },
            "DEGRADING": {
                "color": "#17a2b8", 
                "label": "DEGRADING (Early Drift)", 
                "action": "Routine Monitoring"
            },
            "WARNING": {
                "color": "#ffc107", 
                "label": "WARNING (Inspection Needed)", 
                "action": "Elevate Diagnostics"
            },
            "PREDICTIVE_ALERT": {
                "color": "#fd7e14", 
                "label": "PREDICTIVE ALERT (Actionable)", 
                "action": "Schedule 15-min Intervention"
            },
            "CRITICAL": {
                "color": "#dc3545", 
                "label": "CRITICAL (Severe Risk)", 
                "action": "Immediate Controlled Stop / Derate"
            },
            "FAILED": {
                "color": "#6c757d", 
                "label": "FAILED (Breakdown)", 
                "action": "Emergency Corrective Repair"
            },
            "MAINTENANCE": {
                "color": "#6f42c1", 
                "label": "MAINTENANCE (Under Repair)", 
                "action": "Repair In Progress"
            },
            "RECOVERY": {
                "color": "#20c997", 
                "label": "RECOVERY (Post-Repair)", 
                "action": "Stabilizing Phase"
            }
        }
        return badges.get(state, badges["NORMAL"])