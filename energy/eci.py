"""
PRIME-Factory Context-Aware Energy Condition Indicator (ECI) v6.0
Computes expected nominal power using commanded reference speed to preserve a true uncorrupted baseline (Section 7 & 10).
Integrated with decision engine and evidence tracking.
"""

import config
from typing import Dict, Optional, Tuple


def get_context_expected_power(machine_id: str, product_key: str) -> float:
    """
    Computes expected active power under healthy nominal conditions for a given product recipe.
    """
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


def calculate_eci_with_evidence(
    actual_power_kw: float,
    machine_id: str,
    product_key: str,
    context: Optional[Dict] = None
) -> Dict:
    """
    Calculates ECI and returns detailed evidence for decision tracing.
    """
    expected_power = get_context_expected_power(machine_id, product_key)
    eci = (actual_power_kw - expected_power) / max(expected_power, 0.001)
    eci = round(float(eci), 4)
    
    # Determine severity
    threshold = config.DECISION_CONFIG.get('eci_deviation_threshold', 0.15)
    if abs(eci) > threshold * 2:
        severity = "HIGH"
    elif abs(eci) > threshold:
        severity = "MEDIUM"
    else:
        severity = "LOW"
    
    # Determine if this is a legitimate context change
    is_legitimate = False
    if context and context.get('product_change', False):
        is_legitimate = True
    
    return {
        "eci": eci,
        "expected_power": expected_power,
        "actual_power": actual_power_kw,
        "severity": severity,
        "threshold": threshold,
        "is_legitimate_change": is_legitimate,
        "recommendation": (
            "Monitor power consumption" if abs(eci) < threshold else
            "Check for energy inefficiency" if abs(eci) < threshold * 2 else
            "Investigate energy anomaly immediately"
        )
    }


def get_eci_trend(eci_history: list, window: int = 10) -> float:
    """
    Calculate the trend of ECI values over the last N samples.
    Returns positive for increasing ECI, negative for decreasing.
    """
    if len(eci_history) < window:
        return 0.0
    
    recent = eci_history[-window:]
    if len(recent) < 2:
        return 0.0
    
    # Simple linear trend
    x = list(range(len(recent)))
    n = len(recent)
    sum_x = sum(x)
    sum_y = sum(recent)
    sum_xy = sum(x[i] * recent[i] for i in range(n))
    sum_x2 = sum(x[i] ** 2 for i in range(n))
    
    try:
        slope = (n * sum_xy - sum_x * sum_y) / (n * sum_x2 - sum_x ** 2)
        return round(slope, 4)
    except ZeroDivisionError:
        return 0.0