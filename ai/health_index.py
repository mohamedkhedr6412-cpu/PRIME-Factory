"""
PRIME-Factory Health Index, Attribution (XAI) & Rolling RUL Estimator v3.0
Fixes C4 & C7: Implements a 15-minute rolling linear regression for RUL and eliminates fake fallbacks.
"""
import numpy as np
import config

def estimate_rolling_rul(hi_history: list, window_size: int = 15) -> tuple:
    """
    تقدير العمر التشغيلي المتبقي (RUL) عبر الانحدار الخطي المتحرك لآخر 15 دقيقة:
    RUL = (HI_current - HI_critical) / |slope|
    """
    if len(hi_history) < window_size:
        return None, "RUL Not Established (Insufficient History)"
    
    recent_hi = np.array(hi_history[-window_size:])
    current_hi = recent_hi[-1]
    
    if current_hi >= config.HI_THRESHOLDS["HEALTHY"]:
        return None, "RUL Not Established (Stable Baseline)"
    
    x = np.arange(window_size)
    # حساب ميل الانحدار الخطي
    slope, _ = np.polyfit(x, recent_hi, 1)
    
    # إذا كان الانحدار سلبياً ومستمراً (تدهور فعلي)
    if slope < -0.02 and current_hi > config.HI_THRESHOLDS["CRITICAL"]:
        rul_minutes = int((current_hi - config.HI_THRESHOLDS["CRITICAL"]) / abs(slope))
        return max(0, rul_minutes), f"{rul_minutes} min (Trend-Based)"
    elif current_hi <= config.HI_THRESHOLDS["CRITICAL"]:
        return 0, "0 min (Critical Failure Reached)"
    else:
        return None, "RUL Not Established (Stable State)"

def calculate_health_index_and_evidence(
    anomaly_score: float,
    persistence_ratio: float,
    eci: float,
    temp_c: float,
    vib_rms: float
) -> dict:
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
    
    # تسمية علمية دقيقة لمساهمات الحساسات (Normalized HI Penalty Contribution)
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
    if hi >= config.HI_THRESHOLDS["HEALTHY"]:
        return "NORMAL (Continue Standard Operation)"
    elif hi >= config.HI_THRESHOLDS["MONITOR"]:
        return "MONITOR (Elevate Inspection & Diagnostics)"
    elif hi >= config.HI_THRESHOLDS["DEGRADED"]:
        return "PLAN_MAINTENANCE (Schedule 15-min Intervention)"
    else:
        return "CRITICAL (Immediate Controlled Stop / Derate)"
        