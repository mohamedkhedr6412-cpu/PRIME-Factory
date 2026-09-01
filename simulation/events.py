"""
PRIME-Factory Event Logging & Audit Trail Engine v4.0
Maintains a structured, chronological record of all simulation, detector, and maintenance events.
"""
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Dict, Any

@dataclass
class SimulationEvent:
    timestep: int
    event_type: str        # FAULT_INJECTED, ANOMALY_DETECTED, PREDICTIVE_ALERT, MAINTENANCE_EXECUTED, etc.
    severity: str          # INFO, WARNING, PREDICTIVE, CRITICAL, FAILURE
    machine_id: str
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = ""

class EventLog:
    def __init__(self):
        self.events: List[SimulationEvent] = []

    def add_event(
        self,
        timestep: int,
        event_type: str,
        severity: str,
        machine_id: str,
        message: str,
        evidence: Dict[str, Any] = None,
        recommended_action: str = ""
    ):
        event = SimulationEvent(
            timestep=timestep,
            event_type=event_type,
            severity=severity.upper(),
            machine_id=machine_id,
            message=message,
            evidence=evidence or {},
            recommended_action=recommended_action
        )
        self.events.append(event)

    def get_events_as_dataframe(self):
        import pandas as pd
        if not self.events:
            return pd.DataFrame(columns=["Timestep (min)", "Severity", "Machine", "Event Type", "Message", "Recommended Action"])
        
        return pd.DataFrame([
            {
                "Timestep (min)": e.timestep,
                "Severity": e.severity,
                "Machine": e.machine_id,
                "Event Type": e.event_type,
                "Message": e.message,
                "Recommended Action": e.recommended_action
            }
            for e in self.events
        ])

    def clear(self):
        self.events.clear()
        