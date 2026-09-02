"""
PRIME-Factory Evidence & Decision Trace Engine v6.0
Section 14: Complete trace from sensor → anomaly → decision → outcome
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime
import json
import uuid


@dataclass
class EvidenceStep:
    """Single step in the evidence chain"""
    step_type: str  # SENSE, CONTEXT, DETECT, CONFIRM, HEALTH, RUL, DECIDE, ACTION, OUTCOME
    timestamp: int
    machine_id: str
    data: Dict[str, Any]
    description: str


@dataclass
class CompleteTrace:
    """Complete evidence trace from sensing to outcome"""
    trace_id: str
    machine_id: str
    start_timestamp: int
    end_timestamp: Optional[int] = None
    steps: List[EvidenceStep] = field(default_factory=list)
    decision_id: Optional[str] = None
    final_outcome: Optional[str] = None
    
    def add_step(self, step: EvidenceStep):
        """Add a step to the trace."""
        self.steps.append(step)
    
    def get_chain(self) -> List[str]:
        """Get the chain of step types as strings."""
        return [s.step_type for s in self.steps]
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for export."""
        return {
            "trace_id": self.trace_id,
            "machine_id": self.machine_id,
            "start_timestamp": self.start_timestamp,
            "end_timestamp": self.end_timestamp,
            "decision_id": self.decision_id,
            "final_outcome": self.final_outcome,
            "steps": [
                {
                    "step_type": s.step_type,
                    "timestamp": s.timestamp,
                    "data": s.data,
                    "description": s.description
                }
                for s in self.steps
            ]
        }


