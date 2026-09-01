"""
PRIME-Factory Maintenance Policies & What-If Engine v6.0
Strictly wrapped around the Unified Simulation Engine (Section 17 & 18).
"""

import config
from core.models import ScenarioConfig, SimulationResult
from simulation.engine import UnifiedSimulationEngine

def _get_val(obj, key, default=0.0):
    """Safely extracts a value from either a dataclass object or a dictionary."""
    if hasattr(obj, key):
        return getattr(obj, key)
    elif isinstance(obj, dict):
        return obj.get(key, default)
    return default

class FactoryPolicySimulator:
    def __init__(self, policy_type: str = "PREDICTIVE", enable_peak_shaving: bool = False, seed: int = config.RANDOM_SEED):
        self.policy_type = policy_type.upper()
        self.enable_peak_shaving = enable_peak_shaving
        self.seed = seed

    def run_policy_benchmark(self, custom_config: dict = None) -> SimulationResult:
        cfg = custom_config if custom_config else config.BENCHMARK_CONFIG
        pdm_t = 180 if "PREDICTIVE" in self.policy_type else (240 if self.policy_type == "PREVENTIVE" else None)
        
        scenario = ScenarioConfig(
            scenario_id=f"BENCH_{self.policy_type}",
            seed=self.seed,
            product_schedule=cfg["product_schedule"],
            fault_machine=cfg["fault_machine"],
            fault_type="Bearing Wear",
            fault_start=cfg["fault_start"],
            max_degradation=cfg["max_degradation"],
            enable_peak_shaving=self.enable_peak_shaving,
            manual_pdm_timestep=pdm_t
        )
        return UnifiedSimulationEngine.run(scenario)

    @staticmethod
    def run_what_if_analysis(
        product_schedule: list, 
        fault_start_t: int = 120, 
        max_deg: float = 0.85, 
        seed: int = config.RANDOM_SEED
    ) -> dict:
        """
        Paired dual-branch What-If analysis comparing Predictive action vs Corrective breakdown
        under identical exogenous realizations (Section 18).
        """
        # Branch 1: Predictive Intervention
        sc_pred = ScenarioConfig(
            scenario_id="WHATIF_PRED",
            seed=seed,
            product_schedule=product_schedule,
            fault_machine="M3",
            fault_type="Bearing Wear",
            fault_start=fault_start_t,
            max_degradation=max_deg,
            manual_pdm_timestep=fault_start_t + 55
        )
        res_pred = UnifiedSimulationEngine.run(sc_pred)

        # Branch 2: No Intervention (Corrective Breakdown)
        sc_corr = ScenarioConfig(
            scenario_id="WHATIF_CORR",
            seed=seed,
            product_schedule=product_schedule,
            fault_machine="M3",
            fault_type="Bearing Wear",
            fault_start=fault_start_t,
            max_degradation=max_deg,
            manual_pdm_timestep=None
        )
        res_corr = UnifiedSimulationEngine.run(sc_corr)

        d_corr = _get_val(res_corr, "downtime_min", 0.0)
        d_pred = _get_val(res_pred, "downtime_min", 0.0)
        c_corr = _get_val(res_corr, "total_operational_cost_usd", 0.0)
        c_pred = _get_val(res_pred, "total_operational_cost_usd", 0.0)
        carb_corr = _get_val(res_corr, "carbon_kg", 0.0)
        carb_pred = _get_val(res_pred, "carbon_kg", 0.0)
        oee_pred = _get_val(res_pred, "oee_pct", 0.0)
        oee_corr = _get_val(res_corr, "oee_pct", 0.0)
        u_pred = _get_val(res_pred, "good_units", 0)
        u_corr = _get_val(res_corr, "good_units", 0)

        res_obj = getattr(res_pred, "resilience", None)
        fa = getattr(res_obj, "failure_avoided", True) if res_obj else True

        return {
            "predictive": res_pred,
            "no_intervention": res_corr,
            "savings": {
                "downtime_saved_min": round(d_corr - d_pred, 1),
                "cost_saved_usd": round(c_corr - c_pred, 2),
                "carbon_saved_kg": round(carb_corr - carb_pred, 2),
                "oee_gain_pct": round(oee_pred - oee_corr, 2),
                "extra_good_units": u_pred - u_corr,
                "resilience_score": "EXCELLENT (Zero Breakdown)" if fa else "DEGRADED"
            }
        }