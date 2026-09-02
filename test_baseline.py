"""
PRIME-Factory Baseline Tests v6.1
Wrapper for legacy baseline tests.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from test_phase1 import TestPhase1


class TestBaseline(unittest.TestCase):
    """
    Legacy baseline tests wrapper.
    All baseline tests are now in TestPhase1.
    This ensures backward compatibility.
    """

    def test_machine_baseline(self):
        """Test machine baseline."""
        test = TestPhase1()
        test.setUp()
        test.test_machine_baseline()

    def test_factory_baseline(self):
        """Test factory baseline."""
        test = TestPhase1()
        test.setUp()
        test.test_factory_integration()

    def test_config(self):
        """Test configuration."""
        test = TestPhase1()
        test.setUp()
        test.test_config_loaded()


def run_all_tests():
    """Run all baseline tests."""
    print("=" * 60)
    print("  PRIME-Factory Baseline Tests (Legacy Wrapper)")
    print("=" * 60)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestBaseline)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print(f"  Summary: {result.testsRun} tests, {len(result.failures)} failures")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)