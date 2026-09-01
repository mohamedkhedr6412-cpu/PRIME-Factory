"""
PRIME-Factory Master Experiment & High-Resolution Evidence Generator v4.1
Executes decoupled scientific benchmarks, multi-seed stochastic validation, ablation analysis,
and exports publication-grade figures (300 DPI) for academic documentation.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

import config
from simulation.factory import PackagingFactory
from simulation.faults import generate_degradation_profile, generate_switching_schedule
from energy.eci import calculate_eci, get_context_expected_power
from energy.energy_model import get_factory_aggregated_power
from ai.isolation_forest import PRIMEIsolationForest
from ai.anomaly import AnomalyProcessor
from ai.health_index import calculate_health_index_and_evidence, estimate_rolling_rul
from maintenance.policies import FactoryPolicySimulator
from evaluation.ablation import run_ablation_study

def run_master_experiment():
    os.makedirs("exports", exist_ok=True)
    print("\n" + "="*80)
    print("      PRIME-FACTORY MASTER EXPERIMENT & EVIDENCE ENGINE v4.1")
    print("="*80)

    # 1. Generate Clean Baseline & Train Isolation Forest
    factory = PackagingFactory()
    train_schedule = generate_switching_schedule(config.TOTAL_TIMESTEPS)
    train_df = factory.run_simulation(train_schedule, seed=config.RANDOM_SEED)

    ai_model_raw = PRIMEIsolationForest(contamination=0.02, seed=config.RANDOM_SEED)
    ai_model_raw.fit(train_df)

    # 2. Run Test Fault Scenario on Target Machine (M3 Sealer)
    factory.reset_factory()
    test_schedule = ["Product_B"] * config.TOTAL_TIMESTEPS
    fault_profile = generate_degradation_profile(config.TOTAL_TIMESTEPS, start_time=120, max_degradation=0.85)
    test_df = factory.run_simulation(test_schedule, degradation_targets={"M3": fault_profile}, seed=config.RANDOM_SEED)

    test_df["expected_p"] = test_df.apply(lambda r: get_context_expected_power(r["machine_id"], r["product"]), axis=1)
    test_df["eci"] = test_df.apply(lambda r: calculate_eci(r["power_kw"], r["machine_id"], r["product"]), axis=1)
    test_df["power_residual"] = test_df["power_kw"] - test_df["expected_p"]
    test_df["raw_ai_score"] = ai_model_raw.predict_anomaly_score(test_df)

    train_df["expected_p"] = train_df.apply(lambda r: get_context_expected_power(r["machine_id"], r["product"]), axis=1)
    train_df["power_residual"] = train_df["power_kw"] - train_df["expected_p"]

    from sklearn.ensemble import IsolationForest
    c_model = IsolationForest(n_estimators=100, contamination=0.02, random_state=config.RANDOM_SEED)
    c_model.fit(train_df[["power_residual", "vibration_rms", "temperature_c"]])

    test_feat = test_df[["power_residual", "vibration_rms", "temperature_c"]]
    c_raw_scores = c_model.decision_function(test_feat)
    test_df["context_ai_score"] = np.round(1.0 / (1.0 + np.exp(c_raw_scores * 5.0)), 4)

    m3_df = test_df[test_df["machine_id"] == "M3"].copy()
    processor = AnomalyProcessor(window_size=config.PERSISTENCE_WINDOW)

    hi_list, pers_list, conf_list, rul_list = [], [], [], []
    for _, row in m3_df.iterrows():
        t = int(row["timestep"])
        p_info = processor.update(row["context_ai_score"], threshold=0.5)
        hi_res = calculate_health_index_and_evidence(
            anomaly_score=row["context_ai_score"],
            persistence_ratio=p_info["persistence_ratio"],
            eci=row["eci"],
            temp_c=row["temperature_c"],
            vib_rms=row["vibration_rms"]
        )
        hi_list.append(hi_res["health_index"])
        pers_list.append(p_info["persistence_ratio"])
        conf_list.append(p_info["is_confirmed_anomaly"])
        rul_val, _ = estimate_rolling_rul(hi_list, current_state=config.STATE_CRITICAL if hi_res["health_index"] < 30 else config.STATE_NORMAL, current_t=t, window_size=15)
        rul_list.append(rul_val if rul_val is not None else -1)

    m3_df["health_index"] = hi_list
    m3_df["persistence_ratio"] = pers_list
    m3_df["confirmed_anomaly"] = conf_list
    m3_df["rul_minutes"] = rul_list

    # 3. Execute Pure Detector Ablation Study
    print("\n[+] Running Calibrated Detector Ablation Study (v4.1)...")
    ablation_df = run_ablation_study(m3_df)
    print(ablation_df.to_string(index=False))
    ablation_df.to_csv("exports/ablation_results.csv", index=False)

    # 4. Execute Decoupled Scientific Policy Benchmark
    print("\n[+] Running Scientific Factory Policy Benchmark (v4.1)...")
    policies = [
        ("CORRECTIVE", False),
        ("PREVENTIVE", False),
        ("PREDICTIVE", False),
        ("PREDICTIVE", True)
    ]
    bench_results = []
    for pol_type, is_ps in policies:
        sim = FactoryPolicySimulator(policy_type=pol_type, enable_peak_shaving=is_ps, seed=config.RANDOM_SEED)
        res = sim.run_policy_benchmark()
        bench_results.append({
            "Policy": res["policy"],
            "Downtime (min)": res["downtime_min"],
            "Events": res["events"],
            "OEE (%)": res["oee_pct"],
            "Good Units": res["good_units"],
            "Energy (kWh)": res["total_energy_kwh"],
            "Peak (kW)": res["peak_demand_kw"],
            "Energy/Unit (Wh)": res["energy_per_unit_wh"],
            "Energy Cost ($)": res["energy_cost_usd"],
            "Downtime Cost ($)": res["downtime_cost_usd"],
            "PF Penalty ($)": res["pf_penalty_usd"],
            "Total Cost ($)": res["total_operational_cost_usd"],
            "Carbon (kg CO2)": res["carbon_kg"]
        })
    bench_df = pd.DataFrame(bench_results)
    print(bench_df.to_string(index=False))
    bench_df.to_csv("exports/benchmark_results.csv", index=False)

    # 5. Export Publication-Grade Figures (300 DPI)
    print("\n[+] Exporting high-resolution figures to exports/...")
    
    # Figure 1: Multi-Modal Physical Response & Degradation
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=300)
    ax1.plot(m3_df["timestep"], m3_df["vibration_rms"], label="Vibration RMS (g)", color="#1f77b4", lw=1.5)
    ax1.set_ylabel("Vibration (g)", color="#1f77b4")
    ax1_t = ax1.twinx()
    ax1_t.plot(m3_df["timestep"], m3_df["temperature_c"], label="Temperature (°C)", color="#ff7f0e", ls="--", lw=1.5)
    ax1_t.set_ylabel("Temp (°C)", color="#ff7f0e")
    ax1.set_title("PRIME-Factory: Multi-Modal Physical Response & Degradation Dynamics")
    ax1.grid(True, alpha=0.3)

    ax2.plot(m3_df["timestep"], m3_df["health_index"], label="Health Index (HI)", color="#2ca02c", lw=2)
    ax2.axhline(70, color="orange", ls=":", label="Monitor Threshold (70)")
    ax2.axhline(50, color="red", ls=":", label="Intervention Threshold (50)")
    ax2.set_xlabel("Simulation Time (Minutes)")
    ax2.set_ylabel("Health Index [0-100]")
    ax2.legend(loc="lower left")
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig("exports/figure1_health_response.png", dpi=300)
    plt.close()

    # Figure 2: Factory Power Demand & Asset ECI Deviation
    factory_power = get_factory_aggregated_power(test_df)
    fig, ax = plt.subplots(figsize=(10, 4), dpi=300)
    ax.plot(factory_power.index, factory_power.values, label="Aggregated Factory Power (kW)", color="#d62728", lw=1.5)
    ax.set_ylabel("Factory Power (kW)", color="#d62728")
    ax_e = ax.twinx()
    ax_e.plot(m3_df["timestep"], m3_df["eci"], label="M3 ECI Deviation", color="#9467bd", lw=1.5, ls="--")
    ax_e.axhline(0.0, color="gray", ls=":")
    ax_e.set_ylabel("ECI Index", color="#9467bd")
    ax.set_title("PRIME-Factory: Factory Power Demand & Asset-Level ECI Deviation")
    ax.set_xlabel("Simulation Time (Minutes)")
    ax.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig("exports/figure2_energy_eci.png", dpi=300)
    plt.close()

    print("\n✓ Master Experiment complete. All benchmark tables and 300 DPI figures exported successfully.")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_master_experiment()