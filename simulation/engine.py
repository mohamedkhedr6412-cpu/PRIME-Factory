"""
PRIME-Factory Unified Simulation & KPI Engine v6.0
Single Source of Truth for Live Telemetry, Benchmarks, and What-If Analysis (Section 3, 11, 16 & 17).
"""

from typing import List, Dict, Any, Optional
import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest

import config
from core.models import ScenarioConfig, SimulationEvent, ResilienceMetrics, SimulationResult
from simulation.factory import PackagingFactory
from simulation.faults import (
    generate_degradation_profile,
    generate_friction_profile,
    generate_electrical_profile
)
from simulation.state_machine import AssetStateMachine
from energy.eci import calculate_eci, get_context_expected_power
from energy.peak_shaving import apply_peak_shaving
from energy.energy_model import calculate_financial_and_esg_impact
from ai.isolation_forest import PRIMEIsolationForest
from ai.anomaly import AnomalyProcessor
from ai.health_index import calculate_health_index_and_evidence, estimate_rolling_rul

class UnifiedSimulationEngine:
    @staticmethod
    def run(scenario: ScenarioConfig) -> SimulationResult:
        rng = np.random.RandomState(scenario.seed)
        factory = PackagingFactory()
        timesteps = len(scenario.product_schedule)
        events: List[SimulationEvent] = []

        # 1. Clean Baseline Training for Machine-Aware AI
        factory.reset_factory()
        clean_df = factory.run_simulation(scenario.product_schedule, seed=scenario.seed)
        clean_df["expected_p"] = clean_df.apply(lambda r: get_context_expected_power(r["machine_id"], r["product"]), axis=1)
        clean_df["power_residual"] = clean_df["power_kw"] - clean_df["expected_p"]

        ai_model = PRIMEIsolationForest(contamination=0.02, seed=scenario.seed)
        ai_model.fit(clean_df)

        context_ai_model = IsolationForest(n_estimators=100, contamination=0.02, random_state=scenario.seed)
        context_ai_model.fit(clean_df[["power_residual", "vibration_rms", "temperature_c"]])

        factory.reset_factory()

        # 2. Exogenous Continuous Degradation Profile Generation
        degradation_plan = None
        if scenario.fault_type != "None (Healthy Baseline)":
            if "Bearing" in scenario.fault_type:
                profile = generate_degradation_profile(timesteps, scenario.fault_start, scenario.max_degradation)
            elif "Friction" in scenario.fault_type:
                profile = generate_friction_profile(timesteps, scenario.fault_start, scenario.max_degradation)
            else:
                profile = generate_electrical_profile(timesteps, scenario.fault_start, scenario.max_degradation)
            degradation_plan = {scenario.fault_machine: profile}

        # 3. Dynamic Synchronous Timestep Execution Loop
        processors = {m: AnomalyProcessor(config.PERSISTENCE_WINDOW) for m in config.MACHINES}
        state_machines = {m: AssetStateMachine(m) for m in config.MACHINES}
        hi_histories = {m: [] for m in config.MACHINES}

        records = []
        is_repairing = False
        repair_timer = 0
        downtime_minutes = 0.0
        maintenance_events = 0
        total_units = 0
        good_units = 0
        scrap_units = 0

        recovery_start_t = None
        recovery_end_t = None
        alert_triggered_t = None

        events.append(SimulationEvent(0, "SYSTEM_START", "INFO", "ALL", "Line initialized in healthy nominal state."))

        for t in range(timesteps):
            prod_key = scenario.product_schedule[t]
            speed_mod = apply_peak_shaving(t) if scenario.enable_peak_shaving else 1.0

            # Causal Intervention Trigger
            if scenario.manual_pdm_timestep is not None and t == scenario.manual_pdm_timestep:
                is_repairing = True
                repair_timer = 15
                maintenance_events += 1
                events.append(SimulationEvent(t, "MAINTENANCE_EXECUTED", "INFO", scenario.fault_machine, "Targeted 15-minute Predictive Intervention executed."))

            if is_repairing:
                repair_timer -= 1
                downtime_minutes += 1.0
                if repair_timer <= 0:
                    is_repairing = False
                    factory.reset_machine(scenario.fault_machine)
                    recovery_start_t = t
                    events.append(SimulationEvent(t, "RECOVERY_STARTED", "INFO", scenario.fault_machine, "Post-repair stabilization phase initiated."))
                
                for m in factory.machines:
                    records.append({
                        "timestep": t, "machine_id": m.machine_id, "machine_name": m.name,
                        "state": config.STATE_MAINTENANCE, "product": prod_key,
                        "speed_rpm": 0.0, "load_factor": 0.0, "vibration_rms": 0.0,
                        "temperature_c": m.current_temp, "current_a": 0.5, "voltage_v": 400.0,
                        "power_kw": 0.2, "pf": 0.95, "degradation": 0.0, "expected_p": 0.2,
                        "eci": 0.0, "raw_ai_score": 0.0, "context_ai_score": 0.0,
                        "persistence_ratio": 0.0, "confirmed_anomaly": 0, "health_index": 98.0,
                        "rul_minutes": -1, "rul_str": "In Service", "rul_confidence": 1.0,
                        "penalty_contributions": {"AI Anomaly Model": 0.0, "Persistence Filter": 0.0, "Energy Deviation (ECI)": 0.0, "Thermal & Vibration Physics": 0.0}
                    })
                continue

            # Physical Machine Step
            step_records = []
            for m in factory.machines:
                if degradation_plan and m.machine_id in degradation_plan:
                    m.degradation_level = degradation_plan[m.machine_id][t]
                else:
                    m.degradation_level = 0.0

                m_rec = m.step(prod_key, dt_minutes=config.TIME_STEP_MINUTES, rng=rng)
                
                if scenario.enable_chaos and m.machine_id == scenario.fault_machine and m.has_vibration:
                    if rng.uniform(0, 1) < 0.03:
                        m_rec["vibration_rms"] += rng.uniform(1.2, 2.5)

                if scenario.enable_peak_shaving and speed_mod < 1.0:
                    m_rec["power_kw"] = round(m_rec["power_kw"] * (speed_mod ** 2.0), 3)

                m_rec["expected_p"] = get_context_expected_power(m.machine_id, prod_key)
                m_rec["eci"] = calculate_eci(m_rec["power_kw"], m.machine_id, prod_key)
                m_rec["power_residual"] = m_rec["power_kw"] - m_rec["expected_p"]
                step_records.append(m_rec)

            step_df = pd.DataFrame(step_records)
            step_df["raw_ai_score"] = ai_model.predict_anomaly_score(step_df)
            c_scores = context_ai_model.decision_function(step_df[["power_residual", "vibration_rms", "temperature_c"]])
            step_df["context_ai_score"] = np.round(1.0 / (1.0 + np.exp(c_scores * 5.0)), 4)

            # Condition Assessment & Health Aggregation
            for _, r in step_df.iterrows():
                m_id = r["machine_id"]
                p_info = processors[m_id].update(r["context_ai_score"], threshold=0.5)
                
                hi_info = calculate_health_index_and_evidence(
                    anomaly_score=r["context_ai_score"],
                    persistence_ratio=p_info["persistence_ratio"],
                    eci=r["eci"],
                    temp_c=r["temperature_c"],
                    vib_rms=r["vibration_rms"]
                )
                curr_hi = hi_info["health_index"]
                hi_histories[m_id].append(curr_hi)

                st_name = state_machines[m_id].update_state(
                    degradation=r["degradation"],
                    health_index=curr_hi,
                    is_confirmed_anomaly=bool(p_info["is_confirmed_anomaly"]),
                    in_maintenance=False
                )

                if st_name == config.STATE_NORMAL and recovery_start_t is not None and recovery_end_t is None and m_id == scenario.fault_machine:
                    recovery_end_t = t
                    events.append(SimulationEvent(t, "RECOVERY_COMPLETED", "INFO", m_id, f"Asset fully recovered to healthy nominal baseline (HI: {curr_hi:.1f})."))

                if st_name == config.STATE_PREDICTIVE_ALERT and alert_triggered_t is None and m_id == scenario.fault_machine:
                    alert_triggered_t = t
                    events.append(SimulationEvent(t, "PREDICTIVE_ALERT", "PREDICTIVE", m_id, f"Actionable anomaly detected. HI: {curr_hi:.1f}."))

                # RUL with Quality & Stability Confidence
                r_val, r_str = estimate_rolling_rul(hi_histories[m_id], current_state=st_name, current_t=t, window_size=15)
                rul_conf = 0.95 if st_name in [config.STATE_CRITICAL, config.STATE_PREDICTIVE_ALERT] else 0.70

                r_dict = dict(r)
                r_dict["timestep"] = t
                r_dict["state"] = st_name
                r_dict["persistence_ratio"] = p_info["persistence_ratio"]
                r_dict["confirmed_anomaly"] = p_info["is_confirmed_anomaly"]
                r_dict["health_index"] = curr_hi
                r_dict["rul_minutes"] = r_val if r_val is not None else -1
                r_dict["rul_str"] = r_str
                r_dict["rul_confidence"] = rul_conf
                r_dict["penalty_contributions"] = hi_info["penalty_contributions"]
                records.append(r_dict)

            # Dynamic True Production & Scrap Output
            target_deg = step_df[step_df["machine_id"] == scenario.fault_machine]["degradation"].iloc[0]
            base_cycle = config.PRODUCTS[prod_key]["base_cycle_time"] / speed_mod
            m_units = int(60.0 / (base_cycle * (1.0 + 0.1 * target_deg)))
            defect_rate = 0.005 + (0.04 * target_deg)
            m_good = int(m_units * (1.0 - defect_rate))
            m_scrap = m_units - m_good

            total_units += m_units
            good_units += m_good
            scrap_units += m_scrap

        # 4. Final Aggregated KPIs & Financials (Single Source of Truth)
        res_df = pd.DataFrame(records)
        agg_power = res_df.groupby("timestep")["power_kw"].sum()
        total_energy_kwh = float(np.sum(agg_power) * (config.TIME_STEP_MINUTES / 60.0))
        peak_demand_kw = float(np.max(agg_power))
        avg_pf = float(res_df["pf"].mean())

        operating_time_min = timesteps - downtime_minutes
        availability = (operating_time_min / timesteps) if timesteps > 0 else 0.0
        cycle_times = [config.PRODUCTS[p]["base_cycle_time"] for p in scenario.product_schedule]
        weighted_ideal_sec = sum(cycle_times) / len(cycle_times)
        performance = ((weighted_ideal_sec * total_units) / (operating_time_min * 60.0)) if operating_time_min > 0 else 0.0
        quality = (good_units / total_units) if total_units > 0 else 0.0
        oee = availability * performance * quality * 100.0

        fin = calculate_financial_and_esg_impact(total_energy_kwh, downtime_minutes, good_units, avg_pf)
        cost_per_unit = (fin["total_operational_cost_usd"] / good_units) if good_units > 0 else 0.0

        # Resilience Metrics Formulation
        rec_time = float(recovery_end_t - recovery_start_t) if (recovery_start_t and recovery_end_t) else 15.0
        resilience = ResilienceMetrics(
            recovery_time_min=rec_time,
            production_loss_units=scrap_units + int(downtime_minutes * 35),
            downtime_avoided_min=60.0 if scenario.manual_pdm_timestep else 0.0,
            recovery_success=(recovery_end_t is not None or scenario.manual_pdm_timestep is not None),
            time_to_recover_min=rec_time + (15.0 if scenario.manual_pdm_timestep else 0.0),
            failure_avoided=(target_deg < 0.75 or scenario.manual_pdm_timestep is not None)
        )

        return SimulationResult(
            config=scenario,
            telemetry_df=res_df,
            events=events,
            total_energy_kwh=round(total_energy_kwh, 2),
            peak_demand_kw=round(peak_demand_kw, 2),
            avg_pf=round(avg_pf, 3),
            downtime_min=downtime_minutes,
            maintenance_events=maintenance_events,
            total_units=total_units,
            good_units=good_units,
            scrap_units=scrap_units,
            availability_pct=round(availability * 100.0, 2),
            performance_pct=round(performance * 100.0, 2),
            quality_pct=round(quality * 100.0, 2),
            oee_pct=round(oee, 2),
            energy_cost_usd=fin["energy_cost_usd"],
            downtime_cost_usd=fin["downtime_cost_usd"],
            pf_penalty_usd=fin["pf_penalty_usd"],
            total_operational_cost_usd=fin["total_operational_cost_usd"],
            carbon_kg=fin["carbon_kg"],
            energy_per_good_unit_wh=fin["energy_per_unit_wh"],
            cost_per_good_unit_usd=round(cost_per_unit, 4),
            resilience=resilience
        )