"""
PRIME-Factory Canonical Data Models & System Architecture v6.1
Strictly implements the unified data objects defined in the Constitution.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd


@dataclass
class ScenarioConfig:
    """Configuration for a simulation scenario."""
    scenario_id: str
    seed: int
    product_schedule: List[str]
    fault_machine: str
    fault_type: str
    fault_start: int
    max_degradation: float

    # NEW: Policy type (v6.1)
    policy_type: str = "PREDICTIVE"

    # Optional flags
    enable_chaos: bool = False
    enable_peak_shaving: bool = False

    # Legacy compatibility (will be deprecated)
    manual_pdm_timestep: Optional[int] = None
    product_switch_schedule: Optional[List[str]] = None


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


@dataclass
class ResilienceMetrics:
    """Resilience metrics for factory recovery."""
    recovery_time_min: float = 0.0
    production_loss_units: int = 0
    downtime_avoided_min: float = 0.0
    recovery_success: bool = True
    time_to_recover_min: float = 0.0
    failure_avoided: bool = True
    total_decisions: int = 0
    critical_decisions: int = 0


@dataclass
class DecisionRecord:
    """Record of a decision made by the decision engine."""
    decision_id: str
    timestamp: int
    machine_id: str
    current_state: str
    health_index: float
    rul_minutes: Optional[float]
    recommendation: str
    priority: str
    evidence_summary: Dict[str, Any]
    action_taken: Optional[str] = None
    action_timestamp: Optional[int] = None


@dataclass
class EvidenceTrace:
    """Complete evidence trace for a decision."""
    trace_id: str
    machine_id: str
    start_timestamp: int
    end_timestamp: Optional[int] = None
    steps: List[Dict] = field(default_factory=list)
    decision_id: Optional[str] = None
    final_outcome: Optional[str] = None


@dataclass
class SimulationResult:
    """Complete simulation results with decision and evidence data."""
    config: ScenarioConfig
    telemetry_df: pd.DataFrame
    events: List[SimulationEvent]
    total_energy_kwh: float
    peak_demand_kw: float
    avg_pf: float
    downtime_min: float
    maintenance_events: int
    total_units: int
    good_units: int
    scrap_units: int
    availability_pct: float
    performance_pct: float
    quality_pct: float
    oee_pct: float
    energy_cost_usd: float
    downtime_cost_usd: float
    pf_penalty_usd: float
    total_operational_cost_usd: float
    carbon_kg: float
    energy_per_good_unit_wh: float
    cost_per_good_unit_usd: float
    resilience: ResilienceMetrics
    decisions: List[DecisionRecord] = field(default_factory=list)
    evidence_traces: List[EvidenceTrace] = field(default_factory=list)
    evidence_tracker: Optional[Any] = None

    # Legacy compatibility for old tests
    def __getitem__(self, key):
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)