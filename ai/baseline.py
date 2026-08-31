"""
PRIME-Factory Baseline Threshold Detector
Static threshold-based anomaly detection used as a reference benchmark.
"""
import numpy as np
import pandas as pd

class ThresholdDetector:
    def __init__(self, vib_threshold: float = 1.2, temp_threshold: float = 50.0, eci_threshold: float = 0.08):
        self.vib_threshold = vib_threshold
        self.temp_threshold = temp_threshold
        self.eci_threshold = eci_threshold

    def predict(self, row: pd.Series) -> int:
        """يعيد 1 إذا تجاوزت أي إشارة العتبة المحددة (شذوذ)، و0 في الحالة الطبيعية"""
        vib_flag = row.get("vibration_rms", 0.0) > self.vib_threshold if row.get("vibration_rms", 0.0) > 0 else False
        temp_flag = row.get("temperature_c", 0.0) > self.temp_threshold
        eci_flag = row.get("eci", 0.0) > self.eci_threshold
        
        return 1 if (vib_flag or temp_flag or eci_flag) else 0