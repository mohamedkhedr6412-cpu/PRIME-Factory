"""
PRIME-Factory Maintenance Policy Benchmark v6.2 FINAL

Policies:
- CORRECTIVE: No intervention until failure
- PREVENTIVE: Fixed interval maintenance (every 140 minutes)
- PREDICTIVE: AI-driven maintenance (decision-based) ONLY
- PREDICTIVE + PEAK SHAVING: Predictive + energy optimization

All policies use the same seed, schedule, fault, and severity.
Now includes counterfactual resilience metrics with correct definitions.
FIXED: recovery_success is extracted from actual simulation result.
FIXED: failure_avoided = corrective_failed and not predictive_failed.
FIXED: production_loss_avoided = units_pred - units_corr.
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

        PREDICTIVE now relies ONLY on AI decision (no backup trigger).
        """
        cfg = custom_config if custom_config is not None else config.BENCHMARK_CONFIG

        fault_start = cfg.get("fault_start", 100)
        max_degradation = cfg.get("max_degradation", 0.95)
        fault_machine = cfg.get("fault_machine", "M3")
        product_schedule = cfg.get("product_schedule", ["Product_B"] * config.TOTAL_TIMESTEPS)

        manual_pdm = None

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
    def run_counterfactual_benchmark(
        product_schedule: list,
        fault_start_t: int = 100,
        max_deg: float = 0.95,
        seed: int = config.RANDOM_SEED,
    ) -> dict:
        """
        Run paired counterfactual analysis: Corrective vs Predictive.
        Returns resilience metrics based on actual comparison.

        ===== FIXED: Correct definitions =====
        - failure_avoided = corrective_failed and not predictive_failed
        - production_loss_avoided = predictive_good_units - corrective_good_units
        - downtime_avoided = corrective_downtime - predictive_downtime
        - recovery_success = actual recovery success from predictive simulation
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
            scenario_id=f"COUNTERFACTUAL_PRED_{seed}",
            policy_type="PREDICTIVE",
            enable_peak_shaving=False,
            **common,
        )

        corr_scenario = ScenarioConfig(
            scenario_id=f"COUNTERFACTUAL_CORR_{seed}",
            policy_type="CORRECTIVE",
            enable_peak_shaving=False,
            **common,
        )

        res_pred = UnifiedSimulationEngine.run(pred_scenario)
        res_corr = UnifiedSimulationEngine.run(corr_scenario)

        # ===== Extract values =====
        d_corr = _get_val(res_corr, "downtime_min", 0.0)
        d_pred = _get_val(res_pred, "downtime_min", 0.0)
        units_corr = _get_val(res_corr, "good_units", 0)
        units_pred = _get_val(res_pred, "good_units", 0)
        cost_corr = _get_val(res_corr, "total_operational_cost_usd", 0.0)
        cost_pred = _get_val(res_pred, "total_operational_cost_usd", 0.0)

        # ===== FIXED: Determine failure status from resilience.failure_avoided =====
        # resilience.failure_avoided = not machine_ever_failed
        # So corrective_failed = not corr_resilience.failure_avoided
        corr_failed = True  # default
        pred_failed = False  # default

        if hasattr(res_corr, 'resilience') and res_corr.resilience is not None:
            corr_failed = not getattr(res_corr.resilience, 'failure_avoided', True)
        if hasattr(res_pred, 'resilience') and res_pred.resilience is not None:
            pred_failed = not getattr(res_pred.resilience, 'failure_avoided', True)

        # ===== FIXED: Counterfactual Resilience Metrics =====
        failure_avoided = corr_failed and not pred_failed
        downtime_avoided = max(0, d_corr - d_pred)
        production_loss_avoided = max(0, units_pred - units_corr)
        cost_saved = max(0, cost_corr - cost_pred)

        # ===== FIXED: recovery_success from actual simulation =====
        recovery_success = False
        if hasattr(res_pred, 'resilience') and res_pred.resilience is not None:
            recovery_success = getattr(res_pred.resilience, 'recovery_success', False)

        return {
            "corrective": res_corr,
            "predictive": res_pred,
            "resilience": {
                "failure_avoided": failure_avoided,
                "downtime_avoided_min": round(downtime_avoided, 2),
                "production_loss_avoided_units": int(production_loss_avoided),
                "cost_saved_usd": round(cost_saved, 2),
                "recovery_success": recovery_success,  # FIXED: not hard-coded
                "corrective_failed": corr_failed,
                "predictive_failed": pred_failed,
            },
            "savings": {
                "downtime_saved_min": round(d_corr - d_pred, 2),
                "cost_saved_usd": round(cost_corr - cost_pred, 2),
                "oee_gain_pct": round(_get_val(res_pred, "oee_pct", 0.0) - _get_val(res_corr, "oee_pct", 0.0), 2),
                "extra_good_units": units_pred - units_corr,
            }
        }

    @staticmethod
    def run_what_if_analysis(
        product_schedule: list,
        fault_start_t: int = 120,
        max_deg: float = 0.85,
        seed: int = config.RANDOM_SEED,
    ) -> dict:
        """
        Run paired what-if analysis: Predictive vs Corrective (legacy, kept for compatibility).
        Now uses the corrected counterfactual definitions.
        """
        return FactoryPolicySimulator.run_counterfactual_benchmark(
            product_schedule=product_schedule,
            fault_start_t=fault_start_t,
            max_deg=max_deg,
            seed=seed
        )