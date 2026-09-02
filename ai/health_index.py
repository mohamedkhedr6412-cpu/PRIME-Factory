"""
PRIME-Factory Health Index, Evidence Attribution & Trend-Based Rolling RUL Estimator v6.0
Computes composite HI (0-100), bounded dynamic RUL, and normalized modality penalty breakdown (Section 9).
"""

import numpy as np
import config
from typing import Dict, Optional, Tuple


def estimate_rolling_rul(
    hi_history: list, 
    current_state: str, 
    current_t: int, 
    window_size: int = 15
) -> Tuple[Optional[int], str]:
    """
    Estimates trend-based Remaining Useful Life using rolling linear regression on HI history.
    Dynamically shortens window to 5 minutes during alert/critical states and strictly caps RUL to shift duration.
    """
    w_size = 5 if current_state in [config.STATE_CRITICAL, config.STATE_PREDICTIVE_ALERT] else window_size
    if len(hi_history) < w_size:
        return None, "Initializing..."

    recent_hi = np.array(hi_history[-w_size:])
    current_hi = recent_hi[-1]

    # Check if healthy
    if current_hi >= config.HI_THRESHOLDS["HEALTHY"]:
        return None, "Stable (Healthy)"

    x = np.arange(len(recent_hi))
    slope, intercept = np.polyfit(x, recent_hi, 1)

    remaining_shift = max(0, config.TOTAL_TIMESTEPS - current_t)
    
    # Determine if degradation is accelerating
    acceleration = 0.0
    if len(hi_history) >= w_size * 2:
        older_hi = np.array(hi_history[-w_size*2:-w_size])
        if len(older_hi) >= w_size:
            older_x = np.arange(len(older_hi))
            older_slope, _ = np.polyfit(older_x, older_hi, 1)
            acceleration = older_slope - slope
    
    # Check if critical
    if current_hi <= config.HI_THRESHOLDS["CRITICAL"]:
        return 0, "0 min (Critical)"
    
    # Calculate RUL
    if slope < -0.02 and current_hi > config.HI_THRESHOLDS["CRITICAL"]:
        # Adjust RUL based on acceleration
        adjusted_slope = slope * (1 + max(0, acceleration / 10))
        rul_calc = int((current_hi - config.HI_THRESHOLDS["CRITICAL"]) / abs(adjusted_slope))
        rul_capped = min(rul_calc, remaining_shift)
        
        # Add status indicator based on current state
        if current_state == config.STATE_CRITICAL:
            return rul_capped, f"{rul_capped} min (Critical)"
        elif current_state == config.STATE_PREDICTIVE_ALERT:
            return rul_capped, f"{rul_capped} min (Alert)"
        else:
            return rul_capped, f"{rul_capped} min"
    else:
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
    Computes composite Health Index (0-100) and normalized penalty attribution across sensor modalities (Section 9).
    Weights: alpha=0.30, beta=0.25, gamma=0.25, delta=0.20.
    Now includes context-awareness for Layer D.
    """
    w = config.HI_WEIGHTS
    
    # Adjust anomaly score based on context if provided
    adjusted_anomaly = anomaly_score
    if context:
        # If context shows legitimate operating change, reduce anomaly impact
        if context.get('is_legitimate_change', False):
            adjusted_anomaly = anomaly_score * 0.5
    
    score_contrib = w["alpha"] * adjusted_anomaly
    persistence_contrib = w["beta"] * persistence_ratio
    
    # ECI contribution with context adjustment
    eci_contrib = w["gamma"] * min(1.0, max(0.0, abs(eci) * 3.0))
    if context and context.get('product_change', False):
        # Product changes naturally cause ECI deviation
        eci_contrib = eci_contrib * 0.6
    
    # Physical penalties
    temp_pen = min(1.0, max(0.0, (temp_c - 42.0) / 25.0))
    vib_pen = min(1.0, max(0.0, (vib_rms - 0.8) / 1.5)) if vib_rms > 0 else 0.0
    physics_contrib = w["delta"] * (0.6 * temp_pen + 0.4 * vib_pen)

    total_penalty = score_contrib + persistence_contrib + eci_contrib + physics_contrib
    hi = config.HEALTH_INDEX_MAX - (total_penalty * 100.0)
    hi = round(float(max(config.HEALTH_INDEX_MIN, min(config.HEALTH_INDEX_MAX, hi))), 2)

    # Calculate attribution percentages
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
    """Maps continuous Health Index to standard operational status."""
    if hi >= config.HI_THRESHOLDS["HEALTHY"]:
        return "NORMAL (Continue Standard Operation)"
    elif hi >= config.HI_THRESHOLDS["MONITOR"]:
        return "MONITOR (Elevate Inspection & Diagnostics)"
    elif hi >= config.HI_THRESHOLDS["DEGRADED"]:
        return "PLAN_MAINTENANCE (Schedule 15-min Intervention)"
    else:
        return "CRITICAL (Immediate Controlled Stop / Derate)"


def get_hi_confidence(hi: float, history_length: int) -> float:
    """
    Calculate confidence score for the health index based on history length.
    Returns a value between 0.0 and 1.0.
    """
    if history_length < 5:
        return 0.3
    elif history_length < 15:
        return 0.6
    elif history_length < 30:
        return 0.8
    else:
        return 0.95