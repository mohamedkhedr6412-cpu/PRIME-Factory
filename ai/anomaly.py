"""
PRIME-Factory Persistence Logic & Context-Aware Anomaly Processor
Filters transient spikes using a sliding window: P_t = (1/N) * Sum(I_{t-k})
"""
import collections
import config

class AnomalyProcessor:
    def __init__(self, window_size: int = config.PERSISTENCE_WINDOW):
        self.window_size = window_size
        self.history = collections.deque(maxlen=window_size)

    def update(self, raw_anomaly_score: float, threshold: float = 0.5) -> dict:
        """
        تحديث نافذة الاستمرارية لحساب نسبة استمرار الشذوذ
        """
        is_anomaly = 1.0 if raw_anomaly_score > threshold else 0.0
        self.history.append(is_anomaly)
        
        # حساب نسبة العينات الشاذة المتتالية (Persistence Ratio)
        persistence_ratio = sum(self.history) / float(self.window_size)
        is_confirmed = 1 if len(self.history) == self.window_size and persistence_ratio >= 0.8 else 0
        
        return {
            "is_raw_anomaly": int(is_anomaly),
            "persistence_ratio": round(persistence_ratio, 3),
            "is_confirmed_anomaly": is_confirmed
        }

    def reset(self):
        self.history.clear()
        