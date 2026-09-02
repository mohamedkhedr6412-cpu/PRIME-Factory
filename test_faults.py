"""
PRIME-Factory Fault Tests v6.1
Wrapper for legacy fault tests.
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
from test_phase1 import TestPhase1
from test_phase2 import TestPhase2


class TestFaults(unittest.TestCase):
    """
    Legacy fault tests wrapper.
    Fault tests are distributed across TestPhase1 and TestPhase2.
    """

    def test_fault_injection(self):
        """Test fault injection and degradation."""
        print("\n[FAULT] Testing fault injection...")
        test = TestPhase1()
        test.test_fault_injection()

    def test_fault_profiles(self):
        """Test fault profile generation."""
        print("\n[FAULT] Testing fault profiles...")
        test = TestPhase1()
        test.test_fault_profiles()

    def test_fault_signatures(self):
        """Test fault signatures are distinct."""
        print("\n[FAULT] Testing fault signatures...")
        test = TestPhase2()
        test.test_fault_signatures()


def run_all_tests():
    """Run all fault tests."""
    print("=" * 60)
    print("  PRIME-Factory Fault Tests (Legacy Wrapper)")
    print("=" * 60)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestFaults)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print(f"  Summary: {result.testsRun} tests, {len(result.failures)} failures")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)