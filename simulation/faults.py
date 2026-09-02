"""
PRIME-Factory Multi-Fault & Scenario Injection Engine v6.0
Generates continuous, time-varying degradation profiles shared across policy branches (Section 12).
"""

import numpy as np
import config

def generate_degradation_profile(total_timesteps: int, start_time: int, max_degradation: float = 0.85) -> list:
    """Generates a smooth, monotonically increasing bearing wear degradation trajectory."""
    profile = np.zeros(total_timesteps)
    if start_time < total_timesteps:
        duration = total_timesteps - start_time
        # Use exponential growth for more realistic bearing wear
        x = np.linspace(0, 1, duration)
        profile[start_time:] = max_degradation * (1 - np.exp(-3 * x))
    return profile.tolist()

def generate_friction_profile(total_timesteps: int, start_time: int, max_friction: float = 0.40) -> list:
    """Generates continuous mechanical friction / conveyor belt drag profile."""
    profile = np.zeros(total_timesteps)
    if start_time < total_timesteps:
        duration = total_timesteps - start_time
        profile[start_time:] = np.linspace(0.0, max_friction, duration)
    return profile.tolist()

def generate_electrical_profile(total_timesteps: int, start_time: int, max_severity: float = 0.40) -> list:
    """Generates stator winding degradation and power factor decay profile."""
    profile = np.zeros(total_timesteps)
    if start_time < total_timesteps:
        duration = total_timesteps - start_time
        profile[start_time:] = np.linspace(0.0, max_severity, duration)
    return profile.tolist()

def generate_switching_schedule(total_timesteps: int) -> list:
    """Generates dynamic multi-product switching schedule: Product_A -> Product_B -> Product_C."""
    schedule = []
    interval = total_timesteps // 3
    for t in range(total_timesteps):
        if t < interval:
            schedule.append("Product_A")
        elif t < 2 * interval:
            schedule.append("Product_B")
        else:
            schedule.append("Product_C")
    return schedule

def inject_sensor_noise_spikes(
    values: np.ndarray, 
    spike_probability: float = 0.03, 
    noise_magnitude: float = 2.5,
    rng: np.random.RandomState = None
) -> np.ndarray:
    """Simulates transient electromagnetic interference and sensor spikes for chaos testing."""
    if rng is None:
        rng = np.random.RandomState()
    noisy_values = values.copy()
    num_spikes = int(len(values) * spike_probability)
    if num_spikes > 0:
        spike_indices = rng.choice(len(values), num_spikes, replace=False)
        for idx in spike_indices:
            noisy_values[idx] += rng.uniform(1.2, noise_magnitude)
    return noisy_values

# ===== NEW: Fault scenario builder for integration with PackagingFactory =====
def build_fault_scenario(
    machine_id: str,
    fault_type: str,
    severity: float,
    start_time: int,
    total_timesteps: int
) -> dict:
    """
    Build a complete fault scenario dictionary for use with PackagingFactory.
    Returns: dict with machine_id, fault_type, severity, start_time, and degradation_profile
    """
    if fault_type == "bearing_wear" or "Bearing" in fault_type:
        profile = generate_degradation_profile(total_timesteps, start_time, severity)
    elif fault_type == "friction" or "Friction" in fault_type:
        profile = generate_friction_profile(total_timesteps, start_time, severity * 0.5)
    elif fault_type == "electrical" or "Electrical" in fault_type:
        profile = generate_electrical_profile(total_timesteps, start_time, severity * 0.5)
    else:
        profile = generate_degradation_profile(total_timesteps, start_time, severity)
    
    return {
        "machine_id": machine_id,
        "fault_type": fault_type,
        "severity": severity,
        "start_time": start_time,
        "degradation_profile": profile
    }