"""
Test 4: Rigorous Factory-Level Policy Benchmark v2.0
Evaluates Corrective vs Preventive vs Predictive vs Peak Shaving on the 5-machine line.
"""
import config
import pandas as pd
from maintenance.policies import FactoryPolicySimulator

schedule = ["Product_B"] * config.TOTAL_TIMESTEPS

policies = [
    ("CORRECTIVE", False),
    ("PREVENTIVE", False),
    ("PREDICTIVE", False),
    ("PREDICTIVE", True)  # Predictive + Peak Shaving
]

results = []

for pol_type, is_ps in policies:
    sim = FactoryPolicySimulator(policy_type=pol_type, enable_peak_shaving=is_ps)
    res = sim.run_policy_benchmark(schedule, fault_machine="M3", start_fault_t=60, max_deg=0.85)
    
    results.append({
        "Maintenance Policy": res["policy"],
        "Downtime (min)": res["downtime_min"],
        "Events": res["events"],
        "OEE (%)": res["oee_pct"],
        "Good Units": res["good_units"],
        "Factory Energy (kWh)": res["total_energy_kwh"],
        "Factory Peak (kW)": res["peak_demand_kw"],
        "Energy/Unit (Wh)": res["energy_per_unit_wh"],
        "Total Cost ($)": res["total_cost_usd"],
        "Carbon (kg CO2)": res["carbon_kg"]
    })

bench_df = pd.DataFrame(results)

print("\n=========================================================================================================================")
print("                                 PRIME-FACTORY FACTORY-LEVEL POLICY BENCHMARK RESULTS v2.0                               ")
print("=========================================================================================================================")
print(bench_df.to_string(index=False))
print("=========================================================================================================================\n")
