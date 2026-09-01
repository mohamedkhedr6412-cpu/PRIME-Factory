"""
PRIME-Factory Context-Aware Energy Condition Indicator (ECI) v6.0
Computes expected nominal power using commanded reference speed to preserve a true uncorrupted baseline (Section 7 & 10).
"""

import config

def get_context_expected_power(machine_id: str, product_key: str) -> float:
    """Computes expected active power under healthy nominal conditions for a given product recipe."""
    machine_nominal = config.MACHINES[machine_id]["nominal_kw"]
    prod = config.PRODUCTS[product_key]
    commanded_speed_rpm = 1500.0 * prod["speed_factor"]
    speed_ratio = commanded_speed_rpm / 1500.0
    expected_power = machine_nominal * prod["load_factor"] * speed_ratio
    return max(0.5, float(expected_power))

def calculate_eci(actual_power_kw: float, machine_id: str, product_key: str, epsilon: float = 1e-3) -> float:
    """
    Calculates the relative Energy Condition Indicator:
    ECI = (P_actual - P_expected) / max(P_expected, epsilon)
    """
    expected_power = get_context_expected_power(machine_id, product_key)
    denom = max(expected_power, epsilon)
    eci = (actual_power_kw - expected_power) / denom
    return round(float(eci), 4)