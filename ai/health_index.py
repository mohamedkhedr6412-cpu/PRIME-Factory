"""
PRIME-Factory Health Index (HI) Formulation
HI_t = 100 - [alpha * A_F + beta * P_t + gamma * |ECI_t| + delta * C_t] * 100
"""
import config

def calculate_health_index(anomaly_score: float, persistence_ratio: float, eci: float, temp_c: float) -> float:
    """
    حساب مؤشر الصحة الهندسية للماكينة من 100 (سليم تمامًا) إلى 0 (تلف حرج)
    """
    w = config.HI_WEIGHTS
    
    # 1. حساب عقوبة الشذوذ والاستمرارية
    score_penalty = anomaly_score
    persistence_penalty = persistence_ratio
    
    # 2. حساب عقوبة انحراف الطاقة (|ECI|)
    eci_penalty = min(1.0, max(0.0, abs(eci) * 3.0))
    
    # 3. حساب العقوبة الحرارية
    temp_penalty = min(1.0, max(0.0, (temp_c - 42.0) / 25.0))
    
    # الدمج الموزون
    total_penalty = (
        w["alpha"] * score_penalty +
        w["beta"] * persistence_penalty +
        w["gamma"] * eci_penalty +
        w["delta"] * temp_penalty
    )
    
    hi = config.HEALTH_INDEX_MAX - (total_penalty * 100.0)
    return round(float(max(config.HEALTH_INDEX_MIN, min(config.HEALTH_INDEX_MAX, hi))), 2)

def map_hi_to_decision(hi: float) -> str:
    """تحويل مؤشر الصحة إلى قرار صيانة تشغيلي"""
    if hi >= config.HI_THRESHOLDS["HEALTHY"]:
        return "NORMAL (Continue Operation)"
    elif hi >= config.HI_THRESHOLDS["MONITOR"]:
        return "MONITOR (Increase Inspection)"
    elif hi >= config.HI_THRESHOLDS["DEGRADED"]:
        return "PLAN_MAINTENANCE (Schedule Intervention)"
    else:
        return "CRITICAL (Immediate Action / Derate)"
    