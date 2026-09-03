"""
PRIME-Factory Health Index, Evidence Attribution & Trend-Based Rolling RUL Estimator v6.2

Computes composite HI (0-100), bounded dynamic RUL, normalized modality penalty breakdown,
and RUL validation metrics across multiple prediction origins.
"""

import numpy as np
import config
from typing import Dict, Optional, Tuple, List


def estimate_rolling_rul(
    hi_history: List[float],
    current_state: str,
    current_t: int,
    window_size: int = 15
) -> Tuple[Optional[int], str]:
    """
    Estimates trend-based RUL using rolling linear regression.

    Dynamically shortens window to 5 minutes during alert/critical states.
    """
    w_size = 5 if current_state in [config.STATE_CRITICAL, config.STATE_PREDICTIVE_ALERT] else window_size

    if len(hi_history) < w_size:
        return None, "Initializing..."

    recent_hi = np.array(hi_history[-w_size:])
    current_hi = recent_hi[-1]

    if current_hi >= config.HI_THRESHOLDS["HEALTHY"]:
        return None, "Stable (Healthy)"

    x = np.arange(len(recent_hi))
    slope, intercept = np.polyfit(x, recent_hi, 1)

    if current_hi <= config.HI_THRESHOLDS["CRITICAL"]:
        return 0, "0 min (Critical)"

    if slope < -0.02 and current_hi > config.HI_THRESHOLDS["CRITICAL"]:
        remaining_shift = max(0, config.TOTAL_TIMESTEPS - current_t)
        rul_calc = int((current_hi - config.HI_THRESHOLDS["CRITICAL"]) / abs(slope))
        rul_capped = min(rul_calc, remaining_shift)

        if current_state == config.STATE_CRITICAL:
            return rul_capped, f"{rul_capped} min (Critical)"
        elif current_state == config.STATE_PREDICTIVE_ALERT:
            return rul_capped, f"{rul_capped} min (Alert)"
        return rul_capped, f"{rul_capped} min"

    return None, "Stable"


def calculate_health_index_and_evidence(
    anomaly_score: float,
    persistence_ratio: float,
    eci: float,
    temp_c: float,
    vib_rms: float,
    context: Optional[Dict] = None
) -> dict:
    """
    Computes composite Health Index (0-100) with penalty attribution.
    """
    w = config.HI_WEIGHTS

    adjusted_anomaly = anomaly_score
    if context and context.get('is_legitimate_change', False):
        adjusted_anomaly = anomaly_score * 0.5

    score_contrib = w["alpha"] * adjusted_anomaly
    persistence_contrib = w["beta"] * persistence_ratio
    eci_contrib = w["gamma"] * min(1.0, max(0.0, abs(eci) * 3.0))

    temp_pen = min(1.0, max(0.0, (temp_c - 42.0) / 25.0))
    vib_pen = min(1.0, max(0.0, (vib_rms - 0.8) / 1.5)) if vib_rms > 0 else 0.0
    physics_contrib = w["delta"] * (0.6 * temp_pen + 0.4 * vib_pen)

    total_penalty = score_contrib + persistence_contrib + eci_contrib + physics_contrib
    hi = config.HEALTH_INDEX_MAX - (total_penalty * 100.0)
    hi = round(float(max(config.HEALTH_INDEX_MIN, min(config.HEALTH_INDEX_MAX, hi))), 2)

    if total_penalty > 1e-4:
        attr_ai = round((score_contrib / total_penalty) * 100.0, 1)
        attr_pers = round((persistence_contrib / total_penalty) * 100.0, 1)
        attr_energy = round((eci_contrib / total_penalty) * 100.0, 1)
        attr_physics = round((physics_contrib / total_penalty) * 100.0, 1)
    else:
        attr_ai, attr_pers, attr_energy, attr_physics = 0.0, 0.0, 0.0, 0.0

    return {
        "health_index": hi,
        "penalty_contributions": {
            "AI Anomaly Model": attr_ai,
            "Persistence Filter": attr_pers,
            "Energy Deviation (ECI)": attr_energy,
            "Thermal & Vibration Physics": attr_physics
        },
        "raw_components": {
            "score_contrib": round(score_contrib, 4),
            "persistence_contrib": round(persistence_contrib, 4),
            "eci_contrib": round(eci_contrib, 4),
            "physics_contrib": round(physics_contrib, 4)
        }
    }


def map_hi_to_decision(hi: float) -> str:
    """Maps Health Index to standard operational status."""
    if hi >= config.HI_THRESHOLDS["HEALTHY"]:
        return "NORMAL (Continue Standard Operation)"
    elif hi >= config.HI_THRESHOLDS["MONITOR"]:
        return "MONITOR (Elevate Inspection & Diagnostics)"
    elif hi >= config.HI_THRESHOLDS["DEGRADED"]:
        return "PLAN_MAINTENANCE (Schedule 15-min Intervention)"
    return "CRITICAL (Immediate Controlled Stop / Derate)"


