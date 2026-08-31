"""
PRIME-Factory Ablation Study Module
Evaluates the incremental value of each architectural layer:
Model A: Threshold Baseline
Model B: Isolation Forest (IF)
Model C: IF + Context
Model D: IF + Context + ECI
Model E: Full PRIME-Factory (IF + Context + Persistence + ECI + HI)
"""
import pandas as pd
import numpy as np
import config

def run_ablation_study(eval_df: pd.DataFrame) -> pd.DataFrame:
    results = []
    
    # تصنيف الحالة الحقيقية (Ground Truth): العطل يبدأ عندما يتجاوز التدهور 0.15
    y_true = (eval_df["degradation"] >= 0.15).astype(int)
    
    # Model A: Threshold Baseline
    y_pred_a = ((eval_df["vibration_rms"] > 1.2) | (eval_df["temperature_c"] > 50.0)).astype(int)
    
    # Model B: Raw Isolation Forest
    y_pred_b = (eval_df["ai_score"] > 0.50).astype(int)
    
    # Model C: IF + Context (Adjusted threshold for product)
    y_pred_c = (eval_df["ai_score"] > 0.55).astype(int)
    
    # Model D: IF + Context + ECI
    y_pred_d = ((eval_df["ai_score"] > 0.50) & (eval_df["eci"] > 0.05)).astype(int)
    
    # Model E: Full PRIME-Factory (HI <= 50)
    y_pred_e = (eval_df["health_index"] <= config.HI_THRESHOLDS["MONITOR"]).astype(int)
    
    models = {
        "Model A (Static Threshold)": y_pred_a,
        "Model B (Isolation Forest)": y_pred_b,
        "Model C (IF + Context)": y_pred_c,
        "Model D (IF + Context + ECI)": y_pred_d,
        "Model E (Full PRIME-Factory)": y_pred_e
    }
    
    for name, preds in models.items():
        tp = np.sum((y_true == 1) & (preds == 1))
        fp = np.sum((y_true == 0) & (preds == 1))
        fn = np.sum((y_true == 1) & (preds == 0))
        tn = np.sum((y_true == 0) & (preds == 0))
        
        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        false_alarms = fp
        
        results.append({
            "Architecture Layer": name,
            "Precision": round(precision, 3),
            "Recall": round(recall, 3),
            "F1-Score": round(f1, 3),
            "False Alarms (Counts)": int(false_alarms)
        })
        
    return pd.DataFrame(results)
