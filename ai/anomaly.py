"""
PRIME-Factory Anomaly Confirmation Engine v6.1

Separates:
1. Raw AI anomaly
2. Context residual evidence
3. ECI evidence
4. Temporal persistence
5. Final confirmation

No layer silently substitutes another layer.
"""

from __future__ import annotations

from collections import deque
from typing import Dict, Optional

import numpy as np

import config


class AnomalyProcessor:
    """
    Machine-local temporal anomaly processor with persistence.
    """

    def __init__(
        self,
        window_size: int = config.PERSISTENCE_WINDOW,
        threshold: float = 0.50,
        persistence_threshold: float = 0.80,
        eci_threshold: Optional[float] = None,
    ):
        self.window_size = max(1, int(window_size))
        self.threshold = float(threshold)
        self.persistence_threshold = float(persistence_threshold)

        self.eci_threshold = (
            float(eci_threshold)
            if eci_threshold is not None
            else float(
                config.DECISION_CONFIG.get(
                    "eci_deviation_threshold",
                    0.15,
                )
            )
        )

        self.history = deque(maxlen=self.window_size)
        self.score_history = deque(maxlen=self.window_size)
        self.context_history = deque(maxlen=self.window_size)

    # ------------------------------------------------------------------
    # Core update
    # ------------------------------------------------------------------

    def update(
        self,
        raw_anomaly_score: float,
        threshold: Optional[float] = None,
        context: Optional[Dict] = None,
    ) -> Dict:
        """
        Process one detector output.
        """
        threshold = self.threshold if threshold is None else float(threshold)

        score = float(np.clip(raw_anomaly_score, 0.0, 1.0))
        raw_anomaly = int(score >= threshold)

        self.score_history.append(score)
        self.history.append(raw_anomaly)

        if context is not None:
            self.context_history.append(dict(context))

        persistence_ratio = float(sum(self.history)) / float(self.window_size)
        persistence_ready = len(self.history) >= self.window_size
        persistent = int(persistence_ready and persistence_ratio >= self.persistence_threshold)

        eci = 0.0
        if context:
            eci = float(context.get("eci", 0.0))

        eci_evidence = int(abs(eci) >= self.eci_threshold)

        return {
            "raw_anomaly_score": round(score, 4),
            "is_raw_anomaly": raw_anomaly,
            "persistence_ratio": round(persistence_ratio, 3),
            "is_persistent": persistent,
            "is_confirmed_anomaly": persistent,  # For backward compatibility
            "eci_evidence": eci_evidence,
            "eci": round(eci, 4),
            "context": context or {},
        }

    # ------------------------------------------------------------------
    # Context normalization
    # ------------------------------------------------------------------

    @staticmethod
    def calculate_context_residual(
        actual_value: float,
        expected_value: float,
    ) -> float:
        """Calculate normalized residual between actual and expected."""
        denominator = max(abs(float(expected_value)), 1e-6)
        residual = abs(float(actual_value) - float(expected_value)) / denominator
        return float(residual)

    def update_with_context_normalization(
        self,
        raw_anomaly_score: float,
        expected_value: float,
        actual_value: float,
        threshold: Optional[float] = None,
        context: Optional[Dict] = None,
    ) -> Dict:
        """
        Update with context residual evidence.
        """
        residual = self.calculate_context_residual(
            actual_value=actual_value,
            expected_value=expected_value,
        )

        context_data = dict(context or {})
        context_data["context_residual"] = round(residual, 4)

        result = self.update(
            raw_anomaly_score=raw_anomaly_score,
            threshold=threshold,
            context=context_data,
        )

        result["context_residual"] = round(residual, 4)
        return result

    # ------------------------------------------------------------------
    # Final fusion
    # ------------------------------------------------------------------

    def confirm(
        self,
        ai_confirmed: bool,
        eci_confirmed: bool,
        require_eci: bool = False,
    ) -> bool:
        """Convert independent evidence into final confirmation."""
        if require_eci:
            return bool(ai_confirmed and eci_confirmed)
        return bool(ai_confirmed)

    # ------------------------------------------------------------------
    # Diagnostics
    # ------------------------------------------------------------------

    def get_persistence_trend(self) -> float:
        if len(self.score_history) < 3:
            return 0.0

        values = list(self.score_history)[-5:]
        if len(values) < 2:
            return 0.0

        x = np.arange(len(values), dtype=float)
        y = np.asarray(values, dtype=float)
        slope = np.polyfit(x, y, 1)[0]
        return round(float(slope), 5)

    def reset(self) -> None:
        self.history.clear()
        self.score_history.clear()
        self.context_history.clear()