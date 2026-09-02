"""
PRIME-Factory Packaging Line Orchestrator v6.0
Coordinates synchronized multi-machine execution, state management, and KPI tracking.
"""

import pandas as pd
import numpy as np
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field

import config
from simulation.machines import Machine
from simulation.state_machine import AssetStateMachine


@dataclass
class FactoryKPIs:
    """Factory-level KPI tracking."""
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


class PackagingFactory:
    """
    Complete factory simulation orchestrating 5 machines with state management.
    """
    
    def __init__(self, seed: int = config.RANDOM_SEED):
        self.seed = seed
        self.rng = np.random.RandomState(seed)
        
        # Initialize machines
        self.machines: Dict[str, Machine] = {}
        for m_id, meta in config.MACHINES.items():
            self.machines[m_id] = Machine(
                machine_id=m_id,
                name=meta["name"],
                has_vibration=meta["has_vibration"],
                nominal_kw=meta["nominal_kw"]
            )
        
        # Initialize state machines for each asset
        self.state_machines: Dict[str, AssetStateMachine] = {
            m_id: AssetStateMachine(m_id) for m_id in self.machines
        }
        
        # Current product schedule
        self.current_product = "Product_B"
        self.timestep = 0
        self.running = False
        self.paused = False
        
        # KPI tracking
        self.kpis = FactoryKPIs()
        self.history: List[Dict] = []
        self.event_log: List[Dict] = []
        
        # Anomaly detection components (will be integrated later)
        self.anomaly_scores: Dict[str, float] = {}
        self.persistence_ratios: Dict[str, float] = {}
        self.confirmed_anomalies: Dict[str, bool] = {}
        
    def reset_factory(self):
        """Reset all machines and state machines to initial conditions."""
        for machine in self.machines.values():
            machine.reset()
        for sm in self.state_machines.values():
            sm.reset()
        
        self.timestep = 0
        self.running = False
        self.paused = False
        self.kpis = FactoryKPIs()
        self.history = []
        self.event_log = []
        self.anomaly_scores = {}
        self.persistence_ratios = {}
        self.confirmed_anomalies = {}
        
        self._log_event("factory_reset", {})
        
    def reset_machine(self, machine_id: str):
        """Reset a single machine after maintenance recovery."""
        if machine_id in self.machines:
            self.machines[machine_id].reset()
            self.state_machines[machine_id].reset()
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
        total_good_units = 0
        total_scrap_units = 0
        
        for machine_id, machine in self.machines.items():
            # Step machine with current product
            record = machine.step(
                self.current_product,
                dt_minutes=dt_minutes,
                rng=self.rng
            )
            machine_records[machine_id] = record
            
            # Update state machine
            sm = self.state_machines[machine_id]
            is_confirmed = self.confirmed_anomalies.get(machine_id, False)
            
            new_state = sm.update_state_with_hysteresis(
                degradation=machine.degradation_level,
                health_index=machine.health_index,
                is_confirmed_anomaly=is_confirmed,
                in_maintenance=(machine.current_state == config.STATE_MAINTENANCE),
                maintenance_duration=config.MAINTENANCE_DURATION_MINUTES,
                hysteresis_count=config.DECISION_CONFIG.get("hysteresis_count", 3)
            )
            
            # Sync machine state with state machine
            machine.current_state = new_state
            
            # Track power
            total_power += machine.active_power_kw
            
            # Production tracking (critical machines only)
            if machine_id in ["M1", "M2", "M3"] and new_state not in [config.STATE_FAILED, config.STATE_MAINTENANCE]:
                # Production logic
                product_config = config.PRODUCTS[self.current_product]
                rate = product_config["speed_factor"] * (1 - machine.degradation_level * 0.3)
                units = self.rng.poisson(rate * dt_minutes / product_config["base_cycle_time"] * 60)
                quality = 1.0 - machine.degradation_level * 0.05
                good = int(units * quality)
                scrap = units - good
                total_good_units += good
                total_scrap_units += scrap
        
        # Update factory KPIs
        self._update_kpis(
            dt_minutes=dt_minutes,
            total_power=total_power,
            good_units=total_good_units,
            scrap_units=total_scrap_units
        )
        
        # Create step summary
        summary = {
            "timestep": self.timestep,
            "status": "running",
            "total_power_kw": total_power,
            "total_energy_kwh": self.kpis.total_energy_kwh,
            "good_units": self.kpis.total_good_units,
            "scrap_units": self.kpis.total_scrap_units,
            "oee": self.kpis.oee,
            "machines": {
                mid: {
                    "state": m.current_state,
                    "degradation": m.degradation_level,
                    "health": m.health_index
                }
                for mid, m in self.machines.items()
            }
        }
        
        self.history.append(summary)
        return summary
    
    def _update_kpis(self, dt_minutes: float, total_power: float, good_units: int, scrap_units: int):
        """Update factory-level KPIs."""
        # Energy
        energy_kwh = total_power * dt_minutes / 60.0
        self.kpis.total_energy_kwh += energy_kwh
        
        # Peak power
        self.kpis.peak_power_kw = max(self.kpis.peak_power_kw, total_power)
        
        # Production
        self.kpis.total_good_units += good_units
        self.kpis.total_scrap_units += scrap_units
        
        # Throughput (units per hour)
        runtime_hours = self.timestep * dt_minutes / 60.0
        if runtime_hours > 0:
            self.kpis.throughput_units_per_hour = self.kpis.total_good_units / runtime_hours
        
        # Energy per unit
        if self.kpis.total_good_units > 0:
            self.kpis.energy_per_unit_wh = (self.kpis.total_energy_kwh * 1000) / self.kpis.total_good_units
        
        # Availability
        total_time = self.timestep * dt_minutes
        downtime = sum(m.downtime_minutes for m in self.machines.values()) / len(self.machines)
        self.kpis.downtime_minutes = downtime
        self.kpis.availability = max(0, 1 - (downtime / max(total_time, 1)))
        
        # Performance (based on ideal vs actual)
        ideal_rate = 60 / 1.5  # units per hour at nominal speed
        actual_rate = self.kpis.throughput_units_per_hour
        self.kpis.performance = min(1.0, actual_rate / ideal_rate)
        
        # Quality
        total = self.kpis.total_good_units + self.kpis.total_scrap_units
        self.kpis.quality = self.kpis.total_good_units / max(total, 1)
        
        # OEE
        self.kpis.oee = self.kpis.availability * self.kpis.performance * self.kpis.quality
    
    def inject_fault(self, machine_id: str, fault_type: str, severity: float):
        """Inject a fault into a specific machine."""
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
        """Perform maintenance on a specific machine."""
        if machine_id in self.machines:
            machine = self.machines[machine_id]
            machine.perform_maintenance(effectiveness)
            self._log_event("maintenance_performed", {
                "machine_id": machine_id,
                "effectiveness": effectiveness,
                "degradation_after": machine.degradation_level,
                "timestep": self.timestep
            })
    
    def set_anomaly_data(self, machine_id: str, anomaly_score: float, persistence: float, confirmed: bool):
        """Set anomaly detection data for a machine (for integration with AI layer)."""
        self.anomaly_scores[machine_id] = anomaly_score
        self.persistence_ratios[machine_id] = persistence
        self.confirmed_anomalies[machine_id] = confirmed
    
    def _log_event(self, event_type: str, data: Dict):
        """Log an event for traceability."""
        self.event_log.append({
            "event_type": event_type,
            "timestep": self.timestep,
            **data
        })
    
    def get_state_summary(self) -> Dict:
        """Get a comprehensive summary of the factory state."""
        return {
            "timestep": self.timestep,
            "running": self.running,
            "paused": self.paused,
            "product": self.current_product,
            "kpis": {
                "oee": self.kpis.oee,
                "availability": self.kpis.availability,
                "performance": self.kpis.performance,
                "quality": self.kpis.quality,
                "throughput": self.kpis.throughput_units_per_hour,
                "good_units": self.kpis.total_good_units,
                "scrap_units": self.kpis.total_scrap_units,
                "total_energy_kwh": self.kpis.total_energy_kwh,
                "peak_power_kw": self.kpis.peak_power_kw,
                "energy_per_unit_wh": self.kpis.energy_per_unit_wh,
                "downtime_minutes": self.kpis.downtime_minutes
            },
            "machines": {
                mid: {
                    "state": m.current_state,
                    "degradation": m.degradation_level,
                    "health": m.health_index,
                    "fault": m.fault_type,
                    "runtime_minutes": m.runtime_minutes,
                    "downtime_minutes": m.downtime_minutes
                }
                for mid, m in self.machines.items()
            }
        }
    
    def get_telemetry_dataframe(self) -> pd.DataFrame:
        """Get all telemetry data as a DataFrame for analysis."""
        records = []
        for machine in self.machines.values():
            records.extend(machine.history)
        return pd.DataFrame(records)
    
    def get_event_log(self) -> pd.DataFrame:
        """Get event log as a DataFrame."""
        return pd.DataFrame(self.event_log)