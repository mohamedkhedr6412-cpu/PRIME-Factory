"""
PRIME-Factory Canonical Data Models & System Architecture v4.2
Strictly implements the unified data objects defined in Section 17.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
import pandas as pd

@dataclass
class ScenarioConfig:
    scenario_id: str
    seed: int
    product_schedule: List[str]
    fault_machine: str
    fault_type: str
    fault_start: int
    max_degradation: float
    enable_chaos: bool = False
    enable_peak_shaving: bool = False
    manual_pdm_timestep: Optional[int] = None

@dataclass
class SimulationEvent:
    timestep: int
    event_type: str
    severity: str
    machine_id: str
    message: str
    evidence: Dict[str, Any] = field(default_factory=dict)
    recommended_action: str = ""

@dataclass
class ResilienceMetrics:
    recovery_time_min: float = 0.0
    production_loss_units: int = 0
    downtime_avoided_min: float = 0.0
    recovery_success: bool = True
    time_to_recover_min: float = 0.0
    failure_avoided: bool = True

@dataclass
class SimulationResult:
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