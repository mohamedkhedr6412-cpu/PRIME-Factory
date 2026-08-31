"""
Test 4: Scientific Factory-Level Policy Benchmark v3.0
"""
import pandas as pd
import config
from maintenance.policies import FactoryPolicySimulator

policies = [
    ("CORRECTIVE", False),
    ("PREVENTIVE", False),
    ("PREDICTIVE", False),
    ("PREDICTIVE", True)
]

results = []
for pol_type, is_ps in policies:
    sim = FactoryPolicySimulator(policy_type=pol_type, enable_peak_shaving=is_ps)
    res = sim.run_policy_benchmark()
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
print("                             PRIME-FACTORY SCIENTIFIC BENCHMARK RESULTS v3.0 (DECOUPLED & AUDITED)                       ")
print("=========================================================================================================================")
print(bench_df.to_string(index=False))
print("=========================================================================================================================\n")
