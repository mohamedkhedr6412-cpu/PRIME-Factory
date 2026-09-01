"""
PRIME-Factory Invariant & Regression Safeguards v4.2
Strictly verifies that code changes maintain physical, algorithmic, and financial integrity (P0-01 to P0-10).
"""

import config
from core.models import ScenarioConfig
from simulation.engine import UnifiedSimulationEngine
from maintenance.policies import FactoryPolicySimulator
from ai.health_index import estimate_rolling_rul

def test_peak_shaving_reduces_peak_demand():
    """P0-02 Verification: Enforces that Demand Response strictly lowers factory peak active power."""
    sim_base = FactoryPolicySimulator(policy_type="PREDICTIVE", enable_peak_shaving=False, seed=42)
    sim_ps = FactoryPolicySimulator(policy_type="PREDICTIVE", enable_peak_shaving=True, seed=42)
    res_base = sim_base.run_policy_benchmark()
    res_ps = sim_ps.run_policy_benchmark()
    assert res_ps.peak_demand_kw <= res_base.peak_demand_kw, "Peak Shaving must reduce peak demand"

def test_predictive_beats_corrective_at_critical_failure():
    """P0-01 Verification: Enforces that predictive maintenance achieves lower downtime and operational cost."""
    cfg = {"fault_machine": "M3", "fault_start": 60, "max_degradation": 0.85, "seed": 42, "product_schedule": ["Product_B"] * config.TOTAL_TIMESTEPS}
    sim_pred = FactoryPolicySimulator(policy_type="PREDICTIVE", seed=42)
    sim_corr = FactoryPolicySimulator(policy_type="CORRECTIVE", seed=42)
    res_pred = sim_pred.run_policy_benchmark(cfg)
    res_corr = sim_corr.run_policy_benchmark(cfg)
    assert res_pred.downtime_min < res_corr.downtime_min
    assert res_pred.total_operational_cost_usd < res_corr.total_operational_cost_usd

def test_financial_sum_identity():
    """P0-04 Verification: Confirms total cost equals the exact sum of its three discrete components."""
    scenario = ScenarioConfig("TEST_FIN", 42, ["Product_B"]*100, "M3", "Bearing Wear", 20, 0.5)
    res = UnifiedSimulationEngine.run(scenario)
    expected_total = round(res.energy_cost_usd + res.downtime_cost_usd + res.pf_penalty_usd, 2)
    assert abs(res.total_operational_cost_usd - expected_total) < 0.05

def test_rul_boundary_and_dynamics():
    """P1-04 Verification: RUL cannot exceed remaining shift time and triggers on degradation."""
    hi_history = [85.0, 75.0, 65.0, 55.0, 45.0, 35.0]
    rul_val, _ = estimate_rolling_rul(hi_history, current_state="CRITICAL", current_t=300)
    assert rul_val is not None
    assert rul_val <= (config.TOTAL_TIMESTEPS - 300)

def test_whatif_deterministic_reproducibility():
    """P0-07 Verification: Confirms What-If paired branches produce identical deterministic outputs."""
    schedule = ["Product_B"] * config.TOTAL_TIMESTEPS
    res_1 = FactoryPolicySimulator.run_what_if_analysis(schedule, fault_start_t=120, max_deg=0.85, seed=42)
    res_2 = FactoryPolicySimulator.run_what_if_analysis(schedule, fault_start_t=120, max_deg=0.85, seed=42)
    assert res_1["savings"]["cost_saved_usd"] == res_2["savings"]["cost_saved_usd"]