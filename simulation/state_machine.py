"""
PRIME-Factory Canonical 8-State Asset State Machine Engine v6.2
Governs asset operational transitions, predictive alert hysteresis, maintenance duration,
and post-repair stabilization lifecycles (Section 6).

FIXED: Hysteresis now correctly tracks candidate states before transition.
FIXED: PREDICTIVE_ALERT now uses PREDICTIVE_ALERT_HI_THRESHOLD (65.0) instead of MONITOR (50.0).
"""

import config


class AssetStateMachine:
    def __init__(self, machine_id: str):
        self.machine_id = machine_id
        self.current_state = config.STATE_NORMAL
        self.state_history = []
        self.recovery_timer = 0
        self.repair_timer = 0
        self.degradation_history = []
        self.health_history = []

        # Candidate tracking for hysteresis
        self._candidate_state = None
        self._candidate_count = 0

    def _calculate_target_state(
        self,
        degradation: float,
        health_index: float,
        is_confirmed_anomaly: bool
    ) -> str:
        """
        Calculate target state without applying hysteresis.
        Pure logic based on current values.
        """
        # Emergency / failure states (override everything)
        if degradation >= 0.75:
            return config.STATE_FAILED

        # Critical: Very low health or severe degradation
        if health_index <= config.HI_THRESHOLDS["CRITICAL"] or degradation >= 0.50:
            return config.STATE_CRITICAL

        # FIXED: Predictive Alert - Use PREDICTIVE_ALERT_HI_THRESHOLD
        # This aligns with PDM_TRIGGER_HI (65.0) for earlier intervention
        if health_index <= config.PREDICTIVE_ALERT_HI_THRESHOLD and is_confirmed_anomaly:
            return config.STATE_PREDICTIVE_ALERT

        # Warning: Degrading health with some degradation
        if health_index <= config.HI_THRESHOLDS["HEALTHY"] or degradation >= 0.15:
            return config.STATE_WARNING

        # Degrading: Early signs of degradation
        if degradation > 0.0:
            return config.STATE_DEGRADING

        # Normal: Everything is healthy
        return config.STATE_NORMAL

    def _update_candidate(self, target_state: str) -> bool:
        """
        FIXED: Track candidate state persistence before applying transition.

        Returns True if candidate has persisted for required count.
        """
        if self._candidate_state is None:
            # First time seeing this target
            self._candidate_state = target_state
            self._candidate_count = 1
            return False

        if self._candidate_state == target_state:
            # Same target, increment count
            self._candidate_count += 1
            return self._candidate_count >= 3
        else:
            # Target changed, reset candidate
            self._candidate_state = target_state
            self._candidate_count = 1
            return False

    def _reset_candidate(self):
        """Reset candidate tracking when transition is applied."""
        self._candidate_state = None
        self._candidate_count = 0

    def update_state_with_hysteresis(
        self,
        degradation: float,
        health_index: float,
        is_confirmed_anomaly: bool,
        in_maintenance: bool = False,
        maintenance_duration: int = config.MAINTENANCE_DURATION_MINUTES,
        hysteresis_count: int = 3
    ) -> str:
        """
        Updates machine operational state with hysteresis to prevent oscillation.

        FIXED: Properly tracks candidate state before applying transition.

        Follows canonical chain:
        NORMAL -> DEGRADING -> WARNING -> PREDICTIVE_ALERT -> CRITICAL -> FAILED
        And recovery: MAINTENANCE -> RECOVERY -> NORMAL
        """

        # Store current values for history
        self.degradation_history.append(degradation)
        self.health_history.append(health_index)

        # ===== MAINTENANCE & RECOVERY (Special States) =====
        # These override normal state transitions

        if in_maintenance:
            self.current_state = config.STATE_MAINTENANCE
            self.repair_timer = maintenance_duration
            self.state_history.append(self.current_state)
            self._reset_candidate()
            return self.current_state

        if self.current_state == config.STATE_MAINTENANCE:
            # Transition from maintenance to recovery
            self.current_state = config.STATE_RECOVERY
            self.recovery_timer = maintenance_duration
            self.state_history.append(self.current_state)
            self._reset_candidate()
            return self.current_state

        if self.current_state == config.STATE_RECOVERY:
            # Countdown recovery timer
            self.recovery_timer -= 1
            if self.recovery_timer <= 0:
                self.current_state = config.STATE_NORMAL
            self.state_history.append(self.current_state)
            self._reset_candidate()
            return self.current_state

        # ===== NORMAL STATE TRANSITIONS =====

        # Calculate target state based on current values
        target_state = self._calculate_target_state(
            degradation, health_index, is_confirmed_anomaly
        )

        # ===== FIXED: Apply hysteresis using candidate tracking =====

        # If target is the same as current state, reset candidate and keep state
        if target_state == self.current_state:
            self._reset_candidate()
            self.state_history.append(self.current_state)
            return self.current_state

        # Target is different from current state
        # Check if candidate has persisted for required count
        if self._update_candidate(target_state):
            # Candidate persisted, apply transition
            self.current_state = target_state
            self._reset_candidate()
        # else: candidate still accumulating, stay in current state

        # Store final state in history
        self.state_history.append(self.current_state)
        return self.current_state

    def update_state(
        self,
        degradation: float,
        health_index: float,
        is_confirmed_anomaly: bool,
        in_maintenance: bool = False,
        maintenance_duration: int = config.MAINTENANCE_DURATION_MINUTES
    ) -> str:
        """
        Legacy method - maintains backward compatibility.
        Calls update_state_with_hysteresis with default parameters.
        """
        return self.update_state_with_hysteresis(
            degradation=degradation,
            health_index=health_index,
            is_confirmed_anomaly=is_confirmed_anomaly,
            in_maintenance=in_maintenance,
            maintenance_duration=maintenance_duration,
            hysteresis_count=config.DECISION_CONFIG.get("hysteresis_count", 3)
        )

    def get_state_transition_summary(self) -> dict:
        """Get summary of state transitions for analysis."""
        if len(self.state_history) < 2:
            return {"total_transitions": 0, "states": [self.current_state]}

        transitions = 0
        for i in range(1, len(self.state_history)):
            if self.state_history[i] != self.state_history[i-1]:
                transitions += 1

        return {
            "total_transitions": transitions,
            "current_state": self.current_state,
            "history_length": len(self.state_history),
            "unique_states": list(set(self.state_history))
        }

    def reset(self):
        """Reset the state machine to initial conditions."""
        self.current_state = config.STATE_NORMAL
        self.state_history = []
        self.recovery_timer = 0
        self.repair_timer = 0
        self.degradation_history = []
        self.health_history = []
        self._candidate_state = None
        self._candidate_count = 0

    @staticmethod
    def get_state_badge(state: str) -> dict:
        """Returns color badges and operational directives for dashboard."""
        badges = {
            "NORMAL": {
                "color": "#28a745",
                "label": "NORMAL (Healthy)",
                "action": "Continue Standard Operation",
                "severity": 0
            },
            "DEGRADING": {
                "color": "#17a2b8",
                "label": "DEGRADING (Early Drift)",
                "action": "Routine Monitoring",
                "severity": 1
            },
            "WARNING": {
                "color": "#ffc107",
                "label": "WARNING (Inspection Needed)",
                "action": "Elevate Diagnostics",
                "severity": 2
            },
            "PREDICTIVE_ALERT": {
                "color": "#fd7e14",
                "label": "PREDICTIVE ALERT (Actionable)",
                "action": "Schedule 15-min Intervention",
                "severity": 3
            },
            "CRITICAL": {
                "color": "#dc3545",
                "label": "CRITICAL (Severe Risk)",
                "action": "Immediate Controlled Stop / Derate",
                "severity": 4
            },
            "FAILED": {
                "color": "#6c757d",
                "label": "FAILED (Breakdown)",
                "action": "Emergency Corrective Repair",
                "severity": 5
            },
            "MAINTENANCE": {
                "color": "#6f42c1",
                "label": "MAINTENANCE (Under Repair)",
                "action": "Repair In Progress",
                "severity": 4
            },
            "RECOVERY": {
                "color": "#20c997",
                "label": "RECOVERY (Post-Repair)",
                "action": "Stabilizing Phase",
                "severity": 2
            }
        }
        return badges.get(state, badges["NORMAL"])