def get_hi_confidence(hi: float, history_length: int) -> float:
    """Calculate confidence score for the health index."""
    if history_length < 5:
        return 0.3
    elif history_length < 15:
        return 0.6
    elif history_length < 30:
        return 0.8
    return 0.95


# ===== RUL VALIDATION (Improved for Phase 2) =====

def calculate_actual_time_to_critical(
    degradation_history: List[float],
    current_t: int,
    critical_threshold: float = 0.75
) -> Optional[int]:
    """
    Calculate the actual time until degradation reaches critical level.
    This is the ground truth for RUL validation.
    """
    if len(degradation_history) <= current_t:
        return None

    # Find when degradation will reach critical threshold
    for t in range(current_t, len(degradation_history)):
        if degradation_history[t] >= critical_threshold:
            return t - current_t

    # If never reaches critical within horizon
    return None


def validate_rul(
    estimated_rul: Optional[int],
    actual_time_to_critical: Optional[int],
    tolerance: float = 0.3
) -> Dict:
    """
    Validate RUL estimation against ground truth.

    Returns:
        - is_valid: bool
        - error_absolute: absolute error in minutes
        - error_relative: relative error (0-1)
        - within_tolerance: bool
    """
    if estimated_rul is None or actual_time_to_critical is None:
        return {
            "is_valid": False,
            "error_absolute": None,
            "error_relative": None,
            "within_tolerance": False,
            "status": "No ground truth available"
        }

    error = abs(estimated_rul - actual_time_to_critical)
    relative_error = error / max(actual_time_to_critical, 1.0)

    return {
        "is_valid": True,
        "error_absolute": int(error),
        "error_relative": round(relative_error, 3),
        "within_tolerance": relative_error <= tolerance,
        "estimated": estimated_rul,
        "actual": actual_time_to_critical,
        "status": "Valid" if relative_error <= tolerance else "Needs improvement"
    }


def evaluate_rul_performance(
    predictions: List[Tuple[Optional[int], Optional[int]]]
) -> Dict:
    """
    Evaluate RUL performance across multiple prediction origins.

    Args:
        predictions: List of tuples (estimated_rul, actual_time_to_critical)

    Returns:
        Dict with MAE, RMSE, Bias, Coverage, n_samples
    """
    # Filter out pairs where either value is None
    valid_pairs = [(e, a) for e, a in predictions if e is not None and a is not None]

    if not valid_pairs:
        return {
            "n_samples": 0,
            "MAE": None,
            "RMSE": None,
            "Bias": None,
            "Coverage": None,
            "status": "No valid pairs"
        }

    estimates = np.array([e for e, _ in valid_pairs])
    actuals = np.array([a for _, a in valid_pairs])

    errors = estimates - actuals
    abs_errors = np.abs(errors)

    mae = np.mean(abs_errors)
    rmse = np.sqrt(np.mean(errors ** 2))
    bias = np.mean(errors)

    # Coverage: percentage of estimates within ±30% of actual
    relative_errors = abs_errors / np.maximum(actuals, 1.0)
    coverage = np.mean(relative_errors <= 0.3)

    return {
        "n_samples": len(valid_pairs),
        "MAE": round(mae, 2),
        "RMSE": round(rmse, 2),
        "Bias": round(bias, 2),
        "Coverage": round(coverage, 3),
        "status": "Calculated"
    }


# ===== NEW: Multi-point RUL validation for the full trajectory =====

def evaluate_rul_across_trajectory(
    hi_history: List[float],
    degradation_history: List[float],
    prediction_origins: List[int],
    window_size: int = 15,
    critical_threshold: float = 0.75
) -> Dict:
    """
    Evaluate RUL at multiple prediction origins across the degradation trajectory.

    Args:
        hi_history: Full health index history
        degradation_history: Full degradation history
        prediction_origins: List of timesteps to evaluate RUL at (e.g., [60, 80, 100, 120])
        window_size: Window size for RUL estimation
        critical_threshold: Degradation level considered critical

    Returns:
        Dict with MAE, RMSE, Bias, Coverage across all origins
    """
    predictions = []

    for t in prediction_origins:
        if t >= len(hi_history) or t >= len(degradation_history):
            continue

        # Get HI history up to this point
        hi_up_to_t = hi_history[:t+1]

        # Estimate RUL at this point (using DEGRADING state as default)
        # Note: In real simulation, we would use the actual state at that time
        estimated_rul, _ = estimate_rolling_rul(
            hi_history=hi_up_to_t,
            current_state=config.STATE_DEGRADING,
            current_t=t,
            window_size=window_size
        )

        # Calculate actual time to critical from this point
        actual_rul = calculate_actual_time_to_critical(
            degradation_history=degradation_history,
            current_t=t,
            critical_threshold=critical_threshold
        )

        predictions.append((estimated_rul, actual_rul))

    return evaluate_rul_performance(predictions)


# ===== Compatibility for legacy tests =====
def compute_rul_metrics(
    rul_estimates: List[Optional[int]],
    actual_ruls: List[Optional[int]]
) -> Dict:
    """Legacy compatibility function."""
    predictions = list(zip(rul_estimates, actual_ruls))
    return evaluate_rul_performance(predictions)