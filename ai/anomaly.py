"""
PRIME-Factory Persistence Logic & Temporal Filter v6.0
Rejects transient noise spikes and enforces multi-sample temporal confirmation before alerting (Section 6 & 8).
"""

import collections
import config
import numpy as np
from typing import Dict, Optional


class AnomalyProcessor:
    """
    Anomaly processor with persistence filtering and context-awareness.
    Implements Layers A-E from Section 8.
    """
    
    def __init__(self, window_size: int = config.PERSISTENCE_WINDOW):
        self.window_size = window_size
        self.history = collections.deque(maxlen=window_size)
        self.context_history = collections.deque(maxlen=window_size)
        self._last_context = None

    def update(
        self, 
        raw_anomaly_score: float, 
        threshold: float = 0.5,
        context: Optional[Dict] = None
    ) -> dict:
        """
        Updates the temporal persistence buffer with the latest anomaly score.
        Now includes context-awareness for Layer C/D/E.
        """
        # Base anomaly detection
        is_anomaly = 1.0 if raw_anomaly_score > threshold else 0.0
        self.history.append(is_anomaly)
        
        # Store context if provided
        if context:
            self.context_history.append(context)
            self._last_context = context
        
        # Calculate persistence
        persistence_ratio = sum(self.history) / float(self.window_size)
        is_confirmed = 1 if (len(self.history) == self.window_size and persistence_ratio >= 0.8) else 0
        
        # Layer D: Energy residual evidence
        eci_evidence = 0.0
        if context and 'eci' in context:
            eci_value = context.get('eci', 0.0)
            eci_threshold = config.DECISION_CONFIG.get('eci_deviation_threshold', 0.15)
            eci_evidence = 1.0 if abs(eci_value) > eci_threshold else 0.0
        
        # Layer E: Decision-ready confirmation
        combined_confirmed = 1 if (is_confirmed and (not context or eci_evidence < 0.5)) else 0
        
        return {
            "is_raw_anomaly": int(is_anomaly),
            "persistence_ratio": round(persistence_ratio, 3),
            "is_confirmed_anomaly": is_confirmed,
            "is_combined_evidence": combined_confirmed,
            "eci_evidence": eci_evidence,
            "context": context
        }

    def update_with_context_normalization(
        self,
        raw_anomaly_score: float,
        expected_value: float,
        actual_value: float,
        threshold: float = 0.5,
        context: Optional[Dict] = None
    ) -> dict:
        """
        Layer C: Context-normalized residual features.
        Uses expected vs actual values for context-aware detection.
        """
        # Calculate residual
        residual = abs(actual_value - expected_value) / max(abs(expected_value), 0.001)
        
        # Combine with raw anomaly score
        normalized_score = (raw_anomaly_score + residual) / 2.0
        
        return self.update(normalized_score, threshold, context)

    def reset(self):
        """Clears the temporal history buffer."""
        self.history.clear()
        self.context_history.clear()
        self._last_context = None

    def get_persistence_trend(self) -> float:
        """Calculate trend in persistence over the history window."""
        if len(self.history) < 3:
            return 0.0
        recent = list(self.history)[-5:]
        return sum(recent) / len(recent) if recent else 0.0