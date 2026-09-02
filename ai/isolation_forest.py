"""
PRIME-Factory Isolation Forest Anomaly Detector v6.1

Canonical unsupervised anomaly detector for PRIME-Factory.
- Trained only on healthy baseline data.
- Accepts PRIME canonical telemetry names.
- Produces deterministic 0..1 anomaly scores.
- Separates raw output from context-conditioned output.

Layer B: Raw Isolation Forest
Layer C: Context-conditioned version (used by engine)
"""

from __future__ import annotations

from typing import Dict, List, Optional

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

import config


class PRIMEIsolationForest:
    """
    Isolation Forest anomaly detector.

    Layer B: Raw Isolation Forest trained on healthy telemetry.
    Layer C: Context-conditioned version using residualized telemetry
             supplied by the caller.
    """

    DEFAULT_FEATURES = [
        "speed_rpm",
        "load_factor",
        "vibration_rms",
        "temperature_c",
        "current_a",
        "power_kw",
    ]

    def __init__(
        self,
        contamination: float = 0.02,
        seed: int = config.RANDOM_SEED,
        threshold: float = 0.50,
        n_estimators: int = 200,
    ):
        self.seed = int(seed)
        self.threshold = float(threshold)
        self.contamination = float(contamination)

        self.feature_cols: List[str] = list(self.DEFAULT_FEATURES)

        self.model = IsolationForest(
            n_estimators=n_estimators,
            contamination=self.contamination,
            random_state=self.seed,
            n_jobs=1,
        )

        self.is_fitted = False
        self.training_rows = 0
        self.training_feature_means: Dict[str, float] = {}
        self.training_feature_stds: Dict[str, float] = {}

        self._last_scores: List[float] = []

    # ------------------------------------------------------------------
    # Feature preparation
    # ------------------------------------------------------------------

    @staticmethod
    def _canonicalize_columns(df: pd.DataFrame) -> pd.DataFrame:
        """
        Convert PRIME simulation telemetry names into the canonical
        detector schema.

        Aliases:
        - speed_rpm   ← speed_factor * 1500.0
        - current_a   ← motor_current_a
        - power_kw    ← active_power_kw
        """
        result = df.copy()

        # Speed: convert speed_factor to RPM
        if "speed_factor" in result.columns and "speed_rpm" not in result.columns:
            result["speed_rpm"] = result["speed_factor"].astype(float) * 1500.0

        # Current alias
        if "motor_current_a" in result.columns and "current_a" not in result.columns:
            result["current_a"] = result["motor_current_a"].astype(float)

        # Power alias
        if "active_power_kw" in result.columns and "power_kw" not in result.columns:
            result["power_kw"] = result["active_power_kw"].astype(float)

        # Ensure all columns exist with defaults
        for col in ["speed_rpm", "load_factor", "vibration_rms", "temperature_c", "current_a", "power_kw"]:
            if col not in result.columns:
                result[col] = 0.0

        return result

    def _prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Prepare features for training or prediction.
        """
        result = self._canonicalize_columns(df)

        # Check for missing columns
        missing = [col for col in self.feature_cols if col not in result.columns]

        if missing:
            raise ValueError(
                "PRIMEIsolationForest missing required features: "
                + ", ".join(missing)
            )

        X = result[self.feature_cols].copy()

        # Convert to numeric
        for col in self.feature_cols:
            X[col] = pd.to_numeric(X[col], errors="coerce")

        # Handle infinities
        X = X.replace([np.inf, -np.inf], np.nan)

        # Forward fill, then backward fill
        X = X.ffill().bfill()

        # Final fallback for any remaining NaN
        if X.isna().any().any():
            X = X.fillna(0.0)

        return X

    # ------------------------------------------------------------------
    # Training
    # ------------------------------------------------------------------

    def fit(self, healthy_df: pd.DataFrame) -> "PRIMEIsolationForest":
        """
        Fit exclusively on healthy baseline data.
        """
        X = self._prepare_features(healthy_df)

        if len(X) < 20:
            raise ValueError(
                "Isolation Forest requires at least 20 healthy samples. "
                f"Got {len(X)}."
            )

        self.model.fit(X)

        self.training_rows = len(X)
        self.training_feature_means = {
            col: float(X[col].mean())
            for col in self.feature_cols
        }
        self.training_feature_stds = {
            col: float(max(X[col].std(), 1e-6))
            for col in self.feature_cols
        }

        self.is_fitted = True
        return self

    # ------------------------------------------------------------------
    # Scoring
    # ------------------------------------------------------------------

    @staticmethod
    def _sigmoid_anomaly(raw_score: np.ndarray) -> np.ndarray:
        """
        Convert sklearn decision_function output into a monotonic
        anomaly score in [0, 1].

        sklearn decision_function:
        - positive → more normal
        - negative → more anomalous

        Higher output = more anomalous.
        """
        raw_score = np.asarray(raw_score, dtype=float)

        # Transform: negative scores become high anomaly scores
        transformed = -5.0 * raw_score
        transformed = np.clip(transformed, -30.0, 30.0)

        score = 1.0 / (1.0 + np.exp(-transformed))
        return np.clip(score, 0.0, 1.0)

    def predict_anomaly_score(
        self,
        df: pd.DataFrame,
    ) -> np.ndarray:
        """
        Return anomaly scores in [0, 1].
        Higher = more anomalous.
        """
        if not self.is_fitted:
            raise ValueError(
                "Isolation Forest must be fitted before prediction."
            )

        X = self._prepare_features(df)
        raw = self.model.decision_function(X)
        scores = self._sigmoid_anomaly(raw)
        scores = np.round(scores, 4)

        self._last_scores.extend(scores.tolist())
        return scores

    def predict_with_evidence(
        self,
        df: pd.DataFrame,
    ) -> pd.DataFrame:
        """
        Return telemetry plus canonical anomaly evidence.
        """
        scores = self.predict_anomaly_score(df)

        result = df.copy()
        result["isolation_score"] = scores
        result["raw_ai_score"] = scores
        result["is_anomaly"] = (scores >= self.threshold).astype(int)

        # FIXED: Use 'anomaly_confidence' instead of 'confidence'
        result["anomaly_confidence"] = np.select(
            [
                scores >= 0.80,
                scores >= 0.60,
                scores >= self.threshold,
            ],
            [
                "HIGH",
                "MEDIUM",
                "LOW",
            ],
            default="NORMAL",
        )

        # FIXED: Also add 'confidence' for backward compatibility with tests
        result["confidence"] = result["anomaly_confidence"]

        return result

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_feature_importance(self) -> Dict[str, float]:
        """
        Return normalized split-frequency proxy.

        IMPORTANT: This is a simplified proxy, not true SHAP or
        causal feature importance. It is labeled as such.
        """
        if not self.is_fitted:
            return {}

        counts = {feature: 0.0 for feature in self.feature_cols}

        for estimator in self.model.estimators_:
            tree = estimator.tree_
            for feature_idx in tree.feature:
                if feature_idx >= 0:
                    feature = self.feature_cols[feature_idx]
                    counts[feature] += 1.0

        total = sum(counts.values())
        if total <= 0:
            return {feature: 0.0 for feature in self.feature_cols}

        return {
            feature: round(counts[feature] / total, 4)
            for feature in self.feature_cols
        }

    def get_average_score(self, window: int = 20) -> float:
        if not self._last_scores:
            return 0.0
        recent = self._last_scores[-max(1, int(window)):]
        return float(np.mean(recent))

    def reset(self) -> None:
        self._last_scores.clear()

    def is_ready(self) -> bool:
        return bool(self.is_fitted)

    def get_training_summary(self) -> Dict:
        return {
            "fitted": self.is_fitted,
            "training_rows": self.training_rows,
            "features": list(self.feature_cols),
            "threshold": self.threshold,
            "contamination": self.contamination,
            "seed": self.seed,
        }