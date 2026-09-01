"""
PRIME-Factory Machine Model v4.1
Includes non-linear bearing wear physics, dynamic thermal lag, and isolated state resets.
"""

import numpy as np
import config

class Machine:
    def __init__(self, machine_id: str, name: str, has_vibration: bool = False, nominal_kw: float = 5.0):
        self.machine_id = machine_id
        self.name = name
        self.has_vibration = has_vibration
        self.nominal_kw = nominal_kw
        
        self.base_temp_c = 42.0
        self.base_vib_rms = 0.8 if has_vibration else 0.0
        self.voltage_v = 400.0
        
        self.reset()

    def reset(self):
        """Resets dynamic internal state to eliminate training/simulation state leakage."""
        self.state = config.STATE_NORMAL
        self.degradation_level = 0.0
        self.current_temp = self.base_temp_c

    def step(self, product_key: str, dt_minutes: float = 1.0, rng: np.random.RandomState = None) -> dict:
        """Executes one simulation timestep with isolated random state."""
        if rng is None:
            rng = np.random.RandomState()

        prod = config.PRODUCTS[product_key]
        
        # 1. Kinematic & Power Calculations
        speed_rpm = 1500.0 * prod["speed_factor"] * (1.0 - 0.05 * self.degradation_level)
        load_kw = self.nominal_kw * prod["load_factor"]
        power_penalty = load_kw * (0.35 * self.degradation_level)
        noise_p = rng.normal(0.0, 0.04)
        actual_power_kw = max(0.2, load_kw + power_penalty + noise_p)
        
        # 2. Power Factor & Electrical Current
        pf = max(0.65, 0.88 - 0.08 * self.degradation_level)
        actual_current_a = (actual_power_kw * 1000.0) / (np.sqrt(3.0) * self.voltage_v * pf)
        
        # 3. Dynamic Thermal Lag (tau = 15 min)
        target_temp = self.base_temp_c + (28.0 * self.degradation_level) + (prod["load_factor"] * 4.0)
        thermal_tau = 15.0
        temp_drift = (target_temp - self.current_temp) * (dt_minutes / thermal_tau)
        self.current_temp += temp_drift + rng.normal(0.0, 0.05)
        
        # 4. Calibrated Non-Linear Vibration (Exponent 1.5)
        if self.has_vibration:
            vib_noise = rng.normal(0.0, 0.03)
            vib_rms = self.base_vib_rms + 3.5 * (self.degradation_level ** 1.5) + vib_noise
            vib_rms = max(0.0, vib_rms)
        else:
            vib_rms = 0.0
            
        # 5. Internal Physical State Mapping
        if self.degradation_level >= 0.75:
            self.state = config.STATE_FAILED
        elif self.degradation_level >= 0.50:
            self.state = config.STATE_CRITICAL
        elif self.degradation_level >= 0.15:
            self.state = config.STATE_WARNING
        elif self.degradation_level > 0.0:
            self.state = config.STATE_DEGRADING
        else:
            self.state = config.STATE_NORMAL
            
        return {
            "machine_id": self.machine_id,
            "machine_name": self.name,
            "state": self.state,
            "product": product_key,
            "speed_rpm": round(float(speed_rpm), 2),
            "load_factor": prod["load_factor"],
            "vibration_rms": round(float(vib_rms), 3),
            "temperature_c": round(float(self.current_temp), 2),
            "current_a": round(float(actual_current_a), 2),
            "voltage_v": round(float(self.voltage_v), 1),
            "power_kw": round(float(actual_power_kw), 3),
            "pf": round(float(pf), 3),
            "degradation": round(float(self.degradation_level), 3)
        }