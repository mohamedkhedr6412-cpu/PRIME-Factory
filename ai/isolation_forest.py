"""
PRIME-Factory Isolation Forest Anomaly Detector v6.0
Trained exclusively on healthy baseline data with deterministic seed isolation (Section 8).
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import config

class PRIMEIsolationForest:
    def __init__(self, contamination: float = 0.02, seed: int = config.RANDOM_SEED):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=seed
        )
        self.feature_cols = ["speed_rpm", "load_factor", "vibration_rms", "temperature_c", "current_a", "power_kw"]
        self.is_fitted = False

    def fit(self, healthy_df: pd.DataFrame):
        """Fits the anomaly detector strictly on verified healthy baseline data."""
        X = healthy_df[self.feature_cols].copy()
        self.model.fit(X)
        self.is_fitted = True

    def predict_anomaly_score(self, df: pd.DataFrame) -> np.ndarray:
        """Computes standardized anomaly scores scaled between 0.0 (Normal) and 1.0 (Anomalous)."""
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting anomaly scores.")
        X = df[self.feature_cols].copy()
        raw_scores = self.model.decision_function(X)
        normalized_scores = 1.0 / (1.0 + np.exp(raw_scores * 5.0))
        return np.round(normalized_scores, 4)