"""
PRIME-Factory Multi-Fault & Scenario Injection Engine v6.1

Generates continuous degradation profiles with distinct fault signatures:
- Bearing Wear: Vibration ↑↑↑, Temperature ↑↑, Power ↑↑, PF ↓
- Mechanical Friction: Power ↑↑↑, Temperature ↑↑, Vibration ↑, PF ↓
- Electrical Anomaly: PF ↓↓↓, Current distortion, Temperature ↑↑, Power abnormal
"""

import numpy as np
import config
from typing import Dict, List, Optional, Tuple


def generate_degradation_profile(
    total_timesteps: int,
    start_time: int,
    max_degradation: float = 0.85,
    profile_type: str = "bearing"
) -> List[float]:
    """
    Generate a degradation profile with exponential growth pattern.

    profile_type options:
    - "bearing": smooth exponential (vibration, temperature, power)
    - "friction": rapid onset (power surge)
    - "electrical": gradual with PF decay
    """
    profile = np.zeros(total_timesteps)

    if start_time >= total_timesteps:
        return profile.tolist()

    duration = total_timesteps - start_time
    t = np.linspace(0, 1, duration)

    if profile_type == "bearing":
        # Smooth exponential: starts slow, accelerates
        profile[start_time:] = max_degradation * (1 - np.exp(-3 * t))
    elif profile_type == "friction":
        # Rapid onset: steep initial rise
        profile[start_time:] = max_degradation * (1 - np.exp(-5 * t))
    elif profile_type == "electrical":
        # Gradual: linear with slight curve
        profile[start_time:] = max_degradation * t * (1 + 0.3 * (1 - t))
    else:
        # Default: linear
        profile[start_time:] = np.linspace(0.0, max_degradation, duration)

    return profile.tolist()


def generate_friction_profile(
    total_timesteps: int,
    start_time: int,
    max_friction: float = 0.40
) -> List[float]:
    """Generate mechanical friction profile with rapid onset."""
    return generate_degradation_profile(
        total_timesteps, start_time, max_friction, profile_type="friction"
    )


def generate_electrical_profile(
    total_timesteps: int,
    start_time: int,
    max_severity: float = 0.40
) -> List[float]:
    """Generate electrical anomaly profile with gradual degradation."""
    return generate_degradation_profile(
        total_timesteps, start_time, max_severity, profile_type="electrical"
    )


def generate_switching_schedule(total_timesteps: int) -> List[str]:
    """Generate dynamic multi-product switching schedule."""
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
    rng: Optional[np.random.RandomState] = None
) -> np.ndarray:
    """Simulate transient sensor noise spikes for chaos testing."""
    if rng is None:
        rng = np.random.RandomState()

    noisy_values = values.copy()
    num_spikes = int(len(values) * spike_probability)

    if num_spikes > 0:
        spike_indices = rng.choice(len(values), num_spikes, replace=False)
        for idx in spike_indices:
            noisy_values[idx] += rng.uniform(1.2, noise_magnitude)

    return noisy_values


# ===== Fault Signature Builder (New for Phase 2) =====

def build_fault_scenario(
    machine_id: str,
    fault_type: str,
    severity: float,
    start_time: int,
    total_timesteps: int,
    signature_parameters: Optional[Dict] = None
) -> Dict:
    """
    Build a complete fault scenario with distinct signatures.

    Each fault type has a unique signature affecting different telemetry channels:
    - Bearing Wear: vibration, temperature, power, PF
    - Friction: power, temperature, current
    - Electrical: PF, current, power
    """
    # Determine profile type
    profile_type_map = {
        "bearing_wear": "bearing",
        "bearing": "bearing",
        "friction": "friction",
        "mechanical_friction": "friction",
        "electrical": "electrical",
        "electrical_anomaly": "electrical",
    }
    profile_type = profile_type_map.get(fault_type.lower(), "bearing")

    # Generate base degradation profile
    degradation_profile = generate_degradation_profile(
        total_timesteps, start_time, severity, profile_type
    )

    # Generate fault signature multipliers for each telemetry channel
    # These multipliers modify the physical response
    signatures = {
        "bearing": {
            "vibration_mult": 1.0 + 2.0,  # 3x baseline
            "temperature_mult": 1.0 + 0.5,
            "power_mult": 1.0 + 0.3,
            "pf_decay": 0.85,  # PF drops to 0.85
            "current_mult": 1.0 + 0.2,
        },
        "friction": {
            "vibration_mult": 1.0 + 0.5,
            "temperature_mult": 1.0 + 0.8,
            "power_mult": 1.0 + 1.0,  # 2x baseline
            "pf_decay": 0.90,
            "current_mult": 1.0 + 0.8,
        },
        "electrical": {
            "vibration_mult": 1.0 + 0.1,
            "temperature_mult": 1.0 + 0.6,
            "power_mult": 1.0 + 0.5,
            "pf_decay": 0.65,  # Severe PF drop
            "current_mult": 1.0 + 1.2,  # High current distortion
        },
    }

    # Merge with custom parameters if provided
    if signature_parameters:
        signatures[profile_type].update(signature_parameters)

    return {
        "machine_id": machine_id,
        "fault_type": fault_type,
        "severity": severity,
        "start_time": start_time,
        "profile_type": profile_type,
        "degradation_profile": degradation_profile,
        "signature": signatures.get(profile_type, signatures["bearing"]),
    }


def apply_fault_signature(
    telemetry: Dict,
    fault_signature: Dict,
    degradation_level: float,
    rng: Optional[np.random.RandomState] = None
) -> Dict:
    """
    Apply fault signature to telemetry values.

    This modifies the telemetry based on the fault type's signature multipliers,
    creating distinct patterns for each fault type.
    """
    if rng is None:
        rng = np.random.RandomState()

    result = telemetry.copy()
    sig = fault_signature

    # Apply degradation-dependent multipliers
    deg_factor = degradation_level

    # Vibration
    if "vibration_rms" in result:
        vib_mult = 1.0 + (sig.get("vibration_mult", 1.0) - 1.0) * deg_factor
        result["vibration_rms"] = result["vibration_rms"] * vib_mult

    # Temperature
    if "temperature_c" in result:
        temp_rise = (sig.get("temperature_mult", 1.0) - 1.0) * deg_factor * 15.0
        result["temperature_c"] = result["temperature_c"] + temp_rise

    # Power
    if "power_kw" in result:
        power_mult = 1.0 + (sig.get("power_mult", 1.0) - 1.0) * deg_factor
        result["power_kw"] = result["power_kw"] * power_mult

    if "active_power_kw" in result:
        power_mult = 1.0 + (sig.get("power_mult", 1.0) - 1.0) * deg_factor
        result["active_power_kw"] = result["active_power_kw"] * power_mult

    # Power Factor
    if "power_factor" in result:
        pf_decay = sig.get("pf_decay", 0.95)
        result["power_factor"] = max(
            0.55,
            result["power_factor"] * (1.0 - (1.0 - pf_decay) * deg_factor)
        )

    # Current
    if "current_a" in result:
        current_mult = 1.0 + (sig.get("current_mult", 1.0) - 1.0) * deg_factor
        result["current_a"] = result["current_a"] * current_mult

    if "motor_current_a" in result:
        current_mult = 1.0 + (sig.get("current_mult", 1.0) - 1.0) * deg_factor
        result["motor_current_a"] = result["motor_current_a"] * current_mult

    return result