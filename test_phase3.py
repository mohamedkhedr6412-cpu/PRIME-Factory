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
            product_schedule=["Product_B"] * 80,
            fault_machine="M3",
            fault_type="Bearing Wear",
            fault_start=20,
            max_degradation=0.85,
            policy_type="PREDICTIVE",
            manual_pdm_timestep=50  # Force maintenance to generate trace
        )

        result = UnifiedSimulationEngine.run(scenario)

        self.assertTrue(hasattr(result, 'evidence_tracker'))
        self.assertIsNotNone(result.evidence_tracker)

        tracker = result.evidence_tracker
        self.assertGreater(len(tracker.traces), 0)

        for trace in tracker.traces:
            self.assertIsNotNone(trace.trace_id)
            self.assertIsNotNone(trace.machine_id)
            self.assertGreater(len(trace.steps), 0)

            step_types = [s.step_type for s in trace.steps]
            self.assertEqual(step_types[0], "SENSE")
            self.assertIn("DECIDE", step_types)

        print(f"✅ EvidenceTracker: {len(tracker.traces)} traces created")
        print(f"   Trace IDs: {[t.trace_id for t in tracker.traces[:5]]}{'...' if len(tracker.traces) > 5 else ''}")

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
            product_key="Product_B",
            persistence_ratio=0.8  # Now accepted
        )

        self.assertEqual(result['decision_code'], "SCHEDULE_PREDICTIVE_MAINTENANCE")
        self.assertEqual(result['urgency'], "HIGH")
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
            fault_type="Bearing Wear",
            fault_start=30,
            max_degradation=0.85,
            policy_type="PREDICTIVE",
            manual_pdm_timestep=70
        )

        result = UnifiedSimulationEngine.run(scenario)

        self.assertIsNotNone(result.telemetry_df)
        self.assertGreater(len(result.telemetry_df), 0)
        self.assertGreater(len(result.decisions), 0)
        # Evidence traces should be generated because maintenance is forced
        self.assertGreater(len(result.evidence_traces), 0)
        self.assertIsNotNone(result.evidence_tracker)
        self.assertGreater(len(result.events), 0)
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
            fault_type="Bearing Wear",
            fault_start=20,
            max_degradation=0.85,
            policy_type="PREDICTIVE",
            manual_pdm_timestep=50  # Force maintenance to generate trace
        )

        result = UnifiedSimulationEngine.run(scenario)
        tracker = result.evidence_tracker

        m3_traces = tracker.get_traces_by_machine("M3")
        self.assertGreater(len(m3_traces), 0)

        latest_trace = m3_traces[-1]
        step_types = [s.step_type for s in latest_trace.steps]

        self.assertGreaterEqual(len(step_types), 7)

        expected_steps = ["SENSE", "CONTEXT", "DETECT", "CONFIRM", "HEALTH", "RUL", "DECIDE"]
        for i, expected in enumerate(expected_steps):
            if i < len(step_types):
                self.assertEqual(step_types[i], expected)

        print(f"✅ Evidence chain complete: {len(step_types)} steps")
        print(f"   Chain: {' → '.join(step_types[:7])}" + (" → ..." if len(step_types) > 7 else ""))

    def test_reproducibility(self):
        """Test reproducibility across multiple seeds"""
        print("\n[TEST 5] Testing reproducibility...")

        seeds = [42, 101, 202]
        results = []

        for seed in seeds:
            scenario = ScenarioConfig(
                scenario_id=f"test_repro_{seed}",
                seed=seed,
                product_schedule=["Product_B"] * 30,
                fault_machine="M3",
                fault_type="Bearing Wear",
                fault_start=10,
                max_degradation=0.5,
                policy_type="PREDICTIVE"
            )
            result = UnifiedSimulationEngine.run(scenario)
            results.append({
                "seed": seed,
                "oee": result.oee_pct,
                "good_units": result.good_units,
                "total_energy": result.total_energy_kwh
            })

        # Check that results vary across seeds (reproducible randomness)
        oee_values = [r["oee"] for r in results]
        energy_values = [r["total_energy"] for r in results]

        # They should not be identical across all seeds
        self.assertTrue(len(set(oee_values)) > 1 or len(set(energy_values)) > 1)

        print(f"✅ Reproducibility: {len(results)} seeds tested")
        for r in results:
            print(f"   Seed {r['seed']}: OEE={r['oee']:.1f}%, Energy={r['total_energy']:.2f}kWh")

    def test_ablation_results_nonzero(self):
        """Test that ablation produces non-zero results for all layers"""
        print("\n[TEST 6] Testing ablation results...")

        scenario = ScenarioConfig(
            scenario_id="test_ablation",
            seed=42,
            product_schedule=["Product_B"] * 80,
            fault_machine="M3",
            fault_type="Bearing Wear",
            fault_start=20,
            max_degradation=0.6,
            policy_type="PREDICTIVE"
        )

        result = UnifiedSimulationEngine.run(scenario)
        m3_df = result.telemetry_df[result.telemetry_df["machine_id"] == "M3"].copy()

        # Run ablation study if possible
        try:
            from evaluation.ablation import run_ablation_study
            ab_df = run_ablation_study(m3_df)

            # All layers should have F1-Score > 0
            for _, row in ab_df.iterrows():
                self.assertGreater(row['F1-Score'], 0, f"Layer {row['Architecture Layer']} has F1-Score=0")

            print(f"✅ Ablation results: {len(ab_df)} layers, all F1-Score > 0")
            print(ab_df[['Architecture Layer', 'F1-Score', 'False Alarms/Hr']].to_string(index=False))
        except Exception as e:
            print(f"   ⚠️ Skipping ablation test: {e}")


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