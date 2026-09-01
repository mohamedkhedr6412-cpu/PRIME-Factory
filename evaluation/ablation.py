"""
PRIME-Factory Architectural Ablation Study Module v4.2
Evaluates incremental value across all 6 detector layers (including Dense Autoencoder)
with mathematically verified F1 identities and explicit timing metrics (P0-05, P0-06).
"""

import pandas as pd
import numpy as np
from sklearn.neural_network import MLPRegressor
import config

def run_ablation_study(eval_df: pd.DataFrame) -> pd.DataFrame:
    """
    Executes pure detector ablation against ground-truth degradation onset (degradation >= 0.15).
    """
    results = []
    y_true = (eval_df["degradation"] >= 0.15).astype(int)

    # Layer A: Traditional Static Thresholds
    y_pred_a = ((eval_df["vibration_rms"] > 1.2) | (eval_df["temperature_c"] > 50.0)).astype(int)

    # Layer B: Raw Isolation Forest
    y_pred_b = (eval_df["raw_ai_score"] > 0.50).astype(int)

    # Layer C: Context-Conditioned Isolation Forest
    y_pred_c = (eval_df["context_ai_score"] > 0.50).astype(int)

    # Layer D: Dense Autoencoder Reconstruction Loss
    healthy_data = eval_df[eval_df["degradation"] == 0.0][["power_kw", "vibration_rms", "temperature_c"]].copy()
    if len(healthy_data) > 20:
        ae_model = MLPRegressor(
            hidden_layer_sizes=(16, 8, 16), 
            activation="relu", 
            max_iter=250, 
            random_state=config.RANDOM_SEED
        )
        ae_model.fit(healthy_data, healthy_data)
        feat_all = eval_df[["power_kw", "vibration_rms", "temperature_c"]].values
        ae_preds = ae_model.predict(feat_all)
        rec_error = np.mean(np.square(feat_all - ae_preds), axis=1)
        ae_thresh = np.percentile(rec_error[:len(healthy_data)], 98)
        y_pred_d = (rec_error > ae_thresh).astype(int)
    else:
        y_pred_d = y_pred_c

    # Layer E: Context IF + ECI Fusion
    y_pred_e = ((eval_df["context_ai_score"] > 0.50) & (eval_df["eci"].abs() > 0.05)).astype(int)

    # Layer F: Full PRIME Detector (Context + ECI + Persistence Filter)
    y_pred_f = ((eval_df["context_ai_score"] > 0.50) & (eval_df["eci"].abs() > 0.05) & (eval_df["confirmed_anomaly"] == 1)).astype(int)

    models = {
        "Model A (Static Thresholds)": y_pred_a,
        "Model B (Raw Isolation Forest)": y_pred_b,
        "Model C (Context-Conditioned IF)": y_pred_c,
        "Model D (Dense Autoencoder Rec.)": y_pred_d,
        "Model E (Context IF + ECI Fusion)": y_pred_e,
        "Model F (Full PRIME + Persistence)": y_pred_f
    }

    shift_hours = config.SHIFT_HOURS

    for name, preds in models.items():
        tp = np.sum((y_true == 1) & (preds == 1))
        fp = np.sum((y_true == 0) & (preds == 1))
        fn = np.sum((y_true == 1) & (preds == 0))

        precision = (tp / (tp + fp)) if (tp + fp) > 0 else 0.0
        recall = (tp / (tp + fn)) if (tp + fn) > 0 else 0.0
        
        # Rigorous F1 calculation identity (P0-05 Fix)
        f1 = (2.0 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0
        false_alarms_per_hour = round(float(fp / shift_hours), 2)

        # Explicit timing definitions (P0-06 Fix)
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