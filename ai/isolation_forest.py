"""
PRIME-Factory Isolation Forest Anomaly Detector
Unsupervised ML model trained exclusively on healthy baseline data.
"""
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest
import config

class PRIMEIsolationForest:
    def __init__(self, contamination: float = 0.02):
        self.model = IsolationForest(
            n_estimators=100,
            contamination=contamination,
            random_state=config.RANDOM_SEED
        )
        self.feature_cols = ["speed_rpm", "load_factor", "vibration_rms", "temperature_c", "current_a", "power_kw"]
        self.is_fitted = False

    def fit(self, healthy_df: pd.DataFrame):
        """تدريب النموذج على بيانات التشغيل السليم فقط دون أي أعطال"""
        X = healthy_df[self.feature_cols].copy()
        self.model.fit(X)
        self.is_fitted = True

    def predict_anomaly_score(self, df: pd.DataFrame) -> np.ndarray:
        """
        حساب درجة الشذوذ كقيمة مستمرة بين 0 (طبيعي) و 1 (شاذ جدًا)
        """
        if not self.is_fitted:
            raise ValueError("Model must be fitted before predicting scores.")
        
        X = df[self.feature_cols].copy()
        # Decision function: قيم سالبة تعني شذوذ، قيم موجبة تعني تشغيل طبيعي
        raw_scores = self.model.decision_function(X)
        # تحويل القراءات إلى مقياس معياري [0, 1]
        normalized_scores = 1.0 / (1.0 + np.exp(raw_scores * 5.0))
        return np.round(normalized_scores, 4)
    