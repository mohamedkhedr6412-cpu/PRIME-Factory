"""
Phase 2 Integration Tests for PRIME-Factory
Tests Decision Engine, Evidence Tracker, and all AI components integration
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
import numpy as np
import pandas as pd
import json
import config

from ai.anomaly import AnomalyProcessor
from ai.baseline import ThresholdDetector
from ai.health_index import (
    calculate_health_index_and_evidence,
    estimate_rolling_rul,
    map_hi_to_decision,
    get_hi_confidence,
    compute_rul_metrics
)
from ai.isolation_forest import PRIMEIsolationForest
from ai.decision import DecisionEngine, Decision

from core.models import ScenarioConfig, SimulationEvent, ResilienceMetrics
from core.evidence import EvidenceTracker, CompleteTrace, EvidenceStep

from energy.eci import calculate_eci, calculate_eci_with_evidence, get_eci_trend
from energy.energy_model import (
    calculate_financial_and_esg_impact,
    calculate_financial_with_evidence
)
from energy.peak_shaving import PeakShavingController

from simulation.factory import PackagingFactory
from simulation.state_machine import AssetStateMachine
from simulation.faults import build_fault_scenario, apply_fault_signature
from simulation.events import EventLog


class TestPhase2(unittest.TestCase):
    """Comprehensive Phase 2 tests for all AI and decision components"""

    def setUp(self):
        self.rng = np.random.RandomState(42)

    def test_anomaly_processor_basic(self):
        """Test 1: Basic anomaly processor functionality"""
        print("\n[TEST 1] Testing AnomalyProcessor...")

        processor = AnomalyProcessor(window_size=5)

        result = processor.update(0.1, threshold=0.5)
        self.assertEqual(result['is_raw_anomaly'], 0)
        self.assertEqual(result['is_confirmed_anomaly'], 0)

        for _ in range(5):
            result = processor.update(0.8, threshold=0.5)

        self.assertEqual(result['is_raw_anomaly'], 1)
        self.assertEqual(result['is_confirmed_anomaly'], 1)
        self.assertGreater(result['persistence_ratio'], 0.8)

        print(f"✅ AnomalyProcessor: Confirmed={result['is_confirmed_anomaly']}, Persistence={result['persistence_ratio']:.3f}")

    def test_anomaly_processor_with_context(self):
        """Test 2: Anomaly processor with context-awareness"""
        print("\n[TEST 2] Testing AnomalyProcessor with context...")

        processor = AnomalyProcessor(window_size=5)
        context = {"product": "Product_B", "speed": 1.0, "load": 1.0, "eci": 0.05}

        result = processor.update(raw_anomaly_score=0.6, threshold=0.5, context=context)

        self.assertIn('context', result)
        self.assertEqual(result['context']['product'], 'Product_B')

        result = processor.update_with_context_normalization(
            raw_anomaly_score=0.4,
            expected_value=5.0,
            actual_value=6.5,
            threshold=0.5,
            context=context
        )

        self.assertIsNotNone(result)
        print(f"✅ Context-Aware Anomaly: ECI evidence={result.get('eci_evidence', 0)}")

    def test_threshold_detector(self):
        """Test 3: Threshold detector (Layer A)"""
        print("\n[TEST 3] Testing ThresholdDetector...")

        detector = ThresholdDetector(
            vib_threshold=1.2,
            temp_threshold=50.0,
            eci_threshold=0.08,
            pf_threshold=0.85
        )

        normal_row = pd.Series({
            'vibration_rms': 0.5,
            'temperature_c': 35.0,
            'eci': 0.02,
            'pf': 0.95
        })
        self.assertEqual(detector.predict(normal_row), 0)

        anomaly_row = pd.Series({
            'vibration_rms': 2.0,
            'temperature_c': 55.0,
            'eci': 0.15,
            'pf': 0.80
        })
        self.assertEqual(detector.predict(anomaly_row), 1)

        evidence = detector.predict_with_evidence(anomaly_row)
        self.assertIn('flags', evidence)
        self.assertTrue(evidence['flags']['temperature'])

        print(f"✅ ThresholdDetector: Normal={detector.predict(normal_row)}, Anomaly={detector.predict(anomaly_row)}")

    def test_health_index_calculation(self):
        """Test 4: Health Index calculation"""
        print("\n[TEST 4] Testing Health Index...")

        result = calculate_health_index_and_evidence(
            anomaly_score=0.1,
            persistence_ratio=0.2,
            eci=0.02,
            temp_c=35.0,
            vib_rms=0.5
        )
        self.assertGreater(result['health_index'], 80)
        self.assertIn('penalty_contributions', result)

        result = calculate_health_index_and_evidence(
            anomaly_score=0.8,
            persistence_ratio=0.9,
            eci=0.25,
            temp_c=55.0,
            vib_rms=2.0
        )
        self.assertLess(result['health_index'], 50)

        context = {"is_legitimate_change": True}
        result = calculate_health_index_and_evidence(
            anomaly_score=0.8,
            persistence_ratio=0.9,
            eci=0.25,
            temp_c=55.0,
            vib_rms=2.0,
            context=context
        )
        self.assertIn('raw_components', result)

        print(f"✅ Health Index: Healthy={calculate_health_index_and_evidence(0.1, 0.2, 0.02, 35, 0.5)['health_index']:.1f}, "
              f"Degraded={result['health_index']:.1f}")

    def test_rul_estimation(self):
        """Test 5: RUL estimation"""
        print("\n[TEST 5] Testing RUL estimation...")

        hi_history = [100 - i * 2 for i in range(20)]

        rul, rul_str = estimate_rolling_rul(
            hi_history=hi_history,
            current_state=config.STATE_DEGRADING,
            current_t=50,
            window_size=15
        )
        self.assertIsNotNone(rul)
        self.assertGreater(rul, 0)

        rul, rul_str = estimate_rolling_rul(
            hi_history=hi_history,
            current_state=config.STATE_CRITICAL,
            current_t=50,
            window_size=15
        )
        self.assertIsNotNone(rul)
        self.assertTrue(len(rul_str) > 0)

        print(f"✅ RUL: {rul} minutes ({rul_str})")

    def test_hi_mapping(self):
        """Test 6: HI to decision mapping"""
        print("\n[TEST 6] Testing HI mapping...")

        self.assertEqual(
            map_hi_to_decision(95.0),
            "NORMAL (Continue Standard Operation)"
        )
        self.assertEqual(
            map_hi_to_decision(60.0),
            "MONITOR (Elevate Inspection & Diagnostics)"
        )
        self.assertEqual(
            map_hi_to_decision(40.0),
            "PLAN_MAINTENANCE (Schedule 15-min Intervention)"
        )
        self.assertEqual(
            map_hi_to_decision(5.0),
            "CRITICAL (Immediate Controlled Stop / Derate)"
        )

        self.assertEqual(get_hi_confidence(80, 3), 0.3)
        self.assertEqual(get_hi_confidence(80, 10), 0.6)
        self.assertEqual(get_hi_confidence(80, 20), 0.8)
        self.assertEqual(get_hi_confidence(80, 40), 0.95)

        print(f"✅ HI Mapping: All mappings correct")

    def test_decision_engine_all_states(self):
        """Test 7: Decision engine for all states"""
        print("\n[TEST 7] Testing DecisionEngine...")

        engine = DecisionEngine()

        test_cases = [
            (config.STATE_NORMAL, 95.0, None, 0.02, False, "LOW"),
            (config.STATE_DEGRADING, 80.0, None, 0.05, False, "LOW"),
            (config.STATE_WARNING, 60.0, None, 0.08, True, "MEDIUM"),
            (config.STATE_PREDICTIVE_ALERT, 40.0, 25, 0.12, True, "HIGH"),
            (config.STATE_CRITICAL, 15.0, 5, 0.30, True, "CRITICAL"),
            (config.STATE_FAILED, 0.0, 0, 0.50, True, "CRITICAL"),
        ]

        for state, hi, rul, eci, confirmed, expected_priority in test_cases:
            decision = engine.evaluate(
                machine_id="M3",
                timestamp=0,
                current_state=state,
                health_index=hi,
                rul_minutes=rul,
                eci=eci,
                is_confirmed_anomaly=confirmed
            )
            self.assertEqual(decision.priority, expected_priority)

            # FIXED: Check recommendation contains appropriate text
            if state == config.STATE_PREDICTIVE_ALERT:
                self.assertIn("PREDICTIVE", decision.recommendation)
            elif state == config.STATE_NORMAL:
                self.assertIn("NORMAL", decision.recommendation)
            elif state == config.STATE_CRITICAL:
                # FIXED: For CRITICAL with RUL<=10, recommendation contains "URGENT"
                if rul is not None and rul <= 10:
                    self.assertIn("URGENT", decision.recommendation)
                else:
                    self.assertIn("CRITICAL", decision.recommendation)
            elif state == config.STATE_FAILED:
                self.assertIn("EMERGENCY", decision.recommendation)

        self.assertEqual(len(engine.get_decision_history()), len(test_cases))
        print(f"✅ DecisionEngine: {len(test_cases)} states tested successfully")

    def test_decision_energy_awareness(self):
        """Test 8: Decision engine energy awareness"""
        print("\n[TEST 8] Testing DecisionEngine energy awareness...")

        engine = DecisionEngine()

        decision = engine.evaluate(
            machine_id="M3",
            timestamp=0,
            current_state=config.STATE_NORMAL,
            health_index=95.0,
            rul_minutes=None,
            eci=0.25,
            is_confirmed_anomaly=False
        )
        self.assertIn("ENERGY", decision.recommendation)

        decision = engine.evaluate(
            machine_id="M3",
            timestamp=0,
            current_state=config.STATE_NORMAL,
            health_index=95.0,
            rul_minutes=None,
            eci=0.02,
            is_confirmed_anomaly=False
        )
        self.assertNotIn("ENERGY", decision.recommendation)

        print(f"✅ Energy Awareness: Detected high ECI={decision.evidence_summary['eci']}")

    def test_decision_with_context(self):
        """Test 9: Decision engine with context"""
        print("\n[TEST 9] Testing DecisionEngine with context...")

        engine = DecisionEngine()
        context = {"product": "Product_C", "production_rate": 150, "shift": "day"}

        decision = engine.evaluate(
            machine_id="M3",
            timestamp=100,
            current_state=config.STATE_PREDICTIVE_ALERT,
            health_index=45.0,
            rul_minutes=25,
            eci=0.15,
            is_confirmed_anomaly=True,
            production_units=5000,
            context=context
        )

        self.assertEqual(decision.evidence_summary['context']['product'], 'Product_C')
        self.assertIn('PREDICTIVE', decision.recommendation)

        print(f"✅ Context-Aware Decision: {decision.recommendation[:60]}...")

    def test_evidence_tracker_basic(self):
        """Test 10: Evidence tracker basic functionality"""
        print("\n[TEST 10] Testing EvidenceTracker...")

        tracker = EvidenceTracker()

        trace = tracker.create_complete_chain(
            machine_id="M3",
            timestamp=0,
            sensor_data={"vibration": 0.8, "temperature": 35.0, "power": 6.0},
            context={"product": "Product_B", "speed": 1.0},
            anomaly_score=0.12,
            persistence_ratio=0.9,
            is_confirmed=True,
            health_index=85.0,
            rul_minutes=120,
            eci=0.05,
            state=config.STATE_DEGRADING,
            decision_recommendation="Increase monitoring",
            decision_id="DEC_0001"
        )

        self.assertEqual(len(trace.steps), 7)
        self.assertEqual(trace.get_chain()[0], "SENSE")
        self.assertEqual(trace.get_chain()[-1], "DECIDE")

        tracker.complete_trace(
            trace,
            end_timestamp=50,
            action_taken="Increased monitoring",
            outcome={"status": "resolved", "health_improved": True}
        )

        self.assertEqual(len(trace.steps), 9)
        self.assertEqual(trace.final_outcome, "resolved")

        retrieved = tracker.get_trace(trace.trace_id)
        self.assertIsNotNone(retrieved)

        print(f"✅ EvidenceTracker: {len(tracker.traces)} traces, {len(trace.steps)} steps")

    def test_evidence_tracker_filtering(self):
        """Test 11: Evidence tracker filtering"""
        print("\n[TEST 11] Testing EvidenceTracker filtering...")

        tracker = EvidenceTracker()

        for i in range(3):
            trace = tracker.create_complete_chain(
                machine_id=f"M{i+1}",
                timestamp=i * 10,
                sensor_data={"vibration": 0.5 + i * 0.3},
                context={"product": "Product_B"},
                anomaly_score=0.1 + i * 0.1,
                persistence_ratio=0.8,
                is_confirmed=True,
                health_index=90 - i * 10,
                rul_minutes=100 - i * 20,
                eci=0.02 + i * 0.03,
                state=config.STATE_DEGRADING,
                decision_recommendation="Monitor",
                decision_id=f"DEC_{i:04d}"
            )

        m1_traces = tracker.get_traces_by_machine("M1")
        self.assertEqual(len(m1_traces), 1)

        recent = tracker.get_recent_traces(2)
        self.assertEqual(len(recent), 2)

        df = tracker.export_to_dataframe()
        self.assertGreater(len(df), 0)
        self.assertIn('trace_id', df.columns)
        self.assertIn('step_type', df.columns)

        print(f"✅ Filtering: {len(tracker.traces)} traces, {len(df)} rows in export")

    def test_eci_calculation(self):
        """Test 12: ECI calculation"""
        print("\n[TEST 12] Testing ECI calculation...")

        expected = calculate_eci(
            actual_power_kw=7.0,
            machine_id="M3",
            product_key="Product_B"
        )
        self.assertIsNotNone(expected)

        evidence = calculate_eci_with_evidence(
            actual_power_kw=8.0,
            machine_id="M3",
            product_key="Product_B",
            context={"product_change": False}
        )
        self.assertIn('severity', evidence)
        self.assertIn('recommendation', evidence)

        eci_history = [0.02, 0.05, 0.08, 0.12, 0.15]
        trend = get_eci_trend(eci_history, window=3)
        self.assertGreater(trend, 0)

        print(f"✅ ECI: Value={expected:.3f}, Trend={trend:.3f}")

    def test_energy_impact_calculation(self):
        """Test 13: Energy impact calculation"""
        print("\n[TEST 13] Testing Energy Impact...")

        result = calculate_financial_and_esg_impact(
            total_energy_kwh=100.0,
            downtime_minutes=30.0,
            good_units=500,
            avg_pf=0.88
        )

        self.assertIn('energy_cost_usd', result)
        self.assertIn('carbon_kg', result)
        self.assertGreater(result['total_operational_cost_usd'], 0)

        evidence = calculate_financial_with_evidence(
            total_energy_kwh=100.0,
            downtime_minutes=30.0,
            good_units=500,
            avg_pf=0.88,
            maintenance_events=1
        )

        self.assertIn('maintenance_cost_usd', evidence)
        self.assertIn('total_cost_with_maintenance_usd', evidence)

        print(f"✅ Energy Impact: Cost=${result['total_operational_cost_usd']:.2f}, Carbon={result['carbon_kg']:.2f}kg")

    def test_peak_shaving(self):
        """Test 14: Peak shaving functionality"""
        print("\n[TEST 14] Testing PeakShaving...")

        controller = PeakShavingController(
            peak_start=240,
            peak_end=360,
            derate_ratio=0.90,
            enabled=True
        )

        self.assertEqual(controller.apply_peak_shaving(300), 0.90)
        self.assertEqual(controller.apply_peak_shaving(100), 1.0)

        controller.apply_peak_shaving(300, current_power=10.0)
        self.assertIsNotNone(controller._history[-1]['power_after'])

        impact = controller.get_peak_shaving_impact()
        self.assertIn('total_events', impact)

        print(f"✅ PeakShaving: Events={impact['total_events']}, Saved={impact['energy_saved_kwh']:.3f}kWh")

    def test_isolation_forest(self):
        """Test 15: Isolation Forest integration"""
        print("\n[TEST 15] Testing IsolationForest...")

        np.random.seed(42)
        n_samples = 100
        data = pd.DataFrame({
            'speed_rpm': np.random.normal(1500, 100, n_samples),
            'load_factor': np.random.normal(0.8, 0.1, n_samples),
            'vibration_rms': np.random.normal(0.5, 0.1, n_samples),
            'temperature_c': np.random.normal(35, 5, n_samples),
            'current_a': np.random.normal(10, 2, n_samples),
            'power_kw': np.random.normal(6, 1, n_samples)
        })

        model = PRIMEIsolationForest(contamination=0.02, seed=42)
        model.fit(data)

        scores = model.predict_anomaly_score(data)
        self.assertEqual(len(scores), n_samples)
        self.assertTrue(all(0 <= s <= 1 for s in scores))

        result_df = model.predict_with_evidence(data)
        self.assertIn('is_anomaly', result_df.columns)
        self.assertIn('anomaly_confidence', result_df.columns)

        print(f"✅ IsolationForest: Fitted with {n_samples} samples, Score range=[{min(scores):.3f}, {max(scores):.3f}]")

    def test_full_ai_pipeline(self):
        """Test 16: Full AI pipeline integration"""
        print("\n[TEST 16] Testing Full AI Pipeline...")

        sample_data = pd.DataFrame({
            'speed_rpm': [1500, 1500, 1500, 1500, 1500, 1500, 1500],
            'load_factor': [0.8, 0.8, 0.8, 0.8, 0.8, 0.8, 0.8],
            'vibration_rms': [0.5, 0.6, 0.8, 1.2, 2.0, 3.0, 4.0],
            'temperature_c': [35, 37, 42, 50, 60, 70, 80],
            'current_a': [10, 11, 12, 14, 18, 22, 26],
            'power_kw': [6, 6.5, 7.2, 8.5, 10.0, 12.0, 14.0],
            'eci': [0.02, 0.05, 0.10, 0.20, 0.35, 0.50, 0.70]
        })

        detector = ThresholdDetector()
        detections = [detector.predict(row) for _, row in sample_data.iterrows()]

        processor = AnomalyProcessor(window_size=3)
        persistence_results = []
        for _, row in sample_data.iterrows():
            score = min(1.0, abs(row['eci']) * 2.0)
            result = processor.update(score, threshold=0.5)
            persistence_results.append(result)

        hi_results = []
        for _, row in sample_data.iterrows():
            hi = calculate_health_index_and_evidence(
                anomaly_score=min(1.0, abs(row['eci']) * 2.0),
                persistence_ratio=0.9,
                eci=row['eci'],
                temp_c=row['temperature_c'],
                vib_rms=row['vibration_rms']
            )
            hi_results.append(hi)

        engine = DecisionEngine()
        decisions = []
        for i, row in sample_data.iterrows():
            hi_value = hi_results[i]['health_index']
            is_confirmed = persistence_results[i]['is_confirmed_anomaly'] == 1

            if hi_value <= config.HI_THRESHOLDS["CRITICAL"]:
                state = config.STATE_CRITICAL
            elif hi_value <= config.HI_THRESHOLDS["MONITOR"]:
                state = config.STATE_PREDICTIVE_ALERT
            elif hi_value <= config.HI_THRESHOLDS["HEALTHY"]:
                state = config.STATE_WARNING
            else:
                state = config.STATE_NORMAL

            decision = engine.evaluate(
                machine_id="M3",
                timestamp=i,
                current_state=state,
                health_index=hi_value,
                rul_minutes=30 - i * 5 if state in [config.STATE_CRITICAL, config.STATE_PREDICTIVE_ALERT] else None,
                eci=row['eci'],
                is_confirmed_anomaly=is_confirmed
            )
            decisions.append(decision)

        critical_count = len([d for d in decisions if d.priority == "CRITICAL"])
        self.assertGreater(critical_count, 0)

        print(f"✅ AI Pipeline: {len(sample_data)} samples processed")
        print(f"   Decisions: {[d.priority for d in decisions]}")

    def test_factory_with_decision_integration(self):
        """Test 17: Factory with decision integration"""
        print("\n[TEST 17] Testing Factory with Decision Integration...")

        factory = PackagingFactory()
        factory.start()

        for step in range(20):
            factory.step()

        state = factory.get_state_summary()
        self.assertIsNotNone(state)
        self.assertEqual(len(state['machines']), 5)

        print(f"✅ Factory Integration: OEE={state['kpis']['oee']:.3f}, Units={state['kpis']['good_units']}")

    def test_full_evidence_cycle(self):
        """Test 18: Full evidence cycle from sensor to outcome"""
        print("\n[TEST 18] Testing Full Evidence Cycle...")

        tracker = EvidenceTracker()
        engine = DecisionEngine()
        processor = AnomalyProcessor(window_size=3)

        machine_id = "M3"
        timestamp = 0

        sensor_data = {
            "vibration_rms": 1.8,
            "temperature_c": 52.0,
            "active_power_kw": 7.2,
            "power_factor": 0.92
        }
        context = {
            "product": "Product_B",
            "speed": 1.0,
            "load": 1.0,
            "eci": 0.12
        }

        anomaly_score = min(1.0, abs(context['eci']) * 3.0)

        persistence = 0.0
        is_confirmed = False
        for i in range(5):
            result = processor.update(anomaly_score, threshold=0.5)
            persistence = result['persistence_ratio']
            is_confirmed = result['is_confirmed_anomaly'] == 1

        hi_result = calculate_health_index_and_evidence(
            anomaly_score=anomaly_score,
            persistence_ratio=persistence,
            eci=context['eci'],
            temp_c=sensor_data['temperature_c'],
            vib_rms=sensor_data['vibration_rms']
        )

        rul_history = [100 - i * 3 for i in range(30)]
        rul, rul_str = estimate_rolling_rul(
            rul_history,
            current_state=config.STATE_DEGRADING,
            current_t=timestamp
        )

        decision = engine.evaluate(
            machine_id=machine_id,
            timestamp=timestamp,
            current_state=config.STATE_DEGRADING,
            health_index=hi_result['health_index'],
            rul_minutes=rul,
            eci=context['eci'],
            is_confirmed_anomaly=is_confirmed
        )

        trace = tracker.create_complete_chain(
            machine_id=machine_id,
            timestamp=timestamp,
            sensor_data=sensor_data,
            context=context,
            anomaly_score=anomaly_score,
            persistence_ratio=persistence,
            is_confirmed=is_confirmed,
            health_index=hi_result['health_index'],
            rul_minutes=rul,
            eci=context['eci'],
            state=config.STATE_DEGRADING,
            decision_recommendation=decision.recommendation,
            decision_id=decision.decision_id
        )

        action_taken = "Scheduled maintenance"
        tracker.complete_trace(
            trace,
            end_timestamp=timestamp + 15,
            action_taken=action_taken,
            outcome={"status": "recovered", "health_index": 90.0}
        )

        self.assertEqual(len(trace.steps), 9)
        self.assertEqual(trace.get_chain()[0], "SENSE")
        self.assertEqual(trace.get_chain()[-1], "OUTCOME")
        self.assertEqual(trace.final_outcome, "recovered")

        print(f"✅ Full Evidence Cycle: {len(trace.steps)} steps")
        print(f"   Chain: {' → '.join(trace.get_chain()[:3])} ... → {trace.get_chain()[-1]}")

    def test_rul_validation(self):
        """Test 19: RUL validation"""
        print("\n[TEST 19] Testing RUL validation...")

        # Simulate degradation history
        degradation_history = [i * 0.01 for i in range(100)]
        hi_history = [100 - d * 100 for d in degradation_history]

        rul, rul_str = estimate_rolling_rul(
            hi_history=hi_history,
            current_state=config.STATE_DEGRADING,
            current_t=50,
            window_size=15
        )

        # Calculate actual time to critical
        from ai.health_index import calculate_actual_time_to_critical
        actual_rul = calculate_actual_time_to_critical(degradation_history, 50, 0.75)

        if rul is not None and actual_rul is not None:
            self.assertGreaterEqual(actual_rul, 0)
            print(f"✅ RUL Validation: Estimated={rul}, Actual={actual_rul}")

            # Compute metrics
            metrics = compute_rul_metrics([rul], [actual_rul])
            print(f"   Metrics: {metrics}")

    def test_fault_signatures(self):
        """Test 20: Fault signatures are distinct"""
        print("\n[TEST 20] Testing fault signatures...")

        faults = ["bearing_wear", "friction", "electrical_anomaly"]
        signatures = {}

        for fault_type in faults:
            scenario = build_fault_scenario(
                machine_id="M3",
                fault_type=fault_type,
                severity=0.5,
                start_time=10,
                total_timesteps=100
            )
            signatures[fault_type] = scenario["signature"]

        # Verify signatures are different
        self.assertNotEqual(
            signatures["bearing_wear"].get("vibration_mult", 0),
            signatures["friction"].get("vibration_mult", 0)
        )
        self.assertNotEqual(
            signatures["bearing_wear"].get("pf_decay", 0),
            signatures["electrical_anomaly"].get("pf_decay", 0)
        )

        print(f"✅ Fault signatures: {len(signatures)} distinct signatures verified")


def run_all_tests():
    """Run all tests with nice output"""
    print("=" * 70)
    print("  PRIME-Factory Phase 2 Integration Tests")
    print("  Testing All AI, Decision, and Evidence Components")
    print("=" * 70)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase2)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 70)
    print(f"  Summary: {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors")
    print("=" * 70)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)