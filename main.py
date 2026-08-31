"""
PRIME-Factory Master Simulation & Publication Evidence Generator v3.0
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
from energy.eci import calculate_eci
from energy.energy_model import get_factory_aggregated_power
from ai.isolation_forest import PRIMEIsolationForest
from ai.anomaly import AnomalyProcessor
from ai.health_index import calculate_health_index_and_evidence, estimate_rolling_rul
from evaluation.ablation import run_ablation_study

os.makedirs("exports", exist_ok=True)

print("\n=======================================================")
print("   PRIME-FACTORY MASTER EXPERIMENT ENGINE v3.0         ")
print("=======================================================")

factory = PackagingFactory()
train_schedule = generate_switching_schedule(config.TOTAL_TIMESTEPS)
train_df = factory.run_simulation(train_schedule)

ai_model = PRIMEIsolationForest(contamination=0.02)
ai_model.fit(train_df)

test_schedule = ["Product_B"] * config.TOTAL_TIMESTEPS
fault_profile = generate_degradation_profile(config.TOTAL_TIMESTEPS, start_time=120, max_degradation=0.85)
test_df = factory.run_simulation(test_schedule, degradation_targets={"M3": fault_profile})

test_df["eci"] = test_df.apply(lambda r: calculate_eci(r["power_kw"], r["machine_id"], r["product"]), axis=1)
test_df["raw_ai_score"] = ai_model.predict_anomaly_score(test_df)
test_df["context_ai_score"] = test_df["raw_ai_score"]

m3_df = test_df[test_df["machine_id"] == "M3"].copy()
processor = AnomalyProcessor(window_size=config.PERSISTENCE_WINDOW)

hi_list, pers_list, conf_list, rul_list = [], [], [], []

for _, row in m3_df.iterrows():
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
    
    # حساب RUL بالانحدار المتحرك
    rul_val, _ = estimate_rolling_rul(hi_list, window_size=15)
    rul_list.append(rul_val if rul_val is not None else -1)

m3_df["health_index"] = hi_list
m3_df["persistence_ratio"] = pers_list
m3_df["confirmed_anomaly"] = conf_list
m3_df["rul_minutes"] = rul_list

print("\n[+] Running Calibrated Detector Ablation Study...")
ablation_df = run_ablation_study(m3_df)
print(ablation_df.to_string(index=False))

# تصدير الرسوم البيانية بدقة 300 DPI
fig, (ax1, ax2) = plt.subplots(2, 1, figsize=(10, 6), sharex=True, dpi=300)
ax1.plot(m3_df["timestep"], m3_df["vibration_rms"], label="Vibration RMS (g)", color="#1f77b4", lw=1.5)
ax1.set_ylabel("Vibration (g)", color="#1f77b4")
ax1_t = ax1.twinx()
ax1_t.plot(m3_df["timestep"], m3_df["temperature_c"], label="Temperature (°C)", color="#ff7f0e", ls="--", lw=1.5)
ax1_t.set_ylabel("Temp (°C)", color="#ff7f0e")
ax1.set_title("PRIME-Factory: Multi-Modal Physical Response & Degradation Dynamics")

ax2.plot(m3_df["timestep"], m3_df["health_index"], label="Health Index (HI)", color="#2ca02c", lw=2)
ax2.axhline(70, color="orange", ls=":", label="Monitor Threshold (70)")
ax2.axhline(50, color="red", ls=":", label="Degraded Threshold (50)")
ax2.set_xlabel("Simulation Time (Minutes)")
ax2.set_ylabel("Health Index [0-100]")
ax2.legend(loc="lower left")
ax2.grid(True, alpha=0.3)

plt.tight_layout()
fig.savefig("exports/figure1_health_response.png", dpi=300)
plt.close()

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
plt.tight_layout()
fig.savefig("exports/figure2_energy_eci.png", dpi=300)
plt.close()

print("\n    ✓ Figures exported successfully to exports/")
print("=======================================================\n")
