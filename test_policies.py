"""
Test 4: Comparative Benchmark of Maintenance Policies & Peak Shaving
Simulates the exact same degradation profile on Machine M3 across:
1. Corrective Policy
2. Preventive Policy
3. PRIME Predictive Policy
4. PRIME Predictive + Peak Shaving
"""
import config
import pandas as pd
from simulation.faults import generate_degradation_profile
from ai.health_index import calculate_health_index
from energy.peak_shaving import apply_peak_shaving
from maintenance.policies import PolicySimulator
from evaluation.kpis import calculate_oee, calculate_energy_kpi

policies = ["CORRECTIVE", "PREVENTIVE", "PREDICTIVE", "PREDICTIVE_PEAK_SHAVING"]
results = []

# توليد نمط تدهور ميكانيكي سريع متكرر
raw_fault_profile = generate_degradation_profile(config.TOTAL_TIMESTEPS, start_time=60, max_degradation=0.85)

for pol_name in policies:
    actual_pol = "PREDICTIVE" if "PREDICTIVE" in pol_name else pol_name
    sim = PolicySimulator(policy_type=actual_pol)
    is_peak_shaving_enabled = (pol_name == "PREDICTIVE_PEAK_SHAVING")

    deg_level = 0.0
    powers = []

    for t in range(config.TOTAL_TIMESTEPS):
        # تطبيق التدهور الطبيعي
        if not sim.is_under_repair and t >= 60:
            deg_level = min(0.85, deg_level + (0.85 / (config.TOTAL_TIMESTEPS - 60)))

        # احتساب خفض السرعة إن كان خفض الذروة مفعلاً
        speed_mod = apply_peak_shaving(t) if is_peak_shaving_enabled else 1.0

        # محاكاة مؤشرات الذكاء الاصطناعي
        ai_score = min(1.0, deg_level * 1.3)
        persistence = 1.0 if deg_level > 0.25 else 0.0
        eci = deg_level * 0.35
        temp = 42.0 + (28.0 * deg_level)
        hi = calculate_health_index(ai_score, persistence, eci, temp)

        base_power = (config.PRODUCTS["Product_B"]["nominal_power_kw"] * (1.0 + 0.35 * deg_level)) * (speed_mod ** 2)
        base_cycle = config.PRODUCTS["Product_B"]["base_cycle_time"] / speed_mod

        step_res = sim.step(t, deg_level, hi, base_power, base_cycle)
        deg_level = step_res["current_degradation"]
        powers.append(step_res["power_kw"])

    operating_time = config.TOTAL_TIMESTEPS - sim.downtime_minutes
    oee_metrics = calculate_oee(
        planned_time_min=config.TOTAL_TIMESTEPS,
        operating_time_min=operating_time,
        ideal_cycle_sec=config.PRODUCTS["Product_B"]["base_cycle_time"],
        total_units=sim.total_units_produced,
        good_units=sim.good_units_produced
    )

    energy_metrics = calculate_energy_kpi(
        total_kwh=sim.energy_consumed_kwh,
        good_units=sim.good_units_produced,
        peak_kw=max(powers)
    )

    results.append({
        "Policy": pol_name,
        "Downtime (min)": sim.downtime_minutes,
        "Interventions": sim.maintenance_events,
        "OEE (%)": oee_metrics["oee_pct"],
        "Good Units": sim.good_units_produced,
        "Total Energy (kWh)": energy_metrics["total_energy_kwh"],
        "Peak Demand (kW)": energy_metrics["peak_demand_kw"],
        "Energy/Unit (Wh)": energy_metrics["energy_per_unit_wh"]
    })

# عرض جدول النتائج النهائي
res_df = pd.DataFrame(results)

print("\n=========================================================================================================")
print("                                 PRIME-FACTORY POLICY BENCHMARK RESULTS                                  ")
print("=========================================================================================================")
print(res_df.to_string(index=False))
print("=========================================================================================================\n")