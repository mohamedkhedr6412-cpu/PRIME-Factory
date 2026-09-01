"""
PRIME-Factory Architectural Ablation Study Module v6.0
Evaluates incremental value across all 5 canonical detector layers (A to E)
with mathematically verified F1 identities and explicit timing metrics (Section 8 & 19).
"""

import pandas as pd
import numpy as np
import config

def run_ablation_study(eval_df: pd.DataFrame) -> pd.DataFrame:
    """
    Executes pure detector ablation against ground-truth degradation onset (degradation >= 0.15).
    Architecture Layers:
    A: Static Thresholds
    B: Raw Isolation Forest
    C: Context-Conditioned Isolation Forest
    D: Context IF + ECI Fusion
    E: Full PRIME (Context IF + ECI + Persistence Filter)
    """
    results = []
    y_true = (eval_df["degradation"] >= 0.15).astype(int)

    # Layer A: Static Thresholds
    y_pred_a = ((eval_df["vibration_rms"] > 1.2) | (eval_df["temperature_c"] > 50.0)).astype(int)

    # Layer B: Raw Isolation Forest
    y_pred_b = (eval_df["raw_ai_score"] > 0.50).astype(int)

    # Layer C: Context-Conditioned Isolation Forest
    y_pred_c = (eval_df["context_ai_score"] > 0.50).astype(int)

    # Layer D: Context IF + ECI Fusion
    y_pred_d = ((eval_df["context_ai_score"] > 0.50) & (eval_df["eci"].abs() > 0.05)).astype(int)

    # Layer E: Full PRIME Detector (Context + ECI + Persistence Filter)
    y_pred_e = ((eval_df["context_ai_score"] > 0.50) & (eval_df["eci"].abs() > 0.05) & (eval_df["confirmed_anomaly"] == 1)).astype(int)

    models = {
        "Layer A (Static Thresholds)": y_pred_a,
        "Layer B (Raw Isolation Forest)": y_pred_b,
        "Layer C (Context-Conditioned IF)": y_pred_c,
        "Layer D (Context IF + ECI Fusion)": y_pred_d,
        "Layer E (Full PRIME + Persistence)": y_pred_e
    }

    shift_hours = config.SHIFT_HOURS

    for name, preds in models.items():
        tp = np.sum((y_true == 1) & (preds == 1))
        fp = np.sum((y_true == 0) & (preds == 1))
        fn = np.sum((y_true == 1) & (preds == 0))

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        
        # Rigorous F1 calculation identity
        f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        false_alarms_per_hour = round(float(fp / shift_hours), 2)

        # Explicit timing definitions
        first_det = eval_df[(preds == 1) & (eval_df["timestep"] >= 60)]["timestep"].min()
        crit_t = eval_df[eval_df["degradation"] >= 0.75]["timestep"].min()
        
        if pd.notna(first_det) and pd.notna(crit_t) and crit_t > first_det:
            lead_time = int(crit_t - first_det)
        else:
            lead_time = 0

        results.append({
            "Architecture Layer": name,
            "Precision": round(float(precision), 3),
            "Recall": round(float(recall), 3),
            "F1-Score": round(float(f1), 3),
            "False Alarms/Hr": false_alarms_per_hour,
            "Early Lead Time (min)": lead_time
        })

    return pd.DataFrame(results)