"""
PRIME-Factory Architectural Ablation Study Module v2.0
Mathematically evaluates the true incremental contribution of each engineering layer:
Model A: Static Thresholds (Baseline)
Model B: Raw Isolation Forest (No Context)
Model C: Context-Conditioned Isolation Forest (Physics Residuals)
Model D: Context IF + ECI Energy Deviation Fusion
Model E: Full PRIME-Factory (Context IF + ECI + Persistence + Composite HI)
"""
import pandas as pd
import numpy as np
import config

def run_ablation_study(eval_df: pd.DataFrame) -> pd.DataFrame:
    results = []
    
    # تصنيف الحقيقة الأرضية للمحاكاة (Simulation Ground Truth)
    y_true = (eval_df["degradation"] >= 0.15).astype(int)
    
    # Model A: العتبات الثابتة التقليدية
    y_pred_a = ((eval_df["vibration_rms"] > 1.2) | (eval_df["temperature_c"] > 50.0)).astype(int)
    
    # Model B: الذكاء الاصطناعي الخام بدون وعي بالسياق
    y_pred_b = (eval_df["raw_ai_score"] > 0.50).astype(int)
    
    # Model C: الذكاء الاصطناعي الواعي بسياق المنتج والحمل (Context Residuals)
    y_pred_c = (eval_df["context_ai_score"] > 0.50).astype(int)
    
    # Model D: دمج كشف الشذوذ مع مؤشر انحراف الطاقة (Context AI + ECI Fusion)
    y_pred_d = ((eval_df["context_ai_score"] > 0.50) & (eval_df["eci"].abs() > 0.05)).astype(int)
    
    # Model E: نظام PRIME المتكامل (Context + ECI + Persistence Window + Health Index)
    y_pred_e = ((eval_df["health_index"] <= config.HI_THRESHOLDS["MONITOR"]) & (eval_df["confirmed_anomaly"] == 1)).astype(int)
    
    models = {
        "Model A (Static Thresholds)": y_pred_a,
        "Model B (Raw Isolation Forest)": y_pred_b,
        "Model C (Context-Conditioned IF)": y_pred_c,
        "Model D (Context IF + ECI Fusion)": y_pred_d,
        "Model E (Full PRIME-Factory Architecture)": y_pred_e
    }
    
    shift_hours = config.SHIFT_HOURS
    
    for name, preds in models.items():
        tp = np.sum((y_true == 1) & (preds == 1))
        fp = np.sum((y_true == 0) & (preds == 1))
        fn = np.sum((y_true == 1) & (preds == 0))
        
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        
        # حساب معدل الإنذارات الكاذبة في الساعة (False Alarms / Hour)
        false_alarms_per_hour = round(fp / shift_hours, 2)
        
        # حساب مهلة الإنذار المبكر بالدقائق قبل الوصول للحالة الحرجة (Lead Time)
        first_det = eval_df[(preds == 1) & (eval_df["timestep"] >= 60)]["timestep"].min()
        crit_t = eval_df[eval_df["degradation"] >= 0.75]["timestep"].min()
        lead_time = (crit_t - first_det) if (pd.notna(first_det) and pd.notna(crit_t) and crit_t > first_det) else 0
        
        results.append({
            "Architecture Layer": name,
            "Precision": round(precision, 3),
            "Recall": round(recall, 3),
            "F1-Score": round(f1, 3),
            "False Alarms/Hr": false_alarms_per_hour,
            "Early Lead Time (min)": int(lead_time)
        })
        
    return pd.DataFrame(results)
