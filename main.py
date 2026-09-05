"""
PRIME-Factory Master Experiment & High-Resolution Evidence Generator v6.2 FINAL
Executes the Unified Engine to generate benchmarks, ablation matrices, and 300 DPI publication plots.
Now aligned with v6.2 canonical contracts and consistent fault conditions.
FIXED: Removed fabricated ablation fallback (raises error instead).
FIXED: failure_avoided = corrective_failed and not predictive_failed.
FIXED: CORRECTIVE run once, reused for comparison.
"""

import os
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

import config
from core.models import ScenarioConfig
from simulation.engine import UnifiedSimulationEngine
from maintenance.policies import FactoryPolicySimulator
from evaluation.ablation import run_ablation_study


def run_master_experiment():
    """Run the complete master experiment and export all results."""
    os.makedirs("exports", exist_ok=True)

    print("\n" + "=" * 80)
    print("      PRIME-FACTORY MASTER EXPERIMENT & EVIDENCE ENGINE v6.2")
    print("=" * 80)

    # ------------------------------------------------------------------
    # 1. Run Master Scenario on Target M3 Sealer
    # ------------------------------------------------------------------
    print("\n[1] Running Master Scenario on M3 Sealer...")

    bench_cfg = config.BENCHMARK_CONFIG

    scenario = ScenarioConfig(
        scenario_id="EXP_2026_MASTER_RUN",
        seed=config.RANDOM_SEED,
        product_schedule=bench_cfg["product_schedule"],
        fault_machine=bench_cfg["fault_machine"],
        fault_type=bench_cfg["fault_type"],
        fault_start=bench_cfg["fault_start"],
        max_degradation=bench_cfg["max_degradation"],
        policy_type="PREDICTIVE"
    )

    result = UnifiedSimulationEngine.run(scenario)
    m3_df = result.telemetry_df[result.telemetry_df["machine_id"] == bench_cfg["fault_machine"]].copy()

    print(f"   ✓ Simulation complete: {len(m3_df)} records for M3")
    print(f"   ✓ OEE: {result.oee_pct:.1f}%")
    print(f"   ✓ Good Units: {result.good_units}")
    print(f"   ✓ Total Cost: ${result.total_operational_cost_usd:.2f}")

    # ------------------------------------------------------------------
    # 2. Ablation Study (Layers A-E)
    # ------------------------------------------------------------------
    print("\n[2] Running Calibrated Detector Ablation Study (Layers A–E)...")

    try:
        ab_df = run_ablation_study(m3_df)
        print(ab_df.to_string(index=False))
        ab_df.to_csv("exports/ablation_results.csv", index=False)
        print("   ✓ Ablation results saved to exports/ablation_results.csv")
    except Exception as e:
        # ===== FIXED: Removed fabricated fallback =====
        print(f"   ❌ Ablation study failed: {e}")
        raise RuntimeError(f"Ablation study failed: {e}")

    # ------------------------------------------------------------------
    # 3. Scientific Policy Benchmark (with optimized runs)
    # ------------------------------------------------------------------
    print("\n[3] Running Scientific Factory Policy Benchmark...")

    benchmark_config = config.BENCHMARK_CONFIG.copy()

    policies = [
        ("CORRECTIVE", False),
        ("PREVENTIVE", False),
        ("PREDICTIVE", False),
        ("PREDICTIVE", True)
    ]

    bench_records = []

    # ===== FIXED: Run CORRECTIVE once and store its result =====
    corrective_result = None
    corrective_failed = False

    for pol_name, is_ps in policies:
        print(f"   Running {pol_name}..." + (" + Peak Shaving" if is_ps else ""))
        sim = FactoryPolicySimulator(
            policy_type=pol_name,
            enable_peak_shaving=is_ps,
            seed=config.RANDOM_SEED
        )
        r = sim.run_policy_benchmark(custom_config=benchmark_config)

        # ===== FIXED: Store corrective result for comparison =====
        if pol_name == "CORRECTIVE":
            corrective_result = r
            if hasattr(r, 'resilience') and r.resilience is not None:
                corrective_failed = not getattr(r.resilience, 'failure_avoided', True)

        # ===== FIXED: Calculate failure_avoided =====
        fail_avoided = False
        if pol_name in ["PREVENTIVE", "PREDICTIVE"]:
            # Compare with corrective result
            if corrective_result is not None:
                pred_failed = False
                if hasattr(r, 'resilience') and r.resilience is not None:
                    pred_failed = not getattr(r.resilience, 'failure_avoided', True)
                fail_avoided = corrective_failed and not pred_failed

        bench_records.append({
            "Policy": pol_name if not is_ps else "PREDICTIVE + PEAK SHAVING",
            "Downtime (min)": r.downtime_min,
            "Events": r.maintenance_events,
            "OEE (%)": r.oee_pct,
            "Good Units": r.good_units,
            "Energy (kWh)": r.total_energy_kwh,
            "Peak (kW)": r.peak_demand_kw,
            "Energy/Unit (Wh)": r.energy_per_good_unit_wh,
            "Energy Cost ($)": r.energy_cost_usd,
            "Downtime Cost ($)": r.downtime_cost_usd,
            "PF Penalty ($)": r.pf_penalty_usd,
            "Total Cost ($)": r.total_operational_cost_usd,
            "Carbon (kg CO2)": r.carbon_kg,
            "Failure Avoided": "✅ Yes" if fail_avoided else "❌ No"
        })

    bench_df = pd.DataFrame(bench_records)
    print("\n   Benchmark Results:")
    print(bench_df.to_string(index=False))
    bench_df.to_csv("exports/benchmark_results.csv", index=False)
    print("   ✓ Benchmark results saved to exports/benchmark_results.csv")

    # ------------------------------------------------------------------
    # 4. Export Publication-Grade Plots (300 DPI)
    # ------------------------------------------------------------------
    print("\n[4] Exporting high-resolution figures to exports/...")

    if len(m3_df) > 1:
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=300)

        ax1.plot(m3_df["timestep"], m3_df["vibration_rms"],
                 label="Vibration RMS (g)", color="#1f77b4", lw=1.5)
        ax1_t = ax1.twinx()
        ax1_t.plot(m3_df["timestep"], m3_df["temperature_c"],
                   label="Temperature (°C)", color="#ff7f0e", ls="--", lw=1.5)
        ax1.set_title("PRIME-Factory: Multi-Modal Physical Response & Degradation Dynamics (v6.2)")
        ax1.grid(True, alpha=0.3)
        ax1.set_ylabel("Vibration (g RMS)")
        ax1_t.set_ylabel("Temperature (°C)")

        ax2.plot(m3_df["timestep"], m3_df["health_index"],
                 label="Health Index (HI)", color="#2ca02c", lw=2)
        ax2.axhline(70, color="orange", ls=":", label="Monitor (70)")
        ax2.axhline(50, color="red", ls=":", label="Intervention Threshold (50)")
        ax2.set_xlabel("Simulation Time (Minutes)")
        ax2.set_ylabel("Health Index [0-100]")
        ax2.legend(loc="lower left")
        ax2.grid(True, alpha=0.3)

        plt.tight_layout()
        fig.savefig("exports/figure1_health_response.png", dpi=300)
        plt.close()
        print("   ✓ Figure saved to exports/figure1_health_response.png")

    # ------------------------------------------------------------------
    # 5. Summary
    # ------------------------------------------------------------------
    print("\n" + "=" * 80)
    print("  ✓ MASTER EXPERIMENT COMPLETE")
    print("=" * 80)
    print("\n  Exported files:")
    print("    - exports/benchmark_results.csv")
    print("    - exports/ablation_results.csv")
    print("    - exports/figure1_health_response.png")
    print("\n  Key Findings:")
    best_oee = bench_df.loc[bench_df['OEE (%)'].idxmax()]
    lowest_cost = bench_df.loc[bench_df['Total Cost ($)'].idxmin()]
    print(f"    - Best OEE: {best_oee['OEE (%)']:.1f}% ({best_oee['Policy']})")
    print(f"    - Lowest Cost: ${lowest_cost['Total Cost ($)']:.2f} ({lowest_cost['Policy']})")
    print("=" * 80 + "\n")


if __name__ == "__main__":
    run_master_experiment()