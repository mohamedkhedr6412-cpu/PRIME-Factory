"""
PRIME-Factory Baseline Threshold Detector v6.0
Architecture Layer A: Conventional static threshold detector for vibration, temperature, ECI, and PF (Section 8).
"""

import pandas as pd
import config

class ThresholdDetector:
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

    def predict(self, row: pd.Series) -> int:
        """Flags an anomaly if any single engineering parameter exceeds fixed static limits."""
        vib_flag = row.get("vibration_rms", 0.0) > self.vib_threshold if row.get("vibration_rms", 0.0) > 0 else False
        temp_flag = row.get("temperature_c", 0.0) > self.temp_threshold
        eci_flag = abs(row.get("eci", 0.0)) > self.eci_threshold
        pf_flag = row.get("pf", 1.0) < self.pf_threshold
        return 1 if (vib_flag or temp_flag or eci_flag or pf_flag) else 0