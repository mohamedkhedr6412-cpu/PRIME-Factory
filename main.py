"""
PRIME-Factory Master Experiment & High-Resolution Evidence Generator v6.0
Executes the Unified Engine to generate benchmarks, ablation matrices, and 300 DPI publication plots (Section 19 & 23).
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd

import config
from core.models import ScenarioConfig
from simulation.engine import UnifiedSimulationEngine
from maintenance.policies import FactoryPolicySimulator
from evaluation.ablation import run_ablation_study

def run_master_experiment():
    os.makedirs("exports", exist_ok=True)
    print("\n" + "="*80)
    print("      PRIME-FACTORY MASTER EXPERIMENT & EVIDENCE ENGINE v6.0")
    print("="*80)

    # 1. Run Master Scenario on Target M3 Sealer
    scenario = ScenarioConfig(
        scenario_id="EXP_2026_MASTER_RUN",
        seed=config.RANDOM_SEED,
        product_schedule=["Product_B"] * config.TOTAL_TIMESTEPS,
        fault_machine="M3",
        fault_type="Bearing Wear",
        fault_start=120,
        max_degradation=0.85
    )
    result = UnifiedSimulationEngine.run(scenario)
    m3_df = result.telemetry_df[result.telemetry_df["machine_id"] == "M3"].copy()

    # 2. Pure Detector Ablation Study (Layers A-E)
    print("\n[+] Running Calibrated Detector Ablation Study (v6.0 Layers A–E)...")
    ab_df = run_ablation_study(m3_df)
    print(ab_df.to_string(index=False))
    ab_df.to_csv("exports/ablation_results.csv", index=False)

    # 3. Scientific Policy Benchmark
    print("\n[+] Running Scientific Factory Policy Benchmark (v6.0)...")
    policies = [("CORRECTIVE", False), ("PREVENTIVE", False), ("PREDICTIVE", False), ("PREDICTIVE", True)]
    bench_records = []
    for pol_name, is_ps in policies:
        sim = FactoryPolicySimulator(policy_type=pol_name, enable_peak_shaving=is_ps, seed=config.RANDOM_SEED)
        r = sim.run_policy_benchmark()
        bench_records.append({
            "Policy": pol_name if not is_ps else "PREDICTIVE + PEAK SHAVING",
            "Downtime (min)": r.downtime_min, "Events": r.maintenance_events,
            "OEE (%)": r.oee_pct, "Good Units": r.good_units,
            "Energy (kWh)": r.total_energy_kwh, "Peak (kW)": r.peak_demand_kw,
            "Energy/Unit (Wh)": r.energy_per_good_unit_wh, "Energy Cost ($)": r.energy_cost_usd,
            "Downtime Cost ($)": r.downtime_cost_usd, "PF Penalty ($)": r.pf_penalty_usd,
            "Total Cost ($)": r.total_operational_cost_usd, "Carbon (kg CO2)": r.carbon_kg
        })
    bench_df = pd.DataFrame(bench_records)
    print(bench_df.to_string(index=False))
    bench_df.to_csv("exports/benchmark_results.csv", index=False)

    # 4. Export Publication-Grade Plots (300 DPI)
    print("\n[+] Exporting high-resolution figures to exports/...")
    fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=300)
    ax1.plot(m3_df["timestep"], m3_df["vibration_rms"], label="Vibration RMS (g)", color="#1f77b4", lw=1.5)
    ax1_t = ax1.twinx()
    ax1_t.plot(m3_df["timestep"], m3_df["temperature_c"], label="Temperature (°C)", color="#ff7f0e", ls="--", lw=1.5)
    ax1.set_title("PRIME-Factory: Multi-Modal Physical Response & Degradation Dynamics (v6.0)")
    ax1.grid(True, alpha=0.3)

    ax2.plot(m3_df["timestep"], m3_df["health_index"], label="Health Index (HI)", color="#2ca02c", lw=2)
    ax2.axhline(70, color="orange", ls=":", label="Monitor (70)")
    ax2.axhline(50, color="red", ls=":", label="Intervention Threshold (50)")
    ax2.set_xlabel("Simulation Time (Minutes)")
    ax2.set_ylabel("Health Index [0-100]")
    ax2.legend(loc="lower left")
    ax2.grid(True, alpha=0.3)
    plt.tight_layout()
    fig.savefig("exports/figure1_health_response.png", dpi=300)
    plt.close()

    print("\n✓ Master Experiment complete. All tables and figures exported successfully.")
    print("="*80 + "\n")

if __name__ == "__main__":
    run_master_experiment()