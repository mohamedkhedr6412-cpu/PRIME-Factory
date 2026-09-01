"""
PRIME-Factory Multi-Fault & Scenario Injection Engine v4.1
Generates continuous degradation profiles (P0-01 Fix) and handles sensor noise stress tests.
"""

import numpy as np
import config

def generate_degradation_profile(total_timesteps: int, start_time: int, max_degradation: float = 0.85) -> list:
    """Generates continuous mechanical bearing wear degradation profile."""
    profile = np.zeros(total_timesteps)
    if start_time < total_timesteps:
        duration = total_timesteps - start_time
        profile[start_time:] = np.linspace(0.0, max_degradation, duration)
    return profile.tolist()

def generate_friction_profile(total_timesteps: int, start_time: int, max_friction: float = 0.40) -> list:
    """Generates progressive mechanical friction / conveyor belt resistance profile."""
    profile = np.zeros(total_timesteps)
    if start_time < total_timesteps:
        duration = total_timesteps - start_time
        profile[start_time:] = np.linspace(0.0, max_friction, duration)
    return profile.tolist()

def generate_electrical_profile(total_timesteps: int, start_time: int, max_severity: float = 0.40) -> list:
    """Generates stator winding degradation and power factor drop profile."""
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
    spike_indices = rng.choice(len(values), num_spikes, replace=False)
    for idx in spike_indices:
        noisy_values[idx] += rng.uniform(1.2, noise_magnitude)
    return noisy_values
