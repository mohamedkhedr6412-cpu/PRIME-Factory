"""
PRIME-Factory Health Index, Evidence Attribution & Trend-Based Rolling RUL Estimator v4.2
Computes composite HI (0-100), bounded dynamic RUL (P1-04), and normalized modality penalty breakdown.
"""

import numpy as np
import config

def estimate_rolling_rul(
    hi_history: list, 
    current_state: str, 
    current_t: int, 
    window_size: int = 15
) -> tuple:
    """
    Estimates trend-based Remaining Useful Life using rolling linear regression on HI history.
    Dynamically shortens window to 5 minutes during alert/critical states and strictly caps RUL to shift duration.
    """
    w_size = 5 if current_state in [config.STATE_CRITICAL, config.STATE_PREDICTIVE_ALERT] else window_size
    if len(hi_history) < w_size:
        return None, "Initializing..."

    recent_hi = np.array(hi_history[-w_size:])
    current_hi = recent_hi[-1]

    if current_hi >= config.HI_THRESHOLDS["HEALTHY"]:
        return None, "Stable (Healthy)"

    x = np.arange(len(recent_hi))
    slope, _ = np.polyfit(x, recent_hi, 1)

    remaining_shift = max(0, config.TOTAL_TIMESTEPS - current_t)
    if slope < -0.02 and current_hi > config.HI_THRESHOLDS["CRITICAL"]:
        rul_calc = int((current_hi - config.HI_THRESHOLDS["CRITICAL"]) / abs(slope))
        rul_capped = min(rul_calc, remaining_shift)
        return rul_capped, f"{rul_capped} min"
    elif current_hi <= config.HI_THRESHOLDS["CRITICAL"]:
        return 0, "0 min (Critical)"
    else:
        return None, "Stable"

def calculate_health_index_and_evidence(
    anomaly_score: float,
    persistence_ratio: float,
    eci: float,
    temp_c: float,
    vib_rms: float
) -> dict:
    """
    Computes composite Health Index (0-100) and normalized penalty attribution across sensor modalities (P1-03).
    """
    w = config.HI_WEIGHTS
    
    score_contrib = w["alpha"] * anomaly_score
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