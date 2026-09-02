"""
PRIME-Factory Event Logging & Audit Trail Engine v6.0
Maintains structured chronological event traces with causal evidence and state transitions (Section 14).
"""

from typing import List, Dict, Any, Optional
import pandas as pd
from dataclasses import dataclass, field

# ===== Local definition of SimulationEvent (since core.models may not exist yet) =====
@dataclass
class SimulationEvent:
    """Structured event record for audit trail."""
    timestep: int
    event_type: str
    severity: str
    machine_id: str
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = ""
    state_before: Optional[str] = None
    state_after: Optional[str] = None


class EventLog:
    """Event logging system with audit trail capabilities."""
    
    def __init__(self):
        self.events: List[SimulationEvent] = []
        self._event_counter = 0

    def add_event(
        self,
        timestep: int,
        event_type: str,
        severity: str,
        machine_id: str,
        message: str,
        evidence: Dict[str, Any] = None,
        recommended_action: str = "",
        state_before: Optional[str] = None,
        state_after: Optional[str] = None
    ):
        """Appends a timestamped operational event to the immutable audit trail."""
        self._event_counter += 1
        event = SimulationEvent(
            timestep=timestep,
            event_type=event_type.upper(),
            severity=severity.upper(),
            machine_id=machine_id,
            message=message,
            evidence=evidence or {},
            recommended_action=recommended_action,
            state_before=state_before,
            state_after=state_after
        )
        self.events.append(event)

    def get_events_as_dataframe(self) -> pd.DataFrame:
        """Exports the event log into a structured DataFrame for UI and CSV export."""
        if not self.events:
            return pd.DataFrame(columns=[
                "Timestep (min)", "Severity", "Machine", "Event Type", 
                "Message", "Recommended Action", "State Before", "State After"
            ])
        return pd.DataFrame([
            {
                "Timestep (min)": e.timestep,
                "Severity": e.severity,
                "Machine": e.machine_id,
                "Event Type": e.event_type,
                "Message": e.message,
                "Recommended Action": e.recommended_action,
                "State Before": e.state_before or "",
                "State After": e.state_after or ""
            }
            for e in self.events
        ])

    def get_events_by_severity(self, severity: str) -> List[SimulationEvent]:
        """Filter events by severity level."""
        return [e for e in self.events if e.severity == severity.upper()]

    def get_events_by_machine(self, machine_id: str) -> List[SimulationEvent]:
        """Filter events by machine ID."""
        return [e for e in self.events if e.machine_id == machine_id]

    def get_events_by_type(self, event_type: str) -> List[SimulationEvent]:
        """Filter events by event type."""
        return [e for e in self.events if e.event_type == event_type.upper()]

    def get_recent_events(self, n: int = 20) -> List[SimulationEvent]:
        """Get the most recent N events."""
        return self.events[-n:] if self.events else []

    def clear(self):
        """Clears all logged events upon simulation reset."""
        self.events.clear()
        self._event_counter = 0

    def get_summary_stats(self) -> Dict[str, Any]:
        """Get summary statistics of the event log."""
        if not self.events:
            return {"total_events": 0, "severity_counts": {}, "type_counts": {}}
        
        severity_counts = {}
        type_counts = {}
        for e in self.events:
            severity_counts[e.severity] = severity_counts.get(e.severity, 0) + 1
            type_counts[e.event_type] = type_counts.get(e.event_type, 0) + 1
        
        return {
            "total_events": len(self.events),
            "severity_counts": severity_counts,
            "type_counts": type_counts,
            "first_event": self.events[0].timestep if self.events else None,
            "last_event": self.events[-1].timestep if self.events else None
        }