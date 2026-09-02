"""
PRIME-Factory Decision Engine - Dashboard Compatibility Wrapper v6.1

IMPORTANT: This is a WRAPPER only.
The canonical decision logic is in ai/decision.py.

DO NOT add independent decision logic here.
"""

from ai.decision import (
    DecisionEngine,
    Decision,
    get_recommendation_from_state,
    evaluate_decision_for_dashboard
)

# Re-export everything from canonical engine
__all__ = [
    "DecisionEngine",
    "Decision",
    "get_recommendation_from_state",
    "evaluate_decision_for_dashboard",
]

# For backward compatibility with old imports
# dashboard/app.py imports:
# from control.decision_engine import DecisionEngine
# This will work because DecisionEngine is re-exported.