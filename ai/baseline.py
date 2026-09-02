"""
PRIME-Factory Baseline Threshold Detector v6.0
Architecture Layer A: Conventional static threshold detector for vibration, temperature, ECI, and PF (Section 8).
Now integrated with decision engine and evidence tracking.
"""

import pandas as pd
import config
from typing import Dict, Any, Optional


class ThresholdDetector:
    """
    Static threshold-based anomaly detector (Layer A).
    Flags anomalies when any parameter exceeds fixed limits.
    """
    
    def __init__(
        self, 
        vib_threshold: float = 1.2, 
        temp_threshold: float = 50.0, 
        eci_threshold: float = 0.08,
        pf_threshold: float = config.PF_ALERT_THRESHOLD
    ):
        self.vib_threshold = vib_threshold
        self.temp_threshold = temp_threshold
        self.eci_threshold = eci_threshold
        self.pf_threshold = pf_threshold
        self._last_detections = []

    def predict(self, row: pd.Series) -> int:
        """
        Flags an anomaly if any single engineering parameter exceeds fixed static limits.
        Returns 1 for anomaly, 0 for normal.
        """
        vib_flag = row.get("vibration_rms", 0.0) > self.vib_threshold if row.get("vibration_rms", 0.0) > 0 else False
        temp_flag = row.get("temperature_c", 0.0) > self.temp_threshold
        eci_flag = abs(row.get("eci", 0.0)) > self.eci_threshold
        pf_flag = row.get("pf", 1.0) < self.pf_threshold
        
        result = 1 if (vib_flag or temp_flag or eci_flag or pf_flag) else 0
        self._last_detections.append(result)
        return result

    def predict_with_evidence(self, row: pd.Series) -> Dict[str, Any]:
        """
        Flags anomaly and returns detailed evidence for decision trace.
        """
        vib_flag = row.get("vibration_rms", 0.0) > self.vib_threshold if row.get("vibration_rms", 0.0) > 0 else False
        temp_flag = row.get("temperature_c", 0.0) > self.temp_threshold
        eci_flag = abs(row.get("eci", 0.0)) > self.eci_threshold
        pf_flag = row.get("pf", 1.0) < self.pf_threshold
        
        is_anomaly = 1 if (vib_flag or temp_flag or eci_flag or pf_flag) else 0
        
        return {
            "is_anomaly": is_anomaly,
            "flags": {
                "vibration": vib_flag,
                "temperature": temp_flag,
                "eci": eci_flag,
                "power_factor": pf_flag
            },
            "thresholds": {
                "vibration": self.vib_threshold,
                "temperature": self.temp_threshold,
                "eci": self.eci_threshold,
                "power_factor": self.pf_threshold
            },
            "current_values": {
                "vibration": row.get("vibration_rms", 0.0),
                "temperature": row.get("temperature_c", 0.0),
                "eci": row.get("eci", 0.0),
                "power_factor": row.get("pf", 1.0)
            }
        }

    def reset(self):
        """Clear detection history."""
        self._last_detections = []

    def get_detection_rate(self, window: int = 20) -> float:
        """
        Calculate the anomaly detection rate over the last N samples.
        """
        if not self._last_detections:
            return 0.0
        recent = self._last_detections[-window:]
        return sum(recent) / len(recent) if recent else 0.0