class EvidenceTracker:
    """
    Track and store evidence chains for decisions.
    Implements the full SENSE → CONTEXT → DETECT → CONFIRM → HEALTH → RUL → DECIDE → ACTION → OUTCOME chain.
    """
    
    def __init__(self):
        self.traces: List[CompleteTrace] = []
        self.events: List[Dict] = []
        self._trace_counter = 0
    
    def create_trace(
        self,
        machine_id: str,
        start_timestamp: int
    ) -> CompleteTrace:
        """Create a new evidence trace for a machine."""
        self._trace_counter += 1
        trace_id = f"TRACE_{self._trace_counter:04d}"
        
        trace = CompleteTrace(
            trace_id=trace_id,
            machine_id=machine_id,
            start_timestamp=start_timestamp
        )
        
        self.traces.append(trace)
        return trace
    
    def add_evidence_step(
        self,
        trace: CompleteTrace,
        step_type: str,
        timestamp: int,
        data: Dict[str, Any],
        description: str
    ):
        """Add an evidence step to a trace."""
        step = EvidenceStep(
            step_type=step_type,
            timestamp=timestamp,
            machine_id=trace.machine_id,
            data=data,
            description=description
        )
        trace.add_step(step)
    
    def create_complete_chain(
        self,
        machine_id: str,
        timestamp: int,
        sensor_data: Dict,
        context: Dict,
        anomaly_score: float,
        persistence_ratio: float,
        is_confirmed: bool,
        health_index: float,
        rul_minutes: Optional[float],
        eci: float,
        state: str,
        decision_recommendation: str,
        decision_id: str
    ) -> CompleteTrace:
        """
        Create a complete evidence chain in one call.
        This implements the full SENSE → CONTEXT → DETECT → CONFIRM → HEALTH → RUL → DECIDE chain.
        """
        trace = self.create_trace(machine_id, timestamp)
        
        # SENSE - Raw sensor data
        self.add_evidence_step(
            trace, "SENSE", timestamp,
            {"sensors": sensor_data},
            f"Raw sensor measurements collected from {machine_id}"
        )
        
        # CONTEXT - Operating context
        self.add_evidence_step(
            trace, "CONTEXT", timestamp,
            {"context": context},
            f"Operating context: {context.get('product', 'unknown')}, Speed: {context.get('speed', 'N/A')}"
        )
        
        # DETECT - Raw anomaly detection
        self.add_evidence_step(
            trace, "DETECT", timestamp,
            {"anomaly_score": anomaly_score},
            f"Anomaly score: {anomaly_score:.4f} (threshold: 0.5)"
        )
        
        # CONFIRM - Persistence confirmation
        self.add_evidence_step(
            trace, "CONFIRM", timestamp,
            {"persistence_ratio": persistence_ratio, "is_confirmed": is_confirmed},
            f"Persistence: {persistence_ratio:.3f}, Confirmed: {is_confirmed}"
        )
        
        # HEALTH - Health Index calculation
        self.add_evidence_step(
            trace, "HEALTH", timestamp,
            {"health_index": health_index},
            f"Health Index: {health_index:.1f}"
        )
        
        # RUL - Remaining Useful Life
        self.add_evidence_step(
            trace, "RUL", timestamp,
            {"rul_minutes": rul_minutes if rul_minutes is not None else "N/A"},
            f"RUL: {rul_minutes:.0f} minutes" if rul_minutes is not None else "RUL: Stable"
        )
        
        # DECIDE - Decision
        self.add_evidence_step(
            trace, "DECIDE", timestamp,
            {
                "state": state,
                "recommendation": decision_recommendation,
                "decision_id": decision_id
            },
            f"Decision: {decision_recommendation[:100]}..."
        )
        
        trace.decision_id = decision_id
        return trace
    
    def complete_trace(
        self,
        trace: CompleteTrace,
        end_timestamp: int,
        action_taken: str,
        outcome: Dict
    ):
        """Complete a trace with action and outcome."""
        trace.end_timestamp = end_timestamp
        
        # ACTION
        self.add_evidence_step(
            trace, "ACTION", end_timestamp,
            {"action": action_taken},
            f"Action taken: {action_taken}"
        )
        
        # OUTCOME
        self.add_evidence_step(
            trace, "OUTCOME", end_timestamp,
            {"outcome": outcome},
            f"Outcome: {outcome.get('status', 'unknown')}"
        )
        
        trace.final_outcome = outcome.get('status', 'completed')
    
    def get_trace(self, trace_id: str) -> Optional[CompleteTrace]:
        """Get a trace by ID."""
        for trace in self.traces:
            if trace.trace_id == trace_id:
                return trace
        return None
    
    def get_traces_by_machine(self, machine_id: str) -> List[CompleteTrace]:
        """Get all traces for a specific machine."""
        return [t for t in self.traces if t.machine_id == machine_id]
    
    def get_traces_by_state(self, state: str) -> List[CompleteTrace]:
        """Get traces that reached a specific state."""
        result = []
        for trace in self.traces:
            for step in trace.steps:
                if step.step_type == "DECIDE" and step.data.get("state") == state:
                    result.append(trace)
                    break
        return result
    
    def get_recent_traces(self, count: int = 20) -> List[CompleteTrace]:
        """Get the most recent N traces."""
        return self.traces[-count:] if self.traces else []
    
    def export_to_json(self, filepath: str) -> bool:
        """Export all traces to JSON file."""
        try:
            data = {
                "total_traces": len(self.traces),
                "traces": [t.to_dict() for t in self.traces],
                "export_timestamp": datetime.now().isoformat()
            }
            with open(filepath, 'w') as f:
                json.dump(data, f, indent=2)
            return True
        except Exception as e:
            print(f"Error exporting evidence: {e}")
            return False
    
    def export_to_dataframe(self):
        """Export traces as a flattened DataFrame for analysis."""
        rows = []
        for trace in self.traces:
            for step in trace.steps:
                rows.append({
                    "trace_id": trace.trace_id,
                    "machine_id": trace.machine_id,
                    "timestamp": step.timestamp,
                    "step_type": step.step_type,
                    "description": step.description,
                    **step.data
                })
        import pandas as pd
        return pd.DataFrame(rows)
    
    def reset(self):
        """Clear all traces."""
        self.traces = []
        self.events = []
        self._trace_counter = 0