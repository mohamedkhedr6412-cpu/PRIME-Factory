"""
PRIME-Factory Machine Simulation v6.1
Individual machine model with degradation, telemetry generation, and context-awareness.
Includes non-linear bearing wear physics, dynamic thermal lag, and fault signatures.
"""

import numpy as np
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
        self.degradation_level = 0.0
        self.health_index = 100.0
        self.current_state = config.STATE_NORMAL

        # Operating context
        self.current_product = "Product_B"

        # Telemetry (canonical schema)
        self.speed_rpm = 1500.0
        self.load_factor = 1.0
        self.vibration_rms = 0.0
        self.temperature_c = 30.0
        self.current_a = 0.0
        self.power_kw = 0.0
        self.power_factor = 0.95
        self.expected_power_kw = 0.0
        self.eci = 0.0

        # Energy tracking
        self.cumulative_energy_kwh = 0.0
        self.runtime_minutes = 0.0
        self.downtime_minutes = 0.0

        # Fault injection
        self.fault_type: Optional[str] = None
        self.fault_severity: float = 0.0
        self.fault_start_time: Optional[float] = None
        self.fault_signature: Optional[Dict] = None

        # Telemetry history
        self.history: List[Dict] = []

        # Baseline values
        self._baseline_vibration = 0.5 if has_vibration else 0.0
        self._baseline_temperature = 30.0
        self._baseline_current = nominal_kw * 2.0
        self._voltage_v = 400.0

    def reset(self):
        """Reset machine to healthy baseline."""
        self.degradation_level = 0.0
        self.health_index = 100.0
        self.current_state = config.STATE_NORMAL

        self.speed_rpm = 1500.0
        self.load_factor = 1.0
        self.vibration_rms = self._baseline_vibration
        self.temperature_c = self._baseline_temperature
        self.current_a = self._baseline_current
        self.power_kw = self.nominal_kw * 0.7
        self.power_factor = 0.95
        self.eci = 0.0

        self.cumulative_energy_kwh = 0.0
        self.runtime_minutes = 0.0
        self.downtime_minutes = 0.0

        self.fault_type = None
        self.fault_severity = 0.0
        self.fault_start_time = None
        self.fault_signature = None
        self.history = []

    def step(
        self,
        product_key: str,
        dt_minutes: float = 1.0,
        rng: Optional[np.random.RandomState] = None
    ) -> Dict:
        """
        Advance machine by one timestep and generate telemetry data.
        Uses canonical telemetry schema.
        """
        if rng is None:
            rng = np.random.RandomState()

        # Update product context
        self.current_product = product_key
        product_config = config.PRODUCTS.get(product_key, config.PRODUCTS["Product_B"])

        # Apply degradation progression
        self._apply_degradation(dt_minutes, rng)

        # Generate telemetry with degradation effects
        self._generate_telemetry(dt_minutes, rng, product_config)

        # Update cumulative energy
        energy_this_step = self.power_kw * dt_minutes / 60.0
        self.cumulative_energy_kwh += energy_this_step

        # Update runtime/downtime
        if self.current_state in [
            config.STATE_NORMAL, config.STATE_DEGRADING,
            config.STATE_WARNING, config.STATE_PREDICTIVE_ALERT
        ]:
            self.runtime_minutes += dt_minutes
        else:
            self.downtime_minutes += dt_minutes

        # Create telemetry record
        record = {
            "machine_id": self.machine_id,
            "timestep": len(self.history),
            "product": self.current_product,
            "speed_rpm": round(float(self.speed_rpm), 2),
            "load_factor": round(float(product_config["load_factor"]), 3),
            "vibration_rms": round(float(self.vibration_rms), 3),
            "temperature_c": round(float(self.temperature_c), 2),
            "current_a": round(float(self.current_a), 2),
            "power_kw": round(float(self.power_kw), 3),
            "active_power_kw": round(float(self.power_kw), 3),
            "power_factor": round(float(self.power_factor), 3),
            "degradation": round(float(self.degradation_level), 3),
            "health_index": round(float(self.health_index), 2),
            "state": self.current_state,
            "eci": round(float(self.eci), 4),
            "expected_power_kw": round(float(self.expected_power_kw), 3),
            "cumulative_energy_kwh": round(float(self.cumulative_energy_kwh), 3),
            "runtime_minutes": round(float(self.runtime_minutes), 1),
            "downtime_minutes": round(float(self.downtime_minutes), 1)
        }

        self.history.append(record)
        return record

    def _apply_degradation(self, dt_minutes: float, rng: np.random.RandomState):
        """Apply degradation progression based on fault or natural wear."""
        if self.fault_type is not None and self.fault_start_time is not None:
            elapsed = self.runtime_minutes - self.fault_start_time
            if elapsed > 0:
                rate = self.fault_severity * 0.005
                delta = rate * dt_minutes * (1 + elapsed / 100)
                self.degradation_level = min(1.0, self.degradation_level + delta)
        else:
            self.degradation_level = min(1.0, self.degradation_level + 1e-5 * dt_minutes)

        self.health_index = max(0, 100 * (1 - self.degradation_level))
        self.health_index += rng.normal(0, 0.5)
        self.health_index = max(0, min(100, self.health_index))

    def _generate_telemetry(
        self,
        dt_minutes: float,
        rng: np.random.RandomState,
        product_config: dict
    ):
        """Generate telemetry values with canonical schema and fault signatures."""
        # Context multipliers
        speed_mult = product_config["speed_factor"]
        load_mult = product_config["load_factor"]
        power_mult = product_config["nominal_power_mult"]

        # Speed (RPM)
        self.speed_rpm = 1500.0 * speed_mult * (1.0 - 0.05 * self.degradation_level)

        # Vibration (non-linear, exponent 1.5)
        if self.has_vibration:
            vib = (self._baseline_vibration * 0.8 +
                   3.5 * (self.degradation_level ** 1.5) +
                   rng.normal(0, 0.03))
            self.vibration_rms = max(0.01, vib)

        # Temperature (dynamic thermal lag)
        target_temp = 42.0 + (28.0 * self.degradation_level) + (load_mult * 4.0)
        thermal_tau = 15.0
        temp_drift = (target_temp - self.temperature_c) * (dt_minutes / thermal_tau)
        self.temperature_c += temp_drift + rng.normal(0, 0.05)

        # Power (base)
        base_power = self.nominal_kw * power_mult * load_mult * speed_mult
        fault_power = base_power * self.degradation_level * 0.15
        power = base_power + fault_power + rng.normal(0, 0.04)

        if self.current_state in [config.STATE_MAINTENANCE, config.STATE_FAILED]:
            power = self.nominal_kw * 0.05

        self.power_kw = max(0.01, power)

        # Expected power (for ECI)
        self.expected_power_kw = self.nominal_kw * power_mult * load_mult * speed_mult

        # Power Factor
        base_pf = 0.88 - 0.08 * self.degradation_level
        self.power_factor = max(0.55, base_pf + rng.normal(0, 0.01))

        # Current
        self.current_a = (self.power_kw * 1000.0) / (np.sqrt(3.0) * self._voltage_v * self.power_factor)

        # --- Apply Fault Signature (if present) ---
        if self.fault_signature is not None and self.degradation_level > 0.01:
            from simulation.faults import apply_fault_signature
            telemetry = {
                "vibration_rms": self.vibration_rms,
                "temperature_c": self.temperature_c,
                "power_kw": self.power_kw,
                "active_power_kw": self.power_kw,
                "power_factor": self.power_factor,
                "current_a": self.current_a,
                "motor_current_a": self.current_a,
            }
            modified = apply_fault_signature(
                telemetry,
                self.fault_signature,
                self.degradation_level,
                rng
            )
            self.vibration_rms = modified.get("vibration_rms", self.vibration_rms)
            self.temperature_c = modified.get("temperature_c", self.temperature_c)
            self.power_kw = modified.get("power_kw", self.power_kw)
            self.power_factor = modified.get("power_factor", self.power_factor)
            self.current_a = modified.get("current_a", self.current_a)

        # ECI (using canonical calculation)
        from energy.eci import calculate_eci
        self.eci = calculate_eci(
            actual_power_kw=self.power_kw,
            machine_id=self.machine_id,
            product_key=self.current_product,
            load_factor=load_mult,
            speed_factor=speed_mult
        )

        # Internal state mapping
        if self.degradation_level >= 0.75:
            self.current_state = config.STATE_FAILED
        elif self.degradation_level >= 0.50:
            self.current_state = config.STATE_CRITICAL
        elif self.degradation_level >= 0.15:
            self.current_state = config.STATE_WARNING
        elif self.degradation_level > 0.0:
            self.current_state = config.STATE_DEGRADING
        else:
            self.current_state = config.STATE_NORMAL

    def inject_fault(
        self,
        fault_type: str,
        severity: float,
        start_time: float,
        signature: Optional[Dict] = None
    ):
        """Inject a controlled fault with optional signature."""
        self.fault_type = fault_type
        self.fault_severity = min(1.0, max(0.1, severity))
        self.fault_start_time = start_time
        self.fault_signature = signature
        self.degradation_level = max(self.degradation_level, 0.05 * severity)

    def clear_fault(self):
        """Clear the fault."""
        self.fault_type = None
        self.fault_severity = 0.0
        self.fault_start_time = None
        self.fault_signature = None

    def perform_maintenance(self, effectiveness: float = config.REPAIR_EFFECTIVENESS):
        """Perform maintenance to reduce degradation."""
        self.degradation_level = self.degradation_level * (1 - effectiveness)
        self.degradation_level = max(0, min(1, self.degradation_level))
        self.clear_fault()
        self.current_state = config.STATE_RECOVERY