"""
PRIME-Factory Health Index (HI), Explainable AI (XAI) & RUL Estimator v2.0
Implements composite health scoring, sensor attribution breakdown, and dynamic RUL.
"""
import config

def calculate_health_index_and_evidence(
    anomaly_score: float,
    persistence_ratio: float,
    eci: float,
    temp_c: float,
    vib_rms: float,
    prev_hi: float = 100.0,
    dt_minutes: float = 1.0
) -> dict:
    """
    حساب مؤشر الصحة الهندسية (HI) + تفكيك نسب مساهمة الحساسات (XAI Attribution) + تقدير RUL
    """
    w = config.HI_WEIGHTS
    
    # 1. تطبيع مساهمات الأدلة
    score_contrib = w["alpha"] * anomaly_score
    persistence_contrib = w["beta"] * persistence_ratio
    eci_contrib = w["gamma"] * min(1.0, max(0.0, abs(eci) * 3.0))
    
    # المساهمة الحرارية والاهتزازية المشتركة
    temp_pen = min(1.0, max(0.0, (temp_c - 42.0) / 25.0))
    vib_pen = min(1.0, max(0.0, (vib_rms - 0.8) / 1.5)) if vib_rms > 0 else 0.0
    physics_contrib = w["delta"] * (0.6 * temp_pen + 0.4 * vib_pen)
    
    total_penalty = score_contrib + persistence_contrib + eci_contrib + physics_contrib
    hi = config.HEALTH_INDEX_MAX - (total_penalty * 100.0)
    hi = round(float(max(config.HEALTH_INDEX_MIN, min(config.HEALTH_INDEX_MAX, hi))), 2)
    
    # 2. تفكيك مساهمات الحساسات (Explainable AI Attribution Percentages)
    if total_penalty > 1e-4:
        attr_ai = round((score_contrib / total_penalty) * 100.0, 1)
        attr_pers = round((persistence_contrib / total_penalty) * 100.0, 1)
        attr_energy = round((eci_contrib / total_penalty) * 100.0, 1)
        attr_physics = round((physics_contrib / total_penalty) * 100.0, 1)
    else:
        attr_ai, attr_pers, attr_energy, attr_physics = 0.0, 0.0, 0.0, 0.0
        
    # 3. تقدير العمر التشغيلي المتبقي للمعدة (Remaining Useful Life - RUL)
    # معدل انحدار مؤشر الصحة
    d_hi_dt = max(0.01, (prev_hi - hi) / dt_minutes) if hi < 70.0 else 0.0
    if d_hi_dt > 0.0 and hi > config.HI_THRESHOLDS["CRITICAL"]:
        estimated_rul_min = int((hi - config.HI_THRESHOLDS["CRITICAL"]) / d_hi_dt)
    elif hi <= config.HI_THRESHOLDS["CRITICAL"]:
        estimated_rul_min = 0
    else:
        estimated_rul_min = 480  # حالة ممتازة تتجاوز الوردية
        
    return {
        "health_index": hi,
        "rul_minutes": estimated_rul_min,
        "attribution": {
            "ai_anomaly": attr_ai,
            "persistence": attr_pers,
            "energy_eci": attr_energy,
            "thermal_vibration": attr_physics
        }
    }

def map_hi_to_decision(hi: float) -> str:
    """تحويل مؤشر الصحة إلى قرار صيانة تشغيلي قطعي"""
    if hi >= config.HI_THRESHOLDS["HEALTHY"]:
        return "NORMAL (Continue Standard Operation)"
    elif hi >= config.HI_THRESHOLDS["MONITOR"]:
        return "MONITOR (Elevate Inspection & Diagnostics)"
    elif hi >= config.HI_THRESHOLDS["DEGRADED"]:
        return "PLAN_MAINTENANCE (Schedule 15-min Intervention)"
    else:
        return "CRITICAL (Immediate Controlled Stop / Derate)"
    