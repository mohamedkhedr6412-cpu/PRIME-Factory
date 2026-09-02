"""
Phase 3 Integration Test - Final Integration Test
Tests the complete integration of all components with EvidenceTracker in the dashboard
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
import pandas as pd
import config
from core.models import ScenarioConfig
from simulation.engine import UnifiedSimulationEngine
from core.evidence import EvidenceTracker
from ai.decision import DecisionEngine


class TestPhase3(unittest.TestCase):
    """Final integration tests for Phase 3"""
    
    def test_evidence_tracker_in_simulation_result(self):
        """Test that EvidenceTracker is included in SimulationResult"""
        print("\n[TEST 1] Testing EvidenceTracker in SimulationResult...")
        
        scenario = ScenarioConfig(
            scenario_id="test_evidence",
            seed=42,
            product_schedule=["Product_B"] * 50,
            fault_machine="M3",
            fault_type="bearing_wear",
            fault_start=20,
            max_degradation=0.5
        )
        
        result = UnifiedSimulationEngine.run(scenario)
        
        # Check that evidence_tracker is present
        self.assertTrue(hasattr(result, 'evidence_tracker'))
        self.assertIsNotNone(result.evidence_tracker)
        
        # Check that traces were created
        tracker = result.evidence_tracker
        self.assertGreater(len(tracker.traces), 0)
        
        # Check that traces have the correct structure
        for trace in tracker.traces:
            self.assertIsNotNone(trace.trace_id)
            self.assertIsNotNone(trace.machine_id)
            self.assertGreater(len(trace.steps), 0)
            
            # Check that the chain starts with SENSE and ends with DECIDE (or ACTION/OUTCOME)
            step_types = [s.step_type for s in trace.steps]
            self.assertEqual(step_types[0], "SENSE")
            self.assertIn("DECIDE", step_types)
        
        print(f"✅ EvidenceTracker: {len(tracker.traces)} traces created")
        print(f"   Trace IDs: {[t.trace_id for t in tracker.traces]}")
    
    def test_decision_engine_static_method(self):
        """Test the static evaluate_decision method in ai.decision.DecisionEngine"""
        print("\n[TEST 2] Testing DecisionEngine static method...")
        
        result = DecisionEngine.evaluate_decision(
            machine_id="M3",
            current_state=config.STATE_PREDICTIVE_ALERT,
            health_index=45.0,
            rul_minutes=25,
            is_confirmed_anomaly=True,
            eci=0.15,
            penalty_contributions={"AI": 30.0, "Persistence": 25.0},
            product_key="Product_B"
        )
        
        self.assertEqual(result['decision_code'], "SCHEDULE_PREDICTIVE_MAINTENANCE")
        self.assertEqual(result['urgency'], "HIGH")
        # FIXED: Check for "PREDICTIVE" instead of "Predictive"
        self.assertIn("PREDICTIVE", result['title'])
        
        print(f"✅ Static method: {result['decision_code']} - {result['urgency']}")
        print(f"   Title: {result['title']}")
    
    def test_full_integration_chain(self):
        """Test the full integration chain from simulation to evidence"""
        print("\n[TEST 3] Testing full integration chain...")
        
        scenario = ScenarioConfig(
            scenario_id="test_full_chain",
            seed=42,
            product_schedule=["Product_B"] * 100,
            fault_machine="M3",
            fault_type="bearing_wear",
            fault_start=30,
            max_degradation=0.7,
            manual_pdm_timestep=70
        )
        
        result = UnifiedSimulationEngine.run(scenario)
        
        # 1. Check that we have telemetry data
        self.assertIsNotNone(result.telemetry_df)
        self.assertGreater(len(result.telemetry_df), 0)
        
        # 2. Check that we have decisions
        self.assertGreater(len(result.decisions), 0)
        
        # 3. Check that we have evidence traces
        self.assertGreater(len(result.evidence_traces), 0)
        
        # 4. Check that the evidence tracker is present
        self.assertIsNotNone(result.evidence_tracker)
        
        # 5. Check that we have events
        self.assertGreater(len(result.events), 0)
        
        # 6. Check that KPIs are calculated
        self.assertGreater(result.oee_pct, 0)
        self.assertGreater(result.total_energy_kwh, 0)
        
        print(f"✅ Full integration: {len(result.decisions)} decisions, {len(result.evidence_traces)} traces")
        print(f"   OEE: {result.oee_pct:.1f}%, Energy: {result.total_energy_kwh:.2f}kWh")
        print(f"   Events: {len(result.events)}")
    
    def test_evidence_chain_completeness(self):
        """Test that evidence chains are complete (SENSE → ... → DECIDE)"""
        print("\n[TEST 4] Testing evidence chain completeness...")
        
        scenario = ScenarioConfig(
            scenario_id="test_chain_completeness",
            seed=42,
            product_schedule=["Product_B"] * 80,
            fault_machine="M3",
            fault_type="bearing_wear",
            fault_start=20,
            max_degradation=0.6
        )
        
        result = UnifiedSimulationEngine.run(scenario)
        tracker = result.evidence_tracker
        
        # Get traces for M3
        m3_traces = tracker.get_traces_by_machine("M3")
        self.assertGreater(len(m3_traces), 0)
        
        # Check the most recent trace
        latest_trace = m3_traces[-1]
        step_types = [s.step_type for s in latest_trace.steps]
        
        # The chain should have at least 7 steps (SENSE, CONTEXT, DETECT, CONFIRM, HEALTH, RUL, DECIDE)
        self.assertGreaterEqual(len(step_types), 7)
        
        # Check that steps are in the correct order
        expected_steps = ["SENSE", "CONTEXT", "DETECT", "CONFIRM", "HEALTH", "RUL", "DECIDE"]
        for i, expected in enumerate(expected_steps):
            if i < len(step_types):
                self.assertEqual(step_types[i], expected)
        
        print(f"✅ Evidence chain complete: {len(step_types)} steps")
        print(f"   Chain: {' → '.join(step_types[:7])}" + (" → ..." if len(step_types) > 7 else ""))


def run_all_tests():
    """Run all tests with nice output"""
    print("=" * 70)
    print("  PRIME-Factory Phase 3 Integration Tests")
    print("  Testing EvidenceTracker Integration and Full Chain")
    print("=" * 70)
    
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase3)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    print("\n" + "=" * 70)
    print(f"  Summary: {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors")
    print("=" * 70)
    
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)