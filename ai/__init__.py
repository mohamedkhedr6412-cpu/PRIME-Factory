"""
PRIME-Factory AI Package
Exports all AI and analytics components.
"""

from ai.anomaly import AnomalyProcessor
from ai.baseline import ThresholdDetector
from ai.health_index import (
    calculate_health_index_and_evidence,
    estimate_rolling_rul,
    map_hi_to_decision,
    get_hi_confidence
)
from ai.isolation_forest import PRIMEIsolationForest
from ai.decision import DecisionEngine, Decision, get_recommendation_from_state

__all__ = [
    'AnomalyProcessor',
    'ThresholdDetector',
    'calculate_health_index_and_evidence',
    'estimate_rolling_rul',
    'map_hi_to_decision',
    'get_hi_confidence',
    'PRIMEIsolationForest',
    'DecisionEngine',
    'Decision',
    'get_recommendation_from_state',
]