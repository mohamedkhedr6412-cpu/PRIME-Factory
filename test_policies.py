"""
PRIME-Factory Policy Tests v6.1
Wrapper for legacy policy tests.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from test_phase1 import TestPhase1
from test_phase3 import TestPhase3


class TestPolicies(unittest.TestCase):
    """
    Legacy policy tests wrapper.
    Policy tests are now in TestPhase1 and TestPhase3.
    """

    def test_policy_benchmark(self):
        """Test policy benchmark runs."""
        print("\n[POLICY] Testing policy benchmark...")
        test = TestPhase1()
        test.test_engine_basic_run()

    def test_what_if_analysis(self):
        """Test what-if analysis."""
        print("\n[POLICY] Testing what-if analysis...")
        # Use the what-if test from Phase 3
        test = TestPhase3()
        test.test_full_integration_chain()

    def test_policy_comparison(self):
        """Test policy comparison."""
        print("\n[POLICY] Testing policy comparison...")
        # This is covered by Phase 1 engine tests
        test = TestPhase1()
        test.test_engine_with_fault_and_maintenance()


def run_all_tests():
    """Run all policy tests."""
    print("=" * 60)
    print("  PRIME-Factory Policy Tests (Legacy Wrapper)")
    print("=" * 60)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPolicies)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print(f"  Summary: {result.testsRun} tests, {len(result.failures)} failures")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)