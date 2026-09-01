"""
PRIME-Factory Invariant & Regression Safeguards v4.1
Guarantees physical and algorithmic consistency across code updates (P0-01, P0-02, P0-04, P0-07).
"""

import pytest
import config
from maintenance.policies import FactoryPolicySimulator
from ai.health_index import estimate_rolling_rul

def test_peak_shaving_reduces_peak_demand():
    """Verifies that Peak Shaving strictly reduces or maintains peak electrical demand."""
    sim_base = FactoryPolicySimulator(policy_type="PREDICTIVE", enable_peak_shaving=False, seed=42)
    sim_ps = FactoryPolicySimulator(policy_type="PREDICTIVE", enable_peak_shaving=True, seed=42)
    res_base = sim_base.run_policy_benchmark()
    res_ps = sim_ps.run_policy_benchmark()
    assert res_ps["peak_demand_kw"] <= res_base["peak_demand_kw"], "Peak Shaving must reduce peak demand"

def test_predictive_beats_corrective_at_critical_failure():
    """Verifies that Predictive Maintenance yields lower downtime and total cost than Corrective Breakdown."""
    cfg = {
        "fault_machine": "M3",
        "fault_start": 60,
        "max_degradation": 0.85,
        "seed": 42,
        "product_schedule": ["Product_B"] * config.TOTAL_TIMESTEPS
    }
    sim_pred = FactoryPolicySimulator(policy_type="PREDICTIVE", seed=42)
    sim_corr = FactoryPolicySimulator(policy_type="CORRECTIVE", seed=42)
    res_pred = sim_pred.run_policy_benchmark(cfg)
    res_corr = sim_corr.run_policy_benchmark(cfg)
    
    assert res_pred["downtime_min"] < res_corr["downtime_min"], "Predictive downtime must be strictly less than Corrective"
    assert res_pred["total_operational_cost_usd"] < res_corr["total_operational_cost_usd"], "Predictive cost must be less than Corrective"

def test_rul_boundary_and_dynamics():
    """Verifies that rolling RUL is bounded by the remaining shift time and responds to critical degradation."""
    hi_history = [85.0, 75.0, 65.0, 55.0, 45.0, 35.0]
    rul_val, _ = estimate_rolling_rul(hi_history, current_state="CRITICAL", current_t=300)
    assert rul_val is not None, "RUL must be calculated during degradation"
    assert rul_val <= (config.TOTAL_TIMESTEPS - 300), "RUL cannot exceed remaining shift horizon"

def test_whatif_deterministic_reproducibility():
    """Verifies that isolated RNG seeds produce identical What-If results across repeat runs."""
    schedule = ["Product_B"] * config.TOTAL_TIMESTEPS
    res_1 = FactoryPolicySimulator.run_what_if_analysis(schedule, fault_start_t=120, max_deg=0.85, seed=42)
    res_2 = FactoryPolicySimulator.run_what_if_analysis(schedule, fault_start_t=120, max_deg=0.85, seed=42)
    assert res_1["savings"]["cost_saved_usd"] == res_2["savings"]["cost_saved_usd"], "What-If must be deterministic"