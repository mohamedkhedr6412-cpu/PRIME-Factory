"""
PRIME-Factory Context-Aware Energy Condition Indicator v6.1

Single source of truth for expected power and ECI.
"""

from __future__ import annotations

from typing import Dict, Optional

import numpy as np

import config


REFERENCE_SPEED_RPM = 1500.0


def get_context_expected_power(
    machine_id: str,
    product_key: str,
    load_factor: Optional[float] = None,
    speed_factor: Optional[float] = None,
) -> float:
    """
    Expected healthy active power under the current operating context.

    The expected baseline is calculated from commanded operating
    conditions, not degraded measured speed.
    """
    if machine_id not in config.MACHINES:
        raise KeyError(f"Unknown machine_id: {machine_id}")

    if product_key not in config.PRODUCTS:
        raise KeyError(f"Unknown product_key: {product_key}")

    machine = config.MACHINES[machine_id]
    product = config.PRODUCTS[product_key]

    load = float(product["load_factor"]) if load_factor is None else float(load_factor)
    speed = float(product["speed_factor"]) if speed_factor is None else float(speed_factor)

    expected = (
        float(machine["nominal_kw"])
        * float(product["nominal_power_mult"])
        * load
        * speed
    )

    return max(0.5, float(expected))


def calculate_eci(
    actual_power_kw: float,
    machine_id: str,
    product_key: str,
    load_factor: Optional[float] = None,
    speed_factor: Optional[float] = None,
) -> float:
    """Calculate the Energy Condition Indicator (ECI)."""
    expected = get_context_expected_power(
        machine_id=machine_id,
        product_key=product_key,
        load_factor=load_factor,
        speed_factor=speed_factor,
    )

    eci = (float(actual_power_kw) - expected) / max(expected, 1e-6)
    return round(float(eci), 4)


def calculate_eci_with_evidence(
    actual_power_kw: float,
    machine_id: str,
    product_key: str,
    context: Optional[Dict] = None,
) -> Dict:
    """Calculate ECI with detailed evidence for decision tracing."""
    context = context or {}

    expected = get_context_expected_power(
        machine_id=machine_id,
        product_key=product_key,
        load_factor=context.get("load_factor"),
        speed_factor=context.get("speed_factor"),
    )

    actual = float(actual_power_kw)
    eci = (actual - expected) / max(expected, 1e-6)
    eci = float(eci)

    threshold = float(config.DECISION_CONFIG.get("eci_deviation_threshold", 0.15))
    abs_eci = abs(eci)

    if abs_eci >= threshold * 2.0:
        severity = "HIGH"
    elif abs_eci >= threshold:
        severity = "MEDIUM"
    else:
        severity = "LOW"

    return {
        "eci": round(eci, 4),
        "expected_power_kw": round(expected, 4),
        "actual_power_kw": round(actual, 4),
        "absolute_deviation": round(abs_eci, 4),
        "threshold": threshold,
        "severity": severity,
        "is_energy_anomaly": bool(abs_eci >= threshold),
        "product": product_key,
        "machine_id": machine_id,
        "context": context,
        # ADDED: recommendation field for tests
        "recommendation": (
            "Monitor power consumption" if abs_eci < threshold else
            "Check for energy inefficiency" if abs_eci < threshold * 2 else
            "Investigate energy anomaly immediately"
        )
    }


def get_eci_trend(eci_history: list, window: int = 10) -> float:
    """Calculate the trend of ECI values over the last N samples."""
    if len(eci_history) < 2:
        return 0.0

    values = np.asarray(eci_history[-max(2, window):], dtype=float)
    x = np.arange(len(values), dtype=float)
    slope = np.polyfit(x, values, 1)[0]

    return round(float(slope), 4)