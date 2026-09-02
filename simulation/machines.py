"""
PRIME-Factory Machine Simulation v6.0
Individual machine model with degradation, telemetry, and context-awareness.
"""

import numpy as np
from dataclasses import dataclass, field
from typing import Dict, Optional, List
import config

class Machine:
    """
    Individual machine model with degradation, telemetry generation,
    and context-aware power consumption.
    """
    
    def __init__(
        self,
        machine_id: str,
        name: str,
        has_vibration: bool = False,
        nominal_kw: float = 5.0
    ):
        self.machine_id = machine_id
        self.name = name
        self.has_vibration = has_vibration
        self.nominal_kw = nominal_kw
        
        # State variables
        self.degradation_level = 0.0  # 0 = healthy, 1 = failed
        self.health_index = 100.0
        self.current_state = config.STATE_NORMAL
        
        # Operating context
        self.current_product = "Product_B"
        self.speed_factor = 1.0
        self.load_factor = 1.0
        
        # Telemetry
        self.vibration_rms = 0.0
        self.temperature_c = 25.0
        self.motor_current_a = 0.0
        self.active_power_kw = 0.0
        self.reactive_power_kvar = 0.0
        self.apparent_power_kva = 0.0
        self.power_factor = 0.95
        
        # Energy tracking
        self.cumulative_energy_kwh = 0.0
        self.runtime_minutes = 0.0
        self.downtime_minutes = 0.0
        
        # Fault injection
        self.fault_type: Optional[str] = None
        self.fault_severity: float = 0.0
        self.fault_start_time: Optional[float] = None
        
        # Telemetry history
        self.history: List[Dict] = []
        
        # Baseline values (will be set on first step)
        self._baseline_vibration = 0.5 if has_vibration else 0.0
        self._baseline_temperature = 30.0
        self._baseline_current = nominal_kw * 2.0  # Rough estimate
        
        # Health index calculation components
        self.anomaly_history: List[float] = []
        self.persistence_history: List[float] = []
        self.eci_history: List[float] = []
        
    def reset(self):
        """Reset machine to healthy baseline."""
        self.degradation_level = 0.0
        self.health_index = 100.0
        self.current_state = config.STATE_NORMAL
        self.vibration_rms = self._baseline_vibration
        self.temperature_c = self._baseline_temperature
        self.motor_current_a = self._baseline_current
        self.active_power_kw = self.nominal_kw * 0.7  # Typical operating power
        self.cumulative_energy_kwh = 0.0
        self.runtime_minutes = 0.0
        self.downtime_minutes = 0.0
        self.fault_type = None
        self.fault_severity = 0.0
        self.fault_start_time = None
        self.history = []
        self.anomaly_history = []
        self.persistence_history = []
        self.eci_history = []
        
    def step(
        self,
        product_key: str,
        dt_minutes: float = 1.0,
        rng: Optional[np.random.RandomState] = None
    ) -> Dict:
        """
        Advance machine by one timestep and generate telemetry data.
        Returns dictionary with all telemetry values.
        """
        if rng is None:
            rng = np.random.RandomState()
        
        # Update product context
        self.current_product = product_key
        product_config = config.PRODUCTS.get(product_key, config.PRODUCTS["Product_B"])
        self.speed_factor = product_config["speed_factor"]
        self.load_factor = product_config["load_factor"]
        
        # Apply degradation progression
        self._apply_degradation(dt_minutes, rng)
        
        # Generate telemetry with degradation effects
        self._generate_telemetry(dt_minutes, rng)
        
        # Update cumulative energy
        energy_this_step = self.active_power_kw * dt_minutes / 60.0
        self.cumulative_energy_kwh += energy_this_step
        
        # Update runtime/downtime
        if self.current_state in [config.STATE_NORMAL, config.STATE_DEGRADING, 
                                   config.STATE_WARNING, config.STATE_PREDICTIVE_ALERT]:
            self.runtime_minutes += dt_minutes
        else:
            self.downtime_minutes += dt_minutes
        
        # Create telemetry record
        record = {
            "machine_id": self.machine_id,
            "timestep": len(self.history),
            "product": self.current_product,
            "degradation": self.degradation_level,
            "health_index": self.health_index,
            "state": self.current_state,
            "vibration_rms": self.vibration_rms,
            "temperature_c": self.temperature_c,
            "motor_current_a": self.motor_current_a,
            "active_power_kw": self.active_power_kw,
            "reactive_power_kvar": self.reactive_power_kvar,
            "apparent_power_kva": self.apparent_power_kva,
            "power_factor": self.power_factor,
            "speed_factor": self.speed_factor,
            "load_factor": self.load_factor,
            "cumulative_energy_kwh": self.cumulative_energy_kwh,
            "runtime_minutes": self.runtime_minutes,
            "downtime_minutes": self.downtime_minutes
        }
        
        self.history.append(record)
        return record
    
    def _apply_degradation(self, dt_minutes: float, rng: np.random.RandomState):
        """Apply degradation progression based on fault or natural wear."""
        if self.fault_type is not None and self.fault_start_time is not None:
            # Active fault injection with exponential progression
            elapsed = self.runtime_minutes - self.fault_start_time
            if elapsed > 0:
                # Exponential degradation: starts slow, accelerates
                rate = self.fault_severity * 0.005  # per minute
                delta = rate * dt_minutes * (1 + elapsed / 100)
                self.degradation_level = min(1.0, self.degradation_level + delta)
        else:
            # Natural wear (very slow)
            self.degradation_level = min(1.0, self.degradation_level + 1e-5 * dt_minutes)
        
        # Update health index based on degradation
        self.health_index = max(0, 100 * (1 - self.degradation_level))
        
        # Add small random variation
        self.health_index += rng.normal(0, 0.5)
        self.health_index = max(0, min(100, self.health_index))
    
    def _generate_telemetry(self, dt_minutes: float, rng: np.random.RandomState):
        """Generate telemetry values with degradation and context effects."""
        product = config.PRODUCTS.get(self.current_product, config.PRODUCTS["Product_B"])
        
        # Context multipliers
        speed_mult = self.speed_factor
        load_mult = self.load_factor
        power_mult = product["nominal_power_mult"]
        
        # Degradation effects
        deg_factor = 1.0 + self.degradation_level * 0.5  # Up to 50% increase
        
        # ===== Vibration =====
        if self.has_vibration:
            base_vib = self._baseline_vibration * 0.8
            fault_vib = self.degradation_level * 5.0
            vib = base_vib + fault_vib + rng.normal(0, 0.1)
            self.vibration_rms = max(0.01, vib)
        else:
            self.vibration_rms = 0.0
        
        # ===== Temperature =====
        temp_rise = self.degradation_level * 15.0
        temp = self._baseline_temperature + temp_rise + rng.normal(0, 1.0)
        self.temperature_c = max(20, temp)
        
        # ===== Current =====
        base_current = self.nominal_kw * 2.0 * load_mult * power_mult
        fault_current = base_current * self.degradation_level * 0.2
        current = base_current + fault_current + rng.normal(0, 0.2)
        self.motor_current_a = max(0.1, current)
        
        # ===== Power =====
        # Base power consumption depends on product and load
        base_power = self.nominal_kw * power_mult * load_mult * speed_mult
        
        # Degradation increases power consumption
        fault_power = base_power * self.degradation_level * 0.15
        power = base_power + fault_power + rng.normal(0, 0.05)
        
        # If machine is stopped, use standby power
        if self.current_state in [config.STATE_MAINTENANCE, config.STATE_FAILED]:
            power = self.nominal_kw * 0.05  # Standby power
        
        self.active_power_kw = max(0.01, power)
        
        # ===== Reactive Power & Power Factor =====
        # PF deteriorates with degradation
        base_pf = 0.95 - self.degradation_level * 0.15
        pf = max(0.75, base_pf + rng.normal(0, 0.01))
        self.power_factor = pf
        
        self.reactive_power_kvar = self.active_power_kw * np.tan(np.arccos(pf))
        self.apparent_power_kva = self.active_power_kw / pf
        
    def inject_fault(self, fault_type: str, severity: float, start_time: float):
        """Inject a controlled fault into the machine."""
        self.fault_type = fault_type
        self.fault_severity = min(1.0, max(0.1, severity))
        self.fault_start_time = start_time
        
        # Immediate initial degradation
        self.degradation_level = max(self.degradation_level, 0.05 * severity)
    
    def clear_fault(self):
        """Clear the fault (but degradation remains)."""
        self.fault_type = None
        self.fault_severity = 0.0
        self.fault_start_time = None
    
    def perform_maintenance(self, effectiveness: float = config.REPAIR_EFFECTIVENESS):
        """Perform maintenance to reduce degradation."""
        self.degradation_level = self.degradation_level * (1 - effectiveness)
        self.degradation_level = max(0, min(1, self.degradation_level))
        self.clear_fault()
        self.current_state = config.STATE_RECOVERY
        
    def recover(self):
        """Complete recovery after maintenance."""
        if self.degradation_level < 0.15:
            self.current_state = config.STATE_NORMAL
        elif self.degradation_level < 0.30:
            self.current_state = config.STATE_DEGRADING
        else:
            self.current_state = config.STATE_WARNING
            