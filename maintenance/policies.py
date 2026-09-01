"""
PRIME-Factory Maintenance Policies & What-If Engine v4.0
Supports scientific benchmarks, interactive intervention execution, and live What-If dual-branch comparisons.
"""
import numpy as np
import pandas as pd
import config
from simulation.factory import PackagingFactory
from simulation.faults import generate_degradation_profile
from energy.eci import calculate_eci
from energy.peak_shaving import apply_peak_shaving
from energy.energy_model import get_factory_aggregated_power, calculate_financial_and_esg_impact
from ai.isolation_forest import PRIMEIsolationForest
from ai.anomaly import AnomalyProcessor
from ai.health_index import calculate_health_index_and_evidence
from evaluation.kpis import calculate_oee_multiproduct

class FactoryPolicySimulator:
    def __init__(self, policy_type: str = "PREDICTIVE", enable_peak_shaving: bool = False):
        self.policy_type = policy_type.upper()
        self.enable_peak_shaving = enable_peak_shaving
        self.factory = PackagingFactory()
        
    def run_policy_benchmark(self, custom_config: dict = None) -> dict:
        cfg = custom_config if custom_config else config.BENCHMARK_CONFIG
        product_schedule = cfg["product_schedule"]
        fault_machine = cfg["fault_machine"]
        start_fault_t = cfg["fault_start"]
        max_deg = cfg["max_degradation"]
        
        timesteps = len(product_schedule)
        
        train_df = self.factory.run_simulation(product_schedule)
        ai_model = PRIMEIsolationForest(contamination=0.02)
        ai_model.fit(train_df)
        
        current_deg = 0.0
        is_repairing = False
        repair_timer = 0
        downtime_minutes = 0.0
        maintenance_events = 0
        
        factory_records = []
        processor = AnomalyProcessor(window_size=config.PERSISTENCE_WINDOW)
        
        total_units = 0
        good_units = 0
        
        for t in range(timesteps):
            prod_key = product_schedule[t]
            speed_mod = apply_peak_shaving(t) if self.enable_peak_shaving else 1.0
            
            if is_repairing:
                repair_timer -= 1
                downtime_minutes += 1.0
                if repair_timer <= 0:
                    is_repairing = False
                    current_deg = 0.0
                
                for m in self.factory.machines:
                    factory_records.append({
                        "timestep": t,
                        "machine_id": m.machine_id,
                        "power_kw": 0.3,
                        "state": config.STATE_MAINTENANCE,
                        "degradation": current_deg
                    })
                continue
            
            if t >= start_fault_t:
                current_deg = min(max_deg, current_deg + (max_deg / (timesteps - start_fault_t)))
            
            m_step_data = []
            for m in self.factory.machines:
                if m.machine_id == fault_machine:
                    m.degradation_level = current_deg
                else:
                    m.degradation_level = 0.0
                
                rec = m.step(prod_key, dt_minutes=config.TIME_STEP_MINUTES)
                rec["power_kw"] = round(rec["power_kw"] * (speed_mod ** 2), 3)
                rec["timestep"] = t
                rec["eci"] = calculate_eci(rec["power_kw"], rec["machine_id"], prod_key)
                m_step_data.append(rec)
                factory_records.append(rec)
            
            step_df = pd.DataFrame(m_step_data)
            step_df["ai_score"] = ai_model.predict_anomaly_score(step_df)
            
            fault_m_row = step_df[step_df["machine_id"] == fault_machine].iloc[0]
            p_info = processor.update(fault_m_row["ai_score"], threshold=0.5)
            
            hi_info = calculate_health_index_and_evidence(
                anomaly_score=fault_m_row["ai_score"],
                persistence_ratio=p_info["persistence_ratio"],
                eci=fault_m_row["eci"],
                temp_c=fault_m_row["temperature_c"],
                vib_rms=fault_m_row["vibration_rms"]
            )
            current_hi = hi_info["health_index"]
            
            trigger_repair = False
            duration = 0
            
            if self.policy_type == "CORRECTIVE":
                if current_deg >= 0.75:
                    trigger_repair = True
                    duration = 60
            elif self.policy_type == "PREVENTIVE":
                if t > 0 and (t % 160 == 0):
                    trigger_repair = True
                    duration = 25
            elif "PREDICTIVE" in self.policy_type:
                if current_hi <= config.HI_THRESHOLDS["MONITOR"] and p_info["is_confirmed_anomaly"]:
                    trigger_repair = True
                    duration = 15
            
            if trigger_repair:
                is_repairing = True
                repair_timer = duration
                maintenance_events += 1
                downtime_minutes += 1.0
            else:
                base_cycle = config.PRODUCTS[prod_key]["base_cycle_time"] / speed_mod
                units_min = int(60.0 / (base_cycle * (1.0 + 0.1 * current_deg)))
                defect_rate = 0.005 + (0.04 * current_deg)
                good_min = int(units_min * (1.0 - defect_rate))
                
                total_units += units_min
                good_units += good_min
                
        res_df = pd.DataFrame(factory_records)
        agg_power = get_factory_aggregated_power(res_df)
        total_energy_kwh = float(np.sum(agg_power) * (config.TIME_STEP_MINUTES / 60.0))
        peak_demand_kw = float(np.max(agg_power))
        
        operating_time_min = timesteps - downtime_minutes
        oee_res = calculate_oee_multiproduct(timesteps, operating_time_min, product_schedule, total_units, good_units)
        fin_impact = calculate_financial_and_esg_impact(total_energy_kwh, downtime_minutes, good_units)
        
        return {
            "policy": self.policy_type if not self.enable_peak_shaving else "PREDICTIVE_PEAK_SHAVING",
            "downtime_min": downtime_minutes,
            "events": maintenance_events,
            "oee_pct": oee_res["oee_pct"],
            "good_units": good_units,
            "total_energy_kwh": round(total_energy_kwh, 2),
            "peak_demand_kw": round(peak_demand_kw, 2),
            "energy_per_unit_wh": fin_impact["energy_per_unit_wh"],
            "total_cost_usd": fin_impact["energy_cost_usd"],
            "carbon_kg": fin_impact["carbon_kg"],
            "telemetry_df": res_df
        }

    @staticmethod
    def run_what_if_analysis(product_schedule: list, fault_start_t: int = 120, max_deg: float = 0.85) -> dict:
        """
        مقارنة مزدوجة متزامنة لنفس السيناريو (Dual-Branch What-If Comparison):
        المسار (أ): التدخل التنبؤي الاستباقي (Predictive Intervention)
        المسار (ب): عدم التدخل / الانتظار حتى الانهيار الحرج (No Intervention / Corrective)
        """
        sim_pred = FactoryPolicySimulator(policy_type="PREDICTIVE")
        res_pred = sim_pred.run_policy_benchmark({
            "product_schedule": product_schedule,
            "fault_machine": "M3",
            "fault_start": fault_start_t,
            "max_degradation": max_deg
        })

        sim_corr = FactoryPolicySimulator(policy_type="CORRECTIVE")
        res_corr = sim_corr.run_policy_benchmark({
            "product_schedule": product_schedule,
            "fault_machine": "M3",
            "fault_start": fault_start_t,
            "max_degradation": max_deg
        })

        return {
            "predictive": res_pred,
            "no_intervention": res_corr,
            "savings": {
                "downtime_saved_min": res_corr["downtime_min"] - res_pred["downtime_min"],
                "cost_saved_usd": round(res_corr["total_cost_usd"] - res_pred["total_cost_usd"], 2),
                "carbon_saved_kg": round(res_corr["carbon_kg"] - res_pred["carbon_kg"], 2),
                "oee_gain_pct": round(res_pred["oee_pct"] - res_corr["oee_pct"], 2),
                "extra_good_units": res_pred["good_units"] - res_corr["good_units"]
            }
        }
    