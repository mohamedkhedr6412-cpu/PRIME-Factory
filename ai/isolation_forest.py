"""
PRIME-Factory Isolation Forest Anomaly Detector v6.0
Trained exclusively on healthy baseline data with deterministic seed isolation (Section 8).
Integrated with decision engine and evidence tracking.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
from typing import Optional, List, Dict
import config


class PRIMEIsolationForest:
    """
    Isolation Forest-based anomaly detector (Layer B).
    Trained on healthy baseline data only.
    """
    
    def __init__(self, contamination: float = 0.02, seed: int = config.RANDOM_SEED):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=seed
        )
        self.feature_cols = ["speed_rpm", "load_factor", "vibration_rms", "temperature_c", "current_a", "power_kw"]
        self.is_fitted = False
        self._last_scores = []

    def fit(self, healthy_df: pd.DataFrame):
        """Fits the anomaly detector strictly on verified healthy baseline data."""
        X = healthy_df[self.feature_cols].copy()
        self.model.fit(X)
        self.is_fitted = True

    def predict_anomaly_score(self, df: pd.DataFrame) -> np.ndarray:
        """
        Computes standardized anomaly scores scaled between 0.0 (Normal) and 1.0 (Anomalous).
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting anomaly scores.")
        X = df[self.feature_cols].copy()
        raw_scores = self.model.decision_function(X)
        normalized_scores = 1.0 / (1.0 + np.exp(raw_scores * 5.0))
        scores = np.round(normalized_scores, 4)
        self._last_scores.extend(scores.tolist())
        return scores

    def predict_with_evidence(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Predicts anomaly scores and returns a DataFrame with detailed evidence.
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting.")
        
        X = df[self.feature_cols].copy()
        raw_scores = self.model.decision_function(X)
        normalized_scores = 1.0 / (1.0 + np.exp(raw_scores * 5.0))
        
        result_df = df.copy()
        result_df['isolation_score'] = np.round(normalized_scores, 4)
        result_df['is_anomaly'] = (normalized_scores > 0.6).astype(int)
        result_df['confidence'] = np.where(
            normalized_scores > 0.7, 'HIGH',
            np.where(normalized_scores > 0.4, 'MEDIUM', 'LOW')
        )
        
        self._last_scores.extend(normalized_scores.tolist())
        return result_df

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Returns feature importance based on tree split frequency.
        This is a simplified version; true feature importance would require additional analysis.
        """
        # Simple placeholder - in real implementation, analyze tree splits
        return {col: 1.0 / len(self.feature_cols) for col in self.feature_cols}

    def reset(self):
        """Clear score history."""
        self._last_scores = []

    def get_average_score(self, window: int = 20) -> float:
        """
        Calculate the average anomaly score over the last N samples.
        """
        if not self._last_scores:
            return 0.0
        recent = self._last_scores[-window:]
        return sum(recent) / len(recent) if recent else 0.0