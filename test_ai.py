"""
PRIME-Factory AI Tests v6.1
Wrapper for legacy AI tests.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from test_phase2 import TestPhase2


class TestAI(unittest.TestCase):
    """
    Legacy AI tests wrapper.
    All AI tests are now in TestPhase2.
    This ensures backward compatibility.
    """

    def test_anomaly_processor(self):
        """Test anomaly processor."""
        test = TestPhase2()
        test.setUp()
        test.test_anomaly_processor_basic()

    def test_health_index(self):
        """Test health index."""
        test = TestPhase2()
        test.setUp()
        test.test_health_index_calculation()

    def test_rul(self):
        """Test RUL estimation."""
        test = TestPhase2()
        test.setUp()
        test.test_rul_estimation()

    def test_isolation_forest(self):
        """Test Isolation Forest."""
        test = TestPhase2()
        test.setUp()
        test.test_isolation_forest()


def run_all_tests():
    """Run all AI tests."""
    print("=" * 60)
    print("  PRIME-Factory AI Tests (Legacy Wrapper)")
    print("=" * 60)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestAI)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print(f"  Summary: {result.testsRun} tests, {len(result.failures)} failures")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)