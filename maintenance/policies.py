"""
PRIME-Factory Maintenance Policy Benchmark v6.2

Policies:
- CORRECTIVE: No intervention until failure
- PREVENTIVE: Fixed interval maintenance (every 160 minutes)
- PREDICTIVE: AI-driven maintenance (decision-based)
- PREDICTIVE + PEAK SHAVING: Predictive + energy optimization

All policies use the same seed, schedule, fault, and severity.
"""

from __future__ import annotations

from typing import Dict, Optional, Any

import config
from core.models import ScenarioConfig, SimulationResult
from simulation.engine import UnifiedSimulationEngine


def _get_val(obj: Any, key: str, default: Any = 0.0):
    if hasattr(obj, key):
        return getattr(obj, key)
    if isinstance(obj, dict):
        return obj.get(key, default)
    return default


class FactoryPolicySimulator:
    """Run policy benchmarks with controlled conditions."""

    VALID_POLICIES = {"CORRECTIVE", "PREVENTIVE", "PREDICTIVE"}

    def __init__(
        self,
        policy_type: str = "PREDICTIVE",
        enable_peak_shaving: bool = False,
        seed: int = config.RANDOM_SEED,
    ):
        policy = policy_type.upper()
        if policy not in self.VALID_POLICIES:
            raise ValueError(f"Unsupported policy: {policy}")

        self.policy_type = policy
        self.enable_peak_shaving = bool(enable_peak_shaving)
        self.seed = int(seed)

    def run_policy_benchmark(
        self,
        custom_config: Optional[dict] = None,
    ) -> SimulationResult:
        """
        Run a benchmark for this policy.

        NOTE: Predictive is now decision-driven, NOT fixed timestep.
        Peak Shaving is integrated via ScenarioConfig.
        """
        cfg = custom_config if custom_config is not None else config.BENCHMARK_CONFIG

        fault_start = cfg.get("fault_start", 60)
        max_degradation = cfg.get("max_degradation", 0.85)
        fault_machine = cfg.get("fault_machine", "M3")
        product_schedule = cfg.get("product_schedule", ["Product_B"] * config.TOTAL_TIMESTEPS)

        # For PREVENTIVE, set a fixed maintenance interval
        # For CORRECTIVE, no intervention
        # For PREDICTIVE, let the AI decide
        manual_pdm = None
        
        if self.policy_type == "PREVENTIVE":
            manual_pdm = 160
        elif self.policy_type == "PREDICTIVE":
            manual_pdm = None

        # FIXED: Create scenario with proper parameters
        scenario = ScenarioConfig(
            scenario_id=f"BENCH_{self.policy_type}_SEED_{self.seed}",
            seed=self.seed,
            product_schedule=list(product_schedule),
            fault_machine=fault_machine,
            fault_type=cfg.get("fault_type", "Bearing Wear"),
            fault_start=fault_start,
            max_degradation=max_degradation,
            policy_type=self.policy_type,
            enable_peak_shaving=self.enable_peak_shaving,
            manual_pdm_timestep=manual_pdm,
        )

        return UnifiedSimulationEngine.run(scenario)

    @staticmethod
    def run_what_if_analysis(
        product_schedule: list,
        fault_start_t: int = 120,
        max_deg: float = 0.85,
        seed: int = config.RANDOM_SEED,
    ) -> dict:
        """
        Run paired what-if analysis: Predictive vs Corrective.
        """
        common = dict(
            seed=seed,
            product_schedule=list(product_schedule),
            fault_machine="M3",
            fault_type="Bearing Wear",
            fault_start=fault_start_t,
            max_degradation=max_deg,
        )

        pred_scenario = ScenarioConfig(
            scenario_id=f"WHATIF_PRED_{seed}",
            policy_type="PREDICTIVE",
            enable_peak_shaving=False,
            **common,
        )

        corr_scenario = ScenarioConfig(
            scenario_id=f"WHATIF_CORR_{seed}",
            policy_type="CORRECTIVE",
            enable_peak_shaving=False,
            **common,
        )

        res_pred = UnifiedSimulationEngine.run(pred_scenario)
        res_corr = UnifiedSimulationEngine.run(corr_scenario)

        d_corr = _get_val(res_corr, "downtime_min", 0.0)
        d_pred = _get_val(res_pred, "downtime_min", 0.0)
        cost_corr = _get_val(res_corr, "total_operational_cost_usd", 0.0)
        cost_pred = _get_val(res_pred, "total_operational_cost_usd", 0.0)
        carbon_corr = _get_val(res_corr, "carbon_kg", 0.0)
        carbon_pred = _get_val(res_pred, "carbon_kg", 0.0)
        oee_corr = _get_val(res_corr, "oee_pct", 0.0)
        oee_pred = _get_val(res_pred, "oee_pct", 0.0)
        units_corr = _get_val(res_corr, "good_units", 0)
        units_pred = _get_val(res_pred, "good_units", 0)

        return {
            "predictive": res_pred,
            "no_intervention": res_corr,
            "savings": {
                "downtime_saved_min": round(d_corr - d_pred, 2),
                "cost_saved_usd": round(cost_corr - cost_pred, 2),
                "carbon_saved_kg": round(carbon_corr - carbon_pred, 2),
                "oee_gain_pct": round(oee_pred - oee_corr, 2),
                "extra_good_units": units_pred - units_corr,
            },
        }