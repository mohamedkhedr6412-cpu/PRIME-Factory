"""
PRIME-Factory Packaging Line Orchestrator v6.1
Coordinates synchronized multi-machine execution with bottleneck-based production.
"""

import pandas as pd
import numpy as np
from typing import Dict, Optional, List
import config
from simulation.machines import Machine


class PackagingFactory:
    """
    Factory orchestrator with 5 machines in series.
    Production is bottleneck-based (min capacity).
    """

    def __init__(self, seed: int = config.RANDOM_SEED):
        self.seed = seed
        self.rng = np.random.RandomState(seed)

        self.machines: Dict[str, Machine] = {}
        for m_id, meta in config.MACHINES.items():
            self.machines[m_id] = Machine(
                machine_id=m_id,
                name=meta["name"],
                has_vibration=meta["has_vibration"],
                nominal_kw=meta["nominal_kw"]
            )

        self.current_product = "Product_B"
        self.timestep = 0
        self.running = False
        self.paused = False

        # KPI tracking
        self.history: List[Dict] = []
        self.event_log: List[Dict] = []

    def reset_factory(self):
        """Reset all machines to initial conditions."""
        for machine in self.machines.values():
            machine.reset()
        self.timestep = 0
        self.running = False
        self.paused = False
        self.history = []

    def reset_machine(self, machine_id: str):
        """Reset a single machine."""
        if machine_id in self.machines:
            self.machines[machine_id].reset()
            self._log_event("machine_reset", {"machine_id": machine_id})

    def start(self):
        """Start the simulation."""
        self.running = True
        self.paused = False
        self._log_event("simulation_start", {"timestamp": self.timestep})

    def pause(self):
        """Pause the simulation."""
        self.paused = True
        self._log_event("simulation_pause", {"timestamp": self.timestep})

    def resume(self):
        """Resume the simulation."""
        self.paused = False
        self._log_event("simulation_resume", {"timestamp": self.timestep})

    def step(self, dt_minutes: float = config.TIME_STEP_MINUTES) -> Dict:
        """
        Advance the simulation by one timestep.
        Returns summary of the step.
        """
        if not self.running or self.paused:
            return {"status": "paused" if self.paused else "stopped"}

        self.timestep += 1

        # Step each machine
        machine_records = {}
        total_power = 0.0

        for machine_id, machine in self.machines.items():
            record = machine.step(
                self.current_product,
                dt_minutes=dt_minutes,
                rng=self.rng
            )
            machine_records[machine_id] = record
            total_power += machine.power_kw

        # Calculate bottleneck production
        capacities = []
        for mid, machine in self.machines.items():
            if machine.current_state not in [config.STATE_FAILED, config.STATE_MAINTENANCE]:
                prod_cfg = config.PRODUCTS[self.current_product]
                cycle_time = prod_cfg["base_cycle_time"]
                speed_factor = prod_cfg["speed_factor"]
                capacity = speed_factor / cycle_time * 60.0  # units per minute
                capacity = capacity * (1.0 - 0.3 * machine.degradation_level)
                capacities.append(capacity)

        if capacities:
            line_rate = min(capacities)
        else:
            line_rate = 0.0

        # Production
        production_rate = line_rate * dt_minutes
        units_this_step = int(production_rate)

        # Quality
        max_deg = max([m.degradation_level for m in self.machines.values()])
        defect_rate = 0.005 + (0.04 * max_deg)

        good_units = int(units_this_step * (1.0 - defect_rate))
        scrap_units = units_this_step - good_units

        # Summary
        summary = {
            "timestep": self.timestep,
            "status": "running",
            "total_power_kw": round(total_power, 3),
            "good_units": good_units,
            "scrap_units": scrap_units,
            "line_rate": round(line_rate, 2),
            "machines": {
                mid: {
                    "state": m.current_state,
                    "degradation": round(m.degradation_level, 3),
                    "health": round(m.health_index, 1),
                    "power_kw": round(m.power_kw, 3)
                }
                for mid, m in self.machines.items()
            }
        }

        self.history.append(summary)
        return summary

    def get_machine(self, machine_id: str) -> Optional[Machine]:
        """Get a machine by ID."""
        return self.machines.get(machine_id)

    def inject_fault(self, machine_id: str, fault_type: str, severity: float):
        """Inject a fault into a machine."""
        if machine_id in self.machines:
            self.machines[machine_id].inject_fault(
                fault_type=fault_type,
                severity=severity,
                start_time=self.timestep
            )
            self._log_event("fault_injected", {
                "machine_id": machine_id,
                "fault_type": fault_type,
                "severity": severity,
                "timestep": self.timestep
            })

    def perform_maintenance(self, machine_id: str, effectiveness: float = config.REPAIR_EFFECTIVENESS):
        """Perform maintenance on a machine."""
        if machine_id in self.machines:
            machine = self.machines[machine_id]
            machine.perform_maintenance(effectiveness)
            self._log_event("maintenance_performed", {
                "machine_id": machine_id,
                "effectiveness": effectiveness,
                "degradation_after": machine.degradation_level,
                "timestep": self.timestep
            })

    def _log_event(self, event_type: str, data: Dict):
        """Log an event."""
        self.event_log.append({
            "event_type": event_type,
            "timestep": self.timestep,
            **data
        })

    def get_state_summary(self) -> Dict:
        """Get a comprehensive summary of factory state."""
        return {
            "timestep": self.timestep,
            "running": self.running,
            "paused": self.paused,
            "product": self.current_product,
            "machines": {
                mid: {
                    "state": m.current_state,
                    "degradation": round(m.degradation_level, 3),
                    "health": round(m.health_index, 1),
                    "fault": m.fault_type,
                    "runtime_minutes": round(m.runtime_minutes, 1),
                    "downtime_minutes": round(m.downtime_minutes, 1)
                }
                for mid, m in self.machines.items()
            },
            "kpis": {  # ADDED for compatibility
                "oee": 0.0,
                "good_units": sum(m.runtime_minutes for m in self.machines.values()) / 60.0 * 60,
                "total_energy_kwh": sum(m.cumulative_energy_kwh for m in self.machines.values())
            }
        }

    def get_telemetry_dataframe(self) -> pd.DataFrame:
        """Get all telemetry data as a DataFrame."""
        records = []
        for machine in self.machines.values():
            records.extend(machine.history)
        return pd.DataFrame(records)

    def get_event_log(self) -> pd.DataFrame:
        """Get event log as a DataFrame."""
        return pd.DataFrame(self.event_log)

    # ===== COMPATIBILITY for legacy tests =====
    def run_simulation(self, product_schedule=None, fault_machine="M3",
                       fault_type="None (Healthy Baseline)", fault_start=60,
                       max_degradation=0.0, seed=None):
        """
        Backward-compatible wrapper for old tests.
        """
        from core.models import ScenarioConfig
        from simulation.engine import UnifiedSimulationEngine

        schedule = (
            product_schedule
            if product_schedule is not None
            else ["Product_B"] * config.TOTAL_TIMESTEPS
        )

        scenario = ScenarioConfig(
            scenario_id="FACTORY_COMPAT",
            seed=seed if seed is not None else self.seed,
            product_schedule=schedule,
            fault_machine=fault_machine,
            fault_type=fault_type,
            fault_start=fault_start,
            max_degradation=max_degradation,
            policy_type="CORRECTIVE"
        )

        result = UnifiedSimulationEngine.run(scenario)
        return result.telemetry_df


# ===== Compatibility for legacy code =====
from dataclasses import dataclass

@dataclass
class FactoryKPIs:
    """Legacy compatibility class. Use evaluation.kpis instead."""
    oee: float = 0.0
    availability: float = 0.0
    performance: float = 0.0
    quality: float = 0.0
    throughput_units_per_hour: float = 0.0
    total_good_units: int = 0
    total_scrap_units: int = 0
    total_energy_kwh: float = 0.0
    peak_power_kw: float = 0.0
    energy_per_unit_wh: float = 0.0
    downtime_minutes: float = 0.0