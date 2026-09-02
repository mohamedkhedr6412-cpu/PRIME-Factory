"""
Phase 1 Integration Tests for PRIME-Factory
Tests all core simulation components for consistency and correctness
"""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import unittest
import numpy as np
import pandas as pd
import config
from simulation.machines import Machine
from simulation.factory import PackagingFactory
from simulation.state_machine import AssetStateMachine
from simulation.faults import (
    generate_degradation_profile,
    generate_friction_profile,
    generate_electrical_profile,
    build_fault_scenario
)
from simulation.events import EventLog, SimulationEvent
from simulation.engine import UnifiedSimulationEngine, ScenarioConfig


class TestPhase1(unittest.TestCase):
    """Comprehensive Phase 1 tests"""

    def test_config_loaded(self):
        """Test 1: Verify config has all required sections"""
        print("\n[TEST 1] Verifying configuration...")

        required_attrs = [
            'MACHINES', 'PRODUCTS', 'STATE_NORMAL', 'STATE_DEGRADING',
            'STATE_WARNING', 'STATE_PREDICTIVE_ALERT', 'STATE_CRITICAL',
            'STATE_FAILED', 'STATE_MAINTENANCE', 'STATE_RECOVERY',
            'HI_THRESHOLDS', 'HI_WEIGHTS', 'MAINTENANCE_DURATION_MINUTES',
            'DECISION_CONFIG', 'COST_PARAMETERS', 'BENCHMARK_CONFIG',
            'PDM_TRIGGER_HI', 'PDM_TRIGGER_RUL'
        ]

        missing = [attr for attr in required_attrs if not hasattr(config, attr)]
        self.assertEqual(len(missing), 0, f"Missing config attributes: {missing}")
        print(f"✅ All {len(required_attrs)} config sections present")

    def test_machine_baseline(self):
        """Test 2: Verify machine creates baseline telemetry"""
        print("\n[TEST 2] Testing machine baseline...")

        machine = Machine(machine_id="M3", name="Sealer", has_vibration=True, nominal_kw=6.0)

        self.assertEqual(machine.degradation_level, 0.0)
        self.assertEqual(machine.health_index, 100.0)

        record = machine.step("Product_B", dt_minutes=1.0)

        required_fields = [
            'machine_id', 'timestep', 'product', 'degradation',
            'health_index', 'state', 'power_kw', 'power_factor'
        ]
        for field in required_fields:
            self.assertIn(field, record, f"Missing field: {field}")

        self.assertGreater(record['power_kw'], 0)
        self.assertLess(record['power_kw'], 20)

        print(f"✅ Machine M3: Power={record['power_kw']:.2f}kW, PF={record['power_factor']:.3f}")

    def test_fault_injection(self):
        """Test 3: Verify fault injection and degradation"""
        print("\n[TEST 3] Testing fault injection...")

        machine = Machine(machine_id="M3", name="Sealer", has_vibration=True, nominal_kw=6.0)
        machine.inject_fault("bearing_wear", 0.5, start_time=0)

        for _ in range(10):
            machine.step("Product_B", dt_minutes=1.0)

        self.assertGreater(machine.degradation_level, 0.0)
        self.assertLess(machine.health_index, 100.0)

        print(f"✅ Fault: Degradation={machine.degradation_level:.3f}, HI={machine.health_index:.1f}")

    def test_state_machine_hysteresis(self):
        """Test 4: Verify state machine with hysteresis"""
        print("\n[TEST 4] Testing state machine hysteresis...")

        sm = AssetStateMachine("M3")

        states = []
        for i in range(20):
            deg = min(1.0, i * 0.05)
            hi = 100 * (1 - deg)
            new_state = sm.update_state_with_hysteresis(
                degradation=deg,
                health_index=hi,
                is_confirmed_anomaly=(hi < 50),
                hysteresis_count=3
            )
            states.append(new_state)

        transitions = sum(1 for i in range(1, len(states)) if states[i] != states[i-1])
        self.assertLessEqual(transitions, 10, f"Too many transitions: {transitions}")

        print(f"✅ State transitions: {transitions} over {len(states)} steps")
        print(f"   Final state: {states[-1]}")

    def test_factory_integration(self):
        """Test 5: Verify factory integrates all components"""
        print("\n[TEST 5] Testing factory integration...")

        factory = PackagingFactory()
        factory.start()

        for _ in range(50):
            factory.step()

        state = factory.get_state_summary()

        self.assertGreaterEqual(state['kpis']['oee'], 0)
        self.assertLessEqual(state['kpis']['oee'], 1.0)
        self.assertGreater(state.get('kpis', {}).get('good_units', 0), -1)
        self.assertGreater(state.get('kpis', {}).get('total_energy_kwh', -1), -1)

        self.assertEqual(len(state['machines']), 5)

        print(f"✅ Factory: OEE={state['kpis']['oee']:.3f}, Units={state['kpis']['good_units']}")
        print(f"   Energy={state['kpis']['total_energy_kwh']:.2f}kWh")

    def test_fault_profiles(self):
        """Test 6: Verify fault profile generation"""
        print("\n[TEST 6] Testing fault profiles...")

        profile = generate_degradation_profile(100, 50, 0.85)

        self.assertEqual(len(profile), 100)
        self.assertEqual(profile[0], 0.0)
        self.assertAlmostEqual(profile[-1], 0.85, delta=0.20)

        for i in range(1, len(profile)):
            self.assertGreaterEqual(profile[i], profile[i-1])

        scenario = build_fault_scenario("M3", "bearing_wear", 0.7, 30, 100)
        self.assertEqual(scenario['machine_id'], "M3")
        self.assertEqual(len(scenario['degradation_profile']), 100)

        print(f"✅ Fault profiles generated correctly")
        print(f"   Final degradation value: {profile[-1]:.4f} (target: 0.85)")

    def test_fault_profiles_linear(self):
        """Test 6b: Verify linear fault profile generation"""
        print("\n[TEST 6b] Testing linear fault profiles...")

        profile = generate_friction_profile(100, 50, 0.40)
        self.assertEqual(len(profile), 100)
        self.assertEqual(profile[0], 0.0)
        self.assertAlmostEqual(profile[-1], 0.40, delta=0.01)

        profile = generate_electrical_profile(100, 50, 0.40)
        self.assertEqual(len(profile), 100)
        self.assertEqual(profile[0], 0.0)
        self.assertAlmostEqual(profile[-1], 0.40, delta=0.01)

        print(f"✅ Linear fault profiles generated correctly")

    def test_event_log(self):
        """Test 7: Verify event logging"""
        print("\n[TEST 7] Testing event log...")

        log = EventLog()

        log.add_event(0, "TEST_EVENT", "INFO", "M3", "Test message")
        log.add_event(1, "WARNING_EVENT", "WARNING", "M1", "Warning message")
        log.add_event(2, "ERROR_EVENT", "ERROR", "M5", "Error message")

        df = log.get_events_as_dataframe()

        self.assertEqual(len(df), 3)
        self.assertEqual(log.get_summary_stats()['total_events'], 3)
        self.assertEqual(len(log.get_events_by_severity("WARNING")), 1)

        print(f"✅ Event log: {len(log.events)} events logged")

    def test_engine_basic_run(self):
        """Test 8: Verify engine runs a complete scenario"""
        print("\n[TEST 8] Testing unified engine...")

        scenario = ScenarioConfig(
            scenario_id="test_baseline",
            seed=42,
            product_schedule=["Product_B"] * 50,
            fault_machine="M3",
            fault_type="None (Healthy Baseline)",
            fault_start=999,
            max_degradation=0.0,
            policy_type="CORRECTIVE"
        )

        result = UnifiedSimulationEngine.run(scenario)

        self.assertIsNotNone(result.telemetry_df)
        self.assertGreater(len(result.telemetry_df), 0)
        self.assertGreater(result.good_units, 0)
        self.assertGreater(result.total_energy_kwh, 0)
        self.assertGreater(result.oee_pct, 50)

        print(f"✅ Engine: OEE={result.oee_pct:.1f}%, Units={result.good_units}")
        print(f"   Energy={result.total_energy_kwh:.2f}kWh, Cost=${result.total_operational_cost_usd:.2f}")

    def test_engine_with_fault_and_maintenance(self):
        """Test 9: Verify engine with fault and maintenance"""
        print("\n[TEST 9] Testing engine with fault and maintenance...")

        scenario = ScenarioConfig(
            scenario_id="test_fault_pdm",
            seed=42,
            product_schedule=["Product_B"] * 100,
            fault_machine="M3",
            fault_type="bearing_wear",
            fault_start=20,
            max_degradation=0.85,
            policy_type="PREDICTIVE",
            manual_pdm_timestep=50
        )

        result = UnifiedSimulationEngine.run(scenario)

        m3_data = result.telemetry_df[result.telemetry_df['machine_id'] == 'M3']
        self.assertGreater(len(m3_data), 0)
        self.assertGreater(m3_data['degradation'].max(), 0.1)

        self.assertGreater(result.maintenance_events, 0)

        if hasattr(result, 'resilience') and result.resilience is not None:
            if isinstance(result.resilience, dict):
                recovery_success = result.resilience.get('recovery_success', False)
            elif hasattr(result.resilience, 'recovery_success'):
                recovery_success = result.resilience.recovery_success
            else:
                recovery_success = False
        else:
            recovery_success = hasattr(result, 'evidence_traces') and len(result.evidence_traces) > 0

        self.assertTrue(recovery_success, "Recovery should be successful")

        print(f"✅ Fault + Maintenance: OEE={result.oee_pct:.1f}%")
        print(f"   Maintenance events={result.maintenance_events}")
        print(f"   Recovery success={recovery_success}")

    def test_multiproduct_context(self):
        """Test 10: Multi-product context switching"""
        print("\n[TEST 10] Testing multi-product context...")

        factory = PackagingFactory()
        factory.start()

        products = ["Product_A", "Product_B", "Product_C"]
        power_readings = []

        for product in products:
            factory.current_product = product
            # Run 5 steps to stabilize
            for _ in range(5):
                factory.step()
            # Record power
            total_power = sum(m.power_kw for m in factory.machines.values())
            power_readings.append(total_power)

        # Product C (heavy) should consume more power than Product A (light)
        self.assertGreater(power_readings[2], power_readings[0] * 1.1)

        print(f"✅ Multi-product: Power A={power_readings[0]:.2f}kW, "
              f"B={power_readings[1]:.2f}kW, C={power_readings[2]:.2f}kW")

    def test_noise_robustness(self):
        """Test 11: Sensor noise robustness"""
        print("\n[TEST 11] Testing noise robustness...")

        # Run with noise enabled
        scenario = ScenarioConfig(
            scenario_id="test_noise",
            seed=42,
            product_schedule=["Product_B"] * 30,
            fault_machine="M3",
            fault_type="None (Healthy Baseline)",
            fault_start=999,
            max_degradation=0.0,
            policy_type="CORRECTIVE",
            enable_chaos=True
        )

        result = UnifiedSimulationEngine.run(scenario)

        self.assertIsNotNone(result.telemetry_df)
        self.assertGreater(len(result.telemetry_df), 0)

        # Check vibration has some variation
        vib_cols = [c for c in result.telemetry_df.columns if 'vibration' in c.lower()]
        if vib_cols:
            vib_std = result.telemetry_df[vib_cols[0]].std()
            self.assertGreater(vib_std, 0.01)

        print(f"✅ Noise robustness: {len(result.telemetry_df)} records, "
              f"vibration std={vib_std:.3f}" if vib_cols else "✅ Noise robustness: passed")


def run_all_tests():
    """Run all tests with nice output"""
    print("=" * 60)
    print("  PRIME-Factory Phase 1 Integration Tests")
    print("=" * 60)

    suite = unittest.TestLoader().loadTestsFromTestCase(TestPhase1)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "=" * 60)
    print(f"  Summary: {result.testsRun} tests, {len(result.failures)} failures, {len(result.errors)} errors")
    print("=" * 60)

    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_all_tests()
    sys.exit(0 if success else 1)